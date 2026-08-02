"""Independently recompute and validate committed F021 freshness evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
import socket
from pathlib import Path
from typing import cast

from pydantic import JsonValue

from openardp.domain.identity import canonical_json_bytes, canonical_sha256

try:
    from scripts.freshness_benchmark import (
        FreshnessDecision,
        FreshnessObservation,
        FreshnessSummary,
        canonical_file,
        decide_freshness,
        load_freshness_protocol,
        read_json_object,
        render_report,
        summarize_observations,
    )
except ModuleNotFoundError:
    from freshness_benchmark import (  # type: ignore[no-redef]
        FreshnessDecision,
        FreshnessObservation,
        FreshnessSummary,
        canonical_file,
        decide_freshness,
        load_freshness_protocol,
        read_json_object,
        render_report,
        summarize_observations,
    )

_FILES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)


def _list(value: JsonValue, name: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _object(value: JsonValue, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _validate_privacy(result: Path) -> None:
    payload = b"\n".join((result / name).read_bytes() for name in _FILES)
    forbidden = {
        str(Path.home()),
        str(result.resolve()),
        socket.gethostname(),
        os.environ.get("USER", ""),
        "Traceback (most recent call last)",
        "Fact fact-000000 uses verification token",
    }
    for value in forbidden:
        if value and value.encode("utf-8") in payload:
            raise ValueError("benchmark evidence contains forbidden private or body data")


def validate_freshness_benchmark(
    repository_root: Path,
    result: Path,
) -> FreshnessDecision:
    """Recompute every derived byte, identity, hash, counter policy and privacy rule."""
    root = repository_root.resolve(strict=True)
    output = result.resolve(strict=True)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("benchmark result must be a regular directory")
    inventory = tuple(sorted(path.name for path in output.iterdir()))
    if inventory != _FILES:
        raise ValueError("benchmark result inventory is incomplete or unexpected")
    protocol, protocol_id = load_freshness_protocol(root)

    observations_raw = read_json_object(output / "observations.json")
    if canonical_file(observations_raw) != (output / "observations.json").read_bytes():
        raise ValueError("observations are not canonical")
    if observations_raw.get("benchmark_version") != "0.1.0":
        raise ValueError("observation benchmark version differs")
    if observations_raw.get("protocol_id") != protocol_id:
        raise ValueError("observation protocol identity differs")
    environment = _object(observations_raw.get("environment"), "environment")
    environment_id = canonical_sha256(environment)
    if observations_raw.get("environment_id") != environment_id:
        raise ValueError("environment identity differs")
    observation_values = _list(observations_raw.get("observations"), "observations")
    observations = tuple(
        FreshnessObservation.model_validate_json(
            canonical_json_bytes(_object(value, "observation"))
        )
        for value in observation_values
    )
    if len(observations) != 28:
        raise ValueError("benchmark must retain exactly 28 observations")
    if any(item.environment_id != environment_id for item in observations):
        raise ValueError("observation environment identity differs")
    facts = _object(observations_raw.get("facts"), "facts")
    if set(facts) != {"reference", "scale"}:
        raise ValueError("profile facts are incomplete")
    for profile in ("reference", "scale"):
        profile_facts = _object(facts[profile], f"{profile} facts")
        if profile_facts.get("block_count") != protocol.corpus.profiles[profile]:
            raise ValueError("fact block count differs from protocol")
        if profile_facts.get("source_sha256_before") != profile_facts.get("source_sha256_after"):
            raise ValueError("source immutability evidence failed")
        if profile_facts.get("object_inventory_before") != profile_facts.get(
            "object_inventory_after"
        ):
            raise ValueError("persisted-object immutability evidence failed")
    run_id = canonical_sha256(
        {
            "environment_id": environment_id,
            "observation_ids": [item.observation_id for item in observations],
            "protocol_id": protocol_id,
        }
    )
    if observations_raw.get("run_id") != run_id:
        raise ValueError("run identity differs")

    summaries = summarize_observations(protocol, observations)
    summary_raw = read_json_object(output / "summary.json")
    expected_summary: dict[str, JsonValue] = {
        "benchmark_version": "0.1.0",
        "protocol_id": protocol_id,
        "run_id": run_id,
        "summaries": [item.model_dump(mode="json") for item in summaries],
    }
    if canonical_file(expected_summary) != (output / "summary.json").read_bytes():
        raise ValueError("summary does not match recomputation")
    persisted_summaries = tuple(
        FreshnessSummary.model_validate_json(canonical_json_bytes(_object(value, "summary")))
        for value in _list(summary_raw.get("summaries"), "summaries")
    )
    if persisted_summaries != summaries:
        raise ValueError("persisted summary models differ")

    decision = decide_freshness(protocol, observations, summaries)
    persisted_decision = FreshnessDecision.model_validate_json(
        canonical_json_bytes(read_json_object(output / "decision.json"))
    )
    if persisted_decision != decision:
        raise ValueError("decision does not match recomputation")
    if canonical_file(decision) != (output / "decision.json").read_bytes():
        raise ValueError("decision bytes are not deterministic")
    if render_report(protocol, summaries, decision) != (output / "report.md").read_bytes():
        raise ValueError("report does not match deterministic projection")

    manifest = read_json_object(output / "run-manifest.json")
    if canonical_file(manifest) != (output / "run-manifest.json").read_bytes():
        raise ValueError("manifest is not canonical")
    manifest_projection = dict(manifest)
    manifest_id = manifest_projection.pop("manifest_id", None)
    if manifest_id != canonical_sha256(manifest_projection):
        raise ValueError("manifest identity differs")
    if manifest.get("run_id") != run_id or manifest.get("protocol_id") != protocol_id:
        raise ValueError("manifest binding differs")
    if manifest.get("environment_id") != environment_id:
        raise ValueError("manifest environment differs")
    files = _object(manifest.get("files"), "manifest files")
    if set(files) != set(_FILES) - {"run-manifest.json"}:
        raise ValueError("manifest file inventory differs")
    for name, value in files.items():
        entry = _object(value, "manifest file")
        payload = (output / name).read_bytes()
        if entry != {
            "byte_length": len(payload),
            "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        }:
            raise ValueError("manifest file binding differs")
    _validate_privacy(output)
    return cast(FreshnessDecision, decision)


def main() -> int:
    """Validate one result directory without rerunning measured workloads."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        decision = validate_freshness_benchmark(arguments.repository_root, arguments.result)
    except (OSError, ValueError):
        print("freshness_benchmark_invalid")
        return 6
    print(
        '{"category":"freshness_benchmark_valid","decision_id":"'
        f'{decision.decision_id}","outcome":"{decision.outcome}"}}'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
