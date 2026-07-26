"""Stable rich ingest and evidence CLI integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.interfaces.cli import _load_model_manifest, main

FIXTURES = Path(__file__).parents[1] / "fixtures" / "rich"
DOCUMENT_BODY = "A deterministic paragraph for native evidence."


def _invoke_json(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, dict[str, object], str]:
    code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1
    return code, json.loads(lines[0]), captured.err


def test_rich_ingest_evidence_and_exact_get_use_stable_json_envelopes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    without_subprocess_coverage: None,
) -> None:
    """Route DOCX explicitly while listing metadata before one requested body."""
    workspace = tmp_path / "store"
    source = tmp_path / "source.docx"
    source.write_bytes((FIXTURES / "synthetic.docx").read_bytes())
    assert main(["init", "--store", str(workspace)]) == 0
    capsys.readouterr()

    code, ingested, stderr = _invoke_json(
        capsys,
        ["ingest", str(source), "--store", str(workspace)],
    )
    assert (code, ingested["command"], ingested["ok"], stderr) == (0, "ingest", True, "")
    ingest_data = ingested["data"]
    assert isinstance(ingest_data, dict)
    assert ingest_data["parser_invoked"] is True
    assert ingest_data["cache_hit"] is False
    assert int(ingest_data["evidence_count"]) >= 1
    scope = ingest_data["scope"]
    assert isinstance(scope, dict)
    document_id = str(scope["document_id"])
    assert DOCUMENT_BODY not in json.dumps(ingested)
    assert str(source) not in json.dumps(ingested)

    code, repeated, _ = _invoke_json(
        capsys,
        ["ingest", str(source), "--store", str(workspace)],
    )
    assert code == 0
    repeated_data = repeated["data"]
    assert isinstance(repeated_data, dict)
    assert repeated_data["cache_hit"] is True
    assert repeated_data["parser_invoked"] is False

    code, listed, _ = _invoke_json(
        capsys,
        ["evidence", document_id, "--store", str(workspace)],
    )
    assert code == 0
    projections = listed["data"]
    assert isinstance(projections, list) and projections
    assert DOCUMENT_BODY not in json.dumps(listed)
    projection = projections[0]
    assert isinstance(projection, dict)
    projection_id = str(projection["evidence_projection_id"])

    code, retrieved, _ = _invoke_json(
        capsys,
        [
            "get-evidence",
            projection_id,
            "--document",
            document_id,
            "--store",
            str(workspace),
        ],
    )
    assert code == 0
    body = retrieved["data"]
    assert isinstance(body, dict)
    assert isinstance(body["body"], str) and body["body"]
    assert retrieved["command"] == "get-evidence"

    code, missing, _ = _invoke_json(
        capsys,
        [
            "get-evidence",
            "sha256:" + "0" * 64,
            "--document",
            document_id,
            "--store",
            str(workspace),
        ],
    )
    assert code == 3
    assert missing["error"] == {
        "code": "not_found",
        "message": "requested evidence was not found",
    }


def test_rich_human_output_is_bounded_and_pdf_assets_fail_before_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    without_subprocess_coverage: None,
) -> None:
    """Keep human summaries useful and reject unconfigured PDF conversion."""
    workspace = tmp_path / "store"
    docx = tmp_path / "source.docx"
    docx.write_bytes((FIXTURES / "synthetic.docx").read_bytes())
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes((FIXTURES / "synthetic.pdf").read_bytes())
    assert main(["init", "--store", str(workspace)]) == 0
    capsys.readouterr()

    assert main(["ingest", str(docx), "--store", str(workspace)]) == 0
    human_ingest = capsys.readouterr()
    assert "evidence items" in human_ingest.out
    assert DOCUMENT_BODY not in human_ingest.out

    code, repeated, _ = _invoke_json(
        capsys,
        ["ingest", str(docx), "--store", str(workspace)],
    )
    assert code == 0
    repeated_data = repeated["data"]
    assert isinstance(repeated_data, dict)
    scope = repeated_data["scope"]
    assert isinstance(scope, dict)
    document_id = str(scope["document_id"])
    code, listed, _ = _invoke_json(
        capsys,
        ["evidence", document_id, "--store", str(workspace)],
    )
    assert code == 0
    projections = listed["data"]
    assert isinstance(projections, list) and projections
    first = projections[0]
    assert isinstance(first, dict)
    projection_id = str(first["evidence_projection_id"])

    assert main(["evidence", document_id, "--store", str(workspace)]) == 0
    human_evidence = capsys.readouterr()
    assert projection_id in human_evidence.out
    assert DOCUMENT_BODY not in human_evidence.out
    assert (
        main(
            [
                "get-evidence",
                projection_id,
                "--document",
                document_id,
                "--store",
                str(workspace),
            ]
        )
        == 0
    )
    human_body = capsys.readouterr()
    assert projection_id in human_body.out
    assert human_body.err == ""

    code, rejected, stderr = _invoke_json(
        capsys,
        ["ingest", str(pdf), "--store", str(workspace)],
    )
    assert code == 4
    assert rejected["error"] == {
        "code": "rejected_input",
        "message": "input was rejected",
    }
    assert DOCUMENT_BODY not in json.dumps(rejected)
    assert str(pdf) not in json.dumps(rejected)
    assert stderr == ""

    code, incomplete_assets, _ = _invoke_json(
        capsys,
        [
            "ingest",
            str(pdf),
            "--docling-model-root",
            str(tmp_path),
            "--store",
            str(workspace),
        ],
    )
    assert code == 4
    assert incomplete_assets["error"] == {
        "code": "rejected_input",
        "message": "input was rejected",
    }


def test_cli_model_manifest_reader_is_bounded_regular_and_no_follow(
    tmp_path: Path,
) -> None:
    """Read one strict local manifest and reject missing, linked and oversized inputs."""
    manifest = ModelBundleManifest(
        bundle_name="reviewed",
        bundle_version="1",
        files=(),
    )
    path = tmp_path / "models.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")

    assert _load_model_manifest(path) == manifest

    linked = tmp_path / "linked.json"
    linked.symlink_to(path)
    with pytest.raises(ValueError, match="invalid"):
        _load_model_manifest(linked)
    with pytest.raises(ValueError, match="invalid"):
        _load_model_manifest(tmp_path / "missing.json")

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (8_388_608 + 1))
    with pytest.raises(ValueError, match="invalid"):
        _load_model_manifest(oversized)
