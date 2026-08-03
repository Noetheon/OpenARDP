"""Pure orchestration helpers for relevance-aware context compilation."""

from __future__ import annotations

from pydantic import JsonValue

from openardp.domain.context_compilation import (
    CONTEXT_ALGORITHM_NAME,
    CONTEXT_ALGORITHM_VERSION,
    PROVENANCE_TARGET_PERCENT,
    RESPONSE_RESERVE_PERCENT,
    AlgorithmIdentity,
    ContextBundleNotice,
    ContextCandidate,
    ReceiptNotice,
)
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.identity import canonical_sha256
from openardp.domain.search import MAX_QUERY_ITEMS, MAX_TERM_CHARACTERS

RELEVANCE_ALGORITHM_NAME = "openardp.lexical-context-relevance"
RELEVANCE_ALGORITHM_VERSION = "1.0.0"
RELEVANCE_EXTENSION_NAMESPACE = "https://openardp.example/ns/context-relevance/v1"
SEMANTIC_EXTENSION_NAMESPACE = "https://openardp.example/ns/semantic-retrieval/v1"
RANKING_ALGORITHM_NAME = "openardp.lexical-context-ranked"
RANKING_ALGORITHM_VERSION = "1.0.0"


def context_algorithm_identity(
    relevance_policy: RelevancePolicy | None = None,
    allocation_policy: LexicalAllocationPolicy | None = None,
) -> AlgorithmIdentity:
    """Return the exact legacy, minimum-relevance or ranked algorithm identity."""
    legacy = AlgorithmIdentity(
        name=CONTEXT_ALGORITHM_NAME,
        version=CONTEXT_ALGORITHM_VERSION,
        config_hash=canonical_sha256(
            {
                "algorithm": CONTEXT_ALGORITHM_NAME,
                "version": CONTEXT_ALGORITHM_VERSION,
                "max_lexical_items": MAX_QUERY_ITEMS,
                "max_lexical_item_characters": MAX_TERM_CHARACTERS,
                "ordering": [
                    "high_value_desc",
                    "term_coverage_desc",
                    "occurrences_desc",
                    "scope_asc",
                    "source_order_asc",
                    "representation_asc",
                    "evidence_id_asc",
                ],
                "response_reserve_percent": RESPONSE_RESERVE_PERCENT,
                "provenance_target_percent": PROVENANCE_TARGET_PERCENT,
            }
        ),
    )
    if relevance_policy is None and allocation_policy is None:
        return legacy
    if relevance_policy is None:
        raise ValueError("allocation policy requires a relevance policy")
    relevance = AlgorithmIdentity(
        name=RELEVANCE_ALGORITHM_NAME,
        version=RELEVANCE_ALGORITHM_VERSION,
        config_hash=canonical_sha256(
            {
                "algorithm": RELEVANCE_ALGORITHM_NAME,
                "version": RELEVANCE_ALGORITHM_VERSION,
                "base_algorithm": legacy.model_dump(mode="json"),
                "relevance_policy": relevance_policy.model_dump(mode="json"),
                "relevance_policy_id": relevance_policy.policy_id,
                "rejection_reason": "insufficient_relevance",
                "abstention_notice": "no_relevant_evidence",
            }
        ),
    )
    if allocation_policy is None:
        return relevance
    return AlgorithmIdentity(
        name=RANKING_ALGORITHM_NAME,
        version=RANKING_ALGORITHM_VERSION,
        config_hash=canonical_sha256(
            {
                "algorithm": RANKING_ALGORITHM_NAME,
                "version": RANKING_ALGORITHM_VERSION,
                "base_algorithm": relevance.model_dump(mode="json"),
                "allocation_policy": allocation_policy.model_dump(mode="json"),
                "allocation_policy_id": allocation_policy.policy_id,
                "ordering": [
                    "high_value_desc",
                    "term_coverage_desc",
                    "occurrences_desc",
                    "relevance_score_desc",
                    "matched_weight_desc",
                    "matched_signals_desc",
                    "scope_asc",
                    "source_order_asc",
                    "representation_asc",
                    "evidence_id_asc",
                ],
                "dedupe_reason": "duplicate_content_candidate",
                "quota_reason": "source_quota_exceeded",
                "ranked_prefix": allocation_policy.ranked_prefix,
            }
        ),
    )


def is_relevance_abstention(
    discovered: tuple[ContextCandidate, ...],
    ordered: tuple[ContextCandidate, ...],
    rejected: tuple[tuple[ContextCandidate, str], ...],
    policy: RelevancePolicy | None,
) -> bool:
    """Return whether a successful empty selection is solely a relevance outcome."""
    relevance_rejections = sum(reason == "insufficient_relevance" for _item, reason in rejected)
    return (
        policy is not None
        and not ordered
        and (not discovered or (relevance_rejections > 0 and relevance_rejections == len(rejected)))
    )


def compilation_notices(
    *,
    truncated: bool,
    relevance_abstained: bool,
    semantic_abstained: bool = False,
) -> tuple[tuple[ContextBundleNotice, ...], tuple[ReceiptNotice, ...]]:
    """Build stable bundle warnings and matching body-free receipt notices."""
    warnings: list[ContextBundleNotice] = []
    notices: list[ReceiptNotice] = []
    if truncated:
        notices.append(ReceiptNotice(code="discovery_truncated"))
        warnings.append(
            ContextBundleNotice(
                code="discovery_truncated",
                message="Discovery or evaluation was truncated at configured limits.",
            )
        )
    if relevance_abstained:
        notices.append(ReceiptNotice(code="no_relevant_evidence"))
        warnings.append(
            ContextBundleNotice(
                code="no_relevant_evidence",
                message="No verified candidate met the configured minimum relevance policy.",
            )
        )
    if semantic_abstained:
        notices.append(ReceiptNotice(code="no_semantic_evidence"))
        warnings.append(
            ContextBundleNotice(
                code="no_semantic_evidence",
                message="No verified candidate met the configured semantic retrieval policy.",
            )
        )
    return tuple(warnings), tuple(notices)


def relevance_extensions(candidate: ContextCandidate) -> dict[str, JsonValue]:
    """Return optional body-free lexical and semantic decision extensions."""
    extensions: dict[str, JsonValue] = {}
    if candidate.relevance is not None:
        extensions[RELEVANCE_EXTENSION_NAMESPACE] = candidate.relevance.extension_value()
    if candidate.semantic is not None:
        extensions[SEMANTIC_EXTENSION_NAMESPACE] = candidate.semantic.model_dump(mode="json")
    return extensions


__all__ = [
    "RANKING_ALGORITHM_NAME",
    "RANKING_ALGORITHM_VERSION",
    "RELEVANCE_ALGORITHM_NAME",
    "RELEVANCE_ALGORITHM_VERSION",
    "RELEVANCE_EXTENSION_NAMESPACE",
    "SEMANTIC_EXTENSION_NAMESPACE",
    "compilation_notices",
    "context_algorithm_identity",
    "is_relevance_abstention",
    "relevance_extensions",
]
