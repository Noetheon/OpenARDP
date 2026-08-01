"""Pure bounded contracts for local watch reconciliation and stable jobs."""

from __future__ import annotations

from enum import StrEnum
from typing import cast

from pydantic import Field, JsonValue, model_validator

from openardp.domain.common import CanonicalUuid, DomainModel, Sha256Id, UtcDatetime
from openardp.domain.identity import canonical_sha256
from openardp.domain.storage import RecoveryResult

_WATCH_CONFIG_DOMAIN = "openardp:watch-config"
_WATCH_ROOT_DOMAIN = "openardp:watch-root"
_WATCH_LOCATOR_DOMAIN = "openardp:watch-relative-locator"
_WATCH_JOB_DOMAIN = "openardp:watch-ingest-job"


class WatchConfig(DomainModel):
    """Trusted bounded policy for one explicitly selected root."""

    recursive: bool = True
    max_depth: int = Field(default=32, ge=0, le=256)
    stability_ms: int = Field(default=5_000, ge=0, le=86_400_000)
    poll_ms: int = Field(default=2_000, ge=1, le=86_400_000)
    max_entries: int = Field(default=10_000, ge=1, le=1_000_000)
    max_active_jobs: int = Field(default=1_000, ge=1, le=100_000)
    max_jobs_per_cycle: int = Field(default=1, ge=0, le=1_000)
    max_attempts: int = Field(default=3, ge=1, le=100)
    retry_base_ms: int = Field(default=1_000, ge=1, le=86_400_000)
    retry_max_ms: int = Field(default=60_000, ge=1, le=604_800_000)
    text_profile: str = Field(default="default", min_length=1, max_length=255)
    rich_profile: str = Field(default="openardp-docling-offline-v1", min_length=1, max_length=255)

    @model_validator(mode="after")
    def _bounds_are_consistent(self) -> WatchConfig:
        if not self.recursive and self.max_depth != 0:
            raise ValueError("non-recursive watcher requires max_depth zero")
        if self.retry_max_ms < self.retry_base_ms:
            raise ValueError("retry maximum must not be below retry base")
        return self

    @property
    def config_hash(self) -> str:
        """Return the exact versioned semantic configuration identity."""
        return _domain_hash(
            _WATCH_CONFIG_DOMAIN,
            cast(dict[str, JsonValue], self.model_dump(mode="json")),
        )


class WatchFileFingerprint(DomainModel):
    """Metadata-only stability hint for one regular local descriptor."""

    device_id: str = Field(min_length=1, max_length=128)
    file_id: str = Field(min_length=1, max_length=128)
    byte_length: int = Field(ge=0, le=9_007_199_254_740_991)
    modified_ns: str = Field(min_length=1, max_length=21)
    mode: int = Field(ge=0, le=9_007_199_254_740_991)

    @model_validator(mode="after")
    def _modified_time_is_exact_decimal(self) -> WatchFileFingerprint:
        digits = self.modified_ns.removeprefix("-")
        if not digits or not digits.isascii() or not digits.isdecimal():
            raise ValueError("modified_ns must be an exact decimal integer string")
        return self


class AdmittedWatchRoot(DomainModel):
    """Exact local directory authority validated by a scanner adapter."""

    root_id: Sha256Id
    root_path: str = Field(min_length=1, max_length=8192)
    root_path_digest: Sha256Id
    device_id: str = Field(min_length=1, max_length=128)
    file_id: str = Field(min_length=1, max_length=128)
    config: WatchConfig

    @model_validator(mode="after")
    def _identities_match(self) -> AdmittedWatchRoot:
        path_digest = watch_locator_digest(self.root_path)
        if self.root_path_digest != path_digest:
            raise ValueError("root path digest is inconsistent")
        expected = watch_root_id(
            root_path_digest=path_digest,
            device_id=self.device_id,
            file_id=self.file_id,
            config_hash=self.config.config_hash,
        )
        if self.root_id != expected:
            raise ValueError("root identity is inconsistent")
        return self


class WatchScanReason(StrEnum):
    """Sanitized reason why a scan cannot establish current truth."""

    OVERFLOW = "scan_overflow"
    ROOT_CHANGED = "scan_root_changed"
    INCOMPLETE = "scan_incomplete"


class WatchScanEntry(DomainModel):
    """One supported regular-file observation from a complete scan."""

    relative_locator: str = Field(min_length=1, max_length=8192)
    locator_digest: Sha256Id
    fingerprint: WatchFileFingerprint
    media_type: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def _locator_is_safe_and_exact(self) -> WatchScanEntry:
        _validate_relative_locator(self.relative_locator)
        if self.locator_digest != watch_locator_digest(self.relative_locator):
            raise ValueError("relative locator digest is inconsistent")
        return self


class WatchScan(DomainModel):
    """Either one complete bounded root fact set or a body-free rescan reason."""

    root_id: Sha256Id
    started_at: UtcDatetime
    completed_at: UtcDatetime
    complete: bool
    reason: WatchScanReason | None = None
    entries: tuple[WatchScanEntry, ...] = ()

    @model_validator(mode="after")
    def _result_shape_is_unambiguous(self) -> WatchScan:
        if self.completed_at < self.started_at:
            raise ValueError("scan completion precedes start")
        if self.complete != (self.reason is None):
            raise ValueError("scan completeness and reason are inconsistent")
        if not self.complete and self.entries:
            raise ValueError("incomplete scan must not expose partial entries")
        order = tuple(entry.relative_locator for entry in self.entries)
        if order != tuple(sorted(set(order))):
            raise ValueError("scan entries must be unique and sorted")
        return self


class WatchObservationState(StrEnum):
    """Durable locator lifecycle across complete scans."""

    CANDIDATE = "CANDIDATE"
    STABLE = "STABLE"
    TOMBSTONED = "TOMBSTONED"


class WatchRoot(DomainModel):
    """Durable current projection of one admitted root registration."""

    authority: AdmittedWatchRoot
    generation: int = Field(ge=0)
    rescan_required: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def _times_are_monotonic(self) -> WatchRoot:
        if self.updated_at < self.created_at:
            raise ValueError("watch root update precedes creation")
        return self


class WatchObservation(DomainModel):
    """Durable path-scoped stability and tombstone fact."""

    root_id: Sha256Id
    relative_locator: str = Field(min_length=1, max_length=8192)
    locator_digest: Sha256Id
    state: WatchObservationState
    fingerprint: WatchFileFingerprint | None = None
    first_observed_at: UtcDatetime
    last_observed_at: UtcDatetime
    stable_since: UtcDatetime | None = None
    last_generation: int = Field(ge=0)
    last_scheduled_key: Sha256Id | None = None
    revision: int = Field(ge=1)
    row_fingerprint: Sha256Id

    @model_validator(mode="after")
    def _observation_is_consistent(self) -> WatchObservation:
        _validate_relative_locator(self.relative_locator)
        if self.locator_digest != watch_locator_digest(self.relative_locator):
            raise ValueError("observation locator digest is inconsistent")
        if self.last_observed_at < self.first_observed_at:
            raise ValueError("last observation precedes first observation")
        if (self.state is WatchObservationState.TOMBSTONED) != (self.fingerprint is None):
            raise ValueError("tombstone and fingerprint shape are inconsistent")
        if self.stable_since is not None and not (
            self.first_observed_at <= self.stable_since <= self.last_observed_at
        ):
            raise ValueError("stable_since is outside observation interval")
        expected = watch_observation_fingerprint(self, include_row_fingerprint=False)
        if self.row_fingerprint != expected:
            raise ValueError("watch observation row fingerprint is inconsistent")
        return self


class WatchJobTarget(DomainModel):
    """Immutable exact target bound to one generic watch-ingest job."""

    job_id: CanonicalUuid
    root_id: Sha256Id
    relative_locator: str = Field(min_length=1, max_length=8192)
    locator_digest: Sha256Id
    fingerprint: WatchFileFingerprint
    parser_profile: str = Field(min_length=1, max_length=255)
    deduplication_key: Sha256Id
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _target_identity_is_exact(self) -> WatchJobTarget:
        _validate_relative_locator(self.relative_locator)
        if self.locator_digest != watch_locator_digest(self.relative_locator):
            raise ValueError("target locator digest is inconsistent")
        expected = watch_job_key(
            root_id=self.root_id,
            locator_digest=self.locator_digest,
            fingerprint=self.fingerprint,
            parser_profile=self.parser_profile,
        )
        if self.deduplication_key != expected:
            raise ValueError("target deduplication key is inconsistent")
        return self


class WatchEventType(StrEnum):
    """Closed path/body-free watcher event classifications."""

    ROOT_REGISTERED = "ROOT_REGISTERED"
    SCAN_COMPLETED = "SCAN_COMPLETED"
    RESCAN_REQUIRED = "RESCAN_REQUIRED"
    OBSERVATION_CREATED = "OBSERVATION_CREATED"
    OBSERVATION_CHANGED = "OBSERVATION_CHANGED"
    OBSERVATION_STABLE = "OBSERVATION_STABLE"
    TARGET_SCHEDULED = "TARGET_SCHEDULED"
    BACKPRESSURE = "BACKPRESSURE"
    TOMBSTONED = "TOMBSTONED"
    REAPPEARED = "REAPPEARED"
    RENAME_HINT = "RENAME_HINT"
    JOB_SUCCEEDED = "JOB_SUCCEEDED"
    JOB_RETRY = "JOB_RETRY"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCELLED = "JOB_CANCELLED"


class WatchEvent(DomainModel):
    """One append-only watcher event containing only opaque identifiers and counts."""

    root_id: Sha256Id
    sequence: int = Field(ge=1)
    event_type: WatchEventType
    locator_digest: Sha256Id | None = None
    job_id: CanonicalUuid | None = None
    generation: int = Field(ge=0)
    occurred_at: UtcDatetime
    entry_count: int = Field(default=0, ge=0)
    scheduled_count: int = Field(default=0, ge=0)
    tombstone_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _shape_matches_classification(self) -> WatchEvent:
        observation_events = {
            WatchEventType.OBSERVATION_CREATED,
            WatchEventType.OBSERVATION_CHANGED,
            WatchEventType.OBSERVATION_STABLE,
            WatchEventType.REAPPEARED,
            WatchEventType.RENAME_HINT,
        }
        job_events = {
            WatchEventType.JOB_SUCCEEDED,
            WatchEventType.JOB_RETRY,
            WatchEventType.JOB_FAILED,
            WatchEventType.JOB_CANCELLED,
        }
        counts = (self.entry_count, self.scheduled_count, self.tombstone_count)
        if self.event_type in observation_events:
            if self.locator_digest is None or self.job_id is not None or any(counts):
                raise ValueError("watch observation event shape is inconsistent")
        elif self.event_type is WatchEventType.TOMBSTONED:
            if self.locator_digest is None or self.job_id is not None or counts != (0, 0, 1):
                raise ValueError("watch tombstone event shape is inconsistent")
        elif self.event_type is WatchEventType.TARGET_SCHEDULED:
            if self.locator_digest is None or self.job_id is None or counts != (0, 1, 0):
                raise ValueError("watch scheduling event shape is inconsistent")
        elif self.event_type in job_events:
            if self.locator_digest is None or self.job_id is None or any(counts):
                raise ValueError("watch job event shape is inconsistent")
        elif self.locator_digest is not None or self.job_id is not None:
            raise ValueError("watch root event must not contain target identifiers")
        elif self.event_type not in {
            WatchEventType.SCAN_COMPLETED,
            WatchEventType.BACKPRESSURE,
        } and any(counts):
            raise ValueError("watch control event must not contain counts")
        return self


class WatchReconciliation(DomainModel):
    """Body-free result of one atomic scan reconciliation."""

    root: WatchRoot
    complete: bool
    entry_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    stable_count: int = Field(ge=0)
    scheduled_job_ids: tuple[CanonicalUuid, ...]
    tombstone_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _job_ids_are_total_ordered(self) -> WatchReconciliation:
        values = tuple(str(value) for value in self.scheduled_job_ids)
        if values != tuple(sorted(set(values))):
            raise ValueError("scheduled job ids must be unique and sorted")
        if not self.complete and (
            self.entry_count
            or self.candidate_count
            or self.stable_count
            or self.scheduled_job_ids
            or self.tombstone_count
        ):
            raise ValueError("incomplete reconciliation cannot report partial mutations")
        return self


class WatchCycleResult(DomainModel):
    """Body-free result of recovery, reconciliation and bounded foreground work."""

    reconciliation: WatchReconciliation
    recovery: RecoveryResult
    succeeded_job_ids: tuple[CanonicalUuid, ...] = ()
    retried_job_ids: tuple[CanonicalUuid, ...] = ()
    failed_job_ids: tuple[CanonicalUuid, ...] = ()
    cancelled_job_ids: tuple[CanonicalUuid, ...] = ()

    @model_validator(mode="after")
    def _processed_sets_are_sorted_and_disjoint(self) -> WatchCycleResult:
        groups = (
            self.succeeded_job_ids,
            self.retried_job_ids,
            self.failed_job_ids,
            self.cancelled_job_ids,
        )
        seen: set[str] = set()
        for group in groups:
            values = tuple(str(value) for value in group)
            if values != tuple(sorted(set(values))) or seen.intersection(values):
                raise ValueError("processed job identities must be sorted and disjoint")
            seen.update(values)
        return self


def watch_locator_digest(locator: str) -> str:
    """Hash one exact root or relative locator without exposing it in events."""
    if not isinstance(locator, str) or not locator:
        raise ValueError("watch locator must be non-empty")
    return _domain_hash(_WATCH_LOCATOR_DOMAIN, {"locator": locator})


def watch_root_id(
    *,
    root_path_digest: str,
    device_id: str,
    file_id: str,
    config_hash: str,
) -> str:
    """Hash one exact admitted root authority and semantic configuration."""
    return _domain_hash(
        _WATCH_ROOT_DOMAIN,
        {
            "root_path_digest": root_path_digest,
            "device_id": device_id,
            "file_id": file_id,
            "config_hash": config_hash,
        },
    )


def watch_job_key(
    *,
    root_id: str,
    locator_digest: str,
    fingerprint: WatchFileFingerprint,
    parser_profile: str,
) -> str:
    """Hash the complete stable observation request independently of execution."""
    return _domain_hash(
        _WATCH_JOB_DOMAIN,
        {
            "root_id": root_id,
            "locator_digest": locator_digest,
            "fingerprint": cast(dict[str, JsonValue], fingerprint.model_dump(mode="json")),
            "parser_profile": parser_profile,
        },
    )


def watch_observation_fingerprint(
    observation: WatchObservation,
    *,
    include_row_fingerprint: bool = False,
) -> str:
    """Hash every mutable observation row fact except its fingerprint."""
    payload = cast(dict[str, JsonValue], observation.model_dump(mode="json"))
    if not include_row_fingerprint:
        payload.pop("row_fingerprint", None)
    return _domain_hash("openardp:watch-observation-row", payload)


def watch_retry_delay_ms(config: WatchConfig, *, attempt_count: int) -> int:
    """Return the exact capped exponential delay for a completed failed attempt."""
    if type(attempt_count) is not int or attempt_count < 1 or attempt_count > config.max_attempts:
        raise ValueError("attempt_count is outside configured retry bounds")
    exponent = min(attempt_count - 1, 62)
    return min(config.retry_base_ms * (1 << exponent), config.retry_max_ms)


def _validate_relative_locator(locator: str) -> None:
    if (
        locator.startswith(("/", "\\"))
        or "\\" in locator
        or any(ord(character) < 32 or ord(character) == 127 for character in locator)
        or any(segment in {"", ".", ".."} for segment in locator.split("/"))
    ):
        raise ValueError("relative watch locator is invalid")


def _domain_hash(domain: str, payload: dict[str, JsonValue]) -> str:
    return canonical_sha256(
        {
            "canonicalization": "RFC8785",
            "domain": domain,
            "identity_version": 1,
            "payload": payload,
        }
    )


__all__ = [
    "AdmittedWatchRoot",
    "WatchConfig",
    "WatchCycleResult",
    "WatchEvent",
    "WatchEventType",
    "WatchFileFingerprint",
    "WatchJobTarget",
    "WatchObservation",
    "WatchObservationState",
    "WatchReconciliation",
    "WatchRoot",
    "WatchScan",
    "WatchScanEntry",
    "WatchScanReason",
    "watch_job_key",
    "watch_locator_digest",
    "watch_observation_fingerprint",
    "watch_retry_delay_ms",
    "watch_root_id",
]
