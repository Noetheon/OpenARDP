"""End-to-end contracts for the F020 offline product benchmark."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.product_benchmark import (
    BenchmarkMetric,
    BenchmarkProfile,
    BenchmarkTreatment,
    ObservationStatus,
    ValueOutcome,
)
from scripts.product_benchmark_runner import (
    execute_product_benchmark,
    validate_product_benchmark,
)


def test_smoke_run_exercises_real_paths_and_publishes_recomputable_evidence(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Measure all text treatments, exact reuse, freshness, context and replay."""
    output = tmp_path / "result"
    result = execute_product_benchmark(
        repository_root,
        profile=BenchmarkProfile.SMOKE,
        output=output,
    )
    validated = validate_product_benchmark(repository_root, output)

    assert validated == result
    assert result.decision.outcome is ValueOutcome.NOT_DEMONSTRATED
    assert {path.name for path in output.iterdir()} == {
        "decision.json",
        "observations.json",
        "report.md",
        "run-manifest.json",
        "summary.json",
    }
    treatments = {item.treatment for item in result.observations}
    assert treatments == set(BenchmarkTreatment)
    assert any(
        item.metric is BenchmarkMetric.PARSER_INVOCATIONS
        and item.treatment is BenchmarkTreatment.OPENARDP
        and item.status is ObservationStatus.PASSED
        and item.value == 0
        for item in result.observations
    )
    assert any(
        item.metric is BenchmarkMetric.PRECISION
        and item.status is ObservationStatus.PASSED
        and item.value == 1.0
        for item in result.observations
    )
    summary = json.loads((output / "summary.json").read_bytes())
    assert summary["profile_facts"]["smoke"]["block_count"] == 100
    payload = b"".join(path.read_bytes() for path in output.iterdir())
    assert str(tmp_path).encode() not in payload
    assert str(repository_root).encode() not in payload


def test_validator_rejects_any_published_file_tamper(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Fail closed before trusting a result whose manifest-bound report changed."""
    output = tmp_path / "result"
    execute_product_benchmark(
        repository_root,
        profile=BenchmarkProfile.SMOKE,
        output=output,
    )
    report = output / "report.md"
    original_report = report.read_bytes()
    with report.open("a", encoding="utf-8") as stream:
        stream.write("tampered\n")
    with pytest.raises(ValueError, match="digest"):
        validate_product_benchmark(repository_root, output)
    report.write_bytes(original_report)

    summary_path = output / "summary.json"
    summary = json.loads(summary_path.read_bytes())
    summary["decision_metrics"]["precision"] = 0
    summary_path.write_bytes(canonical_json_bytes(summary) + b"\n")
    manifest_path = output / "run-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest.pop("run_id")
    manifest["files"] = [
        {
            "byte_length": path.stat().st_size,
            "name": path.name,
            "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(output.iterdir())
        if path.name != "run-manifest.json"
    ]
    manifest["run_id"] = canonical_sha256(manifest)
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    with pytest.raises(ValueError, match="metrics drifted"):
        validate_product_benchmark(repository_root, output)


def test_maintainer_scripts_use_stable_sanitized_exit_semantics(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Return closed categories without a traceback for conflicts and invalid evidence."""
    existing = tmp_path / "existing"
    existing.mkdir()
    conflict = subprocess.run(  # noqa: S603 - fixed local interpreter and repository script
        (
            sys.executable,
            "scripts/run_product_benchmark.py",
            "--profile",
            "smoke",
            "--output",
            str(existing),
        ),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert conflict.returncode == 8
    assert conflict.stdout.strip() == "benchmark_output_conflict"
    assert conflict.stderr == ""

    invalid = subprocess.run(  # noqa: S603 - fixed local interpreter and repository script
        (
            sys.executable,
            "scripts/validate_product_benchmark.py",
            "--result",
            str(tmp_path / "missing"),
        ),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 6
    assert invalid.stdout.strip() == "benchmark_evidence_invalid"
    assert invalid.stderr == ""
