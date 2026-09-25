"""Agent CLI commands in human and JSON form, as an operator or agent runs them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.interfaces.cli import main

GUIDE = "# Guide\n\n## Setup\n\nInstall the sensor on the north wall.\nUse two screws.\n"


def _run(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, str, str]:
    code = main(arguments)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def store(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """Create the store through `add`, which initializes it on first use."""
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "guide.md").write_text(GUIDE, encoding="utf-8")
    (documents / "table.xlsx").write_text("unsupported", encoding="utf-8")
    store = tmp_path / "store"
    code, out, err = _run(capsys, ["add", str(documents), "--store", str(store)])
    assert code == 0
    assert out.startswith("Processed 1 files") and "1 added" in out
    assert "Skipped 1 files with unsupported types." in out
    assert f"Created workspace {store}" in err and "[1/1] guide.md — added" in err
    return store


def test_add_is_idempotent_and_reports_json_outcomes(
    store: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report unchanged files on repeat runs and failures for unsupported explicit files."""
    documents = tmp_path / "documents"
    code, out, err = _run(
        capsys,
        ["add", str(documents), str(documents / "table.xlsx"), "--store", str(store), "--json"],
    )
    assert code == 0 and err == ""
    payload = json.loads(out)["data"]
    assert [outcome["status"] for outcome in payload["outcomes"]] == ["failed", "unchanged"]
    assert payload["outcomes"][0]["hint"].startswith("Supported file types")


def test_docs_find_read_toc_and_verify_render_compact_text(
    store: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Render every agent command as compact, located, citation-ready text."""
    code, out, _ = _run(capsys, ["docs", "--store", str(store)])
    assert code == 0 and out.startswith("1 documents") and "guide.md — md, 6 lines" in out

    code, out, _ = _run(capsys, ["find", "Where is the sensor installed?", "--store", str(store)])
    assert code == 0 and "guide.md:5-6" in out and "§ Guide > Setup" in out

    code, out, _ = _run(capsys, ["read", "guide.md", "--lines", "5-6", "--store", str(store)])
    assert code == 0 and "5\tInstall the sensor on the north wall." in out
    code, out, _ = _run(
        capsys,
        ["read", "guide.md", "--section", "Setup", "--no-line-numbers", "--store", str(store)],
    )
    assert "\nInstall the sensor on the north wall.\n" in out

    code, out, _ = _run(capsys, ["toc", "guide", "--store", str(store)])
    assert code == 0 and "L3 ## Setup" in out

    code, out, _ = _run(capsys, ["verify", "Use two screws.", "--store", str(store)])
    assert code == 0 and out.startswith("VERIFIED (exact): guide.md:6")
    code, out, _ = _run(capsys, ["verify", "Use three screws.", "--store", str(store)])
    assert code == 0 and out.startswith("NOT FOUND")


def test_agent_commands_emit_stable_json(store: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Return the result models in the standard JSON envelope."""
    code, out, _ = _run(capsys, ["find", "sensor", "--store", str(store), "--json"])
    envelope = json.loads(out)
    assert code == 0 and envelope["ok"] is True and envelope["command"] == "find"
    hit = envelope["data"]["hits"][0]
    assert hit["document"]["label"] == "guide.md" and hit["line_start"] == 5
    code, out, _ = _run(capsys, ["refresh", "--full", "--store", str(store), "--json"])
    assert json.loads(out)["data"]["indexed"] == 1
    code, out, _ = _run(capsys, ["refresh", "--store", str(store)])
    assert out.startswith("Agent index: 1 documents, 0 rebuilt")


def test_agent_view_command_writes_the_view(
    store: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Write the Markdown view and point the operator to INDEX.md."""
    target = tmp_path / "view"
    code, out, _ = _run(capsys, ["agent-view", str(target), "--store", str(store)])
    assert code == 0 and "1 written" in out and str(target / "INDEX.md") in out
    assert (target / "guide.md").read_text(encoding="utf-8") == GUIDE


def test_agent_command_failures_are_classified_with_hints(
    store: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Map unknown documents, bad ranges and missing stores to hinted envelopes."""
    code, _, err = _run(capsys, ["read", "nothing.pdf", "--store", str(store)])
    assert code == 3 and "hint: Run `openardp docs`" in err
    code, out, _ = _run(
        capsys, ["read", "guide.md", "--page", "1", "--store", str(store), "--json"]
    )
    assert code == 4 and json.loads(out)["error"]["code"] == "rejected_input"
    missing = tmp_path / "missing-store"
    code, _, err = _run(capsys, ["docs", "--store", str(missing)])
    assert code == 6 and "openardp init" in err
    code, out, _ = _run(capsys, ["add", str(tmp_path / "typo"), "--store", str(store)])
    assert code == 0 and "this file or folder does not exist" in out
    not_a_store = tmp_path / "plain"
    not_a_store.mkdir()
    code, _, _ = _run(capsys, ["add", str(tmp_path / "documents"), "--store", str(not_a_store)])
    assert code == 6
