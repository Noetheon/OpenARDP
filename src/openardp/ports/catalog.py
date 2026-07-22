"""Provider-neutral document, source-version and recoverable-job catalog port."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from openardp.domain.storage import (
    DocumentVersion,
    Job,
    JobEvent,
    JobLease,
    JobSpec,
    LogicalDocument,
    RecoveryResult,
    ReferenceSnapshot,
    SourceKey,
    SourceVersionCommit,
)
from openardp.ports.object_store import PersistenceError


class CatalogError(PersistenceError):
    """Base class for sanitized catalog failures."""


class CatalogIncompatible(CatalogError):
    """Raised for foreign, gapped or checksum-drifted migration histories."""


class CatalogTooNew(CatalogError):
    """Raised before mutation when a newer catalog revision is observed."""


class MigrationFailed(CatalogError):
    """Raised after a pending migration transaction rolls back."""


class DocumentConflict(CatalogError):
    """Raised when stable document identity is reused inconsistently."""


class VersionConflict(CatalogError):
    """Raised when an immutable source-version retry differs from stored facts."""


class InvalidObjectReference(CatalogError):
    """Raised when committed object metadata or references are inconsistent."""


class JobNotFound(CatalogError):
    """Raised when a requested durable job does not exist."""


class JobConflict(CatalogError):
    """Raised when a job idempotency key has different immutable inputs."""


class InvalidJobTransition(CatalogError):
    """Raised when a lifecycle transition is invalid from current state."""


class LeaseConflict(CatalogError):
    """Raised when owner, fencing token, revision or expiry proof is stale."""


@runtime_checkable
class Catalog(Protocol):
    """Atomic local catalog boundary for source facts and generic work."""

    def initialize(self, *, now: datetime) -> int:
        """Validate or transactionally upgrade the catalog and return its revision."""
        ...

    def schema_version(self) -> int:
        """Return the validated installed catalog revision."""
        ...

    def register_document(
        self,
        source_key: SourceKey,
        *,
        document_id: UUID,
        now: datetime,
    ) -> LogicalDocument:
        """Return the stable document for one exact source key."""
        ...

    def commit_source_version(self, commit: SourceVersionCommit) -> DocumentVersion:
        """Atomically make a complete immutable source-version fact visible."""
        ...

    def get_version(self, document_id: UUID, version_id: str) -> DocumentVersion | None:
        """Return one committed source version or no result."""
        ...

    def list_versions(self, document_id: UUID) -> tuple[DocumentVersion, ...]:
        """Return deterministic committed source versions for one document."""
        ...

    def create_job(self, spec: JobSpec) -> Job:
        """Create or idempotently retrieve one queued job."""
        ...

    def claim_job(
        self,
        *,
        kind: str | None,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease | None:
        """Claim one deterministic queued job with a caller fencing token."""
        ...

    def renew_job(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease:
        """Renew an unexpired lease through compare-and-set proof."""
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
        """Complete a running job idempotently with fencing proof."""
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
    ) -> Job:
        """Requeue or terminally fail a running job with sanitized evidence."""
        ...

    def get_job(self, job_id: UUID) -> Job | None:
        """Return one durable job projection or no result."""
        ...

    def list_job_events(self, job_id: UUID) -> tuple[JobEvent, ...]:
        """Return append-only transition evidence in sequence order."""
        ...

    def recover_expired_jobs(self, *, now: datetime) -> RecoveryResult:
        """Requeue or fail exactly the currently expired running jobs."""
        ...

    def reference_snapshot(self, *, observed_at: datetime) -> ReferenceSnapshot:
        """Return sorted version and job object roots from one read transaction."""
        ...
