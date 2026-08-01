"""Atomic revision-9 job evolution and watcher schema migration tests."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATION_9, MIGRATIONS, Migration
from openardp.domain.storage import JobSpec
from openardp.ports.catalog import CatalogTooNew, MigrationFailed

NOW = datetime(2026, 8, 1, 11, 0, tzinfo=UTC)
JOB_ID = UUID("018f7e6a-4c00-4000-8000-000000000031")


def test_migration_nine_upgrades_populated_revision_eight_without_job_drift(
    tmp_path: Path,
) -> None:
    """Preserve released job facts while installing truthful new fields/tables."""
    path = tmp_path / "catalog.sqlite3"
    old = SQLiteCatalog(path, migrations=MIGRATIONS[:8])
    old.initialize(now=NOW)
    before = old.create_job(
        JobSpec(
            job_id=JOB_ID,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=2,
            created_at=NOW,
        )
    )

    current = SQLiteCatalog(path)
    assert current.initialize(now=NOW) == 9
    after = current.get_job(JOB_ID)
    assert after is not None
    excluded = {"available_at", "cancellation_requested_at"}
    assert after.model_dump(exclude=excluded) == before.model_dump(exclude=excluded)
    assert after.available_at == NOW
    assert after.cancellation_requested_at is None
    with sqlite3.connect(path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name LIKE 'watch_%'"
            )
        }
        assert tables == {
            "watch_roots",
            "watch_observations",
            "watch_job_targets",
            "watch_events",
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        indexes = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_schema WHERE type='index'")
        }
        assert {
            "jobs_queue_idx",
            "jobs_lease_idx",
            "jobs_active_lease_token_idx",
            "watch_observations_state_idx",
            "watch_job_targets_root_idx",
            "watch_events_job_idx",
        } <= indexes
        jobs_sql = str(
            connection.execute(
                "SELECT sql FROM sqlite_schema WHERE type='table' AND name='jobs'"
            ).fetchone()[0]
        )
        assert "'CANCELLED'" in jobs_sql
        assert "available_at >= created_at" in jobs_sql
        assert "cancellation_requested_at" in jobs_sql


def test_failed_migration_nine_rolls_back_revision_eight_exactly(tmp_path: Path) -> None:
    """Expose either complete revision 8 or complete revision 9, never a half swap."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=MIGRATIONS[:8]).initialize(now=NOW)
    before = tuple(sqlite3.connect(path).iterdump())
    broken = Migration(
        version=9,
        name="broken-watch-jobs",
        statements=(*MIGRATION_9.statements[:5], "INVALID MIGRATION SQL"),
    )
    with pytest.raises(MigrationFailed):
        SQLiteCatalog(path, migrations=(*MIGRATIONS[:8], broken)).initialize(now=NOW)
    assert SQLiteCatalog(path, migrations=MIGRATIONS[:8]).schema_version() == 8
    assert tuple(sqlite3.connect(path).iterdump()) == before


def test_migration_nine_is_append_only_after_released_checksums() -> None:
    """Freeze every prior migration while adding one exact new revision."""
    assert MIGRATION_9.version == 9
    assert MIGRATION_9.name == "local-watcher-and-cancellable-jobs"
    assert len({item.checksum for item in MIGRATIONS}) == 9


def test_twenty_initializers_converge_on_one_revision_nine_upgrade(tmp_path: Path) -> None:
    """Serialize concurrent upgrades and append the released migration exactly once."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=MIGRATIONS[:8]).initialize(now=NOW)

    def initialize(_: int) -> int:
        return SQLiteCatalog(path).initialize(now=NOW)

    with ThreadPoolExecutor(max_workers=10) as executor:
        revisions = tuple(executor.map(initialize, range(20)))
    assert revisions == (9,) * 20
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM schema_migrations WHERE version = 9"
        ).fetchone() == (1,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_revision_nine_reader_rejects_future_history_without_mutation(tmp_path: Path) -> None:
    """Fail closed when a future migration is present and retain its exact history."""
    path = tmp_path / "future.sqlite3"
    catalog = SQLiteCatalog(path)
    assert catalog.initialize(now=NOW) == 9
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
            "VALUES (10, 'future', ?, ?)",
            ("sha256:" + "f" * 64, "2026-08-01T11:00:00.000000Z"),
        )
        connection.commit()
        before = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    with pytest.raises(CatalogTooNew):
        catalog.initialize(now=NOW)
    with sqlite3.connect(path) as connection:
        after = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert after == before


@pytest.mark.parametrize("boundary", range(len(MIGRATION_9.statements) + 1))
def test_every_migration_nine_statement_boundary_rolls_back_and_retries_cleanly(
    tmp_path: Path,
    boundary: int,
) -> None:
    """Inject a failure before/after every statement and retain exact revision 8."""
    path = tmp_path / f"boundary-{boundary}.sqlite3"
    old = SQLiteCatalog(path, migrations=MIGRATIONS[:8])
    old.initialize(now=NOW)
    old.create_job(
        JobSpec(
            job_id=JOB_ID,
            kind="ingest",
            deduplication_key="migration-boundary",
            max_attempts=2,
            created_at=NOW,
        )
    )
    with sqlite3.connect(path) as connection:
        before = tuple(connection.iterdump())
    broken = Migration(
        version=9,
        name=f"broken-watch-jobs-{boundary}",
        statements=(
            *MIGRATION_9.statements[:boundary],
            "THIS IS NOT VALID SQLITE",
        ),
    )
    with pytest.raises(MigrationFailed):
        SQLiteCatalog(path, migrations=(*MIGRATIONS[:8], broken)).initialize(now=NOW)
    with sqlite3.connect(path) as connection:
        assert tuple(connection.iterdump()) == before
    assert SQLiteCatalog(path, migrations=MIGRATIONS[:8]).schema_version() == 8
    assert SQLiteCatalog(path).initialize(now=NOW) == 9
    assert SQLiteCatalog(path).get_job(JOB_ID) is not None
