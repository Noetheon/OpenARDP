"""Provider-neutral document, source-version and recoverable-job catalog port."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from openardp.domain.ingestion import (
    DocumentHead,
    DocumentHeadUpdate,
    DocumentSummary,
    IngestionDisposition,
    IngestionEvent,
    ParserRecipe,
    ReadyRepresentationCommit,
    RepresentationAcquireResult,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationCommitResult,
    RepresentationLease,
    RepresentationScope,
)
from openardp.domain.search import (
    IndexCoverage,
    SearchFilters,
    SearchIndexEntry,
    SearchMatchPage,
)
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


class RepresentationConflict(CatalogError):
    """Raised when immutable representation facts are reused inconsistently."""


class RepresentationLeaseConflict(CatalogError):
    """Raised when representation owner, token, revision or expiry proof is stale."""


class RepresentationBusy(CatalogError):
    """Raised when another unexpired owner holds the representation claim."""


class RepresentationIncomplete(CatalogError):
    """Raised when a requested representation is not complete and READY."""


class RepresentationIntegrityError(CatalogError):
    """Raised when representation objects or projections fail verification."""


class DocumentNotFound(CatalogError):
    """Raised when a requested logical document does not exist."""


class RepresentationNotFound(CatalogError):
    """Raised when a requested representation scope does not exist."""


class BlockNotFound(CatalogError):
    """Raised when a requested normalized block does not exist."""


class AmbiguousBlock(CatalogError):
    """Raised when a block handle does not identify one current block."""


class SearchCapabilityUnavailable(CatalogError):
    """Raised when the runtime cannot provide the mandated FTS5 capability."""


class SearchIndexIncomplete(CatalogError):
    """Raised when in-scope READY representations lack complete index coverage."""


class SearchIndexDrifted(CatalogError):
    """Raised when index rows disagree with verified catalog or CAS evidence."""


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

    def get_document(self, document_id: UUID) -> LogicalDocument | None:
        """Return one registered logical document or no result."""
        ...

    def get_document_by_source(self, source_key: SourceKey) -> LogicalDocument | None:
        """Return the logical document for one exact source key or no result."""
        ...

    def list_documents(self) -> tuple[LogicalDocument, ...]:
        """Return every logical document in deterministic source-key order."""
        ...

    def acquire_representation(
        self,
        scope: RepresentationScope,
        recipe: ParserRecipe,
        *,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> RepresentationAcquireResult:
        """Claim, reuse or report busy processing for one representation scope."""
        ...

    def renew_representation(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        lease_until: datetime,
    ) -> RepresentationLease:
        """Renew one active fenced representation claim."""
        ...

    def fail_representation(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
        failure_code: str,
    ) -> RepresentationAggregate:
        """Record one sanitized failed representation attempt."""
        ...

    def commit_ready_representation(
        self,
        commit: ReadyRepresentationCommit,
        *,
        owner_id: str | None,
        lease_token: str | None,
        expected_revision: int | None,
        disposition: IngestionDisposition,
    ) -> RepresentationCommitResult:
        """Atomically make one complete immutable representation READY."""
        ...

    def load_representation(
        self,
        scope: RepresentationScope,
    ) -> RepresentationAggregate | None:
        """Return one header and complete block projection from one snapshot."""
        ...

    def record_ready_ingest(
        self,
        scope: RepresentationScope,
        *,
        source_observed_at: datetime,
        ingested_at: datetime,
        disposition: IngestionDisposition,
    ) -> DocumentHeadUpdate:
        """Append a verified READY reuse event and update the current head."""
        ...

    def get_document_head(self, document_id: UUID) -> DocumentHead | None:
        """Return the current successful observation for one document."""
        ...

    def list_document_summaries(self) -> tuple[DocumentSummary, ...]:
        """Return deterministic body-free current document summaries."""
        ...

    def resolve_ready_representation(
        self,
        document_id: UUID,
        *,
        version_id: str | None,
    ) -> RepresentationAggregate | None:
        """Resolve one current or historical READY aggregate deterministically."""
        ...

    def find_current_blocks(self, block_id: UUID) -> tuple[RepresentationBlock, ...]:
        """Return current-head projections matching one logical block handle."""
        ...

    def list_ingestion_events(self, document_id: UUID) -> tuple[IngestionEvent, ...]:
        """Return append-only successful ingest evidence in sequence order."""
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

    def search_block_entries(
        self,
        *,
        match: str,
        filters: SearchFilters,
    ) -> SearchMatchPage:
        """Execute coverage-checked FTS match and return one total-ordered page."""
        ...

    def index_coverage(
        self,
        *,
        scopes: tuple[RepresentationScope, ...] | None = None,
    ) -> tuple[IndexCoverage, ...]:
        """Return deterministic structural coverage for READY scopes."""
        ...

    def replace_scope_index(
        self,
        scope: RepresentationScope,
        entries: tuple[SearchIndexEntry, ...],
        texts: tuple[str, ...],
        *,
        now: datetime,
    ) -> int:
        """Atomically replace one READY scope's index rows with verified entries."""
        ...

    def list_ready_scopes(
        self,
        *,
        document_id: UUID | None = None,
    ) -> tuple[RepresentationScope, ...]:
        """Return READY representation scopes in deterministic identity order."""
        ...

    def list_scope_index_entries(
        self,
        scope: RepresentationScope,
    ) -> tuple[SearchIndexEntry, ...]:
        """Return stored index mapping rows for one READY scope in ordinal order."""
        ...
