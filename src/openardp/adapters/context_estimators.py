"""Exact versioned budget estimators for serialized canonical context bytes."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import JsonValue

from openardp.domain.context import BudgetUnit
from openardp.domain.context_compilation import EstimatorIdentity
from openardp.domain.identity import canonical_sha256
from openardp.ports.context import (
    ContextConfigurationMismatch,
    ContextEstimator,
    ContextLimitExceeded,
)

ESTIMATOR_VERSION = "1.0.0"
DEFAULT_FIXED_POINT_ITERATIONS = 8


def _identity(name: str, unit: BudgetUnit, parameters: dict[str, JsonValue]) -> EstimatorIdentity:
    """Build one deterministic replaceable estimator identity."""
    config_hash = canonical_sha256(
        {
            "estimator": name,
            "version": ESTIMATOR_VERSION,
            "unit": unit.value,
            "parameters": parameters,
        }
    )
    return EstimatorIdentity(
        name=name,
        version=ESTIMATOR_VERSION,
        unit=unit,
        config_hash=config_hash,
    )


class Utf8ByteEstimator:
    """Exact UTF-8 byte measurement of serialized context payloads."""

    @property
    def identity(self) -> EstimatorIdentity:
        """Return the complete versioned estimator identity."""
        return _identity("openardp.utf8-bytes", BudgetUnit.BYTES, {})

    def measure(self, payload: bytes) -> int:
        """Measure the exact payload length in bytes."""
        return len(payload)


class UnicodeCharacterEstimator:
    """Exact Unicode scalar-value measurement of valid UTF-8 payloads."""

    @property
    def identity(self) -> EstimatorIdentity:
        """Return the complete versioned estimator identity."""
        return _identity("openardp.unicode-characters", BudgetUnit.CHARACTERS, {})

    def measure(self, payload: bytes) -> int:
        """Count exact Unicode scalar values; invalid UTF-8 fails visibly."""
        return len(payload.decode("utf-8"))


class ConservativeTokenEstimator:
    """Honest overestimate of one token per UTF-8 byte without accuracy claims."""

    @property
    def identity(self) -> EstimatorIdentity:
        """Return the complete versioned estimator identity."""
        return _identity("openardp.conservative-utf8-tokens", BudgetUnit.TOKENS, {})

    def measure(self, payload: bytes) -> int:
        """Overestimate tokens as exact UTF-8 byte count."""
        return len(payload)


BUILT_IN_ESTIMATORS: tuple[ContextEstimator, ...] = (
    Utf8ByteEstimator(),
    UnicodeCharacterEstimator(),
    ConservativeTokenEstimator(),
)


def additive_usage_fixed_point(zero_usage: int) -> int:
    """Resolve two embedded decimal usage fields from an exact zero-usage measure."""
    usage = 0
    for _ in range(DEFAULT_FIXED_POINT_ITERATIONS):
        measured = zero_usage + (2 * (len(str(usage)) - 1))
        if measured == usage:
            return usage
        usage = measured
    raise ContextLimitExceeded("budget_fixed_point_diverged")


def empty_phase_metrics() -> dict[str, int]:
    """Return a fresh complete phase ledger for compile and replay paths."""
    return {
        "snapshot_ns": 0,
        "discovery_ns": 0,
        "classification_ns": 0,
        "materialization_ns": 0,
        "budgeting_ns": 0,
        "finalization_ns": 0,
        "compile_ns": 0,
    }


def resolve_estimator(identity: EstimatorIdentity) -> ContextEstimator:
    """Return the built-in estimator for one exact identity without fallback."""
    for estimator in BUILT_IN_ESTIMATORS:
        if estimator.identity == identity:
            return estimator
    raise ContextConfigurationMismatch("estimator_identity_not_installed")


def fixed_point_measure(
    builder: Callable[[int], bytes],
    estimator: ContextEstimator,
    *,
    max_iterations: int = DEFAULT_FIXED_POINT_ITERATIONS,
) -> int:
    """Measure a payload whose embedded usage field must equal its own measurement."""
    usage = 0
    for _ in range(max_iterations):
        measured = estimator.measure(builder(usage))
        if measured == usage:
            return usage
        usage = measured
    raise ContextLimitExceeded("budget_fixed_point_diverged")


__all__ = [
    "BUILT_IN_ESTIMATORS",
    "DEFAULT_FIXED_POINT_ITERATIONS",
    "ESTIMATOR_VERSION",
    "ConservativeTokenEstimator",
    "UnicodeCharacterEstimator",
    "Utf8ByteEstimator",
    "additive_usage_fixed_point",
    "empty_phase_metrics",
    "fixed_point_measure",
    "resolve_estimator",
]
