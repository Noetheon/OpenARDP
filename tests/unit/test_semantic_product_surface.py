"""Model-free product-surface profile and replay resolution tests."""

from __future__ import annotations

import pytest

from openardp.domain.context_compilation import AlgorithmIdentity
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.semantic_retrieval import (
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
)
from openardp.interfaces.context_composition import (
    RetrievalProfile,
    retrieval_profile_for_algorithm,
)
from openardp.ports.context import ContextConfigurationMismatch
from openardp.services.context_compiler import context_algorithm_identity
from openardp.services.semantic_retrieval import semantic_algorithm_identity


def _recipe() -> SemanticProviderRecipe:
    return SemanticProviderRecipe(
        provider="fake-semantic",
        provider_version="1.0.0",
        model_id="example/model",
        model_revision="1" * 40,
        model_bundle_id="sha256:" + "2" * 64,
        dimensions=3,
        max_tokens=32,
        query_prefix="query: ",
        passage_prefix="passage: ",
        pooling="mean_attention_mask",
        normalization="l2",
        similarity="cosine",
        quantizer="half_away_from_zero_millionths_v1",
        transformers_version="4.55.0",
        torch_version="2.8.0",
    )


@pytest.mark.parametrize(
    "algorithm",
    (
        context_algorithm_identity(),
        context_algorithm_identity(RelevancePolicy()),
        context_algorithm_identity(RelevancePolicy(), LexicalAllocationPolicy()),
    ),
)
def test_every_builtin_lexical_algorithm_resolves_to_lexical(
    algorithm: AlgorithmIdentity,
) -> None:
    """Classify every replay-compatible provider-free algorithm exactly."""
    assert retrieval_profile_for_algorithm(algorithm) is RetrievalProfile.LEXICAL


def test_f029_algorithm_resolves_to_semantic() -> None:
    """Classify the exact Rich-first hybrid F029 identity as semantic."""
    algorithm = semantic_algorithm_identity(
        _recipe(),
        SemanticRetrievalPolicy(),
        SemanticRetrievalLimits(),
        LexicalAllocationPolicy(),
        hybrid_lexical_fallback=True,
        source_balanced=True,
        rich_first=True,
    )
    assert retrieval_profile_for_algorithm(algorithm) is RetrievalProfile.SEMANTIC


def test_unknown_algorithm_fails_closed() -> None:
    """Never reinterpret an unknown persisted algorithm as a supported profile."""
    algorithm = AlgorithmIdentity(
        name="example.unknown",
        version="1.0.0",
        config_hash="sha256:" + "3" * 64,
    )
    with pytest.raises(ContextConfigurationMismatch, match="algorithm_mismatch"):
        retrieval_profile_for_algorithm(algorithm)
