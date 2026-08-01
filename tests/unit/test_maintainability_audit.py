"""Deterministic maintainability-policy contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_maintainability import PolicyError, audit_repository, load_policy


def _write_source(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_policy(root: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "version": 1,
        "source_root": "src/openardp",
        "module_line_limit": 20,
        "function_line_limit": 5,
        "module_exceptions": {},
        "function_exceptions": {},
    }
    payload.update(overrides)
    path = root / "policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_policy_rejects_duplicate_keys_unknown_keys_and_unsafe_roots(tmp_path: Path) -> None:
    """Fail closed before source inspection when policy JSON is ambiguous or unsafe."""
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"version":1,"version":1,"source_root":"src/openardp",'
        '"module_line_limit":20,"function_line_limit":5,'
        '"module_exceptions":{},"function_exceptions":{}}',
        encoding="utf-8",
    )
    with pytest.raises(PolicyError, match="duplicate policy key"):
        load_policy(duplicate)

    with pytest.raises(PolicyError, match="unknown policy field"):
        load_policy(_write_policy(tmp_path, surprise=True))

    with pytest.raises(PolicyError, match="source_root must be a safe relative path"):
        load_policy(_write_policy(tmp_path, source_root="../outside"))


def test_audit_is_deterministic_and_includes_decorator_span(tmp_path: Path) -> None:
    """Sort diagnostics and count decorators without importing inspected modules."""
    _write_source(tmp_path, "src/openardp/z.py", "def tiny():\n    return 1\n")
    _write_source(
        tmp_path,
        "src/openardp/a.py",
        "def marker(value):\n"
        "    return value\n\n"
        "@marker\n"
        "def long():\n"
        "    one = 1\n"
        "    two = 2\n"
        "    three = 3\n"
        "    return one + two + three\n",
    )
    policy = load_policy(_write_policy(tmp_path))
    first = audit_repository(tmp_path, policy)
    second = audit_repository(tmp_path, policy)
    assert first == second
    assert [(finding.code, finding.key) for finding in first] == [
        ("function-limit", "src/openardp/a.py:long"),
    ]
    assert first[0].actual == 6
    assert first[0].allowed == 5


def test_exception_growth_missing_targets_and_stale_allowances_fail(tmp_path: Path) -> None:
    """Permit only current bounded legacy debt and force obsolete entries out."""
    _write_source(
        tmp_path,
        "src/openardp/sample.py",
        "def long():\n"
        "    a = 1\n"
        "    b = 2\n"
        "    c = 3\n"
        "    d = 4\n"
        "    e = 5\n"
        "    return a + b + c + d + e\n",
    )
    policy = load_policy(
        _write_policy(
            tmp_path,
            function_line_limit=3,
            function_exceptions={
                "src/openardp/sample.py:long": {
                    "maximum_lines": 6,
                    "reason": "reviewed legacy workflow",
                },
                "src/openardp/sample.py:missing": {
                    "maximum_lines": 8,
                    "reason": "must not disappear silently",
                },
            },
        )
    )
    findings = audit_repository(tmp_path, policy)
    assert [(item.code, item.key) for item in findings] == [
        ("function-growth", "src/openardp/sample.py:long"),
        ("missing-exception-target", "src/openardp/sample.py:missing"),
    ]

    improved_policy = load_policy(
        _write_policy(
            tmp_path,
            function_line_limit=10,
            function_exceptions={
                "src/openardp/sample.py:long": {
                    "maximum_lines": 12,
                    "reason": "now unnecessary",
                }
            },
        )
    )
    assert [(item.code, item.key) for item in audit_repository(tmp_path, improved_policy)] == [
        ("stale-exception", "src/openardp/sample.py:long")
    ]


def test_module_limits_and_exception_paths_are_strict(tmp_path: Path) -> None:
    """Reject new oversized modules and malformed exception keys deterministically."""
    _write_source(tmp_path, "src/openardp/big.py", "\n".join(f"VALUE_{i} = {i}" for i in range(8)))
    policy = load_policy(_write_policy(tmp_path, module_line_limit=4))
    assert [(item.code, item.key) for item in audit_repository(tmp_path, policy)] == [
        ("module-limit", "src/openardp/big.py")
    ]

    with pytest.raises(PolicyError, match="unsafe module exception key"):
        load_policy(
            _write_policy(
                tmp_path,
                module_exceptions={"/absolute.py": {"maximum_lines": 10, "reason": "invalid"}},
            )
        )


def test_policy_rejects_empty_reasons_and_invalid_bounds(tmp_path: Path) -> None:
    """Require finite reviewable ceilings and non-empty rationales."""
    with pytest.raises(PolicyError, match="reason must be non-empty"):
        load_policy(
            _write_policy(
                tmp_path,
                module_exceptions={"src/openardp/a.py": {"maximum_lines": 10, "reason": "  "}},
            )
        )
    with pytest.raises(PolicyError, match="must be a positive integer"):
        load_policy(_write_policy(tmp_path, function_line_limit=0))
