"""Local context-compiler composition profiles for product interfaces."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
    VisualContextCandidateSource,
)
from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.semantic_candidates import (
    HybridRetrievalCandidateSource,
    SemanticContextCandidateSource,
)
from openardp.domain.context_compilation import AlgorithmIdentity
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.domain.semantic_retrieval import SemanticRetrievalLimits, SemanticRetrievalPolicy
from openardp.ports.context import (
    ContextCandidateSource,
    ContextConfigurationMismatch,
    ContextEstimator,
)
from openardp.ports.semantic_retrieval import SemanticRetrievalProvider
from openardp.services.context_compiler import ContextCompilerService, context_algorithm_identity
from openardp.services.semantic_retrieval import semantic_algorithm_identity


def local_context_compiler(
    workspace: LocalWorkspace,
    estimator: ContextEstimator,
    representation_verifier: Callable[[Any], None],
    *,
    minimum_relevance: bool = True,
    ranked_allocation: bool = True,
) -> ContextCompilerService:
    """Compose the ranked, relevance-only or explicit legacy local profile."""
    lexical_sources = (
        TextLexicalCandidateSource(workspace.object_store, workspace.catalog),
        RichLexicalCandidateSource(
            workspace.object_store,
            workspace.catalog,
            representation_verifier=representation_verifier,
        ),
    )
    relevance_policy = RelevancePolicy() if minimum_relevance else None
    if ranked_allocation and relevance_policy is None:
        raise ValueError("ranked allocation requires minimum relevance")
    allocation_policy = LexicalAllocationPolicy() if ranked_allocation else None
    candidate_sources: tuple[ContextCandidateSource, ...]
    if relevance_policy is None:
        candidate_sources = lexical_sources
    else:
        candidate_sources = (
            RelevanceObservingCandidateSource(
                workspace.object_store,
                lexical_sources,
                relevance_policy,
            ),
        )
    return ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        estimator,
        (
            *candidate_sources,
            VisualContextCandidateSource(workspace.object_store, workspace.catalog),
        ),
        relevance_policy=relevance_policy,
        allocation_policy=allocation_policy,
    )


def local_context_compiler_for_algorithm(
    workspace: LocalWorkspace,
    estimator: ContextEstimator,
    representation_verifier: Callable[[Any], None],
    algorithm: AlgorithmIdentity,
) -> ContextCompilerService:
    """Compose the exact built-in profile recorded by a persisted receipt."""
    relevance = RelevancePolicy()
    allocation = LexicalAllocationPolicy()
    if algorithm == context_algorithm_identity(relevance, allocation):
        return local_context_compiler(workspace, estimator, representation_verifier)
    if algorithm == context_algorithm_identity(relevance):
        return local_context_compiler(
            workspace,
            estimator,
            representation_verifier,
            ranked_allocation=False,
        )
    if algorithm == context_algorithm_identity():
        return local_context_compiler(
            workspace,
            estimator,
            representation_verifier,
            minimum_relevance=False,
            ranked_allocation=False,
        )
    raise ContextConfigurationMismatch("algorithm_mismatch")


def local_semantic_context_compiler(
    workspace: LocalWorkspace,
    estimator: ContextEstimator,
    text_verifier: Callable[[Any], None],
    rich_verifier: Callable[[Any], None],
    provider: SemanticRetrievalProvider,
    *,
    policy: SemanticRetrievalPolicy | None = None,
    provider_limits: SemanticRetrievalLimits | None = None,
    allocation_policy: LexicalAllocationPolicy | None = None,
    hybrid_lexical_fallback: bool = True,
    source_balanced: bool = True,
    semantic_max_per_document: int = 32,
    semantic_ranked_prefix: int = 4,
    rich_first: bool = True,
) -> ContextCompilerService:
    """Compose one explicit optional semantic profile; default composition stays lexical."""
    selected_policy = policy or SemanticRetrievalPolicy()
    selected_limits = provider_limits or SemanticRetrievalLimits()
    selected_allocation = allocation_policy or LexicalAllocationPolicy()
    source = SemanticContextCandidateSource(
        workspace.object_store,
        workspace.catalog,
        provider,
        selected_policy,
        selected_limits,
        text_verifier=text_verifier,
        rich_verifier=rich_verifier,
        source_balanced=source_balanced,
        max_per_document=semantic_max_per_document,
        ranked_prefix=semantic_ranked_prefix,
        rich_first=rich_first,
    )
    candidate_source: ContextCandidateSource = source
    if hybrid_lexical_fallback:
        lexical = RelevanceObservingCandidateSource(
            workspace.object_store,
            (
                TextLexicalCandidateSource(workspace.object_store, workspace.catalog),
                RichLexicalCandidateSource(
                    workspace.object_store,
                    workspace.catalog,
                    representation_verifier=rich_verifier,
                ),
            ),
            RelevancePolicy(),
        )
        candidate_source = HybridRetrievalCandidateSource(lexical, source)
    return ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        estimator,
        (candidate_source,),
        algorithm=semantic_algorithm_identity(
            provider.recipe,
            selected_policy,
            selected_limits,
            selected_allocation,
            hybrid_lexical_fallback=hybrid_lexical_fallback,
            source_balanced=source_balanced,
            semantic_max_per_document=semantic_max_per_document,
            semantic_ranked_prefix=semantic_ranked_prefix,
            rich_first=rich_first,
        ),
        allocation_policy=selected_allocation,
        semantic_abstention=True,
    )


__all__ = [
    "local_context_compiler",
    "local_context_compiler_for_algorithm",
    "local_semantic_context_compiler",
]
