"""Independently validate one body-free F027 paired benchmark result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
FOCUSED = ("Q02", "Q03", "Q06", "Q13", "Q14", "Q17", "Q18", "Q19")
POSITIVE = frozenset({"Q02", "Q03", "Q06", "Q13", "Q14", "Q19"})
UNSUPPORTED = frozenset({"Q17", "Q18"})
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_KEYS = {"body", "content", "hostname", "path", "query", "question", "username"}
TOP_FIELDS = {
    "allocation_policy",
    "allocation_policy_id",
    "benchmark_version",
    "comparison",
    "corpus_id",
    "decision",
    "focused_question_ids",
    "gates",
    "model_bundle_id",
    "profiles",
    "protocol_id",
    "question_set_id",
    "relevance_policy_id",
    "result_id",
}


class ValidationFailure(ValueError):
    """Stable independent validation failure."""


def _load(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4_194_304:
        raise ValidationFailure("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValidationFailure("json_duplicate")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValidationFailure("json_shape")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _identity(value: Any, identity: Any) -> None:
    expected = "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()
    if not isinstance(identity, str) or SHA.fullmatch(identity) is None or identity != expected:
        raise ValidationFailure("identity")


def _metric(rows: dict[str, Any], name: str) -> Fraction:
    positives = [rows[item] for item in sorted(POSITIVE)]
    if name == "evidence_precision":
        denominator = sum(int(row["selected_count"]) for row in positives)
        return Fraction(sum(int(row["relevant_count"]) for row in positives), denominator)
    if name == "mrr":
        return sum(
            Fraction(1, int(row["first_relevant_rank"]))
            if row["first_relevant_rank"]
            else Fraction()
            for row in positives
        ) / len(positives)
    return Fraction(
        sum(len(row["covered_source_keys"]) for row in positives),
        sum(int(row["required_source_count"]) for row in positives),
    )


def _privacy(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            _privacy(item)
    elif isinstance(value, dict):
        if FORBIDDEN_KEYS & set(value):
            raise ValidationFailure("privacy")
        for item in value.values():
            _privacy(item)


def validate(result_root: Path) -> str:
    """Recompute identity, metrics, gates, privacy and closed decision."""
    result = _load(result_root / "result.json")
    if set(result) != TOP_FIELDS or result.get("benchmark_version") != VERSION:
        raise ValidationFailure("fields")
    projection = dict(result)
    result_id = projection.pop("result_id", None)
    _identity(projection, result_id)
    _identity(result["allocation_policy"], result["allocation_policy_id"])
    if result.get("focused_question_ids") != list(FOCUSED):
        raise ValidationFailure("coverage")
    profiles = result.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != {"f026", "f027"}:
        raise ValidationFailure("profiles")
    for profile, expected_name in (
        ("f026", "openardp.lexical-context-relevance"),
        ("f027", "openardp.lexical-context-ranked"),
    ):
        rows = profiles[profile]
        if not isinstance(rows, dict) or tuple(rows) != FOCUSED:
            raise ValidationFailure("rows")
        for row in rows.values():
            audit = row.get("context_audit", {})
            if audit.get("algorithm", {}).get("name") != expected_name:
                raise ValidationFailure("algorithm")
    expected_metrics: dict[str, dict[str, Fraction]] = {"f026": {}, "f027": {}}
    for profile in expected_metrics:
        for name in ("evidence_precision", "mrr", "source_recall"):
            expected_metrics[profile][name] = _metric(profiles[profile], name)
            metric = result["comparison"][profile][name]
            if expected_metrics[profile][name] != Fraction(
                int(metric["numerator"]), int(metric["denominator"])
            ):
                raise ValidationFailure("metric")
    q03_counts: dict[str, int] = {}
    for item in profiles["f027"]["Q03"]["selected_source_keys"]:
        source = str(item)
        q03_counts[source] = q03_counts.get(source, 0) + 1
    if result["comparison"]["q03_selected_by_source"] != dict(sorted(q03_counts.items())):
        raise ValidationFailure("quota_counts")
    gates = {
        "citation_integrity_preserved": all(
            profiles["f027"][item]["citation_integrity_complete"] is True for item in POSITIVE
        ),
        "evidence_precision_non_regression": expected_metrics["f027"]["evidence_precision"]
        >= expected_metrics["f026"]["evidence_precision"],
        "mrr_non_regression": expected_metrics["f027"]["mrr"] >= expected_metrics["f026"]["mrr"],
        "positive_support_preserved": all(
            profiles["f027"][item]["full_support"] is True for item in POSITIVE
        ),
        "q03_document_quota": bool(q03_counts) and max(q03_counts.values()) <= 16,
        "semantic_runs_identical": result.get("gates", {}).get("semantic_runs_identical") is True,
        "source_recall_non_regression": expected_metrics["f027"]["source_recall"]
        >= expected_metrics["f026"]["source_recall"],
        "unsupported_abstained": all(
            profiles["f027"][item]["abstained"] is True
            and profiles["f027"][item]["selected_count"] == 0
            for item in UNSUPPORTED
        ),
    }
    if result.get("gates") != gates:
        raise ValidationFailure("gates")
    decision = "LEXICAL_RANKING_READY" if all(gates.values()) else "LEXICAL_RANKING_NOT_READY"
    if result.get("decision") != decision:
        raise ValidationFailure("decision")
    _privacy(result)
    report = (result_root / "report.md").read_text(encoding="utf-8")
    if decision not in report:
        raise ValidationFailure("report")
    return decision


def main() -> int:
    """Parse one result directory and emit a stable validation category."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.result)
    except (OSError, ValueError, ZeroDivisionError):
        print("ranking_benchmark_invalid")
        return 6
    print(f"ranking_benchmark_valid decision={decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
