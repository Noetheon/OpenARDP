"""Pure invariants for provider-neutral semantic retrieval."""

from __future__ import annotations

import math

import pytest

from openardp.domain.identity import canonical_sha256
from openardp.domain.semantic_retrieval import (
    PreparedSemanticCorpus,
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
    SemanticScore,
    quantize_cosine,
)


def _recipe() -> SemanticProviderRecipe:
    return SemanticProviderRecipe(
        provider="fake-semantic",
        provider_version="1.0.0",
        model_id="fixture/multilingual",
        model_revision="a" * 40,
        model_bundle_id="sha256:" + "b" * 64,
        dimensions=3,
        max_tokens=16,
        query_prefix="query: ",
        passage_prefix="passage: ",
        pooling="mean_attention_mask",
        normalization="l2",
        similarity="cosine",
        quantizer="half_away_from_zero_millionths_v1",
        transformers_version="0.0.0",
        torch_version="0.0.0",
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-2.0, -1_000_000),
        (-0.0000005, -1),
        (0.0, 0),
        (0.0000005, 1),
        (0.8000004, 800_000),
        (2.0, 1_000_000),
    ],
)
def test_cosine_quantizer_is_bounded_and_half_away_from_zero(value: float, expected: int) -> None:
    """Clamp the cosine range and make exact half-step behavior portable."""
    assert quantize_cosine(value) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_cosine_quantizer_rejects_non_finite_scores(value: float) -> None:
    """Reject NaN and infinities before they can enter deterministic ordering."""
    with pytest.raises(ValueError, match="finite"):
        quantize_cosine(value)


def test_recipe_policy_and_limits_have_complete_stable_identities() -> None:
    """Bind inference and admission behavior to canonical exact identities."""
    recipe = _recipe()
    assert recipe.recipe_id.startswith("sha256:")
    assert recipe.recipe_id == _recipe().recipe_id
    policy = SemanticRetrievalPolicy()
    assert policy.minimum_score_millionths == 800_000
    assert policy.policy_id == SemanticRetrievalPolicy().policy_id
    limits = SemanticRetrievalLimits(max_passages=2, max_cache_entries=2, max_response_entries=2)
    assert limits.max_passages == 2
    with pytest.raises(ValueError, match="cache"):
        SemanticRetrievalLimits(max_passages=2, max_cache_entries=1)


def test_passage_and_score_keep_only_exact_identity_and_fixed_point_result() -> None:
    """Keep provider output body-free and tied to exact evidence/object IDs."""
    recipe = _recipe()
    passage = SemanticPassage(
        evidence_id="evidence-1",
        object_id="sha256:" + "c" * 64,
        text="untrusted body",
    )
    score = SemanticScore(
        evidence_id=passage.evidence_id,
        object_id=passage.object_id,
        provider_recipe_id=recipe.recipe_id,
        score_millionths=812_345,
        cache_hit=False,
    )
    assert "text" not in score.model_dump(mode="json")
    assert score.score_millionths == 812_345


def test_prepared_corpus_identity_binds_order_recipe_limits_and_never_contains_body() -> None:
    """Make the process-local handle deterministic without retaining passage text."""
    recipe = _recipe()
    passages = (
        _passage := SemanticPassage(
            evidence_id="evidence-1",
            object_id="sha256:" + "c" * 64,
            text="untrusted body",
        ),
    )
    limits = SemanticRetrievalLimits(max_passages=1, max_cache_entries=1)
    prepared = PreparedSemanticCorpus.from_passages(recipe.recipe_id, passages, limits)
    assert prepared.corpus_id == canonical_sha256(
        {
            "domain": "openardp.prepared-semantic-corpus",
            "version": 1,
            "provider_recipe_id": recipe.recipe_id,
            "passages": [{"evidence_id": _passage.evidence_id, "object_id": _passage.object_id}],
            "limits": limits.model_dump(mode="json"),
        }
    )
    assert prepared.passage_count == 1
    assert prepared.total_text_bytes == len(b"untrusted body")
    assert "untrusted body" not in str(prepared.model_dump(mode="json"))
    changed = PreparedSemanticCorpus.from_passages(
        recipe.recipe_id,
        (
            SemanticPassage(
                evidence_id="evidence-2",
                object_id=_passage.object_id,
                text=_passage.text,
            ),
        ),
        limits,
    )
    assert changed.corpus_id != prepared.corpus_id
