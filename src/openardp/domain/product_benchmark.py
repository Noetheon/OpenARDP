"""Pure closed records for the F020 product-value benchmark."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated

from pydantic import Field, JsonValue, StringConstraints, model_validator

from openardp.domain.common import DomainModel, Sha256Id
from openardp.domain.identity import canonical_json_bytes, canonical_sha256

PRODUCT_BENCHMARK_VERSION = "0.1.0"
UNBOUND_ID = "sha256:" + "0" * 64

BenchmarkId = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]
ReasonCode = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$"),
]


class BenchmarkProfile(StrEnum):
    """Closed workload profiles."""

    SMOKE = "smoke"
    REFERENCE = "reference"
    SCALE = "scale"
    FULL = "full"


class BenchmarkTreatment(StrEnum):
    """Fair repeated-task treatments."""

    RAW_REPARSE = "raw_reparse"
    PERSISTED_NATIVE = "persisted_native"
    OPENARDP = "openardp"


class BenchmarkPhase(StrEnum):
    """Measured lifecycle phases."""

    PREPARE = "prepare"
    SEARCH = "search"
    STATUS = "status"
    REINGEST = "reingest"
    CONTEXT = "context"
    REPLAY = "replay"
    EDIT = "edit"
    NATIVE_LOAD = "native_load"
    EVIDENCE = "evidence"


class BenchmarkMetric(StrEnum):
    """Closed metric vocabulary."""

    LATENCY = "latency"
    CPU_TIME = "cpu_time"
    PEAK_RSS = "peak_rss"
    PARSER_INVOCATIONS = "parser_invocations"
    SOURCE_BYTES = "source_bytes"
    NATIVE_BYTES = "native_bytes"
    SELECTED_BYTES = "selected_bytes"
    WORKSPACE_BYTES = "workspace_bytes"
    PRECISION = "precision"
    RECALL = "recall"
    RECIPROCAL_RANK = "reciprocal_rank"
    ANCHOR_CORRECTNESS = "anchor_correctness"
    CONTEXT_COVERAGE = "context_coverage"
    REPLAY_MATCH = "replay_match"
    STALE_INCIDENTS = "stale_incidents"


class MetricUnit(StrEnum):
    """Closed metric units."""

    NANOSECONDS = "ns"
    BYTES = "bytes"
    COUNT = "count"
    RATIO = "ratio"


class ObservationStatus(StrEnum):
    """Terminal observation status."""

    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class ValueOutcome(StrEnum):
    """Workload-bounded product-value outcomes."""

    WORTHWHILE = "WORTHWHILE"
    CONDITIONALLY_WORTHWHILE = "CONDITIONALLY_WORTHWHILE"
    NOT_DEMONSTRATED = "NOT_DEMONSTRATED"


class CheckStatus(StrEnum):
    """Deterministic value-check status."""

    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


_METRIC_UNITS: dict[BenchmarkMetric, MetricUnit] = {
    BenchmarkMetric.LATENCY: MetricUnit.NANOSECONDS,
    BenchmarkMetric.CPU_TIME: MetricUnit.NANOSECONDS,
    BenchmarkMetric.PEAK_RSS: MetricUnit.BYTES,
    BenchmarkMetric.PARSER_INVOCATIONS: MetricUnit.COUNT,
    BenchmarkMetric.SOURCE_BYTES: MetricUnit.BYTES,
    BenchmarkMetric.NATIVE_BYTES: MetricUnit.BYTES,
    BenchmarkMetric.SELECTED_BYTES: MetricUnit.BYTES,
    BenchmarkMetric.WORKSPACE_BYTES: MetricUnit.BYTES,
    BenchmarkMetric.PRECISION: MetricUnit.RATIO,
    BenchmarkMetric.RECALL: MetricUnit.RATIO,
    BenchmarkMetric.RECIPROCAL_RANK: MetricUnit.RATIO,
    BenchmarkMetric.ANCHOR_CORRECTNESS: MetricUnit.RATIO,
    BenchmarkMetric.CONTEXT_COVERAGE: MetricUnit.RATIO,
    BenchmarkMetric.REPLAY_MATCH: MetricUnit.RATIO,
    BenchmarkMetric.STALE_INCIDENTS: MetricUnit.COUNT,
}


class BenchmarkObservation(DomainModel):
    """One immutable body-free benchmark fact."""

    schema_version: str = PRODUCT_BENCHMARK_VERSION
    observation_id: Sha256Id
    protocol_id: Sha256Id
    corpus_id: Sha256Id
    policy_id: Sha256Id
    environment_id: Sha256Id
    profile: BenchmarkProfile
    workload_id: BenchmarkId
    treatment: BenchmarkTreatment
    phase: BenchmarkPhase
    metric: BenchmarkMetric
    unit: MetricUnit
    repetition: int = Field(strict=True, ge=0, le=100_000)
    status: ObservationStatus
    value: int | float | None = None
    reason_code: ReasonCode | None = None

    @property
    def identity_projection(self) -> dict[str, JsonValue]:
        """Return every immutable fact except the declared identifier."""
        return self.model_dump(mode="json", exclude={"observation_id"})

    @model_validator(mode="after")
    def _value_unit_and_identity_are_valid(self) -> BenchmarkObservation:
        if self.schema_version != PRODUCT_BENCHMARK_VERSION:
            raise ValueError("unsupported product benchmark schema version")
        if self.unit is not _METRIC_UNITS[self.metric]:
            raise ValueError("metric unit does not match metric")
        if self.status is ObservationStatus.PASSED:
            if self.value is None or isinstance(self.value, bool):
                raise ValueError("passed observation requires a numeric value")
            if not math.isfinite(float(self.value)) or self.value < 0:
                raise ValueError("observation value must be finite and non-negative")
            if self.reason_code is not None:
                raise ValueError("passed observation cannot carry a reason")
            if self.unit is not MetricUnit.RATIO and type(self.value) is not int:
                raise ValueError("integer metric requires integer value")
            if self.unit is MetricUnit.RATIO and not 0.0 <= float(self.value) <= 1.0:
                raise ValueError("ratio must be between zero and one")
        elif self.value is not None or self.reason_code is None:
            raise ValueError("non-passed observation requires reason and no value")
        if canonical_sha256(self.identity_projection) != self.observation_id:
            raise ValueError("benchmark observation identity mismatch")
        return self


class MetricSummary(DomainModel):
    """Deterministic robust summary over homogeneous passed timings."""

    summary_id: Sha256Id
    metric: BenchmarkMetric
    unit: MetricUnit
    profile: BenchmarkProfile
    workload_id: BenchmarkId
    treatment: BenchmarkTreatment
    phase: BenchmarkPhase
    sample_count: int = Field(strict=True, ge=1)
    p50: int = Field(strict=True, ge=0)
    p95: int = Field(strict=True, ge=0)
    median_absolute_deviation: int = Field(strict=True, ge=0)
    confidence_low: int = Field(strict=True, ge=0)
    confidence_high: int = Field(strict=True, ge=0)
    observation_ids: tuple[Sha256Id, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _summary_is_consistent(self) -> MetricSummary:
        if self.metric not in {BenchmarkMetric.LATENCY, BenchmarkMetric.CPU_TIME}:
            raise ValueError("timing summary requires a timing metric")
        if self.unit is not MetricUnit.NANOSECONDS:
            raise ValueError("timing summary unit must be nanoseconds")
        if self.sample_count != len(self.observation_ids):
            raise ValueError("sample count does not match observation inventory")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("summary observations must be unique")
        if not self.confidence_low <= self.p50 <= self.confidence_high:
            raise ValueError("summary confidence interval does not contain p50")
        projection = self.model_dump(mode="json", exclude={"summary_id"})
        if canonical_sha256(projection) != self.summary_id:
            raise ValueError("metric summary identity mismatch")
        return self


class ValueCheck(DomainModel):
    """One frozen-policy clause and its exact evidence result."""

    check_id: BenchmarkId
    status: CheckStatus
    reason_code: ReasonCode | None = None
    expected: JsonValue
    observed: JsonValue

    @model_validator(mode="after")
    def _status_reason_agrees(self) -> ValueCheck:
        if self.status is CheckStatus.PASSED and self.reason_code is not None:
            raise ValueError("passed value check cannot carry a reason")
        if self.status is not CheckStatus.PASSED and self.reason_code is None:
            raise ValueError("non-passed value check requires a reason")
        return self


class ValueDecision(DomainModel):
    """One canonical workload-bounded product-value decision."""

    decision_version: str = PRODUCT_BENCHMARK_VERSION
    decision_id: Sha256Id
    protocol_id: Sha256Id
    corpus_id: Sha256Id
    policy_id: Sha256Id
    outcome: ValueOutcome
    reason_codes: tuple[ReasonCode, ...]
    checks: tuple[ValueCheck, ...] = Field(min_length=1)
    inherited_release_status: str = "NO-GO"

    @model_validator(mode="after")
    def _decision_is_canonical(self) -> ValueDecision:
        if self.decision_version != PRODUCT_BENCHMARK_VERSION:
            raise ValueError("unsupported value decision version")
        if self.reason_codes != tuple(dict.fromkeys(self.reason_codes)):
            raise ValueError("decision reason codes must be ordered and unique")
        if self.outcome is ValueOutcome.WORTHWHILE and self.reason_codes:
            raise ValueError("worthwhile decision cannot have blockers")
        if self.inherited_release_status != "NO-GO":
            raise ValueError("F020 cannot replace the F015 release decision")
        projection = self.model_dump(mode="json", exclude={"decision_id"})
        if canonical_sha256(projection) != self.decision_id:
            raise ValueError("value decision identity mismatch")
        return self


def make_observation(
    *,
    protocol_id: str,
    corpus_id: str,
    policy_id: str,
    environment_id: str,
    profile: BenchmarkProfile,
    workload_id: str,
    treatment: BenchmarkTreatment,
    phase: BenchmarkPhase,
    metric: BenchmarkMetric,
    unit: MetricUnit,
    repetition: int,
    value: int | float | None = None,
    status: ObservationStatus = ObservationStatus.PASSED,
    reason_code: str | None = None,
) -> BenchmarkObservation:
    """Create and fully validate one canonically identified observation."""
    provisional = BenchmarkObservation.model_construct(
        schema_version=PRODUCT_BENCHMARK_VERSION,
        observation_id=UNBOUND_ID,
        protocol_id=protocol_id,
        corpus_id=corpus_id,
        policy_id=policy_id,
        environment_id=environment_id,
        profile=profile,
        workload_id=workload_id,
        treatment=treatment,
        phase=phase,
        metric=metric,
        unit=unit,
        repetition=repetition,
        status=status,
        value=value,
        reason_code=reason_code,
    )
    payload = provisional.model_dump(mode="json", exclude={"observation_id"})
    identified: dict[str, JsonValue] = {
        **payload,
        "observation_id": canonical_sha256(payload),
    }
    return BenchmarkObservation.model_validate_json(canonical_json_bytes(identified))


__all__ = [
    "PRODUCT_BENCHMARK_VERSION",
    "BenchmarkMetric",
    "BenchmarkObservation",
    "BenchmarkPhase",
    "BenchmarkProfile",
    "BenchmarkTreatment",
    "CheckStatus",
    "MetricSummary",
    "MetricUnit",
    "ObservationStatus",
    "ValueCheck",
    "ValueDecision",
    "ValueOutcome",
    "make_observation",
]
