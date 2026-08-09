"""Block reconciliation and lineage persistence."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from uuid import UUID

from pydantic import ValidationError

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.domain.common import ComponentDescriptor, GenerationProvenance
from openardp.domain.derivation_lifecycle import DerivationEventReason, DerivationLifecycleState
from openardp.domain.ingestion import RepresentationScope, RepresentationState
from openardp.domain.reconciliation import (
    RECONCILIATION_ALGORITHM_VERSION,
    BlockLineageMembership,
    MatchMethod,
    ReconciliationDisposition,
    ReconciliationMatch,
    ReconciliationPlan,
    ReconciliationResult,
)
from openardp.domain.relation import BlockReference, Relation, RelationKind
from openardp.domain.storage import StoredObject, decode_storage_datetime, encode_storage_datetime
from openardp.ports.catalog import (
    ReconciliationConflict,
    ReconciliationIntegrityError,
    ReconciliationScopeError,
)


class _SQLiteCatalogReconciliationMixin(_SQLiteCatalogBase):
    """Block reconciliation and lineage persistence."""

    def commit_reconciliation(
        self,
        plan: ReconciliationPlan,
        *,
        object_is_verified: Callable[[str], bool] | None = None,
    ) -> ReconciliationResult:
        """Atomically publish one complete lineage plan or converge exactly."""
        created_at = encode_storage_datetime(plan.created_at)
        with self._write_connection() as connection:
            existing = self._load_reconciliation(connection, plan.run_id)
            if existing is not None:
                if existing.plan.result_fingerprint != plan.result_fingerprint:
                    raise ReconciliationConflict("reconciliation run has conflicting facts")
                stale_ids: tuple[str, ...] = ()
                reactivated_ids: tuple[str, ...] = ()
                head = self._required_document_head(
                    connection, existing.plan.current_scope.document_id
                )
                if head.scope == existing.plan.current_scope:
                    lifecycle_plan = existing.plan.model_copy(
                        update={"created_at": plan.created_at}
                    )
                    stale_ids, reactivated_ids = self._apply_reconciliation_lifecycle(
                        connection,
                        lifecycle_plan,
                        object_is_verified=object_is_verified,
                    )
                return ReconciliationResult(
                    disposition=ReconciliationDisposition.CONVERGED,
                    plan=existing.plan,
                    stale_artifact_ids=stale_ids,
                    reactivated_artifact_ids=reactivated_ids,
                )
            target = connection.execute(
                "SELECT run_id FROM reconciliation_runs WHERE document_id = ? "
                "AND current_version_id = ? AND current_representation_id = ?",
                (
                    str(plan.current_scope.document_id),
                    plan.current_scope.version_id,
                    plan.current_scope.representation_id,
                ),
            ).fetchone()
            if target is not None:
                raise ReconciliationConflict("reconciliation target already has different facts")
            for scope in (plan.previous_scope, plan.current_scope):
                aggregate = self._required_representation(connection, scope)
                if aggregate.representation.state is not RepresentationState.READY:
                    raise ReconciliationScopeError("reconciliation scope is not ready")
            head = self._required_document_head(connection, plan.current_scope.document_id)
            if head.scope != plan.current_scope:
                raise ReconciliationScopeError("reconciliation target is not the current head")
            connection.execute(
                "INSERT INTO reconciliation_runs("
                "run_id, document_id, previous_version_id, previous_representation_id, "
                "current_version_id, current_representation_id, algorithm_version, "
                "config_hash, result_fingerprint, matched_count, reusable_count, new_count, "
                "ambiguous_count, comparison_count, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan.run_id,
                    str(plan.current_scope.document_id),
                    plan.previous_scope.version_id,
                    plan.previous_scope.representation_id,
                    plan.current_scope.version_id,
                    plan.current_scope.representation_id,
                    plan.algorithm_version,
                    plan.config_hash,
                    plan.result_fingerprint,
                    plan.matched_count,
                    plan.reusable_count,
                    plan.new_count,
                    plan.ambiguous_count,
                    plan.comparison_count,
                    created_at,
                ),
            )
            self._fault_point("after_reconciliation_run")
            for membership in (*plan.seed_memberships, *plan.memberships):
                self._persist_lineage_membership(connection, membership, created_at=created_at)
            self._fault_point("after_reconciliation_members")
            for match in plan.matches:
                self._register_object(connection, match.relation_object, registered_at=created_at)
                connection.execute(
                    "INSERT INTO reconciliation_relations("
                    "relation_id, run_id, relation_object_id, method, confidence_ppm, reusable, "
                    "document_id, previous_version_id, previous_representation_id, "
                    "previous_block_id, current_version_id, current_representation_id, "
                    "current_block_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        match.relation.relation_id,
                        plan.run_id,
                        match.relation_object.object_id,
                        match.method.value,
                        match.confidence_ppm,
                        int(match.reusable),
                        str(match.current.document_id),
                        match.previous.version_id,
                        match.previous.representation_id,
                        str(match.previous.block_id),
                        match.current.version_id,
                        match.current.representation_id,
                        str(match.current.block_id),
                    ),
                )
                self._fault_point("after_reconciliation_relation")
            stale_ids, reactivated_ids = self._apply_reconciliation_lifecycle(
                connection,
                plan,
                object_is_verified=object_is_verified,
            )
            stored = self._load_reconciliation(connection, plan.run_id)
            if stored is None or stored.plan.result_fingerprint != plan.result_fingerprint:
                raise ReconciliationIntegrityError("reconciliation verification failed")
            self._fault_point("before_reconciliation_commit")
            return ReconciliationResult(
                disposition=ReconciliationDisposition.COMMITTED,
                plan=stored.plan,
                stale_artifact_ids=stale_ids,
                reactivated_artifact_ids=reactivated_ids,
            )

    def get_reconciliation(self, run_id: str) -> ReconciliationResult | None:
        """Return one verified complete reconciliation without mutable side effects."""
        with self._read_connection() as connection:
            return self._load_reconciliation(connection, run_id)

    def get_lineage(self, block: BlockReference) -> BlockLineageMembership | None:
        """Return one exact lineage membership for a canonical block reference."""
        with self._read_connection() as connection:
            return self._load_lineage_membership(connection, block)

    def _persist_lineage_membership(
        self,
        connection: sqlite3.Connection,
        membership: BlockLineageMembership,
        *,
        created_at: str,
    ) -> None:
        existing = self._load_lineage_membership(connection, membership.block)
        if existing is not None:
            if existing != membership:
                raise ReconciliationConflict("block lineage membership has conflicting facts")
            return
        block = connection.execute(
            "SELECT object_id FROM representation_block_projection WHERE document_id = ? "
            "AND version_id = ? AND representation_id = ? AND block_id = ?",
            (
                str(membership.block.document_id),
                membership.block.version_id,
                membership.block.representation_id,
                str(membership.block.block_id),
            ),
        ).fetchone()
        if block is None:
            raise ReconciliationIntegrityError("lineage block is absent")
        connection.execute(
            "INSERT OR IGNORE INTO lineage_block_keys("
            "document_id, version_id, representation_id, ordinal, block_id, object_id, "
            "parent_id, kind, sibling_order, line_start, line_end) "
            "SELECT document_id, version_id, representation_id, ordinal, block_id, object_id, "
            "parent_id, kind, sibling_order, line_start, line_end "
            "FROM representation_block_projection WHERE document_id = ? AND version_id = ? "
            "AND representation_id = ? AND block_id = ?",
            (
                str(membership.block.document_id),
                membership.block.version_id,
                membership.block.representation_id,
                str(membership.block.block_id),
            ),
        )
        lineage = connection.execute(
            "SELECT document_id FROM block_lineages WHERE lineage_id = ?",
            (membership.lineage_id,),
        ).fetchone()
        if lineage is None:
            connection.execute(
                "INSERT INTO block_lineages("
                "lineage_id, document_id, origin_version_id, origin_representation_id, "
                "origin_block_id, introduced_by_run_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    membership.lineage_id,
                    str(membership.block.document_id),
                    membership.block.version_id,
                    membership.block.representation_id,
                    str(membership.block.block_id),
                    membership.introduced_by_run_id,
                    created_at,
                ),
            )
            self._fault_point("after_reconciliation_lineage")
        elif str(lineage["document_id"]) != str(membership.block.document_id):
            raise ReconciliationConflict("lineage cannot cross logical documents")
        connection.execute(
            "INSERT INTO block_lineage_members("
            "document_id, version_id, representation_id, block_id, lineage_id, "
            "canonical_hash, binding_digest, introduced_by_run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(membership.block.document_id),
                membership.block.version_id,
                membership.block.representation_id,
                str(membership.block.block_id),
                membership.lineage_id,
                membership.canonical_hash,
                membership.binding_digest,
                membership.introduced_by_run_id,
            ),
        )

    @staticmethod
    def _membership_from_row(row: sqlite3.Row) -> BlockLineageMembership:
        return BlockLineageMembership(
            lineage_id=str(row["lineage_id"]),
            block=BlockReference(
                record_type="block",
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
                block_id=UUID(str(row["block_id"])),
            ),
            canonical_hash=str(row["canonical_hash"]),
            binding_digest=str(row["binding_digest"]),
            introduced_by_run_id=str(row["introduced_by_run_id"]),
        )

    def _load_lineage_membership(
        self,
        connection: sqlite3.Connection,
        block: BlockReference,
    ) -> BlockLineageMembership | None:
        row = connection.execute(
            "SELECT * FROM block_lineage_members WHERE document_id = ? AND version_id = ? "
            "AND representation_id = ? AND block_id = ?",
            (
                str(block.document_id),
                block.version_id,
                block.representation_id,
                str(block.block_id),
            ),
        ).fetchone()
        if row is None:
            return None
        try:
            membership = self._membership_from_row(row)
        except ValidationError as error:
            raise ReconciliationIntegrityError("stored lineage membership is invalid") from error
        if membership.block != block:
            raise ReconciliationIntegrityError("stored lineage membership scope drifted")
        return membership

    def _load_reconciliation(
        self,
        connection: sqlite3.Connection,
        run_id: str,
    ) -> ReconciliationResult | None:
        row = connection.execute(
            "SELECT * FROM reconciliation_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        document_id = UUID(str(row["document_id"]))
        previous_scope = RepresentationScope(
            document_id=document_id,
            version_id=str(row["previous_version_id"]),
            representation_id=str(row["previous_representation_id"]),
        )
        current_scope = RepresentationScope(
            document_id=document_id,
            version_id=str(row["current_version_id"]),
            representation_id=str(row["current_representation_id"]),
        )
        membership_rows = connection.execute(
            "SELECT m.* FROM block_lineage_members AS m "
            "JOIN representation_block_projection AS b ON b.document_id = m.document_id "
            "AND b.version_id = m.version_id AND b.representation_id = m.representation_id "
            "AND b.block_id = m.block_id WHERE m.document_id = ? AND m.version_id = ? "
            "AND m.representation_id = ? ORDER BY b.ordinal",
            (str(document_id), current_scope.version_id, current_scope.representation_id),
        ).fetchall()
        seed_rows = connection.execute(
            "SELECT m.* FROM block_lineage_members AS m "
            "JOIN representation_block_projection AS b ON b.document_id = m.document_id "
            "AND b.version_id = m.version_id AND b.representation_id = m.representation_id "
            "AND b.block_id = m.block_id WHERE m.document_id = ? AND m.version_id = ? "
            "AND m.representation_id = ? ORDER BY b.ordinal",
            (str(document_id), previous_scope.version_id, previous_scope.representation_id),
        ).fetchall()
        memberships = tuple(self._membership_from_row(item) for item in membership_rows)
        seeds = tuple(self._membership_from_row(item) for item in seed_rows)
        ready = connection.execute(
            "SELECT ready_at FROM document_representations WHERE document_id = ? "
            "AND version_id = ? AND representation_id = ?",
            (str(document_id), current_scope.version_id, current_scope.representation_id),
        ).fetchone()
        if ready is None or ready["ready_at"] is None:
            raise ReconciliationIntegrityError("reconciliation target representation is absent")
        relation_rows = connection.execute(
            "SELECT r.*, o.byte_length, pm.lineage_id, pm.canonical_hash AS previous_hash, "
            "cm.canonical_hash AS current_hash FROM reconciliation_relations AS r "
            "JOIN objects AS o ON o.object_id = r.relation_object_id "
            "JOIN block_lineage_members AS pm ON pm.document_id = r.document_id "
            "AND pm.version_id = r.previous_version_id "
            "AND pm.representation_id = r.previous_representation_id "
            "AND pm.block_id = r.previous_block_id "
            "JOIN block_lineage_members AS cm ON cm.document_id = r.document_id "
            "AND cm.version_id = r.current_version_id "
            "AND cm.representation_id = r.current_representation_id "
            "AND cm.block_id = r.current_block_id "
            "JOIN representation_block_projection AS cb ON cb.document_id = r.document_id "
            "AND cb.version_id = r.current_version_id "
            "AND cb.representation_id = r.current_representation_id "
            "AND cb.block_id = r.current_block_id "
            "WHERE r.run_id = ? ORDER BY cb.ordinal",
            (run_id,),
        ).fetchall()
        matches: list[ReconciliationMatch] = []
        for relation_row in relation_rows:
            previous = BlockReference(
                record_type="block",
                document_id=document_id,
                version_id=str(relation_row["previous_version_id"]),
                representation_id=str(relation_row["previous_representation_id"]),
                block_id=UUID(str(relation_row["previous_block_id"])),
            )
            current = BlockReference(
                record_type="block",
                document_id=document_id,
                version_id=str(relation_row["current_version_id"]),
                representation_id=str(relation_row["current_representation_id"]),
                block_id=UUID(str(relation_row["current_block_id"])),
            )
            confidence_ppm = int(relation_row["confidence_ppm"])
            relation = Relation(
                schema_version="0.1.0",
                relation_id=str(relation_row["relation_id"]),
                kind=RelationKind.SAME_LOGICAL_BLOCK_AS,
                source=current,
                target=previous,
                confidence=confidence_ppm / 1_000_000,
                algorithm_version=RECONCILIATION_ALGORITHM_VERSION,
                provenance=GenerationProvenance(
                    component=ComponentDescriptor(
                        name="openardp-reconciliation",
                        version=RECONCILIATION_ALGORITHM_VERSION,
                        profile="conservative",
                    ),
                    created_at=decode_storage_datetime(str(ready["ready_at"])),
                ),
            )
            matches.append(
                ReconciliationMatch(
                    previous=previous,
                    current=current,
                    lineage_id=str(relation_row["lineage_id"]),
                    previous_canonical_hash=str(relation_row["previous_hash"]),
                    current_canonical_hash=str(relation_row["current_hash"]),
                    method=MatchMethod(str(relation_row["method"])),
                    confidence_ppm=confidence_ppm,
                    reusable=bool(relation_row["reusable"]),
                    relation=relation,
                    relation_object=StoredObject(
                        object_id=str(relation_row["relation_object_id"]),
                        byte_length=int(relation_row["byte_length"]),
                    ),
                )
            )
        previous_bindings = {item.binding_digest for item in seeds}
        current_bindings = {item.binding_digest for item in memberships}
        try:
            plan = ReconciliationPlan(
                run_id=str(row["run_id"]),
                previous_scope=previous_scope,
                current_scope=current_scope,
                algorithm_version=str(row["algorithm_version"]),
                config_hash=str(row["config_hash"]),
                seed_memberships=seeds,
                memberships=memberships,
                matches=tuple(matches),
                inactive_binding_digests=tuple(sorted(previous_bindings - current_bindings)),
                matched_count=int(row["matched_count"]),
                reusable_count=int(row["reusable_count"]),
                new_count=int(row["new_count"]),
                ambiguous_count=int(row["ambiguous_count"]),
                comparison_count=int(row["comparison_count"]),
                result_fingerprint=str(row["result_fingerprint"]),
                created_at=decode_storage_datetime(str(row["created_at"])),
            )
        except (ValidationError, ValueError) as error:
            raise ReconciliationIntegrityError("stored reconciliation is invalid") from error
        return ReconciliationResult(
            disposition=ReconciliationDisposition.COMMITTED,
            plan=plan,
        )

    def _apply_reconciliation_lifecycle(
        self,
        connection: sqlite3.Connection,
        plan: ReconciliationPlan,
        *,
        object_is_verified: Callable[[str], bool] | None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        stale_ids: list[str] = []
        if plan.inactive_binding_digests:
            for artifact_id in self._invalidation_artifact_ids(
                connection,
                plan.inactive_binding_digests,
            ):
                self._transition_derivation(
                    connection,
                    artifact_id=artifact_id,
                    to_state=DerivationLifecycleState.STALE,
                    reason=DerivationEventReason.DEPENDENCY_INACTIVE,
                    run_id=plan.run_id,
                    occurred_at=plan.created_at,
                )
                stale_ids.append(artifact_id)

        reactivated_ids: list[str] = []
        made_progress = True
        while made_progress:
            made_progress = False
            candidates = connection.execute(
                "SELECT n.artifact_id, n.slot_id FROM derivation_nodes AS n "
                "JOIN derivation_slots AS s ON s.slot_id = n.slot_id "
                "WHERE n.state = 'STALE' AND s.current_artifact_id IS NULL "
                "ORDER BY n.artifact_id"
            ).fetchall()
            for candidate in candidates:
                artifact_id = str(candidate["artifact_id"])
                slot_id = str(candidate["slot_id"])
                if not self._derivation_dependencies_are_current(
                    connection,
                    artifact_id,
                    object_is_verified=object_is_verified,
                ):
                    continue
                connection.execute(
                    "UPDATE derivation_slots SET current_artifact_id = ?, updated_at = ? "
                    "WHERE slot_id = ? AND current_artifact_id IS NULL",
                    (artifact_id, encode_storage_datetime(plan.created_at), slot_id),
                )
                if int(connection.execute("SELECT changes()").fetchone()[0]) != 1:
                    continue
                self._transition_derivation(
                    connection,
                    artifact_id=artifact_id,
                    to_state=DerivationLifecycleState.CURRENT,
                    reason=DerivationEventReason.REACTIVATED,
                    run_id=plan.run_id,
                    occurred_at=plan.created_at,
                )
                reactivated_ids.append(artifact_id)
                made_progress = True
        self._fault_point("after_reconciliation_lifecycle")
        return tuple(stale_ids), tuple(reactivated_ids)

    @staticmethod
    def _invalidation_artifact_ids(
        connection: sqlite3.Connection,
        inactive_binding_digests: tuple[str, ...],
    ) -> tuple[str, ...]:
        rows = connection.execute(
            "WITH RECURSIVE affected(artifact_id) AS ("
            "SELECT DISTINCT n.artifact_id FROM derivation_nodes AS n "
            "JOIN derivation_dependencies AS d ON d.artifact_id = n.artifact_id "
            "WHERE n.state = 'CURRENT' AND d.kind = 'EVIDENCE_BINDING' "
            "AND d.input_digest IN (SELECT value FROM json_each(?)) "
            "UNION SELECT n.artifact_id FROM derivation_nodes AS n "
            "JOIN derivation_dependencies AS d ON d.artifact_id = n.artifact_id "
            "JOIN affected AS a ON a.artifact_id = d.producer_artifact_id "
            "WHERE n.state = 'CURRENT' AND d.kind = 'DERIVATION_OUTPUT') "
            "SELECT artifact_id FROM affected ORDER BY artifact_id",
            (json.dumps(inactive_binding_digests),),
        ).fetchall()
        return tuple(str(row["artifact_id"]) for row in rows)


__all__ = ["_SQLiteCatalogReconciliationMixin"]
