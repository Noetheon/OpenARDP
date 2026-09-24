"""Ports for token-efficient agent access over prepared evidence.

The agent layer derives one disposable Markdown text per prepared document version and a
disposable passage index over those texts. Neither is authoritative: both are rebuilt
from the catalog, the content-addressed store and retained provider-native artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from pydantic import JsonValue

from openardp.domain.agent_text import AgentPassage, AgentTextRecord, IndexedDocument


class AgentAccessError(RuntimeError):
    """Base class for sanitized agent-access failures."""


class AgentDocumentNotFound(AgentAccessError, LookupError):
    """Raised when a document reference matches no prepared document."""


class AgentDocumentAmbiguous(AgentAccessError):
    """Raised when a document reference matches several prepared documents."""

    def __init__(self, message: str, *, candidates: Sequence[str] = ()) -> None:
        """Keep the candidate labels for callers that may show local names."""
        super().__init__(message)
        self.candidates = tuple(candidates)


class AgentRangeInvalid(AgentAccessError, ValueError):
    """Raised when a requested page, slide, line range or section does not exist."""


class AgentRenderUnavailable(AgentAccessError):
    """Raised when a rich rendering dependency is not installed."""


class AgentTextRenderer(Protocol):
    """Render one retained provider-native document into agent Markdown."""

    @property
    def renderer_id(self) -> str:
        """Return the exact versioned renderer identity recorded with each text."""
        ...

    def render(self, native_document: Mapping[str, JsonValue], *, media_type: str) -> str:
        """Return Markdown with page or slide marker lines where the provider knows them."""
        ...


class AgentIndex(Protocol):
    """Disposable local index of agent texts and their retrieval passages."""

    def indexed_documents(self) -> tuple[IndexedDocument, ...]:
        """Return body-free facts for every indexed document."""
        ...

    def replace_document(self, record: AgentTextRecord, passages: Sequence[AgentPassage]) -> None:
        """Atomically replace one document text and all of its passages."""
        ...

    def remove_documents(self, document_ids: Sequence[str]) -> None:
        """Remove documents that no longer have a prepared head."""
        ...

    def load_text(self, document_id: str) -> AgentTextRecord | None:
        """Return one complete indexed text record."""
        ...

    def search(
        self,
        match_expression: str,
        *,
        document_ids: Sequence[str] | None,
        limit: int,
    ) -> tuple[tuple[AgentPassage, float], ...]:
        """Return passages matching one bound FTS expression with their BM25 rank."""
        ...


__all__ = [
    "AgentAccessError",
    "AgentDocumentAmbiguous",
    "AgentDocumentNotFound",
    "AgentIndex",
    "AgentRangeInvalid",
    "AgentRenderUnavailable",
    "AgentTextRenderer",
]
