"""Deterministic projection checks for F020 product-value evidence."""

from __future__ import annotations

from pathlib import Path

from openardp.adapters.product_benchmarks import load_benchmark_inputs
from openardp.domain.product_benchmark import ValueOutcome
from scripts.product_benchmark_evaluation import decide_value
from scripts.product_benchmark_runner import _render_report


def _metrics() -> dict[str, object]:
    return {
        "anchor_correctness": 1.0,
        "context_coverage": 1.0,
        "precision": 1.0,
        "recall": 1.0,
        "replay_match": 1.0,
        "stale_incidents": 0,
        "unchanged_parser_invocations": 0,
        "reference_blocks": 10_000,
        "scale_blocks": 100_000,
        "search_p95_ns_at_100k": 1,
        "status_p95_ns": 1,
        "context_selected_native_ratio": 0.1,
        "break_even": 2,
        "rich_formats": ["docx", "pdf", "pptx"],
        "complete": True,
    }


def test_report_projection_is_deterministic_and_keeps_unfavorable_reason(
    repository_root: Path,
) -> None:
    """Render identical bytes and keep hard-safety failure prominent."""
    inputs = load_benchmark_inputs(repository_root / "benchmarks/product-value/v0.1.0")
    metrics = dict(_metrics(), stale_incidents=1)
    decision = decide_value(inputs, metrics)
    summary = {
        "decision_metrics": metrics,
        "profile_facts": {},
        "rich": {},
        "summaries": [],
    }
    first = _render_report(summary, decision)
    second = _render_report(summary, decision)
    assert first == second
    assert decision.outcome is ValueOutcome.NOT_DEMONSTRATED
    assert "stale-evidence-served" in first
    assert "does not replace the inherited F015 release `NO-GO`" in first
