"""Pure F024 summary, decision and report tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.realworld_corpus_benchmark_evaluation import decide, render_report, summarize

ROOT = Path(__file__).parents[2]
PROTOCOL = json.loads((ROOT / "benchmarks/realworld-corpus/v0.1.0/protocol.json").read_bytes())


def _row(format_name: str, repetition: int) -> dict[str, object]:
    return {
        "anchor_classes": ["line_range"],
        "asset_key": f"asset-{format_name}",
        "block_count": 2,
        "block_set_id": "sha256:" + format_name[0] * 64,
        "cpu_ns": 10,
        "error_category": None,
        "format": format_name,
        "native_bytes": 20,
        "native_id": "sha256:" + format_name[-1] * 64,
        "network_attempts": 0,
        "outcome": "pass",
        "page_count": 1 if format_name in {"pdf", "pptx"} else 0,
        "peak_rss_bytes": 1024,
        "pointer_bounded_count": 0,
        "pointer_resolution_complete": True,
        "recipe_id": "sha256:" + "a" * 64,
        "repetition": repetition,
        "retrieval_complete": True,
        "source_id": "sha256:" + "b" * 64,
        "table_count": 1 if format_name == "csv" else 0,
        "wall_ns": 20,
    }


def _observations() -> dict[str, object]:
    formats = PROTOCOL["required_formats"]
    return {
        "benchmark_version": PROTOCOL["benchmark_version"],
        "corpus": {
            "corpus_id": PROTOCOL["expected_corpus_id"],
            "payload_bytes": PROTOCOL["expected_payload_bytes"],
            "payload_count": PROTOCOL["expected_payload_count"],
        },
        "environment": {
            "architecture": "test",
            "os_family": "test",
            "python_version": "3.12.0",
        },
        "model": {
            "bundle_id": PROTOCOL["expected_model_bundle_id"],
            "source_lock_id": PROTOCOL["expected_model_source_lock_id"],
        },
        "offline": {
            "corpus_preverified": True,
            "explicit_pdf_bundle": True,
            "socket_denied_before_provider_import": True,
        },
        "rows": [
            _row(format_name, repetition) for format_name in formats for repetition in range(2)
        ],
    }


def test_complete_observations_are_ready_and_deterministic() -> None:
    """Accept exactly two successful deterministic rows for all six formats."""
    observations = _observations()
    summary = summarize(observations, PROTOCOL)
    decision = decide(summary, PROTOCOL)

    assert summary["coverage"]["row_count"] == 12
    assert summary["coverage"]["formats"] == PROTOCOL["required_formats"]
    assert all(item["deterministic"] for item in summary["assets"])
    assert decision == {
        "benchmark_version": PROTOCOL["benchmark_version"],
        "decision": "REALWORLD_BASELINE_READY",
        "failure_codes": [],
    }


def test_unfavorable_identity_and_network_facts_remain_fail_closed() -> None:
    """Never average away a nondeterministic or connected observation."""
    observations = _observations()
    rows = observations["rows"]
    assert isinstance(rows, list)
    rows[1]["block_set_id"] = "sha256:" + "f" * 64
    rows[2]["network_attempts"] = 1

    decision = decide(summarize(observations, PROTOCOL), PROTOCOL)

    assert decision["decision"] == "REALWORLD_BASELINE_NOT_READY"
    assert "correctness:nondeterministic:asset-csv" in decision["failure_codes"]
    assert "offline:network_attempt" in decision["failure_codes"]


def test_missing_format_and_resource_breach_are_explicit() -> None:
    """Require closed coverage and every per-asset resource bound."""
    observations = _observations()
    observations["rows"] = [row for row in observations["rows"] if row["format"] != "pdf"]
    observations["rows"][0]["wall_ns"] = PROTOCOL["maximum_asset_wall_ns"] + 1

    decision = decide(summarize(observations, PROTOCOL), PROTOCOL)

    assert "coverage:formats" in decision["failure_codes"]
    assert "resource:wall" in decision["failure_codes"]


def test_report_is_body_free_and_deterministic() -> None:
    """Render aggregate evidence without source or extracted text."""
    observations = _observations()
    summary = summarize(observations, PROTOCOL)
    decision = decide(summary, PROTOCOL)

    first = render_report(summary, decision)
    second = render_report(copy.deepcopy(summary), copy.deepcopy(decision))

    assert first == second
    assert "REALWORLD_BASELINE_READY" in first
    assert "semantic" in first.lower()
    assert "document_body" not in first
