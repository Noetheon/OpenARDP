"""Pure evaluation and report projection for the F023 PDF bundle benchmark."""

from __future__ import annotations

import statistics
from itertools import product
from typing import Any


def _p95(values: list[int]) -> int:
    """Return the deterministic nearest-rank p95 for a non-empty sample."""
    ordered = sorted(values)
    index = max(0, (95 * len(ordered) + 99) // 100 - 1)
    return ordered[index]


def _bootstrap_median_interval(values: list[int]) -> tuple[int, int]:
    """Return an exhaustive deterministic 95-percent bootstrap median interval."""
    medians = sorted(
        int(statistics.median(sample)) for sample in product(values, repeat=len(values))
    )
    low = int(0.025 * (len(medians) - 1))
    high = int(0.975 * (len(medians) - 1))
    return medians[low], medians[high]


def summarize(observations: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    """Derive exact inventory, correctness and robust timing summaries."""
    runs = observations["conversion_runs"]
    validation_runs = observations["validation_runs"]
    walls = [int(item["wall_ns"]) for item in runs]
    cpus = [int(item["cpu_ns"]) for item in runs]
    native_ids = sorted({str(item["native_sha256"]) for item in runs})
    median_wall = int(statistics.median(walls))
    wall_confidence_low, wall_confidence_high = _bootstrap_median_interval(walls)
    return {
        "asset_bytes": observations["installation"]["asset_bytes"],
        "asset_file_count": observations["installation"]["asset_file_count"],
        "bundle_id": observations["installation"]["bundle_id"],
        "conversion": {
            "all_anchored": all(
                item["anchored_evidence_count"] == item["evidence_count"] for item in runs
            ),
            "all_pointers": all(
                item["pointer_evidence_count"] == item["evidence_count"] for item in runs
            ),
            "cpu_p50_ns": int(statistics.median(cpus)),
            "cpu_p95_ns": _p95(cpus),
            "cold_wall_ns": runs[0]["wall_ns"],
            "deterministic_native": len(native_ids) == 1,
            "evidence_count": runs[0]["evidence_count"],
            "native_sha256": native_ids[0] if len(native_ids) == 1 else None,
            "page_count": runs[0]["page_count"],
            "peak_rss_bytes": max(int(item["peak_rss_bytes"]) for item in runs),
            "sample_count": len(runs),
            "wall_mad_ns": int(statistics.median(abs(value - median_wall) for value in walls)),
            "wall_median_confidence_high_ns": wall_confidence_high,
            "wall_median_confidence_low_ns": wall_confidence_low,
            "wall_p50_ns": median_wall,
            "wall_p95_ns": _p95(walls),
            "warm_wall_p50_ns": int(
                statistics.median(item["wall_ns"] for item in runs if item["cache_state"] == "warm")
            ),
            "warm_wall_p95_ns": _p95(
                [item["wall_ns"] for item in runs if item["cache_state"] == "warm"]
            ),
        },
        "offline": observations["offline"],
        "package_bytes": observations["package"]["package_bytes"],
        "package_id": observations["package"]["package_id"],
        "package_overhead_bytes": (
            observations["package"]["package_bytes"]
            - observations["installation"]["installation_bytes"]
        ),
        "provisioning": observations["provisioning"],
        "source_lock_id": observations["installation"]["source_lock_id"],
        "thresholds": {
            "maximum_asset_bytes": protocol["maximum_asset_bytes"],
            "maximum_package_overhead_bytes": protocol["maximum_package_overhead_bytes"],
            "maximum_validation_ns": protocol["maximum_validation_ns"],
            "maximum_validation_rss_bytes": protocol["maximum_validation_rss_bytes"],
            "retained_samples": protocol["retained_samples"],
        },
        "validation": {
            "all_identities_match": all(
                item["bundle_id"] == observations["installation"]["bundle_id"]
                and item["source_lock_id"] == observations["installation"]["source_lock_id"]
                for item in validation_runs
            ),
            "peak_rss_bytes": max(item["peak_rss_bytes"] for item in validation_runs),
            "sample_count": len(validation_runs),
            "wall_p50_ns": int(statistics.median(item["wall_ns"] for item in validation_runs)),
            "wall_p95_ns": _p95([item["wall_ns"] for item in validation_runs]),
        },
    }


def decide(summary: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    """Apply the closed readiness policy while retaining unfavorable evidence."""
    failures: list[str] = []
    conversion = summary["conversion"]
    expected = (
        ("asset_bytes", "expected_asset_bytes"),
        ("asset_file_count", "expected_asset_file_count"),
        ("bundle_id", "expected_bundle_id"),
        ("package_id", "expected_package_id"),
        ("source_lock_id", "expected_source_lock_id"),
    )
    for field, policy in expected:
        if summary[field] != protocol[policy]:
            failures.append(f"identity:{field}")
    if summary["asset_bytes"] > protocol["maximum_asset_bytes"]:
        failures.append("size:assets")
    if summary["package_overhead_bytes"] > protocol["maximum_package_overhead_bytes"]:
        failures.append("size:package_overhead")
    if conversion["sample_count"] != protocol["retained_samples"]:
        failures.append("coverage:retained_samples")
    for field in ("all_anchored", "all_pointers", "deterministic_native"):
        if not conversion[field]:
            failures.append(f"correctness:{field}")
    if conversion["evidence_count"] <= 0 or conversion["page_count"] <= 0:
        failures.append("correctness:empty_projection")
    if not all(summary["offline"].values()):
        failures.append("offline:authority")
    validation = summary["validation"]
    if validation["sample_count"] != protocol["validation_samples"]:
        failures.append("coverage:validation_samples")
    if not validation["all_identities_match"]:
        failures.append("validation:identity")
    if validation["wall_p95_ns"] > protocol["maximum_validation_ns"]:
        failures.append("validation:latency")
    if validation["peak_rss_bytes"] > protocol["maximum_validation_rss_bytes"]:
        failures.append("validation:rss")
    return {
        "benchmark_version": protocol["benchmark_version"],
        "decision": "PDF_OFFLINE_READY" if not failures else "PDF_OFFLINE_NOT_READY",
        "failure_codes": failures,
    }


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render the deterministic human-readable projection."""
    conversion = summary["conversion"]
    lines = [
        "# F023 offline PDF model bundle result",
        "",
        f"Decision: **{decision['decision']}**",
        "",
        f"- Exact model payload: {summary['asset_bytes']} bytes in "
        f"{summary['asset_file_count']} files",
        f"- Portable package: {summary['package_bytes']} bytes "
        f"({summary['package_overhead_bytes']} bytes overhead)",
        f"- Fresh retained conversions: {conversion['sample_count']}",
        f"- Conversion wall p50/p95: {conversion['wall_p50_ns']} / {conversion['wall_p95_ns']} ns",
        f"- Conversion CPU p50/p95: {conversion['cpu_p50_ns']} / {conversion['cpu_p95_ns']} ns",
        f"- Peak child RSS: {conversion['peak_rss_bytes']} bytes",
        f"- Validation wall p50/p95: {summary['validation']['wall_p50_ns']} / "
        f"{summary['validation']['wall_p95_ns']} ns",
        f"- Validation peak RSS: {summary['validation']['peak_rss_bytes']} bytes",
        f"- Connected provision duration: {summary['provisioning']['duration_ns']} ns",
        f"- Evidence/pages: {conversion['evidence_count']} / {conversion['page_count']}",
        "",
        "Workers used fresh private cache roots, provider offline flags and socket denial "
        "before provider import. The result proves synthetic offline readiness only; it "
        "does not establish real-world or semantic quality.",
        "",
    ]
    return "\n".join(lines)


__all__ = ["decide", "render_report", "summarize"]
