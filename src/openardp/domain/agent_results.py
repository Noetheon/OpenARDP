"""Body-bounded result models of the token-efficient agent access surface."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from openardp.domain.agent_query import MatchLevel
from openardp.domain.agent_text import PageLabel
from openardp.domain.common import DomainModel, Sha256Id


class Freshness(StrEnum):
    """Relationship between a prepared version and the current source file."""

    CURRENT = "current"
    CHANGED = "changed"
    MISSING = "missing"
    UNKNOWN = "unknown"


class DocumentRef(DomainModel):
    """Compact identity of one prepared document version."""

    document_id: str
    short_id: str
    label: str
    locator: str
    media_type: str
    version_id: Sha256Id
    page_label: PageLabel | None = None


class DocumentEntry(DocumentRef):
    """One prepared document with its size and freshness."""

    token_estimate: int = Field(ge=0)
    line_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    heading_count: int = Field(ge=0)
    freshness: Freshness = Freshness.UNKNOWN


class PendingDocument(DomainModel):
    """A registered source without a prepared representation."""

    document_id: str
    label: str
    locator: str


class DocsResult(DomainModel):
    """All prepared documents and registered sources that are not yet prepared."""

    documents: tuple[DocumentEntry, ...]
    pending: tuple[PendingDocument, ...] = ()
    total_tokens: int = Field(ge=0)


class FindHit(DomainModel):
    """One ranked passage with its exact location and a compact snippet."""

    document: DocumentRef
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = None
    heading: str = ""
    snippet: str
    matched_terms: int = Field(ge=0)
    token_estimate: int = Field(ge=0)


class FindResult(DomainModel):
    """Ranked passages for one question or keyword query."""

    query_terms: tuple[str, ...]
    hits: tuple[FindHit, ...]
    candidates: int = Field(ge=0)
    changed_sources: tuple[str, ...] = ()


class ReadResult(DomainModel):
    """One bounded contiguous excerpt of an agent text."""

    document: DocumentRef
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=0)
    total_lines: int = Field(ge=0)
    pages: tuple[int, ...] = ()
    text: str
    token_estimate: int = Field(ge=0)
    truncated: bool = False
    next_line: int | None = None
    freshness: Freshness = Freshness.UNKNOWN


class OutlineEntry(DomainModel):
    """One heading, page or slide with the size of the section it opens."""

    line: int = Field(ge=1)
    level: int = Field(ge=0)
    text: str
    page: int | None = None
    token_estimate: int = Field(ge=0)


class OutlineResult(DomainModel):
    """Navigable structure of one prepared document."""

    document: DocumentEntry
    entries: tuple[OutlineEntry, ...]
    truncated: bool = False


class QuoteMatch(DomainModel):
    """One verified occurrence of a quote in a prepared document version."""

    document: DocumentRef
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = None
    level: MatchLevel
    current_version: bool = True
    freshness: Freshness = Freshness.UNKNOWN


class ClosestPassage(DomainModel):
    """Most similar passage when a quote was not found."""

    document: DocumentRef
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = None
    similarity: float = Field(ge=0.0, le=1.0)
    snippet: str


class VerifyStatus(StrEnum):
    """Outcome of one quote verification."""

    VERIFIED = "verified"
    ONLY_IN_OTHER_VERSION = "only_in_other_version"
    NOT_FOUND = "not_found"


class VerifyResult(DomainModel):
    """Quote verification against exact prepared document versions."""

    status: VerifyStatus
    matches: tuple[QuoteMatch, ...] = ()
    closest: ClosestPassage | None = None
    searched_documents: int = Field(ge=0)


class AddStatus(StrEnum):
    """Outcome of preparing one source file."""

    ADDED = "added"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    FAILED = "failed"


class AddOutcome(DomainModel):
    """Result of preparing one discovered source file."""

    path: str
    status: AddStatus
    document_id: str | None = None
    error_code: str | None = None
    hint: str | None = None
    seconds: float = Field(ge=0.0)


class AddReport(DomainModel):
    """Results of one bulk preparation run."""

    outcomes: tuple[AddOutcome, ...]
    skipped_unsupported: int = Field(default=0, ge=0)
    seconds: float = Field(default=0.0, ge=0.0)

    def count(self, status: AddStatus) -> int:
        """Return how many files ended in one status."""
        return sum(1 for outcome in self.outcomes if outcome.status is status)


class ExportReport(DomainModel):
    """Results of writing one agent view directory."""

    directory: str
    index_file: str
    documents: int = Field(ge=0)
    written: tuple[str, ...] = ()
    unchanged: int = Field(default=0, ge=0)
    removed: tuple[str, ...] = ()
    total_tokens: int = Field(ge=0)


__all__ = [
    "AddOutcome",
    "AddReport",
    "AddStatus",
    "ClosestPassage",
    "DocsResult",
    "DocumentEntry",
    "DocumentRef",
    "ExportReport",
    "FindHit",
    "FindResult",
    "Freshness",
    "OutlineEntry",
    "OutlineResult",
    "PendingDocument",
    "QuoteMatch",
    "ReadResult",
    "VerifyResult",
    "VerifyStatus",
]
