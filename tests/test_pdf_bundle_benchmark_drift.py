"""Frozen F023 benchmark drift gate."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_pdf_bundle_benchmark import validate


def test_committed_pdf_bundle_reference_is_internally_valid() -> None:
    """Keep the decision-bearing reference independently reproducible."""
    root = Path(__file__).parents[1]
    result = root / "benchmarks/pdf-bundle/v0.1.0/results/reference-macos-arm64"
    assert validate(root, result)["decision"] == "PDF_OFFLINE_READY"
