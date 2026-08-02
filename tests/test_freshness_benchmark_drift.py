"""Independent F021 evidence recomputation, privacy and drift tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import JsonValue

from openardp.domain.identity import canonical_sha256
from scripts.freshness_benchmark import (
    canonical_file,
    decide_freshness,
    load_freshness_protocol,
    render_report,
    summarize_observations,
)
from scripts.validate_freshness_benchmark import validate_freshness_benchmark
from tests.integration.test_freshness_benchmark import ENVIRONMENT_ID, _observations


def _write_valid_result(root: Path, output: Path) -> None:
    protocol, protocol_id = load_freshness_protocol(root)
    observations = _observations(root)
    summaries = summarize_observations(protocol, observations)
    decision = decide_freshness(protocol, observations, summaries)
    environment: dict[str, JsonValue] = {"class": "synthetic-test"}
    environment_id = canonical_sha256(environment)
    rebound = tuple(
        item.model_copy(
            update={
                "environment_id": environment_id,
                "observation_id": canonical_sha256(
                    {
                        **item.model_dump(mode="json", exclude={"observation_id"}),
                        "environment_id": environment_id,
                    }
                ),
            }
        )
        for item in observations
    )
    assert environment_id != ENVIRONMENT_ID
    summaries = summarize_observations(protocol, rebound)
    decision = decide_freshness(protocol, rebound, summaries)
    run_id = canonical_sha256(
        {
            "environment_id": environment_id,
            "observation_ids": [item.observation_id for item in rebound],
            "protocol_id": protocol_id,
        }
    )
    output.mkdir()
    observation_payload: dict[str, JsonValue] = {
        "benchmark_version": "0.1.0",
        "environment": environment,
        "environment_id": environment_id,
        "facts": {
            profile: {
                "block_count": blocks,
                "object_inventory_after": "sha256:" + "b" * 64,
                "object_inventory_before": "sha256:" + "b" * 64,
                "source_bytes": blocks * 100,
                "source_sha256_after": "sha256:" + "c" * 64,
                "source_sha256_before": "sha256:" + "c" * 64,
            }
            for profile, blocks in protocol.corpus.profiles.items()
        },
        "observations": [item.model_dump(mode="json") for item in rebound],
        "protocol_id": protocol_id,
        "run_id": run_id,
    }
    summary_payload: dict[str, JsonValue] = {
        "benchmark_version": "0.1.0",
        "protocol_id": protocol_id,
        "run_id": run_id,
        "summaries": [item.model_dump(mode="json") for item in summaries],
    }
    files = {
        "observations.json": canonical_file(observation_payload),
        "summary.json": canonical_file(summary_payload),
        "decision.json": canonical_file(decision),
        "report.md": render_report(protocol, summaries, decision),
    }
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    manifest: dict[str, JsonValue] = {
        "benchmark_version": "0.1.0",
        "duration_ns": 1,
        "environment_id": environment_id,
        "files": {
            name: {
                "byte_length": len(payload),
                "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in files.items()
        },
        "protocol_id": protocol_id,
        "run_id": run_id,
    }
    manifest["manifest_id"] = canonical_sha256(manifest)
    (output / "run-manifest.json").write_bytes(canonical_file(manifest))


def test_validator_accepts_recomputed_evidence_and_rejects_tampering(tmp_path: Path) -> None:
    """Accept complete canonical evidence and reject one changed report byte."""
    root = Path.cwd()
    output = tmp_path / "result"
    _write_valid_result(root, output)
    assert validate_freshness_benchmark(root, output).outcome == "PASS"

    report = output / "report.md"
    report.write_bytes(report.read_bytes() + b"tampered\n")
    with pytest.raises(ValueError, match="report"):
        validate_freshness_benchmark(root, output)
