"""Independently validate F036 evidence without importing producer or evaluator code."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
RESULT_NAMES = {
    "observations.json",
    "summary.json",
    "decision.json",
    "report.md",
    "run-manifest.json",
}
METRICS = (
    "task_completion",
    "answerable_completion",
    "atom_coverage",
    "source_coverage",
    "citation_integrity",
    "source_fitness",
    "safe_abstention",
)
FORBIDDEN_KEYS = frozenset(
    {"body", "content", "query", "question", "reference_answer", "text", "hostname", "username"}
)
ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class DownstreamUtilityValidationError(ValueError):
    """Stable independent-validation failure."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DownstreamUtilityValidationError("duplicate_json_member")
        value[key] = item
    return value


def _load(path: Path, *, canonical: bool = False) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw, object_pairs_hook=_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DownstreamUtilityValidationError("invalid_json") from exc
    if not isinstance(value, dict):
        raise DownstreamUtilityValidationError("json_object_required")
    if canonical and raw != _canonical(value) + b"\n":
        raise DownstreamUtilityValidationError("json_not_canonical")
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DownstreamUtilityValidationError("canonical_json") from exc


def _identity(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _fact(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"sha256": "sha256:" + hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}


def _reject_disclosure(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.casefold() in FORBIDDEN_KEYS:
                raise DownstreamUtilityValidationError("disclosure")
            _reject_disclosure(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_disclosure(nested)
    elif isinstance(value, str) and (value.startswith("/") or ABSOLUTE_WINDOWS_PATH.match(value)):
        raise DownstreamUtilityValidationError("absolute_path")


def _nonnegative(value: object, category: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DownstreamUtilityValidationError(category)
    return value


def _protocol(root: Path) -> dict[str, Any]:
    protocol = _load(root / "benchmarks/downstream-utility/v0.1.0/protocol.json")
    projected = dict(protocol)
    declared = projected.pop("protocol_id", None)
    if declared != _identity(projected):
        raise DownstreamUtilityValidationError("protocol_identity")
    if (
        protocol.get("benchmark_version") != VERSION
        or protocol.get("budgets") != [1, 3, 5, 10, 64]
        or protocol.get("primary_budget") != 3
        or protocol.get("network") != "denied"
    ):
        raise DownstreamUtilityValidationError("protocol_contract")
    paths = {
        "f034": root / "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64",
        "f035": root / "benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64",
    }
    for name, directory in paths.items():
        expected = protocol["inputs"][name]
        if (
            _fact(directory / "observations.json")["sha256"] != expected["observations_sha256"]
            or _fact(directory / "run-manifest.json")["sha256"] != expected["manifest_sha256"]
        ):
            raise DownstreamUtilityValidationError("input_digest")
    return protocol


def _evaluate(observation: dict[str, Any], budget: int) -> dict[str, Any]:
    question_id = observation.get("question_id")
    required_atoms = _nonnegative(observation.get("required_atom_count"), "atom_count")
    required_sources = _nonnegative(observation.get("required_source_count"), "source_count")
    abstained = observation.get("abstained")
    selected = observation.get("selected")
    wall_ns = _nonnegative(observation.get("wall_ns"), "wall_time")
    if (
        not isinstance(question_id, str)
        or not question_id
        or (required_atoms == 0) != (required_sources == 0)
        or not isinstance(abstained, bool)
        or not isinstance(selected, list)
        or not all(isinstance(item, dict) for item in selected)
        or observation.get("selected_count", len(selected)) != len(selected)
    ):
        raise DownstreamUtilityValidationError("observation_shape")
    atoms: set[str] = set()
    sources: dict[str, tuple[int, int]] = {}
    relevant_count = 0
    citation_count = 0
    completion_rank: int | None = None
    for index, item in enumerate(selected[:budget], start=1):
        relevant = item.get("relevant")
        valid = item.get("citation_valid")
        covered = item.get("covered_atom_ids")
        source = item.get("source_key")
        if (
            item.get("order") != index - 1
            or not isinstance(relevant, bool)
            or not isinstance(valid, bool)
            or not isinstance(covered, list)
            or not all(isinstance(atom, str) and atom for atom in covered)
            or not isinstance(source, str)
            or not source
        ):
            raise DownstreamUtilityValidationError("selected_shape")
        if not relevant:
            if covered:
                raise DownstreamUtilityValidationError("irrelevant_coverage")
            continue
        relevant_count += 1
        if not valid:
            continue
        citation_count += 1
        atoms.update(covered)
        score = _nonnegative(item.get("source_fitness_score", 0), "fitness")
        maximum = _nonnegative(item.get("source_fitness_max", 0), "fitness")
        if score > maximum:
            raise DownstreamUtilityValidationError("fitness")
        current = sources.get(source)
        if (
            current is None
            or current[1] == 0
            or (maximum > 0 and score * current[1] > current[0] * maximum)
        ):
            sources[source] = (score, maximum)
        if (
            required_atoms > 0
            and len(atoms) >= required_atoms
            and len(sources) >= required_sources
            and completion_rank is None
        ):
            completion_rank = index
    answerable = required_atoms > 0
    answerable_completion = answerable and completion_rank is not None
    safe = not answerable and abstained and not selected
    return {
        "question_id": question_id,
        "budget": budget,
        "answerable": answerable,
        "selected_count": len(selected),
        "inspected_count": min(budget, len(selected)),
        "required_atom_count": required_atoms,
        "trusted_atom_count": min(len(atoms), required_atoms),
        "required_source_count": required_sources,
        "trusted_source_count": min(len(sources), required_sources),
        "relevant_inspected_count": relevant_count,
        "citation_valid_relevant_count": citation_count,
        "citation_integrity": citation_count == relevant_count,
        "source_fitness_score": sum(score for score, _ in sources.values()),
        "source_fitness_max": sum(maximum for _, maximum in sources.values()),
        "items_to_completion": completion_rank,
        "answerable_completion": answerable_completion,
        "safe_unsupported_completion": safe,
        "task_completion": answerable_completion or safe,
        "retrieval_wall_ns": wall_ns,
    }


def _source_rows(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    f035 = _load(
        root
        / "benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64/observations.json"
    )
    f034 = _load(
        root / "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64/observations.json"
    )
    if f035.get("protocol_id") != protocol["inputs"]["f035"]["protocol_id"] or (
        f034.get("protocol_id") != protocol["inputs"]["f034"]["protocol_id"]
        or f034.get("corpus_id") != protocol["inputs"]["f034"]["corpus_id"]
        or f034.get("question_set_id") != protocol["inputs"]["f034"]["question_set_id"]
    ):
        raise DownstreamUtilityValidationError("input_binding")
    raw_f035 = f035.get("rows")
    raw_f034 = f034.get("rows")
    if not isinstance(raw_f035, list) or not isinstance(raw_f034, list):
        raise DownstreamUtilityValidationError("input_rows")
    rows: list[dict[str, Any]] = []
    for wrapper in raw_f035:
        if not isinstance(wrapper, dict) or set(wrapper) != {
            "suite",
            "run",
            "profile",
            "ordinal",
            "observation",
        }:
            raise DownstreamUtilityValidationError("f035_shape")
        rows.append(
            {
                "suite": wrapper["suite"],
                "treatment": wrapper["profile"],
                "run": _nonnegative(wrapper["run"], "run"),
                "ordinal": _nonnegative(wrapper["ordinal"], "ordinal"),
                "observation": wrapper["observation"],
            }
        )
    ordinals: defaultdict[str, int] = defaultdict(int)
    for observation in raw_f034:
        if not isinstance(observation, dict):
            raise DownstreamUtilityValidationError("f034_shape")
        treatment = observation.get("treatment")
        if treatment not in protocol["holdout"]["baseline_treatments"]:
            raise DownstreamUtilityValidationError("f034_treatment")
        rows.append(
            {
                "suite": protocol["holdout"]["suite"],
                "treatment": treatment,
                "run": protocol["holdout"]["baseline_runs"][0],
                "ordinal": ordinals[str(treatment)],
                "observation": observation,
            }
        )
        ordinals[str(treatment)] += 1
    _coverage(rows, protocol)
    return rows


def _coverage(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> None:
    groups: defaultdict[tuple[str, str, int | str], list[dict[str, Any]]] = defaultdict(list)
    keys: set[tuple[object, ...]] = set()
    for row in rows:
        key = (row["suite"], row["treatment"], row["run"], row["ordinal"])
        if key in keys:
            raise DownstreamUtilityValidationError("duplicate_source_row")
        keys.add(key)
        groups[(row["suite"], row["treatment"], row["run"])].append(row)
    expected = {
        (protocol["development"]["suite"], profile, run)
        for profile in protocol["development"]["profiles"]
        for run in protocol["development"]["runs"]
    }
    expected.update(
        {
            (
                protocol["holdout"]["suite"],
                treatment,
                protocol["holdout"]["baseline_runs"][0],
            )
            for treatment in protocol["holdout"]["baseline_treatments"]
        }
    )
    expected.update(
        {
            (protocol["holdout"]["suite"], protocol["holdout"]["candidate_profile"], run)
            for run in protocol["holdout"]["candidate_runs"]
        }
    )
    if set(groups) != expected:
        raise DownstreamUtilityValidationError("group_coverage")
    sequences: defaultdict[str, set[tuple[str, ...]]] = defaultdict(set)
    for (suite, _, _), grouped_rows in groups.items():
        ordered = sorted(grouped_rows, key=lambda row: int(row["ordinal"]))
        if [row["ordinal"] for row in ordered] != list(range(len(ordered))):
            raise DownstreamUtilityValidationError("ordinal_coverage")
        questions = tuple(str(row["observation"].get("question_id")) for row in ordered)
        if len(set(questions)) != len(questions):
            raise DownstreamUtilityValidationError("question_duplicate")
        sequences[suite].add(questions)
    if any(len(values) != 1 for values in sequences.values()):
        raise DownstreamUtilityValidationError("question_coverage")


def _review_rows(
    source_rows: list[dict[str, Any]], protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [
        {
            "suite": source["suite"],
            "treatment": source["treatment"],
            "run": source["run"],
            "ordinal": source["ordinal"],
            **_evaluate(source["observation"], budget),
        }
        for source in source_rows
        for budget in protocol["budgets"]
    ]
    return sorted(
        rows,
        key=lambda row: (
            str(row["suite"]),
            str(row["treatment"]),
            str(row["run"]),
            int(row["ordinal"]),
            int(row["budget"]),
        ),
    )


def _fraction(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator == 0:
        numerator, denominator = 1, 1
    return {
        "numerator": numerator,
        "denominator": denominator,
        "ratio": f"{numerator / denominator:.6f}",
    }


def _rank(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered) / 100) - 1)]


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise DownstreamUtilityValidationError("empty_aggregate")
    answerable = [row for row in rows if row["answerable"]]
    unsupported = [row for row in rows if not row["answerable"]]
    efforts = [
        int(row["items_to_completion"])
        for row in answerable
        if row["answerable_completion"] and row["items_to_completion"] is not None
    ]
    return {
        "question_count": len(rows),
        "answerable_count": len(answerable),
        "unsupported_count": len(unsupported),
        "task_completion": _fraction(sum(bool(row["task_completion"]) for row in rows), len(rows)),
        "answerable_completion": _fraction(
            sum(bool(row["answerable_completion"]) for row in answerable), len(answerable)
        ),
        "safe_abstention": _fraction(
            sum(bool(row["safe_unsupported_completion"]) for row in unsupported),
            len(unsupported),
        ),
        "atom_coverage": _fraction(
            sum(int(row["trusted_atom_count"]) for row in answerable),
            sum(int(row["required_atom_count"]) for row in answerable),
        ),
        "source_coverage": _fraction(
            sum(int(row["trusted_source_count"]) for row in answerable),
            sum(int(row["required_source_count"]) for row in answerable),
        ),
        "citation_integrity": _fraction(
            sum(int(row["citation_valid_relevant_count"]) for row in rows),
            sum(int(row["relevant_inspected_count"]) for row in rows),
        ),
        "source_fitness": _fraction(
            sum(int(row["source_fitness_score"]) for row in rows),
            sum(int(row["source_fitness_max"]) for row in rows),
        ),
        "items_inspected": sum(int(row["inspected_count"]) for row in rows),
        "completed_answerable_effort": {
            "count": len(efforts),
            "p50_items": _rank(efforts, 50),
            "p95_items": _rank(efforts, 95),
        },
    }


def _projection(rows: list[dict[str, Any]]) -> str:
    projected = [
        {key: value for key, value in row.items() if key not in {"run", "retrieval_wall_ns"}}
        for row in sorted(rows, key=lambda row: (int(row["ordinal"]), int(row["budget"])))
    ]
    return _identity(projected)


def _at_least(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) >= int(right["numerator"]) * int(
        left["denominator"]
    )


def _runtime(source_rows: list[dict[str, Any]], treatment: str, minimum: int) -> dict[str, Any]:
    values = [
        int(row["observation"]["wall_ns"])
        for row in source_rows
        if row["suite"] == "f025_development"
        and row["treatment"] == treatment
        and int(row["ordinal"]) >= minimum
    ]
    return {
        "warm_count": len(values),
        "warm_p50_ns": _rank(values, 50),
        "warm_p95_ns": _rank(values, 95),
        "warm_total_ns": sum(values),
    }


def _summary(
    rows: list[dict[str, Any]], source_rows: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, Any]:
    groups: defaultdict[tuple[str, str, int | str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["suite"], row["treatment"], row["run"], row["budget"])].append(row)
    development: dict[str, Any] = {"by_run": {}, "deterministic": {}, "runtime": {}}
    suite = protocol["development"]["suite"]
    for profile in protocol["development"]["profiles"]:
        development["by_run"][profile] = {}
        projections: list[str] = []
        for run in protocol["development"]["runs"]:
            development["by_run"][profile][str(run)] = {
                str(budget): _aggregate(groups[(suite, profile, run, budget)])
                for budget in protocol["budgets"]
            }
            run_rows = [
                row
                for row in rows
                if row["suite"] == suite and row["treatment"] == profile and row["run"] == run
            ]
            projections.append(_projection(run_rows))
        development["deterministic"][profile] = len(set(projections)) == 1
        development["runtime"][profile] = _runtime(
            source_rows, profile, int(protocol["development"]["warm_min_ordinal"])
        )
    primary = str(protocol["primary_budget"])
    development["primary_budget"] = protocol["primary_budget"]
    development["primary"] = {
        profile: development["by_run"][profile]["0"][primary]
        for profile in protocol["development"]["profiles"]
    }
    baseline = development["primary"]["f029_baseline"]
    candidate = development["primary"]["f035_candidate"]
    checks = {
        f"{metric}_non_regression": _at_least(candidate[metric], baseline[metric])
        for metric in protocol["gates"]["primary_non_regression"]
    }
    baseline_time = development["runtime"]["f029_baseline"]
    candidate_time = development["runtime"]["f035_candidate"]
    fraction = protocol["gates"]["warm_p50_max_baseline_fraction"]
    checks.update(
        {
            "profiles_deterministic": all(development["deterministic"].values()),
            "warm_p50_improved_25_percent": int(candidate_time["warm_p50_ns"]) * int(fraction[1])
            <= int(baseline_time["warm_p50_ns"]) * int(fraction[0]),
            "warm_p95_non_regression": int(candidate_time["warm_p95_ns"])
            <= int(baseline_time["warm_p95_ns"]),
        }
    )
    development["checks"] = checks

    suite = protocol["holdout"]["suite"]
    holdout: dict[str, Any] = {"comparison": protocol["holdout"]["comparison"], "by_run": {}}
    treatment_runs = [
        *(
            (treatment, protocol["holdout"]["baseline_runs"][0])
            for treatment in protocol["holdout"]["baseline_treatments"]
        ),
        *(
            (protocol["holdout"]["candidate_profile"], run)
            for run in protocol["holdout"]["candidate_runs"]
        ),
    ]
    for treatment, run in treatment_runs:
        holdout["by_run"].setdefault(treatment, {})[str(run)] = {
            str(budget): _aggregate(groups[(suite, treatment, run, budget)])
            for budget in protocol["budgets"]
        }
    candidate_profile = protocol["holdout"]["candidate_profile"]
    projections = [
        _projection(
            [
                row
                for row in rows
                if row["suite"] == suite
                and row["treatment"] == candidate_profile
                and row["run"] == run
            ]
        )
        for run in protocol["holdout"]["candidate_runs"]
    ]
    holdout["candidate_deterministic"] = len(set(projections)) == 1
    f029 = holdout["by_run"]["f029_semantic_direct"]["f034_reference"]
    f035 = holdout["by_run"][candidate_profile]["0"]
    holdout_checks = {"candidate_deterministic": holdout["candidate_deterministic"]}
    for budget in protocol["budgets"]:
        for metric in protocol["gates"]["primary_non_regression"]:
            holdout_checks[f"budget_{budget}_{metric}_non_regression"] = _at_least(
                f035[str(budget)][metric], f029[str(budget)][metric]
            )
    holdout["primary_budget"] = protocol["primary_budget"]
    holdout["primary"] = {
        "f027_lexical_direct": holdout["by_run"]["f027_lexical_direct"]["f034_reference"][primary],
        "f029_semantic_direct": f029[primary],
        candidate_profile: f035[primary],
    }
    holdout["checks"] = holdout_checks
    summary: dict[str, Any] = {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "review_row_count": len(rows),
        "development": development,
        "holdout": holdout,
    }
    summary["summary_id"] = _identity(summary)
    return summary


def _decision(summary: dict[str, Any]) -> dict[str, Any]:
    validity_checks = {
        "no_failures": True,
        "development_deterministic": all(summary["development"]["deterministic"].values()),
        "holdout_candidate_deterministic": summary["holdout"]["candidate_deterministic"],
    }
    development_checks = dict(summary["development"]["checks"])
    holdout_checks = dict(summary["holdout"]["checks"])
    decision: dict[str, Any] = {
        "benchmark_version": VERSION,
        "summary_id": summary["summary_id"],
        "validity": "valid" if all(validity_checks.values()) else "invalid",
        "development_candidate": "accepted" if all(development_checks.values()) else "rejected",
        "holdout_generalization": "positive" if all(holdout_checks.values()) else "negative",
        "validity_checks": validity_checks,
        "development_checks": development_checks,
        "holdout_checks": holdout_checks,
        "failures": [],
    }
    decision["decision_id"] = _identity(decision)
    return decision


def _report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    development = summary["development"]
    holdout = summary["holdout"]
    lines = [
        "# OpenARDP F036 Downstream Evidence Utility",
        "",
        f"- Validity: `{decision['validity']}`",
        f"- F025 candidate: `{decision['development_candidate']}`",
        f"- F034 generalization: `{decision['holdout_generalization']}`",
        "- Primary review budget: 3 evidence items; complete curve: 1, 3, 5, 10, 64.",
        "",
        "## F025 primary utility",
        "",
        "| Metric | F029 | F035 |",
        "|---|---:|---:|",
    ]
    for metric in METRICS:
        lines.append(
            f"| {metric} | {development['primary']['f029_baseline'][metric]['ratio']} | "
            f"{development['primary']['f035_candidate'][metric]['ratio']} |"
        )
    lines.extend(
        [
            "",
            f"- Warm time-to-ready p50 ns: "
            f"{development['runtime']['f029_baseline']['warm_p50_ns']} -> "
            f"{development['runtime']['f035_candidate']['warm_p50_ns']}",
            f"- Warm time-to-ready p95 ns: "
            f"{development['runtime']['f029_baseline']['warm_p95_ns']} -> "
            f"{development['runtime']['f035_candidate']['warm_p95_ns']}",
            "",
            "## F034 primary utility",
            "",
            "| Treatment | Task complete | Atoms | Sources | Source fitness | Citations |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for treatment, metrics in holdout["primary"].items():
        lines.append(
            f"| {treatment} | {metrics['task_completion']['ratio']} | "
            f"{metrics['atom_coverage']['ratio']} | {metrics['source_coverage']['ratio']} | "
            f"{metrics['source_fitness']['ratio']} | {metrics['citation_integrity']['ratio']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "- F034 comparison is unpaired and timing-free across two previously frozen "
            "benchmark packages.",
            "- Results contain no question text, reference answer, document body, embedding or "
            "local path.",
            "- Item counts are review-effort proxies, not measured human reading time.",
            "- Completion proves benchmark support is present in a bounded citation-valid packet; "
            "it does not prove human",
            "  comprehension, generated-answer correctness, domain readiness or universal "
            "retrieval quality.",
            "",
        ]
    )
    return "\n".join(lines)


def validate(root: Path, result: Path) -> dict[str, Any]:
    """Reconstruct every row, aggregate, verdict, identity and output digest."""
    root = root.resolve(strict=True)
    protocol = _protocol(root)
    if result.is_symlink() or not result.is_dir():
        raise DownstreamUtilityValidationError("result_directory")
    entries = tuple(result.iterdir())
    if {entry.name for entry in entries} != RESULT_NAMES or any(
        entry.is_symlink() or not entry.is_file() for entry in entries
    ):
        raise DownstreamUtilityValidationError("result_inventory")
    if sum(entry.stat().st_size for entry in entries) > int(protocol["result_max_bytes"]):
        raise DownstreamUtilityValidationError("result_size")
    observations = _load(result / "observations.json", canonical=True)
    summary = _load(result / "summary.json", canonical=True)
    decision = _load(result / "decision.json", canonical=True)
    manifest = _load(result / "run-manifest.json", canonical=True)
    for value in (observations, summary, decision, manifest):
        _reject_disclosure(value)
    source_rows = _source_rows(root, protocol)
    expected_rows = _review_rows(source_rows, protocol)
    if observations != {"protocol_id": protocol["protocol_id"], "rows": expected_rows}:
        raise DownstreamUtilityValidationError("observation_mismatch")
    expected_summary = _summary(expected_rows, source_rows, protocol)
    if summary != expected_summary:
        raise DownstreamUtilityValidationError("summary_mismatch")
    expected_decision = _decision(expected_summary)
    if decision != expected_decision:
        raise DownstreamUtilityValidationError("decision_mismatch")
    if (result / "report.md").read_text(encoding="utf-8") != _report(summary, decision):
        raise DownstreamUtilityValidationError("report_mismatch")
    expected_manifest_keys = {
        "benchmark_version",
        "protocol_id",
        "offline",
        "review_row_count",
        "holdout_evaluations",
        "comparison",
        "environment",
        "inputs",
        "files",
        "run_id",
    }
    if set(manifest) != expected_manifest_keys:
        raise DownstreamUtilityValidationError("manifest_shape")
    environment = manifest.get("environment")
    environment_valid = (
        isinstance(environment, dict)
        and set(environment) == {"python", "system", "machine"}
        and all(isinstance(value, str) and value for value in environment.values())
    )
    if not environment_valid:
        raise DownstreamUtilityValidationError("environment_shape")
    expected_inputs = {
        "f034_observations": _fact(
            root
            / "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64/observations.json"
        ),
        "f034_run_manifest": _fact(
            root
            / "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64/run-manifest.json"
        ),
        "f035_observations": _fact(
            root
            / "benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64/observations.json"
        ),
        "f035_run_manifest": _fact(
            root
            / "benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64/run-manifest.json"
        ),
    }
    expected_files = {
        name: _fact(result / name) for name in RESULT_NAMES if name != "run-manifest.json"
    }
    projected_manifest = dict(manifest)
    declared_run_id = projected_manifest.pop("run_id", None)
    if (
        manifest.get("benchmark_version") != VERSION
        or manifest.get("protocol_id") != protocol["protocol_id"]
        or manifest.get("offline") is not True
        or manifest.get("review_row_count") != len(expected_rows)
        or manifest.get("holdout_evaluations") != 1
        or manifest.get("comparison") != protocol["holdout"]["comparison"]
        or manifest.get("inputs") != expected_inputs
        or manifest.get("files") != expected_files
        or declared_run_id != _identity(projected_manifest)
    ):
        raise DownstreamUtilityValidationError("manifest_binding")
    return decision


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    return parser.parse_args()


def main() -> int:
    """Validate with one stable non-disclosing status line."""
    arguments = _arguments()
    try:
        decision = validate(Path.cwd(), arguments.result)
    except (DownstreamUtilityValidationError, KeyError, OSError, TypeError, ValueError):
        print("downstream_utility_validation_failed", file=sys.stderr)
        return 2
    print(
        f"downstream_utility_valid development={decision['development_candidate']} "
        f"holdout={decision['holdout_generalization']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
