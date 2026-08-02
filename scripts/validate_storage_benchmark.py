"""Independent evidence validator for the F022 storage benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from openardp.domain.identity import canonical_json_bytes

_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
_CATEGORIES = (
    "catalog",
    "compact_derived_objects",
    "control",
    "ordinary_objects",
    "quarantine",
    "staging",
)


def _load_json(path: Path) -> Any:
    payload = path.read_bytes()
    value = json.loads(payload)
    if payload != canonical_json_bytes(value) + b"\n":
        raise ValueError("noncanonical benchmark JSON")
    return value


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _render(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    lines = [
        "# F022 storage amplification result",
        "",
        f"Decision: **{decision['decision']}**",
        "",
        "| Scenario | Logical bytes | Logical x | Allocated bytes | "
        "Allocated x | Files | Reduction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("fresh-reference", "migrated-reference", "fresh-scale"):
        item = summary["scenarios"][name]
        allocated = str(item["allocated_bytes"]) if item["allocation_supported"] else "unavailable"
        allocated_x = (
            f"{item['allocated_amplification']:.4f}"
            if item["allocation_supported"]
            else "unavailable"
        )
        lines.append(
            f"| {name} | {item['logical_bytes']} | {item['logical_amplification']:.4f} | "
            f"{allocated} | {allocated_x} | {item['file_count']} | "
            f"{item['logical_reduction_ratio']:.2%} |"
        )
    lines.extend(
        (
            "",
            "Logical and filesystem-allocated reductions are separate measurements. "
            "Allocation uses `st_blocks * 512` on this host and is filesystem-dependent. "
            "Original F020 evidence is retained; "
            "no historical result was rewritten.",
            "",
        )
    )
    return "\n".join(lines)


def validate(repository_root: Path, output: Path) -> dict[str, Any]:
    """Recompute every inventory total, metric, threshold and projection."""
    root = repository_root.resolve(strict=True)
    expected_names = _NAMES
    if output.is_symlink() or not output.is_dir():
        raise ValueError("unsafe benchmark output")
    names = tuple(sorted(path.name for path in output.iterdir()))
    if names != expected_names:
        raise ValueError("benchmark result inventory mismatch")
    benchmark_root = root / "benchmarks/storage/v0.1.0"
    protocol = json.loads((benchmark_root / "protocol.json").read_bytes())
    baseline = json.loads((benchmark_root / "baseline.json").read_bytes())
    product_root = root / "benchmarks/product-value/v0.1.0"
    for name, expected in protocol["baseline_inputs"].items():
        if _sha256(product_root / name) != expected:
            raise ValueError("frozen input drift")
    if (
        _sha256(product_root / "results/reference-macos-arm64/summary.json")
        != baseline["f020_summary_sha256"]
    ):
        raise ValueError("historical baseline drift")
    observations = _load_json(output / "observations.json")
    summary = _load_json(output / "summary.json")
    decision = _load_json(output / "decision.json")
    manifest = _load_json(output / "run-manifest.json")
    combined = b"".join((output / name).read_bytes() for name in _NAMES).lower()
    for marker in (b"/users/", b"\\users\\", b"password", b"api_key", b"hostname"):
        if marker in combined:
            raise ValueError("privacy marker detected")
    if [item["scenario"] for item in observations] != protocol["scenarios"]:
        raise ValueError("scenario order drift")
    derived: dict[str, Any] = {}
    for item in observations:
        for phase in ("before", "after"):
            inventory = item[phase]
            if tuple(sorted(inventory["categories"])) != _CATEGORIES:
                raise ValueError("category inventory drift")
            totals = inventory["totals"]
            for key in ("allocated_bytes", "file_count", "logical_bytes"):
                if totals[key] != sum(
                    category[key] for category in inventory["categories"].values()
                ):
                    raise ValueError("category arithmetic mismatch")
        profile = item["profile"]
        source_bytes = item["source"]["byte_length"]
        if item["source"]["sha256"] != baseline["profiles"][profile]["source_sha256"]:
            raise ValueError("source identity drift")
        if source_bytes != baseline["profiles"][profile]["source_bytes"]:
            raise ValueError("source length drift")
        after = item["after"]["totals"]
        historical = baseline["profiles"][profile]["workspace_logical_bytes"]
        derived[item["scenario"]] = {
            "allocated_amplification": (
                after["allocated_bytes"] / source_bytes
                if item["after"]["allocation_supported"]
                else None
            ),
            "allocated_bytes": after["allocated_bytes"],
            "allocation_supported": item["after"]["allocation_supported"],
            "all_checks_passed": all(item["checks"].values()),
            "file_count": after["file_count"],
            "logical_amplification": after["logical_bytes"] / source_bytes,
            "logical_bytes": after["logical_bytes"],
            "logical_reduction_ratio": (historical - after["logical_bytes"]) / historical,
            "source_bytes": source_bytes,
        }
    if summary["scenarios"] != derived:
        raise ValueError("summary arithmetic drift")
    expected_thresholds = {
        "allocated_reference_max_multiplier": protocol["allocated_reference_max_multiplier"],
        "logical_max_multiplier": protocol["logical_max_multiplier"],
        "minimum_logical_reduction_ratio": protocol["minimum_logical_reduction_ratio"],
    }
    if summary["thresholds"] != expected_thresholds:
        raise ValueError("threshold drift")
    failures: list[str] = []
    for name, item in derived.items():
        if not item["all_checks_passed"]:
            failures.append(f"{name}:correctness")
        if item["logical_amplification"] > protocol["logical_max_multiplier"]:
            failures.append(f"{name}:logical_amplification")
        if item["logical_reduction_ratio"] < protocol["minimum_logical_reduction_ratio"]:
            failures.append(f"{name}:logical_reduction")
    reference = derived["fresh-reference"]
    if not reference["allocation_supported"]:
        failures.append("fresh-reference:allocation_unavailable")
    elif reference["allocated_amplification"] > protocol["allocated_reference_max_multiplier"]:
        failures.append("fresh-reference:allocated_amplification")
    expected_decision = {
        "benchmark_version": "0.1.0",
        "decision": "PASS" if not failures else "FAIL",
        "failure_codes": failures,
    }
    if decision != expected_decision:
        raise ValueError("decision drift")
    if (output / "report.md").read_text(encoding="utf-8") != _render(summary, decision):
        raise ValueError("report drift")
    expected_files = [
        {
            "byte_length": (output / name).stat().st_size,
            "name": name,
            "sha256": _sha256(output / name),
        }
        for name in _NAMES
        if name != "run-manifest.json"
    ]
    if (
        manifest["files"] != expected_files
        or manifest["legacy_revision"] != protocol["legacy_revision"]
    ):
        raise ValueError("manifest drift")
    expected_run = dict(manifest)
    run_id = expected_run.pop("run_id")
    if run_id != "sha256:" + hashlib.sha256(canonical_json_bytes(expected_run)).hexdigest():
        raise ValueError("run identity drift")
    if sum((output / name).stat().st_size for name in _NAMES) > protocol["maximum_result_bytes"]:
        raise ValueError("result size limit exceeded")
    return decision


def main() -> int:
    """Validate one published result without invoking its producer."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.repository_root, arguments.output)
    except (OSError, ValueError, json.JSONDecodeError):
        print("storage_benchmark_invalid")
        return 4
    print(f"storage_benchmark_valid decision={decision['decision']}")
    return 0 if decision["decision"] == "PASS" else 8


if __name__ == "__main__":
    raise SystemExit(main())
