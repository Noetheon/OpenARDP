"""Pure records and invariants for local object and catalog persistence."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, SecretStr, StringConstraints, field_validator, model_validator

from openardp.domain.common import (
    CanonicalUuid,
    DocumentId,
    DomainModel,
    Sha256Id,
    UtcDatetime,
)

_STORAGE_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

ConnectorName = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]
OpaqueLocator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=8192)]
ReferenceRole = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$"),
]
MachineToken = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_.-]*$"),
]
MediaType = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=255)]
OwnerId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=255)]
DeduplicationKey = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]


def encode_storage_datetime(value: datetime) -> str:
    """Encode a UTC instant as fixed-width RFC 3339 for lexical SQL comparison."""
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None or offset != timedelta(0):
        raise ValueError("storage timestamp must be timezone-aware UTC")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def decode_storage_datetime(value: str) -> datetime:
    """Decode the one accepted fixed-width storage timestamp form."""
    if _STORAGE_TIMESTAMP.fullmatch(value) is None:
        raise ValueError("storage timestamp must use fixed-width UTC RFC 3339")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def uuid7_from_parts(*, timestamp_ms: int, random_bits: int) -> UUID:
    """Build an RFC 9562 UUIDv7 from one millisecond instant and 74 random bits."""
    if not 0 <= timestamp_ms < 1 << 48:
        raise ValueError("UUIDv7 timestamp must fit in 48 bits")
    if not 0 <= random_bits < 1 << 74:
        raise ValueError("UUIDv7 random value must fit in 74 bits")
    random_a = random_bits >> 62
    random_b = random_bits & ((1 << 62) - 1)
    value = (timestamp_ms << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return UUID(int=value)


def generate_uuid7(*, now: datetime, random_bits: int | None = None) -> UUID:
    """Generate a UUIDv7 with injectable UTC time and cryptographic randomness."""
    encoded_now = decode_storage_datetime(encode_storage_datetime(now))
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = encoded_now - epoch
    timestamp_ms = delta.days * 86_400_000 + delta.seconds * 1_000 + delta.microseconds // 1_000
    entropy = secrets.randbits(74) if random_bits is None else random_bits
    return uuid7_from_parts(timestamp_ms=timestamp_ms, random_bits=entropy)


def _ensure_unique_reference_slots(references: tuple[ObjectReference, ...]) -> None:
    slots = [(reference.role, reference.ordinal) for reference in references]
    if len(slots) != len(set(slots)):
        raise ValueError("object reference slots must be unique by role and ordinal")


class SourceKey(DomainModel):
    """Exact connector namespace and opaque locator for one logical document."""

    connector: ConnectorName
    locator: OpaqueLocator


class StoredObject(DomainModel):
    """Verified immutable content-addressed object metadata."""

    object_id: Sha256Id
    byte_length: int = Field(ge=0)


class StoreAnomalyCode(StrEnum):
    """Safe classification of a non-canonical managed-store entry."""

    MALFORMED_ENTRY = "MALFORMED_ENTRY"
    UNSAFE_ENTRY = "UNSAFE_ENTRY"
    CORRUPT_OBJECT = "CORRUPT_OBJECT"
    STAGING_RESIDUE = "STAGING_RESIDUE"


class StoreAnomaly(DomainModel):
    """Sanitized relative evidence about a managed-store inconsistency."""

    code: StoreAnomalyCode
    relative_location: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4096)]
    object_id: Sha256Id | None = None


class ObjectInventory(DomainModel):
    """Deterministic verified CAS objects and separately classified anomalies."""

    objects: tuple[StoredObject, ...]
    anomalies: tuple[StoreAnomaly, ...]

    @model_validator(mode="after")
    def _entries_are_canonical(self) -> ObjectInventory:
        identifiers = tuple(item.object_id for item in self.objects)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("inventory objects must be sorted and unique")
        anomaly_keys = tuple(
            (item.relative_location, item.code.value, item.object_id or "")
            for item in self.anomalies
        )
        if anomaly_keys != tuple(sorted(set(anomaly_keys))):
            raise ValueError("inventory anomalies must be sorted and unique")
        return self


class LogicalDocument(DomainModel):
    """Stable logical document registered for one exact source key."""

    document_id: DocumentId
    source_key: SourceKey
    created_at: UtcDatetime


class ObjectReference(DomainModel):
    """Typed ordered owner-to-object reachability edge."""

    role: ReferenceRole
    ordinal: int = Field(ge=0)
    object_id: Sha256Id
    byte_length: int = Field(ge=0)
    media_type: MediaType | None = None

    @field_validator("role")
    @classmethod
    def _source_role_is_reserved(cls, value: str) -> str:
        if value == "source":
            raise ValueError("source role is reserved for the source-version object")
        return value


class _VersionRecord(DomainModel):
    """Shared immutable shape for requested and persisted source-version facts."""

    document_id: DocumentId
    version_id: Sha256Id
    source: StoredObject
    media_type: MediaType
    source_modified_at: UtcDatetime | None = None
    references: tuple[ObjectReference, ...] = ()
    committed_at: UtcDatetime

    @model_validator(mode="after")
    def _source_and_references_are_consistent(self) -> _VersionRecord:
        if self.source.object_id != self.version_id:
            raise ValueError("source object identity must equal version_id")
        _ensure_unique_reference_slots(self.references)
        return self


class SourceVersionCommit(_VersionRecord):
    """Physically verified source-version data requested for atomic catalog commit."""


class DocumentVersion(_VersionRecord):
    """Complete source-version fact visible from the committed catalog."""


class JobState(StrEnum):
    """Small durable lifecycle for generic local work."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobSpec(DomainModel):
    """Immutable idempotent job request and its retained object roots."""

    job_id: CanonicalUuid
    kind: MachineToken
    deduplication_key: DeduplicationKey
    max_attempts: int = Field(ge=1, le=100)
    references: tuple[ObjectReference, ...] = ()
    available_at: UtcDatetime | None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _references_are_unambiguous(self) -> JobSpec:
        _ensure_unique_reference_slots(self.references)
        if self.available_at is not None and self.available_at < self.created_at:
            raise ValueError("available_at must not precede created_at")
        return self


class Job(DomainModel):
    """Current durable projection of one generic catalog job."""

    job_id: CanonicalUuid
    kind: MachineToken
    deduplication_key: DeduplicationKey
    state: JobState
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1, le=100)
    revision: int = Field(ge=0)
    available_at: UtcDatetime
    active_owner_id: OwnerId | None = None
    lease_expires_at: UtcDatetime | None = None
    cancellation_requested_at: UtcDatetime | None = None
    last_failure_code: MachineToken | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    terminal_at: UtcDatetime | None = None
    references: tuple[ObjectReference, ...] = ()

    @model_validator(mode="after")
    def _state_fields_are_consistent(self) -> Job:
        if self.attempt_count > self.max_attempts:
            raise ValueError("attempt_count must not exceed max_attempts")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.available_at < self.created_at:
            raise ValueError("available_at must not precede created_at")
        _ensure_unique_reference_slots(self.references)
        if self.state is JobState.RUNNING:
            if self.active_owner_id is None or self.lease_expires_at is None:
                raise ValueError("RUNNING job requires an owner and lease expiry")
            if self.terminal_at is not None:
                raise ValueError("RUNNING job must not have terminal_at")
            if self.cancellation_requested_at is not None and not (
                self.created_at <= self.cancellation_requested_at <= self.updated_at
            ):
                raise ValueError("cancellation request time is inconsistent")
        else:
            if self.active_owner_id is not None or self.lease_expires_at is not None:
                raise ValueError("non-RUNNING job must not retain an active lease")
            if self.cancellation_requested_at is not None:
                raise ValueError("cancellation request requires a RUNNING job")
        if self.state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
            if self.terminal_at is None:
                raise ValueError("terminal job requires terminal_at")
            if self.terminal_at < self.created_at:
                raise ValueError("terminal_at must not precede created_at")
        elif self.terminal_at is not None:
            raise ValueError("non-terminal job must not have terminal_at")
        return self


class JobLease(DomainModel):
    """Running job plus raw caller capability, masked from representation."""

    job: Job
    lease_token: SecretStr

    @model_validator(mode="after")
    def _lease_is_running_and_strong(self) -> JobLease:
        if self.job.state is not JobState.RUNNING:
            raise ValueError("job lease requires a RUNNING job")
        if len(self.lease_token.get_secret_value()) < 16:
            raise ValueError("lease token must contain at least 16 characters")
        return self


class JobEventType(StrEnum):
    """Sanitized append-only job transition classifications."""

    ENQUEUED = "ENQUEUED"
    CLAIMED = "CLAIMED"
    RENEWED = "RENEWED"
    COMPLETED = "COMPLETED"
    RETRY_QUEUED = "RETRY_QUEUED"
    FAILED = "FAILED"
    LEASE_RECOVERED = "LEASE_RECOVERED"
    LEASE_EXHAUSTED = "LEASE_EXHAUSTED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class JobEvent(DomainModel):
    """One append-only durable job transition without payload or token material."""

    job_id: CanonicalUuid
    sequence: int = Field(ge=1)
    event_type: JobEventType
    from_state: JobState | None
    to_state: JobState
    occurred_at: UtcDatetime
    attempt_count: int = Field(ge=0)
    owner_id: OwnerId | None = None
    failure_code: MachineToken | None = None

    @model_validator(mode="after")
    def _classification_matches_transition(self) -> JobEvent:
        transitions: dict[JobEventType, set[tuple[JobState | None, JobState]]] = {
            JobEventType.ENQUEUED: {(None, JobState.QUEUED)},
            JobEventType.CLAIMED: {(JobState.QUEUED, JobState.RUNNING)},
            JobEventType.RENEWED: {(JobState.RUNNING, JobState.RUNNING)},
            JobEventType.COMPLETED: {(JobState.RUNNING, JobState.SUCCEEDED)},
            JobEventType.RETRY_QUEUED: {(JobState.RUNNING, JobState.QUEUED)},
            JobEventType.FAILED: {(JobState.RUNNING, JobState.FAILED)},
            JobEventType.LEASE_RECOVERED: {(JobState.RUNNING, JobState.QUEUED)},
            JobEventType.LEASE_EXHAUSTED: {(JobState.RUNNING, JobState.FAILED)},
            JobEventType.CANCEL_REQUESTED: {(JobState.RUNNING, JobState.RUNNING)},
            JobEventType.CANCELLED: {
                (JobState.QUEUED, JobState.CANCELLED),
                (JobState.RUNNING, JobState.CANCELLED),
            },
        }
        if (self.from_state, self.to_state) not in transitions[self.event_type]:
            raise ValueError("job event classification does not match transition")
        queued_cancellation = (
            self.event_type is JobEventType.CANCELLED and self.from_state is JobState.QUEUED
        )
        if self.event_type is JobEventType.ENQUEUED:
            if self.attempt_count != 0 or self.owner_id is not None:
                raise ValueError("unclaimed job event must have attempt zero and no owner")
        elif queued_cancellation:
            if self.owner_id is not None:
                raise ValueError("queued cancellation event must not have an owner")
        elif self.attempt_count < 1 or self.owner_id is None:
            raise ValueError("job transition event requires an attempt and owner")
        failure_events = {
            JobEventType.RETRY_QUEUED,
            JobEventType.FAILED,
            JobEventType.LEASE_RECOVERED,
            JobEventType.LEASE_EXHAUSTED,
        }
        if (self.event_type in failure_events) != (self.failure_code is not None):
            raise ValueError("job event failure code does not match classification")
        return self


class RecoveryResult(DomainModel):
    """Deterministically sorted jobs changed by one expired-lease recovery pass."""

    requeued_job_ids: tuple[CanonicalUuid, ...]
    failed_job_ids: tuple[CanonicalUuid, ...]
    cancelled_job_ids: tuple[CanonicalUuid, ...] = ()
    recovered_at: UtcDatetime

    @model_validator(mode="after")
    def _job_ids_are_sorted_and_disjoint(self) -> RecoveryResult:
        requeued = tuple(str(item) for item in self.requeued_job_ids)
        failed = tuple(str(item) for item in self.failed_job_ids)
        cancelled = tuple(str(item) for item in self.cancelled_job_ids)
        if (
            requeued != tuple(sorted(set(requeued)))
            or failed != tuple(sorted(set(failed)))
            or cancelled != tuple(sorted(set(cancelled)))
            or set(requeued) & set(failed)
            or set(requeued) & set(cancelled)
            or set(failed) & set(cancelled)
        ):
            raise ValueError("recovery job identities must be sorted and disjoint")
        return self


class ReferenceSnapshot(DomainModel):
    """Unique catalog reachability roots observed in one read transaction."""

    object_ids: tuple[Sha256Id, ...]
    observed_at: UtcDatetime
    catalog_schema_version: int = Field(ge=1)

    @model_validator(mode="after")
    def _identities_are_sorted_and_unique(self) -> ReferenceSnapshot:
        if tuple(sorted(set(self.object_ids))) != self.object_ids:
            raise ValueError("reference snapshot identities must be sorted and unique")
        return self


class ReachabilityIssueCode(StrEnum):
    """Read-only reachability inconsistency classifications."""

    MISSING_REFERENCE = "MISSING_REFERENCE"
    CORRUPT_REFERENCE = "CORRUPT_REFERENCE"
    CORRUPT_STORE_OBJECT = "CORRUPT_STORE_OBJECT"
    MALFORMED_STORE_ENTRY = "MALFORMED_STORE_ENTRY"
    UNSAFE_STORE_ENTRY = "UNSAFE_STORE_ENTRY"
    STAGING_RESIDUE = "STAGING_RESIDUE"


class ReachabilityIssue(DomainModel):
    """Sanitized integrity or layout inconsistency from one reachability run."""

    code: ReachabilityIssueCode
    object_id: Sha256Id | None = None
    relative_location: str | None = None

    @model_validator(mode="after")
    def _evidence_matches_classification(self) -> ReachabilityIssue:
        if (
            self.code
            in {
                ReachabilityIssueCode.MISSING_REFERENCE,
                ReachabilityIssueCode.CORRUPT_REFERENCE,
                ReachabilityIssueCode.CORRUPT_STORE_OBJECT,
            }
            and self.object_id is None
        ):
            raise ValueError("object reachability issue requires object_id")
        if (
            self.code
            in {
                ReachabilityIssueCode.MALFORMED_STORE_ENTRY,
                ReachabilityIssueCode.UNSAFE_STORE_ENTRY,
                ReachabilityIssueCode.STAGING_RESIDUE,
            }
            and self.relative_location is None
        ):
            raise ValueError("layout reachability issue requires relative_location")
        return self


class ReachabilityReport(DomainModel):
    """Deterministic read-only classification at one catalog observation."""

    observed_at: UtcDatetime
    catalog_schema_version: int = Field(ge=1)
    reachable: tuple[StoredObject, ...]
    candidates: tuple[StoredObject, ...]
    inconsistencies: tuple[ReachabilityIssue, ...]

    @model_validator(mode="after")
    def _classifications_are_deterministic_and_disjoint(self) -> ReachabilityReport:
        reachable_ids = tuple(item.object_id for item in self.reachable)
        candidate_ids = tuple(item.object_id for item in self.candidates)
        if reachable_ids != tuple(sorted(set(reachable_ids))):
            raise ValueError("reachable objects must be sorted and unique")
        if candidate_ids != tuple(sorted(set(candidate_ids))):
            raise ValueError("candidate objects must be sorted and unique")
        if set(reachable_ids) & set(candidate_ids):
            raise ValueError("reachable and candidate objects must be disjoint")
        issue_keys = tuple(
            (issue.code.value, issue.object_id or "", issue.relative_location or "")
            for issue in self.inconsistencies
        )
        if issue_keys != tuple(sorted(set(issue_keys))):
            raise ValueError("reachability issues must be sorted and unique")
        return self
