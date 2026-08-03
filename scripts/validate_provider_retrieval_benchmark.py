"""Independently validate one body-free F029 result using only the stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

VERSION = "0.3.0"
QUESTION_IDS = tuple(f"Q{value:02d}" for value in range(1, 20))
TREATMENTS = ("f027_lexical_direct", "f029_semantic_direct")
GERMAN = ("Q04", "Q08")
FILES = ("decision.json", "observations.json", "report.md", "run-manifest.json", "summary.json")
READY = "PROVIDER_RETRIEVAL_READY"
NOT_READY = "PROVIDER_RETRIEVAL_NOT_READY"


class ValidationError(ValueError):
    """Stable validation failure without result-content disclosure."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _identity(value: dict[str, Any], field: str) -> str:
    declared = value.get(field)
    payload = dict(value)
    payload.pop(field, None)
    expected = "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()
    if declared != expected:
        raise ValidationError(f"{field}_mismatch")
    return expected


def _load(
    path: Path, maximum: int = 4_194_304, *, require_canonical: bool = True
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValidationError("json_file_invalid")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValidationError("duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValidationError("non_finite_json")),
        )
    except ValidationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError("json_invalid") from error
    if not isinstance(value, dict) or (
        require_canonical and path.read_bytes() != _canonical(value) + b"\n"
    ):
        raise ValidationError("json_not_canonical")
    return value


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


def _fraction(numerator: int, denominator: int, *, vacuous: bool = False) -> Fraction:
    if denominator == 0:
        return Fraction(1 if vacuous else 0, 1)
    return Fraction(numerator, denominator)


def _metrics(rows: list[dict[str, Any]], questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if questions[str(row["question_id"])]["answerable"]]
    unsupported = [row for row in rows if not questions[str(row["question_id"])]["answerable"]]
    selected = sum(int(row["selected_count"]) for row in rows)
    relevant = sum(int(row["relevant_count"]) for row in rows)
    valid = sum(sum(bool(item["citation_valid"]) for item in row["selected"]) for row in rows)
    reciprocal = sum(
        Fraction(1, int(row["first_relevant_rank"])) if row["first_relevant_rank"] else Fraction()
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


def _greater(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) > int(right["numerator"]) * int(
        left["denominator"]
    )


def _question_metric(row: dict[str, Any], key: str) -> dict[str, Any]:
    if key == "full_support":
        return _metric(Fraction(int(bool(row["full_support"])), 1))
    return _metric(_fraction(len(row["covered_atom_ids"]), int(row["required_atom_count"])))


def _validate_rows(
    observations: dict[str, Any], questions: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = observations.get("rows")
    if not isinstance(rows, list):
        raise ValidationError("rows_invalid")
    expected = [
        (question_id, treatment) for question_id in QUESTION_IDS for treatment in TREATMENTS
    ]
    actual = [
        (row.get("question_id"), row.get("treatment")) for row in rows if isinstance(row, dict)
    ]
    if actual != expected or len(rows) != len(expected):
        raise ValidationError("row_coverage")
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
    for row in rows:
        if not isinstance(row, dict) or set(row) != row_keys:
            raise ValidationError("row_shape")
        question = questions[str(row["question_id"])]
        selected = row["selected"]
        if not isinstance(selected, list):
            raise ValidationError("selected_shape")
        for order, item in enumerate(selected):
            if not isinstance(item, dict) or set(item) != selected_keys or item["order"] != order:
                raise ValidationError("selected_shape")
            if not isinstance(item["evidence_id"], str) or not item["evidence_id"]:
                raise ValidationError("selected_identity")
            if not isinstance(item["source_key"], str) or not isinstance(
                item["covered_atom_ids"], list
            ):
                raise ValidationError("selected_shape")
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
        full = (
            row["outcome"] == "pass"
            and answerable
            and len(covered_atoms) == len(question["support_atoms"])
            and len(covered_sources) == len(question["required_sources"])
        )
        checks = {
            "covered_atom_ids": covered_atoms,
            "covered_source_keys": covered_sources,
            "required_atom_count": len(question["support_atoms"]),
            "required_source_count": len(question["required_sources"]),
            "full_support": full,
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
        if any(row[key] != value for key, value in checks.items()):
            raise ValidationError("row_derived_fact")
        identity_value = {
            key: value
            for key, value in row.items()
            if key not in {"observation_id", "wall_ns", "cpu_ns", "context_audit"}
        }
        # Producer IDs intentionally precede the optional audit projection.
        if (
            row["observation_id"]
            != "sha256:" + hashlib.sha256(_canonical(identity_value)).hexdigest()
        ):
            raise ValidationError("observation_identity")
        if not isinstance(row["wall_ns"], int) or not isinstance(row["cpu_ns"], int):
            raise ValidationError("timing_shape")
        audit = row["context_audit"]
        if not isinstance(audit, dict) or set(audit) != {
            "algorithm",
            "notices",
            "rejected_reason_counts",
            "warnings",
        }:
            raise ValidationError("audit_shape")
    return rows


def _summarize(
    rows: list[dict[str, Any]],
    questions: dict[str, dict[str, Any]],
    protocol: dict[str, Any],
    semantic_identical: bool,
    provider_metrics: dict[str, int],
    supported_formats: list[str],
    version: str,
) -> dict[str, Any]:
    treatments = {
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
                identifier
                for identifier, question in questions.items()
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
    for question_id in GERMAN:
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
            "strict_improvement": _greater(semantic_atom, lexical_atom)
            or _greater(semantic_full, lexical_full),
        }
    summary: dict[str, Any] = {
        "benchmark_version": version,
        "corpus_id": protocol["corpus_id"],
        "question_set_id": protocol["question_set_id"],
        "source_protocol_id": protocol["source_protocol_id"],
        "protocol_id": protocol["protocol_id"],
        "row_count": len(rows),
        "closed_coverage": True,
        "semantic_runs_identical": semantic_identical,
        "supported_formats_ingested": supported_formats,
        "treatments": treatments,
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
    summary["summary_id"] = "sha256:" + hashlib.sha256(_canonical(summary)).hexdigest()
    return summary


def _decide(summary: dict[str, Any], failures: list[str]) -> dict[str, Any]:
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
    clean_failures = sorted(set(failures))
    decision: dict[str, Any] = {
        "benchmark_version": summary["benchmark_version"],
        "decision": READY if not clean_failures and all(checks.values()) else NOT_READY,
        "failures": clean_failures,
        "blockers": sorted(key for key, value in checks.items() if not value),
        "satisfied": sorted(key for key, value in checks.items() if value),
        "summary_id": summary["summary_id"],
    }
    decision["decision_id"] = "sha256:" + hashlib.sha256(_canonical(decision)).hexdigest()
    return decision


def _report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
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
    for question_id in GERMAN:
        row = summary["german_questions"][question_id]
        lines.append(
            f"- {question_id}: atom recall {row['lexical_atom_recall']['ratio']} -> "
            f"{row['semantic_atom_recall']['ratio']}; full support "
            f"{row['lexical_full_support']['ratio']} -> {row['semantic_full_support']['ratio']}."
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


def validate(root: Path, result: Path, *, protocol_version: str = VERSION) -> dict[str, Any]:
    """Validate exact inputs, observations, derived files and manifest closure."""
    if protocol_version not in {"0.1.0", "0.2.0", "0.3.0"}:
        raise ValidationError("protocol_version")
    if result.is_symlink() or not result.is_dir():
        raise ValidationError("result_directory")
    if sorted(path.name for path in result.iterdir()) != sorted(FILES):
        raise ValidationError("result_file_set")
    protocol = _load(
        root / f"benchmarks/provider-retrieval/v{protocol_version}/protocol.json",
        require_canonical=False,
    )
    _identity(protocol, "protocol_id")
    expected_retrieval = None
    if protocol_version in {"0.2.0", "0.3.0"}:
        expected_retrieval = {
            "hybrid_lexical_fallback": True,
            "retrieval_tier_order": ["minimum_relevant_lexical", "semantic"],
            "semantic_max_per_document": 32,
            "semantic_ranked_prefix": 4,
            "source_balanced_semantic_admission": True,
        }
    if protocol_version == "0.3.0" and expected_retrieval is not None:
        expected_retrieval["representation_precedence"] = "rich_then_text"
    if protocol.get("retrieval_profile") != expected_retrieval:
        raise ValidationError("retrieval_profile")
    question_file = _load(
        root / "benchmarks/semantic-e2e/v0.1.0/questions.json",
        require_canonical=False,
    )
    _identity(question_file, "question_set_id")
    question_rows = question_file.get("questions")
    if not isinstance(question_rows, list):
        raise ValidationError("questions_shape")
    questions = {str(row["question_id"]): row for row in question_rows}
    if tuple(questions) != QUESTION_IDS:
        raise ValidationError("question_coverage")
    observations = _load(result / "observations.json")
    if observations.get("benchmark_version") != protocol_version:
        raise ValidationError("observation_version")
    if any(
        observations.get(key) != protocol[key]
        for key in ("corpus_id", "question_set_id", "protocol_id")
    ):
        raise ValidationError("observation_inputs")
    rows = _validate_rows(observations, questions)
    manifest = _load(result / "run-manifest.json")
    if manifest.get("fresh_runs") != 2 or manifest.get("offline") is not True:
        raise ValidationError("manifest_execution")
    recipe = manifest.get("provider_recipe")
    second_recipe = manifest.get("second_provider_recipe")
    if not isinstance(recipe, dict) or not isinstance(second_recipe, dict):
        raise ValidationError("provider_recipe")
    _identity(recipe, "recipe_id")
    _identity(second_recipe, "recipe_id")
    model = protocol["model"]
    if any(
        recipe.get(field) != model[source]
        for field, source in (
            ("model_id", "model_id"),
            ("model_revision", "model_revision"),
            ("model_bundle_id", "model_bundle_id"),
            ("dimensions", "dimensions"),
            ("max_tokens", "max_tokens"),
        )
    ):
        raise ValidationError("provider_recipe_model")
    metrics = manifest.get("first_provider_metrics")
    if not isinstance(metrics, dict) or set(metrics) != {
        "cache_hits",
        "passages_scored",
        "peak_worker_rss_bytes",
        "requests",
    }:
        raise ValidationError("provider_metrics")
    supported_formats = manifest.get("supported_formats_ingested")
    if not isinstance(supported_formats, list) or not all(
        isinstance(value, str) for value in supported_formats
    ):
        raise ValidationError("supported_formats")
    summary = _summarize(
        rows,
        questions,
        protocol,
        bool(manifest.get("semantic_runs_identical")),
        metrics,
        supported_formats,
        protocol_version,
    )
    published_summary = _load(result / "summary.json")
    if published_summary != summary:
        raise ValidationError("summary_mismatch")
    failures = [] if manifest.get("all_runs_identical") else ["fresh_run_mismatch"]
    if manifest.get("supported_formats_ingested") != manifest.get(
        "second_supported_formats_ingested"
    ):
        failures.append("ingested_format_mismatch")
    if recipe != second_recipe:
        failures.append("provider_recipe_mismatch")
    second_failure_count = manifest.get("second_failure_count")
    if not isinstance(second_failure_count, int) or isinstance(second_failure_count, bool):
        raise ValidationError("second_failure_count")
    if any(row["outcome"] == "failed" for row in rows) or second_failure_count:
        failures.append("product_runtime_failure")
    decision = _decide(summary, failures)
    published_decision = _load(result / "decision.json")
    if published_decision != decision:
        raise ValidationError("decision_mismatch")
    if (result / "report.md").read_text(encoding="utf-8") != _report(summary, decision):
        raise ValidationError("report_mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(FILES) - {"run-manifest.json"}:
        raise ValidationError("manifest_files")
    for name, facts in files.items():
        payload = (result / name).read_bytes()
        expected = {
            "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "byte_length": len(payload),
        }
        if facts != expected:
            raise ValidationError("manifest_file_digest")
    _identity(manifest, "run_id")
    if sum((result / name).stat().st_size for name in FILES) > int(protocol["result_max_bytes"]):
        raise ValidationError("result_size")
    forbidden = {
        "body",
        "content",
        "document_text",
        "query",
        "vector",
        "embedding",
        "path",
        "hostname",
        "username",
    }
    stack: list[Any] = [observations, summary, decision, manifest]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if forbidden & {str(key).casefold() for key in value}:
                raise ValidationError("forbidden_result_field")
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, str) and (value.startswith("/Users/") or value.startswith("C:\\")):
            raise ValidationError("local_path_leak")
    return decision


def main() -> int:
    """Validate one explicit result path without importing project code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument(
        "--protocol-version",
        choices=("0.1.0", "0.2.0", "0.3.0"),
        default="0.3.0",
    )
    arguments = parser.parse_args()
    try:
        decision = validate(
            arguments.repository_root.resolve(strict=True),
            arguments.result,
            protocol_version=arguments.protocol_version,
        )
    except (OSError, ValidationError, KeyError, TypeError, ValueError):
        print("provider_retrieval_result_invalid")
        return 7
    print(f"provider_retrieval_result_valid decision={decision['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
