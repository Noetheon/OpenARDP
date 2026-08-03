"""Eligibility classification shared by legacy and ranked context profiles."""

from __future__ import annotations

from dataclasses import dataclass

from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode, EvidenceRepresentation
from openardp.domain.context_compilation import (
    CandidateFreshness,
    ContextCandidate,
    ContextSelectionPolicy,
)
from openardp.domain.context_relevance import RelevancePolicy
from openardp.ports.context import ContextIntegrityFailure

_SENSITIVITY_RANK = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
    Sensitivity.UNKNOWN: 4,
}

_MODE_PREFERRED: dict[ContextMode, frozenset[EvidenceRepresentation]] = {
    ContextMode.SUMMARY: frozenset({EvidenceRepresentation.SUMMARY}),
    ContextMode.EXACT: frozenset({EvidenceRepresentation.EXACT}),
    ContextMode.NUMERIC: frozenset(
        {EvidenceRepresentation.EXACT, EvidenceRepresentation.STRUCTURED}
    ),
    ContextMode.VISUAL: frozenset({EvidenceRepresentation.VISUAL_HANDLE}),
    ContextMode.VERIFICATION: frozenset({EvidenceRepresentation.EXACT}),
    ContextMode.MIXED: frozenset({EvidenceRepresentation.EXACT, EvidenceRepresentation.STRUCTURED}),
}


def required_representations(policy: ContextSelectionPolicy) -> set[EvidenceRepresentation]:
    """Derive honest evidence requirements from explicit policy or mode defaults."""
    if policy.required_evidence:
        return set(policy.required_evidence)
    return set(_MODE_PREFERRED[policy.mode])


def candidate_total_order_key(candidate: ContextCandidate) -> tuple[object, ...]:
    """Return the historical F008/F026 deterministic total order key."""
    return (
        not candidate.high_value,
        candidate.retrieval_tier,
        -(
            candidate.semantic.score_millionths
            if candidate.semantic is not None
            else candidate.term_coverage
        ),
        -candidate.occurrences,
        str(candidate.scope.document_id),
        candidate.scope.version_id,
        candidate.scope.representation_id,
        candidate.source_order,
        candidate.representation.value,
        candidate.evidence_id,
    )


@dataclass(frozen=True, slots=True)
class ClassifiedCandidates:
    """Policy-classified discovery partition before allocation and budget selection."""

    ordered: tuple[ContextCandidate, ...]
    rejected: tuple[tuple[ContextCandidate, str], ...]
    stale: tuple[ContextCandidate, ...]


def classify_candidates(
    candidates: tuple[ContextCandidate, ...],
    policy: ContextSelectionPolicy,
    *,
    relevance_policy: RelevancePolicy | None = None,
) -> ClassifiedCandidates:
    """Partition every discovered subject exactly once under the declared policy."""
    valid: list[ContextCandidate] = []
    rejected: list[tuple[ContextCandidate, str]] = []
    stale: list[ContextCandidate] = []
    seen: set[tuple[str, ...]] = set()
    maximum_rank = _SENSITIVITY_RANK[policy.maximum_sensitivity]
    for candidate in candidates:
        if candidate.freshness is not CandidateFreshness.CURRENT:
            stale.append(candidate)
            continue
        if candidate.trust.zone not in policy.allowed_trust_zones:
            rejected.append((candidate, "trust_zone_not_allowed"))
            continue
        if _SENSITIVITY_RANK[candidate.trust.sensitivity] > maximum_rank:
            rejected.append((candidate, "sensitivity_exceeded"))
            continue
        key = (
            str(candidate.scope.document_id),
            candidate.scope.version_id,
            candidate.scope.representation_id,
            candidate.evidence_id,
            candidate.representation.value,
        )
        if key in seen:
            rejected.append((candidate, "duplicate_candidate"))
            continue
        seen.add(key)
        if (
            relevance_policy is not None
            and candidate.representation is not EvidenceRepresentation.VISUAL_HANDLE
        ):
            if candidate.relevance is None:
                raise ContextIntegrityFailure("candidate_relevance_missing")
            if candidate.relevance.policy_id != relevance_policy.policy_id:
                raise ContextIntegrityFailure("candidate_relevance_policy_mismatch")
            if not candidate.relevance.meets_minimum:
                rejected.append((candidate, "insufficient_relevance"))
                continue
        high_value = candidate.representation in _MODE_PREFERRED[policy.mode]
        valid.append(candidate.model_copy(update={"high_value": high_value}))
    valid.sort(key=candidate_total_order_key)
    return ClassifiedCandidates(
        ordered=tuple(valid),
        rejected=tuple(rejected),
        stale=tuple(stale),
    )


__all__ = [
    "ClassifiedCandidates",
    "candidate_total_order_key",
    "classify_candidates",
    "required_representations",
]
