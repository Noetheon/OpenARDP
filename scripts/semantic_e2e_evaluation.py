"""Pure exact aggregation, decision and reporting for F025 observations."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from typing import Any

try:
    from scripts.semantic_e2e_benchmark import (
        PRODUCT_TREATMENTS,
        QUESTION_IDS,
        SemanticBenchmarkError,
    )
except ModuleNotFoundError:
    from semantic_e2e_benchmark import PRODUCT_TREATMENTS, QUESTION_IDS, SemanticBenchmarkError

from openardp.domain.identity import canonical_sha256

READY = "SEMANTIC_E2E_READY"
CONDITIONAL = "SEMANTIC_E2E_CONDITIONALLY_READY"
NOT_READY = "SEMANTIC_E2E_NOT_READY"


def _ratio(value: Fraction) -> str:
    with localcontext() as context:
        context.prec = 30
        projected = (Decimal(value.numerator) / Decimal(value.denominator)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_EVEN
        )
    return format(projected, "f")


def _metric(value: Fraction) -> dict[str, Any]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "ratio": _ratio(value),
    }


def _safe_fraction(numerator: int, denominator: int, *, vacuous: bool = False) -> Fraction:
    if denominator == 0:
        return Fraction(1 if vacuous else 0, 1)
    return Fraction(numerator, denominator)


def _treatment_metrics(
    rows: list[dict[str, Any]], questions: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    answerable = [row for row in rows if questions[str(row["question_id"])]["answerable"]]
    unsupported = [row for row in rows if not questions[str(row["question_id"])]["answerable"]]
    german = [row for row in answerable if questions[str(row["question_id"])]["language"] == "de"]
    selected = sum(int(row["selected_count"]) for row in rows)
    relevant = sum(int(row["relevant_count"]) for row in rows)
    citation_valid = sum(
        sum(bool(item["citation_valid"]) for item in row["selected"]) for row in rows
    )
    reciprocal = sum(
        (Fraction(1, int(row["first_relevant_rank"])) if row["first_relevant_rank"] else Fraction())
        for row in answerable
    )
    metrics = {
        "full_support": _metric(
            _safe_fraction(sum(bool(row["full_support"]) for row in answerable), len(answerable))
        ),
        "atom_recall": _metric(
            _safe_fraction(
                sum(len(row["covered_atom_ids"]) for row in answerable),
                sum(int(row["required_atom_count"]) for row in answerable),
            )
        ),
        "evidence_precision": _metric(_safe_fraction(relevant, selected)),
        "mrr": _metric(_safe_fraction(reciprocal, len(answerable))),
        "source_recall": _metric(
            _safe_fraction(
                sum(len(row["covered_source_keys"]) for row in answerable),
                sum(int(row["required_source_count"]) for row in answerable),
            )
        ),
        "citation_integrity": _metric(_safe_fraction(citation_valid, selected, vacuous=True)),
        "abstention": _metric(
            _safe_fraction(sum(bool(row["abstained"]) for row in unsupported), len(unsupported))
        ),
        "german_atom_recall": _metric(
            _safe_fraction(
                sum(len(row["covered_atom_ids"]) for row in german),
                sum(int(row["required_atom_count"]) for row in german),
            )
        ),
        "source_fitness": _metric(
            _safe_fraction(
                sum(int(row["source_fitness_score"]) for row in rows),
                sum(int(row["source_fitness_max"]) for row in rows),
                vacuous=True,
            )
        ),
    }
    return metrics


def summarize(
    rows: list[dict[str, Any]],
    questions: dict[str, dict[str, Any]],
    *,
    corpus_id: str,
    question_set_id: str,
    protocol_id: str,
    supported_formats_ingested: tuple[str, ...],
    semantic_runs_identical: bool,
) -> dict[str, Any]:
    """Recompute closed coverage and all exact treatment metrics."""
    expected = [
        (question_id, treatment) for question_id in QUESTION_IDS for treatment in PRODUCT_TREATMENTS
    ]
    actual = [(str(row.get("question_id")), str(row.get("treatment"))) for row in rows]
    if actual != expected or len(actual) != len(set(actual)):
        raise SemanticBenchmarkError("observation_coverage")
    by_treatment = {
        treatment: _treatment_metrics(
            [row for row in rows if row["treatment"] == treatment], questions
        )
        for treatment in PRODUCT_TREATMENTS
    }
    expected_formats = ("docx", "md", "pdf", "pptx", "txt")
    ingestion = _safe_fraction(
        len(set(supported_formats_ingested) & set(expected_formats)), len(expected_formats)
    )
    summary: dict[str, Any] = {
        "benchmark_version": "0.1.0",
        "corpus_id": corpus_id,
        "question_set_id": question_set_id,
        "protocol_id": protocol_id,
        "row_count": len(rows),
        "closed_coverage": True,
        "semantic_runs_identical": semantic_runs_identical,
        "supported_formats_ingested": sorted(supported_formats_ingested),
        "supported_format_ingestion": _metric(ingestion),
        "treatments": by_treatment,
        "capability_gaps": sorted(
            {
                "csv_product_ingestion_unsupported",
                *(
                    ()
                    if by_treatment["openardp_direct"]["german_atom_recall"]["numerator"]
                    else ("direct_cross_language_retrieval_absent",)
                ),
                *(
                    ()
                    if by_treatment["openardp_direct"]["abstention"]["ratio"] == "1.000000"
                    else ("unsupported_false_positive_selection",)
                ),
            }
        ),
    }
    summary["summary_id"] = canonical_sha256(summary)
    return summary


def _meets(metric: dict[str, Any], threshold: list[int]) -> bool:
    return int(metric["numerator"]) * int(threshold[1]) >= int(threshold[0]) * int(
        metric["denominator"]
    )


def decide(
    summary: dict[str, Any], protocol: dict[str, Any], *, hard_failures: list[str]
) -> dict[str, Any]:
    """Apply the frozen exact-integer readiness policy without rounded ratios."""
    direct = summary["treatments"]["openardp_direct"]
    operator = summary["treatments"]["openardp_operator"]
    ready_policy = protocol["thresholds"]["ready"]
    conditional_policy = protocol["thresholds"]["conditional"]
    ready_checks = {
        "direct_full_support": _meets(direct["full_support"], ready_policy["direct_full_support"]),
        "direct_atom_recall": _meets(direct["atom_recall"], ready_policy["direct_atom_recall"]),
        "direct_evidence_precision": _meets(
            direct["evidence_precision"], ready_policy["direct_evidence_precision"]
        ),
        "direct_mrr": _meets(direct["mrr"], ready_policy["direct_mrr"]),
        "direct_source_recall": _meets(
            direct["source_recall"], ready_policy["direct_source_recall"]
        ),
        "direct_citation_integrity": _meets(
            direct["citation_integrity"], ready_policy["direct_citation_integrity"]
        ),
        "supported_format_ingestion": _meets(
            summary["supported_format_ingestion"], ready_policy["supported_format_ingestion"]
        ),
        "direct_abstention": _meets(direct["abstention"], ready_policy["direct_abstention"]),
        "direct_german_atom_recall": _meets(
            direct["german_atom_recall"], ready_policy["direct_german_atom_recall"]
        ),
        "semantic_runs_identical": bool(summary["semantic_runs_identical"]),
    }
    conditional_checks = {
        "operator_full_support": _meets(
            operator["full_support"], conditional_policy["operator_full_support"]
        ),
        "operator_atom_recall": _meets(
            operator["atom_recall"], conditional_policy["operator_atom_recall"]
        ),
        "operator_source_recall": _meets(
            operator["source_recall"], conditional_policy["operator_source_recall"]
        ),
        "operator_citation_integrity": _meets(
            operator["citation_integrity"], conditional_policy["operator_citation_integrity"]
        ),
        "direct_full_support_floor": _meets(
            direct["full_support"], conditional_policy["direct_full_support"]
        ),
        "semantic_runs_identical": bool(summary["semantic_runs_identical"]),
    }
    failures = sorted(set(hard_failures))
    if not failures and all(ready_checks.values()):
        value = READY
        checks = ready_checks
    elif not failures and all(conditional_checks.values()):
        value = CONDITIONAL
        checks = conditional_checks
    else:
        value = NOT_READY
        checks = ready_checks
    blockers = sorted(name for name, passed in checks.items() if not passed)
    decision: dict[str, Any] = {
        "benchmark_version": "0.1.0",
        "decision": value,
        "failures": failures,
        "blockers": blockers,
        "satisfied": sorted(name for name, passed in checks.items() if passed),
        "summary_id": summary["summary_id"],
    }
    decision["decision_id"] = canonical_sha256(decision)
    return decision


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render the deterministic body-free human interpretation."""
    lines = [
        "# OpenARDP Semantic End-to-End Evaluation",
        "",
        f"**Decision:** `{decision['decision']}`",
        "",
        "This diagnostic evaluates the delivered evidence layer, not prose generation. Direct",
        "questions and frozen operator terms are reported separately; operator assistance is not",
        "semantic retrieval. CSV remains an explicit",
        "unsupported product format.",
        "",
        "## Exact results",
        "",
        "| Treatment | Full | Recall | Precision | MRR | Sources | Citations | Abstain | DE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for treatment in PRODUCT_TREATMENTS:
        metrics = summary["treatments"][treatment]
        lines.append(
            "| "
            + treatment
            + " | "
            + " | ".join(
                metrics[key]["ratio"]
                for key in (
                    "full_support",
                    "atom_recall",
                    "evidence_precision",
                    "mrr",
                    "source_recall",
                    "citation_integrity",
                    "abstention",
                    "german_atom_recall",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Semantic rows identical across two fresh workspaces: "
            f"`{str(summary['semantic_runs_identical']).lower()}`.",
            f"- Supported-format ingestion: `{summary['supported_format_ingestion']['ratio']}`.",
            f"- Hard failures: `{', '.join(decision['failures']) or 'none'}`.",
            f"- Decision blockers: `{', '.join(decision['blockers']) or 'none'}`.",
            f"- Retained capability gaps: `{', '.join(summary['capability_gaps']) or 'none'}`.",
            "",
            "F015 `NO-GO`, F020 `CONDITIONALLY_WORTHWHILE`, and F024",
            "`REALWORLD_BASELINE_READY` remain historical",
            "evidence. This result changes only the bounded semantic/source-quality assessment.",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CONDITIONAL",
    "NOT_READY",
    "READY",
    "decide",
    "render_report",
    "summarize",
]
