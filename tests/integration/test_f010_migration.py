"""Migration-7 compatibility and atomicity evidence for F010."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import (
    CURRENT_SCHEMA_VERSION,
    MIGRATION_7,
    MIGRATIONS,
    Migration,
)
from openardp.domain.storage import SourceKey, uuid7_from_parts
from openardp.ports.catalog import CatalogTooNew, MigrationFailed

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
DOCUMENT_ID = uuid7_from_parts(timestamp_ms=1_720_000_000_000, random_bits=10)
F010_TABLES = {
    "reconciliation_runs",
    "block_lineages",
    "block_lineage_members",
    "reconciliation_relations",
    "derivation_slots",
    "derivation_nodes",
    "derivation_dependencies",
    "derivation_events",
}


def _application_rows(path: Path) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            connection.execute(
                "SELECT document_id, connector, source_locator, created_at "
                "FROM documents ORDER BY document_id"
            )
        )


def test_real_revision_six_catalog_upgrades_without_changing_existing_rows(
    tmp_path: Path,
) -> None:
    """Append F010 storage while preserving all released checksums and facts."""
    path = tmp_path / "catalog.sqlite3"
    released = SQLiteCatalog(path, migrations=MIGRATIONS[:6])
    assert released.initialize(now=NOW) == 6
    released.register_document(
        SourceKey(connector="local", locator="/synthetic/existing.txt"),
        document_id=DOCUMENT_ID,
        now=NOW,
    )
    prior_checksums = tuple(migration.checksum for migration in MIGRATIONS[:6])
    rows_before = _application_rows(path)

    current = SQLiteCatalog(path)
    assert current.initialize(now=NOW + timedelta(seconds=1)) == CURRENT_SCHEMA_VERSION
    assert current.initialize(now=NOW + timedelta(seconds=2)) == CURRENT_SCHEMA_VERSION

    assert tuple(migration.checksum for migration in MIGRATIONS[:6]) == prior_checksums
    assert _application_rows(path) == rows_before
    with sqlite3.connect(path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert tables >= F010_TABLES


def test_failed_migration_seven_rolls_back_revision_six_exactly(tmp_path: Path) -> None:
    """Keep the complete released revision-six catalog when new DDL fails."""
    path = tmp_path / "catalog.sqlite3"
    released = SQLiteCatalog(path, migrations=MIGRATIONS[:6])
    assert released.initialize(now=NOW) == 6
    before = path.read_bytes()
    broken = Migration(
        version=7,
        name="broken-f010",
        statements=(
            "CREATE TABLE should_rollback (id INTEGER PRIMARY KEY) STRICT",
            "INVALID SQL",
        ),
    )

    with pytest.raises(MigrationFailed):
        SQLiteCatalog(path, migrations=(*MIGRATIONS[:6], broken)).initialize(now=NOW)

    assert SQLiteCatalog(path, migrations=MIGRATIONS[:6]).schema_version() == 6
    assert path.read_bytes() == before


@pytest.mark.parametrize("statement_index", range(len(MIGRATION_7.statements)))
def test_every_revision_seven_statement_failure_is_atomic(
    tmp_path: Path,
    statement_index: int,
) -> None:
    """Inject failure at every DDL/index boundary and preserve revision six exactly."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=MIGRATIONS[:6]).initialize(now=NOW)
    before = path.read_bytes()
    statements = list(MIGRATION_7.statements)
    statements[statement_index] = "INVALID SQL"
    broken = Migration(
        version=7,
        name="broken-f010-boundary",
        statements=tuple(statements),
    )

    with pytest.raises(MigrationFailed):
        SQLiteCatalog(path, migrations=(*MIGRATIONS[:6], broken)).initialize(now=NOW)

    assert SQLiteCatalog(path, migrations=MIGRATIONS[:6]).schema_version() == 6
    assert path.read_bytes() == before


def test_parallel_revision_seven_initializers_converge(tmp_path: Path) -> None:
    """Serialize concurrent installers and leave one complete migration history."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=MIGRATIONS[:6]).initialize(now=NOW)

    def initialize(index: int) -> int:
        return SQLiteCatalog(path).initialize(now=NOW + timedelta(seconds=index))

    with ThreadPoolExecutor(max_workers=8) as executor:
        versions = tuple(executor.map(initialize, range(8)))

    assert versions == (CURRENT_SCHEMA_VERSION,) * 8
    with sqlite3.connect(path) as connection:
        rows = tuple(
            connection.execute(
                "SELECT version, COUNT(*) FROM schema_migrations GROUP BY version ORDER BY version"
            )
        )
    assert rows == tuple((version, 1) for version in range(1, CURRENT_SCHEMA_VERSION + 1))


def test_revision_six_reader_rejects_revision_seven_without_mutation(tmp_path: Path) -> None:
    """Prevent an older process from opening or rewriting the new schema."""
    path = tmp_path / "catalog.sqlite3"
    assert SQLiteCatalog(path).initialize(now=NOW) == CURRENT_SCHEMA_VERSION
    before = path.read_bytes()

    with pytest.raises(CatalogTooNew):
        SQLiteCatalog(path, migrations=MIGRATIONS[:6]).initialize(now=NOW)

    assert path.read_bytes() == before


def test_revision_seven_tables_are_strict_and_indexes_are_present(tmp_path: Path) -> None:
    """Freeze the intended durable shape and its query backstops."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path).initialize(now=NOW)
    with sqlite3.connect(path) as connection:
        strict = {
            str(row[1]): int(row[5])
            for row in connection.execute("PRAGMA table_list")
            if str(row[1]) in F010_TABLES
        }
        indexes = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_schema WHERE type = 'index'")
        }
        foreign_keys = {
            table: tuple(connection.execute(f"PRAGMA foreign_key_list({table})"))
            for table in F010_TABLES
        }

    assert strict == {table: 1 for table in F010_TABLES}
    assert {
        "block_lineage_members_binding_idx",
        "block_lineage_members_lineage_idx",
        "reconciliation_relations_object_idx",
        "derivation_nodes_current_slot_idx",
        "derivation_dependencies_input_idx",
        "derivation_dependencies_producer_idx",
    } <= indexes
    assert all(str(row[6]).upper() == "RESTRICT" for rows in foreign_keys.values() for row in rows)
    assert len(foreign_keys["derivation_slots"]) == 2
