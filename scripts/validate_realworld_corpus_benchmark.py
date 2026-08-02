"""Independent validator for the F024 structural baseline result."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.validate_realworld_corpus import ValidationFailure
    from scripts.validate_realworld_corpus import validate as validate_corpus
except ModuleNotFoundError:
    from validate_realworld_corpus import ValidationFailure
    from validate_realworld_corpus import validate as validate_corpus

RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
ROW_FIELDS = {
    "anchor_classes",
    "asset_key",
    "block_count",
    "block_set_id",
    "cpu_ns",
    "error_category",
    "format",
    "native_bytes",
    "native_id",
    "network_attempts",
    "outcome",
    "page_count",
    "peak_rss_bytes",
    "pointer_bounded_count",
    "pointer_resolution_complete",
    "recipe_id",
    "repetition",
    "retrieval_complete",
    "source_id",
    "table_count",
    "wall_ns",
}


class BenchmarkValidationFailure(ValueError):
    """One stable body-free result validation failure."""


def _load_json(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise BenchmarkValidationFailure("duplicate_json")
            result[key] = value
        return result

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                BenchmarkValidationFailure("json_value")
            ),
        )
    except BenchmarkValidationFailure:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BenchmarkValidationFailure("json_invalid") from error


def _safe(value: Any) -> None:
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise BenchmarkValidationFailure("json_value")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise BenchmarkValidationFailure("json_value")
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
    raise BenchmarkValidationFailure("json_value")


def _canonical(value: Any) -> bytes:
    _safe(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise BenchmarkValidationFailure("object")
    return value


def _array(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise BenchmarkValidationFailure("array")
    return value


def _integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BenchmarkValidationFailure("integer")
    return value


def _sha_id(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise BenchmarkValidationFailure("sha256")
    try:
        int(value[7:], 16)
    except ValueError as error:
        raise BenchmarkValidationFailure("sha256") from error
    return value


def _p95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _summarize(observations: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    rows = [_object(item) for item in _array(observations.get("rows"))]
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["asset_key"])].append(row)
    assets: list[dict[str, Any]] = []
    for key in sorted(grouped):
        selected = sorted(grouped[key], key=lambda item: int(item["repetition"]))
        identity_fields = ("source_id", "recipe_id", "native_id", "block_set_id")
        structural_fields = (
            "anchor_classes",
            "block_count",
            "page_count",
            "pointer_bounded_count",
            "table_count",
        )
        deterministic = all(
            len({str(item[field]) for item in selected}) == 1 for field in identity_fields
        ) and all(
            len(
                {
                    tuple(item[field]) if isinstance(item[field], list) else item[field]
                    for item in selected
                }
            )
            == 1
            for field in structural_fields
        )
        walls = [int(item["wall_ns"]) for item in selected]
        cpus = [int(item["cpu_ns"]) for item in selected]
        first = selected[0]
        assets.append(
            {
                "anchor_classes": sorted(
                    {str(anchor) for item in selected for anchor in item["anchor_classes"]}
                ),
                "asset_key": key,
                "block_count": int(first["block_count"]),
                "block_set_id": first["block_set_id"] if deterministic else None,
                "cpu_p50_ns": int(statistics.median(cpus)),
                "cpu_p95_ns": _p95(cpus),
                "deterministic": deterministic,
                "error_categories": sorted(
                    {
                        str(item["error_category"])
                        for item in selected
                        if item["error_category"] is not None
                    }
                ),
                "format": first["format"],
                "native_bytes": int(first["native_bytes"]),
                "native_id": first["native_id"] if deterministic else None,
                "network_attempts": sum(int(item["network_attempts"]) for item in selected),
                "outcomes": sorted({str(item["outcome"]) for item in selected}),
                "page_count": int(first["page_count"]),
                "peak_rss_bytes": max(int(item["peak_rss_bytes"]) for item in selected),
                "pointer_bounded_count": int(first["pointer_bounded_count"]),
                "pointer_resolution_complete": all(
                    bool(item["pointer_resolution_complete"]) for item in selected
                ),
                "recipe_id": first["recipe_id"] if deterministic else None,
                "repetitions": len(selected),
                "retrieval_complete": all(bool(item["retrieval_complete"]) for item in selected),
                "source_id": first["source_id"] if deterministic else None,
                "table_count": int(first["table_count"]),
                "wall_p50_ns": int(statistics.median(walls)),
                "wall_p95_ns": _p95(walls),
            }
        )
    return {
        "assets": assets,
        "benchmark_version": observations["benchmark_version"],
        "corpus": observations["corpus"],
        "coverage": {
            "asset_count": len(assets),
            "formats": sorted({str(item["format"]) for item in rows}),
            "row_count": len(rows),
        },
        "environment": observations["environment"],
        "model": observations["model"],
        "offline": observations["offline"],
        "thresholds": {
            "maximum_asset_wall_ns": protocol["maximum_asset_wall_ns"],
            "maximum_peak_rss_bytes": protocol["maximum_peak_rss_bytes"],
            "required_repetitions": protocol["required_repetitions"],
        },
    }


def _decide(summary: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    corpus = summary["corpus"]
    model = summary["model"]
    for actual, expected, label in (
        (corpus["corpus_id"], protocol["expected_corpus_id"], "corpus_id"),
        (corpus["payload_bytes"], protocol["expected_payload_bytes"], "payload_bytes"),
        (corpus["payload_count"], protocol["expected_payload_count"], "payload_count"),
        (model["bundle_id"], protocol["expected_model_bundle_id"], "model_bundle_id"),
        (
            model["source_lock_id"],
            protocol["expected_model_source_lock_id"],
            "model_source_lock_id",
        ),
    ):
        if actual != expected:
            failures.append(f"identity:{label}")
    coverage = summary["coverage"]
    if coverage["formats"] != protocol["required_formats"]:
        failures.append("coverage:formats")
    if coverage["asset_count"] != protocol["expected_payload_count"]:
        failures.append("coverage:assets")
    if coverage["row_count"] != (
        protocol["expected_payload_count"] * protocol["required_repetitions"]
    ):
        failures.append("coverage:rows")
    if not all(bool(value) for value in summary["offline"].values()):
        failures.append("offline:authority")
    if any(int(asset["network_attempts"]) for asset in summary["assets"]):
        failures.append("offline:network_attempt")
    for asset in summary["assets"]:
        key = str(asset["asset_key"])
        if asset["repetitions"] != protocol["required_repetitions"]:
            failures.append(f"coverage:repetitions:{key}")
        if asset["outcomes"] != ["pass"] or asset["error_categories"]:
            failures.append(f"execution:{key}")
        if not asset["deterministic"]:
            failures.append(f"correctness:nondeterministic:{key}")
        if asset["block_count"] <= 0 or not asset["anchor_classes"]:
            failures.append(f"correctness:empty:{key}")
        if not asset["retrieval_complete"] or not asset["pointer_resolution_complete"]:
            failures.append(f"correctness:retrieval:{key}")
        if asset["format"] in {"pdf", "pptx"} and asset["page_count"] <= 0:
            failures.append(f"correctness:pages:{key}")
        if asset["format"] == "csv" and asset["table_count"] <= 0:
            failures.append(f"correctness:table:{key}")
        if asset["wall_p95_ns"] > protocol["maximum_asset_wall_ns"]:
            failures.append("resource:wall")
        if asset["peak_rss_bytes"] > protocol["maximum_peak_rss_bytes"]:
            failures.append("resource:rss")
    failures = sorted(set(failures))
    return {
        "benchmark_version": protocol["benchmark_version"],
        "decision": (
            "REALWORLD_BASELINE_READY" if not failures else "REALWORLD_BASELINE_NOT_READY"
        ),
        "failure_codes": failures,
    }


def _report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    lines = [
        "# F024 real-world corpus structural baseline",
        "",
        f"Decision: **{decision['decision']}**",
        "",
        f"- Corpus: `{summary['corpus']['corpus_id']}`",
        f"- Payloads: {summary['corpus']['payload_count']} / "
        f"{summary['corpus']['payload_bytes']} bytes",
        f"- Formats: {', '.join(summary['coverage']['formats'])}",
        f"- Retained observations: {summary['coverage']['row_count']}",
        "",
        "| Asset | Format | Blocks | Pages | Tables | Bounded pointers | "
        "Wall p50/p95 (ns) | Peak RSS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for asset in summary["assets"]:
        lines.append(
            f"| {asset['asset_key']} | {asset['format']} | {asset['block_count']} | "
            f"{asset['page_count']} | {asset['table_count']} | "
            f"{asset['pointer_bounded_count']} | {asset['wall_p50_ns']} / "
            f"{asset['wall_p95_ns']} | {asset['peak_rss_bytes']} |"
        )
    lines.extend(
        (
            "",
            "This result covers exact offline structural parsing and retrievability for six "
            "selected English public-sector files. It does not establish semantic answer "
            "correctness, ranking or citation quality, general document-population quality, "
            "legal certainty or publisher endorsement.",
            "",
        )
    )
    return "\n".join(lines)


def _validate_rows(
    observations: dict[str, Any],
    lock: dict[str, Any],
    protocol: dict[str, Any],
) -> None:
    if set(observations) != {
        "benchmark_version",
        "corpus",
        "environment",
        "model",
        "offline",
        "rows",
    }:
        raise BenchmarkValidationFailure("observation_fields")
    assets = {str(item["key"]): item for item in _array(lock.get("assets"))}
    rows = [_object(item) for item in _array(observations.get("rows"))]
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if set(row) != ROW_FIELDS:
            raise BenchmarkValidationFailure("row_fields")
        key = str(row.get("asset_key"))
        repetition = _integer(row.get("repetition"))
        if key not in assets or (key, repetition) in seen:
            raise BenchmarkValidationFailure("row_key")
        seen.add((key, repetition))
        asset = assets[key]
        if row.get("format") != asset["format"] or row.get("source_id") != asset["sha256"]:
            raise BenchmarkValidationFailure("row_source")
        for field in ("block_set_id", "native_id", "recipe_id", "source_id"):
            _sha_id(row.get(field))
        for field in (
            "block_count",
            "cpu_ns",
            "native_bytes",
            "network_attempts",
            "page_count",
            "peak_rss_bytes",
            "pointer_bounded_count",
            "table_count",
            "wall_ns",
        ):
            _integer(row.get(field))
        anchors = _array(row.get("anchor_classes"))
        if anchors != sorted(set(anchors)) or not all(isinstance(item, str) for item in anchors):
            raise BenchmarkValidationFailure("row_anchors")
        if row.get("outcome") not in {"pass", "fail"}:
            raise BenchmarkValidationFailure("row_outcome")
        if not isinstance(row.get("pointer_resolution_complete"), bool) or not isinstance(
            row.get("retrieval_complete"), bool
        ):
            raise BenchmarkValidationFailure("row_boolean")
        if row.get("error_category") is not None and row.get("error_category") not in {
            "model_boundary",
            "parser_failure",
            "resource_limit",
            "timeout",
            "validation",
        }:
            raise BenchmarkValidationFailure("row_error")
    expected = {
        (key, repetition)
        for key in assets
        for repetition in range(int(protocol["required_repetitions"]))
    }
    if seen != expected:
        raise BenchmarkValidationFailure("row_coverage")
    serialized = _canonical(observations).decode("utf-8").casefold()
    for prohibited in ("/users/", "c:\\users\\", "traceback", "document_body"):
        if prohibited in serialized:
            raise BenchmarkValidationFailure("body_or_path_leakage")


def validate(repository_root: Path, result: Path) -> dict[str, Any]:
    """Regenerate every result projection without importing producer/evaluator code."""
    root = repository_root.resolve(strict=True)
    corpus_root = root / "corpora/realworld/v0.1.0"
    corpus_id, count, size = validate_corpus(corpus_root)
    protocol = _object(_load_json(root / "benchmarks/realworld-corpus/v0.1.0/protocol.json"))
    lock = _object(_load_json(corpus_root / "corpus-lock.json"))
    output = result.resolve(strict=True)
    if output.is_symlink() or not output.is_dir():
        raise BenchmarkValidationFailure("result_root")
    files = {item.name for item in output.iterdir() if item.is_file() and not item.is_symlink()}
    if files != set(RESULT_NAMES) or any(item.is_dir() for item in output.iterdir()):
        raise BenchmarkValidationFailure("result_inventory")
    if sum((output / name).stat().st_size for name in RESULT_NAMES) > int(
        protocol["maximum_result_bytes"]
    ):
        raise BenchmarkValidationFailure("result_size")
    observations = _object(_load_json(output / "observations.json"))
    _validate_rows(observations, lock, protocol)
    if observations.get("corpus") != {
        "corpus_id": corpus_id,
        "payload_bytes": size,
        "payload_count": count,
    }:
        raise BenchmarkValidationFailure("corpus_facts")
    expected_summary = _summarize(observations, protocol)
    expected_decision = _decide(expected_summary, protocol)
    summary = _load_json(output / "summary.json")
    decision = _load_json(output / "decision.json")
    if summary != expected_summary or decision != expected_decision:
        raise BenchmarkValidationFailure("projection_drift")
    report = (output / "report.md").read_text(encoding="utf-8")
    if report != _report(expected_summary, expected_decision):
        raise BenchmarkValidationFailure("report_drift")
    for name in ("observations.json", "summary.json", "decision.json"):
        if (output / name).read_bytes() != _canonical(_load_json(output / name)) + b"\n":
            raise BenchmarkValidationFailure("canonical_json")

    manifest = _object(_load_json(output / "run-manifest.json"))
    if set(manifest) != {"benchmark_version", "duration_ns", "files", "run_id"}:
        raise BenchmarkValidationFailure("manifest_fields")
    if manifest.get("benchmark_version") != protocol["benchmark_version"]:
        raise BenchmarkValidationFailure("manifest_version")
    _integer(manifest.get("duration_ns"))
    entries = [_object(item) for item in _array(manifest.get("files"))]
    expected_names = [name for name in RESULT_NAMES if name != "run-manifest.json"]
    if [item.get("name") for item in entries] != expected_names:
        raise BenchmarkValidationFailure("manifest_inventory")
    for entry in entries:
        name = str(entry["name"])
        payload = (output / name).read_bytes()
        if entry.get("byte_length") != len(payload) or entry.get("sha256") != _sha(payload):
            raise BenchmarkValidationFailure("manifest_digest")
    projection = dict(manifest)
    run_id = _sha_id(projection.pop("run_id"))
    if run_id != _sha(_canonical(projection)):
        raise BenchmarkValidationFailure("run_id")
    if (output / "run-manifest.json").read_bytes() != _canonical(manifest) + b"\n":
        raise BenchmarkValidationFailure("canonical_manifest")
    return expected_decision


def main() -> int:
    """Validate one result and emit only its stable decision."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.repository_root, arguments.result)
    except (BenchmarkValidationFailure, ValidationFailure, OSError, ValueError):
        print("benchmark_invalid")
        return 6
    print(f"decision={decision['decision']} failures={len(decision['failure_codes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
