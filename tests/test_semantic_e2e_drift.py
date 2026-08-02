"""Repository drift checks for frozen F025 semantic evidence."""

from __future__ import annotations

from pathlib import Path

from scripts.semantic_e2e_benchmark import load_inputs
from scripts.validate_semantic_e2e_benchmark import validate_result

ROOT = Path(__file__).parents[1]
REFERENCE = ROOT / "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64"


def test_semantic_inputs_and_reference_result_do_not_drift() -> None:
    """Bind committed evidence to exact protocol, questions and independent decision."""
    inputs = load_inputs(ROOT)
    decision = validate_result(ROOT, REFERENCE)

    assert inputs.protocol["corpus_id"] == inputs.questions["corpus_id"]
    assert decision in {
        "SEMANTIC_E2E_READY",
        "SEMANTIC_E2E_CONDITIONALLY_READY",
        "SEMANTIC_E2E_NOT_READY",
    }
