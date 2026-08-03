"""Pure lexical ranking and source-allocation contracts."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    SourceLocator,
    TrustZone,
)
from openardp.domain.context import EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    CandidateFreshness,
    ContextBlockProvenance,
    ContextCandidate,
)
from openardp.domain.context_ranking import (
    LexicalAllocationPolicy,
    allocate_lexical_candidates,
    lexical_candidate_rank_key,
)
from openardp.domain.context_relevance import CandidateRelevance, RelevancePolicy
from openardp.domain.storage import StoredObject


def _candidate(
    document: int,
    evidence: int,
    *,
    score: int = 500_000,
    matched_weight: int = 2,
    matched_signals: int = 2,
    body: int | None = None,
    coverage: int = 2,
    occurrences: int = 2,
) -> ContextCandidate:
    document_id = UUID(f"01890f62-24e8-7c00-8000-{document:012d}")
    block_id = UUID(f"12345678-1234-4234-9234-{evidence:012d}")
    scope = VersionScope(
        document_id=document_id,
        version_id="sha256:" + f"{document:x}"[-1] * 64,
        representation_id="sha256:" + f"{(document + 7):x}"[-1] * 64,
    )
    policy = RelevancePolicy()
    return ContextCandidate(
        evidence_id=str(block_id),
        scope=scope,
        provenance=ContextBlockProvenance(
            record_type="block",
            document_id=document_id,
            version_id=scope.version_id,
            representation_id=scope.representation_id,
            block_id=block_id,
            source=SourceLocator(extraction_method="synthetic"),
        ),
        representation=EvidenceRepresentation.EXACT,
        source_order=evidence,
        body_object=StoredObject(
            object_id="sha256:" + f"{body if body is not None else evidence:x}"[-1] * 64,
            byte_length=1,
        ),
        body_media_type="application/json",
        trust=DataTrustClassification(
            zone=TrustZone.EXTERNAL_UNTRUSTED,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.PUBLIC,
        ),
        freshness=CandidateFreshness.CURRENT,
        term_coverage=coverage,
        occurrences=occurrences,
        reason_code="fts_lexical_match",
        high_value=True,
        relevance=CandidateRelevance(
            policy_id=policy.policy_id,
            total_signals=4,
            matched_signals=matched_signals,
            total_weight=4,
            matched_weight=matched_weight,
            score_millionths=score,
            volatile_time_matched=True,
            meets_minimum=True,
        ),
    )


def test_policy_identity_binds_quota_and_required_controls() -> None:
    """Every decision-significant allocation control has a canonical identity."""
    default = LexicalAllocationPolicy()
    changed = LexicalAllocationPolicy(max_per_document=15)

    assert default.policy_id == LexicalAllocationPolicy().policy_id
    assert default.policy_id != changed.policy_id
    with pytest.raises(ValidationError):
        LexicalAllocationPolicy(deduplicate_exact_bodies=False)
    with pytest.raises(ValidationError):
        LexicalAllocationPolicy(fair_round_robin=False)


def test_rank_preserves_lexical_strength_then_breaks_ties_with_relevance() -> None:
    """Coverage and occurrence strength dominate normalized relevance tie-breakers."""
    ranked = sorted(
        (
            _candidate(
                1,
                1,
                score=250_000,
                matched_weight=1,
                matched_signals=1,
                coverage=3,
                occurrences=5,
            ),
            _candidate(
                2,
                2,
                score=750_000,
                matched_weight=3,
                matched_signals=3,
                coverage=2,
                occurrences=9,
            ),
            _candidate(3, 3, score=500_000, matched_weight=2, matched_signals=1),
            _candidate(4, 4, score=500_000, matched_weight=2, matched_signals=2),
        ),
        key=lexical_candidate_rank_key,
    )

    assert [item.evidence_id[-12:] for item in ranked] == [
        "000000000001",
        "000000000002",
        "000000000004",
        "000000000003",
    ]


def test_exact_body_deduplication_retains_only_best_ranked_provenance() -> None:
    """One CAS body occurs once and every later provenance is rejected explicitly."""
    weak = _candidate(1, 1, score=250_000, matched_weight=1, matched_signals=1, body=9)
    strong = _candidate(2, 2, score=750_000, matched_weight=3, matched_signals=3, body=9)

    result = allocate_lexical_candidates((weak, strong), LexicalAllocationPolicy())

    assert result.ordered == (strong,)
    assert result.rejected == ((weak, "duplicate_content_candidate"),)


def test_round_robin_is_fair_deterministic_and_input_order_independent() -> None:
    """Every available document gets a first item before any document gets a second."""
    candidates = (
        _candidate(1, 1, score=750_000, matched_weight=3, matched_signals=3),
        _candidate(1, 2, score=500_000),
        _candidate(2, 3, score=500_000),
        _candidate(2, 4, score=250_000, matched_weight=1, matched_signals=1),
    )

    policy = LexicalAllocationPolicy(ranked_prefix=0)
    forward = allocate_lexical_candidates(candidates, policy)
    reverse = allocate_lexical_candidates(tuple(reversed(candidates)), policy)

    assert [item.evidence_id[-12:] for item in forward.ordered] == [
        "000000000001",
        "000000000003",
        "000000000002",
        "000000000004",
    ]
    assert forward == reverse


def test_hard_document_quota_rejects_tail_without_padding_other_sources() -> None:
    """Quota is a maximum, never a reservation or weak-evidence source requirement."""
    candidates = (*(_candidate(1, evidence) for evidence in range(1, 5)), _candidate(2, 9))

    result = allocate_lexical_candidates(
        candidates,
        LexicalAllocationPolicy(max_per_document=2, ranked_prefix=0),
    )

    assert [item.evidence_id[-12:] for item in result.ordered] == [
        "000000000001",
        "000000000009",
        "000000000002",
    ]
    assert [item.evidence_id[-12:] for item, _reason in result.rejected] == [
        "000000000003",
        "000000000004",
    ]
    assert {reason for _item, reason in result.rejected} == {"source_quota_exceeded"}


def test_ranked_prefix_preserves_early_relevance_before_diversification() -> None:
    """A small global prefix protects answer rank before fair source interleaving."""
    candidates = (
        _candidate(1, 1, coverage=4),
        _candidate(1, 2, coverage=3),
        _candidate(1, 3, coverage=2),
        _candidate(2, 4, coverage=1),
    )

    result = allocate_lexical_candidates(
        candidates,
        LexicalAllocationPolicy(ranked_prefix=2),
    )

    assert [item.evidence_id[-12:] for item in result.ordered] == [
        "000000000001",
        "000000000002",
        "000000000003",
        "000000000004",
    ]
