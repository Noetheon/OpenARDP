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
PREPARED_HYBRID_SEMANTIC_ALGORITHM_VERSION = "1.3.0"


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
    prepared_corpus: bool = False,
) -> AlgorithmIdentity:
    """Bind provider inference, admission and F027 allocation into replay identity."""
    extra: dict[str, JsonValue]
    if prepared_corpus:
        if not rich_first or not source_balanced:
            raise ValueError("prepared semantic profile requires rich source balance")
        version = PREPARED_HYBRID_SEMANTIC_ALGORITHM_VERSION
        relevance = RelevancePolicy()
        extra = {
            "hybrid_lexical_fallback": hybrid_lexical_fallback,
            "lexical_relevance_policy": relevance.model_dump(mode="json"),
            "lexical_relevance_policy_id": relevance.policy_id,
            "retrieval_tier_order": (
                ["minimum_relevant_lexical", "semantic"]
                if hybrid_lexical_fallback
                else ["semantic"]
            ),
            "source_balanced_semantic_admission": True,
            "semantic_max_per_document": semantic_max_per_document,
            "semantic_ranked_prefix": semantic_ranked_prefix,
            "representation_precedence": "rich_then_text",
            "prepared_corpus": "process_local_exact_snapshot_v1",
            "selected_evidence_verification": "catalog_scope_and_cas_v1",
            "budgeting": "additive_canonical_prefix_v1",
            "prepared_lexical_corpus": (
                "exact_snapshot_catalog_reconcile_v1" if hybrid_lexical_fallback else "disabled"
            ),
        }
    elif not hybrid_lexical_fallback and not source_balanced:
        version = SEMANTIC_ALGORITHM_VERSION
        extra = {}
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
    "PREPARED_HYBRID_SEMANTIC_ALGORITHM_VERSION",
    "RICH_HYBRID_SEMANTIC_ALGORITHM_VERSION",
    "SEMANTIC_ALGORITHM_NAME",
    "SEMANTIC_ALGORITHM_VERSION",
    "semantic_algorithm_identity",
]
