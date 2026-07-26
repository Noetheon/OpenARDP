"""Security boundaries for untrusted evidence contract data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.domain.common import validate_json
from openardp.domain.evidence import TrustClassification
from scripts.validate_evidence_contracts import validate_manifest

ROOT = Path(__file__).parents[2]


def valid_trust() -> dict[str, object]:
    """Return a valid raw trust root."""
    return {
        "contract_version": "0.1.0",
        "stability": "experimental",
        "origin_zone": "external_untrusted",
        "effective_zone": "external_untrusted",
        "role": "data",
        "instruction_execution_allowed": False,
        "integrity": "verified_sha256",
        "sensitivity": "internal",
        "extensions": {},
    }


def test_raw_json_rejects_unknown_duplicate_and_unsafe_values() -> None:
    """Keep raw contract decoding strict before semantic validation."""
    with pytest.raises(ValidationError):
        validate_json(TrustClassification, json.dumps({**valid_trust(), "unknown": True}))
    duplicate = json.dumps(valid_trust())[:-1] + ',"role":"metadata"}'
    with pytest.raises(ValueError, match="duplicate JSON object name"):
        validate_json(TrustClassification, duplicate)
    unsafe = {**valid_trust(), "extensions": {"https://example.test/n": 9_007_199_254_740_992}}
    with pytest.raises(ValueError, match="safe integer"):
        validate_json(TrustClassification, json.dumps(unsafe))


def test_document_evidence_can_never_authorize_execution() -> None:
    """Reject instruction authority regardless of source text."""
    for change in (
        {"role": "metadata"},
        {"instruction_execution_allowed": True},
    ):
        with pytest.raises(ValidationError):
            TrustClassification.model_validate({**valid_trust(), **change})


def test_validation_errors_hide_raw_pointer_or_extension_values() -> None:
    """Avoid reflecting attacker-controlled values in ordinary diagnostics."""
    raw_value = "DO-NOT-ECHO-THIS-POINTER"
    invalid = {
        **valid_trust(),
        "extensions": {"not-a-namespace": raw_value},
    }
    with pytest.raises(ValidationError) as captured:
        TrustClassification.model_validate(invalid)
    assert raw_value not in str(captured.value)


def test_standalone_manifest_validates_without_adapter_imports() -> None:
    """Run the public corpus through a domain-only validator."""
    manifest = ROOT / "conformance" / "evidence" / "v0.1.0" / "manifest.json"
    assert validate_manifest(manifest) == (7, 8, 1, 6)
    source = (ROOT / "scripts" / "validate_evidence_contracts.py").read_text(encoding="utf-8")
    for prohibited in (
        "openardp.adapters",
        "openardp.interfaces",
        "openardp.ports",
        "openardp.services",
    ):
        assert prohibited not in source


def test_manifest_paths_are_confined_to_fixture_root(tmp_path: Path) -> None:
    """Reject absolute or traversing fixture references before file access."""
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    fixture_root = tmp_path / "corpus"
    fixture_root.mkdir()
    manifest = fixture_root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract_version": "0.1.0",
                "valid": [{"model": "trust_classification", "path": "../outside.json"}],
                "invalid": [],
                "record_sets": [],
                "canonicalization_vectors": "../outside.json",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="traversal-free"):
        validate_manifest(manifest)
