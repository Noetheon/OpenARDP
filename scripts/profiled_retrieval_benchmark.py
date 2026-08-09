"""Pure validation and evaluation contracts for the F035 retrieval benchmark."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

try:
    from scripts.provider_retrieval_benchmark import _metrics
except ModuleNotFoundError:
    from provider_retrieval_benchmark import _metrics

from openardp.domain.identity import canonical_json_bytes, canonical_sha256

VERSION = "0.1.0"
PROFILES = ("f029_baseline", "f035_candidate")
SUITES = ("f025_development", "f034_holdout")
RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "phases.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
COMPILER_PHASES = (
    "snapshot_ns",
    "discovery_ns",
    "classification_ns",
    "materialization_ns",
    "budgeting_ns",
    "finalization_ns",
)
SOURCE_PHASES = (
    "enumeration_ns",
    "provider_ns",
    "admission_ns",
    "reconciliation_ns",
)
PROVIDER_PHASES = ("passage_encode_ns", "query_encode_ns", "similarity_ns")


class ProfiledRetrievalError(ValueError):
    """Stable body-free F035 benchmark failure category."""


def load_json(path: Path, *, maximum_bytes: int = 8_388_608) -> dict[str, Any]:
    """Read a bounded JSON object while rejecting duplicate members."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ProfiledRetrievalError("json_file")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ProfiledRetrievalError("json_duplicate_key")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ProfiledRetrievalError("json_non_finite")
            ),
        )
    except ProfiledRetrievalError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProfiledRetrievalError("json_invalid") from error
    if not isinstance(value, dict):
        raise ProfiledRetrievalError("json_shape")
    return value


def load_protocol(root: Path) -> dict[str, Any]:
    """Load and verify the immutable F035 protocol identity."""
    protocol = load_json(root / "benchmarks/profiled-retrieval/v0.1.0/protocol.json")
    declared = protocol.get("protocol_id")
    projected = dict(protocol)
    projected.pop("protocol_id", None)
    if declared != canonical_sha256(projected):
        raise ProfiledRetrievalError("protocol_identity")
    expected = {
        "benchmark_version": VERSION,
        "development_runs": 2,
        "holdout_runs": 2,
        "profile_order": [list(PROFILES), list(reversed(PROFILES))],
    }
    if any(protocol.get(key) != value for key, value in expected.items()):
        raise ProfiledRetrievalError("protocol_contract")
    return protocol


def _nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _metric_at_least(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) >= int(right["numerator"]) * int(
        left["denominator"]
    )


def _metric_strictly_greater(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return int(left["numerator"]) * int(right["denominator"]) > int(right["numerator"]) * int(
        left["denominator"]
    )


def _nearest_rank(values: list[int], percentile: int) -> int:
    if not values:
        raise ProfiledRetrievalError("timing_coverage")
    ordered = sorted(values)
    return ordered[max(0, math.ceil((percentile / 100) * len(ordered)) - 1)]


def _projection(rows: list[dict[str, Any]]) -> str:
    projected = [
        {
            key: value
            for key, value in row["observation"].items()
            if key not in {"wall_ns", "cpu_ns"}
        }
        for row in rows
    ]
    return canonical_sha256(projected)


def _validate_observation_coverage(
    rows: list[dict[str, Any]],
    *,
    f025_ids: tuple[str, ...],
    f034_ids: tuple[str, ...],
) -> None:
    expected = {
        ("f025_development", run, profile, ordinal, question_id)
        for run in range(2)
        for profile in PROFILES
        for ordinal, question_id in enumerate(f025_ids)
    }
    expected.update(
        {
            ("f034_holdout", run, "f035_candidate", ordinal, question_id)
            for run in range(2)
            for ordinal, question_id in enumerate(f034_ids)
        }
    )
    actual: list[tuple[str, int, str, int, str]] = []
    for row in rows:
        if set(row) != {"suite", "run", "profile", "ordinal", "observation"}:
            raise ProfiledRetrievalError("observation_shape")
        observation = row["observation"]
        if not isinstance(observation, dict):
            raise ProfiledRetrievalError("observation_shape")
        actual.append(
            (
                str(row["suite"]),
                int(row["run"]),
                str(row["profile"]),
                int(row["ordinal"]),
                str(observation.get("question_id")),
            )
        )
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ProfiledRetrievalError("observation_coverage")


def validate_phases(rows: list[dict[str, Any]], observation_rows: list[dict[str, Any]]) -> None:
    """Require complete non-overlapping phase trees reconciled to query wall time."""
    observation_keys = {
        (row["suite"], row["run"], row["profile"], row["ordinal"]) for row in observation_rows
    }
    phase_keys: set[tuple[object, ...]] = set()
    for row in rows:
        if set(row) != {
            "suite",
            "run",
            "profile",
            "ordinal",
            "wall_ns",
            "compiler",
            "source",
            "provider",
        }:
            raise ProfiledRetrievalError("phase_shape")
        key = (row["suite"], row["run"], row["profile"], row["ordinal"])
        if key in phase_keys:
            raise ProfiledRetrievalError("phase_duplicate")
        phase_keys.add(key)
        wall_ns = row["wall_ns"]
        compiler = row["compiler"]
        source = row["source"]
        provider = row["provider"]
        if not _nonnegative_int(wall_ns) or not all(
            isinstance(value, dict) for value in (compiler, source, provider)
        ):
            raise ProfiledRetrievalError("phase_value")
        if set(compiler) != {*COMPILER_PHASES, "compile_ns"}:
            raise ProfiledRetrievalError("compiler_phase_shape")
        if set(source) != set(SOURCE_PHASES) or set(provider) != set(PROVIDER_PHASES):
            raise ProfiledRetrievalError("nested_phase_shape")
        if not all(_nonnegative_int(value) for value in compiler.values()):
            raise ProfiledRetrievalError("compiler_phase_value")
        if not all(_nonnegative_int(value) for value in source.values()):
            raise ProfiledRetrievalError("source_phase_value")
        if not all(_nonnegative_int(value) for value in provider.values()):
            raise ProfiledRetrievalError("provider_phase_value")
        if sum(int(compiler[name]) for name in COMPILER_PHASES) > int(
            compiler["compile_ns"]
        ) or int(compiler["compile_ns"]) > int(wall_ns):
            raise ProfiledRetrievalError("compiler_phase_reconciliation")
        if sum(int(source[name]) for name in SOURCE_PHASES) > int(compiler["discovery_ns"]):
            raise ProfiledRetrievalError("source_phase_reconciliation")
        if sum(int(provider[name]) for name in PROVIDER_PHASES) > int(source["provider_ns"]):
            raise ProfiledRetrievalError("provider_phase_reconciliation")
    if phase_keys != observation_keys:
        raise ProfiledRetrievalError("phase_coverage")


def _suite_rows(
    rows: list[dict[str, Any]], suite: str, run: int, profile: str
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row["suite"] == suite and row["run"] == run and row["profile"] == profile
    ]
    return sorted(selected, key=lambda row: int(row["ordinal"]))


def summarize(
    observations: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    protocol: dict[str, Any],
    f025_questions: dict[str, dict[str, Any]],
    f034_questions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Recompute quality, deterministic projections and cold/warm timing gates."""
    f025_ids = tuple(f025_questions)
    f034_ids = tuple(f034_questions)
    _validate_observation_coverage(observations, f025_ids=f025_ids, f034_ids=f034_ids)
    validate_phases(phases, observations)
    quality: dict[str, Any] = {}
    deterministic: dict[str, bool] = {}
    for profile in PROFILES:
        first = _suite_rows(observations, SUITES[0], 0, profile)
        second = _suite_rows(observations, SUITES[0], 1, profile)
        quality[profile] = _metrics([row["observation"] for row in first], f025_questions)
        deterministic[profile] = _projection(first) == _projection(second)
    runtime: dict[str, Any] = {}
    for profile in PROFILES:
        selected = [
            row for row in phases if row["suite"] == SUITES[0] and row["profile"] == profile
        ]
        cold = [int(row["wall_ns"]) for row in selected if int(row["ordinal"]) == 0]
        warm = [int(row["wall_ns"]) for row in selected if int(row["ordinal"]) > 0]
        runtime[profile] = {
            "cold_ns": cold,
            "warm_count": len(warm),
            "warm_p50_ns": _nearest_rank(warm, 50),
            "warm_p95_ns": _nearest_rank(warm, 95),
            "wall_ns": sum(cold) + sum(warm),
        }
    holdout_runs = [_suite_rows(observations, SUITES[1], run, "f035_candidate") for run in range(2)]
    holdout_quality = _metrics([row["observation"] for row in holdout_runs[0]], f034_questions)
    holdout_deterministic = _projection(holdout_runs[0]) == _projection(holdout_runs[1])
    baseline = quality["f029_baseline"]
    candidate = quality["f035_candidate"]
    protected = tuple(protocol["gates"]["protected_quality"])
    development_checks = {
        **{
            f"{name}_non_regression": _metric_at_least(candidate[name], baseline[name])
            for name in protected
        },
        "absolute_quality_strict_improvement": any(
            _metric_strictly_greater(candidate[name], baseline[name])
            for name in protocol["gates"]["strict_improvement_any"]
        ),
        "warm_p50_improved_25_percent": runtime["f035_candidate"]["warm_p50_ns"] * 4
        <= runtime["f029_baseline"]["warm_p50_ns"] * 3,
        "warm_p95_non_regression": runtime["f035_candidate"]["warm_p95_ns"]
        <= runtime["f029_baseline"]["warm_p95_ns"],
    }
    holdout_baseline = protocol["holdout_baseline"]
    holdout_checks = {
        f"{name}_non_regression": _metric_at_least(holdout_quality[name], expected)
        for name, expected in holdout_baseline.items()
    }
    summary: dict[str, Any] = {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "development": {
            "quality": quality,
            "deterministic": deterministic,
            "runtime": runtime,
            "checks": development_checks,
        },
        "holdout": {
            "baseline": holdout_baseline,
            "candidate": holdout_quality,
            "deterministic": holdout_deterministic,
            "checks": holdout_checks,
        },
    }
    summary["summary_id"] = canonical_sha256(summary)
    return summary


def decide(summary: dict[str, Any], failures: tuple[str, ...] = ()) -> dict[str, Any]:
    """Keep benchmark validity, development acceptance and holdout outcome separate."""
    validity = {
        "no_runtime_failures": not failures,
        "development_deterministic": all(summary["development"]["deterministic"].values()),
        "holdout_deterministic": bool(summary["holdout"]["deterministic"]),
    }
    development = dict(summary["development"]["checks"])
    holdout = dict(summary["holdout"]["checks"])
    decision: dict[str, Any] = {
        "benchmark_version": VERSION,
        "summary_id": summary["summary_id"],
        "validity": "valid" if all(validity.values()) else "invalid",
        "development_candidate": "accepted" if all(development.values()) else "rejected",
        "holdout_generalization": "positive" if all(holdout.values()) else "negative",
        "validity_checks": validity,
        "development_checks": development,
        "holdout_checks": holdout,
        "failures": sorted(set(failures)),
    }
    decision["decision_id"] = canonical_sha256(decision)
    return decision


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render a concise deterministic projection of the validated evidence."""
    baseline = summary["development"]["quality"]["f029_baseline"]
    candidate = summary["development"]["quality"]["f035_candidate"]
    runtime = summary["development"]["runtime"]
    lines = [
        "# OpenARDP F035 Profiled Retrieval Optimization",
        "",
        f"- Validity: `{decision['validity']}`",
        f"- Development candidate: `{decision['development_candidate']}`",
        f"- Holdout generalization: `{decision['holdout_generalization']}`",
        "",
        "| Metric | F029 | F035 |",
        "|---|---:|---:|",
    ]
    for name in (
        "full_support",
        "atom_recall",
        "source_recall",
        "evidence_precision",
        "mrr",
        "citation_integrity",
        "unsupported_abstention",
    ):
        lines.append(f"| {name} | {baseline[name]['ratio']} | {candidate[name]['ratio']} |")
    lines.extend(
        [
            "",
            f"- Warm p50 ns: {runtime['f029_baseline']['warm_p50_ns']} -> "
            f"{runtime['f035_candidate']['warm_p50_ns']}",
            f"- Warm p95 ns: {runtime['f029_baseline']['warm_p95_ns']} -> "
            f"{runtime['f035_candidate']['warm_p95_ns']}",
            "- Phase evidence is body-free; selected bodies and embeddings are not persisted.",
            "- The holdout verdict is reported even when negative and was not used for tuning.",
            "",
        ]
    )
    return "\n".join(lines)


def canonical_file(path: Path, value: dict[str, Any]) -> None:
    """Write one canonical JSON object with a trailing newline."""
    path.write_bytes(canonical_json_bytes(value) + b"\n")


__all__ = [
    "COMPILER_PHASES",
    "PROFILES",
    "PROVIDER_PHASES",
    "RESULT_NAMES",
    "SOURCE_PHASES",
    "SUITES",
    "VERSION",
    "ProfiledRetrievalError",
    "canonical_file",
    "decide",
    "load_json",
    "load_protocol",
    "render_report",
    "summarize",
    "validate_phases",
]
