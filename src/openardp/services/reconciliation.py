"""Verified CAS-first orchestration for conservative block reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from openardp.domain.block import ContentBlock
from openardp.domain.common import validate_json
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import (
    RepresentationAggregate,
    RepresentationScope,
    RepresentationState,
)
from openardp.domain.reconciliation import (
    ReconciliationBlock,
    ReconciliationResult,
    reconcile_blocks,
)
from openardp.domain.relation import BlockReference
from openardp.ports.catalog import (
    ReconciliationDerivationCatalog,
    ReconciliationIntegrityError,
    ReconciliationScopeError,
)
from openardp.ports.context import CancellationCheck
from openardp.ports.object_store import ObjectStore, ObjectStoreError


class ReconciliationCancelled(RuntimeError):
    """Raised at a bounded phase when reconciliation is cancelled."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _never_cancel() -> bool:
    return False


class ReconciliationService:
    """Verify two READY F002 aggregates, plan, publish relations and commit atomically."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: ReconciliationDerivationCatalog,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """Bind provider-neutral storage ports and an injectable UTC clock."""
        self._object_store = object_store
        self._catalog = catalog
        self._clock = clock

    def reconcile(
        self,
        previous_scope: RepresentationScope,
        current_scope: RepresentationScope,
        *,
        cancellation_check: CancellationCheck | None = None,
    ) -> ReconciliationResult:
        """Publish one verified deterministic reconciliation of distinct same-document scopes."""
        cancel = cancellation_check or _never_cancel
        if (
            previous_scope.document_id != current_scope.document_id
            or previous_scope == current_scope
        ):
            raise ReconciliationScopeError("reconciliation scopes are ineligible")
        self._check_cancel(cancel)
        previous_aggregate = self._required_ready(previous_scope)
        current_aggregate = self._required_ready(current_scope)
        previous = self._project(previous_aggregate, include_lineage=True, cancel=cancel)
        current = self._project(current_aggregate, include_lineage=True, cancel=cancel)
        ready_at = current_aggregate.representation.ready_at
        if ready_at is None:
            raise ReconciliationIntegrityError("ready representation timestamp is absent")
        plan = reconcile_blocks(
            previous,
            current,
            previous_scope=previous_scope,
            current_scope=current_scope,
            current_ready_at=ready_at,
            created_at=self._clock(),
        )
        self._check_cancel(cancel)
        for match in plan.matches:
            payload = canonical_json_bytes(match.relation.model_dump(mode="json"))
            stored = self._object_store.put_chunks((payload,))
            verified = self._object_store.verify(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            if verified != match.relation_object:
                raise ReconciliationIntegrityError("relation object publication is inconsistent")
            self._check_cancel(cancel)
        return self._catalog.commit_reconciliation(
            plan,
            object_is_verified=self._object_is_verified,
        )

    def _required_ready(self, scope: RepresentationScope) -> RepresentationAggregate:
        aggregate = self._catalog.load_representation(scope)
        if aggregate is None or aggregate.representation.state is not RepresentationState.READY:
            raise ReconciliationScopeError("reconciliation scope is not ready")
        return aggregate

    def _project(
        self,
        aggregate: RepresentationAggregate,
        *,
        include_lineage: bool,
        cancel: CancellationCheck,
    ) -> tuple[ReconciliationBlock, ...]:
        projected: list[ReconciliationBlock] = []
        try:
            for row in aggregate.blocks:
                self._check_cancel(cancel)
                verified = self._object_store.verify(
                    row.object.object_id,
                    expected_length=row.object.byte_length,
                )
                payload = b"".join(self._object_store.iter_chunks(verified.object_id))
                block = validate_json(ContentBlock, payload)
                if payload != canonical_json_bytes(block.model_dump(mode="json")):
                    raise ReconciliationIntegrityError("block object is non-canonical")
                if (
                    block.document_id != row.scope.document_id
                    or block.version_id != row.scope.version_id
                    or block.representation_id != row.scope.representation_id
                    or block.block_id != row.block_id
                    or block.parent_id != row.parent_id
                    or block.kind is not row.kind
                    or block.order != row.order
                    or block.source.extensions.get("openardp.text")
                    != {"line_start": row.line_start, "line_end": row.line_end}
                ):
                    raise ReconciliationIntegrityError("block projection is inconsistent")
                reference = BlockReference(
                    record_type="block",
                    document_id=block.document_id,
                    version_id=block.version_id,
                    representation_id=block.representation_id,
                    block_id=block.block_id,
                )
                membership = self._catalog.get_lineage(reference) if include_lineage else None
                projected.append(
                    ReconciliationBlock(
                        reference=reference,
                        parent_id=block.parent_id,
                        kind=block.kind,
                        order=block.order,
                        ordinal=row.ordinal,
                        canonical_hash=block.canonical_hash,
                        text=block.text,
                        structured_hash=(
                            canonical_sha256(block.structured)
                            if block.structured is not None
                            else None
                        ),
                        asset_id=block.asset_id,
                        native_stable_id=block.source.native_id,
                        lineage_id=(membership.lineage_id if membership is not None else None),
                        lineage_introduced_by_run_id=(
                            membership.introduced_by_run_id if membership is not None else None
                        ),
                    )
                )
        except ReconciliationIntegrityError:
            raise
        except (ObjectStoreError, ValidationError, ValueError) as error:
            raise ReconciliationIntegrityError("block verification failed") from error
        return tuple(projected)

    @staticmethod
    def _check_cancel(cancel: CancellationCheck) -> None:
        if cancel():
            raise ReconciliationCancelled("reconciliation cancelled")

    def _object_is_verified(self, object_id: str) -> bool:
        try:
            self._object_store.verify(object_id)
        except ObjectStoreError:
            return False
        return True


__all__ = ["ReconciliationCancelled", "ReconciliationService"]
