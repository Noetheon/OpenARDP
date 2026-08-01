"""Checksummed additive revision-8 migration tests."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATION_8, MIGRATIONS, Migration
from openardp.ports.catalog import CatalogTooNew, MigrationFailed

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)


def test_migration_eight_is_append_only_checksummed_strict_and_indexed(tmp_path: Path) -> None:
    """Pin revision metadata and required table/index constraints."""
    assert MIGRATION_8.version == 8
    assert MIGRATION_8.name == "visual-evidence"
    assert (
        MIGRATION_8.checksum
        == "sha256:40fd396f436933a84727cb1ef05344bfa05665c2c7f29bfda181a7cb91c45700"
    )
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    assert catalog.initialize(now=NOW) == 8
    with sqlite3.connect(catalog.path) as connection:
        tables = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_schema WHERE type = 'table'"
            )
        }
        assert " STRICT" in tables["visual_page_rasters"]
        assert " STRICT" in tables["visual_evidence"]
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_schema WHERE type = 'index'")
        }
        assert {
            "visual_page_rasters_scope_idx",
            "visual_page_rasters_record_object_idx",
            "visual_page_rasters_raster_object_idx",
            "visual_evidence_scope_idx",
            "visual_evidence_descriptor_object_idx",
            "visual_evidence_crop_object_idx",
        } <= indexes
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_revision_seven_upgrades_without_rewriting_history(tmp_path: Path) -> None:
    """Apply only the pending migration and preserve every prior checksum."""
    path = tmp_path / "catalog.sqlite3"
    old = SQLiteCatalog(path, migrations=MIGRATIONS[:-1])
    assert old.initialize(now=NOW) == 7
    with sqlite3.connect(path) as connection:
        before = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    current = SQLiteCatalog(path)
    assert current.initialize(now=NOW) == 8
    with sqlite3.connect(path) as connection:
        after = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert after[:-1] == before
    assert after[-1] == (8, MIGRATION_8.name, MIGRATION_8.checksum)


def test_revision_eight_failure_rolls_back_and_twenty_initializers_converge(
    tmp_path: Path,
) -> None:
    """Preserve revision 7 on statement failure and serialize concurrent upgrade."""
    failed_path = tmp_path / "failed.sqlite3"
    assert SQLiteCatalog(failed_path, migrations=MIGRATIONS[:-1]).initialize(now=NOW) == 7
    broken = Migration(
        version=8,
        name="visual-evidence",
        statements=(MIGRATION_8.statements[0], "INVALID VISUAL MIGRATION SQL"),
    )
    with pytest.raises(MigrationFailed):
        SQLiteCatalog(failed_path, migrations=(*MIGRATIONS[:-1], broken)).initialize(now=NOW)
    assert SQLiteCatalog(failed_path, migrations=MIGRATIONS[:-1]).schema_version() == 7
    with sqlite3.connect(failed_path) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_schema WHERE name = 'visual_page_rasters'"
            ).fetchone()
            is None
        )

    concurrent_path = tmp_path / "concurrent.sqlite3"
    assert SQLiteCatalog(concurrent_path, migrations=MIGRATIONS[:-1]).initialize(now=NOW) == 7
    with ThreadPoolExecutor(max_workers=10) as executor:
        revisions = tuple(
            executor.map(
                lambda _: SQLiteCatalog(concurrent_path).initialize(now=NOW),
                range(20),
            )
        )
    assert revisions == (8,) * 20
    with sqlite3.connect(concurrent_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = 8"
        ).fetchone() == (1,)


def test_too_new_revision_is_rejected_without_mutation(tmp_path: Path) -> None:
    """Keep downgrade behavior explicit after a future visual schema appears."""
    path = tmp_path / "future.sqlite3"
    catalog = SQLiteCatalog(path)
    assert catalog.initialize(now=NOW) == 8
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
            "VALUES (?, ?, ?, ?)",
            (9, "future", "sha256:" + "f" * 64, "2026-08-01T09:00:00.000000Z"),
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
