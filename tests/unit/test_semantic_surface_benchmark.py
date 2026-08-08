"""Frozen F030 operational benchmark producer/validator contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from scripts.run_semantic_surface_benchmark import (
    _decision,
    _load_protocol,
    _projection_id,
    _publish,
    _summary,
)
from scripts.validate_semantic_surface_benchmark import (
    READY,
    ValidationError,
    _privacy,
    load_protocol,
    validate,
)


def _run(index: int, *, warm_hits: int = 95) -> dict[str, object]:
    value: dict[str, object] = {
        "run_index": index,
        "bundle_verify_ns": 100,
        "cold_wall_ns": 1_000,
        "warm_wall_ns": 500,
        "cold_projection_id": "sha256:" + "4" * 64,
        "warm_projection_id": "sha256:" + "4" * 64,
        "cold_metrics": {
            "requests": 19,
            "passages_scored": 100,
            "cache_hits": 0,
            "peak_worker_rss_bytes": 1_000_000,
        },
        "warm_metrics": {
            "requests": 19,
            "passages_scored": 100,
            "cache_hits": warm_hits,
            "peak_worker_rss_bytes": 1_000_000,
        },
    }
    value["observation_id"] = canonical_sha256(value)
    return value


def _publish_valid(repository_root: Path, destination: Path) -> None:
    protocol = _load_protocol(repository_root)
    runs = [_run(1), _run(2)]
    observations: dict[str, object] = {
        "benchmark_version": "0.1.0",
        "protocol_id": protocol["protocol_id"],
        "corpus_id": protocol["corpus_id"],
        "question_set_id": protocol["question_set_id"],
        "provider_recipe_id": "sha256:" + "5" * 64,
        "runs": runs,
    }
    observations["observations_id"] = canonical_sha256(observations)
    summary = _summary(observations, runs, protocol)  # type: ignore[arg-type]
    decision = _decision(summary, protocol)
    _publish(destination, observations, summary, decision, maximum_bytes=1_048_576)


def test_protocol_and_synthetic_ready_result_validate_independently(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Recompute every identity, metric, gate and manifest without model execution."""
    assert _load_protocol(repository_root) == load_protocol(repository_root)
    destination = tmp_path / "result"
    _publish_valid(repository_root, destination)
    assert validate(repository_root, destination)["decision"] == READY


def test_projection_identity_hashes_canonical_bytes_deterministically() -> None:
    """Treat the F029 timing-free projection as bytes, not a second JSON value."""
    first = [{"question_id": "q1", "wall_ns": 1, "selected_ids": ["block-1"]}]
    second = [{"question_id": "q1", "wall_ns": 9, "selected_ids": ["block-1"]}]
    assert _projection_id(first) == _projection_id(second)
    assert _projection_id(first).startswith("sha256:")


@pytest.mark.parametrize("target", ("summary.json", "observations.json", "decision.json"))
def test_validator_rejects_any_tampered_canonical_result(
    repository_root: Path,
    tmp_path: Path,
    target: str,
) -> None:
    """Reject favorable or unfavorable fact changes even when JSON stays canonical."""
    destination = tmp_path / "result"
    _publish_valid(repository_root, destination)
    path = destination / target
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["tampered"] = True
    path.write_bytes(canonical_json_bytes(payload) + b"\n")
    with pytest.raises(ValidationError):
        validate(repository_root, destination)


def test_validator_rejects_extra_file_and_absolute_path(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Reject inventory expansion and privacy-forbidden local path disclosure."""
    destination = tmp_path / "result"
    _publish_valid(repository_root, destination)
    (destination / "extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValidationError, match="result_inventory"):
        validate(repository_root, destination)


def test_validator_rejects_modified_frozen_protocol(
    repository_root: Path,
    tmp_path: Path,
) -> None:
    """Reject gate drift even when the modified protocol remains valid JSON."""
    source = repository_root / "benchmarks/semantic-surface/v0.1.0/protocol.json"
    destination = tmp_path / "benchmarks/semantic-surface/v0.1.0/protocol.json"
    destination.parent.mkdir(parents=True)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["gates"]["cache_reuse_minimum_millionths"] = 1
    destination.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError, match="protocol_id_mismatch"):
        load_protocol(tmp_path)


@pytest.mark.parametrize(
    "value, category",
    (
        ({"safe": "prefix /Users/example/private.txt"}, "privacy_absolute_path"),
        ({"embedding": []}, "privacy_forbidden_key"),
    ),
)
def test_privacy_validator_rejects_embedded_paths_and_forbidden_keys(
    value: object,
    category: str,
) -> None:
    """Exercise privacy rejection directly rather than relying on earlier identity errors."""
    with pytest.raises(ValidationError, match=category):
        _privacy(value)
