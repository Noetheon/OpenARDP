"""Audit OpenARDP CI policy, classify changed paths and verify cost evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

_PLATFORMS = ("ubuntu-latest", "macos-latest", "windows-latest")
_REQUIRED_CHECKS = (
    "Preflight",
    "Quality (ubuntu-latest)",
    "Quality (macos-latest)",
    "Quality (windows-latest)",
)
_SAFE_GOVERNANCE_EXACT = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "START_HERE.md",
    "VALIDATION.md",
}
_SAFE_GOVERNANCE_PREFIXES = {
    "docs/",
    "specs/",
}
_ACTION_REFERENCE = re.compile(
    r"^\s*-?\s*uses:\s*([^@\s]+)@([0-9a-f]{40})\s+#\s+v\d+\.\d+\.\d+\s*$",
    re.MULTILINE,
)
_USES_LINE = re.compile(r"^\s*-?\s*uses:\s*", re.MULTILINE)
_RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONEY_QUANTUM = Decimal("0.001")


class CIAuditError(ValueError):
    """Raised when CI policy, workflows or cost evidence are invalid."""


@dataclass(frozen=True, slots=True)
class PathRules:
    """Reviewed exact paths and directory prefixes."""

    exact: tuple[str, ...]
    prefixes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowInvariants:
    """Workflow locations and literal contract markers."""

    core_workflow: str
    release_workflow: str
    required_core_markers: tuple[str, ...]
    required_release_markers: tuple[str, ...]
    forbidden_core_markers: tuple[str, ...]
    forbidden_release_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CIPolicy:
    """Validated machine-readable CI execution policy."""

    schema_version: str
    supported_platforms: tuple[str, ...]
    coverage_owner: str
    required_checks: tuple[str, ...]
    governance_only: PathRules
    release_owned: PathRules
    workflow_invariants: WorkflowInvariants


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Deterministic fail-closed classification for one change set."""

    scope: str
    paths: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible stable projection."""
        return {"paths": list(self.paths), "reasons": list(self.reasons), "scope": self.scope}


@dataclass(frozen=True, slots=True)
class AuditFinding:
    """One body-free workflow invariant failure."""

    code: str
    path: str
    marker: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-compatible stable projection."""
        return {"code": self.code, "marker": self.marker, "path": self.path}


@dataclass(frozen=True, slots=True)
class CostBaseline:
    """Validated inputs and stored outputs for one dated cost model."""

    observed_date: str
    captured_at: str
    source: str
    run_count: int
    job_count: int
    prices: Mapping[str, Decimal]
    rounded_minutes: Mapping[str, int]
    stored_gross: Decimal
    minimum_reduction: Decimal
    maximum_reduction: Decimal
    stored_low: Decimal
    stored_high: Decimal
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Recomputed historical gross cost and projected comparable range."""

    gross_cost_usd: Decimal
    projected_cost_low_usd: Decimal
    projected_cost_high_usd: Decimal
    reduction_percent_low: Decimal
    reduction_percent_high: Decimal

    def to_dict(self) -> dict[str, str]:
        """Return decimal values as stable strings."""
        return {
            "gross_cost_usd": _money(self.gross_cost_usd),
            "projected_cost_high_usd": _money(self.projected_cost_high_usd),
            "projected_cost_low_usd": _money(self.projected_cost_low_usd),
            "reduction_percent_high": str(self.reduction_percent_high),
            "reduction_percent_low": str(self.reduction_percent_low),
        }


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CIAuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_reject_duplicate_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CIAuditError(
            f"cannot load JSON policy at {path.name}: {error.__class__.__name__}"
        ) from error
    if not isinstance(value, dict):
        raise CIAuditError("JSON document root must be an object")
    return value


def _require_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise CIAuditError(f"unknown {label} field: {unknown[0]}")
    if missing:
        raise CIAuditError(f"missing {label} field: {missing[0]}")


def _string_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
        raise CIAuditError(f"{label} must be a non-empty string list")
    items = tuple(value)
    if len(items) != len(set(items)):
        raise CIAuditError(f"{label} must not contain duplicates")
    return items


def _safe_relative_path(value: str, *, prefix: bool = False) -> bool:
    if not value or "\\" in value or any(ord(character) < 32 for character in value):
        return False
    if prefix != value.endswith("/"):
        return False
    candidate = value[:-1] if prefix else value
    pure = PurePosixPath(candidate)
    return not pure.is_absolute() and all(part not in {"", ".", ".."} for part in pure.parts)


def _path_rules(value: object, label: str, *, governance: bool) -> PathRules:
    if not isinstance(value, dict):
        raise CIAuditError(f"{label} must be an object")
    _require_fields(value, {"exact", "prefixes"}, label)
    exact = _string_list(value["exact"], f"{label}.exact")
    prefixes = _string_list(value["prefixes"], f"{label}.prefixes")
    if any(not _safe_relative_path(item) for item in exact):
        raise CIAuditError(f"{label}.exact contains an unsafe path")
    if any(not _safe_relative_path(item, prefix=True) for item in prefixes):
        raise CIAuditError(f"{label}.prefixes contains an unsafe prefix")
    if governance and (
        not set(exact) <= _SAFE_GOVERNANCE_EXACT or not set(prefixes) <= _SAFE_GOVERNANCE_PREFIXES
    ):
        raise CIAuditError("governance_only exceeds the reviewed documentation boundary")
    return PathRules(exact=exact, prefixes=prefixes)


def _workflow_invariants(value: object) -> WorkflowInvariants:
    if not isinstance(value, dict):
        raise CIAuditError("workflow_invariants must be an object")
    fields = {
        "core_workflow",
        "release_workflow",
        "required_core_markers",
        "required_release_markers",
        "forbidden_core_markers",
        "forbidden_release_markers",
    }
    _require_fields(value, fields, "workflow_invariants")
    core = value["core_workflow"]
    release = value["release_workflow"]
    if not isinstance(core, str) or not _safe_relative_path(core):
        raise CIAuditError("core_workflow must be a safe relative path")
    if not isinstance(release, str) or not _safe_relative_path(release):
        raise CIAuditError("release_workflow must be a safe relative path")
    return WorkflowInvariants(
        core_workflow=core,
        release_workflow=release,
        required_core_markers=_string_list(value["required_core_markers"], "required_core_markers"),
        required_release_markers=_string_list(
            value["required_release_markers"], "required_release_markers"
        ),
        forbidden_core_markers=_string_list(
            value["forbidden_core_markers"], "forbidden_core_markers"
        ),
        forbidden_release_markers=_string_list(
            value["forbidden_release_markers"], "forbidden_release_markers"
        ),
    )


def load_policy(path: Path) -> CIPolicy:
    """Load and strictly validate the versioned CI policy."""
    value = _load_json(path)
    fields = {
        "schema_version",
        "supported_platforms",
        "coverage_owner",
        "required_checks",
        "governance_only",
        "release_owned",
        "workflow_invariants",
    }
    _require_fields(value, fields, "CI policy")
    if value["schema_version"] != "1.0.0":
        raise CIAuditError("schema_version must equal 1.0.0")
    platforms = _string_list(value["supported_platforms"], "supported_platforms")
    if platforms != _PLATFORMS:
        raise CIAuditError(f"supported_platforms must equal {_PLATFORMS!r}")
    coverage_owner = value["coverage_owner"]
    if not isinstance(coverage_owner, str) or coverage_owner not in platforms:
        raise CIAuditError("coverage_owner must name a supported platform")
    checks = _string_list(value["required_checks"], "required_checks")
    if checks != _REQUIRED_CHECKS:
        raise CIAuditError(f"required_checks must equal {_REQUIRED_CHECKS!r}")
    return CIPolicy(
        schema_version="1.0.0",
        supported_platforms=platforms,
        coverage_owner=coverage_owner,
        required_checks=checks,
        governance_only=_path_rules(value["governance_only"], "governance_only", governance=True),
        release_owned=_path_rules(value["release_owned"], "release_owned", governance=False),
        workflow_invariants=_workflow_invariants(value["workflow_invariants"]),
    )


def classify_paths(paths: Sequence[str], policy: CIPolicy) -> ClassificationResult:
    """Classify paths as governance-only only when every path is safely allowlisted."""
    normalized = tuple(sorted(set(paths)))
    if not normalized:
        return ClassificationResult("full", (), ("empty-change-set",))
    unsafe = tuple(path for path in normalized if not _safe_relative_path(path))
    if unsafe:
        return ClassificationResult("full", normalized, ("unsafe-path",))
    rules = policy.governance_only
    outside = tuple(
        path
        for path in normalized
        if path not in rules.exact and not any(path.startswith(prefix) for prefix in rules.prefixes)
    )
    if outside:
        return ClassificationResult("full", normalized, ("non-governance-path",))
    return ClassificationResult("governance", normalized, ("governance-only",))


def _workflow_findings(
    path: str,
    content: str,
    required: Sequence[str],
    forbidden: Sequence[str],
    kind: str,
) -> list[AuditFinding]:
    findings = [
        AuditFinding(f"missing-{kind}-marker", path, f"required-{index:03d}")
        for index, marker in enumerate(required, start=1)
        if marker not in content
    ]
    findings.extend(
        AuditFinding(f"forbidden-{kind}-marker", path, f"forbidden-{index:03d}")
        for index, marker in enumerate(forbidden, start=1)
        if marker in content
    )
    if len(_ACTION_REFERENCE.findall(content)) != len(_USES_LINE.findall(content)):
        findings.append(AuditFinding("unpinned-action-reference", path, "uses"))
    return findings


def audit_repository(root: Path, policy: CIPolicy) -> list[AuditFinding]:
    """Audit workflow files against the reviewed body-free CI invariants."""
    invariants = policy.workflow_invariants
    findings: list[AuditFinding] = []
    pairs = (
        (
            "core",
            invariants.core_workflow,
            invariants.required_core_markers,
            invariants.forbidden_core_markers,
        ),
        (
            "release",
            invariants.release_workflow,
            invariants.required_release_markers,
            invariants.forbidden_release_markers,
        ),
    )
    for kind, relative, required, forbidden in pairs:
        path = root / relative
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            findings.append(AuditFinding(f"unreadable-{kind}-workflow", relative, "workflow"))
            continue
        findings.extend(_workflow_findings(relative, content, required, forbidden, kind))
    return sorted(findings, key=lambda finding: (finding.code, finding.path, finding.marker))


def _decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise CIAuditError(f"{label} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise CIAuditError(f"{label} must be a finite decimal string") from error
    if not parsed.is_finite() or parsed < 0:
        raise CIAuditError(f"{label} must be a non-negative finite decimal")
    return parsed


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CIAuditError(f"{label} must be a positive integer")
    return value


def load_cost_baseline(path: Path) -> CostBaseline:
    """Load and strictly validate one immutable aggregate cost snapshot."""
    value = _load_json(path)
    fields = {
        "schema_version",
        "observed_date",
        "captured_at",
        "source",
        "run_count",
        "job_count",
        "runner_prices_usd_per_minute",
        "rounded_minutes",
        "gross_cost_usd",
        "model",
    }
    _require_fields(value, fields, "cost baseline")
    if value["schema_version"] != "1.0.0":
        raise CIAuditError("cost baseline schema_version must equal 1.0.0")
    observed_date = value["observed_date"]
    captured_at = value["captured_at"]
    source = value["source"]
    if not isinstance(observed_date, str) or not _DATE.fullmatch(observed_date):
        raise CIAuditError("observed_date must be YYYY-MM-DD")
    if not isinstance(captured_at, str) or not _RFC3339_UTC.fullmatch(captured_at):
        raise CIAuditError("captured_at must be an RFC 3339 UTC timestamp")
    if not isinstance(source, str) or not source:
        raise CIAuditError("source must be a non-empty string")
    price_value = value["runner_prices_usd_per_minute"]
    minute_value = value["rounded_minutes"]
    if not isinstance(price_value, dict) or set(price_value) != {"linux", "macos", "windows"}:
        raise CIAuditError("runner price families must be linux, macos and windows")
    if not isinstance(minute_value, dict) or set(minute_value) != {"linux", "macos", "windows"}:
        raise CIAuditError("rounded minute families must be linux, macos and windows")
    model = value["model"]
    if not isinstance(model, dict):
        raise CIAuditError("model must be an object")
    model_fields = {
        "minimum_reduction_percent",
        "maximum_reduction_percent",
        "projected_cost_low_usd",
        "projected_cost_high_usd",
        "limitations",
    }
    _require_fields(model, model_fields, "cost model")
    limitations = _string_list(model["limitations"], "model.limitations")
    return CostBaseline(
        observed_date=observed_date,
        captured_at=captured_at,
        source=source,
        run_count=_positive_int(value["run_count"], "run_count"),
        job_count=_positive_int(value["job_count"], "job_count"),
        prices={key: _decimal(price_value[key], f"price.{key}") for key in sorted(price_value)},
        rounded_minutes={
            key: _positive_int(minute_value[key], f"rounded_minutes.{key}")
            for key in sorted(minute_value)
        },
        stored_gross=_decimal(value["gross_cost_usd"], "gross_cost_usd"),
        minimum_reduction=_decimal(model["minimum_reduction_percent"], "minimum_reduction_percent"),
        maximum_reduction=_decimal(model["maximum_reduction_percent"], "maximum_reduction_percent"),
        stored_low=_decimal(model["projected_cost_low_usd"], "projected_cost_low_usd"),
        stored_high=_decimal(model["projected_cost_high_usd"], "projected_cost_high_usd"),
        limitations=limitations,
    )


def _money(value: Decimal) -> str:
    return str(value.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_EVEN))


def estimate_cost(baseline: CostBaseline) -> CostEstimate:
    """Recompute stored gross cost and projected reduction range."""
    if (
        not Decimal("0")
        <= baseline.minimum_reduction
        <= baseline.maximum_reduction
        < Decimal("100")
    ):
        raise CIAuditError("reduction percentages must satisfy 0 <= minimum <= maximum < 100")
    gross = sum(
        (
            baseline.prices[family] * baseline.rounded_minutes[family]
            for family in sorted(baseline.prices)
        ),
        start=Decimal("0"),
    ).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)
    low = (gross * (Decimal("100") - baseline.maximum_reduction) / Decimal("100")).quantize(
        _MONEY_QUANTUM, rounding=ROUND_HALF_EVEN
    )
    high = (gross * (Decimal("100") - baseline.minimum_reduction) / Decimal("100")).quantize(
        _MONEY_QUANTUM, rounding=ROUND_HALF_EVEN
    )
    if gross != baseline.stored_gross:
        raise CIAuditError("gross_cost_usd does not match rounded minutes and prices")
    if low != baseline.stored_low:
        raise CIAuditError("projected_cost_low_usd does not match the reduction model")
    if high != baseline.stored_high:
        raise CIAuditError("projected_cost_high_usd does not match the reduction model")
    return CostEstimate(gross, low, high, baseline.minimum_reduction, baseline.maximum_reduction)


def render_json(value: object) -> str:
    """Render canonical compact JSON with a trailing newline."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"


def _append_github_output(path: Path, scope: str) -> None:
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, f"scope={scope}\n".encode("ascii"))
    finally:
        os.close(descriptor)


def _fail(message: str) -> NoReturn:
    print(f"CI audit failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> int:
    """Run classification, workflow audit or cost estimation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    classify = subparsers.add_parser("classify")
    classify.add_argument("--paths-file", type=Path, required=True)
    classify.add_argument("--github-output", type=Path)
    subparsers.add_parser("audit")
    estimate = subparsers.add_parser("estimate")
    estimate.add_argument("--baseline", type=Path)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    policy_path = arguments.policy or root / "quality/ci-policy.json"
    try:
        if arguments.command == "classify":
            policy = load_policy(policy_path)
            paths = arguments.paths_file.read_text(encoding="utf-8").splitlines()
            classification_result = classify_paths(paths, policy)
            if arguments.github_output is not None:
                _append_github_output(arguments.github_output, classification_result.scope)
            sys.stdout.write(render_json(classification_result.to_dict()))
            return 0
        if arguments.command == "audit":
            findings = audit_repository(root, load_policy(policy_path))
            sys.stdout.write(
                render_json(
                    {
                        "finding_count": len(findings),
                        "findings": [finding.to_dict() for finding in findings],
                        "status": "pass" if not findings else "fail",
                    }
                )
            )
            return 0 if not findings else 1
        baseline_path = arguments.baseline or root / "quality/ci-cost-baseline-2026-08-01.json"
        baseline = load_cost_baseline(baseline_path)
        estimate_result = estimate_cost(baseline)
        sys.stdout.write(render_json(estimate_result.to_dict()))
        return 0
    except (CIAuditError, OSError, UnicodeError) as error:
        _fail(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
