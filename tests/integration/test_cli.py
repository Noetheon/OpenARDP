"""Integration tests for the installed stable F004 command surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from openardp.interfaces.cli import _execute, main


def _installed_openardp() -> Path:
    """Return the environment's actual cross-platform console entry point."""
    executable = "openardp.exe" if os.name == "nt" else "openardp"
    command = Path(sys.executable).parent / executable
    assert command.is_file()
    return command


def _run_installed(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the installed command with deterministic UTF-8 capture."""
    return subprocess.run(  # noqa: S603 -- executable is derived from the active environment
        [str(_installed_openardp()), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _invoke_json(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, dict[str, object], str]:
    code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1
    return code, json.loads(lines[0]), captured.err


def test_installed_entry_point_help_and_missing_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose help while keeping non-init commands from creating state."""
    completed = subprocess.run(
        [sys.executable, "-m", "openardp.interfaces.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "init" in completed.stdout
    assert "ingest" in completed.stdout

    missing = tmp_path / "missing"
    code, payload, stderr = _invoke_json(capsys, ["list", "--store", str(missing)])
    assert code == 6
    assert payload["ok"] is False
    assert payload["error"] == {
        "code": "integrity_or_workspace",
        "message": "workspace or persisted evidence is invalid",
    }
    assert stderr == ""
    assert not missing.exists()


def test_all_six_json_commands_are_stable_and_body_minimizing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run the complete command workflow with one stdout envelope per invocation."""
    workspace = tmp_path / "store"
    source = tmp_path / "evidence.md"
    source.write_text(
        "# Title\x1b[31m\n\nDO-NOT-LEAK-THIS-PARAGRAPH",
        encoding="utf-8",
    )

    code, initialized, stderr = _invoke_json(
        capsys,
        ["init", "--store", str(workspace)],
    )
    assert (code, initialized["command"], initialized["ok"], stderr) == (
        0,
        "init",
        True,
        "",
    )

    code, ingested, _ = _invoke_json(
        capsys,
        ["ingest", str(source), "--store", str(workspace)],
    )
    assert code == 0
    ingest_data = ingested["data"]
    assert isinstance(ingest_data, dict)
    scope = ingest_data["scope"]
    assert isinstance(scope, dict)
    document_id = str(scope["document_id"])
    assert "DO-NOT-LEAK" not in json.dumps(ingested)

    code, listed, _ = _invoke_json(capsys, ["list", "--store", str(workspace)])
    assert code == 0
    assert "DO-NOT-LEAK" not in json.dumps(listed)

    code, status, _ = _invoke_json(
        capsys,
        ["status", str(source), "--store", str(workspace)],
    )
    assert code == 0
    status_data = status["data"]
    assert isinstance(status_data, dict)
    assert status_data["freshness"] == "CURRENT"
    assert status_data["integrity_coverage"] == "HEAD"
    assert "DO-NOT-LEAK" not in json.dumps(status)

    code, full_status, _ = _invoke_json(
        capsys,
        ["status", str(source), "--full-integrity", "--store", str(workspace)],
    )
    assert code == 0
    full_status_data = full_status["data"]
    assert isinstance(full_status_data, dict)
    assert full_status_data["freshness"] == "CURRENT"
    assert full_status_data["integrity_coverage"] == "FULL"

    code, outlined, _ = _invoke_json(
        capsys,
        ["outline", document_id, "--store", str(workspace)],
    )
    assert code == 0
    outline_data = outlined["data"]
    assert isinstance(outline_data, list)
    assert len(outline_data) == 1
    heading = outline_data[0]
    assert isinstance(heading, dict)
    block_id = str(heading["block_id"])
    assert "DO-NOT-LEAK" not in json.dumps(outlined)

    source.unlink()
    code, block, _ = _invoke_json(
        capsys,
        ["get", block_id, "--store", str(workspace)],
    )
    assert code == 0
    block_data = block["data"]
    assert isinstance(block_data, dict)
    assert block_data["text"] == "Title\x1b[31m"
    raw = json.dumps(block, ensure_ascii=False)
    assert "\x1b" not in raw
    assert "\\u001b" in raw


def test_search_and_reindex_json_commands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose search and reindex through the stable JSON envelope without full bodies."""
    workspace = tmp_path / "store"
    source = tmp_path / "searchable.txt"
    source.write_text("alpha token for retrieval\n", encoding="utf-8")
    assert main(["init", "--store", str(workspace)]) == 0
    assert main(["ingest", str(source), "--store", str(workspace)]) == 0
    capsys.readouterr()

    code, searched, _ = _invoke_json(
        capsys,
        ["search", "alpha", "--store", str(workspace)],
    )
    assert code == 0
    assert searched["ok"] is True
    assert searched["command"] == "search"
    data = searched["data"]
    assert isinstance(data, dict)
    assert int(data["returned"]) >= 1
    hits = data["hits"]
    assert isinstance(hits, list)
    assert hits
    first = hits[0]
    assert isinstance(first, dict)
    assert "snippet" in first
    assert "block_id" in first
    assert "text" not in first
    assert "body" not in first

    code, reindexed, _ = _invoke_json(capsys, ["reindex", "--store", str(workspace)])
    assert code == 0
    assert reindexed["ok"] is True
    report = reindexed["data"]
    assert isinstance(report, dict)
    scopes = report["scopes"]
    assert isinstance(scopes, list)
    assert scopes

    code, rejected, _ = _invoke_json(
        capsys,
        ["search", "", "--store", str(workspace)],
    )
    assert code == 4
    assert rejected["ok"] is False


def test_workspace_backup_and_restore_json_commands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose paired recovery without overloading quarantine restore authority."""
    source = tmp_path / "source"
    assert main(["init", "--store", str(source)]) == 0
    capsys.readouterr()

    code, backed_up, stderr = _invoke_json(
        capsys,
        [
            "workspace-backup",
            "--store",
            str(source),
            "--destination",
            str(tmp_path / "backup"),
        ],
    )
    assert (code, backed_up["ok"], stderr) == (0, True, "")

    code, restored, stderr = _invoke_json(
        capsys,
        [
            "workspace-restore",
            "--backup",
            str(tmp_path / "backup"),
            "--destination",
            str(tmp_path / "restored"),
        ],
    )
    assert (code, restored["ok"], stderr) == (0, True, "")
    assert (tmp_path / "restored" / ".openardp-workspace.json").is_file()


def test_json_usage_and_not_found_failures_are_single_sanitized_envelopes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Map parser and query errors to stable codes without tracebacks or bodies."""
    code, usage, stderr = _invoke_json(capsys, ["ingest"])
    assert code == 2
    assert usage["error"] == {
        "code": "invalid_usage",
        "message": "command usage is invalid",
    }
    assert stderr == ""


def test_internal_dispatch_rejects_unknown_command_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Characterize the closed command-dispatch fallback before helper extraction."""
    workspace = tmp_path / "store"
    assert main(["init", "--store", str(workspace)]) == 0
    capsys.readouterr()
    before = tuple(workspace.rglob("*"))
    with pytest.raises(ValueError, match="invalid command usage"):
        _execute(Namespace(command="unknown", store=str(workspace)))
    assert tuple(workspace.rglob("*")) == before

    workspace = tmp_path / "store"
    assert main(["init", "--store", str(workspace)]) == 0
    capsys.readouterr()
    code, missing, stderr = _invoke_json(
        capsys,
        [
            "get",
            "efe2cf3a-3c22-8c00-adcc-237de0936768",
            "--store",
            str(workspace),
        ],
    )
    assert code == 3
    assert missing["error"] == {
        "code": "not_found",
        "message": "requested evidence was not found",
    }
    assert stderr == ""


def test_installed_entry_point_runs_all_commands_in_json_and_human_modes(
    tmp_path: Path,
) -> None:
    """Exercise both output contracts through the installed console executable."""
    workspace = tmp_path / "installed-store"
    source = tmp_path / "installed.md"
    source.write_text("# Installed title\n\nPRIVATE-PARAGRAPH", encoding="utf-8")

    def json_command(*arguments: str) -> dict[str, object]:
        completed = _run_installed(*arguments, "--json")
        assert completed.returncode == 0, completed.stderr
        assert completed.stderr == ""
        assert len(completed.stdout.splitlines()) == 1
        payload: dict[str, object] = json.loads(completed.stdout)
        assert payload["ok"] is True
        return payload

    store_arguments = ("--store", str(workspace))
    initialized = json_command("init", *store_arguments)
    ingested = json_command("ingest", str(source), *store_arguments)
    ingest_data = ingested["data"]
    assert isinstance(ingest_data, dict)
    scope = ingest_data["scope"]
    assert isinstance(scope, dict)
    document_id = str(scope["document_id"])
    listed = json_command("list", *store_arguments)
    status = json_command("status", str(source), *store_arguments)
    outlined = json_command("outline", document_id, *store_arguments)
    outline_data = outlined["data"]
    assert isinstance(outline_data, list)
    heading = outline_data[0]
    assert isinstance(heading, dict)
    block_id = str(heading["block_id"])
    fetched = json_command("get", block_id, *store_arguments)

    assert initialized["command"] == "init"
    assert fetched["command"] == "get"
    for payload in (initialized, ingested, listed, status, outlined):
        assert "PRIVATE-PARAGRAPH" not in json.dumps(payload)

    human_commands = (
        ("init", *store_arguments),
        ("ingest", str(source), *store_arguments),
        ("list", *store_arguments),
        ("status", str(source), *store_arguments),
        ("outline", document_id, *store_arguments),
        ("get", block_id, *store_arguments),
    )
    human_results = tuple(_run_installed(*arguments) for arguments in human_commands)
    assert all(result.returncode == 0 for result in human_results)
    assert all(result.stderr == "" for result in human_results)
    assert "Initialized OpenARDP workspace" in human_results[0].stdout
    assert "Ingested" in human_results[1].stdout
    assert document_id in human_results[2].stdout
    assert human_results[3].stdout.strip() == "CURRENT\tHEAD"
    assert "Installed title" in human_results[4].stdout
    assert '"text": "Installed title"' in human_results[5].stdout
    assert all("PRIVATE-PARAGRAPH" not in result.stdout for result in human_results[:-1])
