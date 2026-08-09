"""Watcher scan reconciliation and scheduling transactions."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID, uuid5

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.adapters.sqlite_catalog_support import (
    _WATCH_JOB_NAMESPACE,
    _WatchObservationTransition,
    _WatchScanProgress,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.storage import encode_storage_datetime
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
)
from openardp.ports.catalog import CatalogError, InvalidJobTransition, JobConflict


class _SQLiteCatalogWatchMixin(_SQLiteCatalogBase):
    """Watcher scan reconciliation and scheduling transactions."""

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
                return self._record_incomplete_watch_scan(
                    connection,
                    root_id=root_id,
                    generation=current_generation,
                    now_text=now_text,
                )
            return self._reconcile_complete_watch_scan(
                connection,
                root_id=root_id,
                scan=scan,
                root_row=root_row,
                generation=current_generation + 1,
                now=now,
                now_text=now_text,
            )

    def _record_incomplete_watch_scan(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        generation: int,
        now_text: str,
    ) -> WatchReconciliation:
        """Record rescan intent without interpreting partial observations."""
        connection.execute(
            "UPDATE watch_roots SET rescan_required = 1, updated_at = ? WHERE root_id = ?",
            (now_text, root_id),
        )
        self._append_watch_event(
            connection,
            root_id=root_id,
            event_type=WatchEventType.RESCAN_REQUIRED,
            generation=generation,
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

    def _reconcile_complete_watch_scan(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        scan: WatchScan,
        root_row: sqlite3.Row,
        generation: int,
        now: datetime,
        now_text: str,
    ) -> WatchReconciliation:
        """Reconcile all complete-scan facts inside the caller's transaction."""
        existing_rows = {
            str(row["locator_digest"]): row
            for row in connection.execute(
                "SELECT * FROM watch_observations WHERE root_id = ?",
                (root_id,),
            ).fetchall()
        }
        scanned_digests = {entry.locator_digest for entry in scan.entries}
        rename_hints = self._watch_rename_hints(existing_rows, scan.entries, scanned_digests)
        progress = _WatchScanProgress(
            active_count=self._active_watch_job_count(connection, root_id)
        )
        config = self._watch_root_from_row(root_row).authority.config
        for entry in scan.entries:
            self._reconcile_watch_entry(
                connection,
                root_id=root_id,
                entry=entry,
                previous_row=existing_rows.get(entry.locator_digest),
                config=config,
                observed_at=scan.completed_at,
                generation=generation,
                now=now,
                now_text=now_text,
                progress=progress,
            )
        progress.tombstone_count = self._tombstone_missing_watch_entries(
            connection,
            root_id=root_id,
            existing_rows=existing_rows,
            scanned_digests=scanned_digests,
            observed_at=scan.completed_at,
            generation=generation,
            now_text=now_text,
        )
        self._append_watch_rename_hints(
            connection,
            root_id=root_id,
            rename_hints=rename_hints,
            generation=generation,
            now_text=now_text,
        )
        return self._publish_watch_reconciliation(
            connection,
            root_id=root_id,
            scan=scan,
            generation=generation,
            now_text=now_text,
            progress=progress,
        )

    def _watch_rename_hints(
        self,
        existing_rows: dict[str, sqlite3.Row],
        entries: tuple[WatchScanEntry, ...],
        scanned_digests: set[str],
    ) -> tuple[str, ...]:
        """Return only unambiguous same-fingerprint move hints."""
        previous_by_identity: dict[tuple[str, str], list[WatchObservation]] = {}
        for row in existing_rows.values():
            observation = self._watch_observation_from_row(row)
            if observation.fingerprint is not None:
                identity = (
                    observation.fingerprint.device_id,
                    observation.fingerprint.file_id,
                )
                previous_by_identity.setdefault(identity, []).append(observation)
        current_by_identity: dict[tuple[str, str], list[WatchScanEntry]] = {}
        for entry in entries:
            identity = (entry.fingerprint.device_id, entry.fingerprint.file_id)
            current_by_identity.setdefault(identity, []).append(entry)
        return tuple(
            current[0].locator_digest
            for identity, current in sorted(current_by_identity.items())
            if len(current) == 1
            and len(previous_by_identity.get(identity, ())) == 1
            and previous_by_identity[identity][0].locator_digest not in scanned_digests
            and current[0].locator_digest not in existing_rows
            and previous_by_identity[identity][0].fingerprint == current[0].fingerprint
        )

    @staticmethod
    def _active_watch_job_count(connection: sqlite3.Connection, root_id: str) -> int:
        """Count queued and running targets for one exact watch root."""
        row = connection.execute(
            "SELECT count(*) FROM watch_job_targets AS t "
            "JOIN jobs AS j ON j.job_id = t.job_id "
            "WHERE t.root_id = ? AND j.state IN ('QUEUED', 'RUNNING')",
            (root_id,),
        ).fetchone()
        return int(row[0])

    def _reconcile_watch_entry(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        entry: WatchScanEntry,
        previous_row: sqlite3.Row | None,
        config: WatchConfig,
        observed_at: datetime,
        generation: int,
        now: datetime,
        now_text: str,
        progress: _WatchScanProgress,
    ) -> None:
        """Persist one observed entry and schedule at most one exact job."""
        previous = (
            self._watch_observation_from_row(previous_row) if previous_row is not None else None
        )
        transition = self._watch_entry_transition(
            previous,
            entry.fingerprint,
            config,
            observed_at,
        )
        observation = self._make_watch_observation(
            root_id=root_id,
            relative_locator=entry.relative_locator,
            locator_digest=entry.locator_digest,
            state=transition.state,
            fingerprint=entry.fingerprint,
            first_observed_at=transition.first_observed_at,
            last_observed_at=observed_at,
            stable_since=transition.stable_since,
            last_generation=generation,
            last_scheduled_key=transition.last_scheduled_key,
            revision=transition.revision,
        )
        self._write_watch_observation(connection, observation)
        self._fault_point("after_watch_observation")
        if transition.event_type is not None:
            self._append_watch_event(
                connection,
                root_id=root_id,
                event_type=transition.event_type,
                locator_digest=entry.locator_digest,
                generation=generation,
                occurred_at=now_text,
            )
        if transition.state is WatchObservationState.CANDIDATE:
            progress.candidate_count += 1
            return
        progress.stable_count += 1
        self._schedule_stable_watch_entry(
            connection,
            root_id=root_id,
            entry=entry,
            observation=observation,
            config=config,
            generation=generation,
            now=now,
            now_text=now_text,
            progress=progress,
        )

    @staticmethod
    def _watch_entry_transition(
        previous: WatchObservation | None,
        fingerprint: WatchFileFingerprint,
        config: WatchConfig,
        observed_at: datetime,
    ) -> _WatchObservationTransition:
        """Derive one observation transition without I/O."""
        if previous is None:
            state = (
                WatchObservationState.STABLE
                if config.stability_ms == 0
                else WatchObservationState.CANDIDATE
            )
            return _WatchObservationTransition(
                state=state,
                first_observed_at=observed_at,
                stable_since=observed_at if state is WatchObservationState.STABLE else None,
                last_scheduled_key=None,
                revision=1,
                event_type=WatchEventType.OBSERVATION_CREATED,
            )
        if previous.state is WatchObservationState.TOMBSTONED or previous.fingerprint is None:
            changed_event = WatchEventType.REAPPEARED
        elif previous.fingerprint != fingerprint:
            changed_event = WatchEventType.OBSERVATION_CHANGED
        else:
            changed_event = None
        if changed_event is not None:
            state = (
                WatchObservationState.STABLE
                if config.stability_ms == 0
                else WatchObservationState.CANDIDATE
            )
            return _WatchObservationTransition(
                state=state,
                first_observed_at=observed_at,
                stable_since=observed_at if state is WatchObservationState.STABLE else None,
                last_scheduled_key=None,
                revision=previous.revision + 1,
                event_type=changed_event,
            )
        elapsed_ms = int((observed_at - previous.first_observed_at).total_seconds() * 1_000)
        is_stable = elapsed_ms >= config.stability_ms
        return _WatchObservationTransition(
            state=(WatchObservationState.STABLE if is_stable else WatchObservationState.CANDIDATE),
            first_observed_at=previous.first_observed_at,
            stable_since=(previous.stable_since or observed_at) if is_stable else None,
            last_scheduled_key=previous.last_scheduled_key,
            revision=previous.revision + 1,
            event_type=(
                WatchEventType.OBSERVATION_STABLE
                if is_stable and previous.state is not WatchObservationState.STABLE
                else None
            ),
        )

    def _schedule_stable_watch_entry(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        entry: WatchScanEntry,
        observation: WatchObservation,
        config: WatchConfig,
        generation: int,
        now: datetime,
        now_text: str,
        progress: _WatchScanProgress,
    ) -> None:
        """Schedule one stable entry unless deduplicated or backpressured."""
        profile = (
            config.text_profile if entry.media_type.startswith("text/") else config.rich_profile
        )
        key = watch_job_key(
            root_id=root_id,
            locator_digest=entry.locator_digest,
            fingerprint=entry.fingerprint,
            parser_profile=profile,
        )
        if observation.last_scheduled_key == key:
            return
        if progress.active_count >= config.max_active_jobs:
            progress.backpressure = True
            return
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
        updated = observation.model_copy(
            update={
                "last_scheduled_key": key,
                "row_fingerprint": self._observation_fingerprint_with_update(
                    observation, last_scheduled_key=key
                ),
            }
        )
        self._write_watch_observation(connection, updated)
        progress.scheduled.append(job.job_id)
        progress.active_count += 1
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

    def _tombstone_missing_watch_entries(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        existing_rows: dict[str, sqlite3.Row],
        scanned_digests: set[str],
        observed_at: datetime,
        generation: int,
        now_text: str,
    ) -> int:
        """Persist tombstones for prior live locators absent from a complete scan."""
        count = 0
        for locator_digest, row in sorted(existing_rows.items()):
            previous = self._watch_observation_from_row(row)
            if (
                locator_digest in scanned_digests
                or previous.state is WatchObservationState.TOMBSTONED
            ):
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
            count += 1
            self._append_watch_event(
                connection,
                root_id=root_id,
                event_type=WatchEventType.TOMBSTONED,
                locator_digest=locator_digest,
                generation=generation,
                occurred_at=now_text,
                tombstone_count=1,
            )
        return count

    def _append_watch_rename_hints(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        rename_hints: tuple[str, ...],
        generation: int,
        now_text: str,
    ) -> None:
        """Append body-free rename hints after authoritative observations."""
        for locator_digest in rename_hints:
            self._append_watch_event(
                connection,
                root_id=root_id,
                event_type=WatchEventType.RENAME_HINT,
                locator_digest=locator_digest,
                generation=generation,
                occurred_at=now_text,
            )

    def _publish_watch_reconciliation(
        self,
        connection: sqlite3.Connection,
        *,
        root_id: str,
        scan: WatchScan,
        generation: int,
        now_text: str,
        progress: _WatchScanProgress,
    ) -> WatchReconciliation:
        """Publish final root state and summary before the transaction commits."""
        connection.execute(
            "UPDATE watch_roots SET generation = ?, rescan_required = ?, updated_at = ? "
            "WHERE root_id = ?",
            (generation, int(progress.backpressure), now_text, root_id),
        )
        self._append_watch_event(
            connection,
            root_id=root_id,
            event_type=(
                WatchEventType.BACKPRESSURE
                if progress.backpressure
                else WatchEventType.SCAN_COMPLETED
            ),
            generation=generation,
            occurred_at=now_text,
            entry_count=len(scan.entries),
            scheduled_count=len(progress.scheduled),
            tombstone_count=progress.tombstone_count,
        )
        self._fault_point("before_watch_reconciliation_commit")
        updated_root = self._load_watch_root(connection, root_id)
        if updated_root is None:
            raise CatalogError("watch root did not remain visible")
        return WatchReconciliation(
            root=updated_root,
            complete=True,
            entry_count=len(scan.entries),
            candidate_count=progress.candidate_count,
            stable_count=progress.stable_count,
            scheduled_job_ids=tuple(sorted(progress.scheduled, key=str)),
            tombstone_count=progress.tombstone_count,
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


__all__ = ["_SQLiteCatalogWatchMixin"]
