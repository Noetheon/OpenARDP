"""Deterministic statistics and fail-closed F015 release-gate evaluation."""

from __future__ import annotations

import hashlib
import math
import statistics
from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime

from pydantic import JsonValue

from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.release import (
    Baseline,
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPhase,
    EvidenceMalformed,
    EvidenceStatus,
    GateCheck,
    MetricUnit,
    PlatformEvidence,
    ReleaseDecision,
    ReleaseGatePolicy,
    ReleaseStatus,
    StatisticalSummary,
    SuiteName,
    release_decision_id,
)

_BASE_ALLOWED_CLAIMS = ("evidence-preserving", "experimental-contracts", "local-first")
_GO_ONLY_CLAIMS = ("measured-parser-reuse", "three-platform-supported", "v0.1-release-ready")
_ALWAYS_PROHIBITED_CLAIMS = (
    "enterprise-performance",
    "third-party-reproduced",
    "universal-security",
)


def summarize_samples(
    values: Sequence[int | float],
    *,
    unit: MetricUnit,
    seed_id: str,
    resamples: int = 10_000,
) -> StatisticalSummary:
    """Summarize finite samples with deterministic percentile-bootstrap medians."""
    if not values:
        raise ValueError("at least one sample is required")
    if not 1 <= resamples <= 100_000:
        raise ValueError("resamples must be between 1 and 100000")
    normalized = tuple(float(value) for value in values)
    if any(not math.isfinite(value) or value < 0 for value in normalized):
        raise ValueError("samples must be finite and non-negative")
    median = statistics.median(normalized)
    deviations = tuple(abs(value - median) for value in normalized)
    medians: list[float] = []
    index_stream = _deterministic_indices(
        seed_id=seed_id,
        modulus=len(normalized),
        count=resamples * len(normalized),
    )
    for _ in range(resamples):
        sample = [normalized[next(index_stream)] for _ in normalized]
        medians.append(statistics.median(sample))
    medians.sort()
    lower = medians[_nearest_rank_index(len(medians), 0.025)]
    upper = medians[_nearest_rank_index(len(medians), 0.975)]
    return StatisticalSummary(
        count=len(normalized),
        median=median,
        median_absolute_deviation=statistics.median(deviations),
        confidence_lower=lower,
        confidence_upper=upper,
        unit=unit,
    )


def evaluate_release(
    *,
    policy: ReleaseGatePolicy,
    evidence: Sequence[PlatformEvidence],
    decision_at: datetime,
) -> ReleaseDecision:
    """Verify evidence and apply every frozen gate clause without a waiver path."""
    platform_ids = _validate_release_evidence(policy, evidence)
    first = evidence[0]
    checks: list[GateCheck] = []
    _append_evidence_completeness_checks(policy, evidence, platform_ids, checks)
    reference = _append_reference_check(evidence, checks)
    _append_timing_checks(policy, reference, checks)
    _append_ratio_check(
        policy,
        reference,
        checks,
        metric=BenchmarkMetric.CORRECTNESS,
        baselines=(Baseline.OPENARDP_RETRIEVAL, Baseline.OPENARDP_COMPILER),
        minimum=policy.minimum_correctness_ratio,
        check_id="correctness-threshold",
        success_reason="correctness-threshold-met",
        fail_reason="correctness-threshold-not-met",
    )
    _append_ratio_check(
        policy,
        reference,
        checks,
        metric=BenchmarkMetric.COVERAGE,
        baselines=(Baseline.OPENARDP_COMPILER,),
        minimum=policy.minimum_coverage_ratio,
        check_id="coverage-threshold",
        success_reason="coverage-threshold-met",
        fail_reason="coverage-threshold-not-met",
    )
    _append_bounded_context_check(policy, reference, checks)
    return _build_release_decision(
        policy=policy,
        evidence=evidence,
        first=first,
        checks=checks,
        decision_at=decision_at,
    )


def _validate_release_evidence(
    policy: ReleaseGatePolicy,
    evidence: Sequence[PlatformEvidence],
) -> tuple[str, ...]:
    """Validate exact policy/evidence identities before evaluating any gate."""
    policy.verify_identity()
    if not evidence:
        raise EvidenceMalformed("at least one platform evidence bundle is required")
    for item in evidence:
        item.verify_identity()
        for observation in item.observations:
            if canonical_sha256(observation.identity_projection) != observation.observation_id:
                raise EvidenceMalformed("benchmark observation identity mismatch")
            if (
                observation.protocol_id != item.protocol_id
                or observation.corpus_id != item.corpus_id
                or observation.configuration_id != item.configuration_id
                or observation.executable_id != item.source_tree_id
                or observation.lockfile_id != item.lockfile_id
                or observation.platform_id != item.environment.platform_id
                or observation.python_version != item.environment.python_version
                or observation.source_version_id == "sha256:" + "0" * 64
            ):
                raise EvidenceMalformed("benchmark observation input identity mismatch")
    platform_ids = tuple(item.environment.platform_id for item in evidence)
    if len(set(platform_ids)) != len(platform_ids):
        raise EvidenceMalformed("platform evidence identifiers must be unique")
    return platform_ids


def _append_evidence_completeness_checks(
    policy: ReleaseGatePolicy,
    evidence: Sequence[PlatformEvidence],
    platform_ids: tuple[str, ...],
    checks: list[GateCheck],
) -> None:
    """Append platform, identity, baseline and suite completeness checks."""
    first = evidence[0]
    evidence_ids = tuple(item.evidence_id for item in evidence)
    expected_platforms = set(policy.required_platforms)
    observed_platforms = set(platform_ids)
    _append_check(
        checks,
        check_id="platform-completeness",
        passed=observed_platforms == expected_platforms,
        success_reason="platforms-complete",
        fail_reason="platform-evidence-incomplete",
        evidence_ids=evidence_ids,
        observed=len(observed_platforms),
        expected=len(expected_platforms),
    )
    common_identity = all(
        (
            item.source_tree_id,
            item.protocol_id,
            item.corpus_id,
            item.configuration_id,
            item.lockfile_id,
        )
        == (
            first.source_tree_id,
            first.protocol_id,
            first.corpus_id,
            first.configuration_id,
            first.lockfile_id,
        )
        for item in evidence
    )
    _append_check(
        checks,
        check_id="evidence-identity-agreement",
        passed=common_identity,
        success_reason="evidence-identities-agree",
        fail_reason="evidence-identity-mismatch",
        evidence_ids=evidence_ids,
    )
    baselines_complete = all(
        set(item.baselines) == set(policy.required_baselines) for item in evidence
    )
    _append_check(
        checks,
        check_id="baseline-completeness",
        passed=baselines_complete,
        success_reason="baselines-complete",
        fail_reason="baseline-evidence-incomplete",
        evidence_ids=evidence_ids,
        observed=sum(set(item.baselines) == set(policy.required_baselines) for item in evidence),
        expected=len(evidence),
    )
    required_suites = set(policy.required_suites)
    _append_check(
        checks,
        check_id="suite-completeness",
        passed=all(_required_suites_pass(policy, item) for item in evidence),
        success_reason="suites-complete",
        fail_reason="mandatory-suite-failed",
        evidence_ids=evidence_ids,
        observed=sum(
            sum(suite.status is EvidenceStatus.PASSED for suite in item.suites) for item in evidence
        ),
        expected=len(evidence) * len(required_suites),
    )


def _append_reference_check(
    evidence: Sequence[PlatformEvidence],
    checks: list[GateCheck],
) -> PlatformEvidence | None:
    """Append reference-timing uniqueness and return the sole reference if present."""
    references = tuple(item for item in evidence if item.environment.reference_timing)
    reference = references[0] if len(references) == 1 else None
    _append_check(
        checks,
        check_id="reference-timing-uniqueness",
        passed=reference is not None,
        success_reason="reference-timing-present",
        fail_reason="reference-timing-missing",
        evidence_ids=tuple(item.evidence_id for item in references),
        observed=len(references),
        expected=1,
    )
    return reference


def _append_timing_checks(
    policy: ReleaseGatePolicy,
    reference: PlatformEvidence | None,
    checks: list[GateCheck],
) -> None:
    """Append sample, latency-value and warm-parser checks in fixed order."""
    raw_latency = (
        ()
        if reference is None
        else _observation_values(
            reference.observations,
            baseline=Baseline.RAW_REPARSE,
            metric=BenchmarkMetric.LATENCY,
            phase=BenchmarkPhase.RETRIEVAL,
        )
    )
    openardp_latency = (
        ()
        if reference is None
        else _observation_values(
            reference.observations,
            baseline=Baseline.OPENARDP_RETRIEVAL,
            metric=BenchmarkMetric.LATENCY,
            phase=BenchmarkPhase.RETRIEVAL,
        )
    )
    samples_complete = (
        reference is not None
        and len(raw_latency) >= policy.minimum_timing_samples
        and len(openardp_latency) >= policy.minimum_timing_samples
    )
    reference_ids = () if reference is None else (reference.evidence_id,)
    _append_check(
        checks,
        check_id="timing-sample-sufficiency",
        passed=samples_complete,
        success_reason="timing-samples-sufficient",
        fail_reason="timing-samples-insufficient",
        evidence_ids=reference_ids,
        observed=min(len(raw_latency), len(openardp_latency)),
        expected=policy.minimum_timing_samples,
    )
    observed_upper: float | None = None
    expected_lower: float | None = None
    if samples_complete and reference is not None:
        raw_summary = summarize_samples(
            raw_latency,
            unit=MetricUnit.NANOSECONDS,
            seed_id=canonical_sha256(
                {"evidence_id": reference.evidence_id, "group": "raw-reparse-latency"}
            ),
            resamples=policy.bootstrap_resamples,
        )
        openardp_summary = summarize_samples(
            openardp_latency,
            unit=MetricUnit.NANOSECONDS,
            seed_id=canonical_sha256(
                {"evidence_id": reference.evidence_id, "group": "openardp-retrieval-latency"}
            ),
            resamples=policy.bootstrap_resamples,
        )
        observed_upper = openardp_summary.confidence_upper
        expected_lower = raw_summary.confidence_lower
    _append_check(
        checks,
        check_id="raw-reparse-latency-value",
        passed=(
            observed_upper is not None
            and expected_lower is not None
            and observed_upper < expected_lower
        ),
        success_reason="raw-reparse-interval-exceeded",
        fail_reason="operational-value-not-demonstrated",
        evidence_ids=reference_ids,
        observed=observed_upper,
        expected=expected_lower,
    )
    _append_check(
        checks,
        check_id="warm-parser-avoidance",
        passed=reference is not None and _all_zero_parser_observations(reference.observations),
        success_reason="warm-parser-invocations-zero",
        fail_reason="warm-parser-reuse-not-demonstrated",
        evidence_ids=reference_ids,
        observed=(
            None if reference is None else _warm_parser_invocation_total(reference.observations)
        ),
        expected=0,
    )


def _append_ratio_check(
    policy: ReleaseGatePolicy,
    reference: PlatformEvidence | None,
    checks: list[GateCheck],
    *,
    metric: BenchmarkMetric,
    baselines: tuple[Baseline, ...],
    minimum: float,
    check_id: str,
    success_reason: str,
    fail_reason: str,
) -> None:
    """Append one exact ratio threshold and confidence-interval check."""
    values = (
        ()
        if reference is None
        else _ratio_values(reference.observations, metric=metric, baselines=baselines)
    )
    intervals = (
        {}
        if reference is None
        else summarize_case_ratios(
            reference.observations,
            metric=metric,
            baselines=baselines,
            resamples=policy.bootstrap_resamples,
            seed_id=reference.evidence_id,
        )
    )
    passed = (
        bool(values)
        and min(values) >= minimum
        and bool(intervals)
        and all(summary.confidence_lower >= minimum for summary in intervals.values())
    )
    _append_check(
        checks,
        check_id=check_id,
        passed=passed,
        success_reason=success_reason,
        fail_reason=fail_reason,
        evidence_ids=() if reference is None else (reference.evidence_id,),
        observed=min(values) if values else None,
        expected=minimum,
    )


def _append_bounded_context_check(
    policy: ReleaseGatePolicy,
    reference: PlatformEvidence | None,
    checks: list[GateCheck],
) -> None:
    """Append the selected-to-native context value check."""
    ratio = _selected_to_native_ratio(reference)
    _append_check(
        checks,
        check_id="bounded-context-value",
        passed=ratio is not None and ratio <= policy.maximum_selected_native_ratio,
        success_reason="bounded-context-value-demonstrated",
        fail_reason="bounded-context-value-not-demonstrated",
        evidence_ids=() if reference is None else (reference.evidence_id,),
        observed=ratio,
        expected=policy.maximum_selected_native_ratio,
    )


def _build_release_decision(
    *,
    policy: ReleaseGatePolicy,
    evidence: Sequence[PlatformEvidence],
    first: PlatformEvidence,
    checks: Sequence[GateCheck],
    decision_at: datetime,
) -> ReleaseDecision:
    """Build and self-identify the final fail-closed release decision."""
    blockers = tuple(item.reason for item in checks if not item.passed)
    status = ReleaseStatus.GO if not blockers else ReleaseStatus.NO_GO
    allowed_claims = tuple(
        sorted(_BASE_ALLOWED_CLAIMS + (_GO_ONLY_CLAIMS if status is ReleaseStatus.GO else ()))
    )
    prohibited_claims = tuple(
        sorted(_ALWAYS_PROHIBITED_CLAIMS + (() if status is ReleaseStatus.GO else _GO_ONLY_CLAIMS))
    )
    required_suites = set(policy.required_suites)
    supported_platforms = tuple(
        sorted(
            item.environment.platform_id
            for item in evidence
            if set(suite.name for suite in item.suites) == required_suites
            and all(suite.status is EvidenceStatus.PASSED for suite in item.suites)
        )
    )
    provisional = ReleaseDecision(
        decision_id="sha256:" + "0" * 64,
        decision_at=decision_at,
        source_tree_id=first.source_tree_id,
        policy_id=policy.policy_id,
        protocol_id=first.protocol_id,
        corpus_id=first.corpus_id,
        configuration_id=first.configuration_id,
        lockfile_id=first.lockfile_id,
        status=status,
        checks=tuple(checks),
        blockers=blockers,
        allowed_claims=allowed_claims,
        prohibited_claims=prohibited_claims,
        supported_platforms=supported_platforms,
    )
    return provisional.model_copy(
        update={"decision_id": release_decision_id(provisional.identity_projection)}
    )


def _required_suites_pass(policy: ReleaseGatePolicy, evidence: PlatformEvidence) -> bool:
    """Verify exact policy check registries and bound evidence references."""
    by_name = {suite.name: suite for suite in evidence.suites}
    if set(by_name) != set(policy.required_suites):
        return False
    observation_ids = {item.observation_id for item in evidence.observations}
    for name in policy.required_suites:
        suite = by_name[name]
        expected = set(policy.required_checks[name])
        if (
            suite.status is not EvidenceStatus.PASSED
            or {check.check_id for check in suite.checks} != expected
        ):
            return False
        for check in suite.checks:
            if check.status is not EvidenceStatus.PASSED or not check.evidence_ids:
                return False
            if name in {SuiteName.PERFORMANCE, SuiteName.CORRECTNESS} and not set(
                check.evidence_ids
            ).issubset(observation_ids):
                return False
    return True


def render_release_report(decision: ReleaseDecision) -> bytes:
    """Render a deterministic body-free human report from a verified decision."""
    decision.verify_identity()
    lines = [
        "# OpenARDP v0.1 Release Gate",
        "",
        f"**Decision**: `{decision.status.value}`",
        f"**Candidate**: `{decision.candidate_version}`",
        f"**Decision ID**: `{decision.decision_id}`",
        f"**Source tree**: `{decision.source_tree_id}`",
        f"**Policy**: `{decision.policy_id}`",
        "",
        "## Evidence registry",
        "",
        "- `release-evidence.json`: policy, every platform bundle and every raw observation.",
        "- `platform-evidence.json`: immutable per-sample benchmark and suite evidence.",
        "- `artifacts.json` and `checksums.json`: candidate member inventories and digests.",
        "- `sbom.cdx.json`: normalized dependency, license and graph inventory.",
        "",
        "## Gate checks",
        "",
    ]
    for check in decision.checks:
        marker = "PASS" if check.passed else "FAIL"
        comparison = (
            ""
            if check.observed is None and check.expected is None
            else (
                f"; observed `{_format_comparison(check.observed)}`, "
                f"expected `{_format_comparison(check.expected)}`"
            )
        )
        lines.append(f"- `{check.check_id}`: **{marker}** (`{check.reason}`{comparison})")
    lines.extend(
        [
            "",
            "## Supported platform evidence",
            "",
            *(f"- `{platform}`" for platform in decision.supported_platforms),
            "" if decision.supported_platforms else "- None established by this decision.",
            "",
            "## Residual limits",
            "",
            "- Results apply only to the committed synthetic corpus and declared environments.",
            "- Integrity and passing controls do not prove universal security or license legality.",
            "- A GO is release-ready evidence, not publication or third-party reproduction.",
            "",
            "## Install, upgrade and rollback",
            "",
            "- Install only the checksum-verified `0.1.0rc1` wheel in an offline "
            "Python 3.12 environment.",
            "- Back up a prior workspace before migration; never edit migration history manually.",
            "- Restore the verified pre-upgrade backup to a fresh disjoint destination "
            "for rollback.",
            "- A `NO-GO` decision prohibits release publication regardless of successful "
            "local drills.",
            "",
            "## Blockers",
            "",
            *(
                [f"- `{blocker}`" for blocker in decision.blockers]
                if decision.blockers
                else ["- None."]
            ),
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_claim_map(decision: ReleaseDecision) -> dict[str, JsonValue]:
    """Return the deterministic claim projection used by README validation."""
    decision.verify_identity()
    return {
        "schema_version": "0.1.0",
        "decision_id": decision.decision_id,
        "allowed": list(decision.allowed_claims),
        "prohibited": list(decision.prohibited_claims),
    }


def summarize_case_ratios(
    observations: Iterable[BenchmarkObservation],
    *,
    metric: BenchmarkMetric,
    baselines: tuple[Baseline, ...],
    resamples: int,
    seed_id: str,
) -> dict[str, StatisticalSummary]:
    """Return deterministic ratio intervals independently for every judged case."""
    grouped: dict[str, list[float]] = {}
    for item in observations:
        if (
            item.metric is metric
            and item.baseline in baselines
            and item.status is EvidenceStatus.PASSED
            and item.value is not None
        ):
            grouped.setdefault(item.case_id, []).append(float(item.value))
    return {
        case_id: summarize_samples(
            values,
            unit=MetricUnit.RATIO,
            seed_id=canonical_sha256(
                {"seed_id": seed_id, "case_id": case_id, "metric": metric.value}
            ),
            resamples=resamples,
        )
        for case_id, values in sorted(grouped.items())
    }


def score_ranked_evidence(
    expected_ids: Sequence[str], actual_ids: Sequence[str]
) -> tuple[float, float, float]:
    """Return precision, recall and reciprocal rank for exact evidence identities."""
    if not expected_ids or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("expected evidence identities must be non-empty and unique")
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError("actual evidence identities must be unique")
    expected = set(expected_ids)
    relevant = sum(item in expected for item in actual_ids)
    precision = relevant / len(actual_ids) if actual_ids else 0.0
    recall = relevant / len(expected)
    reciprocal_rank = next(
        (1.0 / rank for rank, item in enumerate(actual_ids, start=1) if item in expected),
        0.0,
    )
    return precision, recall, reciprocal_rank


def score_anchor_matches(expected: Sequence[str], actual: Sequence[str]) -> float:
    """Return exact ordered-anchor coverage without fuzzy substitution."""
    if not expected:
        raise ValueError("expected anchors must be non-empty")
    return sum(
        index < len(actual) and actual[index] == anchor for index, anchor in enumerate(expected)
    ) / len(expected)


def score_budget_coverage(
    required_ids: Sequence[str],
    selected_ids: Sequence[str],
    *,
    selected_bytes: int,
    native_bytes: int,
    maximum_bytes: int,
) -> tuple[float, float]:
    """Return required-evidence coverage and selected/native byte ratio."""
    if not required_ids or len(set(required_ids)) != len(required_ids):
        raise ValueError("required evidence identities must be non-empty and unique")
    if selected_bytes < 0 or native_bytes <= 0 or maximum_bytes < 1:
        raise ValueError("byte budgets must be positive and finite")
    if selected_bytes > maximum_bytes:
        return 0.0, selected_bytes / native_bytes
    coverage = len(set(required_ids) & set(selected_ids)) / len(set(required_ids))
    return coverage, selected_bytes / native_bytes


def _append_check(
    checks: list[GateCheck],
    *,
    check_id: str,
    passed: bool,
    success_reason: str,
    fail_reason: str,
    evidence_ids: tuple[str, ...],
    observed: int | float | None = None,
    expected: int | float | None = None,
) -> None:
    checks.append(
        GateCheck(
            check_id=check_id,
            passed=passed,
            reason=success_reason if passed else fail_reason,
            observed=observed,
            expected=expected,
            evidence_ids=evidence_ids,
        )
    )


def _format_comparison(value: int | float | None) -> str:
    if value is None:
        return "null"
    return canonical_json_bytes(value).decode("ascii")


def _observation_values(
    observations: Iterable[BenchmarkObservation],
    *,
    baseline: Baseline,
    metric: BenchmarkMetric,
    phase: BenchmarkPhase,
) -> tuple[int | float, ...]:
    return tuple(
        item.value
        for item in observations
        if item.baseline is baseline
        and item.metric is metric
        and item.phase is phase
        and item.status is EvidenceStatus.PASSED
        and item.value is not None
    )


def _ratio_values(
    observations: Iterable[BenchmarkObservation],
    *,
    metric: BenchmarkMetric,
    baselines: tuple[Baseline, ...],
) -> tuple[float, ...]:
    return tuple(
        float(item.value)
        for item in observations
        if item.baseline in baselines
        and item.metric is metric
        and item.status is EvidenceStatus.PASSED
        and item.value is not None
    )


def _all_zero_parser_observations(observations: Iterable[BenchmarkObservation]) -> bool:
    expected = {Baseline.OPENARDP_RETRIEVAL, Baseline.OPENARDP_COMPILER}
    observed: set[Baseline] = set()
    for item in observations:
        if (
            item.baseline in expected
            and item.metric is BenchmarkMetric.PARSER_INVOCATIONS
            and item.phase is BenchmarkPhase.WARM
            and item.status is EvidenceStatus.PASSED
        ):
            observed.add(item.baseline)
            if item.value != 0:
                return False
    return observed == expected


def _warm_parser_invocation_total(
    observations: Iterable[BenchmarkObservation],
) -> int | None:
    values = tuple(
        int(item.value)
        for item in observations
        if item.baseline in {Baseline.OPENARDP_RETRIEVAL, Baseline.OPENARDP_COMPILER}
        and item.metric is BenchmarkMetric.PARSER_INVOCATIONS
        and item.phase is BenchmarkPhase.WARM
        and item.status is EvidenceStatus.PASSED
        and item.value is not None
    )
    return sum(values) if values else None


def _selected_to_native_ratio(reference: PlatformEvidence | None) -> float | None:
    if reference is None:
        return None
    selected = _observation_values(
        reference.observations,
        baseline=Baseline.OPENARDP_COMPILER,
        metric=BenchmarkMetric.SELECTED_BYTES,
        phase=BenchmarkPhase.COMPILE,
    )
    native = _observation_values(
        reference.observations,
        baseline=Baseline.NATIVE_REUSE,
        metric=BenchmarkMetric.NATIVE_BYTES,
        phase=BenchmarkPhase.WARM,
    )
    if not selected or not native or statistics.median(native) <= 0:
        return None
    return statistics.median(selected) / statistics.median(native)


def _deterministic_indices(*, seed_id: str, modulus: int, count: int) -> Iterator[int]:
    if modulus < 1:
        raise ValueError("modulus must be positive")
    seed = seed_id.encode("ascii", errors="strict")
    produced = 0
    counter = 0
    while produced < count:
        block = hashlib.sha256(seed + counter.to_bytes(8, "big")).digest()
        counter += 1
        for offset in range(0, len(block), 8):
            if produced >= count:
                break
            yield int.from_bytes(block[offset : offset + 8], "big") % modulus
            produced += 1


def _nearest_rank_index(length: int, quantile: float) -> int:
    rank = max(1, math.ceil(quantile * length))
    return min(length - 1, rank - 1)
