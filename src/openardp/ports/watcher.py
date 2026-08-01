"""Provider-neutral contracts and sanitized failures for local watching."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from openardp.domain.storage import Job, JobLease, RecoveryResult
from openardp.domain.watcher import (
    AdmittedWatchRoot,
    WatchConfig,
    WatchEvent,
    WatchJobTarget,
    WatchObservation,
    WatchReconciliation,
    WatchRoot,
    WatchScan,
)


class WatcherError(RuntimeError):
    """Base class for body/path-free watcher failures."""


class WatchRootInvalid(WatcherError):
    """Raised when explicit root authority is malformed or unsafe."""


class WatchRootOverlap(WatcherError):
    """Raised when a watched root and managed workspace overlap."""


class WatchRootUnsupported(WatcherError):
    """Raised for recognizable unsupported filesystem authority."""


class WatchTargetChanged(WatcherError):
    """Raised when a scheduled metadata observation is no longer current."""


class WatchCancellationObserved(WatcherError):
    """Raised by a runner at a cooperative cancellation checkpoint."""


class WatchRetryableIngestion(WatcherError):
    """Raised for one stable failure eligible for bounded retry."""


class WatchPermanentIngestion(WatcherError):
    """Raised for one stable non-retryable ingestion failure."""


@runtime_checkable
class WatchScanner(Protocol):
    """Admit and completely scan explicit local directory authority."""

    def admit(
        self,
        root: Path,
        *,
        workspace: Path,
        config: WatchConfig,
    ) -> AdmittedWatchRoot:
        """Validate one explicit root without traversing its document entries."""
        ...

    def scan(
        self,
        root: AdmittedWatchRoot,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> WatchScan:
        """Return one complete bounded scan or an empty incomplete result."""
        ...

    def revalidate_target(
        self,
        root: AdmittedWatchRoot,
        target: WatchJobTarget,
    ) -> Path:
        """Reconstruct a target inside its root and require the exact fingerprint."""
        ...


@runtime_checkable
class WatchIngestionRunner(Protocol):
    """Reuse existing ingestion behind one cancellation-aware boundary."""

    def ingest(
        self,
        path: Path,
        *,
        profile: str,
        cancelled: Callable[[], bool],
    ) -> object:
        """Ingest one revalidated exact local path or raise a sanitized failure."""
        ...


@runtime_checkable
class WatchCatalog(Protocol):
    """Durable root, observation and exact target transaction boundary."""

    def register_watch_root(self, root: AdmittedWatchRoot, *, now: datetime) -> WatchRoot:
        """Register or exactly reuse one admitted root authority."""
        ...

    def get_watch_root(self, root_id: str) -> WatchRoot | None:
        """Return one durable root projection."""
        ...

    def reconcile_watch_scan(
        self,
        root_id: str,
        scan: WatchScan,
        *,
        now: datetime,
    ) -> WatchReconciliation:
        """Apply one complete scan atomically or record only rescan state."""
        ...

    def get_watch_target(self, job_id: UUID) -> WatchJobTarget | None:
        """Return one immutable watcher target."""
        ...

    def list_watch_events(self, root_id: str) -> tuple[WatchEvent, ...]:
        """Return append-only body/path-free watcher events."""
        ...

    def list_watch_observations(self, root_id: str) -> tuple[WatchObservation, ...]:
        """Return deterministic private watcher state for local orchestration."""
        ...


@runtime_checkable
class WatchRuntimeCatalog(WatchCatalog, Protocol):
    """Generic-job operations added to the durable watcher transaction boundary."""

    def recover_expired_jobs(self, *, now: datetime) -> RecoveryResult:
        """Recover every expired job deterministically."""
        ...

    def claim_watch_job(
        self,
        root_id: str,
        *,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease | None:
        """Claim one eligible job scoped to the admitted root."""
        ...

    def get_job(self, job_id: UUID) -> Job | None:
        """Return one current generic job projection."""
        ...

    def complete_job(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
    ) -> Job:
        """Complete a running job through fencing proof."""
        ...

    def fail_job(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        retryable: bool,
        failure_code: str,
        retry_at: datetime | None = None,
    ) -> Job:
        """Retry or fail a running job through fencing proof."""
        ...

    def acknowledge_job_cancellation(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
    ) -> Job:
        """Acknowledge one running cancellation request."""
        ...


__all__ = [
    "WatchCancellationObserved",
    "WatchCatalog",
    "WatchIngestionRunner",
    "WatchPermanentIngestion",
    "WatchRetryableIngestion",
    "WatchRootInvalid",
    "WatchRootOverlap",
    "WatchRootUnsupported",
    "WatchRuntimeCatalog",
    "WatchScanner",
    "WatchTargetChanged",
    "WatcherError",
]
