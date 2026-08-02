"""Deterministic F021 benchmark contract and policy tests."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import StatusMode
from scripts.freshness_benchmark import (
    FreshnessCounters,
    FreshnessObservation,
    decide_freshness,
    load_freshness_protocol,
    make_observation,
    render_report,
    summarize_observations,
)

ENVIRONMENT_ID = "sha256:" + "a" * 64


def _observations(root: Path) -> tuple[FreshnessObservation, ...]:
    protocol, _ = load_freshness_protocol(root)
    result: list[FreshnessObservation] = []
    for profile in ("reference", "scale"):
        blocks = protocol.corpus.profiles[profile]
        for mode in protocol.modes:
            for repetition in range(protocol.repetitions):
                counters = (
                    FreshnessCounters(
                        aggregate_loads=0,
                        block_object_verifications=0,
                        parser_invocations=0,
                        source_inspections=1,
                        verifier_invocations=0,
                    )
                    if mode is StatusMode.HEAD
                    else FreshnessCounters(
                        aggregate_loads=1,
                        block_object_verifications=blocks,
                        parser_invocations=0,
                        source_inspections=1,
                        verifier_invocations=1,
                    )
                )
                base = 10_000_000 if mode is StatusMode.HEAD else blocks * 100_000
                result.append(
                    make_observation(
                        environment_id=ENVIRONMENT_ID,
                        profile=profile,
                        mode=mode.value,
                        repetition=repetition,
                        block_count=blocks,
                        source_bytes=blocks * 100,
                        elapsed_ns=base + repetition,
                        freshness="CURRENT",
                        integrity_coverage=("HEAD" if mode is StatusMode.HEAD else "FULL"),
                        counters=counters.model_dump(mode="json"),
                    )
                )
    return tuple(result)


def test_benchmark_recomputes_exact_groups_and_passing_policy() -> None:
    """Derive all four timing groups and operation checks from retained observations."""
    root = Path.cwd()
    protocol, _ = load_freshness_protocol(root)
    observations = _observations(root)

    summaries = summarize_observations(protocol, observations)
    decision = decide_freshness(protocol, observations, summaries)

    assert len(observations) == 28
    assert len(summaries) == 4
    assert all(item.sample_count == 7 for item in summaries)
    assert decision.outcome == "PASS"
    assert decision.improvement_factors["reference"] > 100
    assert b"arbitrary CAS tamper detection" in render_report(protocol, summaries, decision)


def test_benchmark_identity_and_counter_tampering_fail_closed() -> None:
    """Reject changed observation facts and make unfavorable counter evidence fail policy."""
    root = Path.cwd()
    protocol, _ = load_freshness_protocol(root)
    observations = list(_observations(root))
    raw = observations[0].model_dump(mode="json")
    raw["elapsed_ns"] = int(raw["elapsed_ns"]) + 1
    try:
        FreshnessObservation.model_validate_json(canonical_json_bytes(raw))
    except ValidationError as error:
        assert "identity mismatch" in str(error)
    else:
        raise AssertionError("changed observation identity was accepted")

    first = observations[0]
    observations[0] = make_observation(
        **{
            **first.model_dump(mode="json", exclude={"observation_id", "counters"}),
            "counters": {
                **first.counters.model_dump(mode="json"),
                "aggregate_loads": 1,
            },
        }
    )
    summaries = summarize_observations(protocol, observations)
    assert decide_freshness(protocol, observations, summaries).outcome == "FAIL"
