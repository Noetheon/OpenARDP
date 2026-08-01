"""Transactional local SQLite catalog for source facts and recoverable work."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid5

from pydantic import SecretStr, ValidationError

from openardp.adapters.sqlite_migrations import MIGRATIONS, Migration
from openardp.domain.block import BlockKind
from openardp.domain.common import ComponentDescriptor, GenerationProvenance, TrustZone
from openardp.domain.context import BudgetUnit, VersionScope
from openardp.domain.context_compilation import (
    ContextCompilationCommit,
    ContextCompilationRecord,
    ContextCompilationScope,
)
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
from openardp.domain.ingestion import (
    DocumentHead,
    DocumentHeadUpdate,
    DocumentRepresentation,
    DocumentSummary,
    IngestionDisposition,
    IngestionEvent,
    ParserRecipe,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationAcquireResult,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationCommitResult,
    RepresentationLease,
    RepresentationScope,
    RepresentationState,
)
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
from openardp.domain.rich_ingestion import (
    ReadyRichRepresentationCommit,
    RichAttemptAppendResult,
    RichAttemptCommit,
    RichAttemptOutcome,
    RichEvidenceBundle,
    RichParseAttempt,
    RichRepresentationArtifacts,
    RichRepresentationCommitResult,
)
from openardp.domain.search import (
    IndexCoverage,
    SearchFilters,
    SearchIndexEntry,
    SearchMatchPage,
    SearchMatchRow,
    block_text_for_index,
    indexed_text_hash,
)
from openardp.domain.storage import (
    DocumentVersion,
    Job,
    JobEvent,
    JobEventType,
    JobLease,
    JobSpec,
    JobState,
    LogicalDocument,
    ObjectReference,
    RecoveryResult,
    ReferenceSnapshot,
    SourceKey,
    SourceVersionCommit,
    StoredObject,
    decode_storage_datetime,
    encode_storage_datetime,
)
from openardp.domain.visual import (
    VisualEvidenceCommit,
    VisualEvidenceDescriptor,
    VisualEvidenceRecord,
    VisualGranularity,
    VisualPageRaster,
    visual_record_fingerprint,
)
from openardp.domain.watcher import (
    AdmittedWatchRoot,
    WatchConfig,
    WatchEvent,
    WatchEventType,
    WatchFileFingerprint,
    WatchJobTarget,
    WatchObservation,
    WatchObservationState,
    WatchReconciliation,
    WatchRoot,
    WatchScan,
    WatchScanEntry,
    watch_job_key,
    watch_observation_fingerprint,
)
from openardp.ports.catalog import (
    CatalogError,
    CatalogIncompatible,
    CatalogTooNew,
    ContextCompilationConflict,
    DerivationConflict,
    DerivationCycleError,
    DerivationDependencyError,
    DerivationIntegrityError,
    DocumentConflict,
    DocumentNotFound,
    InvalidJobTransition,
    InvalidObjectReference,
    JobConflict,
    JobNotFound,
    LeaseConflict,
    MigrationFailed,
    ReconciliationConflict,
    ReconciliationIntegrityError,
    ReconciliationScopeError,
    RepresentationConflict,
    RepresentationIncomplete,
    RepresentationIntegrityError,
    RepresentationLeaseConflict,
    RepresentationNotFound,
    SearchCapabilityUnavailable,
    SearchIndexIncomplete,
    VersionConflict,
    VisualCatalogConflict,
    VisualCatalogIntegrityError,
)

_WATCH_JOB_NAMESPACE = UUID("a2b64ef3-5813-57bb-a297-903183b34d6d")

_OWNER = re.compile(r"^.{1,255}$", re.DOTALL)
_MACHINE_TOKEN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_PDF_RENDER_PROFILE = re.compile(r"pdf-rgb-v1\+wheel-sha256:[0-9a-f]{64}")
_PNG_ENCODER_PROFILE = re.compile(r"png-rgb-v1\+wheel-sha256:[0-9a-f]{64}")
_MIN_LEASE_TOKEN_LENGTH = 16
_SCHEMA_TABLES = {
    1: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
        }
    ),
    2: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
        }
    ),
    3: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
        }
    ),
    4: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
            "block_search_entries",
            "block_search_index",
            "block_search_index_config",
            "block_search_index_data",
            "block_search_index_docsize",
            "block_search_index_idx",
        }
    ),
    5: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
            "block_search_entries",
            "block_search_index",
            "block_search_index_config",
            "block_search_index_data",
            "block_search_index_docsize",
            "block_search_index_idx",
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
        }
    ),
    6: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
            "block_search_entries",
            "block_search_index",
            "block_search_index_config",
            "block_search_index_data",
            "block_search_index_docsize",
            "block_search_index_idx",
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
            "context_compilations",
            "context_compilation_scopes",
        }
    ),
    7: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
            "block_search_entries",
            "block_search_index",
            "block_search_index_config",
            "block_search_index_data",
            "block_search_index_docsize",
            "block_search_index_idx",
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
            "context_compilations",
            "context_compilation_scopes",
            "reconciliation_runs",
            "block_lineages",
            "block_lineage_members",
            "reconciliation_relations",
            "derivation_slots",
            "derivation_nodes",
            "derivation_dependencies",
            "derivation_events",
        }
    ),
    8: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
            "block_search_entries",
            "block_search_index",
            "block_search_index_config",
            "block_search_index_data",
            "block_search_index_docsize",
            "block_search_index_idx",
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
            "context_compilations",
            "context_compilation_scopes",
            "reconciliation_runs",
            "block_lineages",
            "block_lineage_members",
            "reconciliation_relations",
            "derivation_slots",
            "derivation_nodes",
            "derivation_dependencies",
            "derivation_events",
            "visual_page_rasters",
            "visual_evidence",
        }
    ),
}
_SCHEMA_TABLES[9] = _SCHEMA_TABLES[8] | frozenset(
    {"watch_roots", "watch_observations", "watch_job_targets", "watch_events"}
)


class SQLiteCatalog:
    """SQLite implementation with explicit transactions and checked migrations."""

    def __init__(
        self,
        path: Path,
        *,
        migrations: tuple[Migration, ...] = MIGRATIONS,
        busy_timeout_ms: int = 5000,
    ) -> None:
        """Configure one local catalog file without opening or mutating it."""
        if not migrations:
            raise ValueError("at least one catalog migration is required")
        expected = tuple(range(1, len(migrations) + 1))
        if tuple(migration.version for migration in migrations) != expected:
            raise ValueError("catalog migrations must be contiguous from revision 1")
        if type(busy_timeout_ms) is not int or busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms must be a non-negative integer")
        self._path = path.expanduser().absolute()
        self._migrations = migrations
        self._migration_by_version = {migration.version: migration for migration in migrations}
        self._busy_timeout_ms = busy_timeout_ms

    @property
    def path(self) -> Path:
        """Return the configured catalog path."""
        return self._path

    def initialize(self, *, now: datetime) -> int:
        """Validate or atomically apply every pending catalog migration."""
        applied_at = encode_storage_datetime(now)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        transaction_started = False
        try:
            connection.execute("BEGIN")
            transaction_started = True
            current = self._validate_history(connection)
            connection.execute("COMMIT")
            transaction_started = False
            self._configure_persistent_profile(connection)
            self._require_fts5_capability(connection)
            connection.execute("BEGIN EXCLUSIVE")
            transaction_started = True
            current = self._validate_history(connection)
            for migration in self._migrations[current:]:
                for statement in migration.statements:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (migration.version, migration.name, migration.checksum, applied_at),
                )
            foreign_key_issues = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_issues:
                raise MigrationFailed("catalog foreign-key validation failed")
            connection.execute("COMMIT")
            transaction_started = False
            return self._validate_history(connection)
        except (CatalogIncompatible, CatalogTooNew, MigrationFailed):
            if transaction_started:
                connection.execute("ROLLBACK")
            raise
        except sqlite3.Error as error:
            if transaction_started:
                connection.execute("ROLLBACK")
            raise MigrationFailed("catalog migration transaction failed") from error
        except Exception:
            if transaction_started:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def schema_version(self) -> int:
        """Return the compatible installed catalog revision without mutation."""
        if not self._path.exists():
            raise CatalogIncompatible("catalog is not initialized")
        connection = self._connect()
        try:
            return self._validate_history(connection)
        finally:
            connection.close()

    def diagnostics(self) -> dict[str, str | int]:
        """Return bounded catalog/runtime facts without record content."""
        with self._read_connection() as connection:
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            return {
                "schema_version": self._schema_version_from_connection(connection),
                "journal_mode": str(connection.execute("PRAGMA journal_mode").fetchone()[0]),
                "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
                "foreign_keys": int(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
                "trusted_schema": int(connection.execute("PRAGMA trusted_schema").fetchone()[0]),
                "quick_check": quick_check,
                "sqlite_version": sqlite3.sqlite_version,
            }

    def register_document(
        self,
        source_key: SourceKey,
        *,
        document_id: UUID,
        now: datetime,
    ) -> LogicalDocument:
        """Register or return the stable document for one exact source key."""
        created_at = encode_storage_datetime(now)
        with self._write_connection() as connection:
            existing = self._load_document_by_source(connection, source_key)
            if existing is not None:
                return existing
            collision = self._load_document_by_id(connection, document_id)
            if collision is not None:
                raise DocumentConflict("document identity is already registered")
            connection.execute(
                "INSERT INTO documents(document_id, connector, source_locator, created_at) "
                "VALUES (?, ?, ?, ?)",
                (str(document_id), source_key.connector, source_key.locator, created_at),
            )
            registered = self._load_document_by_id(connection, document_id)
            if registered is None:
                raise CatalogError("document registration did not become visible")
            return registered

    def commit_source_version(self, commit: SourceVersionCommit) -> DocumentVersion:
        """Atomically register object metadata and one complete source-version fact."""
        expected = self._document_version_from_commit(commit)
        registered_at = encode_storage_datetime(commit.committed_at)
        with self._write_connection() as connection:
            if self._load_document_by_id(connection, commit.document_id) is None:
                raise DocumentConflict("document identity is not registered")
            existing = self._load_version(connection, commit.document_id, commit.version_id)
            if existing is not None:
                if self._versions_equivalent(existing, expected):
                    return existing
                raise VersionConflict("source version already exists with different immutable data")
            self._register_object(connection, commit.source, registered_at=registered_at)
            for reference in commit.references:
                self._register_object(connection, reference, registered_at=registered_at)
            connection.execute(
                "INSERT INTO document_versions("
                "document_id, version_id, source_object_id, media_type, source_modified_at, "
                "committed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(commit.document_id),
                    commit.version_id,
                    commit.source.object_id,
                    commit.media_type,
                    (
                        encode_storage_datetime(commit.source_modified_at)
                        if commit.source_modified_at is not None
                        else None
                    ),
                    registered_at,
                ),
            )
            self._fault_point("after_version_header")
            for reference in commit.references:
                connection.execute(
                    "INSERT INTO version_object_references("
                    "document_id, version_id, role, ordinal, object_id, media_type) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(commit.document_id),
                        commit.version_id,
                        reference.role,
                        reference.ordinal,
                        reference.object_id,
                        reference.media_type,
                    ),
                )
                self._fault_point("after_version_reference")
            stored = self._load_version(connection, commit.document_id, commit.version_id)
            if stored is None:
                raise CatalogError("source version was not readable before commit")
            self._fault_point("before_commit")
            return stored

    def get_version(self, document_id: UUID, version_id: str) -> DocumentVersion | None:
        """Return one committed source-version fact or no result."""
        with self._read_connection() as connection:
            return self._load_version(connection, document_id, version_id)

    def list_versions(self, document_id: UUID) -> tuple[DocumentVersion, ...]:
        """Return committed source-version facts in deterministic commit order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT version_id FROM document_versions WHERE document_id = ? "
                "ORDER BY committed_at, version_id",
                (str(document_id),),
            ).fetchall()
            return tuple(
                version
                for row in rows
                if (version := self._load_version(connection, document_id, str(row[0]))) is not None
            )

    def get_document(self, document_id: UUID) -> LogicalDocument | None:
        """Return one registered logical document or no result."""
        with self._read_connection() as connection:
            return self._load_document_by_id(connection, document_id)

    def get_document_by_source(self, source_key: SourceKey) -> LogicalDocument | None:
        """Return the document for one exact source key or no result."""
        with self._read_connection() as connection:
            return self._load_document_by_source(connection, source_key)

    def list_documents(self) -> tuple[LogicalDocument, ...]:
        """Return logical documents in exact source-key order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY connector, source_locator, document_id"
            ).fetchall()
            return tuple(self._document_from_row(row) for row in rows)

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
        """Claim, reuse or report busy work for one immutable representation scope."""
        self._validate_representation_identity(scope, recipe)
        self._validate_representation_owner(owner_id)
        token_hash = self._representation_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise RepresentationLeaseConflict("representation lease must extend beyond now")
        with self._write_connection() as connection:
            if self._load_version(connection, scope.document_id, scope.version_id) is None:
                raise RepresentationNotFound("representation source version does not exist")
            row = self._load_representation_row(connection, scope)
            if row is None:
                connection.execute(
                    "INSERT INTO document_representations("
                    "document_id, version_id, representation_id, parser_name, parser_version, "
                    "parser_profile, parser_config_hash, normalization_schema_version, state, "
                    "attempt_count, revision, active_owner_id, active_lease_token_hash, "
                    "lease_expires_at, last_transition_token_hash, last_failure_code, "
                    "manifest_object_id, native_object_id, block_count, warning_codes_json, "
                    "created_at, updated_at, ready_at) VALUES ("
                    "?, ?, ?, ?, ?, ?, ?, ?, 'STAGING', 1, 1, ?, ?, ?, NULL, NULL, NULL, "
                    "NULL, 0, '[]', ?, ?, NULL)",
                    (
                        str(scope.document_id),
                        scope.version_id,
                        scope.representation_id,
                        recipe.name,
                        recipe.version,
                        recipe.profile,
                        recipe.config_hash,
                        recipe.normalization_schema_version,
                        owner_id,
                        token_hash,
                        lease_text,
                        now_text,
                        now_text,
                    ),
                )
                representation = self._required_representation(connection, scope).representation
                lease = RepresentationLease(
                    representation=representation,
                    lease_token=SecretStr(lease_token),
                )
                return RepresentationAcquireResult(
                    disposition=RepresentationAcquireDisposition.CLAIMED,
                    representation=representation,
                    lease=lease,
                )

            self._assert_row_recipe(row, recipe)
            representation = self._representation_from_row(row)
            if representation.state is RepresentationState.READY:
                return RepresentationAcquireResult(
                    disposition=RepresentationAcquireDisposition.READY,
                    representation=representation,
                )
            if (
                representation.state is RepresentationState.STAGING
                and str(row["lease_expires_at"]) > now_text
            ):
                if (
                    row["active_owner_id"] == owner_id
                    and row["active_lease_token_hash"] == token_hash
                ):
                    lease = RepresentationLease(
                        representation=representation,
                        lease_token=SecretStr(lease_token),
                    )
                    return RepresentationAcquireResult(
                        disposition=RepresentationAcquireDisposition.CLAIMED,
                        representation=representation,
                        lease=lease,
                    )
                return RepresentationAcquireResult(
                    disposition=RepresentationAcquireDisposition.BUSY,
                    representation=representation,
                )
            if now_text < str(row["updated_at"]):
                raise RepresentationLeaseConflict("representation transition time regressed")
            connection.execute(
                "UPDATE document_representations SET state = 'STAGING', "
                "attempt_count = attempt_count + 1, revision = revision + 1, "
                "active_owner_id = ?, active_lease_token_hash = ?, lease_expires_at = ?, "
                "last_transition_token_hash = NULL, last_failure_code = NULL, "
                "manifest_object_id = NULL, native_object_id = NULL, block_count = 0, "
                "warning_codes_json = '[]', updated_at = ?, ready_at = NULL "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (
                    owner_id,
                    token_hash,
                    lease_text,
                    now_text,
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                ),
            )
            taken = self._required_representation(connection, scope).representation
            lease = RepresentationLease(
                representation=taken,
                lease_token=SecretStr(lease_token),
            )
            return RepresentationAcquireResult(
                disposition=RepresentationAcquireDisposition.CLAIMED,
                representation=taken,
                lease=lease,
            )

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
        """Renew one active representation claim through compare-and-set fencing."""
        self._validate_representation_owner(owner_id)
        token_hash = self._representation_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise RepresentationLeaseConflict("representation lease must extend beyond now")
        with self._write_connection() as connection:
            row = self._required_representation_row(connection, scope)
            self._assert_representation_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            if now_text < str(row["updated_at"]):
                raise RepresentationLeaseConflict("representation transition time regressed")
            connection.execute(
                "UPDATE document_representations SET revision = revision + 1, "
                "lease_expires_at = ?, updated_at = ? WHERE document_id = ? AND "
                "version_id = ? AND representation_id = ? AND revision = ? AND state = 'STAGING'",
                (
                    lease_text,
                    now_text,
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                    expected_revision,
                ),
            )
            renewed = self._required_representation(connection, scope).representation
            return RepresentationLease(
                representation=renewed,
                lease_token=SecretStr(lease_token),
            )

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
        """Persist one body-free FAILED outcome through fencing proof."""
        self._validate_representation_owner(owner_id)
        self._validate_failure_code(failure_code)
        token_hash = self._representation_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        with self._write_connection() as connection:
            row = self._required_representation_row(connection, scope)
            if row["state"] == RepresentationState.FAILED.value:
                if (
                    row["last_transition_token_hash"] == token_hash
                    and row["last_failure_code"] == failure_code
                ):
                    return self._required_representation(connection, scope)
                raise RepresentationLeaseConflict("failed representation token does not match")
            self._assert_representation_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            if now_text < str(row["updated_at"]):
                raise RepresentationLeaseConflict("representation transition time regressed")
            connection.execute(
                "UPDATE document_representations SET state = 'FAILED', revision = revision + 1, "
                "active_owner_id = NULL, active_lease_token_hash = NULL, lease_expires_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = ?, updated_at = ? "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                "AND revision = ? AND state = 'STAGING'",
                (
                    token_hash,
                    failure_code,
                    now_text,
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                    expected_revision,
                ),
            )
            return self._required_representation(connection, scope)

    def commit_ready_representation(
        self,
        commit: ReadyRepresentationCommit,
        *,
        owner_id: str | None,
        lease_token: str | None,
        expected_revision: int | None,
        disposition: IngestionDisposition,
        _connection: sqlite3.Connection | None = None,
    ) -> RepresentationCommitResult:
        """Atomically publish one complete READY aggregate, head and ingest event."""
        if disposition is IngestionDisposition.CACHE_HIT:
            raise RepresentationConflict("ready commit cannot be a cache hit")
        now_text = encode_storage_datetime(commit.ready_at)
        observed_text = encode_storage_datetime(commit.source_observed_at)
        with self._optional_write_connection(_connection) as connection:
            row = self._required_representation_row(connection, commit.scope)
            self._assert_row_recipe(row, commit.recipe)
            existing = self._required_representation(connection, commit.scope)
            token_hash = (
                self._representation_token_hash(lease_token) if lease_token is not None else None
            )
            if existing.representation.state is RepresentationState.READY:
                if not self._ready_aggregate_matches(existing, commit):
                    raise RepresentationConflict("ready representation differs from candidate")
                if owner_id is not None or expected_revision is not None:
                    if token_hash is None or row["last_transition_token_hash"] != token_hash:
                        raise RepresentationLeaseConflict(
                            "ready representation fencing token does not match"
                        )
                    event = self._last_scope_event(connection, commit.scope)
                    head = self._required_document_head(connection, commit.scope.document_id)
                    return RepresentationCommitResult(
                        aggregate=existing,
                        head=head,
                        event=event,
                    )
                if disposition is not IngestionDisposition.FORCED_REPARSE:
                    raise RepresentationConflict(
                        "forced identical output must use FORCED_REPARSE disposition"
                    )
                head, event = self._advance_head_and_event(
                    connection,
                    commit.scope,
                    source_observed_at=observed_text,
                    ingested_at=now_text,
                    disposition=disposition,
                    parser_invoked=True,
                )
                return RepresentationCommitResult(
                    aggregate=existing,
                    head=head,
                    event=event,
                )

            if owner_id is None or token_hash is None or expected_revision is None:
                raise RepresentationLeaseConflict("ready commit requires representation lease")
            self._validate_representation_owner(owner_id)
            self._assert_representation_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            version = self._load_version(
                connection,
                commit.scope.document_id,
                commit.scope.version_id,
            )
            if version is None or version.source != commit.native_object:
                raise RepresentationIntegrityError(
                    "native representation object does not match source version"
                )
            for value in (commit.manifest_object, commit.native_object):
                self._register_object(connection, value, registered_at=now_text)
            for item in commit.blocks:
                self._register_object(connection, item.object, registered_at=now_text)
            self._fault_point("after_representation_objects")
            for item in commit.blocks:
                connection.execute(
                    "INSERT INTO representation_blocks("
                    "document_id, version_id, representation_id, ordinal, block_id, object_id, "
                    "parent_id, kind, sibling_order, line_start, line_end) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(commit.scope.document_id),
                        commit.scope.version_id,
                        commit.scope.representation_id,
                        item.ordinal,
                        str(item.block.block_id),
                        item.object.object_id,
                        str(item.block.parent_id) if item.block.parent_id is not None else None,
                        item.block.kind.value,
                        item.block.order,
                        item.line_start,
                        item.line_end,
                    ),
                )
                self._fault_point("after_representation_block")
            for item in commit.blocks:
                text = block_text_for_index(item.block.text)
                entry = SearchIndexEntry(
                    scope=commit.scope,
                    ordinal=item.ordinal,
                    block_id=item.block.block_id,
                    kind=item.block.kind,
                    trust_zone=item.block.trust.zone,
                    line_start=item.line_start,
                    line_end=item.line_end,
                    page=None,
                    slide=None,
                    text_hash=indexed_text_hash(text),
                    indexed_at=commit.ready_at,
                )
                self._insert_search_entry(connection, entry, text)
                self._fault_point("after_search_index_entry")
            self._fault_point("after_search_index")
            warnings_json = json.dumps(
                list(commit.warning_codes),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            connection.execute(
                "UPDATE document_representations SET state = 'READY', revision = revision + 1, "
                "active_owner_id = NULL, active_lease_token_hash = NULL, lease_expires_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = NULL, "
                "manifest_object_id = ?, native_object_id = ?, block_count = ?, "
                "warning_codes_json = ?, updated_at = ?, ready_at = ? WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? AND revision = ? "
                "AND state = 'STAGING'",
                (
                    token_hash,
                    commit.manifest_object.object_id,
                    commit.native_object.object_id,
                    len(commit.blocks),
                    warnings_json,
                    now_text,
                    now_text,
                    str(commit.scope.document_id),
                    commit.scope.version_id,
                    commit.scope.representation_id,
                    expected_revision,
                ),
            )
            self._fault_point("after_representation_ready")
            aggregate = self._required_representation(connection, commit.scope)
            if not self._ready_aggregate_matches(aggregate, commit):
                raise RepresentationIntegrityError("ready representation verification failed")
            head, event = self._advance_head_and_event(
                connection,
                commit.scope,
                source_observed_at=observed_text,
                ingested_at=now_text,
                disposition=disposition,
                parser_invoked=True,
            )
            self._fault_point("before_representation_commit")
            return RepresentationCommitResult(aggregate=aggregate, head=head, event=event)

    def load_representation(
        self,
        scope: RepresentationScope,
    ) -> RepresentationAggregate | None:
        """Load one representation header and all projections from one snapshot."""
        with self._read_connection() as connection:
            row = self._load_representation_row(connection, scope)
            return self._representation_aggregate(connection, row) if row is not None else None

    def record_ready_ingest(
        self,
        scope: RepresentationScope,
        *,
        source_observed_at: datetime,
        ingested_at: datetime,
        disposition: IngestionDisposition,
    ) -> DocumentHeadUpdate:
        """Append a verified READY cache observation and update its current head."""
        if disposition is not IngestionDisposition.CACHE_HIT:
            raise RepresentationConflict("ready reuse must use CACHE_HIT disposition")
        with self._write_connection() as connection:
            aggregate = self._required_representation(connection, scope)
            if aggregate.representation.state is not RepresentationState.READY:
                raise RepresentationIncomplete("representation is not ready")
            head, event = self._advance_head_and_event(
                connection,
                scope,
                source_observed_at=encode_storage_datetime(source_observed_at),
                ingested_at=encode_storage_datetime(ingested_at),
                disposition=disposition,
                parser_invoked=False,
            )
            return DocumentHeadUpdate(head=head, event=event)

    def commit_ready_rich_representation(
        self,
        commit: ReadyRichRepresentationCommit,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        disposition: IngestionDisposition,
    ) -> RichRepresentationCommitResult:
        """Atomically publish one base READY aggregate and its canonical rich attempt."""
        with self._write_connection() as connection:
            base_result = self.commit_ready_representation(
                commit.base,
                owner_id=owner_id,
                lease_token=lease_token,
                expected_revision=expected_revision,
                disposition=disposition,
                _connection=connection,
            )
            self._persist_rich_attempt(
                connection,
                commit.rich,
                event_sequence=base_result.event.sequence,
            )
            accepted = connection.execute(
                "SELECT accepted_attempt_id FROM rich_accepted_representations "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (
                    str(commit.base.scope.document_id),
                    commit.base.scope.version_id,
                    commit.base.scope.representation_id,
                ),
            ).fetchone()
            if accepted is None:
                connection.execute(
                    "INSERT INTO rich_accepted_representations("
                    "document_id, version_id, representation_id, accepted_attempt_id) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        str(commit.base.scope.document_id),
                        commit.base.scope.version_id,
                        commit.base.scope.representation_id,
                        str(commit.rich.attempt.attempt_id),
                    ),
                )
            elif str(accepted["accepted_attempt_id"]) != str(commit.rich.attempt.attempt_id):
                raise RepresentationConflict("accepted rich attempt differs from candidate")
            artifacts = self._required_rich_representation(connection, commit.base.scope)
            if (
                artifacts.accepted_attempt != commit.rich.attempt
                or artifacts.bundle != commit.rich.bundle
            ):
                raise RepresentationIntegrityError("rich representation verification failed")
            self._fault_point("before_rich_representation_commit")
            return RichRepresentationCommitResult(
                artifacts=artifacts,
                head=base_result.head,
                event=base_result.event,
            )

    def append_rich_attempt(
        self,
        commit: RichAttemptCommit,
        *,
        source_observed_at: datetime,
        occurred_at: datetime,
    ) -> RichAttemptAppendResult:
        """Atomically retain one non-canonical attempt without replacing accepted data."""
        if commit.attempt.outcome is RichAttemptOutcome.CANONICAL:
            raise RepresentationConflict("appended rich attempt cannot be canonical")
        observed_text = encode_storage_datetime(source_observed_at)
        occurred_text = encode_storage_datetime(occurred_at)
        with self._write_connection() as connection:
            accepted = self._required_accepted_attempt_id(connection, commit.attempt.scope)
            existing = self._load_rich_attempt_commit(
                connection,
                commit.attempt.attempt_id,
            )
            if existing is not None:
                if existing != commit:
                    raise RepresentationConflict("rich attempt identity has conflicting facts")
                event = self._rich_attempt_event(connection, commit.attempt.attempt_id)
                return RichAttemptAppendResult(
                    attempt=existing.attempt,
                    accepted_attempt_id=accepted,
                    event=event,
                )

            if commit.attempt.outcome is RichAttemptOutcome.CONVERGED:
                _head, event = self._advance_head_and_event(
                    connection,
                    commit.attempt.scope,
                    source_observed_at=observed_text,
                    ingested_at=occurred_text,
                    disposition=IngestionDisposition.CONVERGED,
                    parser_invoked=True,
                )
            else:
                event = self._append_ingestion_event_without_head(
                    connection,
                    commit.attempt.scope,
                    source_observed_at=observed_text,
                    ingested_at=occurred_text,
                    disposition=IngestionDisposition.FORCED_REPARSE,
                )
            self._persist_rich_attempt(
                connection,
                commit,
                event_sequence=event.sequence,
            )
            self._fault_point("before_rich_attempt_commit")
            return RichAttemptAppendResult(
                attempt=commit.attempt,
                accepted_attempt_id=accepted,
                event=event,
            )

    def load_rich_representation(
        self,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts | None:
        """Load one accepted rich aggregate from a single read snapshot."""
        with self._read_connection() as connection:
            return self._rich_representation(connection, scope)

    def get_rich_attempt(self, attempt_id: UUID) -> RichParseAttempt | None:
        """Return one append-only rich attempt or no result."""
        with self._read_connection() as connection:
            commit = self._load_rich_attempt_commit(connection, attempt_id)
            return commit.attempt if commit is not None else None

    def list_rich_attempts(
        self,
        scope: RepresentationScope,
    ) -> tuple[RichParseAttempt, ...]:
        """Return one scope's immutable attempts in deterministic creation order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT attempt_json FROM rich_parse_attempts WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? "
                "ORDER BY created_at, attempt_id",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            try:
                return tuple(
                    RichParseAttempt.model_validate_json(str(row["attempt_json"])) for row in rows
                )
            except ValueError as error:
                raise RepresentationIntegrityError("rich attempt metadata is invalid") from error

    def commit_visual_evidence(self, commit: VisualEvidenceCommit) -> VisualEvidenceRecord:
        """Atomically insert or exactly reuse one page raster and visual descriptor."""
        commit = VisualEvidenceCommit.model_validate(commit)
        descriptor = commit.descriptor
        scope = descriptor.page_raster.scope
        created_at = encode_storage_datetime(descriptor.created_at)
        record = self._visual_record(commit)
        with self._write_connection() as connection:
            rich = self._required_rich_representation(connection, scope)
            projection = next(
                (
                    item
                    for item in rich.bundle.projections
                    if item.evidence_projection_id == descriptor.evidence_projection_id
                ),
                None,
            )
            if projection is None:
                raise VisualCatalogIntegrityError(
                    "visual projection is not in the accepted rich representation"
                )
            native_object = rich.aggregate.representation.native_object
            if (
                descriptor.evidence_reference_id != projection.reference.evidence_reference_id
                or descriptor.target_anchor != projection.reference.anchor
                or descriptor.native_representation_id
                != rich.bundle.native_representation.native_representation_id
                or descriptor.trust != projection.trust
                or native_object is None
                or descriptor.page_raster.source_object != native_object
            ):
                raise VisualCatalogIntegrityError(
                    "visual descriptor disagrees with accepted rich evidence"
                )
            for value in (
                commit.page_raster.raster_object,
                commit.raster_record_object,
                commit.crop_object,
                commit.descriptor_object,
            ):
                self._register_object(connection, value, registered_at=created_at)
                self._fault_point("after_visual_object")
            try:
                connection.execute(
                    "INSERT INTO visual_page_rasters("
                    "raster_id, document_id, version_id, representation_id, page_number, "
                    "recipe_config_hash, raster_record_object_id, raster_object_id, "
                    "raster_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(raster_id) DO NOTHING",
                    (
                        commit.page_raster.raster_id,
                        str(scope.document_id),
                        scope.version_id,
                        scope.representation_id,
                        commit.page_raster.page_number,
                        commit.page_raster.recipe.config_hash,
                        commit.raster_record_object.object_id,
                        commit.page_raster.raster_object.object_id,
                        commit.page_raster.model_dump_json(),
                        created_at,
                    ),
                )
                self._fault_point("after_visual_raster")
                connection.execute(
                    "INSERT INTO visual_evidence("
                    "visual_evidence_id, document_id, version_id, representation_id, "
                    "evidence_projection_id, raster_id, descriptor_object_id, crop_object_id, "
                    "page_number, granularity, canonical_context_profile, descriptor_json, "
                    "created_at, row_fingerprint) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(visual_evidence_id) DO NOTHING",
                    (
                        record.visual_evidence_id,
                        str(scope.document_id),
                        scope.version_id,
                        scope.representation_id,
                        record.evidence_projection_id,
                        record.raster_id,
                        record.descriptor_object.object_id,
                        record.crop_object.object_id,
                        record.page_number,
                        record.granularity.value,
                        int(record.canonical_context_profile),
                        descriptor.model_dump_json(),
                        created_at,
                        record.row_fingerprint,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise VisualCatalogConflict(
                    "visual identity conflicts with persisted immutable facts"
                ) from error
            self._fault_point("after_visual_descriptor")
            persisted = self._load_visual_evidence(connection, record.visual_evidence_id)
            if persisted is None or persisted != commit:
                raise VisualCatalogConflict(
                    "visual evidence conflicts with persisted immutable facts"
                )
            self._fault_point("before_visual_commit")
            return record

    def load_visual_evidence(self, visual_evidence_id: str) -> VisualEvidenceCommit | None:
        """Load one complete verified visual commit or no result."""
        with self._read_connection() as connection:
            return self._load_visual_evidence(connection, visual_evidence_id)

    def load_visual_raster(self, raster_id: str) -> VisualPageRaster | None:
        """Load one verified page-raster record or no result."""
        with self._read_connection() as connection:
            return self._load_visual_raster(connection, raster_id)

    def list_visual_evidence(
        self,
        scope: RepresentationScope,
    ) -> tuple[VisualEvidenceRecord, ...]:
        """List one scope's verified visual records in deterministic identity order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT visual_evidence_id FROM visual_evidence WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? ORDER BY visual_evidence_id",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            records: list[VisualEvidenceRecord] = []
            for row in rows:
                commit = self._load_visual_evidence(
                    connection,
                    str(row["visual_evidence_id"]),
                )
                if commit is None:
                    raise VisualCatalogIntegrityError("visual row vanished during listing")
                records.append(self._visual_record(commit))
            return tuple(records)

    def _load_visual_raster(
        self,
        connection: sqlite3.Connection,
        raster_id: str,
    ) -> VisualPageRaster | None:
        row = connection.execute(
            "SELECT * FROM visual_page_rasters WHERE raster_id = ?",
            (raster_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            raster = VisualPageRaster.model_validate_json(str(row["raster_json"]), strict=True)
            record_object = self._catalog_object(
                connection,
                str(row["raster_record_object_id"]),
            )
            raster_object = self._catalog_object(connection, str(row["raster_object_id"]))
            if (
                raster.raster_id != str(row["raster_id"])
                or raster.scope
                != RepresentationScope(
                    document_id=UUID(str(row["document_id"])),
                    version_id=str(row["version_id"]),
                    representation_id=str(row["representation_id"]),
                )
                or raster.page_number != int(row["page_number"])
                or raster.recipe.config_hash != str(row["recipe_config_hash"])
                or raster.raster_object != raster_object
                or self._canonical_model_object(raster) != record_object
            ):
                raise ValueError("visual raster row drifted")
            return raster
        except (ValidationError, ValueError) as error:
            raise VisualCatalogIntegrityError("stored visual raster is invalid") from error

    def _load_visual_evidence(
        self,
        connection: sqlite3.Connection,
        visual_evidence_id: str,
    ) -> VisualEvidenceCommit | None:
        row = connection.execute(
            "SELECT * FROM visual_evidence WHERE visual_evidence_id = ?",
            (visual_evidence_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            descriptor = VisualEvidenceDescriptor.model_validate_json(
                str(row["descriptor_json"]),
                strict=True,
            )
            raster = self._load_visual_raster(connection, str(row["raster_id"]))
            if raster is None:
                raise ValueError("visual raster is missing")
            commit = VisualEvidenceCommit(
                page_raster=raster,
                descriptor=descriptor,
                raster_record_object=self._catalog_object(
                    connection,
                    str(
                        connection.execute(
                            "SELECT raster_record_object_id FROM visual_page_rasters "
                            "WHERE raster_id = ?",
                            (raster.raster_id,),
                        ).fetchone()[0]
                    ),
                ),
                descriptor_object=self._catalog_object(
                    connection,
                    str(row["descriptor_object_id"]),
                ),
                crop_object=self._catalog_object(connection, str(row["crop_object_id"])),
            )
            record = self._visual_record(commit)
            if (
                record.visual_evidence_id != str(row["visual_evidence_id"])
                or record.scope.document_id != UUID(str(row["document_id"]))
                or record.scope.version_id != str(row["version_id"])
                or record.scope.representation_id != str(row["representation_id"])
                or record.evidence_projection_id != str(row["evidence_projection_id"])
                or record.page_number != int(row["page_number"])
                or record.granularity is not VisualGranularity(str(row["granularity"]))
                or record.canonical_context_profile != bool(int(row["canonical_context_profile"]))
                or record.row_fingerprint != str(row["row_fingerprint"])
            ):
                raise ValueError("visual descriptor row drifted")
            return commit
        except (ValidationError, ValueError, TypeError, IndexError) as error:
            raise VisualCatalogIntegrityError("stored visual evidence is invalid") from error

    @staticmethod
    def _visual_record(commit: VisualEvidenceCommit) -> VisualEvidenceRecord:
        descriptor = commit.descriptor
        recipe = descriptor.recipe
        canonical_profile = (
            recipe.renderer.name == "pypdfium2"
            and recipe.renderer.version == "5.12.1"
            and recipe.renderer.profile is not None
            and _PDF_RENDER_PROFILE.fullmatch(recipe.renderer.profile) is not None
            and recipe.encoder.name == "Pillow"
            and recipe.encoder.version == "12.3.0"
            and recipe.encoder.profile is not None
            and _PNG_ENCODER_PROFILE.fullmatch(recipe.encoder.profile) is not None
            and recipe.scale_numerator == 2
            and recipe.scale_denominator == 1
        )
        unvalidated = VisualEvidenceRecord.model_construct(
            visual_evidence_id=descriptor.visual_evidence_id,
            scope=descriptor.page_raster.scope,
            evidence_projection_id=descriptor.evidence_projection_id,
            raster_id=descriptor.page_raster.raster_id,
            raster_record_object=commit.raster_record_object,
            descriptor_object=commit.descriptor_object,
            crop_object=commit.crop_object,
            page_number=descriptor.page_raster.page_number,
            granularity=descriptor.resolved_region.granularity,
            canonical_context_profile=canonical_profile,
            created_at=descriptor.created_at,
            row_fingerprint="sha256:" + "0" * 64,
        )
        return VisualEvidenceRecord(
            visual_evidence_id=descriptor.visual_evidence_id,
            scope=descriptor.page_raster.scope,
            evidence_projection_id=descriptor.evidence_projection_id,
            raster_id=descriptor.page_raster.raster_id,
            raster_record_object=commit.raster_record_object,
            descriptor_object=commit.descriptor_object,
            crop_object=commit.crop_object,
            page_number=descriptor.page_raster.page_number,
            granularity=descriptor.resolved_region.granularity,
            canonical_context_profile=canonical_profile,
            created_at=descriptor.created_at,
            row_fingerprint=visual_record_fingerprint(unvalidated),
        )

    @staticmethod
    def _canonical_model_object(model: VisualPageRaster) -> StoredObject:
        payload = canonical_json_bytes(model.model_dump(mode="json"))
        return StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )

    @staticmethod
    def _catalog_object(connection: sqlite3.Connection, object_id: str) -> StoredObject:
        row = connection.execute(
            "SELECT byte_length FROM objects WHERE object_id = ?",
            (object_id,),
        ).fetchone()
        if row is None:
            raise VisualCatalogIntegrityError("visual object metadata is missing")
        return StoredObject(object_id=object_id, byte_length=int(row["byte_length"]))

    def commit_context_compilation(
        self,
        commit: ContextCompilationCommit,
    ) -> ContextCompilationRecord:
        """Atomically insert or exactly reuse one compilation and its scope rows."""
        record = commit.record
        created_at = encode_storage_datetime(record.created_at)
        with self._write_connection() as connection:
            self._register_object(connection, record.receipt_object, registered_at=created_at)
            self._register_object(connection, record.bundle_object, registered_at=created_at)
            for scope in commit.scopes:
                root = connection.execute(
                    "SELECT 1 FROM document_representations "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                    (
                        str(scope.scope.document_id),
                        scope.scope.version_id,
                        scope.scope.representation_id,
                    ),
                ).fetchone()
                if root is None:
                    raise RepresentationNotFound(
                        "compilation scope root is not a persisted representation"
                    )
            connection.execute(
                "INSERT INTO context_compilations("
                "receipt_id, receipt_object_id, receipt_byte_length, bundle_object_id, "
                "bundle_byte_length, bundle_id, task_digest, algorithm_name, "
                "algorithm_version, algorithm_config_hash, estimator_name, "
                "estimator_version, estimator_unit, estimator_config_hash, policy_digest, "
                "budget_limit, budget_unit, created_at, selected_count, omitted_count, "
                "rejected_count, stale_count, row_fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(receipt_id) DO NOTHING",
                self._compilation_row_values(record, created_at),
            )
            for scope in commit.scopes:
                connection.execute(
                    "INSERT INTO context_compilation_scopes("
                    "receipt_id, ordinal, document_id, version_id, representation_id) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT(receipt_id, ordinal) DO NOTHING",
                    (
                        record.receipt_id,
                        scope.ordinal,
                        str(scope.scope.document_id),
                        scope.scope.version_id,
                        scope.scope.representation_id,
                    ),
                )
            persisted = self._load_context_compilation(connection, record.receipt_id)
            if persisted is None:
                raise CatalogError("context compilation insert did not persist")
            if persisted != commit:
                raise ContextCompilationConflict(
                    "context compilation conflicts with the persisted immutable record"
                )
            return persisted.record

    def load_context_compilation(
        self,
        receipt_id: str,
    ) -> ContextCompilationCommit | None:
        """Return one body-free compilation aggregate from a single snapshot."""
        with self._read_connection() as connection:
            return self._load_context_compilation(connection, receipt_id)

    def list_context_compilations(self) -> tuple[ContextCompilationRecord, ...]:
        """Return immutable compilation rows in deterministic identity order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT receipt_id FROM context_compilations ORDER BY receipt_id"
            ).fetchall()
            records: list[ContextCompilationRecord] = []
            for row in rows:
                commit = self._load_context_compilation(connection, str(row["receipt_id"]))
                if commit is None:
                    raise CatalogError("context compilation row vanished during listing")
                records.append(commit.record)
            return tuple(records)

    def _load_context_compilation(
        self,
        connection: sqlite3.Connection,
        receipt_id: str,
    ) -> ContextCompilationCommit | None:
        row = connection.execute(
            "SELECT * FROM context_compilations WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None
        scope_rows = connection.execute(
            "SELECT * FROM context_compilation_scopes WHERE receipt_id = ? ORDER BY ordinal",
            (receipt_id,),
        ).fetchall()
        try:
            record = ContextCompilationRecord.model_validate(
                {
                    "receipt_id": str(row["receipt_id"]),
                    "receipt_object": {
                        "object_id": str(row["receipt_object_id"]),
                        "byte_length": int(row["receipt_byte_length"]),
                    },
                    "bundle_object": {
                        "object_id": str(row["bundle_object_id"]),
                        "byte_length": int(row["bundle_byte_length"]),
                    },
                    "bundle_id": UUID(str(row["bundle_id"])),
                    "task_digest": str(row["task_digest"]),
                    "algorithm": {
                        "name": str(row["algorithm_name"]),
                        "version": str(row["algorithm_version"]),
                        "config_hash": str(row["algorithm_config_hash"]),
                    },
                    "estimator": {
                        "name": str(row["estimator_name"]),
                        "version": str(row["estimator_version"]),
                        "unit": BudgetUnit(str(row["estimator_unit"])),
                        "config_hash": str(row["estimator_config_hash"]),
                    },
                    "policy_digest": str(row["policy_digest"]),
                    "budget_limit": int(row["budget_limit"]),
                    "budget_unit": BudgetUnit(str(row["budget_unit"])),
                    "created_at": decode_storage_datetime(str(row["created_at"])),
                    "selected_count": int(row["selected_count"]),
                    "omitted_count": int(row["omitted_count"]),
                    "rejected_count": int(row["rejected_count"]),
                    "stale_count": int(row["stale_count"]),
                    "row_fingerprint": str(row["row_fingerprint"]),
                }
            )
            commit = ContextCompilationCommit(
                record=record,
                scopes=tuple(
                    ContextCompilationScope(
                        receipt_id=str(scope_row["receipt_id"]),
                        ordinal=int(scope_row["ordinal"]),
                        scope=VersionScope(
                            document_id=UUID(str(scope_row["document_id"])),
                            version_id=str(scope_row["version_id"]),
                            representation_id=str(scope_row["representation_id"]),
                        ),
                    )
                    for scope_row in scope_rows
                ),
            )
        except (ValidationError, ValueError) as error:
            raise CatalogError("context compilation rows failed integrity validation") from error
        return commit

    @staticmethod
    def _compilation_row_values(
        record: ContextCompilationRecord,
        created_at: str,
    ) -> tuple[object, ...]:
        return (
            record.receipt_id,
            record.receipt_object.object_id,
            record.receipt_object.byte_length,
            record.bundle_object.object_id,
            record.bundle_object.byte_length,
            str(record.bundle_id),
            record.task_digest,
            record.algorithm.name,
            record.algorithm.version,
            record.algorithm.config_hash,
            record.estimator.name,
            record.estimator.version,
            record.estimator.unit.value,
            record.estimator.config_hash,
            record.policy_digest,
            record.budget_limit,
            record.budget_unit.value,
            created_at,
            record.selected_count,
            record.omitted_count,
            record.rejected_count,
            record.stale_count,
            record.row_fingerprint,
        )

    def get_document_head(self, document_id: UUID) -> DocumentHead | None:
        """Return the current successful representation observation."""
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM document_heads WHERE document_id = ?",
                (str(document_id),),
            ).fetchone()
            return self._head_from_row(row) if row is not None else None

    def list_document_summaries(self) -> tuple[DocumentSummary, ...]:
        """Return deterministic document metadata without block bodies."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT d.*, h.version_id, h.representation_id, h.last_ingested_at, "
                "r.state, r.block_count, r.warning_codes_json FROM documents AS d "
                "LEFT JOIN document_heads AS h ON h.document_id = d.document_id "
                "LEFT JOIN document_representations AS r ON r.document_id = h.document_id "
                "AND r.version_id = h.version_id AND r.representation_id = h.representation_id "
                "ORDER BY d.connector, d.source_locator, d.document_id"
            ).fetchall()
            summaries: list[DocumentSummary] = []
            for row in rows:
                document_id = UUID(str(row["document_id"]))
                has_head = row["representation_id"] is not None
                warnings = self._warning_codes(str(row["warning_codes_json"])) if has_head else ()
                summaries.append(
                    DocumentSummary(
                        document_id=document_id,
                        source_key=SourceKey(
                            connector=str(row["connector"]),
                            locator=str(row["source_locator"]),
                        ),
                        head=(
                            RepresentationScope(
                                document_id=document_id,
                                version_id=str(row["version_id"]),
                                representation_id=str(row["representation_id"]),
                            )
                            if has_head
                            else None
                        ),
                        state=(RepresentationState(str(row["state"])) if has_head else None),
                        block_count=int(row["block_count"]) if has_head else 0,
                        warning_count=len(warnings),
                        last_ingested_at=(
                            decode_storage_datetime(str(row["last_ingested_at"]))
                            if has_head
                            else None
                        ),
                    )
                )
            return tuple(summaries)

    def resolve_ready_representation(
        self,
        document_id: UUID,
        *,
        version_id: str | None,
    ) -> RepresentationAggregate | None:
        """Resolve the current head or one unambiguous historical READY scope."""
        with self._read_connection() as connection:
            if self._load_document_by_id(connection, document_id) is None:
                return None
            if version_id is None:
                head_row = connection.execute(
                    "SELECT * FROM document_heads WHERE document_id = ?",
                    (str(document_id),),
                ).fetchone()
                if head_row is None:
                    return None
                scope = self._head_from_row(head_row).scope
            else:
                rows = connection.execute(
                    "SELECT representation_id FROM document_representations WHERE "
                    "document_id = ? AND version_id = ? AND state = 'READY' "
                    "ORDER BY representation_id",
                    (str(document_id), version_id),
                ).fetchall()
                if not rows:
                    return None
                if len(rows) > 1:
                    raise RepresentationConflict(
                        "multiple READY recipes require an exact representation scope"
                    )
                scope = RepresentationScope(
                    document_id=document_id,
                    version_id=version_id,
                    representation_id=str(rows[0][0]),
                )
            return self._required_representation(connection, scope)

    def find_current_blocks(self, block_id: UUID) -> tuple[RepresentationBlock, ...]:
        """Return current-head block projections matching one logical handle."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT b.*, o.byte_length FROM representation_blocks AS b "
                "JOIN document_heads AS h ON h.document_id = b.document_id "
                "AND h.version_id = b.version_id AND h.representation_id = b.representation_id "
                "JOIN objects AS o ON o.object_id = b.object_id WHERE b.block_id = ? "
                "ORDER BY b.document_id, b.version_id, b.representation_id, b.ordinal",
                (str(block_id),),
            ).fetchall()
            return tuple(self._block_projection_from_row(row) for row in rows)

    def list_ingestion_events(self, document_id: UUID) -> tuple[IngestionEvent, ...]:
        """Return append-only ingestion evidence in sequence order."""
        with self._read_connection() as connection:
            if self._load_document_by_id(connection, document_id) is None:
                raise DocumentNotFound(str(document_id))
            rows = connection.execute(
                "SELECT * FROM ingestion_events WHERE document_id = ? ORDER BY sequence",
                (str(document_id),),
            ).fetchall()
            return tuple(self._ingestion_event_from_row(row) for row in rows)

    def register_watch_root(self, root: AdmittedWatchRoot, *, now: datetime) -> WatchRoot:
        """Register or exactly reuse one admitted root authority."""
        now_text = encode_storage_datetime(now)
        config_json = canonical_json_bytes(root.config.model_dump(mode="json")).decode("utf-8")
        with self._write_connection() as connection:
            existing = connection.execute(
                "SELECT * FROM watch_roots WHERE root_id = ?", (root.root_id,)
            ).fetchone()
            if existing is not None:
                projection = self._watch_root_from_row(existing)
                if projection.authority != root:
                    raise JobConflict("watch root identity has conflicting immutable facts")
                return projection
            connection.execute(
                "INSERT INTO watch_roots("
                "root_id, root_path, root_path_digest, device_id, file_id, config_json, "
                "config_hash, generation, rescan_required, created_at, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)",
                (
                    root.root_id,
                    root.root_path,
                    root.root_path_digest,
                    root.device_id,
                    root.file_id,
                    config_json,
                    root.config.config_hash,
                    now_text,
                    now_text,
                ),
            )
            self._fault_point("after_watch_root")
            self._append_watch_event(
                connection,
                root_id=root.root_id,
                event_type=WatchEventType.ROOT_REGISTERED,
                generation=0,
                occurred_at=now_text,
            )
            created = self._load_watch_root(connection, root.root_id)
            if created is None:
                raise CatalogError("watch root did not become visible")
            return created

    def get_watch_root(self, root_id: str) -> WatchRoot | None:
        """Return one durable current watch-root projection."""
        with self._read_connection() as connection:
            return self._load_watch_root(connection, root_id)

    def reconcile_watch_scan(
        self,
        root_id: str,
        scan: WatchScan,
        *,
        now: datetime,
    ) -> WatchReconciliation:
        """Atomically reconcile a complete scan or record only rescan state."""
        if scan.root_id != root_id:
            raise JobConflict("watch scan root identity does not match")
        now_text = encode_storage_datetime(now)
        if now < scan.completed_at:
            raise InvalidJobTransition("reconciliation time precedes scan completion")
        with self._write_connection() as connection:
            root_row = self._required_watch_root_row(connection, root_id)
            self._assert_transition_time(root_row, now_text=now_text)
            current_generation = int(root_row["generation"])
            if not scan.complete:
                connection.execute(
                    "UPDATE watch_roots SET rescan_required = 1, updated_at = ? WHERE root_id = ?",
                    (now_text, root_id),
                )
                self._append_watch_event(
                    connection,
                    root_id=root_id,
                    event_type=WatchEventType.RESCAN_REQUIRED,
                    generation=current_generation,
                    occurred_at=now_text,
                )
                root = self._load_watch_root(connection, root_id)
                if root is None:
                    raise CatalogError("watch root did not remain visible")
                return WatchReconciliation(
                    root=root,
                    complete=False,
                    entry_count=0,
                    candidate_count=0,
                    stable_count=0,
                    scheduled_job_ids=(),
                    tombstone_count=0,
                )

            generation = current_generation + 1
            existing_rows = {
                str(row["locator_digest"]): row
                for row in connection.execute(
                    "SELECT * FROM watch_observations WHERE root_id = ?",
                    (root_id,),
                ).fetchall()
            }
            scanned_digests = {entry.locator_digest for entry in scan.entries}
            previous_by_file_identity: dict[tuple[str, str], list[WatchObservation]] = {}
            for previous_row in existing_rows.values():
                prior_observation = self._watch_observation_from_row(previous_row)
                if prior_observation.fingerprint is not None:
                    identity = (
                        prior_observation.fingerprint.device_id,
                        prior_observation.fingerprint.file_id,
                    )
                    previous_by_file_identity.setdefault(identity, []).append(prior_observation)
            current_by_file_identity: dict[tuple[str, str], list[WatchScanEntry]] = {}
            for entry in scan.entries:
                identity = (entry.fingerprint.device_id, entry.fingerprint.file_id)
                current_by_file_identity.setdefault(identity, []).append(entry)
            rename_hints = tuple(
                current_entries[0].locator_digest
                for identity, current_entries in sorted(current_by_file_identity.items())
                if len(current_entries) == 1
                and len(previous_by_file_identity.get(identity, ())) == 1
                and previous_by_file_identity[identity][0].locator_digest not in scanned_digests
                and current_entries[0].locator_digest not in existing_rows
                and previous_by_file_identity[identity][0].fingerprint
                == current_entries[0].fingerprint
            )
            seen: set[str] = set()
            candidate_count = 0
            stable_count = 0
            tombstone_count = 0
            scheduled: list[UUID] = []
            active_count = int(
                connection.execute(
                    "SELECT count(*) FROM watch_job_targets AS t "
                    "JOIN jobs AS j ON j.job_id = t.job_id "
                    "WHERE t.root_id = ? AND j.state IN ('QUEUED', 'RUNNING')",
                    (root_id,),
                ).fetchone()[0]
            )
            backpressure = False
            config = self._watch_root_from_row(root_row).authority.config
            observed_at = scan.completed_at
            for entry in scan.entries:
                seen.add(entry.locator_digest)
                previous_row = existing_rows.get(entry.locator_digest)
                previous = (
                    self._watch_observation_from_row(previous_row)
                    if previous_row is not None
                    else None
                )
                event_type: WatchEventType | None = None
                if previous is None:
                    state = (
                        WatchObservationState.STABLE
                        if config.stability_ms == 0
                        else WatchObservationState.CANDIDATE
                    )
                    first_observed_at = observed_at
                    stable_since = observed_at if state is WatchObservationState.STABLE else None
                    last_scheduled_key = None
                    revision = 1
                    event_type = WatchEventType.OBSERVATION_CREATED
                elif (
                    previous.state is WatchObservationState.TOMBSTONED
                    or previous.fingerprint != entry.fingerprint
                ):
                    state = (
                        WatchObservationState.STABLE
                        if config.stability_ms == 0
                        else WatchObservationState.CANDIDATE
                    )
                    first_observed_at = observed_at
                    stable_since = observed_at if state is WatchObservationState.STABLE else None
                    last_scheduled_key = None
                    revision = previous.revision + 1
                    event_type = (
                        WatchEventType.REAPPEARED
                        if previous.state is WatchObservationState.TOMBSTONED
                        else WatchEventType.OBSERVATION_CHANGED
                    )
                else:
                    elapsed_ms = int(
                        (observed_at - previous.first_observed_at).total_seconds() * 1_000
                    )
                    is_stable = elapsed_ms >= config.stability_ms
                    state = (
                        WatchObservationState.STABLE
                        if is_stable
                        else WatchObservationState.CANDIDATE
                    )
                    first_observed_at = previous.first_observed_at
                    stable_since = previous.stable_since or observed_at if is_stable else None
                    last_scheduled_key = previous.last_scheduled_key
                    revision = previous.revision + 1
                    if is_stable and previous.state is not WatchObservationState.STABLE:
                        event_type = WatchEventType.OBSERVATION_STABLE
                observation = self._make_watch_observation(
                    root_id=root_id,
                    relative_locator=entry.relative_locator,
                    locator_digest=entry.locator_digest,
                    state=state,
                    fingerprint=entry.fingerprint,
                    first_observed_at=first_observed_at,
                    last_observed_at=observed_at,
                    stable_since=stable_since,
                    last_generation=generation,
                    last_scheduled_key=last_scheduled_key,
                    revision=revision,
                )
                self._write_watch_observation(connection, observation)
                self._fault_point("after_watch_observation")
                if event_type is not None:
                    self._append_watch_event(
                        connection,
                        root_id=root_id,
                        event_type=event_type,
                        locator_digest=entry.locator_digest,
                        generation=generation,
                        occurred_at=now_text,
                    )
                if state is WatchObservationState.CANDIDATE:
                    candidate_count += 1
                    continue
                stable_count += 1
                profile = (
                    config.text_profile
                    if entry.media_type.startswith("text/")
                    else config.rich_profile
                )
                key = watch_job_key(
                    root_id=root_id,
                    locator_digest=entry.locator_digest,
                    fingerprint=entry.fingerprint,
                    parser_profile=profile,
                )
                if observation.last_scheduled_key == key:
                    continue
                if active_count >= config.max_active_jobs:
                    backpressure = True
                    continue
                job_id = uuid5(_WATCH_JOB_NAMESPACE, key)
                job = self._create_watch_job_and_target(
                    connection,
                    job_id=job_id,
                    root_id=root_id,
                    entry=entry,
                    parser_profile=profile,
                    deduplication_key=key,
                    max_attempts=config.max_attempts,
                    created_at=now,
                )
                observation = observation.model_copy(
                    update={
                        "last_scheduled_key": key,
                        "row_fingerprint": self._observation_fingerprint_with_update(
                            observation, last_scheduled_key=key
                        ),
                    }
                )
                self._write_watch_observation(connection, observation)
                scheduled.append(job.job_id)
                active_count += 1
                self._append_watch_event(
                    connection,
                    root_id=root_id,
                    event_type=WatchEventType.TARGET_SCHEDULED,
                    locator_digest=entry.locator_digest,
                    job_id=job.job_id,
                    generation=generation,
                    occurred_at=now_text,
                    scheduled_count=1,
                )

            for locator_digest, previous_row in sorted(existing_rows.items()):
                previous = self._watch_observation_from_row(previous_row)
                if locator_digest in seen or previous.state is WatchObservationState.TOMBSTONED:
                    continue
                tombstone = self._make_watch_observation(
                    root_id=root_id,
                    relative_locator=previous.relative_locator,
                    locator_digest=locator_digest,
                    state=WatchObservationState.TOMBSTONED,
                    fingerprint=None,
                    first_observed_at=previous.first_observed_at,
                    last_observed_at=observed_at,
                    stable_since=None,
                    last_generation=generation,
                    last_scheduled_key=previous.last_scheduled_key,
                    revision=previous.revision + 1,
                )
                self._write_watch_observation(connection, tombstone)
                self._fault_point("after_watch_tombstone")
                tombstone_count += 1
                self._append_watch_event(
                    connection,
                    root_id=root_id,
                    event_type=WatchEventType.TOMBSTONED,
                    locator_digest=locator_digest,
                    generation=generation,
                    occurred_at=now_text,
                    tombstone_count=1,
                )

            for locator_digest in rename_hints:
                self._append_watch_event(
                    connection,
                    root_id=root_id,
                    event_type=WatchEventType.RENAME_HINT,
                    locator_digest=locator_digest,
                    generation=generation,
                    occurred_at=now_text,
                )

            connection.execute(
                "UPDATE watch_roots SET generation = ?, rescan_required = ?, updated_at = ? "
                "WHERE root_id = ?",
                (generation, int(backpressure), now_text, root_id),
            )
            self._append_watch_event(
                connection,
                root_id=root_id,
                event_type=(
                    WatchEventType.BACKPRESSURE if backpressure else WatchEventType.SCAN_COMPLETED
                ),
                generation=generation,
                occurred_at=now_text,
                entry_count=len(scan.entries),
                scheduled_count=len(scheduled),
                tombstone_count=tombstone_count,
            )
            self._fault_point("before_watch_reconciliation_commit")
            updated_root = self._load_watch_root(connection, root_id)
            if updated_root is None:
                raise CatalogError("watch root did not remain visible")
            return WatchReconciliation(
                root=updated_root,
                complete=True,
                entry_count=len(scan.entries),
                candidate_count=candidate_count,
                stable_count=stable_count,
                scheduled_job_ids=tuple(sorted(scheduled, key=str)),
                tombstone_count=tombstone_count,
            )

    def get_watch_target(self, job_id: UUID) -> WatchJobTarget | None:
        """Return one immutable watcher target without event/log disclosure."""
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM watch_job_targets WHERE job_id = ?", (str(job_id),)
            ).fetchone()
            return self._watch_target_from_row(row) if row is not None else None

    def list_watch_events(self, root_id: str) -> tuple[WatchEvent, ...]:
        """Return append-only body/path-free watcher events."""
        with self._read_connection() as connection:
            self._required_watch_root_row(connection, root_id)
            rows = connection.execute(
                "SELECT * FROM watch_events WHERE root_id = ? ORDER BY sequence",
                (root_id,),
            ).fetchall()
            return tuple(self._watch_event_from_row(row) for row in rows)

    def list_watch_observations(self, root_id: str) -> tuple[WatchObservation, ...]:
        """Return deterministic watcher state while keeping it out of default events."""
        with self._read_connection() as connection:
            self._required_watch_root_row(connection, root_id)
            rows = connection.execute(
                "SELECT * FROM watch_observations WHERE root_id = ? ORDER BY locator_digest",
                (root_id,),
            ).fetchall()
            return tuple(self._watch_observation_from_row(row) for row in rows)

    def create_job(self, spec: JobSpec) -> Job:
        """Create or idempotently return one immutable queued job request."""
        created_at = encode_storage_datetime(spec.created_at)
        available_at = encode_storage_datetime(spec.available_at or spec.created_at)
        with self._write_connection() as connection:
            existing_row = connection.execute(
                "SELECT * FROM jobs WHERE kind = ? AND deduplication_key = ?",
                (spec.kind, spec.deduplication_key),
            ).fetchone()
            if existing_row is not None:
                existing = self._job_from_row(connection, existing_row)
                if self._job_matches_spec(existing, spec):
                    return existing
                raise JobConflict("job idempotency key has different immutable data")
            if connection.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?", (str(spec.job_id),)
            ).fetchone():
                raise JobConflict("job identity is already registered")
            for reference in spec.references:
                self._register_object(connection, reference, registered_at=created_at)
            if self._migrations[-1].version < 9:
                connection.execute(
                    "INSERT INTO jobs("
                    "job_id, kind, deduplication_key, state, attempt_count, max_attempts, "
                    "revision, active_owner_id, active_lease_token_hash, lease_expires_at, "
                    "last_transition_token_hash, last_failure_code, created_at, updated_at, "
                    "terminal_at) VALUES (?, ?, ?, 'QUEUED', 0, ?, 0, NULL, NULL, NULL, NULL, "
                    "NULL, ?, ?, NULL)",
                    (
                        str(spec.job_id),
                        spec.kind,
                        spec.deduplication_key,
                        spec.max_attempts,
                        created_at,
                        created_at,
                    ),
                )
            else:
                connection.execute(
                    "INSERT INTO jobs("
                    "job_id, kind, deduplication_key, state, attempt_count, max_attempts, "
                    "revision, available_at, active_owner_id, active_lease_token_hash, "
                    "lease_expires_at, cancellation_requested_at, last_transition_token_hash, "
                    "last_failure_code, created_at, updated_at, terminal_at) VALUES "
                    "(?, ?, ?, 'QUEUED', 0, ?, 0, ?, NULL, NULL, NULL, NULL, NULL, NULL, "
                    "?, ?, NULL)",
                    (
                        str(spec.job_id),
                        spec.kind,
                        spec.deduplication_key,
                        spec.max_attempts,
                        available_at,
                        created_at,
                        created_at,
                    ),
                )
            for reference in spec.references:
                connection.execute(
                    "INSERT INTO job_object_references("
                    "job_id, role, ordinal, object_id, media_type) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        str(spec.job_id),
                        reference.role,
                        reference.ordinal,
                        reference.object_id,
                        reference.media_type,
                    ),
                )
            self._append_event(
                connection,
                job_id=spec.job_id,
                event_type=JobEventType.ENQUEUED,
                from_state=None,
                to_state=JobState.QUEUED,
                occurred_at=created_at,
                attempt_count=0,
                owner_id=None,
                failure_code=None,
            )
            created = self._load_job(connection, spec.job_id)
            if created is None:
                raise CatalogError("queued job did not become visible")
            return created

    def claim_job(
        self,
        *,
        kind: str | None,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease | None:
        """Claim one queued job or replay an existing unexpired token claim."""
        self._validate_owner(owner_id)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise InvalidJobTransition("lease_until must be later than now")
        with self._write_connection() as connection:
            parameters: tuple[Any, ...]
            if kind is None:
                active_sql = (
                    "SELECT * FROM jobs WHERE state = 'RUNNING' AND active_owner_id = ? "
                    "AND active_lease_token_hash = ? AND lease_expires_at > ?"
                )
                parameters = (owner_id, token_hash, now_text)
            else:
                active_sql = (
                    "SELECT * FROM jobs WHERE state = 'RUNNING' AND kind = ? "
                    "AND active_owner_id = ? AND active_lease_token_hash = ? "
                    "AND lease_expires_at > ?"
                )
                parameters = (kind, owner_id, token_hash, now_text)
            active = connection.execute(active_sql, parameters).fetchone()
            if active is not None:
                return JobLease(
                    job=self._job_from_row(connection, active),
                    lease_token=SecretStr(lease_token),
                )

            if kind is None:
                future_state = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'QUEUED' AND updated_at > ? "
                    "ORDER BY updated_at, job_id LIMIT 1",
                    (now_text,),
                ).fetchone()
            else:
                future_state = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'QUEUED' AND kind = ? "
                    "AND updated_at > ? ORDER BY updated_at, job_id LIMIT 1",
                    (kind, now_text),
                ).fetchone()
            if future_state is not None:
                self._assert_transition_time(future_state, now_text=now_text)

            if kind is None:
                queued = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'QUEUED' AND available_at <= ? "
                    "ORDER BY available_at, created_at, job_id LIMIT 1",
                    (now_text,),
                ).fetchone()
            else:
                queued = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'QUEUED' AND kind = ? "
                    "AND available_at <= ? ORDER BY available_at, created_at, job_id LIMIT 1",
                    (kind, now_text),
                ).fetchone()
            if queued is None:
                return None
            self._assert_transition_time(queued, now_text=now_text)
            job_id = UUID(str(queued["job_id"]))
            attempt_count = int(queued["attempt_count"]) + 1
            revision = int(queued["revision"]) + 1
            connection.execute(
                "UPDATE jobs SET state = 'RUNNING', attempt_count = ?, revision = ?, "
                "active_owner_id = ?, active_lease_token_hash = ?, lease_expires_at = ?, "
                "updated_at = ?, terminal_at = NULL WHERE job_id = ? AND state = 'QUEUED'",
                (
                    attempt_count,
                    revision,
                    owner_id,
                    token_hash,
                    lease_text,
                    now_text,
                    str(job_id),
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=JobEventType.CLAIMED,
                from_state=JobState.QUEUED,
                to_state=JobState.RUNNING,
                occurred_at=now_text,
                attempt_count=attempt_count,
                owner_id=owner_id,
                failure_code=None,
            )
            claimed = self._load_job(connection, job_id)
            if claimed is None:
                raise CatalogError("claimed job did not become visible")
            return JobLease(job=claimed, lease_token=SecretStr(lease_token))

    def claim_watch_job(
        self,
        root_id: str,
        *,
        owner_id: str,
        lease_token: str,
        now: datetime,
        lease_until: datetime,
    ) -> JobLease | None:
        """Claim one eligible watcher job only from the explicitly admitted root."""
        self._validate_owner(owner_id)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise InvalidJobTransition("lease_until must be later than now")
        with self._write_connection() as connection:
            self._required_watch_root_row(connection, root_id)
            active = connection.execute(
                "SELECT j.* FROM jobs AS j JOIN watch_job_targets AS t ON t.job_id = j.job_id "
                "WHERE t.root_id = ? AND j.state = 'RUNNING' AND j.active_owner_id = ? "
                "AND j.active_lease_token_hash = ? AND j.lease_expires_at > ?",
                (root_id, owner_id, token_hash, now_text),
            ).fetchone()
            if active is not None:
                return JobLease(
                    job=self._job_from_row(connection, active),
                    lease_token=SecretStr(lease_token),
                )
            future = connection.execute(
                "SELECT j.* FROM jobs AS j JOIN watch_job_targets AS t ON t.job_id = j.job_id "
                "WHERE t.root_id = ? AND j.state = 'QUEUED' AND j.updated_at > ? "
                "ORDER BY j.updated_at, j.job_id LIMIT 1",
                (root_id, now_text),
            ).fetchone()
            if future is not None:
                self._assert_transition_time(future, now_text=now_text)
            queued = connection.execute(
                "SELECT j.* FROM jobs AS j JOIN watch_job_targets AS t ON t.job_id = j.job_id "
                "WHERE t.root_id = ? AND j.state = 'QUEUED' AND j.available_at <= ? "
                "ORDER BY j.available_at, j.created_at, j.job_id LIMIT 1",
                (root_id, now_text),
            ).fetchone()
            if queued is None:
                return None
            self._assert_transition_time(queued, now_text=now_text)
            job_id = UUID(str(queued["job_id"]))
            attempt_count = int(queued["attempt_count"]) + 1
            revision = int(queued["revision"]) + 1
            connection.execute(
                "UPDATE jobs SET state = 'RUNNING', attempt_count = ?, revision = ?, "
                "active_owner_id = ?, active_lease_token_hash = ?, lease_expires_at = ?, "
                "updated_at = ?, terminal_at = NULL WHERE job_id = ? AND state = 'QUEUED'",
                (
                    attempt_count,
                    revision,
                    owner_id,
                    token_hash,
                    lease_text,
                    now_text,
                    str(job_id),
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=JobEventType.CLAIMED,
                from_state=JobState.QUEUED,
                to_state=JobState.RUNNING,
                occurred_at=now_text,
                attempt_count=attempt_count,
                owner_id=owner_id,
                failure_code=None,
            )
            claimed = self._load_job(connection, job_id)
            if claimed is None:
                raise CatalogError("claimed watch job did not become visible")
            return JobLease(job=claimed, lease_token=SecretStr(lease_token))

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
        """Renew one active lease with exact compare-and-set fencing."""
        self._validate_owner(owner_id)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        lease_text = encode_storage_datetime(lease_until)
        if lease_text <= now_text:
            raise InvalidJobTransition("lease_until must be later than now")
        with self._write_connection() as connection:
            row = self._required_job_row(connection, job_id)
            self._assert_active_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
                allow_idempotent_revision=True,
                requested_lease_until=lease_text,
            )
            self._assert_transition_time(row, now_text=now_text)
            if int(row["revision"]) != expected_revision:
                return JobLease(
                    job=self._job_from_row(connection, row),
                    lease_token=SecretStr(lease_token),
                )
            revision = expected_revision + 1
            connection.execute(
                "UPDATE jobs SET revision = ?, lease_expires_at = ?, updated_at = ? "
                "WHERE job_id = ? AND revision = ? AND state = 'RUNNING'",
                (revision, lease_text, now_text, str(job_id), expected_revision),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=JobEventType.RENEWED,
                from_state=JobState.RUNNING,
                to_state=JobState.RUNNING,
                occurred_at=now_text,
                attempt_count=int(row["attempt_count"]),
                owner_id=owner_id,
                failure_code=None,
            )
            renewed = self._load_job(connection, job_id)
            if renewed is None:
                raise CatalogError("renewed job did not become visible")
            return JobLease(job=renewed, lease_token=SecretStr(lease_token))

    def complete_job(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
    ) -> Job:
        """Complete a running job or replay the same successful transition."""
        self._validate_owner(owner_id)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        with self._write_connection() as connection:
            row = self._required_job_row(connection, job_id)
            if row["state"] == JobState.SUCCEEDED.value:
                if row["last_transition_token_hash"] == token_hash:
                    return self._job_from_row(connection, row)
                raise LeaseConflict("completed job fencing token does not match")
            self._assert_active_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            self._assert_transition_time(row, now_text=now_text)
            connection.execute(
                "UPDATE jobs SET state = 'SUCCEEDED', revision = revision + 1, "
                "active_owner_id = NULL, active_lease_token_hash = NULL, "
                "lease_expires_at = NULL, last_transition_token_hash = ?, "
                "last_failure_code = NULL, updated_at = ?, terminal_at = ? "
                "WHERE job_id = ? AND revision = ? AND state = 'RUNNING'",
                (token_hash, now_text, now_text, str(job_id), expected_revision),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=JobEventType.COMPLETED,
                from_state=JobState.RUNNING,
                to_state=JobState.SUCCEEDED,
                occurred_at=now_text,
                attempt_count=int(row["attempt_count"]),
                owner_id=owner_id,
                failure_code=None,
            )
            self._append_watch_job_outcome(
                connection,
                job_id=job_id,
                state=JobState.SUCCEEDED,
                occurred_at=now_text,
            )
            completed = self._load_job(connection, job_id)
            if completed is None:
                raise CatalogError("completed job did not become visible")
            return completed

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
        """Requeue or terminally fail a running job through fencing proof."""
        self._validate_owner(owner_id)
        self._validate_failure_code(failure_code)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        retry_text = encode_storage_datetime(retry_at) if retry_at is not None else now_text
        if retry_text < now_text:
            raise InvalidJobTransition("retry_at must not precede now")
        if not retryable and retry_at is not None:
            raise InvalidJobTransition("terminal failure cannot specify retry_at")
        with self._write_connection() as connection:
            row = self._required_job_row(connection, job_id)
            if row["state"] in {JobState.QUEUED.value, JobState.FAILED.value}:
                if (
                    row["last_transition_token_hash"] == token_hash
                    and row["last_failure_code"] == failure_code
                ):
                    return self._job_from_row(connection, row)
                raise LeaseConflict("failed job fencing token does not match")
            self._assert_active_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
            )
            if row["cancellation_requested_at"] is not None:
                raise InvalidJobTransition("job cancellation is requested")
            self._assert_transition_time(row, now_text=now_text)
            should_retry = retryable and int(row["attempt_count"]) < int(row["max_attempts"])
            state = JobState.QUEUED if should_retry else JobState.FAILED
            terminal_at = None if should_retry else now_text
            event_type = JobEventType.RETRY_QUEUED if should_retry else JobEventType.FAILED
            connection.execute(
                "UPDATE jobs SET state = ?, revision = revision + 1, available_at = ?, "
                "active_owner_id = NULL, "
                "active_lease_token_hash = NULL, lease_expires_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = ?, updated_at = ?, "
                "terminal_at = ? WHERE job_id = ? AND revision = ? AND state = 'RUNNING'",
                (
                    state.value,
                    retry_text if should_retry else str(row["available_at"]),
                    token_hash,
                    failure_code,
                    now_text,
                    terminal_at,
                    str(job_id),
                    expected_revision,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                from_state=JobState.RUNNING,
                to_state=state,
                occurred_at=now_text,
                attempt_count=int(row["attempt_count"]),
                owner_id=owner_id,
                failure_code=failure_code,
            )
            self._append_watch_job_outcome(
                connection,
                job_id=job_id,
                state=state,
                occurred_at=now_text,
            )
            failed = self._load_job(connection, job_id)
            if failed is None:
                raise CatalogError("failed job did not become visible")
            return failed

    def get_job(self, job_id: UUID) -> Job | None:
        """Return one durable job projection or no result."""
        with self._read_connection() as connection:
            return self._load_job(connection, job_id)

    def list_jobs(
        self,
        *,
        state: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> tuple[Job, ...]:
        """Return deterministic bounded job projections without transition tokens."""
        if type(limit) is not int or not 1 <= limit <= 1_000:
            raise ValueError("job list limit must be between 1 and 1000")
        if state is not None:
            try:
                state_value = JobState(state).value
            except ValueError:
                raise ValueError("job state filter is invalid") from None
        else:
            state_value = None
        clauses: list[str] = []
        parameters: list[Any] = []
        if state_value is not None:
            clauses.append("state = ?")
            parameters.append(state_value)
        if kind is not None:
            if _MACHINE_TOKEN.fullmatch(kind) is None:
                raise ValueError("job kind filter is invalid")
            clauses.append("kind = ?")
            parameters.append(kind)
        query = "SELECT * FROM jobs"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at, job_id LIMIT ?"
        parameters.append(limit)
        with self._read_connection() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
            return tuple(self._job_from_row(connection, row) for row in rows)

    def request_job_cancellation(self, job_id: UUID, *, now: datetime) -> Job:
        """Request queued or running cancellation idempotently with revision fencing."""
        now_text = encode_storage_datetime(now)
        with self._write_connection() as connection:
            row = self._required_job_row(connection, job_id)
            self._assert_transition_time(row, now_text=now_text)
            state = JobState(str(row["state"]))
            if state is JobState.CANCELLED:
                return self._job_from_row(connection, row)
            if state in {JobState.SUCCEEDED, JobState.FAILED}:
                raise InvalidJobTransition("terminal job cannot be cancelled")
            if row["cancellation_requested_at"] is not None:
                return self._job_from_row(connection, row)
            if state is JobState.QUEUED:
                connection.execute(
                    "UPDATE jobs SET state = 'CANCELLED', revision = revision + 1, "
                    "last_transition_token_hash = NULL, last_failure_code = NULL, "
                    "updated_at = ?, terminal_at = ? WHERE job_id = ? AND state = 'QUEUED'",
                    (now_text, now_text, str(job_id)),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type=JobEventType.CANCELLED,
                    from_state=JobState.QUEUED,
                    to_state=JobState.CANCELLED,
                    occurred_at=now_text,
                    attempt_count=int(row["attempt_count"]),
                    owner_id=None,
                    failure_code=None,
                )
                self._append_watch_job_outcome(
                    connection,
                    job_id=job_id,
                    state=JobState.CANCELLED,
                    occurred_at=now_text,
                )
            else:
                connection.execute(
                    "UPDATE jobs SET revision = revision + 1, cancellation_requested_at = ?, "
                    "updated_at = ? WHERE job_id = ? AND state = 'RUNNING' "
                    "AND cancellation_requested_at IS NULL",
                    (now_text, now_text, str(job_id)),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type=JobEventType.CANCEL_REQUESTED,
                    from_state=JobState.RUNNING,
                    to_state=JobState.RUNNING,
                    occurred_at=now_text,
                    attempt_count=int(row["attempt_count"]),
                    owner_id=str(row["active_owner_id"]),
                    failure_code=None,
                )
            changed = self._load_job(connection, job_id)
            if changed is None:
                raise CatalogError("cancelled job did not become visible")
            return changed

    def acknowledge_job_cancellation(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        now: datetime,
    ) -> Job:
        """Acknowledge a running cancellation through the current fenced lease."""
        self._validate_owner(owner_id)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
        with self._write_connection() as connection:
            row = self._required_job_row(connection, job_id)
            if row["state"] == JobState.CANCELLED.value:
                if row["last_transition_token_hash"] == token_hash:
                    return self._job_from_row(connection, row)
                raise LeaseConflict("cancelled job fencing token does not match")
            self._assert_active_lease(
                row,
                owner_id=owner_id,
                token_hash=token_hash,
                expected_revision=expected_revision,
                now_text=now_text,
                allow_cancellation_requested=True,
            )
            if row["cancellation_requested_at"] is None:
                raise InvalidJobTransition("job cancellation is not requested")
            self._assert_transition_time(row, now_text=now_text)
            connection.execute(
                "UPDATE jobs SET state = 'CANCELLED', revision = revision + 1, "
                "active_owner_id = NULL, active_lease_token_hash = NULL, "
                "lease_expires_at = NULL, cancellation_requested_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = NULL, "
                "updated_at = ?, terminal_at = ? WHERE job_id = ? AND revision = ? "
                "AND state = 'RUNNING'",
                (token_hash, now_text, now_text, str(job_id), expected_revision),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=JobEventType.CANCELLED,
                from_state=JobState.RUNNING,
                to_state=JobState.CANCELLED,
                occurred_at=now_text,
                attempt_count=int(row["attempt_count"]),
                owner_id=owner_id,
                failure_code=None,
            )
            self._append_watch_job_outcome(
                connection,
                job_id=job_id,
                state=JobState.CANCELLED,
                occurred_at=now_text,
            )
            cancelled = self._load_job(connection, job_id)
            if cancelled is None:
                raise CatalogError("cancelled job did not become visible")
            return cancelled

    def list_job_events(self, job_id: UUID) -> tuple[JobEvent, ...]:
        """Return append-only transition evidence in sequence order."""
        with self._read_connection() as connection:
            if self._load_job(connection, job_id) is None:
                raise JobNotFound(str(job_id))
            rows = connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY sequence",
                (str(job_id),),
            ).fetchall()
            return tuple(self._event_from_row(row) for row in rows)

    def recover_expired_jobs(self, *, now: datetime) -> RecoveryResult:
        """Requeue or fail every job whose lease is expired at the supplied instant."""
        now_text = encode_storage_datetime(now)
        requeued: list[UUID] = []
        failed: list[UUID] = []
        cancelled: list[UUID] = []
        with self._write_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE state = 'RUNNING' AND lease_expires_at <= ? "
                "ORDER BY job_id",
                (now_text,),
            ).fetchall()
            for row in rows:
                job_id = UUID(str(row["job_id"]))
                cancellation_requested = row["cancellation_requested_at"] is not None
                should_retry = not cancellation_requested and int(row["attempt_count"]) < int(
                    row["max_attempts"]
                )
                state = (
                    JobState.CANCELLED
                    if cancellation_requested
                    else (JobState.QUEUED if should_retry else JobState.FAILED)
                )
                event_type = (
                    JobEventType.CANCELLED
                    if cancellation_requested
                    else (
                        JobEventType.LEASE_RECOVERED
                        if should_retry
                        else JobEventType.LEASE_EXHAUSTED
                    )
                )
                terminal_at = None if should_retry else now_text
                failure_code = None if cancellation_requested else "lease_expired"
                connection.execute(
                    "UPDATE jobs SET state = ?, revision = revision + 1, "
                    "active_owner_id = NULL, active_lease_token_hash = NULL, "
                    "lease_expires_at = NULL, cancellation_requested_at = NULL, "
                    "last_transition_token_hash = ?, last_failure_code = ?, "
                    "updated_at = ?, terminal_at = ? "
                    "WHERE job_id = ? AND state = 'RUNNING' AND lease_expires_at <= ?",
                    (
                        state.value,
                        row["active_lease_token_hash"],
                        failure_code,
                        now_text,
                        terminal_at,
                        str(job_id),
                        now_text,
                    ),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type=event_type,
                    from_state=JobState.RUNNING,
                    to_state=state,
                    occurred_at=now_text,
                    attempt_count=int(row["attempt_count"]),
                    owner_id=str(row["active_owner_id"]),
                    failure_code=failure_code,
                )
                self._append_watch_job_outcome(
                    connection,
                    job_id=job_id,
                    state=state,
                    occurred_at=now_text,
                )
                if cancellation_requested:
                    cancelled.append(job_id)
                else:
                    (requeued if should_retry else failed).append(job_id)
        return RecoveryResult(
            requeued_job_ids=tuple(sorted(requeued, key=str)),
            failed_job_ids=tuple(sorted(failed, key=str)),
            cancelled_job_ids=tuple(sorted(cancelled, key=str)),
            recovered_at=now,
        )

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

    def reference_snapshot(self, *, observed_at: datetime) -> ReferenceSnapshot:
        """Return sorted unique version, job and representation object roots."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT source_object_id AS object_id FROM document_versions "
                "UNION SELECT object_id FROM version_object_references "
                "UNION SELECT object_id FROM job_object_references "
                "UNION SELECT manifest_object_id FROM document_representations "
                "WHERE manifest_object_id IS NOT NULL "
                "UNION SELECT native_object_id FROM document_representations "
                "WHERE native_object_id IS NOT NULL "
                "UNION SELECT object_id FROM representation_blocks "
                "UNION SELECT descriptor_object_id FROM rich_parse_attempts "
                "UNION SELECT provider_native_object_id FROM rich_parse_attempts "
                "UNION SELECT native_record_object_id FROM rich_parse_attempts "
                "UNION SELECT evidence_bundle_object_id FROM rich_parse_attempts "
                "UNION SELECT reference_object_id FROM rich_attempt_evidence "
                "UNION SELECT projection_object_id FROM rich_attempt_evidence "
                "UNION SELECT retrieval_object_id FROM rich_attempt_evidence "
                "UNION SELECT receipt_object_id FROM context_compilations "
                "UNION SELECT bundle_object_id FROM context_compilations "
                "UNION SELECT relation_object_id FROM reconciliation_relations "
                "UNION SELECT record_object_id FROM derivation_nodes "
                "UNION SELECT output_object_id FROM derivation_nodes "
                "WHERE output_object_id IS NOT NULL "
                "UNION SELECT raster_record_object_id FROM visual_page_rasters "
                "UNION SELECT raster_object_id FROM visual_page_rasters "
                "UNION SELECT descriptor_object_id FROM visual_evidence "
                "UNION SELECT crop_object_id FROM visual_evidence "
                "ORDER BY object_id"
            ).fetchall()
            return ReferenceSnapshot(
                object_ids=tuple(str(row[0]) for row in rows),
                observed_at=observed_at,
                catalog_schema_version=self._schema_version_from_connection(connection),
            )

    def search_block_entries(
        self,
        *,
        match: str,
        filters: SearchFilters,
    ) -> SearchMatchPage:
        """Coverage-check scopes, MATCH the FTS index and return one total-ordered page."""
        if not match:
            raise ValueError("match expression is required")
        with self._read_connection() as connection:
            self._assert_in_scope_coverage(connection, filters)
            # Bound optional filters use NULL-sentinel predicates so the SQL text is static.
            current_heads_only = 0 if (filters.include_history or filters.version_id) else 1
            document_id = None if filters.document_id is None else str(filters.document_id)
            kind = None if filters.kind is None else filters.kind.value
            trust = None if filters.trust_zone is None else filters.trust_zone.value
            bound: list[object] = [
                match,
                document_id,
                document_id,
                filters.version_id,
                filters.version_id,
                current_heads_only,
                kind,
                kind,
                trust,
                trust,
                filters.page,
                filters.page,
                filters.slide,
                filters.slide,
            ]
            available = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM block_search_index AS i
                    INNER JOIN block_search_entries AS e ON e.entry_id = i.rowid
                    WHERE block_search_index MATCH ?
                      AND (? IS NULL OR e.document_id = ?)
                      AND (? IS NULL OR e.version_id = ?)
                      AND (? = 0 OR EXISTS (
                            SELECT 1 FROM document_heads AS h
                            WHERE h.document_id = e.document_id
                              AND h.version_id = e.version_id
                              AND h.representation_id = e.representation_id
                      ))
                      AND (? IS NULL OR e.kind = ?)
                      AND (? IS NULL OR e.trust_zone = ?)
                      AND (? IS NULL OR e.page = ?)
                      AND (? IS NULL OR e.slide = ?)
                    """,
                    bound,
                ).fetchone()[0]
            )
            try:
                rows = connection.execute(
                    """
                    SELECT e.entry_id, e.document_id, e.version_id, e.representation_id,
                           e.ordinal, e.block_id, e.kind, e.trust_zone, e.line_start, e.line_end,
                           e.page, e.slide, e.text_hash, bm25(block_search_index) AS rank,
                           b.object_id, o.byte_length
                    FROM block_search_index AS i
                    INNER JOIN block_search_entries AS e ON e.entry_id = i.rowid
                    INNER JOIN representation_blocks AS b
                      ON b.document_id = e.document_id AND b.version_id = e.version_id
                     AND b.representation_id = e.representation_id AND b.ordinal = e.ordinal
                    INNER JOIN objects AS o ON o.object_id = b.object_id
                    WHERE block_search_index MATCH ?
                      AND (? IS NULL OR e.document_id = ?)
                      AND (? IS NULL OR e.version_id = ?)
                      AND (? = 0 OR EXISTS (
                            SELECT 1 FROM document_heads AS h
                            WHERE h.document_id = e.document_id
                              AND h.version_id = e.version_id
                              AND h.representation_id = e.representation_id
                      ))
                      AND (? IS NULL OR e.kind = ?)
                      AND (? IS NULL OR e.trust_zone = ?)
                      AND (? IS NULL OR e.page = ?)
                      AND (? IS NULL OR e.slide = ?)
                    ORDER BY rank ASC, e.document_id ASC, e.ordinal ASC
                    LIMIT ?
                    """,
                    [*bound, filters.limit],
                ).fetchall()
            except sqlite3.OperationalError as error:
                raise CatalogError("search query execution failed") from error
            match_rows = tuple(self._search_match_row(row) for row in rows)
            return SearchMatchPage(
                rows=match_rows,
                available=available,
                limit=filters.limit,
            )

    def index_coverage(
        self,
        *,
        scopes: tuple[RepresentationScope, ...] | None = None,
    ) -> tuple[IndexCoverage, ...]:
        """Return deterministic structural coverage without mutating catalog state."""
        with self._read_connection() as connection:
            selected = scopes if scopes is not None else self._list_ready_scopes(connection)
            reports: list[IndexCoverage] = []
            for scope in selected:
                ready_rows = connection.execute(
                    "SELECT ordinal FROM representation_blocks "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                    "ORDER BY ordinal",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchall()
                indexed_rows = connection.execute(
                    "SELECT ordinal FROM block_search_entries "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                    "ORDER BY ordinal",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchall()
                ready = tuple(int(row["ordinal"]) for row in ready_rows)
                indexed = tuple(int(row["ordinal"]) for row in indexed_rows)
                ready_set = set(ready)
                indexed_set = set(indexed)
                reports.append(
                    IndexCoverage(
                        scope=scope,
                        ready_ordinals=ready,
                        indexed_ordinals=indexed,
                        missing=tuple(sorted(ready_set - indexed_set)),
                        orphaned=tuple(sorted(indexed_set - ready_set)),
                    )
                )
            return tuple(reports)

    def replace_scope_index(
        self,
        scope: RepresentationScope,
        entries: tuple[SearchIndexEntry, ...],
        texts: tuple[str, ...],
        *,
        now: datetime,
    ) -> int:
        """Atomically replace one READY scope's mapping and FTS rows."""
        del now
        if len(entries) != len(texts):
            raise ValueError("entries and texts must have equal length")
        with self._write_connection() as connection:
            row = self._load_representation_row(connection, scope)
            if row is None:
                raise RepresentationNotFound("representation does not exist")
            if str(row["state"]) != RepresentationState.READY.value:
                raise RepresentationIncomplete("representation is not ready")
            for entry in entries:
                if entry.scope != scope:
                    raise RepresentationIntegrityError("index entry scope does not match")
            existing_ids = connection.execute(
                "SELECT entry_id FROM block_search_entries "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            for existing in existing_ids:
                entry_id = int(existing["entry_id"])
                connection.execute(
                    "DELETE FROM block_search_index WHERE rowid = ?",
                    (entry_id,),
                )
            connection.execute(
                "DELETE FROM block_search_entries "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            )
            self._fault_point("after_search_index_delete")
            for entry, text in zip(entries, texts, strict=True):
                self._insert_search_entry(connection, entry, text)
                self._fault_point("after_search_index_entry")
            self._fault_point("after_search_index")
            return len(entries)

    def list_ready_scopes(
        self,
        *,
        document_id: UUID | None = None,
    ) -> tuple[RepresentationScope, ...]:
        """Return READY scopes in deterministic document/version/representation order."""
        with self._read_connection() as connection:
            return self._list_ready_scopes(connection, document_id=document_id)

    def list_scope_index_entries(
        self,
        scope: RepresentationScope,
    ) -> tuple[SearchIndexEntry, ...]:
        """Return stored index mapping rows for one scope in ordinal order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM block_search_entries "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                "ORDER BY ordinal",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            return tuple(self._search_index_entry(row) for row in rows)

    def _list_ready_scopes(
        self,
        connection: sqlite3.Connection,
        *,
        document_id: UUID | None = None,
    ) -> tuple[RepresentationScope, ...]:
        if document_id is None:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations WHERE state = 'READY' "
                "ORDER BY document_id, version_id, representation_id"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations WHERE state = 'READY' AND document_id = ? "
                "ORDER BY document_id, version_id, representation_id",
                (str(document_id),),
            ).fetchall()
        return tuple(
            RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            )
            for row in rows
        )

    def _assert_in_scope_coverage(
        self,
        connection: sqlite3.Connection,
        filters: SearchFilters,
    ) -> None:
        scopes = self._resolve_search_scopes(connection, filters)
        for scope in scopes:
            ready_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM representation_blocks "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchone()[0]
            )
            indexed_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM block_search_entries "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchone()[0]
            )
            if ready_count != indexed_count:
                raise SearchIndexIncomplete("search index coverage is incomplete")
            missing = connection.execute(
                "SELECT b.ordinal FROM representation_blocks AS b "
                "LEFT JOIN block_search_entries AS e "
                "ON e.document_id = b.document_id AND e.version_id = b.version_id "
                "AND e.representation_id = b.representation_id AND e.ordinal = b.ordinal "
                "WHERE b.document_id = ? AND b.version_id = ? AND b.representation_id = ? "
                "AND e.entry_id IS NULL LIMIT 1",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchone()
            if missing is not None:
                raise SearchIndexIncomplete("search index coverage is incomplete")

    def _resolve_search_scopes(
        self,
        connection: sqlite3.Connection,
        filters: SearchFilters,
    ) -> tuple[RepresentationScope, ...]:
        if filters.version_id is not None:
            assert filters.document_id is not None
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations "
                "WHERE state = 'READY' AND document_id = ? AND version_id = ? "
                "ORDER BY representation_id",
                (str(filters.document_id), filters.version_id),
            ).fetchall()
        elif filters.document_id is not None and not filters.include_history:
            rows = connection.execute(
                "SELECT h.document_id, h.version_id, h.representation_id "
                "FROM document_heads AS h "
                "INNER JOIN document_representations AS r "
                "ON r.document_id = h.document_id AND r.version_id = h.version_id "
                "AND r.representation_id = h.representation_id "
                "WHERE h.document_id = ? AND r.state = 'READY'",
                (str(filters.document_id),),
            ).fetchall()
        elif filters.document_id is not None:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations "
                "WHERE state = 'READY' AND document_id = ? "
                "ORDER BY version_id, representation_id",
                (str(filters.document_id),),
            ).fetchall()
        elif not filters.include_history:
            rows = connection.execute(
                "SELECT h.document_id, h.version_id, h.representation_id "
                "FROM document_heads AS h "
                "INNER JOIN document_representations AS r "
                "ON r.document_id = h.document_id AND r.version_id = h.version_id "
                "AND r.representation_id = h.representation_id "
                "WHERE r.state = 'READY' "
                "ORDER BY h.document_id"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations WHERE state = 'READY' "
                "ORDER BY document_id, version_id, representation_id"
            ).fetchall()
        return tuple(
            RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            )
            for row in rows
        )

    def _insert_search_entry(
        self,
        connection: sqlite3.Connection,
        entry: SearchIndexEntry,
        text: str,
    ) -> int:
        cursor = connection.execute(
            "INSERT INTO block_search_entries("
            "document_id, version_id, representation_id, ordinal, block_id, kind, "
            "trust_zone, page, slide, line_start, line_end, text_hash, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(entry.scope.document_id),
                entry.scope.version_id,
                entry.scope.representation_id,
                entry.ordinal,
                str(entry.block_id),
                entry.kind.value,
                entry.trust_zone.value,
                entry.page,
                entry.slide,
                entry.line_start,
                entry.line_end,
                entry.text_hash,
                encode_storage_datetime(entry.indexed_at),
            ),
        )
        if cursor.lastrowid is None:
            raise CatalogError("search index entry insert did not produce a rowid")
        entry_id = int(cursor.lastrowid)
        connection.execute(
            "INSERT INTO block_search_index(rowid, block_text) VALUES (?, ?)",
            (entry_id, text),
        )
        return entry_id

    @staticmethod
    def _search_match_row(row: sqlite3.Row) -> SearchMatchRow:
        return SearchMatchRow(
            entry_id=int(row["entry_id"]),
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            ordinal=int(row["ordinal"]),
            block_id=UUID(str(row["block_id"])),
            kind=BlockKind(str(row["kind"])),
            trust_zone=TrustZone(str(row["trust_zone"])),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
            page=int(row["page"]) if row["page"] is not None else None,
            slide=int(row["slide"]) if row["slide"] is not None else None,
            text_hash=str(row["text_hash"]),
            rank=float(row["rank"]),
            object_id=str(row["object_id"]),
            object_byte_length=int(row["byte_length"]),
        )

    @staticmethod
    def _search_index_entry(row: sqlite3.Row) -> SearchIndexEntry:
        return SearchIndexEntry(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            ordinal=int(row["ordinal"]),
            block_id=UUID(str(row["block_id"])),
            kind=BlockKind(str(row["kind"])),
            trust_zone=TrustZone(str(row["trust_zone"])),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
            page=int(row["page"]) if row["page"] is not None else None,
            slide=int(row["slide"]) if row["slide"] is not None else None,
            text_hash=str(row["text_hash"]),
            indexed_at=decode_storage_datetime(str(row["indexed_at"])),
        )

    @staticmethod
    def _require_fts5_capability(connection: sqlite3.Connection) -> None:
        try:
            connection.execute("CREATE VIRTUAL TABLE temp.fts5_probe USING fts5(x)")
            connection.execute("DROP TABLE temp.fts5_probe")
        except sqlite3.Error as error:
            raise SearchCapabilityUnavailable("SQLite FTS5 capability is unavailable") from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._path,
            timeout=self._busy_timeout_ms / 1000,
            autocommit=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA read_uncommitted = OFF")
        if int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) != 1:
            connection.close()
            raise CatalogError("SQLite foreign keys could not be enabled")
        return connection

    def _configure_persistent_profile(self, connection: sqlite3.Connection) -> None:
        journal_mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0])
        if journal_mode.lower() != "delete":
            raise CatalogError("SQLite rollback journal DELETE mode is required")
        connection.execute("PRAGMA synchronous = EXTRA")
        if int(connection.execute("PRAGMA synchronous").fetchone()[0]) != 3:
            raise CatalogError("SQLite synchronous EXTRA mode is required")

    def _validate_history(self, connection: sqlite3.Connection) -> int:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        if not tables:
            return 0
        if "schema_migrations" not in tables:
            raise CatalogIncompatible("database is not an OpenARDP catalog")
        try:
            rows = connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
        except sqlite3.Error as error:
            raise CatalogIncompatible("catalog migration history is unreadable") from error
        if not rows:
            raise CatalogIncompatible("catalog migration history is empty")
        versions = tuple(int(row["version"]) for row in rows)
        highest = versions[-1]
        if highest > self._migrations[-1].version:
            raise CatalogTooNew("catalog schema is newer than this reader")
        if versions != tuple(range(1, highest + 1)):
            raise CatalogIncompatible("catalog migration history has a gap")
        for row in rows:
            migration = self._migration_by_version.get(int(row["version"]))
            if (
                migration is None
                or row["name"] != migration.name
                or row["checksum"] != migration.checksum
            ):
                raise CatalogIncompatible("catalog migration checksum or name has drifted")
        expected_tables = _SCHEMA_TABLES.get(highest)
        if expected_tables is not None and tables != expected_tables:
            raise CatalogIncompatible("catalog tables do not match migration history")
        return highest

    @contextmanager
    def _optional_write_connection(
        self,
        connection: sqlite3.Connection | None,
    ) -> Iterator[sqlite3.Connection]:
        """Reuse one caller-owned transaction or open the normal write boundary."""
        if connection is not None:
            yield connection
            return
        with self._write_connection() as opened:
            yield opened

    @contextmanager
    def _write_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        transaction_started = False
        try:
            current = self._validate_history(connection)
            if current != self._migrations[-1].version:
                raise CatalogIncompatible("catalog must be initialized to the current revision")
            self._configure_persistent_profile(connection)
            connection.execute("BEGIN IMMEDIATE")
            transaction_started = True
            yield connection
            connection.execute("COMMIT")
            transaction_started = False
        except (CatalogError, RuntimeError, ValueError):
            if transaction_started:
                connection.execute("ROLLBACK")
            raise
        except sqlite3.Error as error:
            if transaction_started:
                connection.execute("ROLLBACK")
            raise CatalogError("catalog transaction failed") from error
        except Exception:
            if transaction_started:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @contextmanager
    def _read_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        transaction_started = False
        try:
            current = self._validate_history(connection)
            if current != self._migrations[-1].version:
                raise CatalogIncompatible("catalog must be initialized to the current revision")
            self._configure_persistent_profile(connection)
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            transaction_started = True
            yield connection
            connection.execute("COMMIT")
            transaction_started = False
        finally:
            if transaction_started:
                connection.execute("ROLLBACK")
            connection.close()

    def _load_document_by_source(
        self,
        connection: sqlite3.Connection,
        source_key: SourceKey,
    ) -> LogicalDocument | None:
        row = connection.execute(
            "SELECT * FROM documents WHERE connector = ? AND source_locator = ?",
            (source_key.connector, source_key.locator),
        ).fetchone()
        return self._document_from_row(row) if row is not None else None

    def _load_document_by_id(
        self,
        connection: sqlite3.Connection,
        document_id: UUID,
    ) -> LogicalDocument | None:
        row = connection.execute(
            "SELECT * FROM documents WHERE document_id = ?", (str(document_id),)
        ).fetchone()
        return self._document_from_row(row) if row is not None else None

    @staticmethod
    def _document_from_row(row: sqlite3.Row) -> LogicalDocument:
        return LogicalDocument(
            document_id=UUID(str(row["document_id"])),
            source_key=SourceKey(
                connector=str(row["connector"]),
                locator=str(row["source_locator"]),
            ),
            created_at=decode_storage_datetime(str(row["created_at"])),
        )

    def _load_version(
        self,
        connection: sqlite3.Connection,
        document_id: UUID,
        version_id: str,
    ) -> DocumentVersion | None:
        row = connection.execute(
            "SELECT v.*, o.byte_length FROM document_versions AS v "
            "JOIN objects AS o ON o.object_id = v.source_object_id "
            "WHERE v.document_id = ? AND v.version_id = ?",
            (str(document_id), version_id),
        ).fetchone()
        if row is None:
            return None
        reference_rows = connection.execute(
            "SELECT r.*, o.byte_length FROM version_object_references AS r "
            "JOIN objects AS o ON o.object_id = r.object_id "
            "WHERE r.document_id = ? AND r.version_id = ? ORDER BY r.role, r.ordinal",
            (str(document_id), version_id),
        ).fetchall()
        references = tuple(self._reference_from_row(item) for item in reference_rows)
        modified = row["source_modified_at"]
        return DocumentVersion(
            document_id=UUID(str(row["document_id"])),
            version_id=str(row["version_id"]),
            source=StoredObject(
                object_id=str(row["source_object_id"]),
                byte_length=int(row["byte_length"]),
            ),
            media_type=str(row["media_type"]),
            source_modified_at=(
                decode_storage_datetime(str(modified)) if modified is not None else None
            ),
            references=references,
            committed_at=decode_storage_datetime(str(row["committed_at"])),
        )

    @staticmethod
    def _reference_from_row(row: sqlite3.Row) -> ObjectReference:
        return ObjectReference(
            role=str(row["role"]),
            ordinal=int(row["ordinal"]),
            object_id=str(row["object_id"]),
            byte_length=int(row["byte_length"]),
            media_type=(str(row["media_type"]) if row["media_type"] is not None else None),
        )

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
            "SELECT object_id FROM representation_blocks WHERE document_id = ? "
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
            "JOIN representation_blocks AS b ON b.document_id = m.document_id "
            "AND b.version_id = m.version_id AND b.representation_id = m.representation_id "
            "AND b.block_id = m.block_id WHERE m.document_id = ? AND m.version_id = ? "
            "AND m.representation_id = ? ORDER BY b.ordinal",
            (str(document_id), current_scope.version_id, current_scope.representation_id),
        ).fetchall()
        seed_rows = connection.execute(
            "SELECT m.* FROM block_lineage_members AS m "
            "JOIN representation_blocks AS b ON b.document_id = m.document_id "
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
            "JOIN representation_blocks AS cb ON cb.document_id = r.document_id "
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

    def _register_object(
        self,
        connection: sqlite3.Connection,
        value: StoredObject | ObjectReference,
        *,
        registered_at: str,
    ) -> None:
        connection.execute(
            "INSERT INTO objects(object_id, byte_length, registered_at) VALUES (?, ?, ?) "
            "ON CONFLICT(object_id) DO NOTHING",
            (value.object_id, value.byte_length, registered_at),
        )
        row = connection.execute(
            "SELECT byte_length FROM objects WHERE object_id = ?", (value.object_id,)
        ).fetchone()
        if row is None or int(row[0]) != value.byte_length:
            raise InvalidObjectReference("object identity has conflicting immutable length")

    @staticmethod
    def _document_version_from_commit(commit: SourceVersionCommit) -> DocumentVersion:
        return DocumentVersion(
            document_id=commit.document_id,
            version_id=commit.version_id,
            source=commit.source,
            media_type=commit.media_type,
            source_modified_at=commit.source_modified_at,
            references=commit.references,
            committed_at=commit.committed_at,
        )

    @staticmethod
    def _versions_equivalent(left: DocumentVersion, right: DocumentVersion) -> bool:
        return (
            left.document_id == right.document_id
            and left.version_id == right.version_id
            and left.source == right.source
            and left.media_type == right.media_type
            and left.source_modified_at == right.source_modified_at
            and SQLiteCatalog._canonical_references(left.references)
            == SQLiteCatalog._canonical_references(right.references)
        )

    @staticmethod
    def _canonical_references(
        references: tuple[ObjectReference, ...],
    ) -> tuple[ObjectReference, ...]:
        return tuple(sorted(references, key=lambda item: (item.role, item.ordinal)))

    @staticmethod
    def _validate_representation_identity(
        scope: RepresentationScope,
        recipe: ParserRecipe,
    ) -> None:
        if recipe.representation_id_for(scope.version_id) != scope.representation_id:
            raise RepresentationConflict("representation recipe identity does not match scope")

    def _load_representation_row(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT r.*, mo.byte_length AS manifest_byte_length, "
                "no.byte_length AS native_byte_length FROM document_representations AS r "
                "LEFT JOIN objects AS mo ON mo.object_id = r.manifest_object_id "
                "LEFT JOIN objects AS no ON no.object_id = r.native_object_id "
                "WHERE r.document_id = ? AND r.version_id = ? AND r.representation_id = ?",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchone(),
        )

    def _required_representation_row(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> sqlite3.Row:
        row = self._load_representation_row(connection, scope)
        if row is None:
            raise RepresentationNotFound("representation does not exist")
        return row

    def _representation_from_row(self, row: sqlite3.Row) -> DocumentRepresentation:
        manifest_id = row["manifest_object_id"]
        native_id = row["native_object_id"]
        ready_at = row["ready_at"]
        lease_expires_at = row["lease_expires_at"]
        return DocumentRepresentation(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            recipe=ParserRecipe(
                name=str(row["parser_name"]),
                version=str(row["parser_version"]),
                profile=str(row["parser_profile"]),
                config_hash=str(row["parser_config_hash"]),
                normalization_schema_version=str(row["normalization_schema_version"]),
            ),
            state=RepresentationState(str(row["state"])),
            attempt_count=int(row["attempt_count"]),
            revision=int(row["revision"]),
            active_owner_id=(
                str(row["active_owner_id"]) if row["active_owner_id"] is not None else None
            ),
            lease_expires_at=(
                decode_storage_datetime(str(lease_expires_at))
                if lease_expires_at is not None
                else None
            ),
            last_failure_code=(
                str(row["last_failure_code"]) if row["last_failure_code"] is not None else None
            ),
            manifest_object=(
                StoredObject(
                    object_id=str(manifest_id),
                    byte_length=int(row["manifest_byte_length"]),
                )
                if manifest_id is not None and row["manifest_byte_length"] is not None
                else None
            ),
            native_object=(
                StoredObject(
                    object_id=str(native_id),
                    byte_length=int(row["native_byte_length"]),
                )
                if native_id is not None and row["native_byte_length"] is not None
                else None
            ),
            block_count=int(row["block_count"]),
            warning_codes=self._warning_codes(str(row["warning_codes_json"])),
            created_at=decode_storage_datetime(str(row["created_at"])),
            updated_at=decode_storage_datetime(str(row["updated_at"])),
            ready_at=(decode_storage_datetime(str(ready_at)) if ready_at is not None else None),
        )

    def _representation_aggregate(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> RepresentationAggregate:
        representation = self._representation_from_row(row)
        block_rows = connection.execute(
            "SELECT b.*, o.byte_length FROM representation_blocks AS b "
            "JOIN objects AS o ON o.object_id = b.object_id WHERE b.document_id = ? "
            "AND b.version_id = ? AND b.representation_id = ? ORDER BY b.ordinal",
            (
                str(representation.scope.document_id),
                representation.scope.version_id,
                representation.scope.representation_id,
            ),
        ).fetchall()
        blocks = tuple(self._block_projection_from_row(item) for item in block_rows)
        try:
            return RepresentationAggregate(representation=representation, blocks=blocks)
        except ValueError as error:
            raise RepresentationIntegrityError(
                "representation projection is inconsistent"
            ) from error

    def _required_representation(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> RepresentationAggregate:
        return self._representation_aggregate(
            connection,
            self._required_representation_row(connection, scope),
        )

    def _persist_rich_attempt(
        self,
        connection: sqlite3.Connection,
        commit: RichAttemptCommit,
        *,
        event_sequence: int,
    ) -> None:
        existing = self._load_rich_attempt_commit(connection, commit.attempt.attempt_id)
        if existing is not None:
            if existing != commit:
                raise RepresentationConflict("rich attempt identity has conflicting facts")
            existing_event = self._rich_attempt_event(connection, commit.attempt.attempt_id)
            if existing_event.sequence != event_sequence:
                raise RepresentationConflict("rich attempt event differs from candidate")
            return

        created_at = encode_storage_datetime(commit.attempt.created_at)
        objects = (
            commit.attempt.descriptor_object,
            commit.attempt.provider_native_object,
            commit.attempt.native_record_object,
            commit.attempt.evidence_bundle_object,
            *(
                value
                for record in commit.bundle.records
                for value in (
                    record.reference_object,
                    record.projection_object,
                    record.retrieval_object,
                )
            ),
        )
        for value in objects:
            self._register_object(connection, value, registered_at=created_at)
        self._fault_point("after_rich_objects")

        attempt_json = canonical_json_bytes(commit.attempt.model_dump(mode="json")).decode("utf-8")
        bundle_json = commit.bundle.canonical_bytes.decode("utf-8")
        attempt = commit.attempt
        connection.execute(
            "INSERT INTO rich_parse_attempts("
            "attempt_id, document_id, version_id, representation_id, outcome, "
            "descriptor_object_id, provider_native_object_id, native_record_object_id, "
            "evidence_bundle_object_id, projection_count, attempt_json, bundle_json, "
            "event_sequence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(attempt.attempt_id),
                str(attempt.scope.document_id),
                attempt.scope.version_id,
                attempt.scope.representation_id,
                attempt.outcome.value,
                attempt.descriptor_object.object_id,
                attempt.provider_native_object.object_id,
                attempt.native_record_object.object_id,
                attempt.evidence_bundle_object.object_id,
                attempt.projection_count,
                attempt_json,
                bundle_json,
                event_sequence,
                created_at,
            ),
        )
        for record in commit.bundle.records:
            connection.execute(
                "INSERT INTO rich_attempt_evidence("
                "attempt_id, ordinal, reference_object_id, projection_object_id, "
                "retrieval_object_id) VALUES (?, ?, ?, ?, ?)",
                (
                    str(attempt.attempt_id),
                    record.ordinal,
                    record.reference_object.object_id,
                    record.projection_object.object_id,
                    record.retrieval_object.object_id,
                ),
            )
            self._fault_point("after_rich_evidence")

    def _load_rich_attempt_commit(
        self,
        connection: sqlite3.Connection,
        attempt_id: UUID,
    ) -> RichAttemptCommit | None:
        row = connection.execute(
            "SELECT * FROM rich_parse_attempts WHERE attempt_id = ?",
            (str(attempt_id),),
        ).fetchone()
        if row is None:
            return None
        try:
            commit = RichAttemptCommit(
                attempt=RichParseAttempt.model_validate_json(str(row["attempt_json"])),
                bundle=RichEvidenceBundle.model_validate_json(str(row["bundle_json"])),
            )
        except ValueError as error:
            raise RepresentationIntegrityError("rich attempt metadata is invalid") from error
        attempt = commit.attempt
        expected_row = (
            str(attempt.attempt_id),
            str(attempt.scope.document_id),
            attempt.scope.version_id,
            attempt.scope.representation_id,
            attempt.outcome.value,
            attempt.descriptor_object.object_id,
            attempt.provider_native_object.object_id,
            attempt.native_record_object.object_id,
            attempt.evidence_bundle_object.object_id,
            attempt.projection_count,
            encode_storage_datetime(attempt.created_at),
        )
        observed_row = (
            str(row["attempt_id"]),
            str(row["document_id"]),
            str(row["version_id"]),
            str(row["representation_id"]),
            str(row["outcome"]),
            str(row["descriptor_object_id"]),
            str(row["provider_native_object_id"]),
            str(row["native_record_object_id"]),
            str(row["evidence_bundle_object_id"]),
            int(row["projection_count"]),
            str(row["created_at"]),
        )
        if (
            observed_row != expected_row
            or str(row["attempt_json"]).encode("utf-8")
            != canonical_json_bytes(attempt.model_dump(mode="json"))
            or str(row["bundle_json"]).encode("utf-8") != commit.bundle.canonical_bytes
        ):
            raise RepresentationIntegrityError("rich attempt catalog facts are inconsistent")
        evidence = connection.execute(
            "SELECT ordinal, reference_object_id, projection_object_id, retrieval_object_id "
            "FROM rich_attempt_evidence WHERE attempt_id = ? ORDER BY ordinal",
            (str(attempt_id),),
        ).fetchall()
        expected = tuple(
            (
                record.ordinal,
                record.reference_object.object_id,
                record.projection_object.object_id,
                record.retrieval_object.object_id,
            )
            for record in commit.bundle.records
        )
        observed = tuple(
            (
                int(item["ordinal"]),
                str(item["reference_object_id"]),
                str(item["projection_object_id"]),
                str(item["retrieval_object_id"]),
            )
            for item in evidence
        )
        if observed != expected:
            raise RepresentationIntegrityError("rich attempt evidence inventory is incomplete")
        return commit

    def _rich_representation(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts | None:
        row = connection.execute(
            "SELECT accepted_attempt_id FROM rich_accepted_representations "
            "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
            (str(scope.document_id), scope.version_id, scope.representation_id),
        ).fetchone()
        if row is None:
            return None
        accepted_id = UUID(str(row["accepted_attempt_id"]))
        commit = self._load_rich_attempt_commit(connection, accepted_id)
        if commit is None:
            raise RepresentationIntegrityError("accepted rich attempt is missing")
        aggregate = self._required_representation(connection, scope)
        try:
            return RichRepresentationArtifacts(
                aggregate=aggregate,
                accepted_attempt_id=accepted_id,
                accepted_attempt=commit.attempt,
                bundle=commit.bundle,
            )
        except ValueError as error:
            raise RepresentationIntegrityError(
                "accepted rich representation is inconsistent"
            ) from error

    def _required_rich_representation(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts:
        artifacts = self._rich_representation(connection, scope)
        if artifacts is None:
            raise RepresentationIncomplete("rich representation is not complete")
        return artifacts

    def _required_accepted_attempt_id(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> UUID:
        row = connection.execute(
            "SELECT accepted_attempt_id FROM rich_accepted_representations "
            "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
            (str(scope.document_id), scope.version_id, scope.representation_id),
        ).fetchone()
        if row is None:
            raise RepresentationIncomplete("accepted rich attempt does not exist")
        return UUID(str(row["accepted_attempt_id"]))

    def _rich_attempt_event(
        self,
        connection: sqlite3.Connection,
        attempt_id: UUID,
    ) -> IngestionEvent:
        row = connection.execute(
            "SELECT e.* FROM rich_parse_attempts AS a "
            "JOIN ingestion_events AS e ON e.document_id = a.document_id "
            "AND e.sequence = a.event_sequence WHERE a.attempt_id = ?",
            (str(attempt_id),),
        ).fetchone()
        if row is None:
            raise RepresentationIntegrityError("rich attempt event is missing")
        return self._ingestion_event_from_row(row)

    @staticmethod
    def _block_projection_from_row(row: sqlite3.Row) -> RepresentationBlock:
        return RepresentationBlock(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            block_id=UUID(str(row["block_id"])),
            object=StoredObject(
                object_id=str(row["object_id"]),
                byte_length=int(row["byte_length"]),
            ),
            ordinal=int(row["ordinal"]),
            parent_id=(UUID(str(row["parent_id"])) if row["parent_id"] is not None else None),
            kind=BlockKind(str(row["kind"])),
            order=int(row["sibling_order"]),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
        )

    @staticmethod
    def _warning_codes(payload: str) -> tuple[str, ...]:
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as error:
            raise RepresentationIntegrityError(
                "representation warning metadata is invalid"
            ) from error
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) for item in value)
            or value != sorted(set(value))
        ):
            raise RepresentationIntegrityError("representation warning metadata is invalid")
        return tuple(value)

    @staticmethod
    def _assert_row_recipe(row: sqlite3.Row, recipe: ParserRecipe) -> None:
        actual = (
            str(row["parser_name"]),
            str(row["parser_version"]),
            str(row["parser_profile"]),
            str(row["parser_config_hash"]),
            str(row["normalization_schema_version"]),
        )
        expected = (
            recipe.name,
            recipe.version,
            recipe.profile,
            recipe.config_hash,
            recipe.normalization_schema_version,
        )
        if actual != expected:
            raise RepresentationConflict("representation recipe differs from persisted facts")

    @staticmethod
    def _ready_aggregate_matches(
        aggregate: RepresentationAggregate,
        commit: ReadyRepresentationCommit,
    ) -> bool:
        representation = aggregate.representation
        expected_blocks = tuple(
            RepresentationBlock(
                scope=commit.scope,
                block_id=item.block.block_id,
                object=item.object,
                ordinal=item.ordinal,
                parent_id=item.block.parent_id,
                kind=item.block.kind,
                order=item.block.order,
                line_start=item.line_start,
                line_end=item.line_end,
            )
            for item in commit.blocks
        )
        return (
            representation.scope == commit.scope
            and representation.recipe == commit.recipe
            and representation.state is RepresentationState.READY
            and representation.manifest_object == commit.manifest_object
            and representation.native_object == commit.native_object
            and representation.block_count == len(commit.blocks)
            and representation.warning_codes == commit.warning_codes
            and aggregate.blocks == expected_blocks
        )

    @staticmethod
    def _validate_representation_owner(owner_id: str) -> None:
        if _OWNER.fullmatch(owner_id) is None:
            raise RepresentationLeaseConflict("representation owner identifier is invalid")

    @staticmethod
    def _representation_token_hash(lease_token: str) -> str:
        if not isinstance(lease_token, str) or len(lease_token) < _MIN_LEASE_TOKEN_LENGTH:
            raise RepresentationLeaseConflict("representation lease token is too short")
        return "sha256:" + hashlib.sha256(lease_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _assert_representation_lease(
        row: sqlite3.Row,
        *,
        owner_id: str,
        token_hash: str,
        expected_revision: int,
        now_text: str,
    ) -> None:
        if row["state"] != RepresentationState.STAGING.value:
            raise RepresentationLeaseConflict("representation is not staging")
        if row["active_owner_id"] != owner_id or row["active_lease_token_hash"] != token_hash:
            raise RepresentationLeaseConflict("representation lease owner or token does not match")
        if str(row["lease_expires_at"]) <= now_text:
            raise RepresentationLeaseConflict("representation lease has expired")
        if int(row["revision"]) != expected_revision:
            raise RepresentationLeaseConflict("representation revision is stale")

    def _advance_head_and_event(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
        *,
        source_observed_at: str,
        ingested_at: str,
        disposition: IngestionDisposition,
        parser_invoked: bool,
    ) -> tuple[DocumentHead, IngestionEvent]:
        if ingested_at < source_observed_at:
            raise RepresentationConflict("ingestion time precedes source observation")
        row = connection.execute(
            "SELECT * FROM document_heads WHERE document_id = ?",
            (str(scope.document_id),),
        ).fetchone()
        head_advanced = False
        if row is None:
            connection.execute(
                "INSERT INTO document_heads(document_id, version_id, representation_id, "
                "source_observed_at, last_ingested_at, last_disposition, revision) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (
                    str(scope.document_id),
                    scope.version_id,
                    scope.representation_id,
                    source_observed_at,
                    ingested_at,
                    disposition.value,
                ),
            )
            head_advanced = True
        else:
            current_scope = self._head_from_row(row).scope
            current_observed = str(row["source_observed_at"])
            if source_observed_at == current_observed and scope != current_scope:
                raise RepresentationConflict("equal source observation has different scope")
            should_update = source_observed_at > current_observed or (
                source_observed_at == current_observed
                and scope == current_scope
                and ingested_at > str(row["last_ingested_at"])
            )
            if should_update:
                connection.execute(
                    "UPDATE document_heads SET version_id = ?, representation_id = ?, "
                    "source_observed_at = ?, last_ingested_at = ?, last_disposition = ?, "
                    "revision = revision + 1 WHERE document_id = ?",
                    (
                        scope.version_id,
                        scope.representation_id,
                        source_observed_at,
                        ingested_at,
                        disposition.value,
                        str(scope.document_id),
                    ),
                )
                head_advanced = True
        self._fault_point("after_document_head")
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM ingestion_events WHERE document_id = ?",
                (str(scope.document_id),),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO ingestion_events(document_id, sequence, version_id, "
            "representation_id, disposition, parser_invoked, head_advanced, occurred_at, "
            "source_observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(scope.document_id),
                sequence,
                scope.version_id,
                scope.representation_id,
                disposition.value,
                int(parser_invoked),
                int(head_advanced),
                ingested_at,
                source_observed_at,
            ),
        )
        self._fault_point("after_ingestion_event")
        head = self._required_document_head(connection, scope.document_id)
        event_row = connection.execute(
            "SELECT * FROM ingestion_events WHERE document_id = ? AND sequence = ?",
            (str(scope.document_id), sequence),
        ).fetchone()
        if event_row is None:
            raise CatalogError("ingestion event did not become visible")
        return head, self._ingestion_event_from_row(event_row)

    def _append_ingestion_event_without_head(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
        *,
        source_observed_at: str,
        ingested_at: str,
        disposition: IngestionDisposition,
    ) -> IngestionEvent:
        """Append a parser-invoked observation while preserving the current head."""
        if ingested_at < source_observed_at:
            raise RepresentationConflict("ingestion time precedes source observation")
        self._required_rich_representation(connection, scope)
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM ingestion_events WHERE document_id = ?",
                (str(scope.document_id),),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO ingestion_events(document_id, sequence, version_id, "
            "representation_id, disposition, parser_invoked, head_advanced, occurred_at, "
            "source_observed_at) VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)",
            (
                str(scope.document_id),
                sequence,
                scope.version_id,
                scope.representation_id,
                disposition.value,
                ingested_at,
                source_observed_at,
            ),
        )
        row = connection.execute(
            "SELECT * FROM ingestion_events WHERE document_id = ? AND sequence = ?",
            (str(scope.document_id), sequence),
        ).fetchone()
        if row is None:
            raise CatalogError("ingestion event did not become visible")
        self._fault_point("after_ingestion_event")
        return self._ingestion_event_from_row(row)

    def _required_document_head(
        self,
        connection: sqlite3.Connection,
        document_id: UUID,
    ) -> DocumentHead:
        row = connection.execute(
            "SELECT * FROM document_heads WHERE document_id = ?",
            (str(document_id),),
        ).fetchone()
        if row is None:
            raise RepresentationIncomplete("document head does not exist")
        return self._head_from_row(row)

    @staticmethod
    def _head_from_row(row: sqlite3.Row) -> DocumentHead:
        return DocumentHead(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            source_observed_at=decode_storage_datetime(str(row["source_observed_at"])),
            last_ingested_at=decode_storage_datetime(str(row["last_ingested_at"])),
            last_disposition=IngestionDisposition(str(row["last_disposition"])),
            revision=int(row["revision"]),
        )

    @staticmethod
    def _ingestion_event_from_row(row: sqlite3.Row) -> IngestionEvent:
        scope = RepresentationScope(
            document_id=UUID(str(row["document_id"])),
            version_id=str(row["version_id"]),
            representation_id=str(row["representation_id"]),
        )
        return IngestionEvent(
            document_id=scope.document_id,
            sequence=int(row["sequence"]),
            scope=scope,
            disposition=IngestionDisposition(str(row["disposition"])),
            parser_invoked=bool(row["parser_invoked"]),
            head_advanced=bool(row["head_advanced"]),
            occurred_at=decode_storage_datetime(str(row["occurred_at"])),
            source_observed_at=decode_storage_datetime(str(row["source_observed_at"])),
        )

    def _last_scope_event(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
    ) -> IngestionEvent:
        row = connection.execute(
            "SELECT * FROM ingestion_events WHERE document_id = ? AND version_id = ? "
            "AND representation_id = ? AND parser_invoked = 1 ORDER BY sequence DESC LIMIT 1",
            (str(scope.document_id), scope.version_id, scope.representation_id),
        ).fetchone()
        if row is None:
            raise RepresentationIncomplete("representation commit event is missing")
        return self._ingestion_event_from_row(row)

    def _load_watch_root(
        self,
        connection: sqlite3.Connection,
        root_id: str,
    ) -> WatchRoot | None:
        row = connection.execute(
            "SELECT * FROM watch_roots WHERE root_id = ?", (root_id,)
        ).fetchone()
        return self._watch_root_from_row(row) if row is not None else None

    @staticmethod
    def _watch_root_from_row(row: sqlite3.Row) -> WatchRoot:
        config = WatchConfig.model_validate_json(str(row["config_json"]))
        authority = AdmittedWatchRoot(
            root_id=str(row["root_id"]),
            root_path=str(row["root_path"]),
            root_path_digest=str(row["root_path_digest"]),
            device_id=str(row["device_id"]),
            file_id=str(row["file_id"]),
            config=config,
        )
        if str(row["config_hash"]) != config.config_hash:
            raise CatalogIncompatible("watch root config identity is inconsistent")
        return WatchRoot(
            authority=authority,
            generation=int(row["generation"]),
            rescan_required=bool(row["rescan_required"]),
            created_at=decode_storage_datetime(str(row["created_at"])),
            updated_at=decode_storage_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _required_watch_root_row(
        connection: sqlite3.Connection,
        root_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM watch_roots WHERE root_id = ?", (root_id,)
        ).fetchone()
        if row is None:
            raise JobNotFound("watch root does not exist")
        return cast(sqlite3.Row, row)

    @staticmethod
    def _make_watch_observation(
        *,
        root_id: str,
        relative_locator: str,
        locator_digest: str,
        state: WatchObservationState,
        fingerprint: WatchFileFingerprint | None,
        first_observed_at: datetime,
        last_observed_at: datetime,
        stable_since: datetime | None,
        last_generation: int,
        last_scheduled_key: str | None,
        revision: int,
    ) -> WatchObservation:
        values: dict[str, Any] = {
            "root_id": root_id,
            "relative_locator": relative_locator,
            "locator_digest": locator_digest,
            "state": state,
            "fingerprint": fingerprint,
            "first_observed_at": first_observed_at,
            "last_observed_at": last_observed_at,
            "stable_since": stable_since,
            "last_generation": last_generation,
            "last_scheduled_key": last_scheduled_key,
            "revision": revision,
        }
        provisional = WatchObservation.model_construct(
            **values,
            row_fingerprint="sha256:" + "0" * 64,
        )
        values["row_fingerprint"] = watch_observation_fingerprint(provisional)
        return WatchObservation.model_validate(values)

    @staticmethod
    def _observation_fingerprint_with_update(
        observation: WatchObservation,
        *,
        last_scheduled_key: str,
    ) -> str:
        updated = observation.model_copy(update={"last_scheduled_key": last_scheduled_key})
        return watch_observation_fingerprint(updated)

    @staticmethod
    def _write_watch_observation(
        connection: sqlite3.Connection,
        observation: WatchObservation,
    ) -> None:
        fingerprint_json = (
            canonical_json_bytes(observation.fingerprint.model_dump(mode="json")).decode("utf-8")
            if observation.fingerprint is not None
            else None
        )
        connection.execute(
            "INSERT INTO watch_observations("
            "root_id, locator_digest, relative_locator, state, fingerprint_json, "
            "first_observed_at, last_observed_at, stable_since, last_generation, "
            "last_scheduled_key, revision, row_fingerprint"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(root_id, locator_digest) DO UPDATE SET "
            "relative_locator = excluded.relative_locator, state = excluded.state, "
            "fingerprint_json = excluded.fingerprint_json, "
            "first_observed_at = excluded.first_observed_at, "
            "last_observed_at = excluded.last_observed_at, "
            "stable_since = excluded.stable_since, last_generation = excluded.last_generation, "
            "last_scheduled_key = excluded.last_scheduled_key, revision = excluded.revision, "
            "row_fingerprint = excluded.row_fingerprint",
            (
                observation.root_id,
                observation.locator_digest,
                observation.relative_locator,
                observation.state.value,
                fingerprint_json,
                encode_storage_datetime(observation.first_observed_at),
                encode_storage_datetime(observation.last_observed_at),
                (
                    encode_storage_datetime(observation.stable_since)
                    if observation.stable_since is not None
                    else None
                ),
                observation.last_generation,
                observation.last_scheduled_key,
                observation.revision,
                observation.row_fingerprint,
            ),
        )

    @staticmethod
    def _watch_observation_from_row(row: sqlite3.Row) -> WatchObservation:
        fingerprint = (
            WatchFileFingerprint.model_validate_json(str(row["fingerprint_json"]))
            if row["fingerprint_json"] is not None
            else None
        )
        return WatchObservation(
            root_id=str(row["root_id"]),
            relative_locator=str(row["relative_locator"]),
            locator_digest=str(row["locator_digest"]),
            state=WatchObservationState(str(row["state"])),
            fingerprint=fingerprint,
            first_observed_at=decode_storage_datetime(str(row["first_observed_at"])),
            last_observed_at=decode_storage_datetime(str(row["last_observed_at"])),
            stable_since=(
                decode_storage_datetime(str(row["stable_since"]))
                if row["stable_since"] is not None
                else None
            ),
            last_generation=int(row["last_generation"]),
            last_scheduled_key=(
                str(row["last_scheduled_key"]) if row["last_scheduled_key"] is not None else None
            ),
            revision=int(row["revision"]),
            row_fingerprint=str(row["row_fingerprint"]),
        )

    def _create_watch_job_and_target(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: UUID,
        root_id: str,
        entry: WatchScanEntry,
        parser_profile: str,
        deduplication_key: str,
        max_attempts: int,
        created_at: datetime,
    ) -> Job:
        created_text = encode_storage_datetime(created_at)
        row = connection.execute(
            "SELECT * FROM jobs WHERE kind = 'watch_ingest' AND deduplication_key = ?",
            (deduplication_key,),
        ).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO jobs("
                "job_id, kind, deduplication_key, state, attempt_count, max_attempts, revision, "
                "available_at, active_owner_id, active_lease_token_hash, lease_expires_at, "
                "cancellation_requested_at, last_transition_token_hash, last_failure_code, "
                "created_at, updated_at, terminal_at) VALUES "
                "(?, 'watch_ingest', ?, 'QUEUED', 0, ?, 0, ?, NULL, NULL, NULL, NULL, NULL, "
                "NULL, ?, ?, NULL)",
                (
                    str(job_id),
                    deduplication_key,
                    max_attempts,
                    created_text,
                    created_text,
                    created_text,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=JobEventType.ENQUEUED,
                from_state=None,
                to_state=JobState.QUEUED,
                occurred_at=created_text,
                attempt_count=0,
                owner_id=None,
                failure_code=None,
            )
            self._fault_point("after_watch_job")
            row = self._required_job_row(connection, job_id)
        job = self._job_from_row(connection, row)
        if (
            job.job_id != job_id
            or job.kind != "watch_ingest"
            or job.deduplication_key != deduplication_key
            or job.max_attempts != max_attempts
        ):
            raise JobConflict("watch job identity has conflicting immutable facts")
        target = WatchJobTarget(
            job_id=job_id,
            root_id=root_id,
            relative_locator=str(entry.relative_locator),
            locator_digest=str(entry.locator_digest),
            fingerprint=entry.fingerprint,
            parser_profile=parser_profile,
            deduplication_key=deduplication_key,
            created_at=created_at,
        )
        fingerprint_json = canonical_json_bytes(target.fingerprint.model_dump(mode="json")).decode(
            "utf-8"
        )
        existing_target = connection.execute(
            "SELECT * FROM watch_job_targets WHERE job_id = ?", (str(job_id),)
        ).fetchone()
        if existing_target is None:
            connection.execute(
                "INSERT INTO watch_job_targets("
                "job_id, root_id, locator_digest, relative_locator, fingerprint_json, "
                "parser_profile, deduplication_key, created_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(job_id),
                    root_id,
                    target.locator_digest,
                    target.relative_locator,
                    fingerprint_json,
                    parser_profile,
                    deduplication_key,
                    created_text,
                ),
            )
            self._fault_point("after_watch_target")
        elif self._watch_target_from_row(existing_target) != target:
            raise JobConflict("watch target identity has conflicting immutable facts")
        return job

    @staticmethod
    def _watch_target_from_row(row: sqlite3.Row) -> WatchJobTarget:
        return WatchJobTarget(
            job_id=UUID(str(row["job_id"])),
            root_id=str(row["root_id"]),
            relative_locator=str(row["relative_locator"]),
            locator_digest=str(row["locator_digest"]),
            fingerprint=WatchFileFingerprint.model_validate_json(str(row["fingerprint_json"])),
            parser_profile=str(row["parser_profile"]),
            deduplication_key=str(row["deduplication_key"]),
            created_at=decode_storage_datetime(str(row["created_at"])),
        )

    def _append_watch_event(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        event_type: WatchEventType,
        generation: int,
        occurred_at: str,
        locator_digest: str | None = None,
        job_id: UUID | None = None,
        entry_count: int = 0,
        scheduled_count: int = 0,
        tombstone_count: int = 0,
    ) -> None:
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM watch_events WHERE root_id = ?",
                (root_id,),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO watch_events("
            "root_id, sequence, event_type, locator_digest, job_id, generation, occurred_at, "
            "entry_count, scheduled_count, tombstone_count"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                root_id,
                sequence,
                event_type.value,
                locator_digest,
                str(job_id) if job_id is not None else None,
                generation,
                occurred_at,
                entry_count,
                scheduled_count,
                tombstone_count,
            ),
        )
        self._fault_point("after_watch_event")

    def _append_watch_job_outcome(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: UUID,
        state: JobState,
        occurred_at: str,
    ) -> None:
        if self._migrations[-1].version < 9:
            return
        target = connection.execute(
            "SELECT root_id, locator_digest FROM watch_job_targets WHERE job_id = ?",
            (str(job_id),),
        ).fetchone()
        if target is None:
            return
        event_type = {
            JobState.QUEUED: WatchEventType.JOB_RETRY,
            JobState.SUCCEEDED: WatchEventType.JOB_SUCCEEDED,
            JobState.FAILED: WatchEventType.JOB_FAILED,
            JobState.CANCELLED: WatchEventType.JOB_CANCELLED,
        }.get(state)
        if event_type is None:
            return
        root = self._required_watch_root_row(connection, str(target["root_id"]))
        self._append_watch_event(
            connection,
            root_id=str(target["root_id"]),
            event_type=event_type,
            locator_digest=str(target["locator_digest"]),
            job_id=job_id,
            generation=int(root["generation"]),
            occurred_at=occurred_at,
        )

    @staticmethod
    def _watch_event_from_row(row: sqlite3.Row) -> WatchEvent:
        return WatchEvent(
            root_id=str(row["root_id"]),
            sequence=int(row["sequence"]),
            event_type=WatchEventType(str(row["event_type"])),
            locator_digest=(
                str(row["locator_digest"]) if row["locator_digest"] is not None else None
            ),
            job_id=UUID(str(row["job_id"])) if row["job_id"] is not None else None,
            generation=int(row["generation"]),
            occurred_at=decode_storage_datetime(str(row["occurred_at"])),
            entry_count=int(row["entry_count"]),
            scheduled_count=int(row["scheduled_count"]),
            tombstone_count=int(row["tombstone_count"]),
        )

    def _load_job(self, connection: sqlite3.Connection, job_id: UUID) -> Job | None:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),)).fetchone()
        return self._job_from_row(connection, row) if row is not None else None

    def _job_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> Job:
        columns = frozenset(row.keys())
        references = tuple(
            self._reference_from_row(item)
            for item in connection.execute(
                "SELECT r.*, o.byte_length FROM job_object_references AS r "
                "JOIN objects AS o ON o.object_id = r.object_id "
                "WHERE r.job_id = ? ORDER BY r.role, r.ordinal",
                (str(row["job_id"]),),
            ).fetchall()
        )
        lease = row["lease_expires_at"]
        terminal = row["terminal_at"]
        return Job(
            job_id=UUID(str(row["job_id"])),
            kind=str(row["kind"]),
            deduplication_key=str(row["deduplication_key"]),
            state=JobState(str(row["state"])),
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            revision=int(row["revision"]),
            available_at=decode_storage_datetime(
                str(row["available_at"] if "available_at" in columns else row["created_at"])
            ),
            active_owner_id=(
                str(row["active_owner_id"]) if row["active_owner_id"] is not None else None
            ),
            lease_expires_at=decode_storage_datetime(str(lease)) if lease is not None else None,
            cancellation_requested_at=(
                decode_storage_datetime(str(row["cancellation_requested_at"]))
                if "cancellation_requested_at" in columns
                and row["cancellation_requested_at"] is not None
                else None
            ),
            last_failure_code=(
                str(row["last_failure_code"]) if row["last_failure_code"] is not None else None
            ),
            created_at=decode_storage_datetime(str(row["created_at"])),
            updated_at=decode_storage_datetime(str(row["updated_at"])),
            terminal_at=(decode_storage_datetime(str(terminal)) if terminal is not None else None),
            references=references,
        )

    @staticmethod
    def _job_matches_spec(job: Job, spec: JobSpec) -> bool:
        return (
            job.job_id == spec.job_id
            and job.kind == spec.kind
            and job.deduplication_key == spec.deduplication_key
            and job.max_attempts == spec.max_attempts
            and job.available_at == (spec.available_at or spec.created_at)
            and job.created_at == spec.created_at
            and job.references == SQLiteCatalog._canonical_references(spec.references)
        )

    def _required_job_row(self, connection: sqlite3.Connection, job_id: UUID) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),)).fetchone()
        if row is None:
            raise JobNotFound(str(job_id))
        return cast(sqlite3.Row, row)

    def _assert_active_lease(
        self,
        row: sqlite3.Row,
        *,
        owner_id: str,
        token_hash: str,
        expected_revision: int,
        now_text: str,
        allow_idempotent_revision: bool = False,
        requested_lease_until: str | None = None,
        allow_cancellation_requested: bool = False,
    ) -> None:
        if row["state"] != JobState.RUNNING.value:
            raise InvalidJobTransition("job is not running")
        if row["active_owner_id"] != owner_id or row["active_lease_token_hash"] != token_hash:
            raise LeaseConflict("job lease owner or fencing token does not match")
        if str(row["lease_expires_at"]) <= now_text:
            raise LeaseConflict("job lease has expired")
        if row["cancellation_requested_at"] is not None and not allow_cancellation_requested:
            raise InvalidJobTransition("job cancellation is requested")
        if int(row["revision"]) != expected_revision:
            if (
                allow_idempotent_revision
                and requested_lease_until is not None
                and int(row["revision"]) == expected_revision + 1
                and str(row["lease_expires_at"]) >= requested_lease_until
            ):
                return
            raise LeaseConflict("job revision is stale")

    @staticmethod
    def _assert_transition_time(row: sqlite3.Row, *, now_text: str) -> None:
        if now_text < str(row["updated_at"]):
            raise InvalidJobTransition("transition time precedes current job state")

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: UUID,
        event_type: JobEventType,
        from_state: JobState | None,
        to_state: JobState,
        occurred_at: str,
        attempt_count: int,
        owner_id: str | None,
        failure_code: str | None,
    ) -> None:
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM job_events WHERE job_id = ?",
                (str(job_id),),
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO job_events("
            "job_id, sequence, event_type, from_state, to_state, occurred_at, attempt_count, "
            "owner_id, failure_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(job_id),
                sequence,
                event_type.value,
                from_state.value if from_state is not None else None,
                to_state.value,
                occurred_at,
                attempt_count,
                owner_id,
                failure_code,
            ),
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> JobEvent:
        return JobEvent(
            job_id=UUID(str(row["job_id"])),
            sequence=int(row["sequence"]),
            event_type=JobEventType(str(row["event_type"])),
            from_state=(
                JobState(str(row["from_state"])) if row["from_state"] is not None else None
            ),
            to_state=JobState(str(row["to_state"])),
            occurred_at=decode_storage_datetime(str(row["occurred_at"])),
            attempt_count=int(row["attempt_count"]),
            owner_id=str(row["owner_id"]) if row["owner_id"] is not None else None,
            failure_code=(str(row["failure_code"]) if row["failure_code"] is not None else None),
        )

    @staticmethod
    def _lease_token_hash(lease_token: str) -> str:
        if not isinstance(lease_token, str) or len(lease_token) < _MIN_LEASE_TOKEN_LENGTH:
            raise LeaseConflict("lease token is too short")
        return "sha256:" + hashlib.sha256(lease_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_owner(owner_id: str) -> None:
        if _OWNER.fullmatch(owner_id) is None:
            raise LeaseConflict("lease owner identifier is invalid")

    @staticmethod
    def _validate_failure_code(failure_code: str) -> None:
        if _MACHINE_TOKEN.fullmatch(failure_code) is None:
            raise InvalidJobTransition("failure code is invalid")

    def _schema_version_from_connection(self, connection: sqlite3.Connection) -> int:
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        if row is None or row[0] is None:
            raise CatalogIncompatible("catalog migration history is empty")
        return int(row[0])

    def _fault_point(self, point: str) -> None:
        """Provide a private deterministic transaction boundary for failure tests."""
        del point
