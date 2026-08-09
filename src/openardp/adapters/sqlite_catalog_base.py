"""Typed common method surface for decomposed SQLite catalog mixins."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from openardp.adapters.sqlite_migrations import Migration
from openardp.domain.derivation_lifecycle import (
    DerivationEventReason,
    DerivationLifecycleState,
    DerivationNode,
)
from openardp.domain.ingestion import (
    DocumentHead,
    DocumentRepresentation,
    IngestionDisposition,
    IngestionEvent,
    ReadyRepresentationCommit,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationCommitResult,
    RepresentationScope,
)
from openardp.domain.maintenance import MaintenanceOperation
from openardp.domain.rich_ingestion import RichRepresentationArtifacts
from openardp.domain.search import SearchIndexEntry
from openardp.domain.storage import (
    DocumentVersion,
    Job,
    JobEventType,
    JobState,
    ObjectReference,
    StoredObject,
)
from openardp.domain.watcher import (
    WatchEvent,
    WatchEventType,
    WatchFileFingerprint,
    WatchJobTarget,
    WatchObservation,
    WatchObservationState,
    WatchRoot,
    WatchScanEntry,
)


class _SQLiteCatalogBase:
    """Declare shared state and cross-responsibility catalog calls."""

    _path: Path
    _migrations: tuple[Migration, ...]
    _migration_by_version: dict[int, Migration]
    _busy_timeout_ms: int

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
        raise NotImplementedError()

    def _insert_search_entry(
        self, connection: sqlite3.Connection, entry: SearchIndexEntry, text: str
    ) -> int:
        raise NotImplementedError()

    def _load_active_operation(self, connection: sqlite3.Connection) -> MaintenanceOperation | None:
        raise NotImplementedError()

    def _maintenance_operation(
        self, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> MaintenanceOperation:
        raise NotImplementedError()

    @contextmanager
    def _optional_write_connection(
        self, connection: sqlite3.Connection | None
    ) -> Iterator[sqlite3.Connection]:
        raise NotImplementedError()

    @contextmanager
    def _write_connection(self, *, allow_maintenance: bool = False) -> Iterator[sqlite3.Connection]:
        raise NotImplementedError()

    @contextmanager
    def _read_connection(self) -> Iterator[sqlite3.Connection]:
        raise NotImplementedError()

    def _load_version(
        self, connection: sqlite3.Connection, document_id: UUID, version_id: str
    ) -> DocumentVersion | None:
        raise NotImplementedError()

    @staticmethod
    def _reference_from_row(row: sqlite3.Row) -> ObjectReference:
        raise NotImplementedError()

    @staticmethod
    def _derivation_dependencies_are_current(
        connection: sqlite3.Connection,
        artifact_id: str,
        *,
        object_is_verified: Callable[[str], bool] | None,
    ) -> bool:
        raise NotImplementedError()

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
        raise NotImplementedError()

    def _register_object(
        self,
        connection: sqlite3.Connection,
        value: StoredObject | ObjectReference,
        *,
        registered_at: str,
    ) -> None:
        raise NotImplementedError()

    def _load_representation_row(
        self, connection: sqlite3.Connection, scope: RepresentationScope
    ) -> sqlite3.Row | None:
        raise NotImplementedError()

    def _representation_from_row(self, row: sqlite3.Row) -> DocumentRepresentation:
        raise NotImplementedError()

    def _required_representation(
        self, connection: sqlite3.Connection, scope: RepresentationScope
    ) -> RepresentationAggregate:
        raise NotImplementedError()

    def _required_rich_representation(
        self, connection: sqlite3.Connection, scope: RepresentationScope
    ) -> RichRepresentationArtifacts:
        raise NotImplementedError()

    @staticmethod
    def _block_projection_from_row(row: sqlite3.Row) -> RepresentationBlock:
        raise NotImplementedError()

    @staticmethod
    def _warning_codes(payload: str) -> tuple[str, ...]:
        raise NotImplementedError()

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
        raise NotImplementedError()

    def _append_ingestion_event_without_head(
        self,
        connection: sqlite3.Connection,
        scope: RepresentationScope,
        *,
        source_observed_at: str,
        ingested_at: str,
        disposition: IngestionDisposition,
    ) -> IngestionEvent:
        raise NotImplementedError()

    def _required_document_head(
        self, connection: sqlite3.Connection, document_id: UUID
    ) -> DocumentHead:
        raise NotImplementedError()

    @staticmethod
    def _head_from_row(row: sqlite3.Row) -> DocumentHead:
        raise NotImplementedError()

    @staticmethod
    def _ingestion_event_from_row(row: sqlite3.Row) -> IngestionEvent:
        raise NotImplementedError()

    def _load_watch_root(self, connection: sqlite3.Connection, root_id: str) -> WatchRoot | None:
        raise NotImplementedError()

    @staticmethod
    def _watch_root_from_row(row: sqlite3.Row) -> WatchRoot:
        raise NotImplementedError()

    @staticmethod
    def _required_watch_root_row(connection: sqlite3.Connection, root_id: str) -> sqlite3.Row:
        raise NotImplementedError()

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
        raise NotImplementedError()

    @staticmethod
    def _observation_fingerprint_with_update(
        observation: WatchObservation, *, last_scheduled_key: str
    ) -> str:
        raise NotImplementedError()

    @staticmethod
    def _write_watch_observation(
        connection: sqlite3.Connection, observation: WatchObservation
    ) -> None:
        raise NotImplementedError()

    @staticmethod
    def _watch_observation_from_row(row: sqlite3.Row) -> WatchObservation:
        raise NotImplementedError()

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
        raise NotImplementedError()

    @staticmethod
    def _watch_target_from_row(row: sqlite3.Row) -> WatchJobTarget:
        raise NotImplementedError()

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
        raise NotImplementedError()

    def _append_watch_job_outcome(
        self, connection: sqlite3.Connection, *, job_id: UUID, state: JobState, occurred_at: str
    ) -> None:
        raise NotImplementedError()

    @staticmethod
    def _watch_event_from_row(row: sqlite3.Row) -> WatchEvent:
        raise NotImplementedError()

    def _job_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> Job:
        raise NotImplementedError()

    def _required_job_row(self, connection: sqlite3.Connection, job_id: UUID) -> sqlite3.Row:
        raise NotImplementedError()

    @staticmethod
    def _assert_transition_time(row: sqlite3.Row, *, now_text: str) -> None:
        raise NotImplementedError()

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
        raise NotImplementedError()

    @staticmethod
    def _validate_failure_code(failure_code: str) -> None:
        raise NotImplementedError()

    def _schema_version_from_connection(self, connection: sqlite3.Connection) -> int:
        raise NotImplementedError()

    def _fault_point(self, point: str) -> None:
        raise NotImplementedError()


__all__ = ["_SQLiteCatalogBase"]
