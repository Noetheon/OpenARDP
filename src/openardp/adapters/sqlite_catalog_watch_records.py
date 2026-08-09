"""Watcher record persistence and projections."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.storage import (
    Job,
    JobEventType,
    JobState,
    decode_storage_datetime,
    encode_storage_datetime,
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
    WatchRoot,
    WatchScanEntry,
    watch_observation_fingerprint,
)
from openardp.ports.catalog import CatalogIncompatible, JobConflict, JobNotFound


class _SQLiteCatalogWatchRecordMixin(_SQLiteCatalogBase):
    """Watcher record persistence and projections."""

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


__all__ = ["_SQLiteCatalogWatchRecordMixin"]
