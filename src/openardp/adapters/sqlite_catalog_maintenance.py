"""Retention, quarantine, recovery, and maintenance transactions."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Literal, cast
from uuid import UUID, uuid5

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.adapters.sqlite_catalog_support import (
    _MAINTENANCE_NAMESPACE,
    _RETENTION_REFERENCES,
)
from openardp.domain.identity import canonical_sha256
from openardp.domain.maintenance import (
    MaintenanceAction,
    MaintenanceOperation,
    MaintenanceOperationEntry,
    MaintenanceOperationKind,
    MaintenanceOperationState,
    QuarantineBatch,
    QuarantineBatchState,
    QuarantineEntry,
    QuarantineEntryState,
    ReclamationPlan,
    RetentionHold,
    RetentionRoot,
    RetentionSnapshot,
)
from openardp.domain.storage import (
    ReferenceSnapshot,
    decode_storage_datetime,
    encode_storage_datetime,
)
from openardp.ports.catalog import CatalogError, MaintenanceRecoveryRequired


class _SQLiteCatalogMaintenanceMixin(_SQLiteCatalogBase):
    """Retention, quarantine, recovery, and maintenance transactions."""

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

    def retention_snapshot(self, *, observed_at: datetime) -> RetentionSnapshot:
        """Return exact explainable roots and active holds in one read transaction."""
        with self._read_connection() as connection:
            return self._retention_snapshot_from_connection(
                connection,
                observed_at=observed_at,
            )

    def add_retention_hold(self, hold: RetentionHold) -> RetentionHold:
        """Create or idempotently return one exact operator hold."""
        with self._write_connection() as connection:
            row = connection.execute(
                "SELECT * FROM retention_holds WHERE hold_id = ?", (hold.hold_id,)
            ).fetchone()
            if row is not None:
                existing = self._retention_hold(row)
                if existing == hold:
                    return existing
                raise CatalogError("retention hold identity conflicts")
            connection.execute(
                "INSERT INTO retention_holds(hold_id, object_id, reason, created_at, "
                "expires_at, released_at) VALUES (?, ?, ?, ?, ?, NULL)",
                (
                    hold.hold_id,
                    hold.object_id,
                    hold.reason,
                    encode_storage_datetime(hold.created_at),
                    (
                        encode_storage_datetime(hold.expires_at)
                        if hold.expires_at is not None
                        else None
                    ),
                ),
            )
            return hold

    def release_retention_hold(self, hold_id: str, *, now: datetime) -> RetentionHold:
        """Release one exact hold idempotently without deleting its history."""
        released_at = encode_storage_datetime(now)
        with self._write_connection() as connection:
            row = connection.execute(
                "SELECT * FROM retention_holds WHERE hold_id = ?", (hold_id,)
            ).fetchone()
            if row is None:
                raise CatalogError("retention hold does not exist")
            hold = self._retention_hold(row)
            if hold.released_at is not None:
                return hold
            if now < hold.created_at:
                raise ValueError("hold release must not precede creation")
            connection.execute(
                "UPDATE retention_holds SET released_at = ? WHERE hold_id = ?",
                (released_at, hold_id),
            )
            updated = connection.execute(
                "SELECT * FROM retention_holds WHERE hold_id = ?", (hold_id,)
            ).fetchone()
            if updated is None:
                raise CatalogError("retention hold release did not become visible")
            return self._retention_hold(updated)

    def quarantine_batch_for_plan(self, plan_id: str) -> QuarantineBatch | None:
        """Return the exact prior batch for an idempotent plan retry."""
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT batch_id FROM quarantine_batches WHERE plan_id = ?", (plan_id,)
            ).fetchone()
            return (
                self._load_quarantine_batch(connection, UUID(str(row["batch_id"])))
                if row is not None
                else None
            )

    def quarantine_batch(self, batch_id: UUID) -> QuarantineBatch | None:
        """Return one named quarantine batch and exact entries."""
        with self._read_connection() as connection:
            return self._load_quarantine_batch(connection, batch_id)

    def claim_quarantine(
        self,
        plan: ReclamationPlan,
        *,
        now: datetime,
    ) -> MaintenanceOperation:
        """Persist exact quarantine intent before any filesystem transition."""
        operation_id = uuid5(_MAINTENANCE_NAMESPACE, f"quarantine:{plan.plan_id}")
        batch_id = uuid5(_MAINTENANCE_NAMESPACE, f"batch:{plan.plan_id}")
        encoded = encode_storage_datetime(now)
        not_before = encode_storage_datetime(
            now + timedelta(seconds=plan.policy.quarantine_grace_seconds)
        )
        with self._write_connection(allow_maintenance=True) as connection:
            active = self._load_active_operation(connection)
            if active is not None:
                if active.operation_id == operation_id:
                    return active
                raise MaintenanceRecoveryRequired("another maintenance operation is active")
            existing = self._load_quarantine_batch(connection, batch_id)
            if existing is not None:
                terminal = connection.execute(
                    "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                    (str(operation_id),),
                ).fetchone()
                if terminal is None:
                    raise CatalogError("quarantine batch has no operation history")
                return self._maintenance_operation(connection, terminal)
            snapshot = self._retention_snapshot_from_connection(connection, observed_at=now)
            if (
                snapshot.catalog_schema_version != plan.catalog_schema_version
                or snapshot.root_snapshot_id != plan.root_snapshot_id
                or snapshot.hold_snapshot_id != plan.hold_snapshot_id
            ):
                raise CatalogError("reclamation plan is stale")
            connection.execute(
                "INSERT INTO quarantine_batches(batch_id, plan_id, policy_id, "
                "root_snapshot_id, inventory_id, state, quarantined_at, not_before, "
                "entry_count, byte_count, terminal_at) VALUES (?, ?, ?, ?, ?, "
                "'PREPARED', ?, ?, ?, ?, NULL)",
                (
                    str(batch_id),
                    plan.plan_id,
                    plan.policy.policy_id,
                    plan.root_snapshot_id,
                    plan.inventory_id,
                    encoded,
                    not_before,
                    len(plan.candidates),
                    sum(item.item.byte_length for item in plan.candidates),
                ),
            )
            connection.execute(
                "INSERT INTO maintenance_operations(operation_id, kind, subject_id, state, "
                "acknowledgement_digest, created_at, updated_at, terminal_at, failure_code) "
                "VALUES (?, 'QUARANTINE', ?, 'PREPARED', NULL, ?, ?, NULL, NULL)",
                (str(operation_id), plan.plan_id, encoded, encoded),
            )
            for sequence, candidate in enumerate(plan.candidates, start=1):
                connection.execute(
                    "INSERT INTO quarantine_entries(batch_id, object_id, byte_length, reason, "
                    "state, quarantined_at, restored_at, committed_at) "
                    "VALUES (?, ?, ?, ?, 'PLANNED', NULL, NULL, NULL)",
                    (
                        str(batch_id),
                        candidate.item.object_id,
                        candidate.item.byte_length,
                        candidate.reason,
                    ),
                )
                connection.execute(
                    "INSERT INTO maintenance_operation_entries(operation_id, sequence, "
                    "object_id, byte_length, action, source_state, destination_state, outcome) "
                    "VALUES (?, ?, ?, ?, 'MOVE_TO_QUARANTINE', 'ACTIVE', 'QUARANTINE', NULL)",
                    (
                        str(operation_id),
                        sequence,
                        candidate.item.object_id,
                        candidate.item.byte_length,
                    ),
                )
            connection.execute(
                "INSERT INTO maintenance_events(operation_id, sequence, event_type, object_id, "
                "entry_count, byte_count, occurred_at) VALUES (?, 1, 'PREPARED', NULL, ?, ?, ?)",
                (
                    str(operation_id),
                    len(plan.candidates),
                    sum(item.item.byte_length for item in plan.candidates),
                    encoded,
                ),
            )
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("quarantine operation did not become visible")
            return self._maintenance_operation(connection, row)

    def claim_restore(
        self,
        batch_id: UUID,
        *,
        now: datetime,
    ) -> MaintenanceOperation:
        """Persist exact restore intent before any filesystem transition."""
        operation_id = uuid5(_MAINTENANCE_NAMESPACE, f"restore:{batch_id}")
        encoded = encode_storage_datetime(now)
        with self._write_connection(allow_maintenance=True) as connection:
            active = self._load_active_operation(connection)
            if active is not None:
                if active.operation_id == operation_id:
                    return active
                raise MaintenanceRecoveryRequired("another maintenance operation is active")
            batch = self._load_quarantine_batch(connection, batch_id)
            if batch is None:
                raise CatalogError("quarantine batch does not exist")
            if batch.state is QuarantineBatchState.RESTORED:
                row = connection.execute(
                    "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                    (str(operation_id),),
                ).fetchone()
                if row is None:
                    raise CatalogError("restored batch has no operation history")
                return self._maintenance_operation(connection, row)
            if batch.state not in {
                QuarantineBatchState.QUARANTINED,
                QuarantineBatchState.PARTIALLY_RESTORED,
            }:
                raise CatalogError("quarantine batch cannot be restored")
            connection.execute(
                "INSERT INTO maintenance_operations(operation_id, kind, subject_id, state, "
                "acknowledgement_digest, created_at, updated_at, terminal_at, failure_code) "
                "VALUES (?, 'RESTORE', ?, 'PREPARED', NULL, ?, ?, NULL, NULL)",
                (str(operation_id), batch.plan_id, encoded, encoded),
            )
            recoverable = tuple(
                item for item in batch.entries if item.state is QuarantineEntryState.QUARANTINED
            )
            for sequence, entry in enumerate(recoverable, start=1):
                connection.execute(
                    "INSERT INTO maintenance_operation_entries(operation_id, sequence, "
                    "object_id, byte_length, action, source_state, destination_state, outcome) "
                    "VALUES (?, ?, ?, ?, 'MOVE_TO_ACTIVE', 'QUARANTINE', 'ACTIVE', NULL)",
                    (str(operation_id), sequence, entry.object_id, entry.byte_length),
                )
            connection.execute(
                "INSERT INTO maintenance_events(operation_id, sequence, event_type, object_id, "
                "entry_count, byte_count, occurred_at) VALUES (?, 1, 'PREPARED', NULL, ?, ?, ?)",
                (
                    str(operation_id),
                    len(recoverable),
                    sum(item.byte_length for item in recoverable),
                    encoded,
                ),
            )
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("restore operation did not become visible")
            return self._maintenance_operation(connection, row)

    def claim_commit(
        self,
        batch_id: UUID,
        *,
        acknowledgement_digest: str,
        now: datetime,
    ) -> MaintenanceOperation:
        """Persist exact delete-or-restore actions after final root and hold checks."""
        operation_id = uuid5(_MAINTENANCE_NAMESPACE, f"commit:{batch_id}")
        encoded = encode_storage_datetime(now)
        with self._write_connection(allow_maintenance=True) as connection:
            active = self._load_active_operation(connection)
            if active is not None:
                if active.operation_id == operation_id:
                    return active
                raise MaintenanceRecoveryRequired("another maintenance operation is active")
            batch = self._load_quarantine_batch(connection, batch_id)
            if batch is None:
                raise CatalogError("quarantine batch does not exist")
            if batch.state in {
                QuarantineBatchState.COMMITTED,
                QuarantineBatchState.BLOCKED,
            }:
                row = connection.execute(
                    "SELECT * FROM maintenance_operations WHERE operation_id=?",
                    (str(operation_id),),
                ).fetchone()
                if row is None:
                    raise CatalogError("committed batch has no operation history")
                return self._maintenance_operation(connection, row)
            if batch.state is not QuarantineBatchState.QUARANTINED:
                raise CatalogError("quarantine batch cannot be committed")
            if now < batch.not_before:
                raise CatalogError("quarantine grace period is active")
            snapshot = self._retention_snapshot_from_connection(connection, observed_at=now)
            protected = {item.object_id for item in snapshot.roots}
            protected.update(hold.object_id for hold in snapshot.holds if hold.active_at(now))
            connection.execute(
                "INSERT INTO maintenance_operations(operation_id, kind, subject_id, state, "
                "acknowledgement_digest, created_at, updated_at, terminal_at, failure_code) "
                "VALUES (?, 'COMMIT', ?, 'PREPARED', ?, ?, ?, NULL, NULL)",
                (
                    str(operation_id),
                    batch.plan_id,
                    acknowledgement_digest,
                    encoded,
                    encoded,
                ),
            )
            entries = tuple(
                item for item in batch.entries if item.state is QuarantineEntryState.QUARANTINED
            )
            for sequence, entry in enumerate(entries, start=1):
                conflict = entry.object_id in protected
                connection.execute(
                    "INSERT INTO maintenance_operation_entries(operation_id, sequence, "
                    "object_id, byte_length, action, source_state, destination_state, outcome) "
                    "VALUES (?, ?, ?, ?, ?, 'QUARANTINE', ?, NULL)",
                    (
                        str(operation_id),
                        sequence,
                        entry.object_id,
                        entry.byte_length,
                        (
                            MaintenanceAction.RESTORE_CONFLICT.value
                            if conflict
                            else MaintenanceAction.DELETE.value
                        ),
                        "ACTIVE" if conflict else "NONE",
                    ),
                )
            connection.execute(
                "UPDATE quarantine_batches SET state='COMMITTING' WHERE batch_id=?",
                (str(batch_id),),
            )
            connection.execute(
                "INSERT INTO maintenance_events(operation_id, sequence, event_type, object_id, "
                "entry_count, byte_count, occurred_at) VALUES (?, 1, 'PREPARED', NULL, ?, ?, ?)",
                (
                    str(operation_id),
                    len(entries),
                    sum(item.byte_length for item in entries),
                    encoded,
                ),
            )
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id=?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("commit operation did not become visible")
            return self._maintenance_operation(connection, row)

    def mark_operation_applying(
        self,
        operation_id: UUID,
        *,
        now: datetime,
    ) -> MaintenanceOperation:
        """Move exact active intent to APPLYING idempotently."""
        encoded = encode_storage_datetime(now)
        with self._write_connection(allow_maintenance=True) as connection:
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("maintenance operation does not exist")
            operation = self._maintenance_operation(connection, row)
            if operation.state in {
                MaintenanceOperationState.SUCCEEDED,
                MaintenanceOperationState.FAILED,
                MaintenanceOperationState.BLOCKED,
            }:
                return operation
            if operation.state is MaintenanceOperationState.PREPARED:
                connection.execute(
                    "UPDATE maintenance_operations SET state='APPLYING', updated_at=? "
                    "WHERE operation_id=?",
                    (encoded, str(operation_id)),
                )
            updated = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                (str(operation_id),),
            ).fetchone()
            if updated is None:
                raise CatalogError("maintenance operation disappeared")
            return self._maintenance_operation(connection, updated)

    def active_maintenance_operation(self) -> MaintenanceOperation | None:
        """Return the one restart-persistent active operation."""
        with self._read_connection() as connection:
            return self._load_active_operation(connection)

    def complete_quarantine(
        self,
        operation_id: UUID,
        *,
        now: datetime,
    ) -> QuarantineBatch:
        """Publish complete verified quarantine state and clear the write fence."""
        return self._complete_move(operation_id, now=now, quarantine=True)

    def complete_restore(
        self,
        operation_id: UUID,
        *,
        now: datetime,
    ) -> QuarantineBatch:
        """Publish complete verified restore state and clear the write fence."""
        return self._complete_move(operation_id, now=now, quarantine=False)

    def complete_commit(
        self,
        operation_id: UUID,
        *,
        now: datetime,
    ) -> QuarantineBatch:
        """Publish exact removed or conflict-restored outcomes after filesystem work."""
        encoded = encode_storage_datetime(now)
        with self._write_connection(allow_maintenance=True) as connection:
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id=?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("maintenance operation does not exist")
            operation = self._maintenance_operation(connection, row)
            if operation.kind is not MaintenanceOperationKind.COMMIT:
                raise CatalogError("maintenance operation kind conflicts")
            batch = self._batch_for_operation(connection, operation)
            if batch is None:
                raise CatalogError("maintenance batch does not exist")
            if operation.state is MaintenanceOperationState.SUCCEEDED:
                return batch
            if operation.state not in {
                MaintenanceOperationState.PREPARED,
                MaintenanceOperationState.APPLYING,
            }:
                raise CatalogError("maintenance operation is not completable")
            retained = False
            for entry in operation.entries:
                is_retained = entry.action is MaintenanceAction.RESTORE_CONFLICT
                retained = retained or is_retained
                connection.execute(
                    "UPDATE maintenance_operation_entries SET outcome=? "
                    "WHERE operation_id=? AND sequence=?",
                    (
                        "RETAINED" if is_retained else "REMOVED",
                        str(operation_id),
                        entry.sequence,
                    ),
                )
                connection.execute(
                    "UPDATE quarantine_entries SET state=?, committed_at=? "
                    "WHERE batch_id=? AND object_id=?",
                    (
                        "CONFLICT_RETAINED" if is_retained else "COMMITTED_REMOVED",
                        encoded,
                        str(batch.batch_id),
                        entry.object_id,
                    ),
                )
            connection.execute(
                "UPDATE quarantine_batches SET state=?, terminal_at=? WHERE batch_id=?",
                ("BLOCKED" if retained else "COMMITTED", encoded, str(batch.batch_id)),
            )
            connection.execute(
                "UPDATE maintenance_operations SET state='SUCCEEDED', updated_at=?, "
                "terminal_at=? WHERE operation_id=?",
                (encoded, encoded, str(operation_id)),
            )
            sequence = int(
                connection.execute(
                    "SELECT coalesce(max(sequence), 0) + 1 FROM maintenance_events "
                    "WHERE operation_id=?",
                    (str(operation_id),),
                ).fetchone()[0]
            )
            connection.execute(
                "INSERT INTO maintenance_events(operation_id, sequence, event_type, object_id, "
                "entry_count, byte_count, occurred_at) VALUES (?, ?, 'SUCCEEDED', NULL, ?, ?, ?)",
                (
                    str(operation_id),
                    sequence,
                    len(operation.entries),
                    sum(item.byte_length for item in operation.entries),
                    encoded,
                ),
            )
            completed = self._load_quarantine_batch(connection, batch.batch_id)
            if completed is None:
                raise CatalogError("commit completion did not become visible")
            return completed

    def _complete_move(
        self,
        operation_id: UUID,
        *,
        now: datetime,
        quarantine: bool,
    ) -> QuarantineBatch:
        encoded = encode_storage_datetime(now)
        expected_kind = (
            MaintenanceOperationKind.QUARANTINE if quarantine else MaintenanceOperationKind.RESTORE
        )
        with self._write_connection(allow_maintenance=True) as connection:
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id = ?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("maintenance operation does not exist")
            operation = self._maintenance_operation(connection, row)
            if operation.kind is not expected_kind:
                raise CatalogError("maintenance operation kind conflicts")
            if operation.state is MaintenanceOperationState.SUCCEEDED:
                batch = self._batch_for_operation(connection, operation)
                if batch is None:
                    raise CatalogError("maintenance batch did not become visible")
                return batch
            if operation.state not in {
                MaintenanceOperationState.PREPARED,
                MaintenanceOperationState.APPLYING,
            }:
                raise CatalogError("maintenance operation is not completable")
            batch = self._batch_for_operation(connection, operation)
            if batch is None:
                raise CatalogError("maintenance batch does not exist")
            entry_state = "QUARANTINED" if quarantine else "RESTORED"
            time_column = "quarantined_at" if quarantine else "restored_at"
            for entry in operation.entries:
                connection.execute(
                    "UPDATE maintenance_operation_entries SET outcome='MOVED' "
                    "WHERE operation_id=? AND sequence=?",
                    (str(operation_id), entry.sequence),
                )
                connection.execute(
                    f"UPDATE quarantine_entries SET state=?, {time_column}=? "  # noqa: S608
                    "WHERE batch_id=? AND object_id=?",
                    (entry_state, encoded, str(batch.batch_id), entry.object_id),
                )
            batch_state = "QUARANTINED" if quarantine else "RESTORED"
            terminal = None if quarantine else encoded
            connection.execute(
                "UPDATE quarantine_batches SET state=?, terminal_at=? WHERE batch_id=?",
                (batch_state, terminal, str(batch.batch_id)),
            )
            connection.execute(
                "UPDATE maintenance_operations SET state='SUCCEEDED', updated_at=?, "
                "terminal_at=? WHERE operation_id=?",
                (encoded, encoded, str(operation_id)),
            )
            sequence = int(
                connection.execute(
                    "SELECT coalesce(max(sequence), 0) + 1 FROM maintenance_events "
                    "WHERE operation_id=?",
                    (str(operation_id),),
                ).fetchone()[0]
            )
            connection.execute(
                "INSERT INTO maintenance_events(operation_id, sequence, event_type, object_id, "
                "entry_count, byte_count, occurred_at) VALUES (?, ?, 'SUCCEEDED', NULL, ?, ?, ?)",
                (
                    str(operation_id),
                    sequence,
                    len(operation.entries),
                    sum(item.byte_length for item in operation.entries),
                    encoded,
                ),
            )
            completed = self._load_quarantine_batch(connection, batch.batch_id)
            if completed is None:
                raise CatalogError("maintenance completion did not become visible")
            return completed

    @staticmethod
    def _retention_hold(row: sqlite3.Row) -> RetentionHold:
        """Decode one exact persisted retention hold."""
        return RetentionHold(
            hold_id=str(row["hold_id"]),
            object_id=str(row["object_id"]),
            reason=str(row["reason"]),
            created_at=decode_storage_datetime(str(row["created_at"])),
            expires_at=(
                decode_storage_datetime(str(row["expires_at"]))
                if row["expires_at"] is not None
                else None
            ),
            released_at=(
                decode_storage_datetime(str(row["released_at"]))
                if row["released_at"] is not None
                else None
            ),
        )

    def _retention_snapshot_from_connection(
        self,
        connection: sqlite3.Connection,
        *,
        observed_at: datetime,
    ) -> RetentionSnapshot:
        roots: list[RetentionRoot] = []
        for table, object_column, reason in _RETENTION_REFERENCES:
            columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
            primary = tuple(
                str(row["name"])
                for row in sorted(
                    (row for row in columns if int(row["pk"]) > 0),
                    key=lambda row: int(row["pk"]),
                )
            )
            projection = ", ".join((object_column, *primary))
            # Identifiers are closed local constants or schema-owned PK names.
            rows = connection.execute(
                f"SELECT {projection} FROM {table} "  # noqa: S608
                f"WHERE {object_column} IS NOT NULL ORDER BY {projection}"
            ).fetchall()
            for row in rows:
                roots.append(
                    RetentionRoot(
                        object_id=str(row[object_column]),
                        reason=reason,
                        reference_digest=canonical_sha256(
                            {
                                "domain": "openardp:retention-reference-v1",
                                "table": table,
                                "column": object_column,
                                "key": [str(row[column]) for column in primary],
                            }
                        ),
                    )
                )
        observed = encode_storage_datetime(observed_at)
        hold_rows = connection.execute(
            "SELECT * FROM retention_holds WHERE released_at IS NULL "
            "AND (expires_at IS NULL OR expires_at > ?) ORDER BY object_id, hold_id",
            (observed,),
        ).fetchall()
        return RetentionSnapshot(
            catalog_schema_version=self._schema_version_from_connection(connection),
            roots=tuple(
                sorted(
                    set(roots),
                    key=lambda item: (
                        item.object_id,
                        item.reason.value,
                        item.reference_digest,
                    ),
                )
            ),
            holds=tuple(self._retention_hold(row) for row in hold_rows),
            observed_at=observed_at,
        )

    def _load_active_operation(
        self,
        connection: sqlite3.Connection,
    ) -> MaintenanceOperation | None:
        row = connection.execute(
            "SELECT * FROM maintenance_operations "
            "WHERE state IN ('PREPARED', 'APPLYING') ORDER BY created_at LIMIT 1"
        ).fetchone()
        return self._maintenance_operation(connection, row) if row is not None else None

    def _maintenance_operation(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> MaintenanceOperation:
        entry_rows = connection.execute(
            "SELECT * FROM maintenance_operation_entries WHERE operation_id=? ORDER BY sequence",
            (str(row["operation_id"]),),
        ).fetchall()
        return MaintenanceOperation(
            operation_id=UUID(str(row["operation_id"])),
            kind=MaintenanceOperationKind(str(row["kind"])),
            subject_id=str(row["subject_id"]),
            state=MaintenanceOperationState(str(row["state"])),
            acknowledgement_digest=(
                str(row["acknowledgement_digest"])
                if row["acknowledgement_digest"] is not None
                else None
            ),
            created_at=decode_storage_datetime(str(row["created_at"])),
            updated_at=decode_storage_datetime(str(row["updated_at"])),
            terminal_at=(
                decode_storage_datetime(str(row["terminal_at"]))
                if row["terminal_at"] is not None
                else None
            ),
            failure_code=(str(row["failure_code"]) if row["failure_code"] is not None else None),
            entries=tuple(
                MaintenanceOperationEntry(
                    sequence=int(entry["sequence"]),
                    object_id=str(entry["object_id"]),
                    byte_length=int(entry["byte_length"]),
                    action=MaintenanceAction(str(entry["action"])),
                    source_state=cast(
                        Literal["ACTIVE", "QUARANTINE", "NONE"],
                        str(entry["source_state"]),
                    ),
                    destination_state=cast(
                        Literal["ACTIVE", "QUARANTINE", "NONE"],
                        str(entry["destination_state"]),
                    ),
                    outcome=(
                        cast(
                            Literal["MOVED", "REMOVED", "RETAINED", "COPIED"],
                            str(entry["outcome"]),
                        )
                        if entry["outcome"] is not None
                        else None
                    ),
                )
                for entry in entry_rows
            ),
        )

    def _load_quarantine_batch(
        self,
        connection: sqlite3.Connection,
        batch_id: UUID,
    ) -> QuarantineBatch | None:
        row = connection.execute(
            "SELECT * FROM quarantine_batches WHERE batch_id=?", (str(batch_id),)
        ).fetchone()
        if row is None:
            return None
        entry_rows = connection.execute(
            "SELECT * FROM quarantine_entries WHERE batch_id=? ORDER BY object_id",
            (str(batch_id),),
        ).fetchall()
        return QuarantineBatch(
            batch_id=batch_id,
            plan_id=str(row["plan_id"]),
            policy_id=str(row["policy_id"]),
            root_snapshot_id=str(row["root_snapshot_id"]),
            inventory_id=str(row["inventory_id"]),
            state=QuarantineBatchState(str(row["state"])),
            quarantined_at=decode_storage_datetime(str(row["quarantined_at"])),
            not_before=decode_storage_datetime(str(row["not_before"])),
            entry_count=int(row["entry_count"]),
            byte_count=int(row["byte_count"]),
            terminal_at=(
                decode_storage_datetime(str(row["terminal_at"]))
                if row["terminal_at"] is not None
                else None
            ),
            entries=tuple(
                QuarantineEntry(
                    object_id=str(entry["object_id"]),
                    byte_length=int(entry["byte_length"]),
                    reason=str(entry["reason"]),
                    state=QuarantineEntryState(str(entry["state"])),
                    quarantined_at=(
                        decode_storage_datetime(str(entry["quarantined_at"]))
                        if entry["quarantined_at"] is not None
                        else None
                    ),
                    restored_at=(
                        decode_storage_datetime(str(entry["restored_at"]))
                        if entry["restored_at"] is not None
                        else None
                    ),
                    committed_at=(
                        decode_storage_datetime(str(entry["committed_at"]))
                        if entry["committed_at"] is not None
                        else None
                    ),
                )
                for entry in entry_rows
            ),
        )

    def _batch_for_operation(
        self,
        connection: sqlite3.Connection,
        operation: MaintenanceOperation,
    ) -> QuarantineBatch | None:
        row = connection.execute(
            "SELECT batch_id FROM quarantine_batches WHERE plan_id=?",
            (operation.subject_id,),
        ).fetchone()
        return (
            self._load_quarantine_batch(connection, UUID(str(row["batch_id"])))
            if row is not None
            else None
        )


__all__ = ["_SQLiteCatalogMaintenanceMixin"]
