"""Independent drift checks for every retained F029 binding result."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.validate_provider_retrieval_benchmark import ValidationError, validate


@pytest.mark.parametrize(
    ("version", "decision"),
    (
        ("0.1.0", "PROVIDER_RETRIEVAL_NOT_READY"),
        ("0.2.0", "PROVIDER_RETRIEVAL_NOT_READY"),
        ("0.3.0", "PROVIDER_RETRIEVAL_READY"),
    ),
)
def test_reference_result_is_independently_valid(
    repository_root: Path,
    version: str,
    decision: str,
) -> None:
    """Recompute every body-free result instead of trusting favorable producer output."""
    result = (
        repository_root / f"benchmarks/provider-retrieval/v{version}/results/reference-macos-arm64"
    )
    assert validate(repository_root, result, protocol_version=version)["decision"] == decision


def test_independent_validator_rejects_favorable_row_tampering(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Reject a changed support claim even when the JSON remains canonical."""
    source = repository_root / "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64"
    target = tmp_path / "tampered"
    shutil.copytree(source, target)
    observations_path = target / "observations.json"
    observations = json.loads(observations_path.read_text(encoding="utf-8"))
    observations["rows"][0]["full_support"] = True
    observations_path.write_text(
        json.dumps(
            observations, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        validate(repository_root, target, protocol_version="0.3.0")
