"""Pure aggregation and validation for F034 body-free retrieval observations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from typing import Any

from openardp.domain.identity import canonical_sha256

try:
    from scripts.retrieval_holdout import QUESTION_IDS, THRESHOLDS, TREATMENTS, VERSION
except ModuleNotFoundError:
    from retrieval_holdout import QUESTION_IDS, THRESHOLDS, TREATMENTS, VERSION


class HoldoutEvaluationError(ValueError):
    """Stable body-free observation or aggregation failure."""


def _fraction(numerator: int, denominator: int, *, vacuous: bool = False) -> Fraction:
    if denominator == 0:
        return Fraction(1 if vacuous else 0, 1)
    return Fraction(numerator, denominator)


def _metric(value: Fraction) -> dict[str, Any]:
    with localcontext() as context:
        context.prec = 30
        ratio = (Decimal(value.numerator) / Decimal(value.denominator)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_EVEN
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "ratio": format(ratio, "f"),
    }


def _metrics(
    rows: Sequence[dict[str, Any]], questions: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    answerable = [row for row in rows if questions[str(row["question_id"])]["answerable"]]
    unsupported = [row for row in rows if not questions[str(row["question_id"])]["answerable"]]
    selected = sum(int(row["selected_count"]) for row in rows)
    relevant = sum(int(row["relevant_count"]) for row in rows)
    valid = sum(sum(bool(item["citation_valid"]) for item in row["selected"]) for row in rows)
    reciprocal = sum(
        (
            Fraction(1, int(row["first_relevant_rank"]))
            if row["first_relevant_rank"]
            else Fraction()
            for row in answerable
        ),
        Fraction(),
    )
    return {
        "full_support": _metric(
            _fraction(sum(bool(row["full_support"]) for row in answerable), len(answerable))
        ),
        "atom_recall": _metric(
            _fraction(
                sum(len(row["covered_atom_ids"]) for row in answerable),
                sum(int(row["required_atom_count"]) for row in answerable),
            )
        ),
        "source_recall": _metric(
            _fraction(
                sum(len(row["covered_source_keys"]) for row in answerable),
                sum(int(row["required_source_count"]) for row in answerable),
            )
        ),
        "evidence_precision": _metric(_fraction(relevant, selected)),
        "mrr": _metric(_fraction(reciprocal, len(answerable))),
        "citation_integrity": _metric(_fraction(valid, selected, vacuous=True)),
        "unsupported_abstention": _metric(
            _fraction(sum(bool(row["abstained"]) for row in unsupported), len(unsupported))
        ),
    }


def _nearest_rank(values: Sequence[int], percentile: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, (len(ordered) * percentile + 99) // 100 - 1)
    return ordered[index]


def _runtime(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    walls = [int(row["wall_ns"]) for row in rows]
    cpus = [int(row["cpu_ns"]) for row in rows]
    return {
        "query_count": len(rows),
        "wall_total_ns": sum(walls),
        "wall_p50_ns": _nearest_rank(walls, 50),
        "wall_p95_ns": _nearest_rank(walls, 95),
        "cpu_total_ns": sum(cpus),
        "cpu_p50_ns": _nearest_rank(cpus, 50),
        "cpu_p95_ns": _nearest_rank(cpus, 95),
    }


def _at_least(metric: Mapping[str, Any], threshold: Sequence[int]) -> bool:
    return int(metric["numerator"]) * int(threshold[1]) >= int(threshold[0]) * int(
        metric["denominator"]
    )


def _row_identity(row: Mapping[str, Any]) -> str:
    return canonical_sha256(
        {
            key: value
            for key, value in row.items()
            if key not in {"context_audit", "cpu_ns", "observation_id", "wall_ns"}
        }
    )


def validate_rows(rows: object, questions: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate closed coverage and every derivable body-free row fact."""
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise HoldoutEvaluationError("rows_shape")
    typed_rows = list(rows)
    expected = [
        (question_id, treatment) for question_id in QUESTION_IDS for treatment in TREATMENTS
    ]
    actual = [(row.get("question_id"), row.get("treatment")) for row in typed_rows]
    if actual != expected:
        raise HoldoutEvaluationError("row_coverage")
    row_keys = {
        "abstained",
        "citation_integrity_complete",
        "context_audit",
        "covered_atom_ids",
        "covered_source_keys",
        "cpu_ns",
        "failure_category",
        "first_relevant_rank",
        "full_support",
        "observation_id",
        "outcome",
        "question_id",
        "relevant_count",
        "required_atom_count",
        "required_source_count",
        "selected",
        "selected_count",
        "source_fitness_max",
        "source_fitness_score",
        "treatment",
        "wall_ns",
    }
    selected_keys = {
        "anchor_type",
        "citation_valid",
        "covered_atom_ids",
        "evidence_id",
        "order",
        "relevant",
        "representation",
        "source_fitness_max",
        "source_fitness_score",
        "source_key",
    }
    for row in typed_rows:
        if set(row) != row_keys:
            raise HoldoutEvaluationError("row_keys")
        question = questions[str(row["question_id"])]
        selected = row["selected"]
        if not isinstance(selected, list):
            raise HoldoutEvaluationError("selected_shape")
        for order, item in enumerate(selected):
            if (
                not isinstance(item, dict)
                or set(item) != selected_keys
                or item.get("order") != order
            ):
                raise HoldoutEvaluationError("selected_shape")
            if not isinstance(item["covered_atom_ids"], list):
                raise HoldoutEvaluationError("selected_shape")
        covered_atoms = sorted(
            set().union(*(set(item["covered_atom_ids"]) for item in selected))
            if selected
            else set()
        )
        covered_sources = sorted(
            {
                item["source_key"]
                for item in selected
                if item["relevant"] and item["source_key"] in question["required_sources"]
            }
        )
        answerable = bool(question["answerable"])
        derived = {
            "covered_atom_ids": covered_atoms,
            "covered_source_keys": covered_sources,
            "required_atom_count": len(question["support_atoms"]),
            "required_source_count": len(question["required_sources"]),
            "full_support": row["outcome"] == "pass"
            and answerable
            and len(covered_atoms) == len(question["support_atoms"])
            and len(covered_sources) == len(question["required_sources"]),
            "abstained": not selected,
            "citation_integrity_complete": bool(selected)
            and all(bool(item["citation_valid"]) for item in selected),
            "relevant_count": sum(bool(item["relevant"]) for item in selected),
            "selected_count": len(selected),
            "first_relevant_rank": next(
                (index + 1 for index, item in enumerate(selected) if item["relevant"]), None
            ),
            "source_fitness_score": sum(int(item["source_fitness_score"]) for item in selected),
            "source_fitness_max": sum(int(item["source_fitness_max"]) for item in selected),
        }
        if any(row[key] != value for key, value in derived.items()):
            raise HoldoutEvaluationError("row_derived_fact")
        if row["observation_id"] != _row_identity(row):
            raise HoldoutEvaluationError("observation_identity")
        if (
            not isinstance(row["wall_ns"], int)
            or isinstance(row["wall_ns"], bool)
            or row["wall_ns"] < 0
            or not isinstance(row["cpu_ns"], int)
            or isinstance(row["cpu_ns"], bool)
            or row["cpu_ns"] < 0
        ):
            raise HoldoutEvaluationError("timing_shape")
        audit = row["context_audit"]
        if not isinstance(audit, dict) or set(audit) != {
            "algorithm",
            "notices",
            "rejected_reason_counts",
            "warnings",
        }:
            raise HoldoutEvaluationError("audit_shape")
    return typed_rows


def summarize(
    rows: list[dict[str, Any]],
    questions: Mapping[str, dict[str, Any]],
    *,
    corpus_id: str,
    question_set_id: str,
    protocol_id: str,
    fresh_runs_identical: bool,
    provider_metrics: Mapping[str, int],
) -> dict[str, Any]:
    """Aggregate exact overall, language and stratum holdout results."""
    validated = validate_rows(rows, questions)
    by_treatment = {
        treatment: _metrics([row for row in validated if row["treatment"] == treatment], questions)
        for treatment in TREATMENTS
    }
    slices: dict[str, Any] = {}
    dimensions = {
        "language": sorted({str(question["language"]) for question in questions.values()}),
        "stratum": sorted({str(question["stratum"]) for question in questions.values()}),
    }
    for dimension, values in dimensions.items():
        slices[dimension] = {}
        for value in values:
            identifiers = {
                question_id
                for question_id, question in questions.items()
                if question[dimension] == value
            }
            slices[dimension][value] = {
                treatment: _metrics(
                    [
                        row
                        for row in validated
                        if row["treatment"] == treatment and row["question_id"] in identifiers
                    ],
                    questions,
                )
                for treatment in TREATMENTS
            }
    summary: dict[str, Any] = {
        "benchmark_version": VERSION,
        "corpus_id": corpus_id,
        "question_set_id": question_set_id,
        "protocol_id": protocol_id,
        "row_count": len(validated),
        "closed_coverage": True,
        "fresh_runs_identical": fresh_runs_identical,
        "treatments": by_treatment,
        "slices": slices,
        "runtime": {
            treatment: _runtime([row for row in validated if row["treatment"] == treatment])
            for treatment in TREATMENTS
        },
        "provider_metrics": dict(sorted(provider_metrics.items())),
    }
    summary["summary_id"] = canonical_sha256(summary)
    return summary


def verdict_checks(summary: Mapping[str, Any]) -> tuple[dict[str, bool], dict[str, bool]]:
    """Derive separate validity and frozen semantic quality checks."""
    semantic = summary["treatments"][TREATMENTS[1]]
    validity = {
        "closed_coverage": bool(summary["closed_coverage"]),
        "fresh_runs_identical": bool(summary["fresh_runs_identical"]),
        "all_citations_valid": all(
            summary["treatments"][treatment]["citation_integrity"]["ratio"] == "1.000000"
            for treatment in TREATMENTS
        ),
    }
    quality = {
        "full_support": _at_least(semantic["full_support"], THRESHOLDS["full_support"]),
        "atom_recall": _at_least(semantic["atom_recall"], THRESHOLDS["atom_recall"]),
        "source_recall": _at_least(semantic["source_recall"], THRESHOLDS["source_recall"]),
        "evidence_precision": _at_least(
            semantic["evidence_precision"], THRESHOLDS["evidence_precision"]
        ),
        "mrr": _at_least(semantic["mrr"], THRESHOLDS["mrr"]),
        "citation_integrity": _at_least(
            semantic["citation_integrity"], THRESHOLDS["citation_integrity"]
        ),
        "unsupported_abstention": _at_least(
            semantic["unsupported_abstention"], THRESHOLDS["unsupported_abstention"]
        ),
        "german_atom_recall": _at_least(
            summary["slices"]["language"]["de"][TREATMENTS[1]]["atom_recall"],
            THRESHOLDS["german_atom_recall"],
        ),
        "spanish_atom_recall": _at_least(
            summary["slices"]["language"]["es"][TREATMENTS[1]]["atom_recall"],
            THRESHOLDS["spanish_atom_recall"],
        ),
    }
    return validity, quality


def render_report(summary: Mapping[str, Any], decision: Mapping[str, Any]) -> str:
    """Render the deterministic honest holdout result without source bodies."""
    lines = [
        "# OpenARDP Independent Retrieval Holdout",
        "",
        f"- **Validity:** `{decision['validity']}`",
        f"- **Quality:** `{decision['quality']}`",
        "",
        "This milestone-only XQuAD holdout measures retrieved evidence and citations,",
        "not generated answers. F025 remains the development benchmark.",
        "",
        "## Exact metrics",
        "",
        "| Treatment | Full | Atoms | Sources | Precision | MRR | Citations | Abstain |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    metric_keys = (
        "full_support",
        "atom_recall",
        "source_recall",
        "evidence_precision",
        "mrr",
        "citation_integrity",
        "unsupported_abstention",
    )
    for treatment in TREATMENTS:
        metrics = summary["treatments"][treatment]
        lines.append(
            f"| {treatment} | "
            + " | ".join(str(metrics[key]["ratio"]) for key in metric_keys)
            + " |"
        )
    lines.extend(["", "## Multilingual atom recall", ""])
    for language in ("en", "de", "es"):
        metrics = summary["slices"]["language"][language]
        lines.append(
            f"- {language}: {metrics[TREATMENTS[0]]['atom_recall']['ratio']} -> "
            f"{metrics[TREATMENTS[1]]['atom_recall']['ratio']}"
        )
    lines.extend(["", "## Query runtime", ""])
    for treatment in TREATMENTS:
        runtime = summary["runtime"][treatment]
        lines.append(
            f"- {treatment}: p50 {runtime['wall_p50_ns']} ns; "
            f"p95 {runtime['wall_p95_ns']} ns; total {runtime['wall_total_ns']} ns"
        )
    metrics = summary["provider_metrics"]
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            f"- Provider requests: {metrics.get('requests', 0)}",
            f"- Passages scored: {metrics.get('passages_scored', 0)}",
            f"- Passage-cache hits: {metrics.get('cache_hits', 0)}",
            f"- Peak provider-worker RSS bytes: {metrics.get('peak_worker_rss_bytes', 0)}",
            "- Embeddings remain disposable worker memory and are not persisted.",
            f"- Quality blockers: {', '.join(decision['quality_blockers']) or 'none'}",
            f"- Validity blockers: {', '.join(decision['validity_blockers']) or 'none'}",
            f"- Failures: {', '.join(decision['failures']) or 'none'}",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "HoldoutEvaluationError",
    "render_report",
    "summarize",
    "validate_rows",
    "verdict_checks",
]
