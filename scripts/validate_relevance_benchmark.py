"""Independently validate one body-free F026 focused comparison result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
FOCUSED = ("Q02", "Q03", "Q06", "Q13", "Q14", "Q17", "Q18", "Q19")
PRIOR_SUCCESS = frozenset({"Q02", "Q03", "Q06", "Q13", "Q14", "Q19"})
UNSUPPORTED = frozenset({"Q17", "Q18"})
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_KEYS = {
    "body",
    "content",
    "hostname",
    "path",
    "query",
    "question",
    "reference_answer",
    "username",
}
TOP_FIELDS = {
    "baseline_run_id",
    "benchmark_version",
    "comparison",
    "corpus_id",
    "decision",
    "focused_question_ids",
    "gates",
    "model_bundle_id",
    "protocol_id",
    "question_set_id",
    "relevance_policy",
    "relevance_policy_id",
    "result_id",
    "rows",
}


class ValidationFailure(ValueError):
    """Stable independent validation failure."""


def _load(path: Path, maximum: int = 4_194_304) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValidationFailure("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ValidationFailure("json_duplicate")
            value[key] = item
        return value

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValidationFailure("json_non_finite")
            ),
        )
    except ValidationFailure:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationFailure("json_invalid") from error
    if not isinstance(value, dict):
        raise ValidationFailure("json_shape")
    return value


def _safe(value: Any) -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise ValidationFailure("json_integer")
        return
    if isinstance(value, list):
        for item in value:
            _safe(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            _safe(item)
        return
    raise ValidationFailure("json_value")


def _canonical(value: Any) -> bytes:
    _safe(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _require_identity(value: str, payload: Any) -> None:
    if SHA.fullmatch(value) is None or value != _sha(payload):
        raise ValidationFailure("identity")


def _privacy(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            _privacy(item)
    elif isinstance(value, dict):
        if FORBIDDEN_KEYS & set(value):
            raise ValidationFailure("privacy_key")
        for item in value.values():
            _privacy(item)


def _baseline(root: Path) -> tuple[str, dict[str, dict[str, Any]]]:
    base = root / "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64"
    manifest = _load(base / "run-manifest.json")
    observations = _load(base / "observations.json")
    rows = {
        row["question_id"]: row
        for row in observations.get("rows", [])
        if isinstance(row, dict)
        and row.get("treatment") == "openardp_direct"
        and row.get("question_id") in FOCUSED
    }
    if tuple(sorted(rows)) != FOCUSED:
        raise ValidationFailure("baseline_coverage")
    return str(manifest["run_id"]), rows


def validate(repository_root: Path, result_root: Path) -> str:
    """Validate identities, closed comparison semantics, privacy and decision."""
    result = _load(result_root / "result.json")
    if set(result) != TOP_FIELDS or result.get("benchmark_version") != VERSION:
        raise ValidationFailure("result_fields")
    if result.get("focused_question_ids") != list(FOCUSED):
        raise ValidationFailure("focused_questions")
    projection = dict(result)
    result_id = projection.pop("result_id")
    if not isinstance(result_id, str):
        raise ValidationFailure("identity")
    _require_identity(result_id, projection)
    policy = result.get("relevance_policy")
    if not isinstance(policy, dict) or not isinstance(result.get("relevance_policy_id"), str):
        raise ValidationFailure("policy")
    _require_identity(result["relevance_policy_id"], policy)
    baseline_id, baseline_rows = _baseline(repository_root)
    if result.get("baseline_run_id") != baseline_id:
        raise ValidationFailure("baseline_identity")

    raw_rows = result.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != len(FOCUSED):
        raise ValidationFailure("row_count")
    rows: dict[str, dict[str, Any]] = {}
    algorithms: set[bytes] = set()
    for row in raw_rows:
        if not isinstance(row, dict) or row.get("question_id") not in FOCUSED:
            raise ValidationFailure("row_shape")
        question_id = str(row["question_id"])
        if question_id in rows or row.get("treatment") != "openardp_direct":
            raise ValidationFailure("row_order")
        observation = dict(row)
        audit = observation.pop("context_audit", None)
        observation_id = observation.pop("observation_id", None)
        if not isinstance(audit, dict) or not isinstance(observation_id, str):
            raise ValidationFailure("audit")
        _require_identity(observation_id, observation)
        algorithm = audit.get("algorithm")
        if not isinstance(algorithm, dict) or algorithm.get("name") != (
            "openardp.lexical-context-relevance"
        ):
            raise ValidationFailure("algorithm")
        algorithms.add(_canonical(algorithm))
        rows[question_id] = row
    if tuple(rows) != FOCUSED or len(algorithms) != 1:
        raise ValidationFailure("row_order")

    comparisons = result.get("comparison")
    if not isinstance(comparisons, list) or len(comparisons) != len(FOCUSED):
        raise ValidationFailure("comparison")
    for question_id, comparison in zip(FOCUSED, comparisons, strict=True):
        if not isinstance(comparison, dict) or comparison.get("question_id") != question_id:
            raise ValidationFailure("comparison")
        baseline = baseline_rows[question_id]
        expected_baseline = {
            "abstained": baseline["abstained"],
            "covered_atom_ids": baseline["covered_atom_ids"],
            "full_support": baseline["full_support"],
            "selected_count": baseline["selected_count"],
        }
        row = rows[question_id]
        expected_treatment = {
            "abstained": row["abstained"],
            "citation_integrity_complete": row["citation_integrity_complete"],
            "covered_atom_ids": row["covered_atom_ids"],
            "full_support": row["full_support"],
            "selected_count": row["selected_count"],
        }
        if (
            comparison.get("baseline") != expected_baseline
            or comparison.get("minimum_relevance") != expected_treatment
        ):
            raise ValidationFailure("comparison")

    expected_gates = {
        "citation_integrity_preserved": all(
            rows[item]["citation_integrity_complete"] is True for item in PRIOR_SUCCESS
        ),
        "prior_success_preserved": all(
            rows[item]["full_support"] is True for item in PRIOR_SUCCESS
        ),
        "semantic_runs_identical": result.get("gates", {}).get("semantic_runs_identical") is True,
        "unsupported_abstained": all(
            rows[item]["abstained"] is True
            and rows[item]["context_audit"].get("warnings") == ["no_relevant_evidence"]
            and "no_relevant_evidence" in rows[item]["context_audit"].get("notices", [])
            for item in UNSUPPORTED
        ),
    }
    if result.get("gates") != expected_gates:
        raise ValidationFailure("gates")
    expected_decision = (
        "RELEVANCE_ABSTENTION_READY"
        if all(expected_gates.values())
        else "RELEVANCE_ABSTENTION_NOT_READY"
    )
    if result.get("decision") != expected_decision:
        raise ValidationFailure("decision")
    _privacy(result)
    report = (result_root / "report.md").read_text(encoding="utf-8")
    if expected_decision not in report or any(item not in report for item in FOCUSED):
        raise ValidationFailure("report")
    return expected_decision


def main() -> int:
    """Parse paths and emit a stable validation category."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.repository_root.resolve(strict=True), arguments.result)
    except (OSError, ValueError):
        print("relevance_benchmark_invalid")
        return 6
    print(f"relevance_benchmark_valid decision={decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
