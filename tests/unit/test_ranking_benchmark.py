"""Independent F027 benchmark aggregation and reference tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_ranking_benchmark import _at_least, _metrics
from scripts.validate_ranking_benchmark import ValidationFailure, validate


def _row(selected: int, relevant: int, rank: int | None, covered: int = 1) -> dict[str, object]:
    return {
        "covered_source_keys": [f"source-{index}" for index in range(covered)],
        "first_relevant_rank": rank,
        "relevant_count": relevant,
        "required_source_count": 1,
        "selected_count": selected,
    }


def test_exact_metrics_and_cross_multiplication_do_not_use_rounded_values() -> None:
    """Precision, MRR and source recall comparisons retain exact rational semantics."""
    rows = {question: _row(2, 1, 2) for question in ("Q02", "Q03", "Q06", "Q13", "Q14", "Q19")}

    metrics = _metrics(rows)

    assert metrics["evidence_precision"]["ratio"] == "0.500000"
    assert metrics["mrr"]["ratio"] == "0.500000"
    assert metrics["source_recall"]["ratio"] == "1.000000"
    assert _at_least(metrics["mrr"], {"numerator": 1, "denominator": 2, "ratio": "x"})


def test_committed_reference_is_independently_valid(repository_root: Path) -> None:
    """The committed body-free reference passes the stdlib-only validator."""
    result = repository_root / "benchmarks/ranking/v0.1.0/results/reference-macos-arm64"
    assert validate(result) == "LEXICAL_RANKING_READY"


def test_validator_rejects_identity_preserving_claim_tampering(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Changing a gate without recomputing the complete identity fails closed."""
    source = repository_root / "benchmarks/ranking/v0.1.0/results/reference-macos-arm64"
    result = tmp_path / "result"
    result.mkdir()
    payload = json.loads((source / "result.json").read_text(encoding="utf-8"))
    payload["gates"]["mrr_non_regression"] = False
    (result / "result.json").write_text(json.dumps(payload), encoding="utf-8")
    (result / "report.md").write_text((source / "report.md").read_text(), encoding="utf-8")

    with pytest.raises(ValidationFailure, match="identity"):
        validate(result)
