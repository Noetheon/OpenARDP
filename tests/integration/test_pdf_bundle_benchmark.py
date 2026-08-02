"""Producer/validator boundary tests over committed F023 evidence."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.validate_pdf_bundle_benchmark import validate

ROOT = Path(__file__).parents[2]
REFERENCE = ROOT / "benchmarks/pdf-bundle/v0.1.0/results/reference-macos-arm64"


def test_independent_validator_accepts_reference_and_rejects_tamper(tmp_path: Path) -> None:
    """Validate raw evidence without importing the producer, then reject byte drift."""
    decision = validate(ROOT, REFERENCE)
    assert decision["decision"] == "PDF_OFFLINE_READY"

    tampered = tmp_path / "result"
    shutil.copytree(REFERENCE, tampered)
    with (tampered / "summary.json").open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError):
        validate(ROOT, tampered)
