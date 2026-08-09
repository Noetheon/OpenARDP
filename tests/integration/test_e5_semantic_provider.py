"""Opt-in exact real-model test for the isolated multilingual E5 adapter."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.domain.semantic_retrieval import SemanticPassage, SemanticRetrievalLimits


@pytest.mark.skipif(
    "OPENARDP_E5_BUNDLE" not in os.environ,
    reason="exact external E5 bundle not configured",
)
def test_real_e5_provider_is_offline_multilingual_and_reuses_passage_cache() -> None:
    """Score German-to-English meaning in one spawned worker and reuse exact vectors."""
    bundle = Path(os.environ["OPENARDP_E5_BUNDLE"])
    lock = Path("model-bundles/multilingual-e5-small-v1/source-lock.json")
    passages = (
        SemanticPassage(
            evidence_id="relevant",
            object_id="sha256:" + "1" * 64,
            text="NASA adds Scientific, Technical and Ethical Robustness as a principle.",
        ),
        SemanticPassage(
            evidence_id="unrelated",
            object_id="sha256:" + "2" * 64,
            text="A recipe explains how to bake sourdough bread.",
        ),
    )
    limits = SemanticRetrievalLimits(
        max_passages=2,
        max_cache_entries=2,
        max_response_entries=2,
        timeout_seconds=180,
    )
    with IsolatedE5SemanticProvider(bundle, expected_source_lock=lock) as provider:
        first = provider.score(
            "Welches zusätzliche Robustheitsprinzip nennt NASA?",
            passages,
            limits,
            lambda: False,
        )
        second = provider.score(
            "Welches zusätzliche Robustheitsprinzip nennt NASA?",
            passages,
            limits,
            lambda: False,
        )
        prepared = provider.prepare(passages, limits, lambda: False)
        compact = provider.score_prepared(
            "Welches zusätzliche Robustheitsprinzip nennt NASA?",
            prepared,
            limits,
            lambda: False,
        )
    by_id = {score.evidence_id: score for score in first}
    assert by_id["relevant"].score_millionths > by_id["unrelated"].score_millionths
    assert by_id["relevant"].score_millionths >= 800_000
    assert all(score.cache_hit is False for score in first)
    assert all(score.cache_hit is True for score in second)
    assert [score.score_millionths for score in first] == [
        score.score_millionths for score in second
    ]
    assert [score.score_millionths for score in second] == [
        score.score_millionths for score in compact
    ]
    assert all(score.cache_hit is True for score in compact)
