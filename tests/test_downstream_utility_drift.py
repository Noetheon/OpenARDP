"""Frozen F036 method and reference-evidence drift guards."""

from __future__ import annotations

from pathlib import Path

from scripts.downstream_utility_benchmark import load_json, load_protocol


def test_f036_protocol_and_reference_decision_remain_frozen(repository_root: Path) -> None:
    """Prevent result-led edits to the post-F025 downstream method or committed verdict."""
    protocol = load_protocol(repository_root)
    result = repository_root / "benchmarks/downstream-utility/v0.1.0/results/reference-macos-arm64"
    decision = load_json(result / "decision.json")
    manifest = load_json(result / "run-manifest.json")

    assert protocol["protocol_id"] == (
        "sha256:58bd259f83d6eeaadca35321ab95c6c62c7d9ad2712f89a0da5413aa3541c133"
    )
    assert protocol["budgets"] == [1, 3, 5, 10, 64]
    assert protocol["primary_budget"] == 3
    assert decision["validity"] == "valid"
    assert decision["development_candidate"] == "accepted"
    assert decision["holdout_generalization"] == "positive"
    assert manifest["holdout_evaluations"] == 1
