"""Paired, verified internal backup, restore and explicit migration tests."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path

import pytest

from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace, WorkspaceIncompatible
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATIONS
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.maintenance import BackupManifest, CapacityReport
from openardp.ports.maintenance import InsufficientSpace, MaintenanceError
from openardp.ports.object_store import ObjectNotFound
from openardp.services.ingestion import IngestionService

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def _regular_snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and not path.name.endswith(("-shm", "-wal"))
    }


def _manifest(backup: Path) -> BackupManifest:
    payload = (backup / "manifest.json").read_bytes()
    manifest = BackupManifest.model_validate_json(payload)
    assert payload == canonical_json_bytes(manifest.model_dump(mode="json"))
    assert (backup / "COMPLETE").read_text(encoding="ascii") == manifest.manifest_id + "\n"
    return manifest


def _legacy_workspace(root: Path) -> None:
    current = LocalWorkspace.initialize(root, now=NOW)
    del current
    for suffix in ("", "-shm", "-wal"):
        (root / f"catalog.sqlite3{suffix}").unlink(missing_ok=True)
    shutil.rmtree(root / "quarantine")
    SQLiteCatalog(root / "catalog.sqlite3", migrations=MIGRATIONS[:10]).initialize(now=NOW)


def test_backup_is_verified_non_mutating_and_excludes_lexical_rows(tmp_path: Path) -> None:
    """Publish marker, catalog and exact objects only after complete verification."""
    root = tmp_path / "source"
    workspace = LocalWorkspace.initialize(root, now=NOW)
    first = workspace.object_store.put_chunks((b"state-a",))
    second = workspace.object_store.put_chunks((b"quarantine-recoverable",))
    workspace.maintenance_store.transition(
        second.object_id,
        to_quarantine=True,
        byte_length=second.byte_length,
    )
    before = _regular_snapshot(root)

    report = workspace.backup(tmp_path / "backup-a", now=NOW)

    assert _regular_snapshot(root) == before
    manifest = _manifest(tmp_path / "backup-a")
    assert report.manifest_id == manifest.manifest_id
    assert manifest.active_object_ids == (first.object_id,)
    assert manifest.quarantined_object_ids == (second.object_id,)
    assert "workspace/catalog.sqlite3" in {item.relative_path for item in manifest.files}
    with sqlite3.connect(tmp_path / "backup-a" / "workspace" / "catalog.sqlite3") as db:
        assert db.execute(
            "SELECT count(*) FROM representation_blocks WHERE indexed_at IS NOT NULL"
        ).fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM block_search_index").fetchone() == (0,)
        assert db.execute("PRAGMA quick_check").fetchone() == ("ok",)


def test_restore_round_trip_is_exact_a_without_later_b(tmp_path: Path) -> None:
    """Restore state A to a fresh path without incorporating B-only object bytes."""
    source = LocalWorkspace.initialize(tmp_path / "source", now=NOW)
    object_a = source.object_store.put_chunks((b"A",))
    source.backup(tmp_path / "backup-a", now=NOW)
    object_b = source.object_store.put_chunks((b"B",))

    report = LocalWorkspace.restore(
        tmp_path / "backup-a",
        tmp_path / "restored-a",
        now=NOW,
    )
    restored = LocalWorkspace.open(tmp_path / "restored-a")

    assert report.manifest_id == _manifest(tmp_path / "backup-a").manifest_id
    assert restored.object_store.verify(object_a.object_id).byte_length == 1
    with pytest.raises(ObjectNotFound):
        restored.object_store.verify(object_b.object_id)
    assert restored.catalog.diagnostics()["quick_check"] == "ok"


def test_restore_rejects_corruption_overlap_and_existing_destination(tmp_path: Path) -> None:
    """Treat a backup as untrusted and never mutate a rejected destination."""
    source = LocalWorkspace.initialize(tmp_path / "source", now=NOW)
    stored = source.object_store.put_chunks((b"evidence",))
    backup = tmp_path / "backup"
    source.backup(backup, now=NOW)
    relative = stored.object_id.removeprefix("sha256:")
    object_path = (
        backup / "workspace" / "objects" / "sha256" / relative[:2] / relative[2:4] / relative[4:]
    )
    object_path.write_bytes(b"corrupt")

    rejected = tmp_path / "rejected"
    with pytest.raises(MaintenanceError):
        LocalWorkspace.restore(backup, rejected, now=NOW)
    assert not rejected.exists()
    with pytest.raises(MaintenanceError, match="overlap"):
        LocalWorkspace.restore(backup, backup / "nested", now=NOW)
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "keep"
    sentinel.write_bytes(b"keep")
    with pytest.raises(MaintenanceError, match="absent"):
        LocalWorkspace.restore(backup, existing, now=NOW)
    assert sentinel.read_bytes() == b"keep"


def test_explicit_revision_ten_migration_publishes_verified_rollback(tmp_path: Path) -> None:
    """Refuse implicit upgrade, then record a pre-upgrade revision-ten backup."""
    root = tmp_path / "legacy"
    _legacy_workspace(root)
    marker = (root / ".openardp-workspace.json").read_bytes()
    assert (root / ".openardp-workspace.json").read_bytes() == marker
    before = _regular_snapshot(root)

    with pytest.raises(WorkspaceIncompatible):
        LocalWorkspace.initialize(root, now=NOW)
    assert _regular_snapshot(root) == before

    migrated = LocalWorkspace.migrate(root, tmp_path / "pre-upgrade", now=NOW)
    manifest = _manifest(tmp_path / "pre-upgrade")
    assert manifest.catalog_schema_version == 10
    assert migrated.catalog.schema_version() == 11
    with sqlite3.connect(root / "catalog.sqlite3") as db:
        row = db.execute(
            "SELECT source_revision, manifest_id, verified FROM migration_backups"
        ).fetchone()
    assert row == (10, manifest.manifest_id, 1)

    LocalWorkspace.restore(tmp_path / "pre-upgrade", tmp_path / "rollback-a", now=NOW)
    restored_catalog = SQLiteCatalog(
        tmp_path / "rollback-a" / "catalog.sqlite3",
        migrations=MIGRATIONS[:10],
    )
    assert restored_catalog.schema_version() == 10


def test_backup_rejects_existing_or_overlapping_destination(tmp_path: Path) -> None:
    """Never overwrite operator state or place a backup inside its source."""
    workspace = LocalWorkspace.initialize(tmp_path / "source", now=NOW)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(MaintenanceError, match="absent"):
        workspace.backup(existing, now=NOW)
    with pytest.raises(MaintenanceError, match="overlap"):
        workspace.backup(workspace.root / "backup", now=NOW)
    assert (
        json.loads((workspace.root / ".openardp-workspace.json").read_bytes())["format"]
        == "openardp-local-workspace"
    )


def test_backup_capacity_rejection_cleans_only_owned_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Publish nothing when required bytes plus reserve exceed current capacity."""
    workspace = LocalWorkspace.initialize(tmp_path / "source", now=NOW)
    workspace.object_store.put_chunks((b"capacity",))

    def reject(required_bytes: int, reserve_bytes: int) -> CapacityReport:
        return CapacityReport(
            required_bytes=required_bytes,
            reserve_bytes=reserve_bytes,
            free_bytes=max(required_bytes + reserve_bytes - 1, 0),
            admitted=False,
        )

    monkeypatch.setattr(workspace.maintenance_store, "capacity", reject)
    destination = tmp_path / "backup"
    with pytest.raises(InsufficientSpace):
        workspace.backup(destination, now=NOW)
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".*.openardp-backup-*.part"))


@pytest.mark.parametrize(
    "boundary",
    ("after_catalog_snapshot", "after_object_copy", "before_backup_publication"),
)
def test_backup_interruption_before_publication_leaves_no_destination(
    tmp_path: Path,
    boundary: str,
) -> None:
    """Clean only the exclusively owned incomplete destination at every stage."""
    workspace = LocalWorkspace.initialize(tmp_path / "source", now=NOW)
    workspace.object_store.put_chunks((b"streamed",))

    def fail(point: str) -> None:
        if point == boundary:
            raise RuntimeError("synthetic backup interruption")

    from openardp.adapters.filesystem_maintenance import backup_workspace

    destination = tmp_path / "backup"
    with pytest.raises(RuntimeError, match="synthetic backup interruption"):
        backup_workspace(
            workspace.root,
            workspace.catalog,
            workspace.maintenance_store,
            destination,
            now=NOW,
            reserve_bytes=0,
            fault=fail,
        )
    assert not destination.exists()


def test_parallel_explicit_migration_commits_once_from_exact_revision(tmp_path: Path) -> None:
    """Only a caller that snapshots revision ten may publish the revision-eleven upgrade."""
    root = tmp_path / "legacy"
    _legacy_workspace(root)

    def migrate(index: int) -> bool:
        try:
            LocalWorkspace.migrate(root, tmp_path / f"backup-{index}", now=NOW)
        except WorkspaceIncompatible:
            return False
        return True

    with ThreadPoolExecutor(max_workers=10) as executor:
        outcomes = tuple(executor.map(migrate, range(20)))
    assert sum(outcomes) == 1
    assert LocalWorkspace.open(root).catalog.schema_version() == 11
    with sqlite3.connect(root / "catalog.sqlite3") as connection:
        assert connection.execute(
            "SELECT count(*) FROM migration_backups WHERE target_revision=11"
        ).fetchone() == (1,)


def test_backup_rejects_missing_root_and_round_trip_excludes_b_catalog_fact(
    tmp_path: Path,
) -> None:
    """Require all roots and restore A catalog history without later B version facts."""
    workspace = LocalWorkspace.initialize(tmp_path / "source", now=NOW)
    ticks = count()
    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        TextParserAdapter(),
        source_factory=LocalSource,
        clock=lambda: NOW + timedelta(seconds=next(ticks)),
    )
    source = tmp_path / "document.txt"
    source.write_text("state A\n", encoding="utf-8")
    os.utime(source, (NOW.timestamp(), NOW.timestamp()))
    first = ingestion.ingest(source)
    workspace.backup(tmp_path / "backup-a", now=NOW, reserve_bytes=0)
    source.write_text("state B\n", encoding="utf-8")
    later = NOW + timedelta(seconds=1)
    os.utime(source, (later.timestamp(), later.timestamp()))
    second = ingestion.ingest(source)
    assert second.scope.version_id != first.scope.version_id

    LocalWorkspace.restore(
        tmp_path / "backup-a",
        tmp_path / "restored-a",
        now=NOW,
        reserve_bytes=0,
    )
    restored = LocalWorkspace.open(tmp_path / "restored-a")
    versions = restored.catalog.list_versions(first.scope.document_id)
    assert tuple(item.version_id for item in versions) == (first.scope.version_id,)

    digest = first.scope.version_id.removeprefix("sha256:")
    rooted_source = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    rooted_source.unlink()
    with pytest.raises(MaintenanceError, match="catalog references"):
        workspace.backup(tmp_path / "invalid-backup", now=NOW, reserve_bytes=0)
    assert not (tmp_path / "invalid-backup").exists()
