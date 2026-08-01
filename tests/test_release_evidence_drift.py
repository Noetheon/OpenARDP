"""Drift tests for frozen F015 release inputs and generated projections."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from openardp.domain.release import ReleaseGatePolicy

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks" / "release" / "v0.1.0"


def test_release_corpus_policy_and_component_inventory_are_current() -> None:
    """Keep pre-result corpus, policy identity and full component inventory frozen."""
    completed = subprocess.run(
        [sys.executable, "scripts/generate_release_corpus.py", "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout == "all 10 release corpus files are current\n"
    policy = ReleaseGatePolicy.model_validate_json((CORPUS / "gate-policy.json").read_bytes())
    policy.verify_identity()
    review = json.loads((CORPUS / "dependency-review.json").read_bytes())
    components = review["components"]
    assert len(components) == 125
    assert len({item["component"] for item in components}) == len(components)
    assert all("license_expression" in item or "license_state" in item for item in components)


def test_dependency_and_sbom_generators_detect_no_drift() -> None:
    """Re-export the exact lock and compare deterministic review/SBOM bytes."""
    for script, expected_fragment in (
        ("scripts/generate_dependency_review.py", "component reviews are current"),
        ("scripts/generate_release_sbom.py", "SBOM components are current"),
    ):
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and reviewed script paths
            [sys.executable, script, "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert expected_fragment in completed.stdout
