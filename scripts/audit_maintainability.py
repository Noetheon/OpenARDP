"""Reject unreviewed growth in oversized production modules and functions."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

_POLICY_FIELDS = {
    "version",
    "source_root",
    "module_line_limit",
    "function_line_limit",
    "module_exceptions",
    "function_exceptions",
}
_ALLOWANCE_FIELDS = {"maximum_lines", "reason"}
_QUALIFIED_NAME = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


class PolicyError(ValueError):
    """Signal malformed maintainability policy or unmeasurable source."""


@dataclass(frozen=True, slots=True)
class HotspotAllowance:
    """Reviewed inclusive ceiling for one existing hotspot."""

    maximum_lines: int
    reason: str


@dataclass(frozen=True, slots=True)
class MaintainabilityPolicy:
    """Strict versioned rules for measuring production source."""

    version: int
    source_root: str
    module_line_limit: int
    function_line_limit: int
    module_exceptions: Mapping[str, HotspotAllowance]
    function_exceptions: Mapping[str, HotspotAllowance]


@dataclass(frozen=True, order=True, slots=True)
class AuditFinding:
    """One deterministic body-free policy violation."""

    code: str
    key: str
    actual: int | None = None
    allowed: int | None = None

    def render(self) -> str:
        """Render a stable shell diagnostic without source content."""
        bounds = ""
        if self.actual is not None:
            bounds += f" actual={self.actual}"
        if self.allowed is not None:
            bounds += f" allowed={self.allowed}"
        return f"{self.code}: {self.key}{bounds}"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError(f"duplicate policy key: {key}")
        result[key] = value
    return result


def _object(value: object, *, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise PolicyError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _positive_integer(value: object, *, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise PolicyError(f"{field} must be a positive integer")
    return value


def _safe_path(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise PolicyError(f"{field} must be a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PolicyError(f"{field} must be a safe relative path")
    normalized = path.as_posix()
    if normalized != value:
        raise PolicyError(f"{field} must be a normalized relative path")
    return normalized


def _allowances(
    value: object,
    *,
    field: str,
    source_root: str,
    function_keys: bool,
) -> dict[str, HotspotAllowance]:
    raw = _object(value, field=field)
    result: dict[str, HotspotAllowance] = {}
    for key in sorted(raw):
        if function_keys:
            path_text, separator, qualified_name = key.partition(":")
            if not separator or not _QUALIFIED_NAME.fullmatch(qualified_name):
                raise PolicyError(f"unsafe function exception key: {key}")
            label = "function"
        else:
            path_text = key
            label = "module"
        try:
            path = _safe_path(path_text, field=f"{label} exception key")
        except PolicyError as error:
            raise PolicyError(f"unsafe {label} exception key: {key}") from error
        if not path.startswith(source_root + "/") or not path.endswith(".py"):
            raise PolicyError(f"unsafe {label} exception key: {key}")
        item = _object(raw[key], field=f"{field}.{key}")
        unknown = set(item) - _ALLOWANCE_FIELDS
        if unknown:
            raise PolicyError(f"unknown allowance field: {sorted(unknown)[0]}")
        if set(item) != _ALLOWANCE_FIELDS:
            raise PolicyError(f"incomplete allowance: {key}")
        maximum = _positive_integer(item["maximum_lines"], field="maximum_lines")
        reason = item["reason"]
        if type(reason) is not str or not reason.strip():
            raise PolicyError("reason must be non-empty")
        normalized_key = f"{path}:{qualified_name}" if function_keys else path
        result[normalized_key] = HotspotAllowance(maximum, reason.strip())
    return result


def load_policy(path: Path) -> MaintainabilityPolicy:
    """Load one strict UTF-8 maintainability policy without duplicate JSON keys."""
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PolicyError("maintainability policy is unreadable") from error
    raw = _object(decoded, field="policy")
    unknown = set(raw) - _POLICY_FIELDS
    if unknown:
        raise PolicyError(f"unknown policy field: {sorted(unknown)[0]}")
    if set(raw) != _POLICY_FIELDS:
        raise PolicyError("maintainability policy fields are incomplete")
    if raw["version"] != 1:
        raise PolicyError("unsupported maintainability policy version")
    source_root = _safe_path(raw["source_root"], field="source_root")
    module_limit = _positive_integer(raw["module_line_limit"], field="module_line_limit")
    function_limit = _positive_integer(raw["function_line_limit"], field="function_line_limit")
    return MaintainabilityPolicy(
        version=1,
        source_root=source_root,
        module_line_limit=module_limit,
        function_line_limit=function_limit,
        module_exceptions=_allowances(
            raw["module_exceptions"],
            field="module_exceptions",
            source_root=source_root,
            function_keys=False,
        ),
        function_exceptions=_allowances(
            raw["function_exceptions"],
            field="function_exceptions",
            source_root=source_root,
            function_keys=True,
        ),
    )


class _FunctionSpans(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self._relative_path = relative_path
        self._scope: list[str] = []
        self.metrics: dict[str, int] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        for child in node.body:
            self.visit(child)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        start = min((item.lineno for item in node.decorator_list), default=node.lineno)
        if node.end_lineno is None:
            raise PolicyError(f"source span unavailable: {self._relative_path}")
        qualified_name = ".".join((*self._scope, node.name))
        key = f"{self._relative_path}:{qualified_name}"
        self.metrics[key] = max(self.metrics.get(key, 0), node.end_lineno - start + 1)
        self._scope.append(node.name)
        for child in node.body:
            self.visit(child)
        self._scope.pop()


def _measure_repository(
    root: Path, policy: MaintainabilityPolicy
) -> tuple[dict[str, int], dict[str, int]]:
    source = root / policy.source_root
    if not source.is_dir():
        raise PolicyError("configured source root is unavailable")
    modules: dict[str, int] = {}
    functions: dict[str, int] = {}
    for path in sorted(source.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=relative)
        except (OSError, UnicodeError, SyntaxError) as error:
            raise PolicyError(f"source cannot be measured: {relative}") from error
        modules[relative] = len(text.splitlines())
        visitor = _FunctionSpans(relative)
        visitor.visit(tree)
        functions.update(visitor.metrics)
    return modules, functions


def _metric_findings(
    metrics: Mapping[str, int],
    exceptions: Mapping[str, HotspotAllowance],
    *,
    default_limit: int,
    kind: str,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for key, actual in metrics.items():
        allowance = exceptions.get(key)
        if allowance is not None and actual <= default_limit:
            findings.append(AuditFinding("stale-exception", key, actual, default_limit))
        elif allowance is not None and actual > allowance.maximum_lines:
            findings.append(AuditFinding(f"{kind}-growth", key, actual, allowance.maximum_lines))
        elif allowance is None and actual > default_limit:
            findings.append(AuditFinding(f"{kind}-limit", key, actual, default_limit))
    for key in set(exceptions) - set(metrics):
        findings.append(AuditFinding("missing-exception-target", key))
    return findings


def audit_repository(root: Path, policy: MaintainabilityPolicy) -> tuple[AuditFinding, ...]:
    """Measure production source and return sorted policy violations."""
    modules, functions = _measure_repository(root.resolve(), policy)
    findings = [
        *_metric_findings(
            modules,
            policy.module_exceptions,
            default_limit=policy.module_line_limit,
            kind="module",
        ),
        *_metric_findings(
            functions,
            policy.function_exceptions,
            default_limit=policy.function_line_limit,
            kind="function",
        ),
    ]
    return tuple(sorted(findings))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the repository audit and return a shell-friendly status code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    policy_path = arguments.policy or root / "quality/maintainability-policy.json"
    try:
        policy = load_policy(policy_path)
        findings = audit_repository(root, policy)
    except PolicyError as error:
        print(f"invalid-policy: {error}")
        return 2
    for finding in findings:
        print(finding.render())
    if findings:
        print(f"Maintainability audit failed with {len(findings)} finding(s).")
        return 1
    print("Maintainability audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
