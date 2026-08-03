"""Pure deterministic minimum-relevance contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from openardp.domain.context_relevance import (
    RelevancePolicy,
    RelevanceSignalClass,
    evaluate_candidate_relevance,
    extract_relevance_signals,
)


def test_default_policy_identity_is_complete_and_deterministic() -> None:
    """The default policy binds every decision field to one stable identity."""
    first = RelevancePolicy()
    second = RelevancePolicy()

    assert first.policy_id == second.policy_id
    assert first.policy_id.startswith("sha256:")
    assert first.minimum_score_millionths == 250_000
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


@pytest.mark.parametrize(
    ("update", "match"),
    [
        ({"minimum_score_millionths": -1}, "greater than or equal"),
        ({"minimum_score_millionths": 1_000_001}, "less than or equal"),
        ({"function_words": ("z", "a")}, "sorted and unique"),
        ({"volatile_time_signals": ()}, "non-empty"),
        ({"ordinary_weight": 0}, "greater than or equal"),
    ],
)
def test_policy_rejects_invalid_or_noncanonical_configuration(
    update: dict[str, object], match: str
) -> None:
    """Invalid bounds and noncanonical configured sets fail closed."""
    with pytest.raises((ValidationError, ValueError), match=match):
        RelevancePolicy(**update)


def test_signal_extraction_is_nfc_casefolded_unique_and_function_word_free() -> None:
    """Task signals are normalized, deduplicated and stripped of function words."""
    signals = extract_relevance_signals(
        "WHAT is Café café and NASA's framework?",
        RelevancePolicy(),
    )

    assert tuple(signal.value for signal in signals) == ("café", "framework", "nasa")
    assert signals[2].signal_class is RelevanceSignalClass.IDENTIFIER


def test_identifiers_dates_and_acronyms_have_explicit_weight() -> None:
    """Exact high-information signals receive the configured identifier weight."""
    policy = RelevancePolicy()
    signals = extract_relevance_signals(
        "CVE-2021-44228 due 2021-12-24 NASA guidance",
        policy,
    )
    by_value = {signal.value: signal for signal in signals}

    assert by_value["cve-2021-44228"].signal_class is RelevanceSignalClass.IDENTIFIER
    assert by_value["2021-12-24"].weight == policy.identifier_weight
    assert by_value["nasa"].weight == policy.identifier_weight
    assert by_value["guidance"].weight == policy.ordinary_weight


def test_calendar_year_is_a_high_weight_volatile_constraint() -> None:
    """A task year must occur exactly in a candidate and keeps identifier weight."""
    policy = RelevancePolicy()
    signal = next(
        item
        for item in extract_relevance_signals("approved deployment budget 2027", policy)
        if item.value == "2027"
    )

    assert signal.value == "2027"
    assert signal.signal_class is RelevanceSignalClass.VOLATILE_TIME
    assert signal.weight == policy.identifier_weight
    assert not evaluate_candidate_relevance(
        "approved deployment budget 2027", "approved deployment budget", policy
    ).meets_minimum


def test_repetition_does_not_increase_coverage_or_score() -> None:
    """Repeated body terms cannot inflate unique task-signal coverage."""
    policy = RelevancePolicy()
    single = evaluate_candidate_relevance("alpha beta gamma delta", "alpha beta", policy)
    repeated = evaluate_candidate_relevance(
        "alpha beta gamma delta",
        "alpha alpha alpha beta beta",
        policy,
    )

    assert repeated == single
    assert single.matched_signals == 2
    assert single.total_signals == 4
    assert single.score_millionths == 500_000


@pytest.mark.parametrize(
    ("minimum", "body", "expected"),
    [
        (500_001, "alpha beta", False),
        (500_000, "alpha beta", True),
        (499_999, "alpha beta", True),
    ],
)
def test_floor_uses_exact_integer_cross_multiplication(
    minimum: int, body: str, expected: bool
) -> None:
    """Eligibility uses an exact inclusive integer floor without float rounding."""
    policy = RelevancePolicy(minimum_score_millionths=minimum)

    observation = evaluate_candidate_relevance("alpha beta gamma delta", body, policy)

    assert observation.meets_minimum is expected


def test_volatile_time_intent_requires_every_candidate_signal() -> None:
    """Every live/current constraint must occur in the same candidate evidence."""
    policy = RelevancePolicy()

    missing = evaluate_candidate_relevance(
        "Which vulnerability was added most recently to the live catalog today?",
        "The vulnerability catalog is mirrored on weekdays.",
        policy,
    )
    present = evaluate_candidate_relevance(
        "Which vulnerability was added most recently to the live catalog today?",
        "The live vulnerability catalog was updated most recently today.",
        policy,
    )
    partial = evaluate_candidate_relevance(
        "Which vulnerability was added most recently to the live catalog today?",
        "The live vulnerability catalog is updated on weekdays.",
        policy,
    )

    assert missing.volatile_time_matched is False
    assert missing.meets_minimum is False
    assert present.volatile_time_matched is True
    assert present.meets_minimum is True
    assert partial.volatile_time_matched is False
    assert partial.meets_minimum is False


@pytest.mark.parametrize("task", ["", "   ", "??? !!!", "what is the and or"])
def test_empty_punctuation_and_function_word_tasks_cannot_be_relevant(task: str) -> None:
    """Tasks without informative signals cannot authorize a relevant candidate."""
    observation = evaluate_candidate_relevance(task, "what is the answer", RelevancePolicy())

    assert observation.total_signals == 0
    assert observation.score_millionths == 0
    assert observation.meets_minimum is False


def test_signal_limit_is_enforced_before_candidate_evaluation() -> None:
    """Task normalization stops at the configured allocation boundary."""
    policy = RelevancePolicy(max_signals=2)

    with pytest.raises(ValueError, match="signal limit"):
        extract_relevance_signals("alpha beta gamma", policy)
