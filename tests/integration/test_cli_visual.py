"""Stable identifier-scoped CLI contracts for F011 visual evidence."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.interfaces.cli import main
from tests.error_envelopes import without_hint
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_service_support import prepared_pdf_visual_service
from tests.integration.visual_support import prepared_visual


def _json_call(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, dict[str, object], str]:
    code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    return code, json.loads(captured.out), captured.err


def _visual_workspace(tmp_path: Path):
    prepared = tmp_path / "prepared"
    catalog, _, commit = prepared_visual(prepared)
    catalog.commit_visual_evidence(commit)
    workspace_root = tmp_path / "workspace"
    LocalWorkspace.initialize(workspace_root, now=NOW)
    with (
        sqlite3.connect(catalog.path) as source,
        sqlite3.connect(workspace_root / "catalog.sqlite3") as destination,
    ):
        source.backup(destination)
    shutil.copytree(prepared / "cas/objects", workspace_root / "objects", dirs_exist_ok=True)
    return workspace_root, commit


def test_visual_inspection_json_and_human_outputs_are_body_free(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inspect an exact descriptor with stable envelope and bounded human summary."""
    workspace, commit = _visual_workspace(tmp_path)
    arguments = [
        "visual-evidence",
        commit.descriptor.visual_evidence_id,
        "--store",
        str(workspace),
    ]
    code, payload, stderr = _json_call(capsys, arguments)
    assert code == 0 and stderr == ""
    assert payload["command"] == "visual-evidence"
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["visual_evidence_id"] == commit.descriptor.visual_evidence_id
    assert "synthetic crop" not in json.dumps(payload)

    assert main(arguments) == 0
    human = capsys.readouterr()
    assert f"visual={commit.descriptor.visual_evidence_id}" in human.out
    assert "usage=local_only export=false" in human.out
    assert human.err == ""


def test_visual_commands_reject_bad_usage_and_report_missing_identifier(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Keep usage and absence in distinct stable JSON classifications."""
    store = tmp_path / "workspace"
    LocalWorkspace.initialize(store, now=NOW)
    code, payload, _ = _json_call(
        capsys,
        ["visual-evidence", "invalid", "--store", str(store)],
    )
    assert code == 3
    assert without_hint(payload["error"]) == {
        "code": "not_found",
        "message": "requested visual evidence was not found",
    }

    code, payload, _ = _json_call(capsys, ["visual-materialize", "--store", str(store)])
    assert code == 2
    assert without_hint(payload["error"]) == {
        "code": "invalid_usage",
        "message": "command usage is invalid",
    }


def test_visual_materialize_cli_succeeds_for_registered_pdf_identifier(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise the public identifier-only CLI through the isolated PDF renderer."""
    prepared = tmp_path / "prepared-pdf"
    catalog, _, rich = prepared_pdf_visual_service(prepared)
    workspace = tmp_path / "workspace-pdf"
    LocalWorkspace.initialize(workspace, now=NOW)
    with (
        sqlite3.connect(catalog.path) as source,
        sqlite3.connect(workspace / "catalog.sqlite3") as destination,
    ):
        source.backup(destination)
    shutil.copytree(prepared / "cas/objects", workspace / "objects", dirs_exist_ok=True)

    code, payload, stderr = _json_call(
        capsys,
        [
            "visual-materialize",
            str(rich.bundle.scope.document_id),
            rich.bundle.projections[0].evidence_projection_id,
            "--store",
            str(workspace),
        ],
    )
    assert code == 0 and stderr == ""
    assert payload["command"] == "visual-materialize"
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["source_version_id"] == rich.bundle.scope.version_id
    assert data["crop_width"] == 246
