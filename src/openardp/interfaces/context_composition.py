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
from openardp.domain.context_relevance import RelevancePolicy
from openardp.ports.context import ContextCandidateSource, ContextEstimator
from openardp.services.context_compiler import ContextCompilerService


def local_context_compiler(
    workspace: LocalWorkspace,
    estimator: ContextEstimator,
    representation_verifier: Callable[[Any], None],
    *,
    minimum_relevance: bool = True,
) -> ContextCompilerService:
    """Compose the relevance-aware or explicit legacy local compiler profile."""
    lexical_sources = (
        TextLexicalCandidateSource(workspace.object_store, workspace.catalog),
        RichLexicalCandidateSource(
            workspace.object_store,
            workspace.catalog,
            representation_verifier=representation_verifier,
        ),
    )
    relevance_policy = RelevancePolicy() if minimum_relevance else None
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
    )


__all__ = ["local_context_compiler"]
