"""Mechanical retrieval, anchor and budget scoring tests for F015."""

from __future__ import annotations

import pytest

from openardp.services.release_gate import (
    score_anchor_matches,
    score_budget_coverage,
    score_ranked_evidence,
)


def test_ranked_retrieval_precision_recall_and_reciprocal_rank_are_exact() -> None:
    """Score committed evidence identities without fuzzy or model judgment."""
    assert score_ranked_evidence(("a", "b"), ("x", "b", "a")) == pytest.approx((2 / 3, 1.0, 0.5))
    assert score_ranked_evidence(("a",), ()) == (0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="unique"):
        score_ranked_evidence(("a", "a"), ("a",))


def test_anchor_scoring_is_ordered_and_exact() -> None:
    """Count only anchors matching the expected position."""
    assert score_anchor_matches(("page-1", "page-2"), ("page-1", "page-9")) == 0.5
    with pytest.raises(ValueError, match="non-empty"):
        score_anchor_matches((), ())


def test_three_budget_outcomes_report_coverage_and_insufficiency() -> None:
    """Bind coverage and selected/native ratio to the exact byte ceiling."""
    assert score_budget_coverage(
        ("a", "b"), ("a", "b"), selected_bytes=200, native_bytes=1_000, maximum_bytes=256
    ) == (1.0, 0.2)
    assert score_budget_coverage(
        ("a", "b"), ("a",), selected_bytes=300, native_bytes=1_000, maximum_bytes=256
    ) == (0.0, 0.3)
    with pytest.raises(ValueError, match="byte budgets"):
        score_budget_coverage(("a",), ("a",), selected_bytes=1, native_bytes=0, maximum_bytes=1)
