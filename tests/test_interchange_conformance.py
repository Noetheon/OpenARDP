"""Offline F014 golden-vector drift and classification tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.adapters.bagit_interchange import BagItPackageAdapter
from openardp.domain.interchange import InterchangeLimits
from openardp.ports.interchange import InterchangeError
from openardp.services.interchange import InterchangeService
from scripts.generate_interchange_vectors import main as generate_vectors
from scripts.validate_interchange_package import classify, validate

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "conformance" / "interchange" / "v0.1.0"


def test_interchange_vector_tree_has_zero_drift() -> None:
    """Regenerate every normative binary vector byte-for-byte."""
    assert generate_vectors(["--check"]) == 0
    manifest = (CORPUS / "manifest.json").read_bytes()
    assert manifest.endswith(b"\n")
    assert b"\r" not in manifest


def test_all_valid_vectors_pass_offline() -> None:
    """Accept every supported synthetic profile package without runtime services."""
    manifest = json.loads((CORPUS / "manifest.json").read_bytes())
    for vector in manifest["valid"]:
        verified = BagItPackageAdapter().verify(
            CORPUS / vector["path"],
            limits=InterchangeLimits(),
        )
        assert verified.package.profile_version == manifest["profile_version"]
        independent = validate(CORPUS / vector["path"], limits=InterchangeLimits())
        assert independent["package_id"] == verified.package.package_id
        assert independent["archive_sha256"] == verified.archive_sha256


def test_all_invalid_vectors_have_stable_categories(tmp_path: Path) -> None:
    """Classify the complete hostile corpus exactly as declared."""
    manifest = json.loads((CORPUS / "manifest.json").read_bytes())
    for vector in manifest["invalid"]:
        limits = InterchangeLimits(**vector.get("limits", {}))
        with pytest.raises(InterchangeError) as captured:
            BagItPackageAdapter().verify(CORPUS / vector["path"], limits=limits)
        assert classify(captured.value) == vector["error"], vector["path"]
        with pytest.raises(InterchangeError) as independent:
            validate(CORPUS / vector["path"], limits=limits)
        assert classify(independent.value) == vector["error"], vector["path"]
        destination = tmp_path / Path(vector["path"]).stem
        with pytest.raises(InterchangeError) as imported:
            InterchangeService().import_snapshot(
                CORPUS / vector["path"],
                destination,
                limits=limits,
            )
        assert classify(imported.value) == vector["error"], vector["path"]
        assert not destination.exists()
