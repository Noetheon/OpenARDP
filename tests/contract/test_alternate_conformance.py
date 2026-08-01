"""Contract tests for the isolated F016 alternate parser conformance spike."""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from openardp.domain.evidence import (
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    validate_evidence_records,
)
from openardp.domain.identity import canonical_json_bytes
from scripts.alternate_evidence_process import (
    ConformanceFailure,
    _load_json_bytes,
    canonical_bytes,
)
from scripts.validate_alternate_conformance import (
    DEFAULT_MANIFEST,
    build_decision,
    main,
    run_conformance,
)

ROOT = Path(__file__).parents[2]
PROCESS = ROOT / "scripts" / "alternate_evidence_process.py"
RECORD_SET = (
    ROOT / "conformance" / "alternate-parser" / "v0.1.0" / "expected" / "alternate-record-set.json"
)
DECISION = RECORD_SET.with_name("decision.json")


def _isolated(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - exact interpreter and repository script
        [sys.executable, "-I", "-S", str(PROCESS), *arguments],
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=10,
    )


def test_self_check_proves_isolated_no_site_import_boundary() -> None:
    """Exclude reference and third-party packages from the alternate process."""
    completed = _isolated("--self-check")
    assert completed.returncode == 0
    assert completed.stderr == b""
    response = json.loads(completed.stdout)
    assert response["isolated"] is True
    assert response["no_site"] is True
    assert response["imports_unavailable"] == ["openardp", "pydantic", "rfc8785"]
    assert completed.stdout == canonical_json_bytes(response) + b"\n"


@pytest.mark.parametrize("value", [1.5, float("nan"), 9_007_199_254_740_992])
def test_independent_canonicalizer_rejects_values_outside_declared_safe_domain(
    value: object,
) -> None:
    """Avoid pretending to implement unsupported RFC 8785 number cases."""
    with pytest.raises(ConformanceFailure, match="unsupported_json"):
        canonical_bytes({"value": value})


def test_independent_json_loader_rejects_duplicate_object_keys() -> None:
    """Prevent ambiguous first-key/last-key interpretations before validation."""
    with pytest.raises(ConformanceFailure, match="duplicate_json_key"):
        _load_json_bytes(b'{"contract_version":"0.1.0","contract_version":"1.0.0"}')


def test_complete_bidirectional_run_matches_committed_artifacts() -> None:
    """Bind the checked-in evidence to one deterministic executable run."""
    record_set, decision = run_conformance()
    assert canonical_json_bytes(record_set) + b"\n" == RECORD_SET.read_bytes()
    assert canonical_json_bytes(decision) + b"\n" == DECISION.read_bytes()
    assert decision["status"] == "supported_for_scoped_claim"
    assert decision["contract_stability"] == "experimental"
    assert decision["provider_leakage"] == []
    assert decision["required_changes"] == []
    assert len(decision["observations"]) == 26


def test_coverage_closes_all_roots_vectors_anchors_directions_and_sources() -> None:
    """Prevent a selected passing subset from satisfying the decision."""
    manifest = json.loads(DEFAULT_MANIFEST.read_bytes())
    decision = json.loads(DECISION.read_bytes())
    required = dict(manifest["required_coverage"])
    required.pop("observations")
    assert decision["coverage"] == required
    assert decision["coverage"]["anchors"] == [
        "page_region",
        "provider_pointer",
        "table_cell",
        "text_span",
    ]
    assert decision["coverage"]["directions"] == [
        "alternate_to_reference",
        "reference_to_alternate",
    ]


def test_alternate_records_are_reference_valid_and_non_docling() -> None:
    """Consume every alternate producer record through strict F006 models."""
    document = json.loads(RECORD_SET.read_bytes())
    assert set(document["outputs"]) == {"table", "text"}
    for output in document["outputs"].values():
        native = NativeRepresentation.model_validate_json(canonical_json_bytes(output["native"]))
        references = [
            EvidenceReference.model_validate_json(canonical_json_bytes(item))
            for item in output["references"]
        ]
        projections = [
            EvidenceProjection.model_validate_json(canonical_json_bytes(item))
            for item in output["projections"]
        ]
        validate_evidence_records(
            native,
            references,
            projections,
            expected_source_version_id=output["source_version_id"],
        )
        assert "docling" not in canonical_json_bytes(output).decode().casefold()
        assert native.provider.name == "stdlib-text-csv"
        assert native.provider.profile == "deterministic-grid"


def _decision_fixture() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    coverage = {
        "anchors": ["text_span"],
        "directions": ["reference_to_alternate"],
        "identity_vectors": 1,
        "invalid_roots": 0,
        "models": ["evidence_reference"],
        "record_sets": 0,
        "source_kinds": ["text"],
        "valid_roots": 1,
    }
    manifest: dict[str, Any] = {
        "implementation": {"sha256": "sha256:" + "a" * 64},
        "inputs": {
            "evidence_manifest": {"sha256": "sha256:" + "b" * 64},
            "identity_vectors": {"sha256": "sha256:" + "c" * 64},
            "sources": [{"sha256": "sha256:" + "d" * 64}],
        },
        "required_coverage": {**coverage, "observations": 1},
    }
    observations = [
        {
            "case_id": "valid:one",
            "direction": "reference_to_alternate",
            "expected": "accept",
            "kind": "root_valid",
            "observed": "accept",
            "status": "pass",
        }
    ]
    return manifest, observations, coverage


@pytest.mark.parametrize("mutation", ["missing", "failed", "duplicate", "coverage"])
def test_decision_fails_closed_for_incomplete_or_inconsistent_evidence(mutation: str) -> None:
    """Reject absent, failed, duplicate and coverage-drifted evidence without waiver."""
    manifest, observations, coverage = _decision_fixture()
    if mutation == "missing":
        observations.clear()
    elif mutation == "failed":
        observations[0]["status"] = "fail"
    elif mutation == "duplicate":
        observations.append(dict(observations[0]))
        manifest["required_coverage"]["observations"] = 2
    else:
        coverage["anchors"] = []
    decision = build_decision(
        manifest,
        observations,
        coverage,
        deterministic=True,
        manifest_sha256="sha256:" + "e" * 64,
    )
    assert decision["status"] == "not_supported"
    assert decision["verified_claims"] == []
    assert decision["failures"]


def test_decision_has_no_override_or_stabilization_surface() -> None:
    """Keep a successful internal spike from becoming a waiver or stability decision."""
    signature = inspect.signature(build_decision)
    assert "override" not in signature.parameters
    decision = json.loads(DECISION.read_bytes())
    assert "the evidence contract is stable or standardized" in decision["prohibited_claims"]
    assert "external" in " ".join(decision["limitations"]).casefold()


def test_check_mode_accepts_exact_generated_evidence(capsys: pytest.CaptureFixture[str]) -> None:
    """Expose one stable offline drift-check command."""
    assert main(["--check"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert "status=supported_for_scoped_claim" in output.out
