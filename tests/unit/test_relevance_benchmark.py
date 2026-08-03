"""Focused F026 benchmark evaluation tests."""

from __future__ import annotations

from scripts.run_relevance_benchmark import PRIOR_SUCCESS, UNSUPPORTED, _evaluate


def _row(*, supported: bool, abstained: bool) -> dict[str, object]:
    return {
        "full_support": supported,
        "abstained": abstained,
        "citation_integrity_complete": supported,
        "context_audit": {
            "warnings": ["no_relevant_evidence"] if abstained else [],
            "notices": ["no_relevant_evidence"] if abstained else [],
        },
    }


def test_evaluation_requires_every_positive_negative_and_determinism_gate() -> None:
    """A favorable label requires the complete frozen comparison, never an average."""
    rows = {item: _row(supported=True, abstained=False) for item in PRIOR_SUCCESS}
    rows.update({item: _row(supported=False, abstained=True) for item in UNSUPPORTED})

    assert all(_evaluate(rows, True).values())
    rows["Q17"] = _row(supported=False, abstained=False)
    assert _evaluate(rows, True)["unsupported_abstained"] is False
    assert _evaluate(rows, False)["semantic_runs_identical"] is False
