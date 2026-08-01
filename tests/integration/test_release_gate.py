"""End-to-end deterministic release-gate evaluation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openardp.domain.release import (
    Baseline,
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    EnvironmentProfile,
    EvidenceCheck,
    EvidenceMalformed,
    EvidenceStatus,
    EvidenceSuite,
    MetricUnit,
    PlatformEvidence,
    ReleaseGatePolicy,
    ReleaseStatus,
    SuiteName,
    benchmark_observation_id,
    platform_evidence_id,
    release_policy_id,
)
from openardp.services.release_gate import (
    build_claim_map,
    evaluate_release,
    render_release_report,
    summarize_samples,
)

SHA = "sha256:" + "2" * 64
PLATFORMS = ("linux-x86_64", "macos-arm64", "windows-x86_64")


def _policy() -> ReleaseGatePolicy:
    provisional = ReleaseGatePolicy(
        policy_id=SHA,
        required_platforms=PLATFORMS,
        required_baselines=tuple(Baseline),
        required_suites=tuple(SuiteName),
        required_checks={name: (f"{name.value}-complete",) for name in SuiteName},
        bootstrap_resamples=1_000,
    )
    return provisional.model_copy(
        update={"policy_id": release_policy_id(provisional.identity_projection)}
    )


def _suite(name: SuiteName, observations: tuple[BenchmarkObservation, ...]) -> EvidenceSuite:
    evidence_id = observations[0].observation_id if observations else SHA
    return EvidenceSuite(
        name=name,
        status=EvidenceStatus.PASSED,
        expected_count=1,
        observed_count=1,
        checks=(
            EvidenceCheck(
                check_id=f"{name.value}-complete",
                status=EvidenceStatus.PASSED,
                evidence_ids=(evidence_id,),
            ),
        ),
    )


def _observation(
    baseline: Baseline,
    metric: BenchmarkMetric,
    unit: MetricUnit,
    value: int | float,
    repetition: int,
    phase: BenchmarkPhase,
) -> BenchmarkObservation:
    provisional = BenchmarkObservation.model_construct(
        observation_id=SHA,
        baseline=baseline,
        case_id="docx-evidence",
        phase=phase,
        repetition=repetition,
        metric=metric,
        unit=unit,
        value=value,
        status=EvidenceStatus.PASSED,
    )
    return provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )


def _reference_observations() -> tuple[BenchmarkObservation, ...]:
    observations: list[BenchmarkObservation] = []
    for repetition in range(7):
        observations.extend(
            (
                _observation(
                    Baseline.RAW_REPARSE,
                    BenchmarkMetric.LATENCY,
                    MetricUnit.NANOSECONDS,
                    1_000 + repetition,
                    repetition,
                    BenchmarkPhase.RETRIEVAL,
                ),
                _observation(
                    Baseline.OPENARDP_RETRIEVAL,
                    BenchmarkMetric.LATENCY,
                    MetricUnit.NANOSECONDS,
                    100 + repetition,
                    repetition,
                    BenchmarkPhase.RETRIEVAL,
                ),
            )
        )
    observations.extend(
        (
            _observation(
                Baseline.OPENARDP_RETRIEVAL,
                BenchmarkMetric.PARSER_INVOCATIONS,
                MetricUnit.COUNT,
                0,
                0,
                BenchmarkPhase.WARM,
            ),
            _observation(
                Baseline.OPENARDP_COMPILER,
                BenchmarkMetric.PARSER_INVOCATIONS,
                MetricUnit.COUNT,
                0,
                0,
                BenchmarkPhase.WARM,
            ),
            _observation(
                Baseline.OPENARDP_RETRIEVAL,
                BenchmarkMetric.CORRECTNESS,
                MetricUnit.RATIO,
                1.0,
                0,
                BenchmarkPhase.RETRIEVAL,
            ),
            _observation(
                Baseline.OPENARDP_COMPILER,
                BenchmarkMetric.CORRECTNESS,
                MetricUnit.RATIO,
                1.0,
                0,
                BenchmarkPhase.COMPILE,
            ),
            _observation(
                Baseline.OPENARDP_COMPILER,
                BenchmarkMetric.COVERAGE,
                MetricUnit.RATIO,
                1.0,
                0,
                BenchmarkPhase.COMPILE,
            ),
            _observation(
                Baseline.OPENARDP_COMPILER,
                BenchmarkMetric.SELECTED_BYTES,
                MetricUnit.BYTES,
                400,
                0,
                BenchmarkPhase.COMPILE,
            ),
            _observation(
                Baseline.NATIVE_REUSE,
                BenchmarkMetric.NATIVE_BYTES,
                MetricUnit.BYTES,
                1_000,
                0,
                BenchmarkPhase.WARM,
            ),
        )
    )
    return tuple(observations)


def _evidence(platform: str, *, reference: bool, all_baselines: bool = True) -> PlatformEvidence:
    os_family = "macos" if platform.startswith("macos") else platform.split("-", maxsplit=1)[0]
    observations = tuple(_bind_observation(item, platform) for item in _reference_observations())
    provisional = PlatformEvidence(
        evidence_id=SHA,
        source_tree_id=SHA,
        protocol_id=SHA,
        corpus_id=SHA,
        configuration_id=SHA,
        lockfile_id=SHA,
        environment=EnvironmentProfile(
            platform_id=platform,
            os_family=os_family,  # type: ignore[arg-type]
            architecture="arm64" if platform.startswith("macos") else "x86_64",
            python_version="3.12.11",
            logical_cpu_bucket="5-8",
            memory_gib_bucket="16-31",
            timer_resolution_ns=1,
            reference_timing=reference,
        ),
        baselines=tuple(Baseline) if all_baselines else (Baseline.RAW_REPARSE,),
        observations=observations,
        suites=tuple(_suite(name, observations) for name in SuiteName),
    )
    return provisional.model_copy(
        update={"evidence_id": platform_evidence_id(provisional.identity_projection)}
    )


def _bind_observation(observation: BenchmarkObservation, platform: str) -> BenchmarkObservation:
    provisional = observation.model_copy(
        update={
            "observation_id": SHA,
            "source_version_id": SHA,
            "protocol_id": SHA,
            "corpus_id": SHA,
            "configuration_id": SHA,
            "executable_id": SHA,
            "lockfile_id": SHA,
            "platform_id": platform,
            "python_version": "3.12.11",
        }
    )
    return provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )


def test_bootstrap_summary_is_byte_reproducible() -> None:
    """Fixed samples and seed always produce one exact interval."""
    first = summarize_samples(
        (1, 2, 3, 4, 5, 6, 7),
        unit=MetricUnit.NANOSECONDS,
        seed_id=SHA,
        resamples=1_000,
    )
    second = summarize_samples(
        (1, 2, 3, 4, 5, 6, 7),
        unit=MetricUnit.NANOSECONDS,
        seed_id=SHA,
        resamples=1_000,
    )
    assert first == second
    assert first.median == 4
    assert first.confidence_lower <= 4 <= first.confidence_upper


def test_complete_evidence_produces_go_and_consistent_projections() -> None:
    """All conjunctive clauses can produce GO without an override."""
    decision = evaluate_release(
        policy=_policy(),
        evidence=(
            _evidence("linux-x86_64", reference=False),
            _evidence("macos-arm64", reference=True),
            _evidence("windows-x86_64", reference=False),
        ),
        decision_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert decision.status is ReleaseStatus.GO
    assert decision.blockers == ()
    report = render_release_report(decision)
    assert b"**Decision**: `GO`" in report
    assert report.endswith(b"\n")
    assert not report.endswith(b"\n\n")
    assert "v0.1-release-ready" in build_claim_map(decision)["allowed"]
    assert tuple(check.check_id for check in decision.checks) == (
        "platform-completeness",
        "evidence-identity-agreement",
        "baseline-completeness",
        "suite-completeness",
        "reference-timing-uniqueness",
        "timing-sample-sufficiency",
        "raw-reparse-latency-value",
        "warm-parser-avoidance",
        "correctness-threshold",
        "coverage-threshold",
        "bounded-context-value",
    )


def test_duplicate_platform_evidence_fails_before_gate_checks() -> None:
    """Keep evidence validation precedence ahead of release policy evaluation."""
    repeated = _evidence("macos-arm64", reference=True)
    with pytest.raises(EvidenceMalformed, match="identifiers must be unique"):
        evaluate_release(
            policy=_policy(),
            evidence=(repeated, repeated),
            decision_at=datetime(2026, 8, 1, tzinfo=UTC),
        )


def test_missing_platform_and_baseline_produce_no_go() -> None:
    """Incomplete comparisons cannot be waived by otherwise passing suites."""
    decision = evaluate_release(
        policy=_policy(),
        evidence=(
            _evidence("linux-x86_64", reference=True, all_baselines=False),
            _evidence("macos-arm64", reference=False),
        ),
        decision_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert decision.status is ReleaseStatus.NO_GO
    assert "platform-evidence-incomplete" in decision.blockers
    assert "baseline-evidence-incomplete" in decision.blockers
    assert "v0.1-release-ready" in decision.prohibited_claims


def test_unbound_or_unregistered_suite_pass_cannot_satisfy_policy() -> None:
    """Reject caller-asserted pass records without exact IDs and evidence bindings."""
    evidence = _evidence("macos-arm64", reference=True)
    security = next(item for item in evidence.suites if item.name is SuiteName.SECURITY)
    forged = security.model_copy(
        update={
            "checks": (
                EvidenceCheck(
                    check_id="security-complete",
                    status=EvidenceStatus.PASSED,
                    evidence_ids=(),
                ),
            )
        }
    )
    provisional = evidence.model_copy(
        update={
            "evidence_id": SHA,
            "suites": tuple(
                forged if item.name is SuiteName.SECURITY else item for item in evidence.suites
            ),
        }
    )
    tampered = provisional.model_copy(
        update={"evidence_id": platform_evidence_id(provisional.identity_projection)}
    )
    decision = evaluate_release(
        policy=_policy(),
        evidence=(
            _evidence("linux-x86_64", reference=False),
            tampered,
            _evidence("windows-x86_64", reference=False),
        ),
        decision_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert decision.status is ReleaseStatus.NO_GO
    assert "mandatory-suite-failed" in decision.blockers
