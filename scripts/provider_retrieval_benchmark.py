"""Pure body-free aggregation contracts for the frozen F029 comparison."""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

try:
    from scripts.semantic_e2e_benchmark import QUESTION_IDS, SemanticBenchmarkError
except ModuleNotFoundError:
    from semantic_e2e_benchmark import QUESTION_IDS, SemanticBenchmarkError

from openardp.domain.identity import canonical_json_bytes, canonical_sha256

BENCHMARK_VERSION = "0.3.0"
SUPPORTED_VERSIONS = ("0.1.0", "0.2.0", "0.3.0")
TREATMENTS = ("f027_lexical_direct", "f029_semantic_direct")
GERMAN_QUESTIONS = ("Q04", "Q08")
RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
READY = "PROVIDER_RETRIEVAL_READY"
NOT_READY = "PROVIDER_RETRIEVAL_NOT_READY"


def load_protocol(root: Path, version: str = BENCHMARK_VERSION) -> dict[str, Any]:
    """Load the exact frozen F029 protocol and verify its canonical identity."""
    if version not in SUPPORTED_VERSIONS:
        raise SemanticBenchmarkError("provider_protocol_version")
    path = root / f"benchmarks/provider-retrieval/v{version}/protocol.json"
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SemanticBenchmarkError("provider_protocol_invalid") from error
    if not isinstance(protocol, dict):
        raise SemanticBenchmarkError("provider_protocol_invalid")
    declared = protocol.get("protocol_id")
    payload = dict(protocol)
    payload.pop("protocol_id", None)
    if declared != canonical_sha256(payload):
        raise SemanticBenchmarkError("provider_protocol_identity")
    expected = {
        "benchmark_version": version,
        "binding_runs": 2,
        "direct_treatments": list(TREATMENTS),
        "german_questions": list(GERMAN_QUESTIONS),
        "question_count": len(QUESTION_IDS),
        "supported_formats": ["csv", "docx", "md", "pdf", "pptx", "txt"],
    }
    if any(protocol.get(key) != value for key, value in expected.items()):
        raise SemanticBenchmarkError("provider_protocol_contract")
    expected_retrieval = None
    if version in {"0.2.0", "0.3.0"}:
        expected_retrieval = {
            "hybrid_lexical_fallback": True,
            "retrieval_tier_order": ["minimum_relevant_lexical", "semantic"],
            "semantic_max_per_document": 32,
            "semantic_ranked_prefix": 4,
            "source_balanced_semantic_admission": True,
        }
    if version == "0.3.0" and expected_retrieval is not None:
        expected_retrieval["representation_precedence"] = "rich_then_text"
    if protocol.get("retrieval_profile") != expected_retrieval:
        raise SemanticBenchmarkError("provider_retrieval_profile")
    return protocol


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


def _metrics(rows: list[dict[str, Any]], questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if questions[str(row["question_id"])]["answerable"]]
    unsupported = [row for row in rows if not questions[str(row["question_id"])]["answerable"]]
    selected = sum(int(row["selected_count"]) for row in rows)
    relevant = sum(int(row["relevant_count"]) for row in rows)
    valid = sum(sum(bool(item["citation_valid"]) for item in row["selected"]) for row in rows)
    reciprocal = sum(
        (Fraction(1, int(row["first_relevant_rank"])) if row["first_relevant_rank"] else Fraction())
        for row in answerable
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


def _at_least(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) >= int(right["numerator"]) * int(
        left["denominator"]
    )


def _strictly_greater(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) > int(right["numerator"]) * int(
        left["denominator"]
    )


def _question_metric(row: dict[str, Any], key: str) -> dict[str, Any]:
    if key == "full_support":
        return _metric(Fraction(int(bool(row["full_support"])), 1))
    if key == "atom_recall":
        return _metric(_fraction(len(row["covered_atom_ids"]), int(row["required_atom_count"])))
    raise ValueError("unsupported question metric")


def summarize(
    rows: list[dict[str, Any]],
    questions: dict[str, dict[str, Any]],
    *,
    corpus_id: str,
    question_set_id: str,
    source_protocol_id: str,
    protocol_id: str,
    supported_formats_ingested: tuple[str, ...],
    semantic_runs_identical: bool,
    provider_metrics: dict[str, int],
    benchmark_version: str = BENCHMARK_VERSION,
) -> dict[str, Any]:
    """Recompute comparison, language/stratum/format slices and exact gates."""
    expected = [
        (question_id, treatment) for question_id in QUESTION_IDS for treatment in TREATMENTS
    ]
    actual = [(str(row.get("question_id")), str(row.get("treatment"))) for row in rows]
    if actual != expected or len(actual) != len(set(actual)):
        raise SemanticBenchmarkError("provider_observation_coverage")
    by_treatment = {
        treatment: _metrics([row for row in rows if row["treatment"] == treatment], questions)
        for treatment in TREATMENTS
    }
    slices: dict[str, Any] = {}
    dimensions = {
        "language": sorted({str(question["language"]) for question in questions.values()}),
        "stratum": sorted({str(question["stratum"]) for question in questions.values()}),
        "format": ["csv", "docx", "md", "pdf", "pptx", "txt"],
    }
    for dimension, values in dimensions.items():
        slices[dimension] = {}
        for value in values:
            identifiers = {
                question_id
                for question_id, question in questions.items()
                if (
                    value in question["required_formats"]
                    if dimension == "format"
                    else question[dimension] == value
                )
            }
            slices[dimension][value] = {
                treatment: _metrics(
                    [
                        row
                        for row in rows
                        if row["treatment"] == treatment and row["question_id"] in identifiers
                    ],
                    questions,
                )
                for treatment in TREATMENTS
            }
    lookup = {(row["question_id"], row["treatment"]): row for row in rows}
    german: dict[str, Any] = {}
    for question_id in GERMAN_QUESTIONS:
        lexical = lookup[(question_id, TREATMENTS[0])]
        semantic = lookup[(question_id, TREATMENTS[1])]
        lexical_atom = _question_metric(lexical, "atom_recall")
        semantic_atom = _question_metric(semantic, "atom_recall")
        lexical_full = _question_metric(lexical, "full_support")
        semantic_full = _question_metric(semantic, "full_support")
        german[question_id] = {
            "lexical_atom_recall": lexical_atom,
            "semantic_atom_recall": semantic_atom,
            "lexical_full_support": lexical_full,
            "semantic_full_support": semantic_full,
            "non_regression": _at_least(semantic_atom, lexical_atom)
            and _at_least(semantic_full, lexical_full),
            "strict_improvement": _strictly_greater(semantic_atom, lexical_atom)
            or _strictly_greater(semantic_full, lexical_full),
        }
    summary: dict[str, Any] = {
        "benchmark_version": benchmark_version,
        "corpus_id": corpus_id,
        "question_set_id": question_set_id,
        "source_protocol_id": source_protocol_id,
        "protocol_id": protocol_id,
        "row_count": len(rows),
        "closed_coverage": True,
        "semantic_runs_identical": semantic_runs_identical,
        "supported_formats_ingested": sorted(supported_formats_ingested),
        "treatments": by_treatment,
        "runtime": {
            treatment: {
                "wall_ns": sum(
                    int(row["wall_ns"]) for row in rows if row["treatment"] == treatment
                ),
                "cpu_ns": sum(int(row["cpu_ns"]) for row in rows if row["treatment"] == treatment),
            }
            for treatment in TREATMENTS
        },
        "slices": slices,
        "german_questions": german,
        "provider_metrics": provider_metrics,
    }
    summary["summary_id"] = canonical_sha256(summary)
    return summary


def decide(summary: dict[str, Any], *, hard_failures: list[str]) -> dict[str, Any]:
    """Apply the frozen F029 readiness gates using only exact integers."""
    lexical = summary["treatments"][TREATMENTS[0]]
    semantic = summary["treatments"][TREATMENTS[1]]
    checks = {
        "all_supported_formats_ingested": summary["supported_formats_ingested"]
        == ["csv", "docx", "md", "pdf", "pptx", "txt"],
        "semantic_runs_identical": bool(summary["semantic_runs_identical"]),
        "semantic_citation_integrity_complete": semantic["citation_integrity"]["ratio"]
        == "1.000000",
        "semantic_unsupported_abstention_complete": semantic["unsupported_abstention"]["ratio"]
        == "1.000000",
        "full_support_non_regression": _at_least(semantic["full_support"], lexical["full_support"]),
        "atom_recall_non_regression": _at_least(semantic["atom_recall"], lexical["atom_recall"]),
        "source_recall_non_regression": _at_least(
            semantic["source_recall"], lexical["source_recall"]
        ),
        "german_q04_non_regression": bool(summary["german_questions"]["Q04"]["non_regression"]),
        "german_q04_strict_improvement": bool(
            summary["german_questions"]["Q04"]["strict_improvement"]
        ),
        "german_q08_non_regression": bool(summary["german_questions"]["Q08"]["non_regression"]),
        "german_q08_strict_improvement": bool(
            summary["german_questions"]["Q08"]["strict_improvement"]
        ),
    }
    failures = sorted(set(hard_failures))
    value = READY if not failures and all(checks.values()) else NOT_READY
    decision: dict[str, Any] = {
        "benchmark_version": summary["benchmark_version"],
        "decision": value,
        "failures": failures,
        "blockers": sorted(name for name, passed in checks.items() if not passed),
        "satisfied": sorted(name for name, passed in checks.items() if passed),
        "summary_id": summary["summary_id"],
    }
    decision["decision_id"] = canonical_sha256(decision)
    return decision


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render a deterministic body-free F027/F029 comparison report."""
    lines = [
        "# OpenARDP Provider-Neutral Retrieval Evaluation",
        "",
        f"**Decision:** `{decision['decision']}`",
        "",
        "This frozen comparison runs the unchanged F025 questions directly against the F027",
        "lexical profile and the explicit offline F029 multilingual provider. It evaluates",
        "retrieved evidence and citations, not generated prose.",
        "",
        "## Exact direct-treatment metrics",
        "",
        "| Treatment | Full | Atoms | Sources | Precision | MRR | Citations | Abstain |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for treatment in TREATMENTS:
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
                    "source_recall",
                    "evidence_precision",
                    "mrr",
                    "citation_integrity",
                    "unsupported_abstention",
                )
            )
            + " |"
        )
    lines.extend(["", "## German cross-language questions", ""])
    for question_id in GERMAN_QUESTIONS:
        row = summary["german_questions"][question_id]
        lines.append(
            f"- {question_id}: atom recall {row['lexical_atom_recall']['ratio']} -> "
            f"{row['semantic_atom_recall']['ratio']}; full support "
            f"{row['lexical_full_support']['ratio']} -> "
            f"{row['semantic_full_support']['ratio']}."
        )
    metrics = summary["provider_metrics"]
    lines.extend(
        [
            "",
            "## Runtime boundary",
            "",
            f"- F027 summed query wall ns: {summary['runtime'][TREATMENTS[0]]['wall_ns']}",
            f"- F029 summed query wall ns: {summary['runtime'][TREATMENTS[1]]['wall_ns']}",
            f"- Provider requests: {metrics['requests']}",
            f"- Passages scored: {metrics['passages_scored']}",
            f"- Passage-cache hits: {metrics['cache_hits']}",
            f"- Peak provider-worker RSS bytes: {metrics['peak_worker_rss_bytes']}",
            "- Embeddings remained disposable worker memory and are absent from this result.",
            "- Both unsupported questions must abstain; no benchmark query rewriting is used.",
            "",
            "## Gate outcome",
            "",
            f"- Blockers: {', '.join(decision['blockers']) if decision['blockers'] else 'none'}",
            f"- Failures: {', '.join(decision['failures']) if decision['failures'] else 'none'}",
            "",
        ]
    )
    return "\n".join(lines)


def file_digest(path: Path) -> tuple[str, int]:
    """Return exact SHA-256 identity and size for one result artifact."""
    payload = path.read_bytes()
    return "sha256:" + hashlib.sha256(payload).hexdigest(), len(payload)


def semantic_projection(rows: list[dict[str, Any]]) -> bytes:
    """Return canonical timing-free observation bytes for determinism checks."""
    return canonical_json_bytes(
        [
            {key: value for key, value in row.items() if key not in {"wall_ns", "cpu_ns"}}
            for row in rows
        ]
    )


__all__ = [
    "BENCHMARK_VERSION",
    "GERMAN_QUESTIONS",
    "NOT_READY",
    "READY",
    "RESULT_NAMES",
    "SUPPORTED_VERSIONS",
    "TREATMENTS",
    "decide",
    "file_digest",
    "load_protocol",
    "render_report",
    "semantic_projection",
    "summarize",
]
