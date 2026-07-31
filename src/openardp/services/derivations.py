"""Provider-free CAS-first derivation DAG publication and verified reads."""

from __future__ import annotations

from collections.abc import Iterable

from openardp.domain.derivation import DerivationRecord, DerivationState
from openardp.domain.derivation_lifecycle import (
    DerivationDependency,
    DerivationDependencyKind,
    DerivationLifecycleEvent,
    DerivationNode,
    DerivationPublication,
    DerivationPublicationResult,
    DerivationSlotKey,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.ports.catalog import (
    DerivationDependencyError,
    DerivationIntegrityError,
    ReconciliationDerivationCatalog,
)
from openardp.ports.context import CancellationCheck
from openardp.ports.object_store import ObjectStore, ObjectStoreError


class DerivationPublicationCancelled(RuntimeError):
    """Raised at a bounded phase when derivation publication is cancelled."""


def _never_cancel() -> bool:
    return False


class DerivationService:
    """Publish already-generated exact outputs without invoking a model or provider."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: ReconciliationDerivationCatalog,
    ) -> None:
        """Bind provider-neutral immutable object and transactional catalog ports."""
        self._object_store = object_store
        self._catalog = catalog

    def publish(
        self,
        record: DerivationRecord,
        dependencies: tuple[DerivationDependency, ...],
        slot: DerivationSlotKey,
        *,
        output_chunks: Iterable[bytes] | None = None,
        failure_code: str | None = None,
        cancellation_check: CancellationCheck | None = None,
    ) -> DerivationPublicationResult:
        """CAS-publish exact record/output bytes then atomically publish their DAG node."""
        cancel = cancellation_check or _never_cancel
        self._check_cancel(cancel)
        record_payload = canonical_json_bytes(record.model_dump(mode="json"))
        record_object = self._object_store.put_chunks((record_payload,))
        record_object = self._object_store.verify(
            record_object.object_id,
            expected_length=record_object.byte_length,
        )
        self._check_cancel(cancel)
        if record.state is DerivationState.READY:
            if output_chunks is None or failure_code is not None:
                raise DerivationIntegrityError(
                    "ready derivation requires output chunks and no failure code"
                )
            output_object = self._object_store.put_chunks(output_chunks)
            output_object = self._object_store.verify(
                output_object.object_id,
                expected_length=output_object.byte_length,
            )
            if output_object.object_id != record.output_hash:
                raise DerivationIntegrityError("derivation output does not match record")
        elif record.state is DerivationState.FAILED:
            if output_chunks is not None or failure_code is None:
                raise DerivationIntegrityError(
                    "failed derivation requires one failure code and no output"
                )
            output_object = None
        else:
            raise DerivationIntegrityError("new derivation record is not terminal")
        for dependency in dependencies:
            if dependency.kind in {
                DerivationDependencyKind.OBJECT,
                DerivationDependencyKind.DERIVATION_OUTPUT,
            }:
                try:
                    self._object_store.verify(dependency.input_digest)
                except ObjectStoreError as error:
                    raise DerivationDependencyError(
                        "derivation object dependency failed verification"
                    ) from error
            self._check_cancel(cancel)
        publication = DerivationPublication(
            record=record,
            record_object=record_object,
            output_object=output_object,
            dependencies=dependencies,
            slot=slot,
            failure_code=failure_code,
            published_at=record.completed_at or record.created_at,
        )
        self._check_cancel(cancel)
        return self._catalog.publish_derivation(publication)

    def get_derivation(
        self,
        artifact_id: str,
        *,
        verify_objects: bool = True,
    ) -> DerivationNode | None:
        """Return body-free metadata and optionally rehash its immutable CAS objects."""
        node = self._catalog.get_derivation(artifact_id)
        if node is None or not verify_objects:
            return node
        try:
            self._object_store.verify(
                node.record_object.object_id,
                expected_length=node.record_object.byte_length,
            )
            if node.output_object is not None:
                self._object_store.verify(
                    node.output_object.object_id,
                    expected_length=node.output_object.byte_length,
                )
        except ObjectStoreError as error:
            raise DerivationIntegrityError("derivation object verification failed") from error
        return node

    def list_derivation_events(
        self,
        artifact_id: str,
    ) -> tuple[DerivationLifecycleEvent, ...]:
        """Return append-only body-free lifecycle evidence."""
        return self._catalog.list_derivation_events(artifact_id)

    @staticmethod
    def _check_cancel(cancel: CancellationCheck) -> None:
        if cancel():
            raise DerivationPublicationCancelled("derivation publication cancelled")


__all__ = ["DerivationPublicationCancelled", "DerivationService"]
