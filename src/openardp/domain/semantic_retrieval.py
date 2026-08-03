"""Provider-neutral invariants for optional semantic evidence retrieval."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from openardp.domain.common import DomainModel, Sha256Id
from openardp.domain.identity import canonical_sha256

SEMANTIC_SCORE_SCALE = 1_000_000
DEFAULT_SEMANTIC_SCORE_FLOOR = 800_000
SemanticEvidenceId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256)]


class SemanticProviderRecipe(DomainModel):
    """Exact identity of one model-specific scoring implementation."""

    provider: str = Field(min_length=1, max_length=128)
    provider_version: str = Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
    model_id: str = Field(min_length=1, max_length=256)
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    model_bundle_id: Sha256Id
    dimensions: int = Field(strict=True, ge=1, le=65_536)
    max_tokens: int = Field(strict=True, ge=1, le=131_072)
    query_prefix: str = Field(min_length=1, max_length=64)
    passage_prefix: str = Field(min_length=1, max_length=64)
    pooling: str = Field(pattern=r"^mean_attention_mask$")
    normalization: str = Field(pattern=r"^l2$")
    similarity: str = Field(pattern=r"^cosine$")
    quantizer: str = Field(pattern=r"^half_away_from_zero_millionths_v1$")
    transformers_version: str = Field(min_length=1, max_length=64)
    torch_version: str = Field(min_length=1, max_length=64)

    @property
    def recipe_id(self) -> Sha256Id:
        """Return the canonical identity of every inference-significant field."""
        return canonical_sha256(self.model_dump(mode="json"))


class SemanticRetrievalLimits(DomainModel):
    """Portable parent-enforced request and worker bounds."""

    max_passages: int = Field(default=10_000, strict=True, ge=1, le=10_000)
    max_total_text_bytes: int = Field(default=64 * 1024 * 1024, strict=True, ge=1024)
    max_passage_bytes: int = Field(default=8 * 1024 * 1024, strict=True, ge=1)
    batch_size: int = Field(default=16, strict=True, ge=1, le=256)
    max_cache_entries: int = Field(default=10_000, strict=True, ge=1, le=10_000)
    max_response_entries: int = Field(default=10_000, strict=True, ge=1, le=10_000)
    timeout_seconds: int = Field(default=900, strict=True, ge=1, le=3_600)

    @model_validator(mode="after")
    def _nested_counts_are_bounded(self) -> Self:
        if self.max_cache_entries < self.max_passages:
            raise ValueError("semantic cache must cover one maximum passage request")
        if self.max_response_entries < self.max_passages:
            raise ValueError("semantic response must cover one maximum passage request")
        return self


class SemanticRetrievalPolicy(DomainModel):
    """Frozen candidate admission configuration above provider scores."""

    name: str = Field(default="openardp-semantic-e5", min_length=1, max_length=128)
    version: str = Field(
        default="1.0.0",
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    )
    minimum_score_millionths: int = Field(
        default=DEFAULT_SEMANTIC_SCORE_FLOOR,
        strict=True,
        ge=-SEMANTIC_SCORE_SCALE,
        le=SEMANTIC_SCORE_SCALE,
    )
    top_k: int = Field(default=128, strict=True, ge=1, le=512)
    require_volatile_time_match: bool = True

    @property
    def policy_id(self) -> Sha256Id:
        """Return the canonical identity of every admission field."""
        return canonical_sha256(self.model_dump(mode="json"))


class SemanticPassage(DomainModel):
    """One exact verified text passed across the semantic provider port."""

    evidence_id: SemanticEvidenceId
    object_id: Sha256Id
    text: str = Field(min_length=1, max_length=8 * 1024 * 1024)


class SemanticScore(DomainModel):
    """Body/vector-free fixed-point result for one exact passage."""

    evidence_id: SemanticEvidenceId
    object_id: Sha256Id
    provider_recipe_id: Sha256Id
    score_millionths: int = Field(
        strict=True,
        ge=-SEMANTIC_SCORE_SCALE,
        le=SEMANTIC_SCORE_SCALE,
    )
    cache_hit: bool


class SemanticCandidateObservation(DomainModel):
    """Internal body-free semantic eligibility observation attached to a candidate."""

    provider_recipe_id: Sha256Id
    policy_id: Sha256Id
    score_millionths: int = Field(
        strict=True,
        ge=-SEMANTIC_SCORE_SCALE,
        le=SEMANTIC_SCORE_SCALE,
    )
    volatile_time_matched: bool
    meets_minimum: bool
    cache_hit: bool


def quantize_cosine(value: float) -> int:
    """Quantize a finite cosine using half-away-from-zero millionths."""
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("semantic score must be finite")
    bounded = min(1.0, max(-1.0, value))
    scaled = bounded * SEMANTIC_SCORE_SCALE
    return int(scaled + 0.5) if scaled >= 0 else int(scaled - 0.5)


__all__ = [
    "DEFAULT_SEMANTIC_SCORE_FLOOR",
    "SEMANTIC_SCORE_SCALE",
    "SemanticCandidateObservation",
    "SemanticPassage",
    "SemanticProviderRecipe",
    "SemanticRetrievalLimits",
    "SemanticRetrievalPolicy",
    "SemanticScore",
    "quantize_cosine",
]
