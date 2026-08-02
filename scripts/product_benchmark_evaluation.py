"""Statistics and value-policy evaluation for the F020 maintainer benchmark."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import cast

from pydantic import JsonValue

from openardp.adapters.product_benchmarks import BenchmarkInputs
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.product_benchmark import (
    UNBOUND_ID,
    BenchmarkMetric,
    BenchmarkObservation,
    CheckStatus,
    MetricSummary,
    MetricUnit,
    ObservationStatus,
    ValueCheck,
    ValueDecision,
    ValueOutcome,
)


def _nearest_rank(values: Sequence[int], probability: float) -> int:
    if not values:
        raise ValueError("percentile requires values")
    index = max(0, math.ceil(probability * len(values)) - 1)
    return sorted(values)[index]


def _integer_median(values: Sequence[int]) -> int:
    if not values:
        raise ValueError("median requires values")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def summarize_timing(
    observations: Sequence[BenchmarkObservation],
    *,
    minimum_samples: int,
    bootstrap_resamples: int,
) -> MetricSummary:
    """Summarize one homogeneous retained timing group deterministically."""
    if minimum_samples < 1 or bootstrap_resamples < 1:
        raise ValueError("summary bounds must be positive")
    if len(observations) < minimum_samples:
        raise ValueError("insufficient timing samples")
    first = observations[0]
    group = (
        first.protocol_id,
        first.corpus_id,
        first.policy_id,
        first.environment_id,
        first.profile,
        first.workload_id,
        first.treatment,
        first.phase,
        first.metric,
        first.unit,
    )
    if first.metric not in {BenchmarkMetric.LATENCY, BenchmarkMetric.CPU_TIME}:
        raise ValueError("timing summary requires latency or CPU time")
    if first.unit is not MetricUnit.NANOSECONDS:
        raise ValueError("timing observations must use nanoseconds")
    if any(
        (
            item.protocol_id,
            item.corpus_id,
            item.policy_id,
            item.environment_id,
            item.profile,
            item.workload_id,
            item.treatment,
            item.phase,
            item.metric,
            item.unit,
        )
        != group
        for item in observations
    ):
        raise ValueError("timing observations are not homogeneous")
    if any(item.status is not ObservationStatus.PASSED for item in observations):
        raise ValueError("timing summary cannot hide non-passed observations")
    ordered = tuple(sorted(observations, key=lambda item: item.repetition))
    repetitions = tuple(item.repetition for item in ordered)
    if repetitions != tuple(sorted(set(repetitions))):
        raise ValueError("timing repetitions must be unique")
    identifiers = tuple(item.observation_id for item in ordered)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("timing observation identities must be unique")
    values = tuple(cast(int, item.value) for item in ordered)
    median = _integer_median(values)
    deviations = tuple(abs(item - median) for item in values)
    seed = int(canonical_sha256(list(identifiers)).removeprefix("sha256:")[:16], 16)
    generator = random.Random(seed)  # noqa: S311 - deterministic statistics, not security
    bootstrap = []
    for _ in range(bootstrap_resamples):
        bootstrap.append(
            _integer_median(tuple(generator.choice(values) for _ in range(len(values))))
        )
    projection: dict[str, JsonValue] = {
        "metric": first.metric.value,
        "unit": first.unit.value,
        "profile": first.profile.value,
        "workload_id": first.workload_id,
        "treatment": first.treatment.value,
        "phase": first.phase.value,
        "sample_count": len(values),
        "p50": median,
        "p95": _nearest_rank(values, 0.95),
        "median_absolute_deviation": _integer_median(deviations),
        "confidence_low": _nearest_rank(bootstrap, 0.025),
        "confidence_high": _nearest_rank(bootstrap, 0.975),
        "observation_ids": list(identifiers),
    }
    identified: dict[str, JsonValue] = {
        **projection,
        "summary_id": canonical_sha256(projection),
    }
    return MetricSummary.model_validate_json(canonical_json_bytes(identified))


def _number(metrics: Mapping[str, object], name: str) -> int | float | None:
    value = metrics.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"metric {name} must be numeric or null")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"metric {name} must be finite and non-negative")
    return value


def _check(
    check_id: str,
    *,
    passed: bool,
    expected: JsonValue,
    observed: JsonValue,
    reason: str,
) -> ValueCheck:
    return ValueCheck(
        check_id=check_id,
        status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
        reason_code=None if passed else reason,
        expected=expected,
        observed=observed,
    )


def decide_value(inputs: BenchmarkInputs, metrics: Mapping[str, object]) -> ValueDecision:
    """Apply the frozen hard and conditional thresholds without a waiver path."""
    hard = inputs.policy.hard_failures
    unconditional = inputs.policy.required_for_unconditional
    checks: list[ValueCheck] = []
    hard_reasons: list[str] = []
    conditional_reasons: list[str] = []

    hard_specs = (
        (
            "anchor-correctness",
            "anchor_correctness",
            hard.minimum_anchor_correctness,
            "anchor-correctness-failed",
        ),
        (
            "context-coverage",
            "context_coverage",
            hard.minimum_context_coverage,
            "context-coverage-failed",
        ),
        ("precision", "precision", hard.minimum_precision, "precision-failed"),
        ("recall", "recall", hard.minimum_recall, "recall-failed"),
        ("replay", "replay_match", hard.minimum_replay_match, "replay-failed"),
    )
    for check_id, key, threshold, reason in hard_specs:
        observed = _number(metrics, key)
        passed = observed is not None and observed >= threshold
        checks.append(
            _check(
                check_id,
                passed=passed,
                expected=threshold,
                observed=cast(JsonValue, observed),
                reason=reason,
            )
        )
        if not passed:
            hard_reasons.append(reason)

    stale = _number(metrics, "stale_incidents")
    stale_passed = stale is not None and stale <= hard.maximum_stale_incidents
    checks.append(
        _check(
            "stale-safety",
            passed=stale_passed,
            expected=hard.maximum_stale_incidents,
            observed=cast(JsonValue, stale),
            reason="stale-evidence-served",
        )
    )
    if not stale_passed:
        hard_reasons.append("stale-evidence-served")

    parser_calls = _number(metrics, "unchanged_parser_invocations")
    parser_passed = (
        parser_calls is not None and parser_calls <= hard.maximum_unchanged_parser_invocations
    )
    checks.append(
        _check(
            "unchanged-parser-avoidance",
            passed=parser_passed,
            expected=hard.maximum_unchanged_parser_invocations,
            observed=cast(JsonValue, parser_calls),
            reason="unchanged-parser-invoked",
        )
    )
    if not parser_passed:
        hard_reasons.append("unchanged-parser-invoked")

    reference_blocks = _number(metrics, "reference_blocks")
    reference_passed = (
        reference_blocks is not None and reference_blocks >= unconditional.minimum_reference_blocks
    )
    checks.append(
        _check(
            "reference-workload",
            passed=reference_passed,
            expected=unconditional.minimum_reference_blocks,
            observed=cast(JsonValue, reference_blocks),
            reason="reference-workload-incomplete",
        )
    )
    if not reference_passed:
        hard_reasons.append("reference-workload-incomplete")

    rich_value = metrics.get("rich_formats", ())
    if not isinstance(rich_value, (tuple, list)) or any(
        not isinstance(item, str) for item in rich_value
    ):
        raise ValueError("rich_formats must be a string sequence")
    rich_formats = tuple(sorted(set(cast(Sequence[str], rich_value))))
    missing_rich = tuple(
        item for item in unconditional.required_rich_formats if item not in rich_formats
    )
    checks.append(
        _check(
            "rich-format-completeness",
            passed=not missing_rich,
            expected=list(unconditional.required_rich_formats),
            observed=list(rich_formats),
            reason="rich-format-incomplete",
        )
    )
    conditional_reasons.extend(f"{item}-unavailable" for item in missing_rich)

    scale_blocks = _number(metrics, "scale_blocks")
    scale_passed = scale_blocks is not None and scale_blocks >= unconditional.minimum_scale_blocks
    checks.append(
        _check(
            "scale-workload",
            passed=scale_passed,
            expected=unconditional.minimum_scale_blocks,
            observed=cast(JsonValue, scale_blocks),
            reason="scale-target-not-completed",
        )
    )
    if not scale_passed:
        conditional_reasons.append("scale-target-not-completed")

    search_p95 = _number(metrics, "search_p95_ns_at_100k")
    if search_p95 is not None:
        search_passed = search_p95 <= unconditional.maximum_search_p95_ns_at_100k
        checks.append(
            _check(
                "scale-search-latency",
                passed=search_passed,
                expected=unconditional.maximum_search_p95_ns_at_100k,
                observed=search_p95,
                reason="search-latency-target-missed",
            )
        )
        if not search_passed:
            conditional_reasons.append("search-latency-target-missed")

    status_p95 = _number(metrics, "status_p95_ns")
    status_passed = status_p95 is not None and status_p95 <= unconditional.maximum_status_p95_ns
    checks.append(
        _check(
            "status-latency",
            passed=status_passed,
            expected=unconditional.maximum_status_p95_ns,
            observed=cast(JsonValue, status_p95),
            reason="status-latency-target-missed",
        )
    )
    if not status_passed:
        conditional_reasons.append("status-latency-target-missed")

    context_ratio = _number(metrics, "context_selected_native_ratio")
    context_passed = (
        context_ratio is not None
        and context_ratio <= unconditional.maximum_context_selected_native_ratio
    )
    checks.append(
        _check(
            "context-reduction",
            passed=context_passed,
            expected=unconditional.maximum_context_selected_native_ratio,
            observed=cast(JsonValue, context_ratio),
            reason="context-reduction-target-missed",
        )
    )
    if not context_passed:
        conditional_reasons.append("context-reduction-target-missed")

    break_even = _number(metrics, "break_even")
    break_even_passed = break_even is not None and break_even <= unconditional.break_even_horizon
    checks.append(
        _check(
            "break-even",
            passed=break_even_passed,
            expected=unconditional.break_even_horizon,
            observed=cast(JsonValue, break_even),
            reason="break-even-not-observed",
        )
    )
    if not break_even_passed:
        conditional_reasons.append("break-even-not-observed")

    complete = metrics.get("complete")
    complete_passed = complete is True
    checks.append(
        _check(
            "benchmark-completeness",
            passed=complete_passed,
            expected=True,
            observed=cast(JsonValue, complete),
            reason="benchmark-incomplete",
        )
    )
    if not complete_passed:
        conditional_reasons.append("benchmark-incomplete")

    if hard_reasons:
        outcome = ValueOutcome.NOT_DEMONSTRATED
        reasons = tuple(dict.fromkeys(hard_reasons))
    elif conditional_reasons:
        outcome = ValueOutcome.CONDITIONALLY_WORTHWHILE
        reasons = tuple(dict.fromkeys(conditional_reasons))
    else:
        outcome = ValueOutcome.WORTHWHILE
        reasons = ()
    provisional = ValueDecision.model_construct(
        decision_version="0.1.0",
        decision_id=UNBOUND_ID,
        protocol_id=inputs.protocol_id,
        corpus_id=inputs.corpus_id,
        policy_id=inputs.policy_id,
        outcome=outcome,
        reason_codes=reasons,
        checks=tuple(checks),
        inherited_release_status="NO-GO",
    )
    projection = provisional.model_dump(mode="json", exclude={"decision_id"})
    identified: dict[str, JsonValue] = {
        **projection,
        "decision_id": canonical_sha256(projection),
    }
    return ValueDecision.model_validate_json(canonical_json_bytes(identified))


__all__ = ["decide_value", "summarize_timing"]
