"""Pure summaries, decision and report for the F024 structural baseline."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any


def _p95(values: list[int]) -> int:
    """Return deterministic nearest-rank p95 for one non-empty sample."""
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def summarize(observations: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    """Derive exact coverage, determinism, retrieval and resource summaries."""
    rows = list(observations["rows"])
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


def decide(summary: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    """Apply the complete fail-closed structural readiness policy."""
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


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render one deterministic body-free human-readable result projection."""
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


__all__ = ["decide", "render_report", "summarize"]
