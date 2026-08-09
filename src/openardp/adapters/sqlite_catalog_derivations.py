"""Derived-artifact lifecycle persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime
from itertools import pairwise
from typing import cast

from pydantic import ValidationError

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.domain.derivation import DerivationRecord
from openardp.domain.derivation_lifecycle import (
    DerivationDependency,
    DerivationDependencyKind,
    DerivationEventReason,
    DerivationLifecycleEvent,
    DerivationLifecycleState,
    DerivationNode,
    DerivationPublication,
    DerivationPublicationDisposition,
    DerivationPublicationResult,
    DerivationSlotKey,
    derivation_node_fingerprint,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.storage import StoredObject, decode_storage_datetime, encode_storage_datetime
from openardp.ports.catalog import (
    DerivationConflict,
    DerivationCycleError,
    DerivationDependencyError,
    DerivationIntegrityError,
)


class _SQLiteCatalogDerivationMixin(_SQLiteCatalogBase):
    """Derived-artifact lifecycle persistence."""

    def publish_derivation(
        self,
        publication: DerivationPublication,
    ) -> DerivationPublicationResult:
        """Atomically publish one exact DAG node or converge without a new event."""
        published_at = encode_storage_datetime(publication.published_at)
        with self._write_connection() as connection:
            existing = self._load_derivation(connection, publication.record.artifact_id)
            if existing is not None:
                if not self._derivation_publication_matches(existing, publication):
                    raise DerivationConflict("derivation artifact has conflicting facts")
                return DerivationPublicationResult(
                    disposition=DerivationPublicationDisposition.CONVERGED,
                    node=existing,
                )
            self._validate_derivation_dependencies(connection, publication)
            self._register_object(connection, publication.record_object, registered_at=published_at)
            if publication.output_object is not None:
                self._register_object(
                    connection, publication.output_object, registered_at=published_at
                )
            connection.execute(
                "INSERT INTO derivation_slots("
                "slot_id, namespace, subject_digest, purpose, current_artifact_id, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, NULL, ?, ?) "
                "ON CONFLICT(slot_id) DO NOTHING",
                (
                    publication.slot.slot_id,
                    publication.slot.namespace,
                    publication.slot.subject_digest,
                    publication.slot.purpose,
                    published_at,
                    published_at,
                ),
            )
            slot_row = connection.execute(
                "SELECT * FROM derivation_slots WHERE slot_id = ?",
                (publication.slot.slot_id,),
            ).fetchone()
            if slot_row is None or (
                str(slot_row["namespace"]),
                str(slot_row["subject_digest"]),
                str(slot_row["purpose"]),
            ) != (
                publication.slot.namespace,
                publication.slot.subject_digest,
                publication.slot.purpose,
            ):
                raise DerivationConflict("derivation slot has conflicting identity facts")
            self._fault_point("after_derivation_slot")
            superseded: list[str] = []
            if publication.output_object is not None:
                prior_rows = connection.execute(
                    "SELECT artifact_id FROM derivation_nodes WHERE slot_id = ? "
                    "AND state IN ('CURRENT', 'STALE') ORDER BY artifact_id",
                    (publication.slot.slot_id,),
                ).fetchall()
                for prior_row in prior_rows:
                    prior_id = str(prior_row["artifact_id"])
                    self._transition_derivation(
                        connection,
                        artifact_id=prior_id,
                        to_state=DerivationLifecycleState.SUPERSEDED,
                        reason=DerivationEventReason.SLOT_REPLACED,
                        occurred_at=publication.published_at,
                    )
                    superseded.append(prior_id)
            node = self._node_from_publication(publication)
            record_json = canonical_json_bytes(publication.record.model_dump(mode="json")).decode(
                "utf-8"
            )
            connection.execute(
                "INSERT INTO derivation_nodes("
                "artifact_id, slot_id, state, record_object_id, record_json, output_object_id, "
                "generator_name, generator_version, generator_profile, model_id, config_hash, "
                "prompt_hash, revision, record_created_at, record_completed_at, created_at, "
                "updated_at, failure_code, row_fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    node.artifact_id,
                    node.slot.slot_id,
                    node.state.value,
                    node.record_object.object_id,
                    record_json,
                    node.output_object.object_id if node.output_object is not None else None,
                    node.record.generator.name,
                    node.record.generator.version,
                    node.record.generator.profile,
                    node.record.model_id,
                    node.record.config_hash,
                    node.record.prompt_hash,
                    node.revision,
                    encode_storage_datetime(node.record.created_at),
                    encode_storage_datetime(cast(datetime, node.record.completed_at)),
                    published_at,
                    published_at,
                    node.failure_code,
                    node.row_fingerprint,
                ),
            )
            self._fault_point("after_derivation_node")
            for dependency in publication.dependencies:
                connection.execute(
                    "INSERT INTO derivation_dependencies("
                    "artifact_id, ordinal, kind, input_digest, producer_artifact_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        node.artifact_id,
                        dependency.ordinal,
                        dependency.kind.value,
                        dependency.input_digest,
                        dependency.producer_artifact_id,
                    ),
                )
                self._fault_point("after_derivation_dependency")
            if node.state is DerivationLifecycleState.CURRENT:
                connection.execute(
                    "UPDATE derivation_slots SET current_artifact_id = ?, updated_at = ? "
                    "WHERE slot_id = ?",
                    (node.artifact_id, published_at, node.slot.slot_id),
                )
            reason = (
                DerivationEventReason.GENERATION_FAILED
                if node.state is DerivationLifecycleState.FAILED
                else DerivationEventReason.PUBLISHED
            )
            self._append_derivation_event(
                connection,
                artifact_id=node.artifact_id,
                from_state=None,
                to_state=node.state,
                reason=reason,
                run_id=None,
                occurred_at=published_at,
            )
            self._fault_point("after_derivation_event")
            stored = self._load_derivation(connection, node.artifact_id)
            if stored is None or stored != node:
                raise DerivationIntegrityError("derivation publication verification failed")
            self._fault_point("before_derivation_commit")
            return DerivationPublicationResult(
                disposition=DerivationPublicationDisposition.COMMITTED,
                node=stored,
                superseded_artifact_ids=tuple(superseded),
            )

    def get_derivation(self, artifact_id: str) -> DerivationNode | None:
        """Return one verified derivation lifecycle projection or no result."""
        with self._read_connection() as connection:
            return self._load_derivation(connection, artifact_id)

    def list_derivation_events(
        self,
        artifact_id: str,
    ) -> tuple[DerivationLifecycleEvent, ...]:
        """Return lifecycle evidence in deterministic sequence order."""
        with self._read_connection() as connection:
            return self._load_derivation_events(connection, artifact_id)

    @staticmethod
    def _derivation_dependencies_are_current(
        connection: sqlite3.Connection,
        artifact_id: str,
        *,
        object_is_verified: Callable[[str], bool] | None,
    ) -> bool:
        dependencies = connection.execute(
            "SELECT * FROM derivation_dependencies WHERE artifact_id = ? ORDER BY ordinal",
            (artifact_id,),
        ).fetchall()
        for dependency in dependencies:
            kind = DerivationDependencyKind(str(dependency["kind"]))
            digest = str(dependency["input_digest"])
            if kind is DerivationDependencyKind.EVIDENCE_BINDING:
                active = connection.execute(
                    "SELECT 1 FROM block_lineage_members AS m "
                    "JOIN document_heads AS h ON h.document_id = m.document_id "
                    "AND h.version_id = m.version_id "
                    "AND h.representation_id = m.representation_id "
                    "WHERE m.binding_digest = ? LIMIT 1",
                    (digest,),
                ).fetchone()
                if active is None:
                    return False
            elif kind is DerivationDependencyKind.OBJECT:
                if (
                    connection.execute(
                        "SELECT 1 FROM objects WHERE object_id = ?", (digest,)
                    ).fetchone()
                    is None
                ):
                    return False
                if object_is_verified is None or not object_is_verified(digest):
                    return False
            else:
                producer = connection.execute(
                    "SELECT state, output_object_id FROM derivation_nodes WHERE artifact_id = ?",
                    (str(dependency["producer_artifact_id"]),),
                ).fetchone()
                if (
                    producer is None
                    or str(producer["state"]) != DerivationLifecycleState.CURRENT.value
                    or str(producer["output_object_id"]) != digest
                ):
                    return False
                if object_is_verified is None or not object_is_verified(digest):
                    return False
        return True

    @staticmethod
    def _node_from_publication(publication: DerivationPublication) -> DerivationNode:
        state = (
            DerivationLifecycleState.CURRENT
            if publication.output_object is not None
            else DerivationLifecycleState.FAILED
        )
        skeleton = DerivationNode.model_construct(
            artifact_id=publication.record.artifact_id,
            slot=publication.slot,
            state=state,
            record=publication.record,
            record_object=publication.record_object,
            output_object=publication.output_object,
            dependencies=publication.dependencies,
            revision=1,
            created_at=publication.published_at,
            updated_at=publication.published_at,
            failure_code=publication.failure_code,
            row_fingerprint="sha256:" + "0" * 64,
        )
        return DerivationNode(
            artifact_id=publication.record.artifact_id,
            slot=publication.slot,
            state=state,
            record=publication.record,
            record_object=publication.record_object,
            output_object=publication.output_object,
            dependencies=publication.dependencies,
            revision=1,
            created_at=publication.published_at,
            updated_at=publication.published_at,
            failure_code=publication.failure_code,
            row_fingerprint=derivation_node_fingerprint(skeleton),
        )

    @staticmethod
    def _derivation_publication_matches(
        node: DerivationNode,
        publication: DerivationPublication,
    ) -> bool:
        return (
            node.record == publication.record
            and node.record_object == publication.record_object
            and node.output_object == publication.output_object
            and node.dependencies == publication.dependencies
            and node.slot == publication.slot
            and node.failure_code == publication.failure_code
        )

    def _validate_derivation_dependencies(
        self,
        connection: sqlite3.Connection,
        publication: DerivationPublication,
    ) -> None:
        artifact_id = publication.record.artifact_id
        for dependency in publication.dependencies:
            if dependency.kind is DerivationDependencyKind.EVIDENCE_BINDING:
                available = connection.execute(
                    "SELECT 1 FROM block_lineage_members AS m "
                    "JOIN document_heads AS h ON h.document_id = m.document_id "
                    "AND h.version_id = m.version_id "
                    "AND h.representation_id = m.representation_id "
                    "WHERE m.binding_digest = ? LIMIT 1",
                    (dependency.input_digest,),
                ).fetchone()
                if available is None:
                    raise DerivationDependencyError("evidence binding dependency is not active")
            elif dependency.kind is DerivationDependencyKind.OBJECT:
                available = connection.execute(
                    "SELECT 1 FROM objects WHERE object_id = ?",
                    (dependency.input_digest,),
                ).fetchone()
                if available is None:
                    raise DerivationDependencyError("object dependency is absent")
            else:
                producer_id = cast(str, dependency.producer_artifact_id)
                if producer_id == artifact_id:
                    raise DerivationCycleError("derivation cannot depend on itself")
                producer = connection.execute(
                    "SELECT output_object_id, state FROM derivation_nodes WHERE artifact_id = ?",
                    (producer_id,),
                ).fetchone()
                if (
                    producer is None
                    or str(producer["state"]) != DerivationLifecycleState.CURRENT.value
                    or str(producer["output_object_id"]) != dependency.input_digest
                ):
                    raise DerivationDependencyError(
                        "producer dependency is absent, inactive or output-mismatched"
                    )
                cycle = connection.execute(
                    "WITH RECURSIVE ancestry(artifact_id) AS ("
                    "SELECT producer_artifact_id FROM derivation_dependencies "
                    "WHERE artifact_id = ? AND producer_artifact_id IS NOT NULL "
                    "UNION SELECT d.producer_artifact_id FROM derivation_dependencies AS d "
                    "JOIN ancestry AS a ON d.artifact_id = a.artifact_id "
                    "WHERE d.producer_artifact_id IS NOT NULL) "
                    "SELECT 1 FROM ancestry WHERE artifact_id = ? LIMIT 1",
                    (producer_id, artifact_id),
                ).fetchone()
                if cycle is not None:
                    raise DerivationCycleError("derivation dependency would create a cycle")

    def _load_derivation(
        self,
        connection: sqlite3.Connection,
        artifact_id: str,
    ) -> DerivationNode | None:
        row = connection.execute(
            "SELECT n.*, ro.byte_length AS record_length, oo.byte_length AS output_length, "
            "s.namespace, s.subject_digest, s.purpose, s.current_artifact_id "
            "FROM derivation_nodes AS n "
            "JOIN objects AS ro ON ro.object_id = n.record_object_id "
            "LEFT JOIN objects AS oo ON oo.object_id = n.output_object_id "
            "JOIN derivation_slots AS s ON s.slot_id = n.slot_id "
            "WHERE n.artifact_id = ?",
            (artifact_id,),
        ).fetchone()
        if row is None:
            return None
        dependency_rows = connection.execute(
            "SELECT * FROM derivation_dependencies WHERE artifact_id = ? ORDER BY ordinal",
            (artifact_id,),
        ).fetchall()
        dependencies = tuple(
            DerivationDependency(
                ordinal=int(item["ordinal"]),
                kind=DerivationDependencyKind(str(item["kind"])),
                input_digest=str(item["input_digest"]),
                producer_artifact_id=(
                    str(item["producer_artifact_id"])
                    if item["producer_artifact_id"] is not None
                    else None
                ),
            )
            for item in dependency_rows
        )
        try:
            record = DerivationRecord.model_validate_json(str(row["record_json"]))
            if (
                str(row["generator_name"]) != record.generator.name
                or str(row["generator_version"]) != record.generator.version
                or (str(row["generator_profile"]) if row["generator_profile"] is not None else None)
                != record.generator.profile
                or (str(row["model_id"]) if row["model_id"] is not None else None)
                != record.model_id
                or str(row["config_hash"]) != record.config_hash
                or (str(row["prompt_hash"]) if row["prompt_hash"] is not None else None)
                != record.prompt_hash
                or decode_storage_datetime(str(row["record_created_at"])) != record.created_at
                or decode_storage_datetime(str(row["record_completed_at"])) != record.completed_at
            ):
                raise DerivationIntegrityError("stored derivation recipe columns drifted")
            output_id = row["output_object_id"]
            node = DerivationNode(
                artifact_id=str(row["artifact_id"]),
                slot=DerivationSlotKey(
                    slot_id=str(row["slot_id"]),
                    namespace=str(row["namespace"]),
                    subject_digest=str(row["subject_digest"]),
                    purpose=str(row["purpose"]),
                ),
                state=DerivationLifecycleState(str(row["state"])),
                record=record,
                record_object=StoredObject(
                    object_id=str(row["record_object_id"]),
                    byte_length=int(row["record_length"]),
                ),
                output_object=(
                    StoredObject(
                        object_id=str(output_id),
                        byte_length=int(row["output_length"]),
                    )
                    if output_id is not None
                    else None
                ),
                dependencies=dependencies,
                revision=int(row["revision"]),
                created_at=decode_storage_datetime(str(row["created_at"])),
                updated_at=decode_storage_datetime(str(row["updated_at"])),
                failure_code=(
                    str(row["failure_code"]) if row["failure_code"] is not None else None
                ),
                row_fingerprint=str(row["row_fingerprint"]),
            )
            if (
                node.state is DerivationLifecycleState.CURRENT
                and str(row["current_artifact_id"]) != node.artifact_id
            ):
                raise DerivationIntegrityError("current derivation slot pointer drifted")
        except (ValidationError, ValueError) as error:
            raise DerivationIntegrityError("stored derivation node is invalid") from error
        return node

    def _transition_derivation(
        self,
        connection: sqlite3.Connection,
        *,
        artifact_id: str,
        to_state: DerivationLifecycleState,
        reason: DerivationEventReason,
        occurred_at: datetime,
        run_id: str | None = None,
    ) -> DerivationNode:
        current = self._load_derivation(connection, artifact_id)
        if current is None:
            raise DerivationIntegrityError("derivation transition target is absent")
        if current.state is to_state:
            return current
        skeleton = DerivationNode.model_construct(
            artifact_id=current.artifact_id,
            slot=current.slot,
            state=to_state,
            record=current.record,
            record_object=current.record_object,
            output_object=current.output_object,
            dependencies=current.dependencies,
            revision=current.revision + 1,
            created_at=current.created_at,
            updated_at=occurred_at,
            failure_code=current.failure_code,
            row_fingerprint="sha256:" + "0" * 64,
        )
        transitioned = DerivationNode(
            artifact_id=current.artifact_id,
            slot=current.slot,
            state=to_state,
            record=current.record,
            record_object=current.record_object,
            output_object=current.output_object,
            dependencies=current.dependencies,
            revision=current.revision + 1,
            created_at=current.created_at,
            updated_at=occurred_at,
            failure_code=current.failure_code,
            row_fingerprint=derivation_node_fingerprint(skeleton),
        )
        occurred_text = encode_storage_datetime(occurred_at)
        connection.execute(
            "UPDATE derivation_nodes SET state = ?, revision = ?, updated_at = ?, "
            "row_fingerprint = ? WHERE artifact_id = ? AND revision = ?",
            (
                transitioned.state.value,
                transitioned.revision,
                occurred_text,
                transitioned.row_fingerprint,
                artifact_id,
                current.revision,
            ),
        )
        if current.state is DerivationLifecycleState.CURRENT:
            connection.execute(
                "UPDATE derivation_slots SET current_artifact_id = NULL, updated_at = ? "
                "WHERE slot_id = ? AND current_artifact_id = ?",
                (occurred_text, current.slot.slot_id, artifact_id),
            )
        self._append_derivation_event(
            connection,
            artifact_id=artifact_id,
            from_state=current.state,
            to_state=to_state,
            reason=reason,
            run_id=run_id,
            occurred_at=occurred_text,
        )
        self._fault_point("after_derivation_state")
        return transitioned

    @staticmethod
    def _append_derivation_event(
        connection: sqlite3.Connection,
        *,
        artifact_id: str,
        from_state: DerivationLifecycleState | None,
        to_state: DerivationLifecycleState,
        reason: DerivationEventReason,
        run_id: str | None,
        occurred_at: str,
    ) -> None:
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM derivation_events "
                "WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO derivation_events(artifact_id, sequence, from_state, to_state, "
            "reason, run_id, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                artifact_id,
                sequence,
                from_state.value if from_state is not None else None,
                to_state.value,
                reason.value,
                run_id,
                occurred_at,
            ),
        )

    def _load_derivation_events(
        self,
        connection: sqlite3.Connection,
        artifact_id: str,
    ) -> tuple[DerivationLifecycleEvent, ...]:
        rows = connection.execute(
            "SELECT * FROM derivation_events WHERE artifact_id = ? ORDER BY sequence",
            (artifact_id,),
        ).fetchall()
        try:
            events = tuple(
                DerivationLifecycleEvent(
                    artifact_id=str(row["artifact_id"]),
                    sequence=int(row["sequence"]),
                    from_state=(
                        DerivationLifecycleState(str(row["from_state"]))
                        if row["from_state"] is not None
                        else None
                    ),
                    to_state=DerivationLifecycleState(str(row["to_state"])),
                    reason=DerivationEventReason(str(row["reason"])),
                    run_id=str(row["run_id"]) if row["run_id"] is not None else None,
                    occurred_at=decode_storage_datetime(str(row["occurred_at"])),
                )
                for row in rows
            )
            for previous, current in pairwise(events):
                if current.from_state is not previous.to_state:
                    raise DerivationIntegrityError("derivation event chain drifted")
            if events:
                node = self._load_derivation(connection, artifact_id)
                if node is None or events[-1].to_state is not node.state:
                    raise DerivationIntegrityError("derivation event terminal state drifted")
            return events
        except (ValidationError, ValueError) as error:
            raise DerivationIntegrityError("stored derivation event is invalid") from error


__all__ = ["_SQLiteCatalogDerivationMixin"]
