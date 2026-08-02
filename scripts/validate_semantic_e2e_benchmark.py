"""Independent stdlib-only validator for frozen F025 inputs and results."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
CORPUS_ID = "sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd"
TREATMENTS = ("openardp_direct", "openardp_operator")
QUESTION_IDS = tuple(f"Q{value:02d}" for value in range(1, 20))
RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
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


class ValidationFailure(ValueError):
    """Stable body-free validation failure."""


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
            parse_constant=lambda _value: (_ for _ in ()).throw(ValidationFailure("json_value")),
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
        if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValidationFailure("json_value")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise ValidationFailure("json_value")
        return
    if isinstance(value, list):
        for item in value:
            _safe(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for key, item in value.items():
            _safe(key)
            _safe(item)
        return
    raise ValidationFailure("json_value")


def _canonical(value: Any) -> bytes:
    _safe(value)
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _identity(value: dict[str, Any], field: str) -> None:
    declared = value.get(field)
    if not isinstance(declared, str) or SHA.fullmatch(declared) is None:
        raise ValidationFailure("identity")
    projection = dict(value)
    projection.pop(field)
    if declared != _sha(projection):
        raise ValidationFailure("identity")


def _closed(value: dict[str, Any], fields: set[str], code: str) -> None:
    if set(value) != fields:
        raise ValidationFailure(code)


def _questions(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    base = root / "benchmarks/semantic-e2e/v0.1.0"
    questions = _load(base / "questions.json")
    protocol = _load(base / "protocol.json")
    schema = _load(base / "questions.schema.json")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValidationFailure("schema")
    _closed(
        questions,
        {"schema_version", "benchmark_version", "corpus_id", "questions", "question_set_id"},
        "question_fields",
    )
    _closed(
        protocol,
        {
            "benchmark_version",
            "protocol_id",
            "corpus_id",
            "question_count",
            "product_treatments",
            "oracle_treatment",
            "product_formats",
            "unsupported_product_formats",
            "context",
            "normalization",
            "thresholds",
            "execution",
            "privacy",
        },
        "protocol_fields",
    )
    _identity(questions, "question_set_id")
    _identity(protocol, "protocol_id")
    if (
        questions.get("schema_version") != VERSION
        or questions.get("benchmark_version") != VERSION
        or protocol.get("benchmark_version") != VERSION
        or questions.get("corpus_id") != CORPUS_ID
        or protocol.get("corpus_id") != CORPUS_ID
        or protocol.get("question_count") != 19
        or protocol.get("product_treatments") != list(TREATMENTS)
        or protocol.get("unsupported_product_formats") != ["csv"]
    ):
        raise ValidationFailure("input_contract")
    records = questions.get("questions")
    if not isinstance(records, list) or len(records) != 19:
        raise ValidationFailure("question_count")
    identifiers = [item.get("question_id") for item in records if isinstance(item, dict)]
    if tuple(identifiers) != QUESTION_IDS:
        raise ValidationFailure("question_order")
    by_id: dict[str, dict[str, Any]] = {}
    formats: set[str] = set()
    languages: set[str] = set()
    strata: set[str] = set()
    question_fields = {
        "question_id",
        "language",
        "stratum",
        "question",
        "operator_query",
        "reference_answer",
        "answerable",
        "temporal_scope",
        "required_formats",
        "required_sources",
        "acceptable_sources",
        "support_atoms",
        "source_fitness",
    }
    for item in records:
        if not isinstance(item, dict):
            raise ValidationFailure("question_shape")
        _closed(item, question_fields, "question_fields")
        for name in ("required_formats", "required_sources", "acceptable_sources"):
            values = item[name]
            if not isinstance(values, list) or values != sorted(set(values)):
                raise ValidationFailure("question_order")
        atoms = item["support_atoms"]
        fitness = item["source_fitness"]
        if not isinstance(atoms, list) or not isinstance(fitness, list):
            raise ValidationFailure("question_shape")
        atom_ids = [atom.get("atom_id") for atom in atoms if isinstance(atom, dict)]
        fitness_ids = [entry.get("source_key") for entry in fitness if isinstance(entry, dict)]
        if atom_ids != sorted(set(atom_ids)) or fitness_ids != sorted(set(fitness_ids)):
            raise ValidationFailure("question_order")
        for atom in atoms:
            if not isinstance(atom, dict):
                raise ValidationFailure("atom_shape")
            _closed(atom, {"atom_id", "source_key", "variants", "required"}, "atom_fields")
            variants = atom["variants"]
            if (
                not isinstance(atom["atom_id"], str)
                or not isinstance(atom["source_key"], str)
                or atom["required"] is not True
                or not isinstance(variants, list)
                or not variants
                or not all(isinstance(value, str) and value for value in variants)
            ):
                raise ValidationFailure("atom_shape")
        for entry in fitness:
            if not isinstance(entry, dict):
                raise ValidationFailure("fitness_shape")
            _closed(
                entry,
                {
                    "source_key",
                    "publisher_authority",
                    "directness",
                    "temporal_fit",
                    "integrity",
                    "reuse_basis",
                    "rationale",
                },
                "fitness_fields",
            )
            dimensions = (
                entry["publisher_authority"],
                entry["directness"],
                entry["temporal_fit"],
                entry["integrity"],
                entry["reuse_basis"],
            )
            if (
                not isinstance(entry["source_key"], str)
                or not isinstance(entry["rationale"], str)
                or not entry["rationale"]
                or any(
                    isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2
                    for value in dimensions
                )
            ):
                raise ValidationFailure("fitness_shape")
        if bool(item["answerable"]):
            if (
                not atoms
                or not item["required_sources"]
                or fitness_ids != item["acceptable_sources"]
            ):
                raise ValidationFailure("answerable")
            if {atom["source_key"] for atom in atoms} != set(item["required_sources"]):
                raise ValidationFailure("answerable")
        elif atoms or item["required_sources"] or item["acceptable_sources"] or fitness:
            raise ValidationFailure("answerable")
        by_id[str(item["question_id"])] = item
        formats.update(item["required_formats"])
        languages.add(str(item["language"]))
        strata.add(str(item["stratum"]))
    if formats != {"csv", "docx", "md", "pdf", "pptx", "txt"}:
        raise ValidationFailure("format_coverage")
    if languages != {"de", "en"} or len(strata) != 6:
        raise ValidationFailure("question_coverage")
    return questions, protocol, by_id


def _row(row: dict[str, Any], question: dict[str, Any], treatment: str) -> None:
    fields = {
        "question_id",
        "treatment",
        "outcome",
        "failure_category",
        "selected",
        "required_atom_count",
        "covered_atom_ids",
        "required_source_count",
        "covered_source_keys",
        "full_support",
        "abstained",
        "citation_integrity_complete",
        "relevant_count",
        "selected_count",
        "first_relevant_rank",
        "source_fitness_score",
        "source_fitness_max",
        "observation_id",
        "wall_ns",
        "cpu_ns",
    }
    _closed(row, fields, "row_fields")
    if row["question_id"] != question["question_id"] or row["treatment"] != treatment:
        raise ValidationFailure("row_key")
    selected = row["selected"]
    if not isinstance(selected, list):
        raise ValidationFailure("selected")
    atom_by_id = {atom["atom_id"]: atom for atom in question["support_atoms"]}
    fitness_by_source = {item["source_key"]: item for item in question["source_fitness"]}
    selected_fields = {
        "order",
        "evidence_id",
        "source_key",
        "representation",
        "anchor_type",
        "covered_atom_ids",
        "relevant",
        "citation_valid",
        "source_fitness_score",
        "source_fitness_max",
    }
    for order, evidence in enumerate(selected):
        if not isinstance(evidence, dict):
            raise ValidationFailure("selected")
        _closed(evidence, selected_fields, "selected_fields")
        covered = evidence["covered_atom_ids"]
        if evidence["order"] != order or covered != sorted(set(covered)):
            raise ValidationFailure("selected_order")
        if any(
            atom_id not in atom_by_id or atom_by_id[atom_id]["source_key"] != evidence["source_key"]
            for atom_id in covered
        ):
            raise ValidationFailure("selected_atoms")
        relevant = bool(covered) and evidence["source_key"] in question["acceptable_sources"]
        if evidence["relevant"] is not relevant:
            raise ValidationFailure("selected_relevance")
        score = 0
        maximum = 0
        if relevant:
            fitness = fitness_by_source[evidence["source_key"]]
            score = sum(
                int(fitness[key])
                for key in (
                    "publisher_authority",
                    "directness",
                    "temporal_fit",
                    "integrity",
                    "reuse_basis",
                )
            )
            maximum = 10
        if evidence["source_fitness_score"] != score or evidence["source_fitness_max"] != maximum:
            raise ValidationFailure("selected_fitness")
    covered_atoms = sorted({atom for item in selected for atom in item["covered_atom_ids"]})
    covered_sources = sorted(
        {
            item["source_key"]
            for item in selected
            if item["relevant"] and item["source_key"] in question["required_sources"]
        }
    )
    full = (
        row["outcome"] == "pass"
        and question["answerable"]
        and len(covered_atoms) == len(question["support_atoms"])
        and len(covered_sources) == len(question["required_sources"])
    )
    expected = {
        "required_atom_count": len(question["support_atoms"]),
        "covered_atom_ids": covered_atoms,
        "required_source_count": len(question["required_sources"]),
        "covered_source_keys": covered_sources,
        "full_support": full,
        "abstained": not selected,
        "citation_integrity_complete": bool(selected)
        and all(item["citation_valid"] for item in selected),
        "relevant_count": sum(bool(item["relevant"]) for item in selected),
        "selected_count": len(selected),
        "first_relevant_rank": next(
            (index + 1 for index, item in enumerate(selected) if item["relevant"]), None
        ),
        "source_fitness_score": sum(item["source_fitness_score"] for item in selected),
        "source_fitness_max": sum(item["source_fitness_max"] for item in selected),
    }
    if any(row[key] != value for key, value in expected.items()):
        raise ValidationFailure("row_aggregate")
    semantic = {key: value for key, value in row.items() if key not in {"wall_ns", "cpu_ns"}}
    declared = semantic.pop("observation_id")
    if declared != _sha(semantic):
        raise ValidationFailure("row_identity")
    if (
        question["answerable"]
        and "csv" in question["required_formats"]
        and (row["outcome"] != "unsupported_format" or selected)
    ):
        raise ValidationFailure("csv_boundary")


def _ratio(value: Fraction) -> str:
    with localcontext() as context:
        context.prec = 30
        result = (Decimal(value.numerator) / Decimal(value.denominator)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_EVEN
        )
    return format(result, "f")


def _metric(value: Fraction) -> dict[str, Any]:
    return {"numerator": value.numerator, "denominator": value.denominator, "ratio": _ratio(value)}


def _fraction(numerator: int | Fraction, denominator: int, vacuous: bool = False) -> Fraction:
    return (
        Fraction(1 if vacuous else 0, 1) if denominator == 0 else Fraction(numerator, denominator)
    )


def _metrics(rows: list[dict[str, Any]], questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if questions[row["question_id"]]["answerable"]]
    unsupported = [row for row in rows if not questions[row["question_id"]]["answerable"]]
    german = [row for row in answerable if questions[row["question_id"]]["language"] == "de"]
    selected = sum(row["selected_count"] for row in rows)
    relevant = sum(row["relevant_count"] for row in rows)
    valid = sum(sum(item["citation_valid"] for item in row["selected"]) for row in rows)
    reciprocal = sum(
        (Fraction(1, row["first_relevant_rank"]) if row["first_relevant_rank"] else Fraction())
        for row in answerable
    )
    return {
        "full_support": _metric(
            _fraction(sum(row["full_support"] for row in answerable), len(answerable))
        ),
        "atom_recall": _metric(
            _fraction(
                sum(len(row["covered_atom_ids"]) for row in answerable),
                sum(row["required_atom_count"] for row in answerable),
            )
        ),
        "evidence_precision": _metric(_fraction(relevant, selected)),
        "mrr": _metric(_fraction(reciprocal, len(answerable))),
        "source_recall": _metric(
            _fraction(
                sum(len(row["covered_source_keys"]) for row in answerable),
                sum(row["required_source_count"] for row in answerable),
            )
        ),
        "citation_integrity": _metric(_fraction(valid, selected, True)),
        "abstention": _metric(
            _fraction(sum(row["abstained"] for row in unsupported), len(unsupported))
        ),
        "german_atom_recall": _metric(
            _fraction(
                sum(len(row["covered_atom_ids"]) for row in german),
                sum(row["required_atom_count"] for row in german),
            )
        ),
        "source_fitness": _metric(
            _fraction(
                sum(row["source_fitness_score"] for row in rows),
                sum(row["source_fitness_max"] for row in rows),
                True,
            )
        ),
    }


def _summary(
    observations: dict[str, Any], questions: dict[str, dict[str, Any]], original: dict[str, Any]
) -> dict[str, Any]:
    rows = observations["rows"]
    by_treatment = {
        treatment: _metrics([row for row in rows if row["treatment"] == treatment], questions)
        for treatment in TREATMENTS
    }
    ingestion = Fraction(len(set(original["supported_formats_ingested"])), 5)
    value: dict[str, Any] = {
        "benchmark_version": VERSION,
        "corpus_id": observations["corpus_id"],
        "question_set_id": observations["question_set_id"],
        "protocol_id": observations["protocol_id"],
        "row_count": len(rows),
        "closed_coverage": True,
        "semantic_runs_identical": original["semantic_runs_identical"],
        "supported_formats_ingested": original["supported_formats_ingested"],
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
    value["summary_id"] = _sha(value)
    return value


def _meets(metric: dict[str, Any], threshold: list[int]) -> bool:
    return metric["numerator"] * threshold[1] >= threshold[0] * metric["denominator"]


def _decision(
    summary: dict[str, Any], protocol: dict[str, Any], failures: list[str]
) -> dict[str, Any]:
    direct = summary["treatments"]["openardp_direct"]
    operator = summary["treatments"]["openardp_operator"]
    ready = protocol["thresholds"]["ready"]
    conditional = protocol["thresholds"]["conditional"]
    ready_checks = {
        "direct_full_support": _meets(direct["full_support"], ready["direct_full_support"]),
        "direct_atom_recall": _meets(direct["atom_recall"], ready["direct_atom_recall"]),
        "direct_evidence_precision": _meets(
            direct["evidence_precision"], ready["direct_evidence_precision"]
        ),
        "direct_mrr": _meets(direct["mrr"], ready["direct_mrr"]),
        "direct_source_recall": _meets(direct["source_recall"], ready["direct_source_recall"]),
        "direct_citation_integrity": _meets(
            direct["citation_integrity"], ready["direct_citation_integrity"]
        ),
        "supported_format_ingestion": _meets(
            summary["supported_format_ingestion"], ready["supported_format_ingestion"]
        ),
        "direct_abstention": _meets(direct["abstention"], ready["direct_abstention"]),
        "direct_german_atom_recall": _meets(
            direct["german_atom_recall"], ready["direct_german_atom_recall"]
        ),
        "semantic_runs_identical": summary["semantic_runs_identical"],
    }
    conditional_checks = {
        "operator_full_support": _meets(
            operator["full_support"], conditional["operator_full_support"]
        ),
        "operator_atom_recall": _meets(
            operator["atom_recall"], conditional["operator_atom_recall"]
        ),
        "operator_source_recall": _meets(
            operator["source_recall"], conditional["operator_source_recall"]
        ),
        "operator_citation_integrity": _meets(
            operator["citation_integrity"], conditional["operator_citation_integrity"]
        ),
        "direct_full_support_floor": _meets(
            direct["full_support"], conditional["direct_full_support"]
        ),
        "semantic_runs_identical": summary["semantic_runs_identical"],
    }
    failures = sorted(set(failures))
    if not failures and all(ready_checks.values()):
        outcome, checks = "SEMANTIC_E2E_READY", ready_checks
    elif not failures and all(conditional_checks.values()):
        outcome, checks = "SEMANTIC_E2E_CONDITIONALLY_READY", conditional_checks
    else:
        outcome, checks = "SEMANTIC_E2E_NOT_READY", ready_checks
    value: dict[str, Any] = {
        "benchmark_version": VERSION,
        "decision": outcome,
        "failures": failures,
        "blockers": sorted(name for name, passed in checks.items() if not passed),
        "satisfied": sorted(name for name, passed in checks.items() if passed),
        "summary_id": summary["summary_id"],
    }
    value["decision_id"] = _sha(value)
    return value


def _report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
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


def _privacy(value: Any) -> None:
    if isinstance(value, dict):
        if set(value) & FORBIDDEN_KEYS:
            raise ValidationFailure("privacy")
        for item in value.values():
            _privacy(item)
    elif isinstance(value, list):
        for item in value:
            _privacy(item)
    elif isinstance(value, str) and ("/Users/" in value or "\\Users\\" in value):
        raise ValidationFailure("privacy")


def validate_result(root: Path, result: Path) -> str:
    """Independently recompute the complete result and return the decision."""
    questions_doc, protocol, questions = _questions(root)
    if result.is_symlink() or not result.is_dir():
        raise ValidationFailure("result_root")
    files_on_disk = {
        path.name for path in result.iterdir() if path.is_file() and not path.is_symlink()
    }
    if files_on_disk != set(RESULT_NAMES) or any(path.is_symlink() for path in result.iterdir()):
        raise ValidationFailure("result_inventory")
    observations = _load(result / "observations.json")
    summary = _load(result / "summary.json")
    decision = _load(result / "decision.json")
    manifest = _load(result / "run-manifest.json")
    _closed(
        observations,
        {"benchmark_version", "corpus_id", "question_set_id", "protocol_id", "rows"},
        "observations_fields",
    )
    _closed(
        manifest,
        {
            "benchmark_version",
            "corpus_id",
            "question_set_id",
            "protocol_id",
            "model_bundle_id",
            "offline",
            "fresh_runs",
            "total_wall_ns",
            "files",
            "run_id",
        },
        "manifest_fields",
    )
    for name, value in (
        ("observations.json", observations),
        ("summary.json", summary),
        ("decision.json", decision),
        ("run-manifest.json", manifest),
    ):
        if (result / name).read_bytes() != _canonical(value) + b"\n":
            raise ValidationFailure("result_canonical")
    rows = observations.get("rows")
    if not isinstance(rows, list) or len(rows) != 38:
        raise ValidationFailure("row_count")
    expected = [
        (question_id, treatment) for question_id in QUESTION_IDS for treatment in TREATMENTS
    ]
    actual = [
        (row.get("question_id"), row.get("treatment")) for row in rows if isinstance(row, dict)
    ]
    if actual != expected:
        raise ValidationFailure("row_coverage")
    for row, (question_id, treatment) in zip(rows, expected, strict=True):
        _row(row, questions[question_id], treatment)
    recomputed_summary = _summary(observations, questions, summary)
    if summary != recomputed_summary:
        raise ValidationFailure("summary")
    failures = [] if summary["semantic_runs_identical"] else ["semantic_fresh_run_mismatch"]
    if any(row["outcome"] == "failed" for row in rows):
        failures.append("product_runtime_failure")
    recomputed_decision = _decision(summary, protocol, failures)
    if decision != recomputed_decision:
        raise ValidationFailure("decision")
    if (result / "report.md").read_text(encoding="utf-8") != _report(summary, decision):
        raise ValidationFailure("report")
    files = {}
    for name in RESULT_NAMES:
        if name == "run-manifest.json":
            continue
        payload = (result / name).read_bytes()
        files[name] = {
            "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "byte_length": len(payload),
        }
    projection = dict(manifest)
    run_id = projection.pop("run_id", None)
    if manifest.get("files") != files or run_id != _sha(projection):
        raise ValidationFailure("manifest")
    if (
        summary.get("supported_formats_ingested") != ["docx", "md", "pdf", "pptx", "txt"]
        or manifest.get("offline") is not True
        or manifest.get("fresh_runs") != 2
        or not isinstance(manifest.get("total_wall_ns"), int)
        or manifest["total_wall_ns"] < 1
        or not isinstance(manifest.get("model_bundle_id"), str)
        or SHA.fullmatch(manifest["model_bundle_id"]) is None
        or sum((result / name).stat().st_size for name in RESULT_NAMES)
        > protocol["execution"]["result_max_bytes"]
    ):
        raise ValidationFailure("result_contract")
    if (
        observations.get("question_set_id") != questions_doc["question_set_id"]
        or observations.get("protocol_id") != protocol["protocol_id"]
        or manifest.get("question_set_id") != questions_doc["question_set_id"]
        or manifest.get("protocol_id") != protocol["protocol_id"]
    ):
        raise ValidationFailure("input_binding")
    for value in (observations, summary, decision, manifest):
        _privacy(value)
    return str(decision["decision"])


def main() -> int:
    """Validate frozen inputs alone or one complete result directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--inputs-only", action="store_true")
    parser.add_argument("--result", type=Path)
    arguments = parser.parse_args()
    try:
        _questions(arguments.repository_root)
        if arguments.inputs_only:
            if arguments.result is not None:
                raise ValidationFailure("arguments")
            print("semantic_inputs_valid")
            return 0
        if arguments.result is None:
            raise ValidationFailure("arguments")
        decision = validate_result(arguments.repository_root, arguments.result)
    except (OSError, ValidationFailure, ValueError):
        print("semantic_result_invalid")
        return 6
    print(f"semantic_result_valid decision={decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
