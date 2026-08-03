"""Provider-specific identity composition without provider-specific evidence."""

from __future__ import annotations

from pydantic import JsonValue

from openardp.domain.context_compilation import AlgorithmIdentity
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_sha256
from openardp.domain.semantic_retrieval import (
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
)

SEMANTIC_ALGORITHM_NAME = "openardp.semantic-context-ranked"
SEMANTIC_ALGORITHM_VERSION = "1.0.0"
HYBRID_SEMANTIC_ALGORITHM_VERSION = "1.1.0"
RICH_HYBRID_SEMANTIC_ALGORITHM_VERSION = "1.2.0"


def semantic_algorithm_identity(
    recipe: SemanticProviderRecipe,
    policy: SemanticRetrievalPolicy,
    limits: SemanticRetrievalLimits,
    allocation: LexicalAllocationPolicy,
    *,
    hybrid_lexical_fallback: bool = False,
    source_balanced: bool = False,
    semantic_max_per_document: int = 32,
    semantic_ranked_prefix: int = 4,
    rich_first: bool = False,
) -> AlgorithmIdentity:
    """Bind provider inference, admission and F027 allocation into replay identity."""
    if not hybrid_lexical_fallback and not source_balanced:
        version = SEMANTIC_ALGORITHM_VERSION
        extra: dict[str, JsonValue] = {}
    else:
        version = (
            RICH_HYBRID_SEMANTIC_ALGORITHM_VERSION
            if rich_first
            else HYBRID_SEMANTIC_ALGORITHM_VERSION
        )
        relevance = RelevancePolicy()
        extra = {
            "hybrid_lexical_fallback": hybrid_lexical_fallback,
            "lexical_relevance_policy": relevance.model_dump(mode="json"),
            "lexical_relevance_policy_id": relevance.policy_id,
            "retrieval_tier_order": ["minimum_relevant_lexical", "semantic"],
            "source_balanced_semantic_admission": source_balanced,
            "semantic_max_per_document": semantic_max_per_document,
            "semantic_ranked_prefix": semantic_ranked_prefix,
        }
        if rich_first:
            extra["representation_precedence"] = "rich_then_text"
    return AlgorithmIdentity(
        name=SEMANTIC_ALGORITHM_NAME,
        version=version,
        config_hash=canonical_sha256(
            {
                "algorithm": SEMANTIC_ALGORITHM_NAME,
                "version": version,
                "provider_recipe": recipe.model_dump(mode="json"),
                "provider_recipe_id": recipe.recipe_id,
                "semantic_policy": policy.model_dump(mode="json"),
                "semantic_policy_id": policy.policy_id,
                "provider_limits": limits.model_dump(mode="json"),
                "allocation_policy": allocation.model_dump(mode="json"),
                "allocation_policy_id": allocation.policy_id,
                "abstention_notice": "no_semantic_evidence",
                "evidence_verification": "exact_cas_catalog_v1",
                **extra,
            }
        ),
    )


__all__ = [
    "HYBRID_SEMANTIC_ALGORITHM_VERSION",
    "RICH_HYBRID_SEMANTIC_ALGORITHM_VERSION",
    "SEMANTIC_ALGORITHM_NAME",
    "SEMANTIC_ALGORITHM_VERSION",
    "semantic_algorithm_identity",
]
