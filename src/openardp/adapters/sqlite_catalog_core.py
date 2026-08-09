"""Catalog initialization, storage optimization, and source facts."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.adapters.sqlite_catalog_support import (
    _MAINTENANCE_NAMESPACE,
    _RETENTION_REFERENCES,
    _SCHEMA_TABLES,
    _SCHEMA_VIEWS,
    _STORAGE_OPTIMIZATION_SUBJECT,
    _canonical_references,
)
from openardp.adapters.sqlite_document_queries import (
    list_document_summaries as project_document_summaries,
)
from openardp.adapters.sqlite_document_queries import load_document_head as project_document_head
from openardp.adapters.sqlite_document_queries import (
    load_document_status_snapshot as project_document_status_snapshot,
)
from openardp.domain.ingestion import (
    DocumentHead,
    DocumentStatusSnapshot,
    DocumentSummary,
    IngestionEvent,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationScope,
)
from openardp.domain.maintenance import (
    MaintenanceOperationKind,
    MaintenanceOperationState,
    RootReason,
)
from openardp.domain.storage import (
    DocumentVersion,
    LogicalDocument,
    ObjectReference,
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
    InvalidObjectReference,
    MaintenanceRecoveryRequired,
    MigrationFailed,
    RepresentationConflict,
    SearchCapabilityUnavailable,
    VersionConflict,
)


class _SQLiteCatalogCoreMixin(_SQLiteCatalogBase):
    """Catalog initialization, storage optimization, and source facts."""

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

    def initialize_current(self, *, now: datetime) -> int:
        """Create a fresh current catalog or validate an existing current revision."""
        if not self._path.exists():
            return self.initialize(now=now)
        current = self.schema_version()
        if current != self._migrations[-1].version:
            raise CatalogIncompatible("catalog requires explicit migration")
        return current

    def schema_version(self) -> int:
        """Return the compatible installed catalog revision without mutation."""
        if not self._path.exists():
            raise CatalogIncompatible("catalog is not initialized")
        connection = self._connect_readonly()
        try:
            return self._validate_history(connection)
        finally:
            connection.close()

    @contextmanager
    def consistent_backup(
        self,
        staged_catalog: Path,
        *,
        now: datetime,
        migrate_at_exit: bool = False,
        manifest_id_supplier: Callable[[], str] | None = None,
        expected_revision: int | None = None,
    ) -> Iterator[int]:
        """Hold the writer boundary across online backup and optional migration."""
        if staged_catalog.exists():
            raise ValueError("staged backup catalog must not exist")
        coordination = self._connect()
        transaction_started = False
        current = 0
        try:
            coordination.execute("BEGIN IMMEDIATE")
            transaction_started = True
            current = self._validate_history(coordination)
            if expected_revision is not None and current != expected_revision:
                raise MigrationFailed("catalog revision changed before paired backup")
            if current == self._migrations[-1].version:
                active = coordination.execute(
                    "SELECT 1 FROM maintenance_operations "
                    "WHERE state IN ('PREPARED', 'APPLYING') LIMIT 1"
                ).fetchone()
                if active is not None:
                    raise MaintenanceRecoveryRequired("maintenance recovery is required")
            source = self._connect_readonly()
            target = sqlite3.connect(staged_catalog, autocommit=True)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            yield current
            if migrate_at_exit:
                if manifest_id_supplier is None:
                    raise MigrationFailed("migration backup identity is unavailable")
                applied_at = encode_storage_datetime(now)
                for migration in self._migrations[current:]:
                    for statement in migration.statements:
                        coordination.execute(statement)
                    coordination.execute(
                        "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                        "VALUES (?, ?, ?, ?)",
                        (migration.version, migration.name, migration.checksum, applied_at),
                    )
                if current < self._migrations[-1].version:
                    coordination.execute(
                        "INSERT INTO migration_backups(target_revision, source_revision, "
                        "manifest_id, created_at, verified) VALUES (?, ?, ?, ?, 1)",
                        (
                            self._migrations[-1].version,
                            current,
                            manifest_id_supplier(),
                            applied_at,
                        ),
                    )
                if coordination.execute("PRAGMA foreign_key_check").fetchall():
                    raise MigrationFailed("catalog foreign-key validation failed")
                coordination.execute("COMMIT")
                transaction_started = False
            else:
                coordination.execute("ROLLBACK")
                transaction_started = False
        except (CatalogError, ValueError):
            if transaction_started:
                coordination.execute("ROLLBACK")
            raise
        except sqlite3.Error as error:
            if transaction_started:
                coordination.execute("ROLLBACK")
            raise MigrationFailed("catalog backup or migration failed") from error
        except Exception:
            if transaction_started:
                coordination.execute("ROLLBACK")
            raise
        finally:
            coordination.close()

    def normalize_backup_copy(self, path: Path) -> tuple[int, tuple[str, ...]]:
        """Remove disposable lexical rows from a staged catalog and verify it."""
        connection = sqlite3.connect(path, autocommit=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            current = self._validate_history(connection)
            connection.execute("BEGIN IMMEDIATE")
            if current >= 4:
                connection.execute("DELETE FROM block_search_index")
                if current >= 11:
                    connection.execute(
                        "UPDATE representation_blocks SET trust_zone = NULL, page = NULL, "
                        "slide = NULL, text_hash = NULL, indexed_at = NULL"
                    )
                else:
                    connection.execute("DELETE FROM block_search_entries")
            connection.execute("COMMIT")
            connection.execute("VACUUM")
            if str(connection.execute("PRAGMA quick_check").fetchone()[0]) != "ok":
                raise CatalogIncompatible("backup catalog integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise CatalogIncompatible("backup catalog foreign-key check failed")
            checksums = tuple(
                str(row[0])
                for row in connection.execute(
                    "SELECT checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            )
            return current, checksums
        finally:
            connection.close()

    def backup_root_object_ids(self) -> tuple[str, ...]:
        """Return every authoritative object root available at the installed revision."""
        connection = self._connect_readonly()
        try:
            self._validate_history(connection)
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type='table'"
                ).fetchall()
            }
            identifiers: set[str] = set()
            for table, object_column, _reason in _RETENTION_REFERENCES:
                if table not in tables:
                    continue
                identifiers.update(
                    str(row[0])
                    for row in connection.execute(
                        f"SELECT {object_column} FROM {table} "  # noqa: S608
                        f"WHERE {object_column} IS NOT NULL"
                    ).fetchall()
                )
            return tuple(sorted(identifiers))
        finally:
            connection.close()

    def eligible_derived_block_objects(self) -> tuple[StoredObject, ...]:
        """Return block objects that have no authoritative non-block reference."""
        with self._read_connection() as connection:
            active = connection.execute(
                "SELECT 1 FROM maintenance_operations "
                "WHERE state IN ('PREPARED', 'APPLYING') LIMIT 1"
            ).fetchone()
            if active is not None:
                raise MaintenanceRecoveryRequired("maintenance recovery is required")
            return self._eligible_derived_block_objects(connection)

    def claim_storage_optimization(
        self,
        *,
        now: datetime,
    ) -> tuple[UUID, tuple[StoredObject, ...]]:
        """Persist or resume the exclusive optimizer fence and freeze eligibility."""
        encoded = encode_storage_datetime(now)
        with self._write_connection(allow_maintenance=True) as connection:
            active = self._load_active_operation(connection)
            if active is not None:
                if (
                    active.kind is not MaintenanceOperationKind.STORAGE_OPTIMIZE
                    or active.subject_id != _STORAGE_OPTIMIZATION_SUBJECT
                ):
                    raise MaintenanceRecoveryRequired("another maintenance operation is active")
                operation_id = active.operation_id
            else:
                generation = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM maintenance_operations WHERE kind='STORAGE_OPTIMIZE'"
                    ).fetchone()[0]
                )
                operation_id = uuid5(
                    _MAINTENANCE_NAMESPACE,
                    f"storage-optimize:{encoded}:{generation}",
                )
                connection.execute(
                    "INSERT INTO maintenance_operations(operation_id, kind, subject_id, state, "
                    "acknowledgement_digest, created_at, updated_at, terminal_at, failure_code) "
                    "VALUES (?, 'STORAGE_OPTIMIZE', ?, 'APPLYING', NULL, ?, ?, NULL, NULL)",
                    (
                        str(operation_id),
                        _STORAGE_OPTIMIZATION_SUBJECT,
                        encoded,
                        encoded,
                    ),
                )
                connection.execute(
                    "INSERT INTO maintenance_events(operation_id, sequence, event_type, "
                    "object_id, entry_count, byte_count, occurred_at) "
                    "VALUES (?, 1, 'APPLYING', NULL, 0, 0, ?)",
                    (str(operation_id), encoded),
                )
            return operation_id, self._eligible_derived_block_objects(connection)

    def complete_storage_optimization(
        self,
        operation_id: UUID,
        *,
        entry_count: int,
        byte_count: int,
        now: datetime,
    ) -> None:
        """Publish terminal optimizer evidence and release its exclusive fence."""
        if min(entry_count, byte_count) < 0:
            raise ValueError("optimization counts must be non-negative")
        encoded = encode_storage_datetime(now)
        with self._write_connection(allow_maintenance=True) as connection:
            row = connection.execute(
                "SELECT * FROM maintenance_operations WHERE operation_id=?",
                (str(operation_id),),
            ).fetchone()
            if row is None:
                raise CatalogError("storage optimization operation does not exist")
            operation = self._maintenance_operation(connection, row)
            if operation.kind is not MaintenanceOperationKind.STORAGE_OPTIMIZE:
                raise CatalogError("maintenance operation kind conflicts")
            if operation.state is MaintenanceOperationState.SUCCEEDED:
                return
            if operation.state not in {
                MaintenanceOperationState.PREPARED,
                MaintenanceOperationState.APPLYING,
            }:
                raise CatalogError("storage optimization operation is not completable")
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
                "INSERT INTO maintenance_events(operation_id, sequence, event_type, "
                "object_id, entry_count, byte_count, occurred_at) "
                "VALUES (?, ?, 'SUCCEEDED', NULL, ?, ?, ?)",
                (
                    str(operation_id),
                    sequence,
                    entry_count,
                    byte_count,
                    encoded,
                ),
            )

    @staticmethod
    def _eligible_derived_block_objects(
        connection: sqlite3.Connection,
    ) -> tuple[StoredObject, ...]:
        """Project one transactionally frozen, authoritative-reference-safe inventory."""
        non_block_references = tuple(
            (table, column)
            for table, column, reason in _RETENTION_REFERENCES
            if reason is not RootReason.TEXT_BLOCK
        )
        non_block_ids: set[str] = set()
        for table, column in non_block_references:
            non_block_ids.update(
                str(row[0])
                for row in connection.execute(
                    f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"  # noqa: S608
                ).fetchall()
            )
        rows = connection.execute(
            "SELECT DISTINCT b.object_id, o.byte_length FROM representation_blocks AS b "
            "JOIN objects AS o ON o.object_id = b.object_id ORDER BY b.object_id"
        ).fetchall()
        return tuple(
            StoredObject(object_id=str(row["object_id"]), byte_length=int(row["byte_length"]))
            for row in rows
            if str(row["object_id"]) not in non_block_ids
        )

    def compact_catalog_storage(self) -> tuple[int, int]:
        """Explicitly reclaim free pages after validating the current idle catalog."""
        before = self._path.stat().st_size
        connection = self._connect()
        try:
            current = self._validate_history(connection)
            if current != self._migrations[-1].version:
                raise CatalogIncompatible("catalog requires explicit migration")
            active = connection.execute(
                "SELECT 1 FROM maintenance_operations "
                "WHERE state IN ('PREPARED', 'APPLYING') LIMIT 1"
            ).fetchone()
            if active is not None:
                raise MaintenanceRecoveryRequired("maintenance recovery is required")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("VACUUM")
            if str(connection.execute("PRAGMA quick_check").fetchone()[0]) != "ok":
                raise CatalogIncompatible("compacted catalog integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise CatalogIncompatible("compacted catalog foreign-key check failed")
        except sqlite3.Error as error:
            raise CatalogError("catalog compaction failed") from error
        finally:
            connection.close()
        return before, self._path.stat().st_size

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

    def get_document_head(self, document_id: UUID) -> DocumentHead | None:
        """Return the current successful representation observation."""
        with self._read_connection() as connection:
            return project_document_head(connection, document_id, convert=self._head_from_row)

    def get_document_status_snapshot(
        self,
        document_id: UUID,
    ) -> DocumentStatusSnapshot | None:
        """Return document, current head and its header without loading projections."""
        with self._read_connection() as connection:
            return project_document_status_snapshot(
                connection,
                document_id,
                load_document=self._load_document_by_id,
                load_representation_row=self._load_representation_row,
                convert_head=self._head_from_row,
                convert_representation=self._representation_from_row,
            )

    def list_document_summaries(self) -> tuple[DocumentSummary, ...]:
        """Return deterministic document metadata without block bodies."""
        with self._read_connection() as connection:
            return project_document_summaries(connection, warning_codes=self._warning_codes)

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
                "SELECT b.*, o.byte_length FROM representation_block_projection AS b "
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

    def _connect_readonly(self) -> sqlite3.Connection:
        """Open one existing catalog through SQLite's true read-only URI mode."""
        try:
            uri = self._path.resolve(strict=True).as_uri() + "?mode=ro"
        except FileNotFoundError:
            raise CatalogIncompatible("catalog is not initialized") from None
        connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=self._busy_timeout_ms / 1000,
            autocommit=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = EXTRA")
        connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA read_uncommitted = OFF")
        if int(connection.execute("PRAGMA synchronous").fetchone()[0]) != 3:
            connection.close()
            raise CatalogError("SQLite synchronous EXTRA mode is required")
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
        expected_views = _SCHEMA_VIEWS.get(highest, frozenset())
        views = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'view'"
            ).fetchall()
        }
        if not expected_views.issubset(views):
            raise CatalogIncompatible("catalog views do not match migration history")
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
    def _write_connection(
        self,
        *,
        allow_maintenance: bool = False,
    ) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        transaction_started = False
        try:
            current = self._validate_history(connection)
            if current != self._migrations[-1].version:
                raise CatalogIncompatible("catalog must be initialized to the current revision")
            self._configure_persistent_profile(connection)
            connection.execute("BEGIN IMMEDIATE")
            transaction_started = True
            if current >= 10 and not allow_maintenance:
                active = connection.execute(
                    "SELECT 1 FROM maintenance_operations "
                    "WHERE state IN ('PREPARED', 'APPLYING') LIMIT 1"
                ).fetchone()
                if active is not None:
                    raise MaintenanceRecoveryRequired("maintenance recovery is required")
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
        connection = self._connect_readonly()
        transaction_started = False
        try:
            current = self._validate_history(connection)
            if current != self._migrations[-1].version:
                raise CatalogIncompatible("catalog must be initialized to the current revision")
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
            and _canonical_references(left.references) == _canonical_references(right.references)
        )

    def _schema_version_from_connection(self, connection: sqlite3.Connection) -> int:
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        if row is None or row[0] is None:
            raise CatalogIncompatible("catalog migration history is empty")
        return int(row[0])

    def _fault_point(self, point: str) -> None:
        """Provide a private deterministic transaction boundary for failure tests."""
        del point


__all__ = ["_SQLiteCatalogCoreMixin"]
