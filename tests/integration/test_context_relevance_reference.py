"""Binding F026 comparison and independent-validator regression tests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_relevance_benchmark import validate

ROOT = Path(__file__).parents[2]
REFERENCE = ROOT / "benchmarks/relevance/v0.1.0/results/reference-macos-arm64"


def test_committed_relevance_comparison_is_independently_valid() -> None:
    """Recompute identities, frozen-baseline comparisons, gates and privacy."""
    assert validate(ROOT, REFERENCE) == "RELEVANCE_ABSTENTION_READY"


def test_frozen_success_and_unsupported_questions_have_exact_outcomes() -> None:
    """Preserve all six successes while converting both false positives to abstention."""
    result = json.loads((REFERENCE / "result.json").read_bytes())
    rows = {row["question_id"]: row for row in result["rows"]}

    for question_id in ("Q02", "Q03", "Q06", "Q13", "Q14", "Q19"):
        assert rows[question_id]["full_support"] is True
        assert rows[question_id]["citation_integrity_complete"] is True
    for question_id in ("Q17", "Q18"):
        assert rows[question_id]["selected_count"] == 0
        assert rows[question_id]["abstained"] is True
        assert rows[question_id]["context_audit"]["warnings"] == ["no_relevant_evidence"]
