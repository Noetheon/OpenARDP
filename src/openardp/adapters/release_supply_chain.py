"""Deterministic CycloneDX normalization and fail-closed dependency review."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from pydantic import JsonValue

from openardp.domain.identity import canonical_sha256
from openardp.domain.release import EvidenceCheck, EvidenceStatus


class SupplyChainEvidenceMalformed(ValueError):
    """Raised when an SBOM, license inventory or vulnerability review is incomplete."""


def normalize_cyclonedx(raw: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a uv CycloneDX 1.5 export and add reviewed component licenses."""
    if raw.get("bomFormat") != "CycloneDX" or raw.get("specVersion") != "1.5":
        raise SupplyChainEvidenceMalformed("CycloneDX 1.5 input is required")
    raw_components = raw.get("components")
    raw_dependencies = raw.get("dependencies")
    review_components = review.get("components")
    if not isinstance(raw_components, list) or not isinstance(raw_dependencies, list):
        raise SupplyChainEvidenceMalformed("SBOM components or dependencies are missing")
    if not isinstance(review_components, list):
        raise SupplyChainEvidenceMalformed("license component inventory is missing")
    licenses = _review_by_key(review_components)
    components: list[dict[str, Any]] = []
    references: set[str] = set()
    observed_keys: set[str] = set()
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("component"), dict):
        raise SupplyChainEvidenceMalformed("SBOM root component is missing")
    all_components = [metadata["component"], *raw_components]
    for raw_component in all_components:
        component = _mapping(raw_component)
        if set(component) - {
            "type",
            "bom-ref",
            "name",
            "version",
            "purl",
            "properties",
        }:
            raise SupplyChainEvidenceMalformed("SBOM component has unreviewed fields")
        name = _string(component, "name")
        version = _string(component, "version")
        reference = _string(component, "bom-ref")
        purl_value = component.get("purl")
        purl = (
            purl_value
            if isinstance(purl_value, str) and purl_value
            else f"pkg:pypi/{name}@{version}"
        )
        key = f"{name}=={version}"
        if key in observed_keys or reference in references:
            raise SupplyChainEvidenceMalformed("SBOM component identity is duplicate")
        observed_keys.add(key)
        references.add(reference)
        license_fact = licenses.get(key)
        if license_fact is None:
            raise SupplyChainEvidenceMalformed("SBOM component lacks a license review")
        normalized = {
            "type": str(component.get("type", "library")),
            "bom-ref": reference,
            "name": name,
            "version": version,
            "purl": purl,
            "licenses": [_license_projection(license_fact)],
        }
        components.append(normalized)
    if observed_keys != set(licenses):
        raise SupplyChainEvidenceMalformed("license inventory and SBOM component set differ")
    dependencies = _normalize_dependencies(raw_dependencies, references)
    serial = canonical_sha256(
        cast(
            JsonValue,
            {
                "components": sorted(components, key=lambda item: item["bom-ref"]),
                "dependencies": dependencies,
            },
        )
    )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{UUID(hex=serial.removeprefix('sha256:')[:32])}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "openardp",
                "version": "0.1.0rc1",
            },
            "tools": [{"vendor": "Astral", "name": "uv", "version": "0.11.31"}],
        },
        "components": sorted(components, key=lambda item: (item["name"], item["version"])),
        "dependencies": dependencies,
    }


def supply_chain_checks(
    sbom: Mapping[str, Any],
    review: Mapping[str, Any],
    *,
    now: datetime,
    maximum_vulnerability_age_days: int,
) -> tuple[EvidenceCheck, ...]:
    """Return explicit license, graph and vulnerability release-gate checks."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    components = sbom.get("components")
    review_components = review.get("components")
    snapshot = review.get("vulnerability_snapshot")
    complete = (
        isinstance(components, list)
        and isinstance(review_components, list)
        and len(components) == len(review_components)
    )
    license_complete = (
        isinstance(review_components, list)
        and complete
        and all(_license_resolved(item) for item in review_components)
    )
    dependencies = sbom.get("dependencies")
    graph_complete = isinstance(dependencies, list) and bool(dependencies)
    snapshot_current = False
    unresolved = True
    reviewed_lower = False
    evidence_ids = (
        canonical_sha256(cast(JsonValue, dict(sbom))),
        review_identity(review),
    )
    if isinstance(snapshot, dict):
        try:
            observed_at = datetime.fromisoformat(
                _string(snapshot, "observed_at").replace("Z", "+00:00")
            )
        except ValueError:
            observed_at = datetime.min.replace(tzinfo=UTC)
        age = now.astimezone(UTC) - observed_at.astimezone(UTC)
        snapshot_current = 0 <= age.days <= maximum_vulnerability_age_days
        findings = snapshot.get("findings")
        if isinstance(findings, list):
            unresolved = any(
                isinstance(item, dict)
                and item.get("severity") in {"critical", "high"}
                and item.get("disposition") != "resolved"
                for item in findings
            )
            reviewed_lower = all(
                isinstance(item, dict) and item.get("disposition") in {"accepted", "resolved"}
                for item in findings
                if isinstance(item, dict) and item.get("severity") not in {"critical", "high"}
            )
    return (
        _check(
            "sbom-component-completeness",
            complete,
            "dependency-review-incomplete",
            evidence_ids,
        ),
        _check(
            "sbom-license-completeness",
            license_complete,
            "license-review-incomplete",
            evidence_ids,
        ),
        _check(
            "sbom-dependency-graph-completeness",
            graph_complete,
            "dependency-graph-incomplete",
            evidence_ids,
        ),
        _check(
            "vulnerability-snapshot-current",
            snapshot_current,
            "vulnerability-snapshot-stale",
            evidence_ids,
        ),
        _check(
            "critical-high-vulnerabilities-resolved",
            not unresolved,
            "vulnerability-unresolved",
            evidence_ids,
        ),
        _check(
            "lower-vulnerabilities-reviewed",
            reviewed_lower,
            "vulnerability-review-incomplete",
            evidence_ids,
        ),
    )


def review_identity(review: Mapping[str, Any]) -> str:
    """Return the canonical identity for a dependency review source."""
    return canonical_sha256(json.loads(json.dumps(review, sort_keys=True)))


def _normalize_dependencies(
    raw_dependencies: Sequence[object], references: set[str]
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    observed: set[str] = set()
    for raw in raw_dependencies:
        dependency = _mapping(raw)
        if set(dependency) - {"ref", "dependsOn"}:
            raise SupplyChainEvidenceMalformed("SBOM dependency fields are invalid")
        reference = _string(dependency, "ref")
        children_raw = dependency.get("dependsOn", [])
        if not isinstance(children_raw, list) or any(
            not isinstance(item, str) for item in children_raw
        ):
            raise SupplyChainEvidenceMalformed("SBOM dependency children are invalid")
        children = sorted(set(children_raw))
        if reference in observed or reference not in references or not set(children) <= references:
            raise SupplyChainEvidenceMalformed("SBOM dependency graph is incomplete")
        observed.add(reference)
        normalized.append({"ref": reference, "dependsOn": children})
    if observed != references:
        raise SupplyChainEvidenceMalformed("SBOM dependency nodes are incomplete")
    return sorted(normalized, key=lambda item: item["ref"])


def _review_by_key(raw_components: Sequence[object]) -> dict[str, Mapping[str, Any]]:
    reviewed: dict[str, Mapping[str, Any]] = {}
    for raw in raw_components:
        item = _mapping(raw)
        if set(item) - {
            "component",
            "direct",
            "disposition",
            "license_expression",
            "license_state",
        }:
            raise SupplyChainEvidenceMalformed("license review fields are invalid")
        key = _string(item, "component")
        if key in reviewed or ("license_expression" in item) == ("license_state" in item):
            raise SupplyChainEvidenceMalformed("license review is duplicate or ambiguous")
        reviewed[key] = item
    return reviewed


def _license_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    expression = item.get("license_expression")
    if isinstance(expression, str) and expression:
        return {"expression": expression}
    state = item.get("license_state")
    if isinstance(state, str) and state:
        return {"license": {"name": state}}
    raise SupplyChainEvidenceMalformed("component license fact is empty")


def _license_resolved(value: object) -> bool:
    return isinstance(value, dict) and isinstance(value.get("license_expression"), str)


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise SupplyChainEvidenceMalformed("expected JSON object")
    return value


def _string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise SupplyChainEvidenceMalformed(f"{key} must be a non-empty string")
    return item


def _check(
    check_id: str,
    passed: bool,
    reason: str,
    evidence_ids: tuple[str, ...],
) -> EvidenceCheck:
    return EvidenceCheck(
        check_id=check_id,
        status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        reason=None if passed else reason,
        evidence_ids=evidence_ids,
    )


__all__ = [
    "SupplyChainEvidenceMalformed",
    "normalize_cyclonedx",
    "review_identity",
    "supply_chain_checks",
]
