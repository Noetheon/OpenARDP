"""Atomic additive revision-10 maintenance schema migration tests."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATION_10, MIGRATIONS, Migration
from openardp.ports.catalog import MigrationFailed

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def test_migration_ten_upgrades_revision_nine_additively(tmp_path: Path) -> None:
    """Install exact retention/maintenance tables without changing prior history."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=MIGRATIONS[:9]).initialize(now=NOW)
    before = (
        sqlite3.connect(path)
        .execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version")
        .fetchall()
    )
    assert SQLiteCatalog(path, migrations=MIGRATIONS[:10]).initialize(now=NOW) == 10
    with sqlite3.connect(path) as connection:
        after = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND "
                "(name LIKE 'maintenance_%' OR name LIKE 'quarantine_%' "
                "OR name IN ('retention_holds', 'migration_backups'))"
            )
        }
        assert after[:9] == before
        assert tables == {
            "retention_holds",
            "quarantine_batches",
            "quarantine_entries",
            "maintenance_operations",
            "maintenance_operation_entries",
            "maintenance_events",
            "migration_backups",
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_every_migration_ten_statement_boundary_rolls_back(tmp_path: Path) -> None:
    """Any revision-10 failure exposes exact revision 9 and retries cleanly."""
    for boundary in range(len(MIGRATION_10.statements) + 1):
        path = tmp_path / f"boundary-{boundary}.sqlite3"
        SQLiteCatalog(path, migrations=MIGRATIONS[:9]).initialize(now=NOW)
        with sqlite3.connect(path) as connection:
            before = tuple(connection.iterdump())
        broken = Migration(
            version=10,
            name=f"broken-maintenance-{boundary}",
            statements=(*MIGRATION_10.statements[:boundary], "INVALID SQLITE"),
        )
        with pytest.raises(MigrationFailed):
            SQLiteCatalog(path, migrations=(*MIGRATIONS[:9], broken)).initialize(now=NOW)
        with sqlite3.connect(path) as connection:
            assert tuple(connection.iterdump()) == before
        assert SQLiteCatalog(path, migrations=MIGRATIONS[:9]).schema_version() == 9
        assert SQLiteCatalog(path, migrations=MIGRATIONS[:10]).initialize(now=NOW) == 10


def test_twenty_initializers_converge_on_one_revision_ten(tmp_path: Path) -> None:
    """Serialize concurrent additive upgrades into one checked history row."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=MIGRATIONS[:9]).initialize(now=NOW)

    with ThreadPoolExecutor(max_workers=10) as executor:
        revisions = tuple(
            executor.map(
                lambda _: SQLiteCatalog(path, migrations=MIGRATIONS[:10]).initialize(now=NOW),
                range(20),
            )
        )
    assert revisions == (10,) * 20
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM schema_migrations WHERE version=10"
        ).fetchone() == (1,)


def test_migration_ten_is_append_only() -> None:
    """Freeze prior checksums while introducing one exact revision."""
    assert MIGRATION_10.version == 10
    assert MIGRATION_10.name == "retention-recovery-maintenance"
    assert len({migration.checksum for migration in MIGRATIONS[:10]}) == 10
