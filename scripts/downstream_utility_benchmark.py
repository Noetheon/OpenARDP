"""Provider-free downstream evidence-review evaluation for F036."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
RESULT_NAMES = (
    "observations.json",
    "summary.json",
    "decision.json",
    "report.md",
    "run-manifest.json",
)
METRIC_NAMES = (
    "task_completion",
    "answerable_completion",
    "atom_coverage",
    "source_coverage",
    "citation_integrity",
    "source_fitness",
    "safe_abstention",
)

_PROTOCOL = Path("benchmarks/downstream-utility/v0.1.0/protocol.json")
_F035_RESULT = Path("benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64")
_F034_RESULT = Path("benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64")


class DownstreamUtilityError(ValueError):
    """Stable body-free benchmark failure."""


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DownstreamUtilityError("duplicate_json_member")
        value[key] = item
    return value


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object while rejecting duplicate members."""
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_members
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DownstreamUtilityError("invalid_json") from exc
    if not isinstance(value, dict):
        raise DownstreamUtilityError("json_object_required")
    return value


def canonical_json_bytes(value: object) -> bytes:
    """Serialize one I-JSON-compatible value deterministically for evidence identities."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DownstreamUtilityError("canonical_json") from exc


def canonical_sha256(value: object) -> str:
    """Return a SHA-256 identity over canonical JSON bytes."""
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_fact(path: Path) -> dict[str, Any]:
    """Return the body-free digest and size of one immutable file."""
    payload = path.read_bytes()
    return {
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
    }


def load_protocol(root: Path) -> dict[str, Any]:
    """Load and verify the frozen F036 protocol and immutable input digests."""
    protocol = load_json(root / _PROTOCOL)
    declared = protocol.get("protocol_id")
    projected = dict(protocol)
    projected.pop("protocol_id", None)
    if declared != canonical_sha256(projected):
        raise DownstreamUtilityError("protocol_identity")
    expected = {
        "benchmark_version": VERSION,
        "budgets": [1, 3, 5, 10, 64],
        "primary_budget": 3,
        "network": "denied",
    }
    if any(protocol.get(key) != value for key, value in expected.items()):
        raise DownstreamUtilityError("protocol_contract")
    input_paths = {
        "f035": _F035_RESULT,
        "f034": _F034_RESULT,
    }
    for name, directory in input_paths.items():
        expected_input = protocol["inputs"][name]
        input_files = {
            "observations.json": "observations_sha256",
            "run-manifest.json": "manifest_sha256",
        }
        for filename, key in input_files.items():
            if file_fact(root / directory / filename)["sha256"] != expected_input[key]:
                raise DownstreamUtilityError("input_digest")
    return protocol


def _nonnegative_int(value: object, category: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DownstreamUtilityError(category)
    return value


def _selected_items(observation: dict[str, Any]) -> list[dict[str, Any]]:
    selected = observation.get("selected")
    if not isinstance(selected, list) or not all(isinstance(item, dict) for item in selected):
        raise DownstreamUtilityError("selected_shape")
    declared_count = observation.get("selected_count", len(selected))
    if _nonnegative_int(declared_count, "selected_count") != len(selected):
        raise DownstreamUtilityError("selected_count")
    return selected


def evaluate_observation(observation: dict[str, Any], *, budget: int) -> dict[str, Any]:
    """Evaluate one ordered retrieval observation under a fixed review-item budget."""
    if budget <= 0:
        raise DownstreamUtilityError("budget")
    question_id = observation.get("question_id")
    if not isinstance(question_id, str) or not question_id:
        raise DownstreamUtilityError("question_identity")
    required_atoms = _nonnegative_int(observation.get("required_atom_count"), "atom_count")
    required_sources = _nonnegative_int(observation.get("required_source_count"), "source_count")
    if (required_atoms == 0) != (required_sources == 0):
        raise DownstreamUtilityError("answerability_shape")
    abstained = observation.get("abstained")
    if not isinstance(abstained, bool):
        raise DownstreamUtilityError("abstention_shape")
    wall_ns = _nonnegative_int(observation.get("wall_ns"), "wall_time")
    selected = _selected_items(observation)
    prefix = selected[:budget]
    atoms: set[str] = set()
    sources: dict[str, tuple[int, int]] = {}
    relevant_count = 0
    citation_valid_count = 0
    items_to_completion: int | None = None
    for index, item in enumerate(prefix, start=1):
        if item.get("order") != index - 1:
            raise DownstreamUtilityError("selected_order")
        relevant = item.get("relevant")
        citation_valid = item.get("citation_valid")
        covered = item.get("covered_atom_ids")
        source_key = item.get("source_key")
        if (
            not isinstance(relevant, bool)
            or not isinstance(citation_valid, bool)
            or not isinstance(covered, list)
            or not all(isinstance(atom, str) and atom for atom in covered)
            or not isinstance(source_key, str)
            or not source_key
        ):
            raise DownstreamUtilityError("selected_item_shape")
        if not relevant:
            if covered:
                raise DownstreamUtilityError("irrelevant_atom_coverage")
            continue
        relevant_count += 1
        if not citation_valid:
            continue
        citation_valid_count += 1
        atoms.update(covered)
        score = _nonnegative_int(item.get("source_fitness_score", 0), "source_fitness")
        maximum = _nonnegative_int(item.get("source_fitness_max", 0), "source_fitness")
        if score > maximum:
            raise DownstreamUtilityError("source_fitness")
        current = sources.get(source_key)
        if (
            current is None
            or current[1] == 0
            or (maximum > 0 and score * current[1] > current[0] * maximum)
        ):
            sources[source_key] = (score, maximum)
        if (
            required_atoms > 0
            and len(atoms) >= required_atoms
            and len(sources) >= required_sources
            and items_to_completion is None
        ):
            items_to_completion = index
    trusted_atom_count = min(len(atoms), required_atoms)
    trusted_source_count = min(len(sources), required_sources)
    answerable = required_atoms > 0
    answerable_completion = answerable and items_to_completion is not None
    safe_unsupported = not answerable and abstained and not selected
    return {
        "question_id": question_id,
        "budget": budget,
        "answerable": answerable,
        "selected_count": len(selected),
        "inspected_count": len(prefix),
        "required_atom_count": required_atoms,
        "trusted_atom_count": trusted_atom_count,
        "required_source_count": required_sources,
        "trusted_source_count": trusted_source_count,
        "relevant_inspected_count": relevant_count,
        "citation_valid_relevant_count": citation_valid_count,
        "citation_integrity": citation_valid_count == relevant_count,
        "source_fitness_score": sum(score for score, _ in sources.values()),
        "source_fitness_max": sum(maximum for _, maximum in sources.values()),
        "items_to_completion": items_to_completion,
        "answerable_completion": answerable_completion,
        "safe_unsupported_completion": safe_unsupported,
        "task_completion": answerable_completion or safe_unsupported,
        "retrieval_wall_ns": wall_ns,
    }


def _source_row(
    suite: str,
    treatment: str,
    run: int | str,
    ordinal: int,
    observation: object,
) -> dict[str, Any]:
    if not isinstance(observation, dict):
        raise DownstreamUtilityError("observation_shape")
    return {
        "suite": suite,
        "treatment": treatment,
        "run": run,
        "ordinal": ordinal,
        "observation": observation,
    }


def load_source_rows(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """Load, bind and reconcile the exact F034/F035 body-free input populations."""
    f035 = load_json(root / _F035_RESULT / "observations.json")
    f034 = load_json(root / _F034_RESULT / "observations.json")
    if f035.get("protocol_id") != protocol["inputs"]["f035"]["protocol_id"]:
        raise DownstreamUtilityError("f035_protocol")
    if (
        f034.get("protocol_id") != protocol["inputs"]["f034"]["protocol_id"]
        or f034.get("corpus_id") != protocol["inputs"]["f034"]["corpus_id"]
        or f034.get("question_set_id") != protocol["inputs"]["f034"]["question_set_id"]
    ):
        raise DownstreamUtilityError("f034_protocol")
    raw_f035 = f035.get("rows")
    raw_f034 = f034.get("rows")
    if not isinstance(raw_f035, list) or not isinstance(raw_f034, list):
        raise DownstreamUtilityError("input_rows")
    rows: list[dict[str, Any]] = []
    for wrapper in raw_f035:
        if not isinstance(wrapper, dict) or set(wrapper) != {
            "suite",
            "run",
            "profile",
            "ordinal",
            "observation",
        }:
            raise DownstreamUtilityError("f035_row_shape")
        suite = wrapper["suite"]
        profile = wrapper["profile"]
        if suite == protocol["development"]["suite"]:
            if profile not in protocol["development"]["profiles"]:
                raise DownstreamUtilityError("development_profile")
        elif suite == protocol["holdout"]["suite"]:
            if profile != protocol["holdout"]["candidate_profile"]:
                raise DownstreamUtilityError("holdout_profile")
        else:
            raise DownstreamUtilityError("suite")
        rows.append(
            _source_row(
                str(suite),
                str(profile),
                _nonnegative_int(wrapper["run"], "run"),
                _nonnegative_int(wrapper["ordinal"], "ordinal"),
                wrapper["observation"],
            )
        )
    baseline_treatments = tuple(protocol["holdout"]["baseline_treatments"])
    ordinals: defaultdict[str, int] = defaultdict(int)
    for observation in raw_f034:
        if not isinstance(observation, dict):
            raise DownstreamUtilityError("f034_row_shape")
        treatment = observation.get("treatment")
        if treatment not in baseline_treatments:
            raise DownstreamUtilityError("holdout_treatment")
        ordinal = ordinals[str(treatment)]
        ordinals[str(treatment)] += 1
        rows.append(
            _source_row(
                protocol["holdout"]["suite"],
                str(treatment),
                protocol["holdout"]["baseline_runs"][0],
                ordinal,
                observation,
            )
        )
    _validate_source_coverage(rows, protocol)
    return rows


def _question_sequence(rows: Iterable[dict[str, Any]]) -> tuple[str, ...]:
    ordered = sorted(rows, key=lambda row: int(row["ordinal"]))
    return tuple(str(row["observation"].get("question_id")) for row in ordered)


def _validate_source_coverage(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> None:
    keys: set[tuple[object, ...]] = set()
    groups: defaultdict[tuple[str, str, int | str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (row["suite"], row["treatment"], row["run"], row["ordinal"])
        if key in keys:
            raise DownstreamUtilityError("source_row_duplicate")
        keys.add(key)
        groups[(row["suite"], row["treatment"], row["run"])].append(row)
    development_keys = {
        (protocol["development"]["suite"], profile, run)
        for profile in protocol["development"]["profiles"]
        for run in protocol["development"]["runs"]
    }
    holdout_keys = {
        (protocol["holdout"]["suite"], treatment, protocol["holdout"]["baseline_runs"][0])
        for treatment in protocol["holdout"]["baseline_treatments"]
    }
    holdout_keys.update(
        {
            (protocol["holdout"]["suite"], protocol["holdout"]["candidate_profile"], run)
            for run in protocol["holdout"]["candidate_runs"]
        }
    )
    if set(groups) != development_keys | holdout_keys:
        raise DownstreamUtilityError("source_group_coverage")
    development_sequences = {_question_sequence(groups[key]) for key in development_keys}
    holdout_sequences = {_question_sequence(groups[key]) for key in holdout_keys}
    if len(development_sequences) != 1 or len(holdout_sequences) != 1:
        raise DownstreamUtilityError("question_coverage")
    for group_rows in groups.values():
        ordinals = sorted(int(row["ordinal"]) for row in group_rows)
        question_count = len(set(_question_sequence(group_rows)))
        if ordinals != list(range(len(group_rows))) or question_count != len(group_rows):
            raise DownstreamUtilityError("ordinal_coverage")


def build_review_rows(
    source_rows: list[dict[str, Any]], protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    """Project every authoritative input row across every frozen review budget."""
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        for budget in protocol["budgets"]:
            rows.append(
                {
                    "suite": source["suite"],
                    "treatment": source["treatment"],
                    "run": source["run"],
                    "ordinal": source["ordinal"],
                    **evaluate_observation(source["observation"], budget=int(budget)),
                }
            )
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


def _nearest_rank(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered) / 100) - 1)]


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one exact suite/treatment/run/budget population."""
    if not rows:
        raise DownstreamUtilityError("aggregate_empty")
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
            "p50_items": _nearest_rank(efforts, 50),
            "p95_items": _nearest_rank(efforts, 95),
        },
    }


def _metric_at_least(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) >= int(right["numerator"]) * int(
        left["denominator"]
    )


def _group_review_rows(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str, int | str, int], list[dict[str, Any]]]:
    grouped: defaultdict[tuple[str, str, int | str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["suite"], row["treatment"], row["run"], row["budget"])].append(row)
    return dict(grouped)


def _timing_free_projection(rows: list[dict[str, Any]]) -> str:
    projected = [
        {key: value for key, value in row.items() if key not in {"run", "retrieval_wall_ns"}}
        for row in sorted(rows, key=lambda row: (int(row["ordinal"]), int(row["budget"])))
    ]
    return canonical_sha256(projected)


def _runtime(
    source_rows: list[dict[str, Any]], profile: str, warm_min_ordinal: int
) -> dict[str, Any]:
    values = [
        int(row["observation"]["wall_ns"])
        for row in source_rows
        if row["suite"] == "f025_development"
        and row["treatment"] == profile
        and int(row["ordinal"]) >= warm_min_ordinal
    ]
    return {
        "warm_count": len(values),
        "warm_p50_ns": _nearest_rank(values, 50),
        "warm_p95_ns": _nearest_rank(values, 95),
        "warm_total_ns": sum(values),
    }


def summarize(
    review_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Recompute complete development, holdout, effort and time-to-ready evidence."""
    grouped = _group_review_rows(review_rows)
    development: dict[str, Any] = {"by_run": {}, "deterministic": {}, "runtime": {}}
    development_suite = protocol["development"]["suite"]
    for profile in protocol["development"]["profiles"]:
        development["by_run"][profile] = {}
        projections: list[str] = []
        for run in protocol["development"]["runs"]:
            development["by_run"][profile][str(run)] = {}
            run_rows: list[dict[str, Any]] = []
            for budget in protocol["budgets"]:
                selected = grouped[(development_suite, profile, run, budget)]
                development["by_run"][profile][str(run)][str(budget)] = aggregate(selected)
                run_rows.extend(selected)
            projections.append(_timing_free_projection(run_rows))
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
    development_checks = {
        f"{metric}_non_regression": _metric_at_least(candidate[metric], baseline[metric])
        for metric in protocol["gates"]["primary_non_regression"]
    }
    baseline_runtime = development["runtime"]["f029_baseline"]
    candidate_runtime = development["runtime"]["f035_candidate"]
    fraction = protocol["gates"]["warm_p50_max_baseline_fraction"]
    development_checks.update(
        {
            "profiles_deterministic": all(development["deterministic"].values()),
            "warm_p50_improved_25_percent": int(candidate_runtime["warm_p50_ns"]) * int(fraction[1])
            <= int(baseline_runtime["warm_p50_ns"]) * int(fraction[0]),
            "warm_p95_non_regression": int(candidate_runtime["warm_p95_ns"])
            <= int(baseline_runtime["warm_p95_ns"]),
        }
    )
    development["checks"] = development_checks

    holdout_suite = protocol["holdout"]["suite"]
    holdout: dict[str, Any] = {
        "comparison": protocol["holdout"]["comparison"],
        "by_run": {},
    }
    holdout_groups = [
        *(
            (treatment, protocol["holdout"]["baseline_runs"][0])
            for treatment in protocol["holdout"]["baseline_treatments"]
        ),
        *(
            (protocol["holdout"]["candidate_profile"], run)
            for run in protocol["holdout"]["candidate_runs"]
        ),
    ]
    for treatment, run in holdout_groups:
        holdout["by_run"].setdefault(treatment, {})[str(run)] = {
            str(budget): aggregate(grouped[(holdout_suite, treatment, run, budget)])
            for budget in protocol["budgets"]
        }
    candidate_profile = protocol["holdout"]["candidate_profile"]
    candidate_projections = []
    for run in protocol["holdout"]["candidate_runs"]:
        run_rows = [
            row
            for row in review_rows
            if row["suite"] == holdout_suite
            and row["treatment"] == candidate_profile
            and row["run"] == run
        ]
        candidate_projections.append(_timing_free_projection(run_rows))
    holdout["candidate_deterministic"] = len(set(candidate_projections)) == 1
    f029 = holdout["by_run"]["f029_semantic_direct"]["f034_reference"]
    f035 = holdout["by_run"][candidate_profile]["0"]
    holdout_checks: dict[str, bool] = {
        "candidate_deterministic": holdout["candidate_deterministic"]
    }
    for budget in protocol["budgets"]:
        for metric in protocol["gates"]["primary_non_regression"]:
            holdout_checks[f"budget_{budget}_{metric}_non_regression"] = _metric_at_least(
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
        "review_row_count": len(review_rows),
        "development": development,
        "holdout": holdout,
    }
    summary["summary_id"] = canonical_sha256(summary)
    return summary


def decide(summary: dict[str, Any], failures: tuple[str, ...] = ()) -> dict[str, Any]:
    """Keep evidence validity, development acceptance and holdout outcome separate."""
    validity_checks = {
        "no_failures": not failures,
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
        "failures": sorted(set(failures)),
    }
    decision["decision_id"] = canonical_sha256(decision)
    return decision


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render the bounded downstream result without overstating the utility proxy."""
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
    for metric in METRIC_NAMES:
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


__all__ = [
    "METRIC_NAMES",
    "RESULT_NAMES",
    "VERSION",
    "DownstreamUtilityError",
    "aggregate",
    "build_review_rows",
    "canonical_json_bytes",
    "canonical_sha256",
    "decide",
    "evaluate_observation",
    "file_fact",
    "load_json",
    "load_protocol",
    "load_source_rows",
    "render_report",
    "summarize",
]
