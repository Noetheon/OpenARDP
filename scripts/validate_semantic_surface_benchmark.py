"""Independently validate one body-free F030 operational result using only stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
READY = "SEMANTIC_SURFACE_READY"
NOT_READY = "SEMANTIC_SURFACE_NOT_READY"
FILES = ("decision.json", "observations.json", "report.md", "run-manifest.json", "summary.json")
_JSON_FILES = ("decision.json", "observations.json", "summary.json")
_FORBIDDEN_KEYS = {
    "body",
    "document_text",
    "evidence_text",
    "hostname",
    "path",
    "query",
    "task",
    "traceback",
    "username",
    "vector",
    "vectors",
    "embedding",
    "embeddings",
}
_ABSOLUTE_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\)")


class ValidationError(ValueError):
    """Stable result rejection without disclosing result contents."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _identity(value: dict[str, Any], field: str) -> str:
    declared = value.get(field)
    payload = dict(value)
    payload.pop(field, None)
    expected = _digest(payload)
    if declared != expected:
        raise ValidationError(f"{field}_mismatch")
    return expected


def _load(path: Path, *, canonical: bool = True, maximum: int = 2_097_152) -> dict[str, Any]:
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
    if not isinstance(value, dict):
        raise ValidationError("json_shape")
    if canonical and path.read_bytes() != _canonical(value) + b"\n":
        raise ValidationError("json_not_canonical")
    return value


def _privacy(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in _FORBIDDEN_KEYS:
                raise ValidationError("privacy_forbidden_key")
            _privacy(item)
    elif isinstance(value, list):
        for item in value:
            _privacy(item)
    elif isinstance(value, str) and _ABSOLUTE_PATH.search(value):
        raise ValidationError("privacy_absolute_path")


def load_protocol(repository_root: Path) -> dict[str, Any]:
    """Load and verify the committed frozen F030 protocol."""
    path = repository_root / "benchmarks/semantic-surface/v0.1.0/protocol.json"
    protocol = _load(path, canonical=False, maximum=65_536)
    if protocol.get("benchmark_version") != VERSION or protocol.get("binding_runs") != 2:
        raise ValidationError("protocol_shape")
    _identity(protocol, "protocol_id")
    return protocol


def _metrics(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != {
        "cache_hits",
        "passages_scored",
        "peak_worker_rss_bytes",
        "requests",
    }:
        raise ValidationError("provider_metrics_shape")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value.values()
    ):
        raise ValidationError("provider_metrics_value")
    return value


def _validate_observations(
    observations: dict[str, Any], protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    if set(observations) != {
        "benchmark_version",
        "corpus_id",
        "observations_id",
        "protocol_id",
        "provider_recipe_id",
        "question_set_id",
        "runs",
    }:
        raise ValidationError("observations_shape")
    _identity(observations, "observations_id")
    if any(
        observations[key] != protocol[key]
        for key in ("benchmark_version", "corpus_id", "protocol_id", "question_set_id")
    ):
        raise ValidationError("observations_identity")
    runs = observations["runs"]
    if not isinstance(runs, list) or len(runs) != protocol["binding_runs"]:
        raise ValidationError("run_count")
    keys = {
        "bundle_verify_ns",
        "cold_metrics",
        "cold_projection_id",
        "cold_wall_ns",
        "observation_id",
        "run_index",
        "warm_metrics",
        "warm_projection_id",
        "warm_wall_ns",
    }
    for index, run in enumerate(runs, start=1):
        if not isinstance(run, dict) or set(run) != keys or run["run_index"] != index:
            raise ValidationError("run_shape")
        _identity(run, "observation_id")
        for field in ("bundle_verify_ns", "cold_wall_ns", "warm_wall_ns"):
            if isinstance(run[field], bool) or not isinstance(run[field], int) or run[field] <= 0:
                raise ValidationError("timing_value")
        for field in ("cold_projection_id", "warm_projection_id"):
            if (
                not isinstance(run[field], str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", run[field]) is None
            ):
                raise ValidationError("projection_identity")
        _metrics(run["cold_metrics"])
        _metrics(run["warm_metrics"])
    return runs


def _derived_summary(
    observations: dict[str, Any], runs: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, Any]:
    cold_wall = sum(run["cold_wall_ns"] for run in runs)
    warm_wall = sum(run["warm_wall_ns"] for run in runs)
    warm_passages = sum(run["warm_metrics"]["passages_scored"] for run in runs)
    warm_hits = sum(run["warm_metrics"]["cache_hits"] for run in runs)
    reuse = warm_hits * 1_000_000 // warm_passages if warm_passages else 0
    peak = max(
        metric["peak_worker_rss_bytes"]
        for run in runs
        for metric in (run["cold_metrics"], run["warm_metrics"])
    )
    within = all(run["cold_projection_id"] == run["warm_projection_id"] for run in runs)
    projection_ids = {
        run[field] for run in runs for field in ("cold_projection_id", "warm_projection_id")
    }
    return {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "corpus_id": protocol["corpus_id"],
        "question_set_id": protocol["question_set_id"],
        "provider_recipe_id": observations["provider_recipe_id"],
        "binding_runs": len(runs),
        "bundle_verification_total_ns": sum(run["bundle_verify_ns"] for run in runs),
        "cold_wall_total_ns": cold_wall,
        "warm_wall_total_ns": warm_wall,
        "warm_to_cold_millionths": warm_wall * 1_000_000 // cold_wall,
        "warm_cache_hits": warm_hits,
        "warm_passages_scored": warm_passages,
        "warm_cache_reuse_millionths": reuse,
        "peak_worker_rss_bytes": peak,
        "within_run_projection_identity": within,
        "across_run_projection_identity": len(projection_ids) == 1,
        "offline": True,
    }


def _failures(summary: dict[str, Any], protocol: dict[str, Any]) -> list[str]:
    gates = protocol["gates"]
    failures: list[str] = []
    if summary["warm_cache_reuse_millionths"] < gates["cache_reuse_minimum_millionths"]:
        failures.append("warm_cache_reuse_below_floor")
    if summary["peak_worker_rss_bytes"] > gates["peak_worker_rss_max_bytes"]:
        failures.append("peak_worker_rss_exceeded")
    if (
        gates["warm_not_slower_than_cold"]
        and summary["warm_wall_total_ns"] > summary["cold_wall_total_ns"]
    ):
        failures.append("warm_slower_than_cold")
    if gates["within_run_projection_identity"] and not summary["within_run_projection_identity"]:
        failures.append("within_run_projection_mismatch")
    if gates["across_run_projection_identity"] and not summary["across_run_projection_identity"]:
        failures.append("across_run_projection_mismatch")
    if gates["offline"] and not summary["offline"]:
        failures.append("offline_boundary_failed")
    return failures


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render the exact small human projection validated byte-for-byte."""
    return (
        "# Semantic retrieval product-surface benchmark\n\n"
        f"Decision: `{decision['decision']}`\n\n"
        f"- Cold wall total: {summary['cold_wall_total_ns']} ns\n"
        f"- Warm wall total: {summary['warm_wall_total_ns']} ns\n"
        f"- Warm/cold: {summary['warm_to_cold_millionths']} millionths\n"
        f"- Warm cache reuse: {summary['warm_cache_reuse_millionths']} millionths\n"
        f"- Peak worker RSS: {summary['peak_worker_rss_bytes']} bytes\n"
        "- Verified semantic bundle: 492794646 bytes\n"
        "- Reference platform: macOS arm64; Linux and Windows timing is unmeasured\n"
        f"- Failures: {', '.join(decision['failures']) if decision['failures'] else 'none'}\n\n"
        "This result covers one pinned offline provider and one small redistributable corpus. "
        "It does not validate answer generation, broad-domain quality or production SLOs.\n"
    )


def validate(repository_root: Path, result: Path) -> dict[str, Any]:
    """Validate one complete result directory and return the decision."""
    if (
        result.is_symlink()
        or not result.is_dir()
        or set(item.name for item in result.iterdir()) != set(FILES)
    ):
        raise ValidationError("result_inventory")
    protocol = load_protocol(repository_root)
    values = {name: _load(result / name) for name in _JSON_FILES}
    observations = values["observations.json"]
    runs = _validate_observations(observations, protocol)
    expected_summary = _derived_summary(observations, runs, protocol)
    summary = values["summary.json"]
    summary_id = summary.get("summary_id")
    if {key: value for key, value in summary.items() if key != "summary_id"} != expected_summary:
        raise ValidationError("summary_derived")
    _identity(summary, "summary_id")
    failures = _failures(expected_summary, protocol)
    expected_decision = {
        "benchmark_version": VERSION,
        "protocol_id": protocol["protocol_id"],
        "summary_id": summary_id,
        "decision": READY if not failures else NOT_READY,
        "failures": failures,
    }
    decision = values["decision.json"]
    if {key: value for key, value in decision.items() if key != "decision_id"} != expected_decision:
        raise ValidationError("decision_derived")
    _identity(decision, "decision_id")
    report = (result / "report.md").read_text(encoding="utf-8")
    if report != render_report(summary, decision):
        raise ValidationError("report_drift")
    for value in (*values.values(), report):
        _privacy(value)
    manifest = _load(result / "run-manifest.json")
    if set(manifest) != {"files", "result_id"}:
        raise ValidationError("manifest_shape")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != set(FILES) - {"run-manifest.json"}:
        raise ValidationError("manifest_files")
    for name, facts in files.items():
        payload = (result / name).read_bytes()
        if facts != {
            "byte_length": len(payload),
            "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        }:
            raise ValidationError("manifest_digest")
    _identity(manifest, "result_id")
    if sum((result / name).stat().st_size for name in FILES) > protocol["result_max_bytes"]:
        raise ValidationError("result_size")
    return decision


def main() -> int:
    """Parse one result path and emit a stable validation outcome."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.repository_root.resolve(), arguments.result.resolve())
    except (OSError, ValidationError, ValueError):
        print("semantic_surface_result_invalid")
        return 1
    print(f"semantic_surface_result_valid decision={decision['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
