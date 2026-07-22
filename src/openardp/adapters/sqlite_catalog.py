"""Transactional local SQLite catalog for source facts and recoverable work."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from pydantic import SecretStr

from openardp.adapters.sqlite_migrations import MIGRATIONS, Migration
from openardp.domain.block import BlockKind
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
from openardp.ports.catalog import (
    CatalogError,
    CatalogIncompatible,
    CatalogTooNew,
    DocumentConflict,
    DocumentNotFound,
    InvalidJobTransition,
    InvalidObjectReference,
    JobConflict,
    JobNotFound,
    LeaseConflict,
    MigrationFailed,
    RepresentationConflict,
    RepresentationIncomplete,
    RepresentationIntegrityError,
    RepresentationLeaseConflict,
    RepresentationNotFound,
    VersionConflict,
)

_OWNER = re.compile(r"^.{1,255}$", re.DOTALL)
_MACHINE_TOKEN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
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
}


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
            current = self._validate_history(connection)
            self._configure_persistent_profile(connection)
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
    ) -> RepresentationCommitResult:
        """Atomically publish one complete READY aggregate, head and ingest event."""
        if disposition is IngestionDisposition.CACHE_HIT:
            raise RepresentationConflict("ready commit cannot be a cache hit")
        now_text = encode_storage_datetime(commit.ready_at)
        observed_text = encode_storage_datetime(commit.source_observed_at)
        with self._write_connection() as connection:
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

    def create_job(self, spec: JobSpec) -> Job:
        """Create or idempotently return one immutable queued job request."""
        created_at = encode_storage_datetime(spec.created_at)
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
            connection.execute(
                "INSERT INTO jobs("
                "job_id, kind, deduplication_key, state, attempt_count, max_attempts, revision, "
                "active_owner_id, active_lease_token_hash, lease_expires_at, "
                "last_transition_token_hash, last_failure_code, created_at, updated_at, terminal_at"
                ") VALUES (?, ?, ?, 'QUEUED', 0, ?, 0, NULL, NULL, NULL, NULL, NULL, ?, ?, NULL)",
                (
                    str(spec.job_id),
                    spec.kind,
                    spec.deduplication_key,
                    spec.max_attempts,
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
                queued = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'QUEUED' ORDER BY created_at, job_id LIMIT 1"
                ).fetchone()
            else:
                queued = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'QUEUED' AND kind = ? "
                    "ORDER BY created_at, job_id LIMIT 1",
                    (kind,),
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
    ) -> Job:
        """Requeue or terminally fail a running job through fencing proof."""
        self._validate_owner(owner_id)
        self._validate_failure_code(failure_code)
        token_hash = self._lease_token_hash(lease_token)
        now_text = encode_storage_datetime(now)
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
            self._assert_transition_time(row, now_text=now_text)
            should_retry = retryable and int(row["attempt_count"]) < int(row["max_attempts"])
            state = JobState.QUEUED if should_retry else JobState.FAILED
            terminal_at = None if should_retry else now_text
            event_type = JobEventType.RETRY_QUEUED if should_retry else JobEventType.FAILED
            connection.execute(
                "UPDATE jobs SET state = ?, revision = revision + 1, active_owner_id = NULL, "
                "active_lease_token_hash = NULL, lease_expires_at = NULL, "
                "last_transition_token_hash = ?, last_failure_code = ?, updated_at = ?, "
                "terminal_at = ? WHERE job_id = ? AND revision = ? AND state = 'RUNNING'",
                (
                    state.value,
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
            failed = self._load_job(connection, job_id)
            if failed is None:
                raise CatalogError("failed job did not become visible")
            return failed

    def get_job(self, job_id: UUID) -> Job | None:
        """Return one durable job projection or no result."""
        with self._read_connection() as connection:
            return self._load_job(connection, job_id)

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
        with self._write_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE state = 'RUNNING' AND lease_expires_at <= ? "
                "ORDER BY job_id",
                (now_text,),
            ).fetchall()
            for row in rows:
                job_id = UUID(str(row["job_id"]))
                should_retry = int(row["attempt_count"]) < int(row["max_attempts"])
                state = JobState.QUEUED if should_retry else JobState.FAILED
                event_type = (
                    JobEventType.LEASE_RECOVERED if should_retry else JobEventType.LEASE_EXHAUSTED
                )
                terminal_at = None if should_retry else now_text
                connection.execute(
                    "UPDATE jobs SET state = ?, revision = revision + 1, "
                    "active_owner_id = NULL, active_lease_token_hash = NULL, "
                    "lease_expires_at = NULL, last_transition_token_hash = ?, "
                    "last_failure_code = 'lease_expired', updated_at = ?, terminal_at = ? "
                    "WHERE job_id = ? AND state = 'RUNNING' AND lease_expires_at <= ?",
                    (
                        state.value,
                        row["active_lease_token_hash"],
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
                    failure_code="lease_expired",
                )
                (requeued if should_retry else failed).append(job_id)
        return RecoveryResult(
            requeued_job_ids=tuple(sorted(requeued, key=str)),
            failed_job_ids=tuple(sorted(failed, key=str)),
            recovered_at=now,
        )

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
                "ORDER BY object_id"
            ).fetchall()
            return ReferenceSnapshot(
                object_ids=tuple(str(row[0]) for row in rows),
                observed_at=observed_at,
                catalog_schema_version=self._schema_version_from_connection(connection),
            )

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

    def _load_job(self, connection: sqlite3.Connection, job_id: UUID) -> Job | None:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),)).fetchone()
        return self._job_from_row(connection, row) if row is not None else None

    def _job_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> Job:
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
            active_owner_id=(
                str(row["active_owner_id"]) if row["active_owner_id"] is not None else None
            ),
            lease_expires_at=decode_storage_datetime(str(lease)) if lease is not None else None,
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
    ) -> None:
        if row["state"] != JobState.RUNNING.value:
            raise InvalidJobTransition("job is not running")
        if row["active_owner_id"] != owner_id or row["active_lease_token_hash"] != token_hash:
            raise LeaseConflict("job lease owner or fencing token does not match")
        if str(row["lease_expires_at"]) <= now_text:
            raise LeaseConflict("job lease has expired")
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
