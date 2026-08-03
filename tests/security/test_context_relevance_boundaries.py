"""Failure, privacy and integrity boundaries for minimum-relevance evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompileLimits,
    ContextSelectionPolicy,
)
from openardp.domain.context_relevance import RelevancePolicy, evaluate_candidate_relevance
from openardp.ports.context import ContextIntegrityFailure, ContextLimitExceeded
from openardp.services.context_compiler import classify_candidates, receipt_object_bytes
from tests.integration.test_context_compiler import _request
from tests.integration.test_context_relevance import _compiler
from tests.integration.test_rich_ingestion import _TamperingStore
from tests.unit.test_context_relevance import _candidate, _snapshot, _StaticSource


def test_missing_or_foreign_observation_fails_closed(tmp_path: Path) -> None:
    """The relevance profile never treats absent or policy-drifted facts as eligible."""
    _store, candidate = _candidate(tmp_path, "alpha beta")
    policy = RelevancePolicy()
    selection = ContextSelectionPolicy(
        mode=ContextMode.EXACT,
        maximum_sensitivity=Sensitivity.UNKNOWN,
    )

    with pytest.raises(ContextIntegrityFailure, match="relevance_missing"):
        classify_candidates((candidate,), selection, relevance_policy=policy)

    foreign = RelevancePolicy(minimum_score_millionths=500_000)
    observation = evaluate_candidate_relevance("alpha beta", "alpha beta", foreign)
    with pytest.raises(ContextIntegrityFailure, match="policy_mismatch"):
        classify_candidates(
            (candidate.model_copy(update={"relevance": observation}),),
            selection,
            relevance_policy=policy,
        )


def test_corrupt_candidate_object_is_integrity_failure_not_abstention(tmp_path: Path) -> None:
    """CAS corruption remains a typed failure and cannot become a successful zero-result."""
    store, candidate = _candidate(tmp_path, "alpha beta " + "x" * 2_000)
    assert candidate.body_object is not None
    source = RelevanceObservingCandidateSource(
        _TamperingStore(store, candidate.body_object.object_id),
        (_StaticSource((candidate,)),),
        RelevancePolicy(),
    )

    with pytest.raises(ContextIntegrityFailure, match="relevance_object_invalid"):
        source.discover("alpha", _snapshot(), ContextCompileLimits(), lambda: False)


def test_body_and_task_limits_fail_instead_of_abstaining(tmp_path: Path) -> None:
    """Bound exhaustion remains distinguishable from an evidence judgment."""
    store, candidate = _candidate(tmp_path, "alpha beta " + "x" * 2_000)
    source = RelevanceObservingCandidateSource(
        store,
        (_StaticSource((candidate,)),),
        RelevancePolicy(max_signals=1),
    )

    with pytest.raises(ContextLimitExceeded, match="relevance_task_limit"):
        source.discover("alpha beta", _snapshot(), ContextCompileLimits(), lambda: False)
    with pytest.raises(ContextLimitExceeded, match="relevance_body_limit"):
        source.discover(
            "alpha",
            _snapshot(),
            ContextCompileLimits(max_body_bytes=1_024),
            lambda: False,
        )


def test_discovery_truncation_limit_is_failure_not_confident_abstention(
    tmp_path: Path,
) -> None:
    """An unevaluated candidate tail cannot be mislabeled as no relevant evidence."""
    store, candidate = _candidate(tmp_path, "unrelated")
    source = RelevanceObservingCandidateSource(
        store,
        (_StaticSource((candidate, candidate)),),
        RelevancePolicy(),
    )

    with pytest.raises(ContextLimitExceeded, match="max_discovered"):
        source.discover(
            "alpha beta",
            _snapshot(),
            ContextCompileLimits(max_discovered=1, max_candidates=1),
            lambda: False,
        )


def test_receipt_relevance_audit_is_body_task_and_path_free(tmp_path: Path) -> None:
    """Audit facts retain only counts, scores and identities, never source data."""
    compiler, corpus = _compiler(tmp_path, RelevancePolicy())
    marker = "ZZRELEVANCESECRETMARKER"
    persisted = compiler.compile_and_persist(
        _request(corpus.document_ids, 1_000_000, task=f"alpha evidence {marker}")
    )

    receipt = receipt_object_bytes(persisted.result.receipt).decode("utf-8")
    assert marker not in receipt
    assert str(corpus.text_path) not in receipt
    assert "alpha text evidence alpha" not in receipt
    assert "score_millionths" in receipt
