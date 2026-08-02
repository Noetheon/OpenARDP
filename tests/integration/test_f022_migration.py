"""Revision-11 normalized block storage migration and rollback tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATION_11, MIGRATIONS, Migration
from openardp.ports.catalog import CatalogIncompatible, MigrationFailed

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
STAMP = "2026-08-02T12:00:00.000000Z"
OPERATION_ID = "00000000-0000-4000-8000-000000000008"
SUBJECT_ID = "sha256:" + "9" * 64


def _revision_ten_with_indexed_block(path: Path) -> tuple[str, str, str, str]:
    catalog = SQLiteCatalog(path, migrations=MIGRATIONS[:10])
    catalog.initialize(now=NOW)
    document_id = "00000000-0000-4000-8000-000000000001"
    source_id = "sha256:" + "1" * 64
    representation_id = "sha256:" + "2" * 64
    manifest_id = "sha256:" + "3" * 64
    block_object_id = "sha256:" + "4" * 64
    block_id = "00000000-0000-4000-8000-000000000005"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executemany(
            "INSERT INTO objects(object_id, byte_length, registered_at) VALUES (?, ?, ?)",
            ((source_id, 10, STAMP), (manifest_id, 20, STAMP), (block_object_id, 30, STAMP)),
        )
        db.execute(
            "INSERT INTO documents(document_id,connector,source_locator,created_at) "
            "VALUES (?, 'local-file', 'synthetic.txt', ?)",
            (document_id, STAMP),
        )
        db.execute(
            "INSERT INTO document_versions(document_id,version_id,source_object_id,"
            "media_type,source_modified_at,committed_at) VALUES (?, ?, ?, 'text/plain', NULL, ?)",
            (document_id, source_id, source_id, STAMP),
        )
        db.execute(
            "INSERT INTO document_representations(document_id,version_id,representation_id,"
            "parser_name,parser_version,parser_profile,parser_config_hash,"
            "normalization_schema_version,state,attempt_count,revision,active_owner_id,"
            "active_lease_token_hash,lease_expires_at,last_transition_token_hash,"
            "last_failure_code,manifest_object_id,native_object_id,block_count,"
            "warning_codes_json,created_at,updated_at,ready_at) VALUES "
            "(?, ?, ?, 'text', '1', 'default', ?, '0.1.0', 'READY', 1, 2, NULL, NULL, NULL, "
            "?, NULL, ?, ?, 1, '[]', ?, ?, ?)",
            (
                document_id,
                source_id,
                representation_id,
                "sha256:" + "5" * 64,
                "sha256:" + "6" * 64,
                manifest_id,
                source_id,
                STAMP,
                STAMP,
                STAMP,
            ),
        )
        db.execute(
            "INSERT INTO representation_blocks(document_id,version_id,representation_id,"
            "ordinal,block_id,object_id,parent_id,kind,sibling_order,line_start,line_end) "
            "VALUES (?, ?, ?, 0, ?, ?, NULL, 'paragraph', 0, 1, 1)",
            (document_id, source_id, representation_id, block_id, block_object_id),
        )
        cursor = db.execute(
            "INSERT INTO block_search_entries(document_id,version_id,representation_id,"
            "ordinal,block_id,kind,trust_zone,page,slide,line_start,line_end,text_hash,indexed_at) "
            "VALUES (?, ?, ?, 0, ?, 'paragraph', 'external_untrusted', NULL, NULL, 1, 1, ?, ?)",
            (document_id, source_id, representation_id, block_id, "sha256:" + "7" * 64, STAMP),
        )
        db.execute(
            "INSERT INTO block_search_index(rowid,block_text) VALUES (?, 'synthetic evidence')",
            (cursor.lastrowid,),
        )
        db.execute(
            "INSERT INTO maintenance_operations(operation_id,kind,subject_id,state,"
            "acknowledgement_digest,created_at,updated_at,terminal_at,failure_code) "
            "VALUES (?, 'BACKUP', ?, 'SUCCEEDED', NULL, ?, ?, ?, NULL)",
            (OPERATION_ID, SUBJECT_ID, STAMP, STAMP, STAMP),
        )
        db.execute(
            "INSERT INTO maintenance_events(operation_id,sequence,event_type,object_id,"
            "entry_count,byte_count,occurred_at) VALUES (?, 1, 'SUCCEEDED', NULL, 1, 30, ?)",
            (OPERATION_ID, STAMP),
        )
    return document_id, source_id, representation_id, block_id


def test_revision_eleven_preserves_index_row_and_normalizes_scope(tmp_path: Path) -> None:
    """Migrate one indexed block without identity, coverage or relational drift."""
    path = tmp_path / "catalog.sqlite3"
    expected = _revision_ten_with_indexed_block(path)

    assert SQLiteCatalog(path).initialize(now=NOW) == 11

    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT document_id,version_id,representation_id,block_id,indexed_at "
            "FROM representation_block_projection"
        ).fetchone()
        assert row == (*expected, STAMP)
        assert db.execute("SELECT count(*) FROM block_search_index").fetchone() == (1,)
        assert db.execute("SELECT count(*) FROM lineage_block_keys").fetchone() == (0,)
        assert db.execute(
            "SELECT kind,state,subject_id FROM maintenance_operations WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone() == ("BACKUP", "SUCCEEDED", SUBJECT_ID)
        assert db.execute(
            "SELECT event_type,entry_count,byte_count FROM maintenance_events WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone() == ("SUCCEEDED", 1, 30)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_revision_eleven_requires_normalized_projection_view(tmp_path: Path) -> None:
    """The normalized compatibility projection is part of the revision contract."""
    path = tmp_path / "catalog.sqlite3"
    catalog = SQLiteCatalog(path)
    catalog.initialize(now=NOW)
    with sqlite3.connect(path) as db:
        db.execute("DROP VIEW representation_block_projection")

    with pytest.raises(CatalogIncompatible, match="views do not match"):
        catalog.schema_version()


def test_every_revision_eleven_statement_boundary_rolls_back(tmp_path: Path) -> None:
    """Expose exact revision ten after any injected schema-statement failure."""
    for boundary in range(len(MIGRATION_11.statements) + 1):
        path = tmp_path / f"boundary-{boundary}.sqlite3"
        SQLiteCatalog(path, migrations=MIGRATIONS[:10]).initialize(now=NOW)
        with sqlite3.connect(path) as db:
            before = tuple(db.iterdump())
        broken = Migration(
            version=11,
            name=f"broken-storage-{boundary}",
            statements=(*MIGRATION_11.statements[:boundary], "INVALID SQLITE"),
        )
        with pytest.raises(MigrationFailed):
            SQLiteCatalog(path, migrations=(*MIGRATIONS[:10], broken)).initialize(now=NOW)
        with sqlite3.connect(path) as db:
            assert tuple(db.iterdump()) == before
        assert SQLiteCatalog(path, migrations=MIGRATIONS[:10]).schema_version() == 10
