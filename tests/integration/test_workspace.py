"""Integration tests for explicit versioned local workspaces."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import (
    LocalWorkspace,
    WorkspaceIncompatible,
    WorkspaceMissing,
)
from openardp.adapters.sqlite_migrations import CURRENT_SCHEMA_VERSION

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


def test_initialize_is_explicit_atomic_and_idempotent(tmp_path: Path) -> None:
    """Publish a canonical marker only after composing valid local stores."""
    root = tmp_path / "workspace"
    first = LocalWorkspace.initialize(root, now=NOW)
    second = LocalWorkspace.initialize(root, now=NOW)

    assert first.root == root.resolve()
    assert second.root == first.root
    assert first.catalog.schema_version() == CURRENT_SCHEMA_VERSION
    marker = root / ".openardp-workspace.json"
    assert json.loads(marker.read_text(encoding="utf-8")) == {
        "catalog": "catalog.sqlite3",
        "format": "openardp-local-workspace",
        "objects": "objects",
        "staging": "staging",
        "version": 1,
    }
    assert marker.read_bytes().endswith(b"}")
    assert not tuple(root.glob("*.part"))


def test_open_never_initializes_a_missing_workspace(tmp_path: Path) -> None:
    """Keep non-init commands from creating or repairing state."""
    root = tmp_path / "missing"
    with pytest.raises(WorkspaceMissing, match="workspace is not initialized"):
        LocalWorkspace.open(root)
    assert not root.exists()


@pytest.mark.parametrize(
    "marker",
    [
        b"not-json",
        b'{"format":"other","version":1}',
        b'{"catalog":"catalog.sqlite3","format":"openardp-local-workspace","objects":"objects","staging":"staging","version":2}',
    ],
)
def test_open_rejects_malformed_foreign_or_newer_markers(
    tmp_path: Path,
    marker: bytes,
) -> None:
    """Reject unrecognized state without silent repair."""
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".openardp-workspace.json").write_bytes(marker)
    before = marker
    with pytest.raises(WorkspaceIncompatible, match="workspace is incompatible"):
        LocalWorkspace.open(root)
    assert (root / ".openardp-workspace.json").read_bytes() == before


def test_initialize_rejects_foreign_nonempty_root(tmp_path: Path) -> None:
    """Do not adopt unrelated directories as application-owned state."""
    root = tmp_path / "foreign"
    root.mkdir()
    sentinel = root / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(WorkspaceIncompatible, match="workspace is incompatible"):
        LocalWorkspace.initialize(root, now=NOW)
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_open_preserves_every_regular_byte_and_mtime(tmp_path: Path) -> None:
    """Validate a current workspace without hidden repair or journal publication."""
    root = tmp_path / "workspace"
    workspace = LocalWorkspace.initialize(root, now=NOW)
    workspace.object_store.put_chunks((b"immutable",))
    before = {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(("-shm", "-wal"))
    }

    opened = LocalWorkspace.open(root)

    after = {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(("-shm", "-wal"))
    }
    assert opened.catalog.schema_version() == CURRENT_SCHEMA_VERSION
    assert after == before


def test_newer_catalog_fails_all_workspace_entrypoints_without_mutation(
    tmp_path: Path,
) -> None:
    """Reject unsupported forward state through open and init byte-for-byte."""
    root = tmp_path / "workspace"
    LocalWorkspace.initialize(root, now=NOW)
    with sqlite3.connect(root / "catalog.sqlite3") as connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
            "VALUES (12, 'future-revision', ?, '2026-07-22T12:00:00.000000Z')",
            ("sha256:" + "f" * 64,),
        )
    before = {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }

    with pytest.raises(WorkspaceIncompatible):
        LocalWorkspace.open(root)
    with pytest.raises(WorkspaceIncompatible):
        LocalWorkspace.initialize(root, now=NOW)

    after = {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }
    assert after == before
