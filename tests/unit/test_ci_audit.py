"""Deterministic CI policy, classification and cost-evidence contracts."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.audit_ci import (
    CIAuditError,
    audit_repository,
    classify_paths,
    estimate_cost,
    load_cost_baseline,
    load_policy,
    render_json,
)


def _policy_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "supported_platforms": ["ubuntu-latest", "macos-latest", "windows-latest"],
        "coverage_owner": "ubuntu-latest",
        "required_checks": [
            "Preflight",
            "Quality (ubuntu-latest)",
            "Quality (macos-latest)",
            "Quality (windows-latest)",
        ],
        "governance_only": {
            "exact": ["CHANGELOG.md", "README.md"],
            "prefixes": ["docs/", "specs/"],
        },
        "release_owned": {
            "exact": ["pyproject.toml", "uv.lock"],
            "prefixes": ["benchmarks/release/", "release/"],
        },
        "workflow_invariants": {
            "core_workflow": ".github/workflows/ci.yml",
            "release_workflow": ".github/workflows/release-evidence.yml",
            "required_core_markers": ["name: CI"],
            "required_release_markers": ["name: Release Evidence"],
            "forbidden_core_markers": ["pull_request_target"],
            "forbidden_release_markers": ["pull_request_target"],
        },
    }
    payload.update(overrides)
    return payload


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_policy_rejects_duplicate_unknown_and_inconsistent_fields(tmp_path: Path) -> None:
    """Reject ambiguous or incomplete policy data before classifying any path."""
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":"1.0.0","schema_version":"1.0.0"}', encoding="utf-8")
    with pytest.raises(CIAuditError, match="duplicate JSON key"):
        load_policy(duplicate)

    unknown = _policy_payload(surprise=True)
    with pytest.raises(CIAuditError, match="unknown CI policy field"):
        load_policy(_write_json(tmp_path / "unknown.json", unknown))

    invalid_owner = _policy_payload(coverage_owner="freebsd-latest")
    with pytest.raises(CIAuditError, match="coverage_owner"):
        load_policy(_write_json(tmp_path / "owner.json", invalid_owner))

    duplicate_check = _policy_payload(required_checks=["Preflight", "Preflight"])
    with pytest.raises(CIAuditError, match="required_checks"):
        load_policy(_write_json(tmp_path / "checks.json", duplicate_check))


def test_policy_rejects_unsafe_or_overbroad_governance_allowlist(tmp_path: Path) -> None:
    """Keep reduced execution limited to safe documentation/governance roots."""
    unsafe_values = (
        {"exact": ["../README.md"], "prefixes": ["docs/"]},
        {"exact": ["/README.md"], "prefixes": ["docs/"]},
        {"exact": ["README.md"], "prefixes": ["src/"]},
        {"exact": ["README.md"], "prefixes": [".github/"]},
        {"exact": ["README.md"], "prefixes": ["docs"]},
    )
    for index, allowlist in enumerate(unsafe_values):
        payload = _policy_payload(governance_only=allowlist)
        with pytest.raises(CIAuditError, match="governance_only"):
            load_policy(_write_json(tmp_path / f"unsafe-{index}.json", payload))


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["README.md"], "governance"),
        (["docs/18_CI_COST_AND_QUALITY.md"], "governance"),
        (["specs/019-ci-cost-optimization/spec.md"], "governance"),
        (["docs/a.md", "CHANGELOG.md"], "governance"),
        (["docs/a.md", "src/openardp/__init__.py"], "full"),
        ([], "full"),
        ([""], "full"),
        (["../README.md"], "full"),
        (["/outside/README.md"], "full"),
        (["docs/ok.md\x00src/bad.py"], "full"),
        ([".github/workflows/ci.yml"], "full"),
        (["quality/ci-policy.json"], "full"),
        (["scripts/audit_ci.py"], "full"),
        (["pyproject.toml"], "full"),
        (["uv.lock"], "full"),
        (["tests/unit/test_ci_audit.py"], "full"),
        (["schemas/new.schema.json"], "full"),
        (["benchmarks/release/v0.1.0/gate-policy.json"], "full"),
        (["unknown/new.asset"], "full"),
    ],
)
def test_classification_is_narrow_and_fail_closed(
    tmp_path: Path, paths: list[str], expected: str
) -> None:
    """Classify only wholly allowlisted change sets as governance-only."""
    policy = load_policy(_write_json(tmp_path / "policy.json", _policy_payload()))
    result = classify_paths(paths, policy)
    assert result.scope == expected
    expected_paths = sorted(set(paths)) if paths else []
    assert list(result.paths) == expected_paths
    assert result.reasons


def test_classification_and_rendering_are_deterministic(tmp_path: Path) -> None:
    """Sort and de-duplicate paths and reasons for byte-identical automation output."""
    policy = load_policy(_write_json(tmp_path / "policy.json", _policy_payload()))
    first = classify_paths(["docs/z.md", "README.md", "docs/z.md"], policy)
    second = classify_paths(["README.md", "docs/z.md"], policy)
    assert first == second
    assert render_json(first.to_dict()) == render_json(second.to_dict())


def test_cost_baseline_recomputes_gross_total_and_rejects_drift(tmp_path: Path) -> None:
    """Recompute all money from integer rounded minutes and decimal price strings."""
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "observed_date": "2026-08-01",
        "captured_at": "2026-08-02T00:00:00Z",
        "source": "GitHub Actions aggregate",
        "run_count": 34,
        "job_count": 158,
        "runner_prices_usd_per_minute": {
            "linux": "0.006",
            "windows": "0.010",
            "macos": "0.062",
        },
        "rounded_minutes": {"linux": 277, "windows": 463, "macos": 199},
        "gross_cost_usd": "18.630",
        "model": {
            "minimum_reduction_percent": "55.0",
            "maximum_reduction_percent": "65.0",
            "projected_cost_low_usd": "6.520",
            "projected_cost_high_usd": "8.384",
            "limitations": ["Not an invoice."],
        },
    }
    path = _write_json(tmp_path / "baseline.json", payload)
    estimate = estimate_cost(load_cost_baseline(path))
    assert estimate.gross_cost_usd == Decimal("18.630")
    assert estimate.projected_cost_low_usd == Decimal("6.520")
    assert estimate.projected_cost_high_usd == Decimal("8.384")

    payload["gross_cost_usd"] = "18.631"
    with pytest.raises(CIAuditError, match="gross_cost_usd"):
        estimate_cost(load_cost_baseline(_write_json(path, payload)))


def test_repository_audit_reports_missing_markers_without_body_content(tmp_path: Path) -> None:
    """Return stable invariant identifiers and paths for workflow drift."""
    policy = load_policy(_write_json(tmp_path / "policy.json", _policy_payload()))
    core = tmp_path / ".github/workflows/ci.yml"
    release = tmp_path / ".github/workflows/release-evidence.yml"
    core.parent.mkdir(parents=True)
    core.write_text("name: Wrong\n# secret-body-canary\n", encoding="utf-8")
    release.write_text("name: Also Wrong\n", encoding="utf-8")
    findings = audit_repository(tmp_path, policy)
    assert [finding.code for finding in findings] == [
        "missing-core-marker",
        "missing-release-marker",
    ]
    rendered = render_json({"findings": [finding.to_dict() for finding in findings]})
    assert "secret-body-canary" not in rendered
