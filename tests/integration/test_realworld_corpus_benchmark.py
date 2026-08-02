"""Parser-path and independent-result tests for F024."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.realworld_corpus import load_corpus_lock
from scripts.realworld_corpus_benchmark import (
    execute,
    observe_csv,
    observe_rich,
    observe_text,
    publish_result,
)
from scripts.validate_realworld_corpus_benchmark import (
    BenchmarkValidationFailure,
    validate,
)

ROOT = Path(__file__).parents[2]
CORPUS = ROOT / "corpora/realworld/v0.1.0"
BENCHMARK = ROOT / "benchmarks/realworld-corpus/v0.1.0"
RICH_FIXTURES = ROOT / "tests/fixtures/rich"


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def test_real_text_and_markdown_emit_body_free_deterministic_facts() -> None:
    """Exercise both shipped text modes over genuine committed sources."""
    lock = load_corpus_lock(CORPUS)
    for format_name in ("md", "txt"):
        asset = next(item for item in lock["assets"] if item["format"] == format_name)
        first = observe_text(asset, CORPUS / asset["path"], 0)
        second = observe_text(asset, CORPUS / asset["path"], 1)

        assert first["outcome"] == "pass"
        assert first["block_count"] > 0
        assert first["anchor_classes"] == ["line_range"]
        assert first["native_id"] == second["native_id"]
        assert first["block_set_id"] == second["block_set_id"]
        assert "text" not in first


def test_isolated_csv_probe_emits_body_free_table_facts(tmp_path: Path) -> None:
    """Exercise the independent bounded process without retaining table contents."""
    root = tmp_path / "corpus"
    source = root / "sources/sample.csv"
    source.parent.mkdir(parents=True)
    payload = b"name,value\nalpha,1\nbeta,2\n"
    source.write_bytes(payload)
    asset = {
        "format": "csv",
        "key": "sample-csv",
        "media_type": "text/csv",
        "path": "sources/sample.csv",
        "sha256": _sha(payload),
    }

    row = observe_csv(asset, root, 0)

    assert row["outcome"] == "pass"
    assert row["block_count"] == 3
    assert row["table_count"] == 1
    assert row["pointer_resolution_complete"] is True
    assert row["retrieval_complete"] is True
    assert set(row["anchor_classes"]) == {
        "page_region",
        "provider_pointer",
        "table_cell",
        "text_span",
    }
    assert "payload_hex" not in row


def test_rich_docx_observation_resolves_every_pointer(
    without_subprocess_coverage: None,
) -> None:
    """Exercise a real isolated Docling worker with body-free projection facts."""
    source = RICH_FIXTURES / "synthetic.docx"
    payload = source.read_bytes()
    asset = {
        "format": "docx",
        "key": "fixture-docx",
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "path": "synthetic.docx",
        "sha256": _sha(payload),
    }

    row = observe_rich(
        asset,
        source,
        0,
        model_root=None,
        model_manifest=None,
    )

    assert row["block_count"] > 0
    assert row["pointer_resolution_complete"] is True
    assert row["retrieval_complete"] is True
    assert row["native_bytes"] > 0


def _passing_observations() -> tuple[dict[str, object], dict[str, object]]:
    protocol = json.loads((BENCHMARK / "protocol.json").read_bytes())
    lock = load_corpus_lock(CORPUS)
    rows: list[dict[str, object]] = []
    for asset in lock["assets"]:
        for repetition in range(2):
            format_name = asset["format"]
            rows.append(
                {
                    "anchor_classes": ["table_cell"]
                    if format_name == "csv"
                    else ["page_region"]
                    if format_name in {"pdf", "pptx"}
                    else ["line_range"],
                    "asset_key": asset["key"],
                    "block_count": 1,
                    "block_set_id": "sha256:" + "1" * 64,
                    "cpu_ns": 1,
                    "error_category": None,
                    "format": format_name,
                    "native_bytes": 1,
                    "native_id": "sha256:" + "2" * 64,
                    "network_attempts": 0,
                    "outcome": "pass",
                    "page_count": 1 if format_name in {"pdf", "pptx"} else 0,
                    "peak_rss_bytes": 1024,
                    "pointer_bounded_count": 0,
                    "pointer_resolution_complete": True,
                    "recipe_id": "sha256:" + "3" * 64,
                    "repetition": repetition,
                    "retrieval_complete": True,
                    "source_id": asset["sha256"],
                    "table_count": 1 if format_name == "csv" else 0,
                    "wall_ns": 1,
                }
            )
    return (
        {
            "benchmark_version": protocol["benchmark_version"],
            "corpus": {
                "corpus_id": protocol["expected_corpus_id"],
                "payload_bytes": protocol["expected_payload_bytes"],
                "payload_count": protocol["expected_payload_count"],
            },
            "environment": {
                "architecture": "test",
                "os_family": "test",
                "python_version": "3.12.0",
            },
            "model": {
                "bundle_id": protocol["expected_model_bundle_id"],
                "source_lock_id": protocol["expected_model_source_lock_id"],
            },
            "offline": {
                "corpus_preverified": True,
                "explicit_pdf_bundle": True,
                "socket_denied_before_provider_import": True,
            },
            "rows": rows,
        },
        protocol,
    )


def test_independent_validator_regenerates_complete_result(tmp_path: Path) -> None:
    """Prove producer prose and summaries are not trusted."""
    observations, protocol = _passing_observations()
    output = tmp_path / "result"

    decision = publish_result(observations, protocol, output, duration_ns=10)
    regenerated = validate(ROOT, output)

    assert decision == regenerated
    assert regenerated["decision"] == "REALWORLD_BASELINE_READY"


def test_independent_validator_rejects_observation_and_report_tamper(tmp_path: Path) -> None:
    """Reject raw-fact and human-projection drift independently."""
    observations, protocol = _passing_observations()
    original = tmp_path / "original"
    publish_result(observations, protocol, original, duration_ns=10)

    observation_tamper = tmp_path / "observation-tamper"
    shutil.copytree(original, observation_tamper)
    payload = json.loads((observation_tamper / "observations.json").read_bytes())
    payload["rows"][0]["block_count"] = 2
    (observation_tamper / "observations.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkValidationFailure):
        validate(ROOT, observation_tamper)

    report_tamper = tmp_path / "report-tamper"
    shutil.copytree(original, report_tamper)
    (report_tamper / "report.md").write_text("better than measured\n", encoding="utf-8")
    with pytest.raises(BenchmarkValidationFailure):
        validate(ROOT, report_tamper)


def test_execution_requires_explicit_existing_pdf_bundle(tmp_path: Path) -> None:
    """Never turn a baseline run into implicit model provisioning."""
    with pytest.raises((OSError, ValueError)):
        execute(
            ROOT,
            pdf_bundle=tmp_path / "missing",
            output=tmp_path / "result",
        )
