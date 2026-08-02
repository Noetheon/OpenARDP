"""Pure F021 freshness-benchmark contracts, evaluation and reporting."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import Field, JsonValue, StringConstraints, model_validator

from openardp.domain.common import DomainModel, Sha256Id
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import IntegrityCoverage, SourceFreshness, StatusMode

_MAX_JSON_BYTES = 16 * 1024 * 1024
_Profile = Literal["reference", "scale"]
_Identifier = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]


class FreshnessBaseline(DomainModel):
    """Frozen F020 status result used for honest before/after comparison."""

    environment_id: Sha256Id
    f020_summary_path: Literal[
        "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/summary.json"
    ]
    f020_summary_sha256: Sha256Id
    p95_ns: dict[_Profile, int]


class FreshnessCorpus(DomainModel):
    """Frozen F020 corpus source and required block cardinalities."""

    f020_corpus_spec_path: Literal["benchmarks/product-value/v0.1.0/corpus-spec.json"]
    f020_corpus_spec_sha256: Sha256Id
    profiles: dict[_Profile, int]


class FreshnessTarget(DomainModel):
    """Non-waivable default-path latency and operation limits."""

    default_maximum_p95_ns: int = Field(strict=True, ge=1)
    default_maximum_aggregate_loads_per_request: Literal[0]
    default_maximum_block_object_verifications_per_request: Literal[0]
    default_maximum_parser_invocations_per_request: Literal[0]
    default_required_source_inspections_per_request: Literal[1]
    default_maximum_verifier_invocations_per_request: Literal[0]


class FreshnessPrivacy(DomainModel):
    """Closed prohibited evidence classes."""

    forbidden: tuple[_Identifier, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _privacy_is_canonical(self) -> FreshnessPrivacy:
        if self.forbidden != tuple(sorted(set(self.forbidden))):
            raise ValueError("privacy classes must be sorted and unique")
        return self


class FreshnessProtocol(DomainModel):
    """Frozen F021 measurement and decision protocol."""

    protocol_version: Literal["0.1.0"]
    baseline: FreshnessBaseline
    corpus: FreshnessCorpus
    modes: tuple[StatusMode, StatusMode]
    privacy: FreshnessPrivacy
    repetitions: Literal[7]
    required_counters: tuple[_Identifier, ...]
    statistics: tuple[Literal["p50", "p95", "raw_samples"], ...]
    target: FreshnessTarget
    timing_clock: Literal["monotonic_ns"]
    timing_unit: Literal["ns"]
    warmup_repetitions: Literal[1]

    @model_validator(mode="after")
    def _registries_are_exact(self) -> FreshnessProtocol:
        if self.modes != (StatusMode.HEAD, StatusMode.FULL):
            raise ValueError("benchmark modes must be HEAD then FULL")
        if self.statistics != ("p50", "p95", "raw_samples"):
            raise ValueError("benchmark statistics are not canonical")
        required = (
            "aggregate_loads",
            "block_object_verifications",
            "parser_invocations",
            "source_inspections",
            "verifier_invocations",
        )
        if self.required_counters != required:
            raise ValueError("benchmark counters are not canonical")
        if self.corpus.profiles != {"reference": 10_000, "scale": 100_000}:
            raise ValueError("benchmark corpus scales changed")
        return self


class FreshnessCounters(DomainModel):
    """Structural work performed by one timed status request."""

    aggregate_loads: int = Field(strict=True, ge=0)
    block_object_verifications: int = Field(strict=True, ge=0)
    parser_invocations: int = Field(strict=True, ge=0)
    source_inspections: int = Field(strict=True, ge=0)
    verifier_invocations: int = Field(strict=True, ge=0)


class FreshnessObservation(DomainModel):
    """One retained status request and its body-free structural evidence."""

    observation_id: Sha256Id
    environment_id: Sha256Id
    profile: _Profile
    mode: StatusMode
    repetition: int = Field(strict=True, ge=0, le=6)
    block_count: int = Field(strict=True, ge=1, le=100_000)
    source_bytes: int = Field(strict=True, ge=1)
    elapsed_ns: int = Field(strict=True, ge=1)
    freshness: SourceFreshness
    integrity_coverage: IntegrityCoverage
    counters: FreshnessCounters

    @model_validator(mode="after")
    def _identity_and_result_are_truthful(self) -> FreshnessObservation:
        projection = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != canonical_sha256(projection):
            raise ValueError("observation identity mismatch")
        expected = (
            IntegrityCoverage.HEAD if self.mode is StatusMode.HEAD else IntegrityCoverage.FULL
        )
        if self.freshness is not SourceFreshness.CURRENT or self.integrity_coverage is not expected:
            raise ValueError("benchmark status result is not exact and successful")
        return self


class FreshnessSummary(DomainModel):
    """Deterministic nearest-rank latency summary for one profile and mode."""

    summary_id: Sha256Id
    profile: _Profile
    mode: StatusMode
    sample_count: Literal[7]
    p50_ns: int = Field(strict=True, ge=1)
    p95_ns: int = Field(strict=True, ge=1)
    raw_samples_ns: tuple[int, ...] = Field(min_length=7, max_length=7)
    observation_ids: tuple[Sha256Id, ...] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def _summary_identity_matches(self) -> FreshnessSummary:
        projection = self.model_dump(mode="json", exclude={"summary_id"})
        if self.summary_id != canonical_sha256(projection):
            raise ValueError("summary identity mismatch")
        return self


class FreshnessCheck(DomainModel):
    """One non-waivable target or structural policy result."""

    check_id: _Identifier
    passed: bool
    expected: JsonValue
    observed: JsonValue


class FreshnessDecision(DomainModel):
    """F021 bounded optimization outcome derived from retained evidence."""

    decision_id: Sha256Id
    outcome: Literal["PASS", "FAIL"]
    checks: tuple[FreshnessCheck, ...] = Field(min_length=1)
    improvement_factors: dict[_Profile, float]

    @model_validator(mode="after")
    def _decision_is_consistent(self) -> FreshnessDecision:
        expected = "PASS" if all(item.passed for item in self.checks) else "FAIL"
        if self.outcome != expected:
            raise ValueError("decision outcome does not match checks")
        projection = self.model_dump(mode="json", exclude={"decision_id"})
        if self.decision_id != canonical_sha256(projection):
            raise ValueError("decision identity mismatch")
        return self


def _unique_pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def read_json_object(path: Path) -> dict[str, JsonValue]:
    """Read one bounded regular JSON object while rejecting duplicate members."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("benchmark JSON must be a regular file")
    payload = path.read_bytes()
    if len(payload) > _MAX_JSON_BYTES:
        raise ValueError("benchmark JSON exceeds limit")
    value = json.loads(payload, object_pairs_hook=_unique_pairs)
    if not isinstance(value, dict):
        raise ValueError("benchmark JSON root must be an object")
    return value


def load_freshness_protocol(repository_root: Path) -> tuple[FreshnessProtocol, str]:
    """Load the frozen protocol and verify both referenced F020 artifacts."""
    root = repository_root.resolve(strict=True)
    path = root / "benchmarks/freshness/v0.1.0/protocol.json"
    raw = read_json_object(path)
    protocol = FreshnessProtocol.model_validate_json(canonical_json_bytes(raw))
    references = (
        (protocol.baseline.f020_summary_path, protocol.baseline.f020_summary_sha256),
        (protocol.corpus.f020_corpus_spec_path, protocol.corpus.f020_corpus_spec_sha256),
    )
    for relative, expected in references:
        payload = (root / relative).read_bytes()
        observed = "sha256:" + hashlib.sha256(payload).hexdigest()
        if observed != expected:
            raise ValueError("frozen F020 benchmark input drifted")
    return protocol, canonical_sha256(raw)


def make_observation(**values: object) -> FreshnessObservation:
    """Create one content-identified observation from typed caller values."""
    projection = cast(dict[str, JsonValue], values)
    return FreshnessObservation.model_validate_json(
        canonical_json_bytes({**projection, "observation_id": canonical_sha256(projection)})
    )


def _nearest_rank(values: Sequence[int], probability: float) -> int:
    if not values:
        raise ValueError("percentile requires observations")
    return sorted(values)[max(0, math.ceil(probability * len(values)) - 1)]


def summarize_observations(
    protocol: FreshnessProtocol,
    observations: Sequence[FreshnessObservation],
) -> tuple[FreshnessSummary, ...]:
    """Recompute all four exact profile/mode timing groups."""
    groups: defaultdict[tuple[str, StatusMode], list[FreshnessObservation]] = defaultdict(list)
    for item in observations:
        groups[(item.profile, item.mode)].append(item)
    expected_groups = {
        (profile, mode) for profile in protocol.corpus.profiles for mode in protocol.modes
    }
    if set(groups) != expected_groups:
        raise ValueError("benchmark timing groups are incomplete or unexpected")
    summaries: list[FreshnessSummary] = []
    for profile, mode in sorted(groups, key=lambda item: (item[0], item[1].value)):
        ordered = tuple(sorted(groups[(profile, mode)], key=lambda item: item.repetition))
        if tuple(item.repetition for item in ordered) != tuple(range(protocol.repetitions)):
            raise ValueError("benchmark repetitions are incomplete")
        if any(item.block_count != protocol.corpus.profiles[profile] for item in ordered):
            raise ValueError("observation block count differs from protocol")
        values = tuple(item.elapsed_ns for item in ordered)
        projection: dict[str, JsonValue] = {
            "profile": profile,
            "mode": mode.value,
            "sample_count": protocol.repetitions,
            "p50_ns": _nearest_rank(values, 0.5),
            "p95_ns": _nearest_rank(values, 0.95),
            "raw_samples_ns": list(values),
            "observation_ids": [item.observation_id for item in ordered],
        }
        summaries.append(
            FreshnessSummary.model_validate_json(
                canonical_json_bytes({**projection, "summary_id": canonical_sha256(projection)})
            )
        )
    return tuple(summaries)


def _check(
    check_id: str,
    *,
    expected: JsonValue,
    observed: JsonValue,
    passed: bool,
) -> FreshnessCheck:
    return FreshnessCheck(
        check_id=check_id,
        expected=expected,
        observed=observed,
        passed=passed,
    )


def decide_freshness(
    protocol: FreshnessProtocol,
    observations: Sequence[FreshnessObservation],
    summaries: Sequence[FreshnessSummary],
) -> FreshnessDecision:
    """Apply latency and exact-operation requirements without waiver behavior."""
    checks: list[FreshnessCheck] = []
    factors: dict[_Profile, float] = {}
    by_summary = {(item.profile, item.mode): item for item in summaries}
    for profile in ("reference", "scale"):
        head_summary = by_summary[(profile, StatusMode.HEAD)]
        target = protocol.target.default_maximum_p95_ns
        checks.append(
            _check(
                f"{profile}-head-p95",
                expected=target,
                observed=head_summary.p95_ns,
                passed=head_summary.p95_ns <= target,
            )
        )
        factors[profile] = round(protocol.baseline.p95_ns[profile] / head_summary.p95_ns, 6)
    for item in observations:
        counters = item.counters
        prefix = f"{item.profile}-{item.mode.value.lower()}-{item.repetition}"
        expected = (
            (0, 0, 0, 1, 0) if item.mode is StatusMode.HEAD else (1, item.block_count, 0, 1, 1)
        )
        observed = (
            counters.aggregate_loads,
            counters.block_object_verifications,
            counters.parser_invocations,
            counters.source_inspections,
            counters.verifier_invocations,
        )
        checks.append(
            _check(
                f"{prefix}-counters",
                expected=list(expected),
                observed=list(observed),
                passed=observed == expected,
            )
        )
    projection: dict[str, JsonValue] = {
        "outcome": "PASS" if all(item.passed for item in checks) else "FAIL",
        "checks": [item.model_dump(mode="json") for item in checks],
        "improvement_factors": cast(dict[str, JsonValue], factors),
    }
    return FreshnessDecision.model_validate_json(
        canonical_json_bytes({**projection, "decision_id": canonical_sha256(projection)})
    )


def render_report(
    protocol: FreshnessProtocol,
    summaries: Sequence[FreshnessSummary],
    decision: FreshnessDecision,
) -> bytes:
    """Render the deterministic bounded human projection."""
    by_summary = {(item.profile, item.mode): item for item in summaries}
    lines = [
        "# F021 Incremental Freshness Benchmark",
        "",
        f"**Outcome:** `{decision.outcome}`",
        "",
        "## Measured results",
        "",
        "| Scale | Blocks | Mode | p50 | p95 | F020 p95 | Improvement |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for profile in ("reference", "scale"):
        for mode in (StatusMode.HEAD, StatusMode.FULL):
            summary = by_summary[(profile, mode)]
            baseline = protocol.baseline.p95_ns[profile]
            improvement = (
                f"{decision.improvement_factors[profile]:.3f}x"
                if mode is StatusMode.HEAD
                else "not compared"
            )
            lines.append(
                f"| `{profile}` | {protocol.corpus.profiles[profile]} | `{mode.value}` | "
                f"{summary.p50_ns / 1_000_000:.3f} ms | {summary.p95_ns / 1_000_000:.3f} ms | "
                f"{baseline / 1_000_000:.3f} ms | {improvement} |"
            )
    failed = tuple(item.check_id for item in decision.checks if not item.passed)
    lines.extend(
        [
            "",
            "## Policy result",
            "",
            "- Default HEAD p95 target: at most "
            f"{protocol.target.default_maximum_p95_ns / 1_000_000:.0f} ms at both scales.",
            "- Default structural target: one exact source inspection and zero "
            "aggregate loads, block verifications, parser calls or full-verifier calls.",
            f"- Failed checks: {', '.join(failed) if failed else 'none'}.",
            "",
            "## Assurance boundary",
            "",
            "`HEAD` proves exact current source identity against one atomic READY catalog "
            "header. It does not read every stored block and therefore does not claim "
            "arbitrary CAS tamper detection.",
            "",
            "`FULL` retains the exhaustive native, manifest, projection and block verification "
            "path. Its cost is reported separately and is intentionally not represented as "
            "constant-time.",
            "",
            "## Limitations",
            "",
            "- The timing decision binds to the committed macOS arm64 reference environment; "
            "shared CI checks semantics and counters.",
            "- The corpus is deterministic and synthetic. Real-world and semantic-use-case "
            "evidence remain F024 and F025.",
            "- Exact source hashing still scales with authoritative source bytes; the optimized "
            "claim is sublinear in prepared block count.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def canonical_file(model: DomainModel | Mapping[str, JsonValue]) -> bytes:
    """Return newline-terminated canonical JSON bytes for one evidence artifact."""
    value = model.model_dump(mode="json") if isinstance(model, DomainModel) else dict(model)
    return canonical_json_bytes(cast(JsonValue, value)) + b"\n"


__all__ = [
    "FreshnessCounters",
    "FreshnessDecision",
    "FreshnessObservation",
    "FreshnessProtocol",
    "FreshnessSummary",
    "canonical_file",
    "decide_freshness",
    "load_freshness_protocol",
    "make_observation",
    "read_json_object",
    "render_report",
    "summarize_observations",
]
