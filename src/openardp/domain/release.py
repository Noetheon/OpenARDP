"""Pure contracts for benchmark evidence and a fail-closed release decision."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated, Literal, cast

from pydantic import Field, JsonValue, StringConstraints, model_validator

from openardp.domain.common import DomainModel, Sha256Id, UtcDatetime
from openardp.domain.identity import canonical_sha256

RELEASE_EVIDENCE_VERSION = "0.1.0"
BENCHMARK_PROTOCOL_VERSION = "0.1.0"
RELEASE_GATE_POLICY_VERSION = "0.1.0"
IDENTITY_ALGORITHM = "sha256-rfc8785-v1"
UNBOUND_EVIDENCE_ID = "sha256:" + "0" * 64

_Identifier = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]
_PlatformId = Annotated[
    str,
    StringConstraints(strict=True, min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]
_NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
_PositiveInt = Annotated[int, Field(strict=True, ge=1)]
_Ratio = Annotated[float, Field(strict=True, ge=0.0, le=1.0, allow_inf_nan=False)]


class ReleaseEvidenceError(ValueError):
    """Base class for deterministic release-evidence validation failures."""


class EvidenceIdentityMismatch(ReleaseEvidenceError):
    """Raised when declared evidence identity does not match canonical facts."""


class EvidenceMalformed(ReleaseEvidenceError):
    """Raised when an evidence bundle is incomplete or structurally unsafe."""


class Baseline(StrEnum):
    """Fair benchmark treatment names fixed by the F015 protocol."""

    RAW_REPARSE = "raw_reparse"
    NATIVE_REUSE = "native_reuse"
    NATIVE_RETRIEVAL = "native_retrieval"
    OPENARDP_RETRIEVAL = "openardp_retrieval"
    OPENARDP_COMPILER = "openardp_compiler"


class BenchmarkPhase(StrEnum):
    """Measured lifecycle phase."""

    COLD = "cold"
    WARM = "warm"
    UPDATE = "update"
    RETRIEVAL = "retrieval"
    COMPILE = "compile"
    REPLAY = "replay"


class BenchmarkMetric(StrEnum):
    """Closed metric vocabulary."""

    LATENCY = "latency"
    PARSER_INVOCATIONS = "parser_invocations"
    STORAGE_BYTES = "storage_bytes"
    SELECTED_BYTES = "selected_bytes"
    NATIVE_BYTES = "native_bytes"
    CORRECTNESS = "correctness"
    COVERAGE = "coverage"
    PRECISION = "precision"
    RECALL = "recall"
    RECIPROCAL_RANK = "reciprocal_rank"
    ANCHOR_CORRECTNESS = "anchor_correctness"
    REPLAY_MATCH = "replay_match"
    STALE_REJECTION = "stale_rejection"


class MetricUnit(StrEnum):
    """Unambiguous metric units."""

    NANOSECONDS = "ns"
    COUNT = "count"
    BYTES = "bytes"
    RATIO = "ratio"


class EvidenceStatus(StrEnum):
    """Terminal status for one observation, check or suite."""

    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class SuiteName(StrEnum):
    """Mandatory release evidence suite names."""

    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    SECURITY = "security"
    PRIVACY = "privacy"
    SUPPLY_CHAIN = "supply_chain"
    FRESH_INSTALL = "fresh_install"
    UPGRADE_RECOVERY = "upgrade_recovery"
    PLATFORM_REPRODUCTION = "platform_reproduction"


class ReleaseStatus(StrEnum):
    """Binding release decision."""

    GO = "GO"
    NO_GO = "NO-GO"


class EnvironmentProfile(DomainModel):
    """Redacted environment facts suitable for release evidence."""

    platform_id: _PlatformId
    os_family: Literal["linux", "macos", "windows"]
    architecture: _Identifier
    python_implementation: Literal["cpython"] = "cpython"
    python_version: Annotated[str, StringConstraints(strict=True, pattern=r"^3\.12\.[0-9]+$")]
    logical_cpu_bucket: Literal["unknown", "1", "2", "3-4", "5-8", "9-16", "17+"]
    memory_gib_bucket: Literal["unknown", "<4", "4-7", "8-15", "16-31", "32-63", "64+"]
    timer_resolution_ns: _PositiveInt
    reference_timing: bool = False


class SourceTreeEntry(DomainModel):
    """One portable allowlisted candidate source entry."""

    path: Annotated[
        str,
        StringConstraints(strict=True, min_length=1, max_length=512, pattern=r"^[^\\\x00]+$"),
    ]
    byte_length: _NonNegativeInt
    sha256: Sha256Id


class SourceTreeInventory(DomainModel):
    """Canonical self-reference-free candidate source inventory."""

    source_tree_id: Sha256Id
    entries: tuple[SourceTreeEntry, ...]

    @model_validator(mode="after")
    def _entries_are_canonical(self) -> SourceTreeInventory:
        paths = tuple(item.path for item in self.entries)
        if not paths or paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise ValueError("source tree entries must be non-empty, sorted and unique")
        observed_id = canonical_sha256([item.model_dump(mode="json") for item in self.entries])
        if observed_id != self.source_tree_id:
            raise ValueError("source tree identity mismatch")
        return self


class BenchmarkObservation(DomainModel):
    """One immutable raw benchmark observation."""

    observation_id: Sha256Id
    source_version_id: Sha256Id = UNBOUND_EVIDENCE_ID
    protocol_id: Sha256Id = UNBOUND_EVIDENCE_ID
    corpus_id: Sha256Id = UNBOUND_EVIDENCE_ID
    configuration_id: Sha256Id = UNBOUND_EVIDENCE_ID
    executable_id: Sha256Id = UNBOUND_EVIDENCE_ID
    lockfile_id: Sha256Id = UNBOUND_EVIDENCE_ID
    platform_id: _PlatformId = "unbound"
    python_version: Annotated[str, StringConstraints(strict=True, pattern=r"^3\.12\.[0-9]+$")] = (
        "3.12.0"
    )
    baseline: Baseline
    case_id: _Identifier
    phase: BenchmarkPhase
    repetition: _NonNegativeInt
    metric: BenchmarkMetric
    unit: MetricUnit
    value: int | float | None
    status: EvidenceStatus
    reason: _Identifier | None = None

    @model_validator(mode="after")
    def _status_and_value_agree(self) -> BenchmarkObservation:
        if self.status is EvidenceStatus.PASSED:
            if self.value is None or isinstance(self.value, bool) or self.value < 0:
                raise ValueError("passed observation requires a non-negative numeric value")
            if self.reason is not None:
                raise ValueError("passed observation cannot carry a reason")
        elif self.value is not None or self.reason is None:
            raise ValueError("non-passed observation requires reason and no value")
        expected = {
            BenchmarkMetric.LATENCY: MetricUnit.NANOSECONDS,
            BenchmarkMetric.PARSER_INVOCATIONS: MetricUnit.COUNT,
            BenchmarkMetric.STORAGE_BYTES: MetricUnit.BYTES,
            BenchmarkMetric.SELECTED_BYTES: MetricUnit.BYTES,
            BenchmarkMetric.NATIVE_BYTES: MetricUnit.BYTES,
            BenchmarkMetric.CORRECTNESS: MetricUnit.RATIO,
            BenchmarkMetric.COVERAGE: MetricUnit.RATIO,
            BenchmarkMetric.PRECISION: MetricUnit.RATIO,
            BenchmarkMetric.RECALL: MetricUnit.RATIO,
            BenchmarkMetric.RECIPROCAL_RANK: MetricUnit.RATIO,
            BenchmarkMetric.ANCHOR_CORRECTNESS: MetricUnit.RATIO,
            BenchmarkMetric.REPLAY_MATCH: MetricUnit.RATIO,
            BenchmarkMetric.STALE_REJECTION: MetricUnit.RATIO,
        }[self.metric]
        if self.unit is not expected:
            raise ValueError("metric unit does not match metric")
        if self.unit in {MetricUnit.NANOSECONDS, MetricUnit.COUNT, MetricUnit.BYTES}:
            if self.value is not None and type(self.value) is not int:
                raise ValueError("integer metric requires an integer value")
        elif self.value is not None and not 0.0 <= float(self.value) <= 1.0:
            raise ValueError("ratio metric must be between zero and one")
        if benchmark_observation_id(self.identity_projection) != self.observation_id:
            raise ValueError("benchmark observation identity mismatch")
        return self

    @property
    def identity_projection(self) -> dict[str, JsonValue]:
        """Return the complete observation facts without the declared identifier."""
        value = self.model_dump(mode="json")
        value.pop("observation_id")
        return cast(dict[str, JsonValue], value)

    @property
    def key(self) -> tuple[str, str, str, int, str]:
        """Return the unique semantic observation key."""
        return (
            self.baseline.value,
            self.case_id,
            self.phase.value,
            self.repetition,
            self.metric.value,
        )


class EvidenceCheck(DomainModel):
    """One body-free evidence assertion inside a suite."""

    check_id: _Identifier
    status: EvidenceStatus
    reason: _Identifier | None = None
    observed: int | float | None = None
    expected: int | float | None = None
    evidence_ids: tuple[Sha256Id, ...] = ()

    @model_validator(mode="after")
    def _reason_matches_status(self) -> EvidenceCheck:
        if self.status is EvidenceStatus.PASSED and self.reason is not None:
            raise ValueError("passed evidence check cannot carry a reason")
        if self.status is not EvidenceStatus.PASSED and self.reason is None:
            raise ValueError("non-passed evidence check requires a reason")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique")
        return self


class EvidenceSuite(DomainModel):
    """One complete suite assertion whose status is recomputed by the gate."""

    name: SuiteName
    status: EvidenceStatus
    expected_count: _NonNegativeInt
    observed_count: _NonNegativeInt
    checks: tuple[EvidenceCheck, ...]

    @model_validator(mode="after")
    def _checks_are_complete_and_unique(self) -> EvidenceSuite:
        ids = tuple(item.check_id for item in self.checks)
        if len(set(ids)) != len(ids):
            raise ValueError("suite check ids must be unique")
        if self.observed_count != len(self.checks):
            raise ValueError("observed_count must equal check count")
        derived = (
            EvidenceStatus.PASSED
            if self.expected_count == self.observed_count
            and all(item.status is EvidenceStatus.PASSED for item in self.checks)
            else EvidenceStatus.FAILED
        )
        if self.status is not derived:
            raise ValueError("suite status does not match complete check outcomes")
        return self


class PlatformEvidence(DomainModel):
    """Complete evidence produced by one redacted platform profile."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    evidence_id: Sha256Id
    identity_algorithm: Literal["sha256-rfc8785-v1"] = "sha256-rfc8785-v1"
    source_tree_id: Sha256Id
    protocol_id: Sha256Id
    corpus_id: Sha256Id
    configuration_id: Sha256Id
    lockfile_id: Sha256Id
    environment: EnvironmentProfile
    baselines: tuple[Baseline, ...]
    observations: tuple[BenchmarkObservation, ...]
    suites: tuple[EvidenceSuite, ...]

    @model_validator(mode="after")
    def _collections_are_unique(self) -> PlatformEvidence:
        if len(set(self.baselines)) != len(self.baselines):
            raise ValueError("baselines must be unique")
        keys = tuple(item.key for item in self.observations)
        if len(set(keys)) != len(keys):
            raise ValueError("observation keys must be unique")
        names = tuple(item.name for item in self.suites)
        if len(set(names)) != len(names):
            raise ValueError("suite names must be unique")
        return self

    @property
    def identity_projection(self) -> dict[str, JsonValue]:
        """Return every normative field except the declared evidence identifier."""
        value = self.model_dump(mode="json")
        value.pop("evidence_id")
        return cast(dict[str, JsonValue], value)

    def verify_identity(self) -> None:
        """Reject an evidence identifier that does not match canonical facts."""
        if canonical_sha256(self.identity_projection) != self.evidence_id:
            raise EvidenceIdentityMismatch("platform evidence identity mismatch")


class ReleaseGatePolicy(DomainModel):
    """Predeclared immutable release thresholds with no waiver surface."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    policy_version: Literal["0.1.0"] = "0.1.0"
    policy_id: Sha256Id
    required_platforms: tuple[_PlatformId, ...]
    required_baselines: tuple[Baseline, ...]
    required_suites: tuple[SuiteName, ...]
    required_checks: dict[SuiteName, tuple[_Identifier, ...]]
    minimum_timing_samples: Annotated[int, Field(strict=True, ge=7, le=1_000)] = 7
    bootstrap_resamples: Annotated[int, Field(strict=True, ge=1_000, le=100_000)] = 10_000
    minimum_correctness_ratio: _Ratio = 1.0
    minimum_coverage_ratio: _Ratio = 1.0
    maximum_selected_native_ratio: _Ratio = 0.5
    maximum_vulnerability_age_days: Annotated[int, Field(strict=True, ge=1, le=365)] = 30

    @model_validator(mode="after")
    def _required_sets_are_unique_and_complete(self) -> ReleaseGatePolicy:
        for name, values in (
            ("required_platforms", self.required_platforms),
            ("required_baselines", self.required_baselines),
            ("required_suites", self.required_suites),
        ):
            if not values or len(set(values)) != len(values):
                raise ValueError(f"{name} must be non-empty and unique")
        if set(self.required_baselines) != set(Baseline):
            raise ValueError("policy must require all five baselines")
        if set(self.required_checks) != set(self.required_suites):
            raise ValueError("policy required checks must cover every required suite")
        check_ids = tuple(
            check_id for suite in self.required_suites for check_id in self.required_checks[suite]
        )
        if any(not self.required_checks[suite] for suite in self.required_suites) or len(
            check_ids
        ) != len(set(check_ids)):
            raise ValueError("policy required check identifiers must be non-empty and unique")
        return self

    @property
    def identity_projection(self) -> dict[str, JsonValue]:
        """Return the policy facts hashed before observing evidence."""
        value = self.model_dump(mode="json")
        value.pop("policy_id")
        return cast(dict[str, JsonValue], value)

    def verify_identity(self) -> None:
        """Reject a policy identifier that does not match its thresholds."""
        if canonical_sha256(self.identity_projection) != self.policy_id:
            raise EvidenceIdentityMismatch("release policy identity mismatch")


class StatisticalSummary(DomainModel):
    """Deterministic median/MAD/percentile-bootstrap summary."""

    count: _PositiveInt
    median: float
    median_absolute_deviation: float
    confidence_level: Annotated[float, Field(strict=True, ge=0.95, le=0.95)] = 0.95
    confidence_lower: float
    confidence_upper: float
    unit: MetricUnit

    @model_validator(mode="after")
    def _interval_contains_median(self) -> StatisticalSummary:
        if not self.confidence_lower <= self.median <= self.confidence_upper:
            raise ValueError("confidence interval must contain median")
        return self


class GateCheck(DomainModel):
    """One exhaustive gate-policy outcome."""

    check_id: _Identifier
    passed: bool
    reason: _Identifier
    observed: int | float | None = None
    expected: int | float | None = None
    evidence_ids: tuple[Sha256Id, ...] = ()

    @model_validator(mode="after")
    def _numeric_comparison_is_finite(self) -> GateCheck:
        for value in (self.observed, self.expected):
            if value is not None and (isinstance(value, bool) or not math.isfinite(float(value))):
                raise ValueError("gate numeric comparison must be finite")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("gate evidence_ids must be unique")
        return self


class ReleaseDecision(DomainModel):
    """Authoritative immutable GO or NO-GO decision."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    decision_id: Sha256Id
    decision_at: UtcDatetime
    candidate_version: Literal["0.1.0rc1"] = "0.1.0rc1"
    source_tree_id: Sha256Id
    policy_id: Sha256Id
    protocol_id: Sha256Id
    corpus_id: Sha256Id
    configuration_id: Sha256Id
    lockfile_id: Sha256Id
    status: ReleaseStatus
    checks: tuple[GateCheck, ...]
    blockers: tuple[_Identifier, ...]
    allowed_claims: tuple[_Identifier, ...]
    prohibited_claims: tuple[_Identifier, ...]
    supported_platforms: tuple[_PlatformId, ...]

    @model_validator(mode="after")
    def _decision_is_exhaustive(self) -> ReleaseDecision:
        ids = tuple(item.check_id for item in self.checks)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("gate checks must be non-empty and unique")
        derived_blockers = tuple(item.reason for item in self.checks if not item.passed)
        if self.blockers != derived_blockers:
            raise ValueError("blockers must equal ordered failed-check reasons")
        derived_status = ReleaseStatus.GO if not self.blockers else ReleaseStatus.NO_GO
        if self.status is not derived_status:
            raise ValueError("decision status does not match blockers")
        for values, name in (
            (self.allowed_claims, "allowed_claims"),
            (self.prohibited_claims, "prohibited_claims"),
            (self.supported_platforms, "supported_platforms"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must be unique")
        if set(self.allowed_claims) & set(self.prohibited_claims):
            raise ValueError("allowed and prohibited claims must be disjoint")
        return self

    @property
    def identity_projection(self) -> dict[str, JsonValue]:
        """Return normative decision facts without self-id or observation time."""
        value = self.model_dump(mode="json")
        value.pop("decision_id")
        value.pop("decision_at")
        return cast(dict[str, JsonValue], value)

    def verify_identity(self) -> None:
        """Reject a decision identifier that does not match canonical facts."""
        if canonical_sha256(self.identity_projection) != self.decision_id:
            raise EvidenceIdentityMismatch("release decision identity mismatch")


class ReleaseEvidenceBundle(DomainModel):
    """Public machine-readable root joining policy, platform evidence and decision."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    policy: ReleaseGatePolicy
    platform_evidence: tuple[PlatformEvidence, ...]
    decision: ReleaseDecision

    @model_validator(mode="after")
    def _records_agree(self) -> ReleaseEvidenceBundle:
        self.policy.verify_identity()
        self.decision.verify_identity()
        if not self.platform_evidence:
            raise ValueError("release evidence bundle requires platform evidence")
        for item in self.platform_evidence:
            item.verify_identity()
        if self.decision.policy_id != self.policy.policy_id:
            raise ValueError("decision policy identity does not match bundle policy")
        first = self.platform_evidence[0]
        expected = (
            first.source_tree_id,
            first.protocol_id,
            first.corpus_id,
            first.configuration_id,
            first.lockfile_id,
        )
        if any(
            (
                item.source_tree_id,
                item.protocol_id,
                item.corpus_id,
                item.configuration_id,
                item.lockfile_id,
            )
            != expected
            for item in self.platform_evidence
        ):
            raise ValueError("platform evidence identities do not agree")
        if (
            self.decision.source_tree_id,
            self.decision.protocol_id,
            self.decision.corpus_id,
            self.decision.configuration_id,
            self.decision.lockfile_id,
        ) != expected:
            raise ValueError("decision identities do not match platform evidence")
        return self


def platform_evidence_id(payload: dict[str, JsonValue]) -> str:
    """Return the canonical identity for platform evidence without `evidence_id`."""
    if "evidence_id" in payload:
        raise ValueError("platform evidence identity payload must exclude evidence_id")
    return canonical_sha256(payload)


def benchmark_observation_id(payload: dict[str, JsonValue]) -> str:
    """Return the canonical identity for one raw observation without its identifier."""
    if "observation_id" in payload:
        raise ValueError("benchmark observation identity payload must exclude observation_id")
    return canonical_sha256(payload)


def release_policy_id(payload: dict[str, JsonValue]) -> str:
    """Return the canonical identity for a gate policy without `policy_id`."""
    if "policy_id" in payload:
        raise ValueError("release policy identity payload must exclude policy_id")
    return canonical_sha256(payload)


def release_decision_id(payload: dict[str, JsonValue]) -> str:
    """Return the canonical identity for a decision without id/time fields."""
    if "decision_id" in payload or "decision_at" in payload:
        raise ValueError("release decision identity payload must exclude id and decision_at")
    return canonical_sha256(payload)
