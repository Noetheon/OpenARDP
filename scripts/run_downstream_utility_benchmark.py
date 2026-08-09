"""Derive the frozen F036 downstream evidence-utility result package."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.downstream_utility_benchmark import (
        RESULT_NAMES,
        DownstreamUtilityError,
        build_review_rows,
        canonical_json_bytes,
        canonical_sha256,
        decide,
        file_fact,
        load_protocol,
        load_source_rows,
        render_report,
        summarize,
    )
except ModuleNotFoundError:
    from downstream_utility_benchmark import (
        RESULT_NAMES,
        DownstreamUtilityError,
        build_review_rows,
        canonical_json_bytes,
        canonical_sha256,
        decide,
        file_fact,
        load_protocol,
        load_source_rows,
        render_report,
        summarize,
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _manifest(
    root: Path,
    staging: Path,
    protocol: dict[str, Any],
    review_row_count: int,
) -> dict[str, Any]:
    inputs = {
        "f034_observations": file_fact(
            root
            / "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64/observations.json"
        ),
        "f034_run_manifest": file_fact(
            root
            / "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64/run-manifest.json"
        ),
        "f035_observations": file_fact(
            root
            / "benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64/observations.json"
        ),
        "f035_run_manifest": file_fact(
            root
            / "benchmarks/profiled-retrieval/v0.1.0/results/reference-macos-arm64/run-manifest.json"
        ),
    }
    manifest: dict[str, Any] = {
        "benchmark_version": protocol["benchmark_version"],
        "protocol_id": protocol["protocol_id"],
        "offline": True,
        "review_row_count": review_row_count,
        "holdout_evaluations": 1,
        "comparison": protocol["holdout"]["comparison"],
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "inputs": inputs,
        "files": {
            name: file_fact(staging / name) for name in RESULT_NAMES if name != "run-manifest.json"
        },
    }
    manifest["run_id"] = canonical_sha256(manifest)
    return manifest


def produce(root: Path, output: Path) -> dict[str, Any]:
    """Build and atomically publish one deterministic result directory."""
    root = root.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise DownstreamUtilityError("output_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    protocol = load_protocol(root)
    source_rows = load_source_rows(root, protocol)
    review_rows = build_review_rows(source_rows, protocol)
    summary = summarize(review_rows, source_rows, protocol)
    decision = decide(summary)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        _write_json(
            staging / "observations.json",
            {"protocol_id": protocol["protocol_id"], "rows": review_rows},
        )
        _write_json(staging / "summary.json", summary)
        _write_json(staging / "decision.json", decision)
        (staging / "report.md").write_text(
            render_report(summary, decision), encoding="utf-8", newline="\n"
        )
        manifest = _manifest(root, staging, protocol, len(review_rows))
        _write_json(staging / "run-manifest.json", manifest)
        total_bytes = sum(path.stat().st_size for path in staging.iterdir())
        if total_bytes > int(protocol["result_max_bytes"]):
            raise DownstreamUtilityError("result_size")
        os.replace(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return decision


def main() -> int:
    """Execute with one stable body-free success or failure line."""
    arguments = _arguments()
    try:
        decision = produce(Path.cwd(), arguments.output)
    except (DownstreamUtilityError, KeyError, OSError, TypeError, ValueError):
        print("downstream_utility_execution_failed", file=sys.stderr)
        return 2
    print(
        f"downstream_utility_complete development={decision['development_candidate']} "
        f"holdout={decision['holdout_generalization']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
