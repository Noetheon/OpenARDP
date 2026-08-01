"""Pure release-evidence identities, statistics and gate invariants."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from openardp.domain.identity import canonical_sha256
from openardp.domain.release import (
    Baseline,
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    EnvironmentProfile,
    EvidenceCheck,
    EvidenceStatus,
    EvidenceSuite,
    GateCheck,
    MetricUnit,
    PlatformEvidence,
    ReleaseDecision,
    ReleaseGatePolicy,
    ReleaseStatus,
    SuiteName,
    benchmark_observation_id,
)

SHA = "sha256:" + "1" * 64


def _environment() -> EnvironmentProfile:
    return EnvironmentProfile(
        platform_id="macos-arm64",
        os_family="macos",
        architecture="arm64",
        python_version="3.12.11",
        logical_cpu_bucket="9-16",
        memory_gib_bucket="16-31",
        timer_resolution_ns=1,
        reference_timing=True,
    )


def test_observation_rejects_unit_drift_and_non_passed_values() -> None:
    """Metric units and terminal value semantics are closed."""
    with pytest.raises(ValidationError, match="metric unit"):
        BenchmarkObservation(
            observation_id=SHA,
            baseline=Baseline.RAW_REPARSE,
            case_id="docx-1",
            phase=BenchmarkPhase.COLD,
            repetition=0,
            metric=BenchmarkMetric.LATENCY,
            unit=MetricUnit.BYTES,
            value=1,
            status=EvidenceStatus.PASSED,
        )
    with pytest.raises(ValidationError, match="reason and no value"):
        BenchmarkObservation(
            observation_id=SHA,
            baseline=Baseline.RAW_REPARSE,
            case_id="docx-1",
            phase=BenchmarkPhase.COLD,
            repetition=0,
            metric=BenchmarkMetric.LATENCY,
            unit=MetricUnit.NANOSECONDS,
            value=1,
            status=EvidenceStatus.UNAVAILABLE,
            reason="provider-unavailable",
        )


def test_suite_status_is_recomputed_from_complete_checks() -> None:
    """A declared pass cannot hide a missing or failed control."""
    failed = EvidenceCheck(
        check_id="control-1",
        status=EvidenceStatus.FAILED,
        reason="control-failed",
    )
    with pytest.raises(ValidationError, match="suite status"):
        EvidenceSuite(
            name=SuiteName.SECURITY,
            status=EvidenceStatus.PASSED,
            expected_count=1,
            observed_count=1,
            checks=(failed,),
        )


def test_policy_requires_every_fair_baseline() -> None:
    """A benchmark policy cannot omit an unfavorable comparator."""
    payload = {
        "schema_version": "0.1.0",
        "policy_version": "0.1.0",
        "required_platforms": ("macos-arm64",),
        "required_baselines": (Baseline.RAW_REPARSE,),
        "required_suites": (SuiteName.PERFORMANCE,),
        "required_checks": {SuiteName.PERFORMANCE: ("performance-complete",)},
        "minimum_timing_samples": 7,
        "bootstrap_resamples": 10_000,
        "minimum_correctness_ratio": 1.0,
        "minimum_coverage_ratio": 1.0,
        "maximum_selected_native_ratio": 0.5,
        "maximum_vulnerability_age_days": 30,
    }
    with pytest.raises(ValidationError, match="all five baselines"):
        ReleaseGatePolicy(policy_id=SHA, **payload)


def test_platform_evidence_rejects_duplicate_observation_identity() -> None:
    """Duplicate samples cannot inflate confidence."""
    provisional = BenchmarkObservation.model_construct(
        observation_id=SHA,
        baseline=Baseline.RAW_REPARSE,
        case_id="docx-1",
        phase=BenchmarkPhase.COLD,
        repetition=0,
        metric=BenchmarkMetric.LATENCY,
        unit=MetricUnit.NANOSECONDS,
        value=1,
        status=EvidenceStatus.PASSED,
    )
    observation = provisional.model_copy(
        update={"observation_id": benchmark_observation_id(provisional.identity_projection)}
    )
    with pytest.raises(ValidationError, match="observation keys"):
        PlatformEvidence(
            evidence_id=SHA,
            source_tree_id=SHA,
            protocol_id=SHA,
            corpus_id=SHA,
            configuration_id=SHA,
            lockfile_id=SHA,
            environment=_environment(),
            baselines=tuple(Baseline),
            observations=(observation, observation),
            suites=(),
        )


def test_no_go_status_is_derived_from_exact_failed_checks() -> None:
    """No narrative or override can convert a failed check into GO."""
    checks = (
        GateCheck(check_id="platforms", passed=True, reason="platforms-complete"),
        GateCheck(check_id="timing", passed=False, reason="reference-timing-missing"),
    )
    payload = {
        "schema_version": "0.1.0",
        "candidate_version": "0.1.0rc1",
        "source_tree_id": SHA,
        "policy_id": SHA,
        "protocol_id": SHA,
        "corpus_id": SHA,
        "configuration_id": SHA,
        "lockfile_id": SHA,
        "status": ReleaseStatus.NO_GO,
        "checks": checks,
        "blockers": ("reference-timing-missing",),
        "allowed_claims": ("local-first",),
        "prohibited_claims": ("release-ready",),
        "supported_platforms": ("macos-arm64",),
    }
    provisional = ReleaseDecision(
        decision_id=SHA,
        decision_at=datetime(2026, 8, 1, tzinfo=UTC),
        **payload,
    )
    decision_payload = {
        **provisional.model_dump(mode="json"),
        "decision_id": canonical_sha256(provisional.identity_projection),
    }
    decision = ReleaseDecision.model_validate_json(
        json.dumps(decision_payload, separators=(",", ":"))
    )
    decision.verify_identity()
    with pytest.raises(ValidationError, match="status does not match blockers"):
        ReleaseDecision.model_validate_json(
            json.dumps(
                {**decision.model_dump(mode="json"), "status": ReleaseStatus.GO.value},
                separators=(",", ":"),
            )
        )
