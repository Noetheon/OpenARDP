"""Minimum-relevance and explicit-abstention compiler integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.domain.common import TrustZone
from openardp.domain.context_relevance import RelevancePolicy
from openardp.ports.context import ContextConfigurationMismatch
from openardp.services.context_compiler import (
    ContextCompilerService,
    context_algorithm_identity,
)
from tests.integration.test_context_compiler import _mixed_corpus, _request

RELEVANCE_NAMESPACE = "https://openardp.example/ns/context-relevance/v1"


def _compiler(tmp_path: Path, policy: RelevancePolicy) -> tuple[ContextCompilerService, object]:
    corpus = _mixed_corpus(tmp_path)
    raw = (
        TextLexicalCandidateSource(corpus.store, corpus.catalog),
        RichLexicalCandidateSource(
            corpus.store,
            corpus.catalog,
            representation_verifier=lambda _artifacts: None,
        ),
    )
    source = RelevanceObservingCandidateSource(corpus.store, raw, policy)
    compiler = ContextCompilerService(
        corpus.store,
        corpus.catalog,
        Utf8ByteEstimator(),
        (source,),
        relevance_policy=policy,
    )
    return compiler, corpus


def test_empty_discovery_emits_explicit_body_free_abstention(tmp_path: Path) -> None:
    """A valid no-match is successful and explicit in bundle plus receipt."""
    compiler, corpus = _compiler(tmp_path, RelevancePolicy())

    result = compiler.compile(
        _request(
            corpus.document_ids,
            1_000_000,
            task="NASA approved AGI deployment budget 2027",
        )
    )

    assert result.bundle.items == ()
    assert [warning.code for warning in result.bundle.warnings] == ["no_relevant_evidence"]
    assert "no_relevant_evidence" in {notice.code for notice in result.receipt.notices}
    assert result.receipt.selected == ()
    assert result.receipt.rejected == ()
    assert result.receipt.budget.bundle_used <= result.receipt.budget.bundle_ceiling


def test_all_below_floor_are_rejected_once_and_abstain(tmp_path: Path) -> None:
    """Incidental matches remain auditable rejections and never enter context."""
    policy = RelevancePolicy(minimum_score_millionths=250_001)
    compiler, corpus = _compiler(tmp_path, policy)

    result = compiler.compile(
        _request(corpus.document_ids, 1_000_000, task="alpha beta gamma delta")
    )

    assert result.bundle.items == ()
    assert result.receipt.selected == ()
    assert result.receipt.rejected
    assert {decision.reason_code for decision in result.receipt.rejected} == {
        "insufficient_relevance"
    }
    assert all(RELEVANCE_NAMESPACE in decision.extensions for decision in result.receipt.rejected)
    assert "no_relevant_evidence" in {notice.code for notice in result.receipt.notices}


def test_strong_verified_matches_survive_with_auditable_relevance(tmp_path: Path) -> None:
    """The relevance floor preserves both verified text and rich evidence."""
    policy = RelevancePolicy()
    compiler, corpus = _compiler(tmp_path, policy)

    result = compiler.compile(_request(corpus.document_ids, 1_000_000, task="alpha evidence"))

    assert {item.provenance.record_type for item in result.bundle.items} == {
        "block",
        "evidence_projection",
    }
    assert result.bundle.warnings == ()
    assert result.receipt.rejected == ()
    assert all(RELEVANCE_NAMESPACE in decision.extensions for decision in result.receipt.selected)
    assert all(
        decision.extensions[RELEVANCE_NAMESPACE]["meets_minimum"] is True
        for decision in result.receipt.selected
    )


def test_policy_identity_is_separate_from_legacy_and_replay_mismatch_fails(
    tmp_path: Path,
) -> None:
    """Persisted output binds the exact relevance policy and cannot silently float."""
    policy = RelevancePolicy()
    compiler, corpus = _compiler(tmp_path, policy)
    request = _request(corpus.document_ids, 1_000_000, task="alpha evidence")

    persisted = compiler.compile_and_persist(request)

    assert persisted.result.receipt.algorithm != context_algorithm_identity()
    assert persisted.result.receipt.algorithm == context_algorithm_identity(policy)
    incompatible = ContextCompilerService(
        corpus.store,
        corpus.catalog,
        Utf8ByteEstimator(),
        (),
    )
    with pytest.raises(ContextConfigurationMismatch, match="algorithm"):
        incompatible.replay("alpha evidence", persisted.record.receipt_id)


def test_budget_only_omission_does_not_claim_relevance_abstention(tmp_path: Path) -> None:
    """Candidates that pass relevance but do not fit remain budget omissions."""
    compiler, corpus = _compiler(tmp_path, RelevancePolicy())

    result = compiler.compile(_request(corpus.document_ids, 1_200, task="alpha evidence"))

    assert result.receipt.selected == ()
    assert result.receipt.omitted
    assert result.receipt.rejected == ()
    assert "no_relevant_evidence" not in {notice.code for notice in result.receipt.notices}
    assert "no_relevant_evidence" not in {warning.code for warning in result.bundle.warnings}


def test_trust_only_rejection_does_not_claim_relevance_abstention(tmp_path: Path) -> None:
    """Trust-policy rejection remains distinct from insufficient relevance."""
    compiler, corpus = _compiler(tmp_path, RelevancePolicy())
    request = _request(corpus.document_ids, 1_000_000, task="alpha evidence")
    request = request.model_copy(
        update={
            "policy": request.policy.model_copy(
                update={"allowed_trust_zones": (TrustZone.LOCAL_TRUSTED,)}
            )
        }
    )

    result = compiler.compile(request)

    assert result.receipt.selected == ()
    assert result.receipt.rejected
    assert {decision.reason_code for decision in result.receipt.rejected} == {
        "trust_zone_not_allowed"
    }
    assert "no_relevant_evidence" not in {notice.code for notice in result.receipt.notices}
