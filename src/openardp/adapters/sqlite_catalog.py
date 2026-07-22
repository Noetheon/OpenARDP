"""Transactional local SQLite catalog for source facts and recoverable work."""

from __future__ import annotations

import hashlib
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
    InvalidJobTransition,
    InvalidObjectReference,
    JobConflict,
    JobNotFound,
    LeaseConflict,
    MigrationFailed,
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
        """Return sorted unique version and job object roots from one read snapshot."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT source_object_id AS object_id FROM document_versions "
                "UNION SELECT object_id FROM version_object_references "
                "UNION SELECT object_id FROM job_object_references "
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
