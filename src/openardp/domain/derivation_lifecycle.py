"""Pure internal lifecycle contracts for exact derivation DAG nodes."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from openardp.domain.common import DomainModel, Sha256Id, UtcDatetime
from openardp.domain.derivation import DerivationRecord, DerivationState
from openardp.domain.identity import canonical_json_bytes, canonical_sha256, derivation_slot_id
from openardp.domain.storage import MachineToken, StoredObject

_SLOT_TOKEN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,126}[a-z0-9])?$")


class DerivationLifecycleState(StrEnum):
    """Current-workspace eligibility of one immutable derivation result."""

    CURRENT = "CURRENT"
    STALE = "STALE"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class DerivationDependencyKind(StrEnum):
    """Authority-free interpretation of one exact recipe input digest."""

    EVIDENCE_BINDING = "EVIDENCE_BINDING"
    OBJECT = "OBJECT"
    DERIVATION_OUTPUT = "DERIVATION_OUTPUT"


class DerivationDependency(DomainModel):
    """One ordered exact direct input and optional producer edge."""

    ordinal: int = Field(strict=True, ge=0, le=100_000)
    kind: DerivationDependencyKind
    input_digest: Sha256Id
    producer_artifact_id: Sha256Id | None = None

    @model_validator(mode="after")
    def _producer_shape_matches_kind(self) -> Self:
        has_producer = self.producer_artifact_id is not None
        if has_producer != (self.kind is DerivationDependencyKind.DERIVATION_OUTPUT):
            raise ValueError("producer_artifact_id is required only for derivation output inputs")
        return self


class DerivationSlotKey(DomainModel):
    """Deterministic local identity for one logical derivation output purpose."""

    slot_id: Sha256Id
    namespace: str
    subject_digest: Sha256Id
    purpose: str

    @model_validator(mode="after")
    def _tokens_and_identity_are_valid(self) -> Self:
        for name, value in (("namespace", self.namespace), ("purpose", self.purpose)):
            if _SLOT_TOKEN.fullmatch(value) is None:
                raise ValueError(f"{name} must be a bounded lowercase machine token")
        expected = derivation_slot_id(
            namespace=self.namespace,
            subject_digest=self.subject_digest,
            purpose=self.purpose,
        )
        if self.slot_id != expected:
            raise ValueError("slot_id does not match namespace, subject and purpose")
        return self


class DerivationPublication(DomainModel):
    """Complete verified material requested for one atomic node publication."""

    record: DerivationRecord
    record_object: StoredObject
    output_object: StoredObject | None = None
    dependencies: tuple[DerivationDependency, ...]
    slot: DerivationSlotKey
    failure_code: MachineToken | None = None
    published_at: UtcDatetime

    @model_validator(mode="after")
    def _record_objects_and_dependencies_are_exact(self) -> Self:
        record_payload = canonical_json_bytes(self.record.model_dump(mode="json"))
        expected_record = StoredObject(
            object_id="sha256:" + hashlib.sha256(record_payload).hexdigest(),
            byte_length=len(record_payload),
        )
        if self.record_object != expected_record:
            raise ValueError("record_object does not match canonical derivation record")
        ordinals = tuple(item.ordinal for item in self.dependencies)
        if ordinals != tuple(range(len(self.dependencies))):
            raise ValueError("dependency ordinals must be contiguous from zero")
        digests = tuple(item.input_digest for item in self.dependencies)
        if digests != self.record.input_hashes:
            raise ValueError("dependency digests must exactly match the ordered recipe inputs")
        if self.published_at < self.record.created_at:
            raise ValueError("published_at cannot precede record creation")
        if self.record.completed_at is not None and self.published_at < self.record.completed_at:
            raise ValueError("published_at cannot precede record completion")
        if self.record.state is DerivationState.READY:
            if (
                self.output_object is None
                or self.record.output_hash != self.output_object.object_id
                or self.failure_code is not None
            ):
                raise ValueError("READY publication requires its exact output and no failure")
        elif self.record.state is DerivationState.FAILED:
            if self.output_object is not None or self.failure_code is None:
                raise ValueError("FAILED publication requires a failure code and no output")
        else:
            raise ValueError("new publication accepts only READY or FAILED generation records")
        return self


class DerivationNode(DomainModel):
    """Body-free workspace lifecycle projection for one immutable generation record."""

    artifact_id: Sha256Id
    slot: DerivationSlotKey
    state: DerivationLifecycleState
    record: DerivationRecord
    record_object: StoredObject
    output_object: StoredObject | None = None
    dependencies: tuple[DerivationDependency, ...]
    revision: int = Field(strict=True, ge=1)
    created_at: UtcDatetime
    updated_at: UtcDatetime
    failure_code: MachineToken | None = None
    row_fingerprint: Sha256Id

    @model_validator(mode="after")
    def _row_and_lifecycle_are_consistent(self) -> Self:
        if self.artifact_id != self.record.artifact_id:
            raise ValueError("node artifact_id does not match generation record")
        if self.updated_at < self.created_at:
            raise ValueError("node updated_at cannot precede created_at")
        publication = DerivationPublication(
            record=self.record,
            record_object=self.record_object,
            output_object=self.output_object,
            dependencies=self.dependencies,
            slot=self.slot,
            failure_code=self.failure_code,
            published_at=self.created_at,
        )
        if self.state is DerivationLifecycleState.FAILED:
            if publication.record.state is not DerivationState.FAILED:
                raise ValueError("FAILED node requires a failed generation record")
        elif publication.record.state is not DerivationState.READY:
            raise ValueError("successful lifecycle state requires a ready generation record")
        expected = derivation_node_fingerprint(self)
        if self.row_fingerprint != expected:
            raise ValueError("row_fingerprint does not match node facts")
        return self


class DerivationEventReason(StrEnum):
    """Stable body-free reason for one actual lifecycle transition."""

    PUBLISHED = "published"
    GENERATION_FAILED = "generation_failed"
    DEPENDENCY_INACTIVE = "dependency_inactive"
    REACTIVATED = "reactivated"
    SLOT_REPLACED = "slot_replaced"


class DerivationLifecycleEvent(DomainModel):
    """Append-only body-free evidence for one node state transition."""

    artifact_id: Sha256Id
    sequence: int = Field(strict=True, ge=1)
    from_state: DerivationLifecycleState | None = None
    to_state: DerivationLifecycleState
    reason: DerivationEventReason
    run_id: Sha256Id | None = None
    occurred_at: UtcDatetime

    @model_validator(mode="after")
    def _transition_reason_is_consistent(self) -> Self:
        if self.from_state == self.to_state:
            raise ValueError("lifecycle event must change state")
        if self.from_state is None:
            expected = (
                DerivationEventReason.GENERATION_FAILED
                if self.to_state is DerivationLifecycleState.FAILED
                else DerivationEventReason.PUBLISHED
            )
            if self.reason is not expected or self.run_id is not None:
                raise ValueError("initial lifecycle event reason is inconsistent")
        elif self.reason in {
            DerivationEventReason.DEPENDENCY_INACTIVE,
            DerivationEventReason.REACTIVATED,
        }:
            if self.run_id is None:
                raise ValueError("reconciliation lifecycle event requires run_id")
        elif self.run_id is not None:
            raise ValueError("non-reconciliation lifecycle event cannot carry run_id")
        return self


class DerivationPublicationDisposition(StrEnum):
    """Observable result of an idempotent derivation publication."""

    COMMITTED = "COMMITTED"
    CONVERGED = "CONVERGED"


class DerivationPublicationResult(DomainModel):
    """One complete node plus its idempotent publication classification."""

    disposition: DerivationPublicationDisposition
    node: DerivationNode
    superseded_artifact_ids: tuple[Sha256Id, ...] = ()

    @model_validator(mode="after")
    def _superseded_ids_are_deterministic(self) -> Self:
        if self.superseded_artifact_ids != tuple(sorted(set(self.superseded_artifact_ids))):
            raise ValueError("superseded artifact identifiers must be sorted and unique")
        if self.node.artifact_id in self.superseded_artifact_ids:
            raise ValueError("published artifact cannot supersede itself")
        if (
            self.disposition is DerivationPublicationDisposition.CONVERGED
            and self.superseded_artifact_ids
        ):
            raise ValueError("converged publication cannot repeat supersession")
        return self


def derivation_node_fingerprint(node: DerivationNode) -> str:
    """Hash immutable and mutable row facts except the fingerprint itself."""
    payload = node.model_dump(mode="json", exclude={"row_fingerprint"})
    return canonical_sha256(payload)


__all__ = [
    "DerivationDependency",
    "DerivationDependencyKind",
    "DerivationEventReason",
    "DerivationLifecycleEvent",
    "DerivationLifecycleState",
    "DerivationNode",
    "DerivationPublication",
    "DerivationPublicationDisposition",
    "DerivationPublicationResult",
    "DerivationSlotKey",
    "derivation_node_fingerprint",
]
