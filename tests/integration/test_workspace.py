"""Integration tests for explicit versioned local workspaces."""

from __future__ import annotations

import json
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
