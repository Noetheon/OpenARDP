"""CycloneDX, license and vulnerability review tests for F015."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.release_supply_chain import (
    SupplyChainEvidenceMalformed,
    normalize_cyclonedx,
    review_identity,
    supply_chain_checks,
)
from openardp.domain.release import EvidenceStatus

ROOT = Path(__file__).resolve().parents[2]


def _raw_sbom() -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "metadata": {
            "component": {
                "type": "library",
                "bom-ref": "openardp@0.1.0rc1",
                "name": "openardp",
                "version": "0.1.0rc1",
            }
        },
        "components": [
            {
                "type": "library",
                "bom-ref": "pydantic@2.12.5",
                "name": "pydantic",
                "version": "2.12.5",
                "purl": "pkg:pypi/pydantic@2.12.5",
            }
        ],
        "dependencies": [
            {"ref": "openardp@0.1.0rc1", "dependsOn": ["pydantic@2.12.5"]},
            {"ref": "pydantic@2.12.5"},
        ],
    }


def _review() -> dict[str, object]:
    return {
        "components": [
            {
                "component": "openardp==0.1.0rc1",
                "direct": True,
                "disposition": "approved",
                "license_expression": "Apache-2.0",
            },
            {
                "component": "pydantic==2.12.5",
                "direct": True,
                "disposition": "approved",
                "license_expression": "MIT",
            },
        ],
        "vulnerability_snapshot": {
            "observed_at": "2026-08-01T00:00:00Z",
            "findings": [],
        },
    }


def test_cyclonedx_normalization_is_deterministic_complete_and_license_enriched() -> None:
    """Bind every component and dependency node to one reviewed license fact."""
    first = normalize_cyclonedx(_raw_sbom(), _review())
    assert first == normalize_cyclonedx(_raw_sbom(), _review())
    assert len(first["components"]) == 2
    assert all(component["licenses"] for component in first["components"])
    assert len(first["dependencies"]) == 2
    assert review_identity(_review()).startswith("sha256:")


def test_cyclonedx_rejects_missing_component_license_and_graph_node() -> None:
    """Never silently omit a lock component, license or dependency node."""
    incomplete = _review()
    incomplete["components"] = incomplete["components"][:-1]  # type: ignore[index]
    with pytest.raises(SupplyChainEvidenceMalformed, match="lacks a license"):
        normalize_cyclonedx(_raw_sbom(), incomplete)
    raw = _raw_sbom()
    raw["dependencies"] = raw["dependencies"][:-1]  # type: ignore[index]
    with pytest.raises(SupplyChainEvidenceMalformed, match="nodes are incomplete"):
        normalize_cyclonedx(raw, _review())


def test_supply_chain_gate_requires_current_snapshot_and_resolved_licenses() -> None:
    """Keep committed unreviewed components/current-scan absence visible as blockers."""
    sbom = json.loads((ROOT / "release" / "evidence" / "v0.1.0" / "sbom.cdx.json").read_bytes())
    review = json.loads(
        (ROOT / "benchmarks" / "release" / "v0.1.0" / "dependency-review.json").read_bytes()
    )
    checks = supply_chain_checks(
        sbom,
        review,
        now=datetime(2026, 8, 1, tzinfo=UTC),
        maximum_vulnerability_age_days=30,
    )
    by_id = {item.check_id: item for item in checks}
    assert by_id["sbom-component-completeness"].status is EvidenceStatus.PASSED
    assert by_id["sbom-license-completeness"].status is EvidenceStatus.FAILED
    assert by_id["vulnerability-snapshot-current"].status is EvidenceStatus.FAILED


def test_complete_review_and_current_empty_snapshot_pass() -> None:
    """Accept a fully reviewed, current, finding-free synthetic supply-chain record."""
    review = _review()
    sbom = normalize_cyclonedx(_raw_sbom(), review)
    checks = supply_chain_checks(
        sbom,
        review,
        now=datetime(2026, 8, 2, tzinfo=UTC),
        maximum_vulnerability_age_days=30,
    )
    assert all(item.status is EvidenceStatus.PASSED for item in checks)
