"""Opt-in real offline PDF conversion against the provisioned F023 bundle."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.domain.rich_ingestion import ModelBundleManifest, RichMediaType, RichParserLimits

FIXTURE = Path(__file__).parents[1] / "fixtures" / "rich" / "synthetic.pdf"


def _reference_bundle() -> Path:
    value = os.environ.get("OPENARDP_PDF_BUNDLE_ROOT")
    if value is None:
        pytest.skip("OPENARDP_PDF_BUNDLE_ROOT is not configured")
    return Path(value)


def test_real_bundle_converts_pdf_offline_with_stable_evidence_identity(
    without_subprocess_coverage: None,
) -> None:
    """Bind the exact bundle ID and repeat a fresh-worker PDF conversion offline."""
    root = _reference_bundle()
    manifest = ModelBundleManifest.model_validate_json((root / "manifest.json").read_bytes())
    adapter = IsolatedDoclingAdapter(
        limits=RichParserLimits(timeout_seconds=180.0),
        model_root=root / "assets",
        model_manifest=manifest,
    )
    first = adapter.parse((FIXTURE.read_bytes(),), media_type=RichMediaType.PDF.value)
    second = adapter.parse((FIXTURE.read_bytes(),), media_type=RichMediaType.PDF.value)

    assert adapter.recipe.model_bundle_id == manifest.bundle_id
    assert first.native_document["pages"]
    assert first.candidates
    assert all(candidate.anchor is not None for candidate in first.candidates)
    assert all(candidate.native_pointer.pointer.startswith("#/") for candidate in first.candidates)
    assert (
        hashlib.sha256(first.canonical_native_bytes).digest()
        == hashlib.sha256(second.canonical_native_bytes).digest()
    )
