"""Independent F028 benchmark reference and tamper tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_csv_ingestion_benchmark import ValidationFailure, validate


def test_committed_csv_reference_is_independently_valid(repository_root: Path) -> None:
    """Recompute frozen source facts and every body-free readiness gate."""
    result = repository_root / "benchmarks/csv-ingestion/v0.1.0/results/reference-macos-arm64"
    assert validate(result, repository_root) == "CSV_INGESTION_READY"


def test_csv_validator_rejects_identity_preserving_claim_tampering(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Reject changed logical coverage before trusting a favorable decision."""
    source = repository_root / "benchmarks/csv-ingestion/v0.1.0/results/reference-macos-arm64"
    result = tmp_path / "result"
    result.mkdir()
    payload = json.loads((source / "result.json").read_text(encoding="utf-8"))
    payload["csv"]["record_count"] = 1
    (result / "result.json").write_text(json.dumps(payload), encoding="utf-8")
    (result / "report.md").write_text((source / "report.md").read_text(), encoding="utf-8")

    with pytest.raises(ValidationFailure, match="identity"):
        validate(result, repository_root)
