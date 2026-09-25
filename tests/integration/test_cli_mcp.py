"""Stable CLI launch and startup safety for the read-only MCP server."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import (
    LocalWorkspace,
    WorkspaceError,
    WorkspaceIncompatible,
)
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import CURRENT_SCHEMA_VERSION
from openardp.interfaces.cli import _parser, _serve_mcp, main
from openardp.interfaces.mcp_protocol import PROTOCOL_REVISION


def _arguments(store: Path, *extra: str) -> object:
    """Parse one bounded MCP launch argument set through the real CLI parser."""
    return _parser().parse_args(["mcp", "--store", str(store), *extra])


def _snapshot(root: Path) -> dict[str, str]:
    """Return exact relative-file digests for startup mutation checks."""
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _transcript() -> bytes:
    """Return one initialize/ready/tools-list/EOF client transcript."""
    messages = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_REVISION},
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    return b"".join(
        json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n" for message in messages
    )


def test_mcp_parser_help_and_launch_limits_are_bounded(capsys: pytest.CaptureFixture[str]) -> None:
    """Publish one additive verb with fixed launch-only deadline and response caps."""
    with pytest.raises(SystemExit) as caught:
        _parser().parse_args(["mcp", "--help"])
    assert caught.value.code == 0
    help_text = capsys.readouterr().out
    assert "--store" in help_text
    assert "--deadline-ms" in help_text
    assert "--response-cap-bytes" in help_text

    arguments = _arguments(
        Path.cwd() / "not-opened",
        "--deadline-ms",
        "120000",
        "--response-cap-bytes",
        "4194304",
    )
    assert arguments.command == "mcp"
    assert arguments.deadline_ms == 120_000
    assert arguments.response_cap_bytes == 4_194_304


def test_mcp_launch_serves_exact_golden_tools_and_does_not_mutate(tmp_path: Path) -> None:
    """Compose the stdio server over one current workspace without startup writes."""
    store = tmp_path / "store"
    LocalWorkspace.initialize(store, now=datetime(2026, 7, 31, tzinfo=UTC))
    before = _snapshot(store)
    source = io.BytesIO(_transcript())
    sink = io.BytesIO()
    assert _serve_mcp(_arguments(store), source=source, sink=sink) == 0
    assert _snapshot(store) == before

    responses = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert len(responses) == 2
    assert responses[0]["result"]["capabilities"] == {"tools": {"listChanged": False}}
    golden_path = Path(__file__).parents[1] / "fixtures" / "mcp" / "tools-list.json"
    golden = json.loads(golden_path.read_bytes())
    assert responses[1]["result"] == golden


def test_missing_workspace_uses_existing_sanitized_cli_classification(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fail before stream serving and never create a missing workspace."""
    missing = tmp_path / "missing"
    assert main(["mcp", "--store", str(missing)]) == 6
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "error[integrity_or_workspace]: workspace or persisted evidence is invalid\n"
        "hint: Create a workspace first: openardp init --store PATH\n"
    )
    assert str(missing) not in captured.err
    assert not missing.exists()


@pytest.mark.parametrize("fault", ("marker", "catalog", "too_new"))
def test_incompatible_corrupt_and_too_new_startup_is_read_only(
    tmp_path: Path,
    fault: str,
) -> None:
    """Reject actual incompatible states without migration, repair or byte drift."""
    store = tmp_path / fault
    LocalWorkspace.initialize(store, now=datetime(2026, 7, 31, tzinfo=UTC))
    catalog_path = store / "catalog.sqlite3"
    if fault == "marker":
        (store / ".openardp-workspace.json").write_bytes(b"{}")
    elif fault == "catalog":
        catalog_path.write_bytes(b"not-a-sqlite-catalog")
    else:
        with sqlite3.connect(catalog_path) as connection:
            connection.execute(
                "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    CURRENT_SCHEMA_VERSION + 1,
                    "future",
                    "sha256:" + "f" * 64,
                    "2026-07-31T00:00:00.000000Z",
                ),
            )
            connection.commit()
    before = _snapshot(store)
    with pytest.raises(WorkspaceError):
        _serve_mcp(_arguments(store), source=io.BytesIO(), sink=io.BytesIO())
    assert _snapshot(store) == before


def test_locked_catalog_fails_closed_without_startup_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Map an actual SQLite lock to workspace failure without changing catalog bytes."""
    store = tmp_path / "locked"
    LocalWorkspace.initialize(store, now=datetime(2026, 7, 31, tzinfo=UTC))
    catalog_path = store / "catalog.sqlite3"
    before = _snapshot(store)
    original = SQLiteCatalog
    monkeypatch.setattr(
        "openardp.adapters.local_workspace.SQLiteCatalog",
        lambda path: original(path, busy_timeout_ms=1),
    )
    with sqlite3.connect(catalog_path, isolation_level=None) as locker:
        locker.execute("BEGIN EXCLUSIVE")
        with pytest.raises(WorkspaceIncompatible):
            _serve_mcp(_arguments(store), source=io.BytesIO(), sink=io.BytesIO())
        locker.execute("ROLLBACK")
    assert _snapshot(store) == before


def test_invalid_launch_caps_fail_before_any_stream_io(tmp_path: Path) -> None:
    """Reject launch-time limit widening or narrowing outside the published range."""
    store = tmp_path / "store"
    LocalWorkspace.initialize(store, now=datetime(2026, 7, 31, tzinfo=UTC))
    for extra in (
        ("--deadline-ms", "999"),
        ("--deadline-ms", "120001"),
        ("--response-cap-bytes", "65535"),
        ("--response-cap-bytes", "4194305"),
    ):
        source = io.BytesIO(_transcript())
        with pytest.raises(ValueError):
            _serve_mcp(_arguments(store, *extra), source=source, sink=io.BytesIO())
        assert source.tell() == 0
