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
from openardp.domain.context_compilation import AlgorithmIdentity
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.ports.context import (
    ContextCandidateSource,
    ContextConfigurationMismatch,
    ContextEstimator,
)
from openardp.services.context_compiler import ContextCompilerService, context_algorithm_identity


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


__all__ = ["local_context_compiler", "local_context_compiler_for_algorithm"]
