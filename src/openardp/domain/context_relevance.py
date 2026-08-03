"""Deterministic provider-free minimum-relevance policy and observations."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Self

from pydantic import Field, JsonValue, model_validator

from openardp.domain.common import DomainModel, Sha256Id
from openardp.domain.identity import canonical_sha256

RELEVANCE_SCORE_SCALE = 1_000_000
_TOKEN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
_DEFAULT_FUNCTION_WORDS = tuple(
    sorted(
        {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "das",
            "dem",
            "den",
            "der",
            "die",
            "ein",
            "eine",
            "for",
            "from",
            "how",
            "in",
            "is",
            "it",
            "mit",
            "of",
            "on",
            "or",
            "should",
            "the",
            "to",
            "und",
            "von",
            "was",
            "welche",
            "welcher",
            "welches",
            "what",
            "when",
            "which",
            "who",
            "why",
            "wie",
            "with",
            "zu",
        }
    )
)
_DEFAULT_VOLATILE_TIME_SIGNALS = ("current", "heute", "latest", "live", "recently", "today")


class RelevanceSignalClass(StrEnum):
    """Closed explainable classes for bounded task signals."""

    ORDINARY = "ordinary"
    IDENTIFIER = "identifier"
    VOLATILE_TIME = "volatile_time"


class RelevancePolicy(DomainModel):
    """Complete deterministic minimum-relevance configuration."""

    name: str = Field(default="openardp-exact-coverage", min_length=1, max_length=128)
    version: str = Field(
        default="1.0.0",
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    )
    minimum_score_millionths: int = Field(
        default=250_000,
        strict=True,
        ge=0,
        le=RELEVANCE_SCORE_SCALE,
    )
    max_signals: int = Field(default=64, strict=True, ge=1, le=256)
    max_signal_characters: int = Field(default=128, strict=True, ge=1, le=512)
    ordinary_weight: int = Field(default=1, strict=True, ge=1, le=100)
    identifier_weight: int = Field(default=4, strict=True, ge=1, le=100)
    function_words: tuple[str, ...] = _DEFAULT_FUNCTION_WORDS
    volatile_time_signals: tuple[str, ...] = _DEFAULT_VOLATILE_TIME_SIGNALS

    @model_validator(mode="after")
    def _sets_and_weights_are_canonical(self) -> Self:
        for name, values in (
            ("function_words", self.function_words),
            ("volatile_time_signals", self.volatile_time_signals),
        ):
            if not values:
                raise ValueError(f"{name} must be non-empty")
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{name} must be sorted and unique")
            if any(_normalize_token(value) != value for value in values):
                raise ValueError(f"{name} must contain normalized tokens")
        if set(self.function_words) & set(self.volatile_time_signals):
            raise ValueError("function words and volatile signals must not overlap")
        return self

    @property
    def policy_id(self) -> Sha256Id:
        """Return the canonical identity of every decision-significant field."""
        return canonical_sha256(self.model_dump(mode="json"))


class RelevanceSignal(DomainModel):
    """One normalized unique task signal and its fixed weight."""

    value: str = Field(min_length=1, max_length=512)
    signal_class: RelevanceSignalClass
    weight: int = Field(strict=True, ge=1, le=100)


class CandidateRelevance(DomainModel):
    """Body-free integer relevance observation for one verified candidate."""

    policy_id: Sha256Id
    total_signals: int = Field(strict=True, ge=0, le=256)
    matched_signals: int = Field(strict=True, ge=0, le=256)
    total_weight: int = Field(strict=True, ge=0, le=25_600)
    matched_weight: int = Field(strict=True, ge=0, le=25_600)
    score_millionths: int = Field(strict=True, ge=0, le=RELEVANCE_SCORE_SCALE)
    volatile_time_matched: bool
    meets_minimum: bool

    @model_validator(mode="after")
    def _counts_and_score_are_consistent(self) -> Self:
        if self.matched_signals > self.total_signals or self.matched_weight > self.total_weight:
            raise ValueError("matched relevance cannot exceed total relevance")
        expected = (
            0
            if self.total_weight == 0
            else self.matched_weight * RELEVANCE_SCORE_SCALE // self.total_weight
        )
        if self.score_millionths != expected:
            raise ValueError("relevance score is inconsistent")
        return self

    def extension_value(self) -> dict[str, JsonValue]:
        """Return the closed body-free receipt extension projection."""
        return {
            "matched_signals": self.matched_signals,
            "matched_weight": self.matched_weight,
            "meets_minimum": self.meets_minimum,
            "policy_id": self.policy_id,
            "score_millionths": self.score_millionths,
            "total_signals": self.total_signals,
            "total_weight": self.total_weight,
            "volatile_time_matched": self.volatile_time_matched,
        }


def extract_relevance_signals(task: str, policy: RelevancePolicy) -> tuple[RelevanceSignal, ...]:
    """Extract canonical bounded task signals without retaining task text."""
    normalized_task = unicodedata.normalize("NFC", task)
    by_value: dict[str, RelevanceSignal] = {}
    for match in _TOKEN.finditer(normalized_task):
        raw = match.group(0)
        value = _normalize_token(raw)
        if value.endswith("'s") and len(value) > 2:
            value = value[:-2]
            raw = raw[:-2]
        if not value or value in policy.function_words:
            continue
        if len(value) > policy.max_signal_characters:
            raise ValueError("relevance signal character limit exceeded")
        if value in policy.volatile_time_signals:
            signal_class = RelevanceSignalClass.VOLATILE_TIME
            weight = policy.ordinary_weight
        elif _is_calendar_year(value):
            signal_class = RelevanceSignalClass.VOLATILE_TIME
            weight = policy.identifier_weight
        elif _is_identifier(raw, value):
            signal_class = RelevanceSignalClass.IDENTIFIER
            weight = policy.identifier_weight
        else:
            signal_class = RelevanceSignalClass.ORDINARY
            weight = policy.ordinary_weight
        by_value[value] = RelevanceSignal(
            value=value,
            signal_class=signal_class,
            weight=weight,
        )
        if len(by_value) > policy.max_signals:
            raise ValueError("relevance signal limit exceeded")
    return tuple(by_value[value] for value in sorted(by_value))


def evaluate_candidate_relevance(
    task: str,
    candidate_text: str,
    policy: RelevancePolicy,
) -> CandidateRelevance:
    """Evaluate exact unique signal coverage with an integer-only floor."""
    signals = extract_relevance_signals(task, policy)
    body_tokens = {
        _normalize_token(match.group(0))
        for match in _TOKEN.finditer(unicodedata.normalize("NFC", candidate_text))
    }
    matched = tuple(signal for signal in signals if signal.value in body_tokens)
    total_weight = sum(signal.weight for signal in signals)
    matched_weight = sum(signal.weight for signal in matched)
    volatile = tuple(
        signal for signal in signals if signal.signal_class is RelevanceSignalClass.VOLATILE_TIME
    )
    volatile_time_matched = not volatile or all(signal in matched for signal in volatile)
    meets_minimum = (
        total_weight > 0
        and volatile_time_matched
        and matched_weight * RELEVANCE_SCORE_SCALE >= total_weight * policy.minimum_score_millionths
    )
    score = 0 if total_weight == 0 else matched_weight * RELEVANCE_SCORE_SCALE // total_weight
    return CandidateRelevance(
        policy_id=policy.policy_id,
        total_signals=len(signals),
        matched_signals=len(matched),
        total_weight=total_weight,
        matched_weight=matched_weight,
        score_millionths=score,
        volatile_time_matched=volatile_time_matched,
        meets_minimum=meets_minimum,
    )


def _normalize_token(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _is_identifier(raw: str, normalized: str) -> bool:
    letters = tuple(character for character in raw if character.isalpha())
    return any(character.isdigit() for character in normalized) or (
        len(letters) >= 2 and all(character.isupper() for character in letters)
    )


def _is_calendar_year(value: str) -> bool:
    return len(value) == 4 and value.isdecimal() and 1900 <= int(value) <= 2200


__all__ = [
    "RELEVANCE_SCORE_SCALE",
    "CandidateRelevance",
    "RelevancePolicy",
    "RelevanceSignal",
    "RelevanceSignalClass",
    "evaluate_candidate_relevance",
    "extract_relevance_signals",
]
