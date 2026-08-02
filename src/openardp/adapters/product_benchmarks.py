"""Offline corpus and treatment support for the F020 product benchmark."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, JsonValue, StringConstraints, model_validator

from openardp.domain.common import DomainModel, Sha256Id
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.product_benchmark import (
    BenchmarkMetric,
    BenchmarkProfile,
    MetricUnit,
)

_MAX_INPUT_BYTES = 1024 * 1024
_INPUT_NAMES = ("corpus-spec.json", "judgments.json", "protocol.json", "value-policy.json")
_Identifier = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]


class BenchmarkResourceLimits(DomainModel):
    """Frozen resource limits for a benchmark run."""

    maximum_blocks: int = Field(strict=True, ge=1, le=100_000)
    maximum_result_bytes: int = Field(strict=True, ge=1024, le=64 * 1024 * 1024)
    maximum_run_seconds: int = Field(strict=True, ge=1, le=86_400)
    maximum_source_bytes: int = Field(strict=True, ge=1024, le=100 * 1024 * 1024)
    maximum_workspace_bytes: int = Field(strict=True, ge=1024, le=16 * 1024 * 1024 * 1024)


class BenchmarkPrivacyPolicy(DomainModel):
    """Closed prohibited output classes."""

    forbidden: tuple[_Identifier, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _values_are_sorted_unique(self) -> BenchmarkPrivacyPolicy:
        if self.forbidden != tuple(sorted(set(self.forbidden))):
            raise ValueError("privacy classes must be sorted and unique")
        return self


class BenchmarkProtocol(DomainModel):
    """Versioned product-benchmark measurement rules."""

    protocol_version: Literal["0.1.0"]
    warmup_repetitions: int = Field(strict=True, ge=0, le=10)
    repetitions: int = Field(strict=True, ge=1, le=100)
    bootstrap_resamples: int = Field(strict=True, ge=100, le=100_000)
    confidence_level: float = Field(strict=True, ge=0.95, le=0.95)
    timing_clock: Literal["monotonic_ns"]
    timing_unit: Literal["ns"]
    statistics: tuple[_Identifier, ...] = Field(min_length=4, max_length=4)
    metrics: dict[BenchmarkMetric, MetricUnit]
    profiles: dict[BenchmarkProfile, tuple[_Identifier, ...]]
    resource_limits: BenchmarkResourceLimits
    privacy: BenchmarkPrivacyPolicy

    @model_validator(mode="after")
    def _registry_is_complete(self) -> BenchmarkProtocol:
        if set(self.metrics) != set(BenchmarkMetric):
            raise ValueError("metric registry must be complete")
        if set(self.profiles) != set(BenchmarkProfile):
            raise ValueError("profile registry must be complete")
        return self


class CorpusProfileSpec(DomainModel):
    """One generated text scale and its fixed query targets."""

    block_count: int = Field(strict=True, ge=1, le=100_000)
    query_ordinals: tuple[int, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def _targets_are_canonical(self) -> CorpusProfileSpec:
        if self.query_ordinals != tuple(sorted(set(self.query_ordinals))):
            raise ValueError("query ordinals must be sorted and unique")
        if any(item < 0 or item >= self.block_count for item in self.query_ordinals):
            raise ValueError("query ordinal is outside profile")
        return self


class RichFixtureSpec(DomainModel):
    """One immutable redistributable rich fixture."""

    format: Literal["docx", "pdf", "pptx"]
    path: Annotated[str, StringConstraints(strict=True, pattern=r"^[^/].*[^/]$")]
    sha256: Sha256Id


class BenchmarkCorpusSpec(DomainModel):
    """Frozen deterministic corpus grammar and profiles."""

    corpus_version: Literal["0.1.0"]
    generator_version: Literal["1"]
    license: Literal["CC0-1.0"]
    paragraph_template_version: Literal["control-record-v1"]
    seed: _Identifier
    synthetic_only: Literal[True]
    profiles: dict[BenchmarkProfile, CorpusProfileSpec]
    rich_fixtures: tuple[RichFixtureSpec, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def _profiles_and_formats_are_exact(self) -> BenchmarkCorpusSpec:
        if set(self.profiles) != {
            BenchmarkProfile.SMOKE,
            BenchmarkProfile.REFERENCE,
            BenchmarkProfile.SCALE,
        }:
            raise ValueError("corpus profiles must contain smoke, reference and scale")
        formats = tuple(item.format for item in self.rich_fixtures)
        if formats != tuple(sorted(set(formats))) or set(formats) != {"docx", "pdf", "pptx"}:
            raise ValueError("rich fixture formats must be sorted and complete")
        return self


class QueryRule(DomainModel):
    """Mechanical query and expected-fact derivation."""

    expected_document: Literal["generated-profile-source"]
    expected_rank: Literal[1]
    fact_id_format: Literal["fact-{ordinal:06d}"]
    query_id_format: Literal["query-{profile}-{ordinal:06d}"]
    token_derivation: Literal["sha256(seed-colon-ordinal)-first-16"]


class BenchmarkJudgments(DomainModel):
    """Fixed mechanical judgments without an external evaluator."""

    judgment_version: Literal["0.1.0"]
    budgets: tuple[int, ...] = Field(min_length=3, max_length=3)
    query_rule: QueryRule
    rich_expected_terms: dict[Literal["docx", "pdf", "pptx"], tuple[str, ...]]

    @model_validator(mode="after")
    def _budgets_and_formats_are_exact(self) -> BenchmarkJudgments:
        if self.budgets != tuple(sorted(set(self.budgets))) or any(
            item < 1 for item in self.budgets
        ):
            raise ValueError("budgets must be positive, sorted and unique")
        if set(self.rich_expected_terms) != {"docx", "pdf", "pptx"}:
            raise ValueError("rich judgments must cover every rich format")
        return self


class HardFailurePolicy(DomainModel):
    """Safety and correctness thresholds that dominate performance."""

    maximum_stale_incidents: Literal[0]
    maximum_unchanged_parser_invocations: Literal[0]
    minimum_anchor_correctness: float = Field(strict=True, ge=1.0, le=1.0)
    minimum_context_coverage: float = Field(strict=True, ge=1.0, le=1.0)
    minimum_precision: float = Field(strict=True, ge=1.0, le=1.0)
    minimum_recall: float = Field(strict=True, ge=1.0, le=1.0)
    minimum_replay_match: float = Field(strict=True, ge=1.0, le=1.0)


class UnconditionalPolicy(DomainModel):
    """Thresholds required for an unconditional useful result."""

    break_even_horizon: int = Field(strict=True, ge=1, le=100)
    maximum_context_selected_native_ratio: float = Field(strict=True, ge=0.0, le=1.0)
    maximum_search_p95_ns_at_100k: int = Field(strict=True, ge=1)
    maximum_status_p95_ns: int = Field(strict=True, ge=1)
    minimum_reference_blocks: int = Field(strict=True, ge=1, le=100_000)
    minimum_scale_blocks: int = Field(strict=True, ge=1, le=100_000)
    required_rich_formats: tuple[Literal["docx", "pdf", "pptx"], ...]


class SamplePolicy(DomainModel):
    """Minimum valid repeated timings."""

    minimum_timing_samples: int = Field(strict=True, ge=1, le=100)
    warmups: int = Field(strict=True, ge=0, le=10)


class BenchmarkValuePolicy(DomainModel):
    """Frozen three-state value decision policy."""

    policy_version: Literal["0.1.0"]
    decision_version: Literal["0.1.0"]
    hard_failures: HardFailurePolicy
    required_for_unconditional: UnconditionalPolicy
    required_reference_treatments: tuple[
        Literal["raw_reparse", "persisted_native", "openardp"], ...
    ]
    sample_policy: SamplePolicy


@dataclass(frozen=True, slots=True)
class BenchmarkInputs:
    """Validated input quartet and exact canonical identities."""

    protocol: BenchmarkProtocol
    corpus: BenchmarkCorpusSpec
    judgments: BenchmarkJudgments
    policy: BenchmarkValuePolicy
    protocol_id: str
    corpus_id: str
    judgments_id: str
    policy_id: str


@dataclass(frozen=True, slots=True)
class GeneratedCorpus:
    """One generated source and body-free manifest facts."""

    profile: BenchmarkProfile
    source: Path
    source_sha256: str
    source_bytes: int
    block_count: int
    manifest: Path


def _unique_pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _read_closed_json(path: Path) -> dict[str, JsonValue]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("benchmark input must be a regular file")
    data = path.read_bytes()
    if len(data) > _MAX_INPUT_BYTES:
        raise ValueError("benchmark input exceeds size limit")
    value = json.loads(data, object_pairs_hook=_unique_pairs)
    if not isinstance(value, dict):
        raise ValueError("benchmark input root must be an object")
    return value


def load_benchmark_inputs(root: Path) -> BenchmarkInputs:
    """Load the exact normative benchmark quartet with strict closed validation."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("benchmark input root must be a directory")
    observed = tuple(sorted(path.name for path in root.glob("*.json")))
    if observed != _INPUT_NAMES:
        raise ValueError("benchmark input inventory is incomplete or unexpected")
    raw = {name: _read_closed_json(root / name) for name in _INPUT_NAMES}
    protocol = BenchmarkProtocol.model_validate_json(canonical_json_bytes(raw["protocol.json"]))
    corpus = BenchmarkCorpusSpec.model_validate_json(canonical_json_bytes(raw["corpus-spec.json"]))
    judgments = BenchmarkJudgments.model_validate_json(canonical_json_bytes(raw["judgments.json"]))
    policy = BenchmarkValuePolicy.model_validate_json(
        canonical_json_bytes(raw["value-policy.json"])
    )
    if protocol.repetitions != policy.sample_policy.minimum_timing_samples:
        raise ValueError("protocol repetitions and policy samples differ")
    if protocol.warmup_repetitions != policy.sample_policy.warmups:
        raise ValueError("protocol and policy warmups differ")
    return BenchmarkInputs(
        protocol=protocol,
        corpus=corpus,
        judgments=judgments,
        policy=policy,
        protocol_id=canonical_sha256(raw["protocol.json"]),
        corpus_id=canonical_sha256(raw["corpus-spec.json"]),
        judgments_id=canonical_sha256(raw["judgments.json"]),
        policy_id=canonical_sha256(raw["value-policy.json"]),
    )


def corpus_token(seed: str, ordinal: int) -> str:
    """Derive one unique query token without persisted random state."""
    if ordinal < 0 or ordinal > 100_000:
        raise ValueError("corpus ordinal is outside bounds")
    digest = hashlib.sha256(f"{seed}:{ordinal}".encode()).hexdigest()[:16]
    return f"needle-{digest}"


def _paragraph(seed: str, ordinal: int) -> str:
    token = corpus_token(seed, ordinal)
    return (
        f"Fact fact-{ordinal:06d} uses verification token {token}. "
        f"Control family {ordinal % 97:02d} preserves immutable evidence and provenance. "
        f"Review cohort {ordinal % 31:02d} treats this synthetic record as untrusted data."
    )


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def generate_text_corpus(
    inputs: BenchmarkInputs,
    profile: BenchmarkProfile,
    output: Path,
) -> GeneratedCorpus:
    """Generate one exact bounded synthetic source into a fresh directory."""
    if profile not in inputs.corpus.profiles:
        raise ValueError("profile has no generated text corpus")
    if output.exists():
        raise FileExistsError("corpus output already exists")
    output.mkdir(parents=True)
    specification = inputs.corpus.profiles[profile]
    payload = (
        "\n\n".join(
            _paragraph(inputs.corpus.seed, ordinal) for ordinal in range(specification.block_count)
        )
        + "\n"
    ).encode("utf-8")
    if len(payload) > inputs.protocol.resource_limits.maximum_source_bytes:
        raise ValueError("generated corpus exceeds source limit")
    source = output / f"{profile.value}.txt"
    _atomic_write(source, payload)
    source_sha256 = "sha256:" + hashlib.sha256(payload).hexdigest()
    manifest_value: dict[str, JsonValue] = {
        "block_count": specification.block_count,
        "corpus_id": inputs.corpus_id,
        "generator_version": inputs.corpus.generator_version,
        "license": inputs.corpus.license,
        "profile": profile.value,
        "query_ids": [
            f"query-{profile.value}-{ordinal:06d}" for ordinal in specification.query_ordinals
        ],
        "source": {
            "byte_length": len(payload),
            "logical_name": source.name,
            "sha256": source_sha256,
        },
        "synthetic_only": True,
    }
    manifest = output / "corpus-manifest.json"
    _atomic_write(manifest, canonical_json_bytes(manifest_value) + b"\n")
    return GeneratedCorpus(
        profile=profile,
        source=source,
        source_sha256=source_sha256,
        source_bytes=len(payload),
        block_count=specification.block_count,
        manifest=manifest,
    )


__all__ = [
    "BenchmarkCorpusSpec",
    "BenchmarkInputs",
    "BenchmarkProtocol",
    "BenchmarkValuePolicy",
    "GeneratedCorpus",
    "corpus_token",
    "generate_text_corpus",
    "load_benchmark_inputs",
]
