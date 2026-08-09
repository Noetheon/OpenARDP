"""Narrow optional semantic scoring provider boundary."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openardp.domain.semantic_retrieval import (
    PreparedSemanticCorpus,
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticScore,
)
from openardp.ports.context import CancellationCheck


class SemanticRetrievalFailure(RuntimeError):
    """Base sanitized provider failure."""


class SemanticProviderUnavailable(SemanticRetrievalFailure):
    """Raised when the explicitly configured provider cannot be used."""


class SemanticProviderTimedOut(SemanticRetrievalFailure):
    """Raised after terminating a provider that exceeded its wall bound."""


class SemanticProviderInvalid(SemanticRetrievalFailure):
    """Raised when a provider response violates the closed contract."""


class SemanticProviderLimitExceeded(SemanticRetrievalFailure):
    """Raised before a provider request would exceed configured bounds."""


@runtime_checkable
class SemanticRetrievalProvider(Protocol):
    """Score verified passages for one untrusted query without selecting evidence."""

    @property
    def recipe(self) -> SemanticProviderRecipe:
        """Return the exact installed inference recipe."""
        ...

    def score(
        self,
        query: str,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> tuple[SemanticScore, ...]:
        """Return exactly one fixed-point score per unique supplied passage."""
        ...

    def close(self) -> None:
        """Release provider workers and disposable vector caches idempotently."""
        ...


@runtime_checkable
class PreparedSemanticRetrievalProvider(SemanticRetrievalProvider, Protocol):
    """Optionally prepare an exact corpus once for compact process-local scoring."""

    def prepare(
        self,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> PreparedSemanticCorpus:
        """Prepare verified passages and return a body-free process-local handle."""
        ...

    def score_prepared(
        self,
        query: str,
        corpus: PreparedSemanticCorpus,
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> tuple[SemanticScore, ...]:
        """Score every identity in one still-live prepared corpus."""
        ...


__all__ = [
    "PreparedSemanticRetrievalProvider",
    "SemanticProviderInvalid",
    "SemanticProviderLimitExceeded",
    "SemanticProviderTimedOut",
    "SemanticProviderUnavailable",
    "SemanticRetrievalFailure",
    "SemanticRetrievalProvider",
]
