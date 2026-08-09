"""Recoverable job lifecycle transactions."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from pydantic import SecretStr

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.adapters.sqlite_catalog_support import (
    _MACHINE_TOKEN,
    _MIN_LEASE_TOKEN_LENGTH,
    _OWNER,
    _canonical_references,
)
from openardp.domain.storage import (
    Job,
    JobEvent,
    JobEventType,
    JobLease,
    JobSpec,
    JobState,
    RecoveryResult,
    decode_storage_datetime,
    encode_storage_datetime,
)
from openardp.ports.catalog import (
    CatalogError,
    InvalidJobTransition,
    JobConflict,
    JobNotFound,
    LeaseConflict,
)


class _SQLiteCatalogJobMixin(_SQLiteCatalogBase):
    """Recoverable job lifecycle transactions."""

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
            and job.references == _canonical_references(spec.references)
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


__all__ = ["_SQLiteCatalogJobMixin"]
