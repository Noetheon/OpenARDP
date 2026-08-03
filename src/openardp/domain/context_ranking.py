"""Deterministic lexical ranking, exact deduplication and source allocation."""

from __future__ import annotations

from collections import defaultdict
from typing import Self

from pydantic import Field, model_validator

from openardp.domain.common import DomainModel, Sha256Id
from openardp.domain.context_compilation import ContextCandidate
from openardp.domain.identity import canonical_sha256

DEFAULT_MAX_PER_DOCUMENT = 16


class LexicalAllocationPolicy(DomainModel):
    """Immutable configuration for provider-free candidate allocation."""

    name: str = Field(default="openardp-lexical-source-allocation", min_length=1, max_length=128)
    version: str = Field(
        default="1.0.0",
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    )
    max_per_document: int = Field(
        default=DEFAULT_MAX_PER_DOCUMENT,
        strict=True,
        ge=1,
        le=512,
    )
    ranked_prefix: int = Field(default=4, strict=True, ge=0, le=64)
    deduplicate_exact_bodies: bool = True
    fair_round_robin: bool = True

    @model_validator(mode="after")
    def _required_controls_are_enabled(self) -> Self:
        if not self.deduplicate_exact_bodies:
            raise ValueError("exact body deduplication must be enabled")
        if not self.fair_round_robin:
            raise ValueError("fair round robin must be enabled")
        return self

    @property
    def policy_id(self) -> Sha256Id:
        """Return the canonical identity of all decision-significant fields."""
        return canonical_sha256(self.model_dump(mode="json"))


class AllocationResult(DomainModel):
    """Exhaustive allocation partition after candidate eligibility checks."""

    ordered: tuple[ContextCandidate, ...]
    rejected: tuple[tuple[ContextCandidate, str], ...]


def lexical_candidate_rank_key(candidate: ContextCandidate) -> tuple[object, ...]:
    """Return the cross-platform total rank key for one eligible candidate."""
    relevance = candidate.relevance
    semantic = candidate.semantic
    return (
        not candidate.high_value,
        candidate.retrieval_tier,
        -(semantic.score_millionths if semantic is not None else candidate.term_coverage),
        -candidate.occurrences,
        -(relevance.score_millionths if relevance is not None else 0),
        -(relevance.matched_weight if relevance is not None else 0),
        -(relevance.matched_signals if relevance is not None else 0),
        str(candidate.scope.document_id),
        candidate.scope.version_id,
        candidate.scope.representation_id,
        candidate.source_order,
        candidate.representation.value,
        candidate.evidence_id,
    )


def _candidate_identity(candidate: ContextCandidate) -> tuple[str, ...]:
    return (
        str(candidate.scope.document_id),
        candidate.scope.version_id,
        candidate.scope.representation_id,
        candidate.evidence_id,
        candidate.representation.value,
    )


def allocate_lexical_candidates(
    candidates: tuple[ContextCandidate, ...],
    policy: LexicalAllocationPolicy,
) -> AllocationResult:
    """Rank, exact-deduplicate, quota and fairly interleave eligible candidates."""
    ranked = sorted(candidates, key=lexical_candidate_rank_key)
    unique: list[ContextCandidate] = []
    rejected: list[tuple[ContextCandidate, str]] = []
    seen_bodies: set[str] = set()
    for candidate in ranked:
        body_id = candidate.body_object.object_id if candidate.body_object is not None else None
        if body_id is not None and body_id in seen_bodies:
            rejected.append((candidate, "duplicate_content_candidate"))
            continue
        if body_id is not None:
            seen_bodies.add(body_id)
        unique.append(candidate)

    queues: dict[tuple[str, str], list[ContextCandidate]] = defaultdict(list)
    for candidate in unique:
        source = (str(candidate.scope.document_id), candidate.scope.version_id)
        if len(queues[source]) >= policy.max_per_document:
            rejected.append((candidate, "source_quota_exceeded"))
            continue
        queues[source].append(candidate)

    admitted = [candidate for queue in queues.values() for candidate in queue]
    prefix = sorted(admitted, key=lexical_candidate_rank_key)[: policy.ranked_prefix]
    prefix_ids = {_candidate_identity(candidate) for candidate in prefix}
    for source in queues:
        queues[source] = [
            candidate
            for candidate in queues[source]
            if _candidate_identity(candidate) not in prefix_ids
        ]
    ordered: list[ContextCandidate] = list(prefix)
    tiers = sorted({candidate.retrieval_tier for queue in queues.values() for candidate in queue})
    for tier in tiers:
        tier_queues = {
            source: [candidate for candidate in queue if candidate.retrieval_tier == tier]
            for source, queue in queues.items()
        }
        source_order = sorted(
            (source for source in tier_queues if tier_queues[source]),
            key=lambda source: lexical_candidate_rank_key(tier_queues[source][0]),
        )
        round_index = 0
        while True:
            emitted = False
            for source in source_order:
                queue = tier_queues[source]
                if round_index < len(queue):
                    ordered.append(queue[round_index])
                    emitted = True
            if not emitted:
                break
            round_index += 1
    return AllocationResult(ordered=tuple(ordered), rejected=tuple(rejected))


__all__ = [
    "DEFAULT_MAX_PER_DOCUMENT",
    "AllocationResult",
    "LexicalAllocationPolicy",
    "allocate_lexical_candidates",
    "lexical_candidate_rank_key",
]
