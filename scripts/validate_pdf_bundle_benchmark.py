"""Independent validator for committed F023 offline PDF benchmark evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from openardp.domain.identity import canonical_json_bytes

try:
    from scripts.pdf_bundle_benchmark_evaluation import decide, render_report, summarize
except ModuleNotFoundError:
    from pdf_bundle_benchmark_evaluation import decide, render_report, summarize

_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> Any:
    payload = path.read_bytes()
    value = json.loads(payload)
    if payload != canonical_json_bytes(value) + b"\n":
        raise ValueError("noncanonical benchmark JSON")
    return value


def validate(repository_root: Path, output: Path) -> dict[str, Any]:
    """Recompute input identities, statistics, policy and every projection."""
    root = repository_root.resolve(strict=True)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("unsafe benchmark output")
    if tuple(sorted(path.name for path in output.iterdir())) != _NAMES:
        raise ValueError("benchmark result inventory mismatch")
    benchmark_root = root / "benchmarks/pdf-bundle/v0.1.0"
    protocol = json.loads((benchmark_root / "protocol.json").read_bytes())
    baseline = json.loads((benchmark_root / "baseline.json").read_bytes())
    f020 = root / "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/summary.json"
    if _sha256(f020.read_bytes()) != baseline["f020_summary_sha256"]:
        raise ValueError("historical baseline drift")
    observations = _load_json(output / "observations.json")
    source = (root / protocol["fixture_path"]).read_bytes()
    if (
        observations["fixture"]
        != {
            "byte_length": len(source),
            "sha256": protocol["fixture_sha256"],
        }
        or _sha256(source) != protocol["fixture_sha256"]
    ):
        raise ValueError("fixture drift")
    summary = _load_json(output / "summary.json")
    decision = _load_json(output / "decision.json")
    expected_summary = summarize(observations, protocol)
    expected_decision = decide(expected_summary, protocol)
    if summary != expected_summary or decision != expected_decision:
        raise ValueError("derived evidence drift")
    if (output / "report.md").read_text(encoding="utf-8") != render_report(summary, decision):
        raise ValueError("report drift")
    manifest = _load_json(output / "run-manifest.json")
    expected_files = [
        {
            "byte_length": (output / name).stat().st_size,
            "name": name,
            "sha256": _sha256((output / name).read_bytes()),
        }
        for name in _NAMES
        if name != "run-manifest.json"
    ]
    if manifest["files"] != expected_files:
        raise ValueError("result manifest drift")
    identity = dict(manifest)
    run_id = identity.pop("run_id")
    if run_id != _sha256(canonical_json_bytes(identity)):
        raise ValueError("run identity drift")
    combined = b"".join((output / name).read_bytes() for name in _NAMES).lower()
    for marker in (b"/users/", b"\\users\\", b"password", b"api_key", b"hostname"):
        if marker in combined:
            raise ValueError("privacy marker detected")
    if sum((output / name).stat().st_size for name in _NAMES) > protocol["maximum_result_bytes"]:
        raise ValueError("result size limit exceeded")
    return decision


def main() -> int:
    """Validate a published result without importing the benchmark producer."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate(arguments.repository_root, arguments.result)
    except (OSError, ValueError, json.JSONDecodeError):
        print("pdf_bundle_benchmark_invalid")
        return 4
    print(f"pdf_bundle_benchmark_valid decision={decision['decision']}")
    return 0 if decision["decision"] == "PDF_OFFLINE_READY" else 8


if __name__ == "__main__":
    raise SystemExit(main())
