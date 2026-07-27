"""Exact versioned estimator and fixed-point budget accounting tests."""

from __future__ import annotations

import pytest

from openardp.adapters.context_estimators import (
    BUILT_IN_ESTIMATORS,
    ConservativeTokenEstimator,
    UnicodeCharacterEstimator,
    Utf8ByteEstimator,
    fixed_point_measure,
    resolve_estimator,
)
from openardp.domain.context import BudgetUnit
from openardp.domain.context_compilation import EstimatorIdentity
from openardp.ports.context import ContextConfigurationMismatch, ContextLimitExceeded

UNICODE_TEXT = "Unicode é and 漢字"


def test_byte_estimator_counts_exact_utf8_bytes() -> None:
    """Measure exact serialized bytes without interpretation."""
    estimator = Utf8ByteEstimator()
    assert estimator.measure(b"") == 0
    assert estimator.measure(b"abc") == 3
    assert estimator.measure(UNICODE_TEXT.encode()) == len(UNICODE_TEXT.encode())
    identity = estimator.identity
    assert identity.unit is BudgetUnit.BYTES
    assert identity.name == "openardp.utf8-bytes"
    assert identity.version == "1.0.0"
    assert identity.config_hash.startswith("sha256:")


def test_character_estimator_counts_exact_unicode_scalars() -> None:
    """Count Unicode scalar values rather than bytes or grapheme guesses."""
    estimator = UnicodeCharacterEstimator()
    assert estimator.measure("é".encode()) == 1
    assert estimator.measure("漢字".encode()) == 2
    assert estimator.measure("é".encode()) == 2
    assert estimator.identity.unit is BudgetUnit.CHARACTERS
    with pytest.raises(UnicodeDecodeError):
        estimator.measure(b"\xff\xfe")


def test_conservative_token_estimator_never_undercounts_bytes() -> None:
    """Overestimate honestly at one token per UTF-8 byte without accuracy claims."""
    estimator = ConservativeTokenEstimator()
    payload = UNICODE_TEXT.encode()
    assert estimator.measure(payload) == len(payload)
    assert estimator.identity.unit is BudgetUnit.TOKENS
    assert estimator.identity.config_hash != Utf8ByteEstimator().identity.config_hash


def test_estimator_identities_are_deterministic_and_distinct() -> None:
    """Keep every built-in estimator identity stable across constructions."""
    first = tuple(estimator.identity for estimator in BUILT_IN_ESTIMATORS)
    again = tuple(type(estimator)().identity for estimator in BUILT_IN_ESTIMATORS)
    assert first == again
    assert len({identity.config_hash for identity in first}) == len(first)
    assert len({identity.unit for identity in first}) == 3


def test_resolve_estimator_requires_exact_identity_match() -> None:
    """Reject replay or caller drift on any identity field without fallback."""
    identity = Utf8ByteEstimator().identity
    assert resolve_estimator(identity).identity == identity
    for change in (
        {"version": "1.0.1"},
        {"unit": BudgetUnit.TOKENS},
        {"config_hash": "sha256:" + "9" * 64},
        {"name": "openardp.other"},
    ):
        drifted = EstimatorIdentity(**{**identity.model_dump(), **change})
        with pytest.raises(ContextConfigurationMismatch, match="estimator"):
            resolve_estimator(drifted)


def test_fixed_point_measure_converges_when_usage_digits_stabilize() -> None:
    """Iterate canonical measurement until the embedded usage field is exact."""
    estimator = Utf8ByteEstimator()
    builds: list[int] = []

    def builder(usage: int) -> bytes:
        builds.append(usage)
        return b'{"estimated_used":' + str(usage).encode() + b',"body":"' + b"x" * 100 + b'"}'

    usage = fixed_point_measure(builder, estimator)
    assert usage == estimator.measure(builder(usage))
    assert builds[0] == 0
    assert len(builds) <= 4


def test_fixed_point_measure_returns_oversize_measurement_for_caller_failure() -> None:
    """Report an overflowing exact measurement instead of hiding it."""
    estimator = Utf8ByteEstimator()

    def builder(usage: int) -> bytes:
        del usage
        return b"x" * 2_000

    assert fixed_point_measure(builder, estimator) == 2_000


def test_fixed_point_measure_fails_closed_without_convergence() -> None:
    """Never loop indefinitely on a pathological builder."""
    estimator = Utf8ByteEstimator()
    state = {"flip": False}

    def builder(usage: int) -> bytes:
        state["flip"] = not state["flip"]
        return b"x" * (usage + (1 if state["flip"] else 2))

    with pytest.raises(ContextLimitExceeded, match="fixed_point"):
        fixed_point_measure(builder, estimator, max_iterations=4)
