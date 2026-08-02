"""F022 explicit storage optimizer CLI contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.interfaces.cli import main


def test_storage_optimize_json_is_body_free_and_counted(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Publish one stable JSON envelope without source text or physical paths."""
    workspace = tmp_path / "workspace"
    source = tmp_path / "source.txt"
    marker = "DO-NOT-LEAK-STORAGE-BODY"
    source.write_text((marker + " repeated evidence\n\n") * 10, encoding="utf-8")
    assert main(["init", "--store", str(workspace), "--json"]) == 0
    capsys.readouterr()
    assert main(["ingest", str(source), "--store", str(workspace), "--json"]) == 0
    capsys.readouterr()

    assert main(["storage-optimize", "--store", str(workspace), "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["ok"] is True
    assert payload["command"] == "storage-optimize"
    assert payload["data"]["eligible_count"] == payload["data"]["completed_count"]
    assert payload["data"]["failed_count"] == 0
    assert marker not in captured.out
    assert str(source) not in captured.out
    assert captured.err == ""
