"""Pure contracts for exact lexical search, index coverage and reindex reports."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from openardp.domain.block import BlockKind
from openardp.domain.common import (
    CanonicalUuid,
    DomainModel,
    Sha256Id,
    TrustZone,
    UtcDatetime,
)
from openardp.domain.ingestion import RepresentationScope

MAX_QUERY_CHARACTERS = 4096
MAX_QUERY_ITEMS = 32
MAX_TERM_CHARACTERS = 256
MAX_PHRASE_CHARACTERS = 1024
MAX_SNIPPET_CHARACTERS = 240
DEFAULT_SEARCH_LIMIT = 20
MIN_SEARCH_LIMIT = 1
MAX_SEARCH_LIMIT = 100
MAX_INDEXED_TEXT_CHARACTERS = 1024 * 1024

_WHITESPACE = re.compile(r"\s+")
_TERM_FORBIDDEN = re.compile(r'[\s"]')

# Filter trust zones from the F005 contract (subset of F002 TrustZone).
SEARCH_TRUST_ZONES = frozenset(
    {
        TrustZone.LOCAL_TRUSTED,
        TrustZone.ORGANIZATION_TRUSTED,
        TrustZone.EXTERNAL_UNTRUSTED,
    }
)


class SearchQueryRejected(ValueError):
    """Raised when operator query input is empty, oversized or malformed."""


class SearchIndexEntry(DomainModel):
    """One derived lexical mapping row for a READY representation block."""

    scope: RepresentationScope
    ordinal: int = Field(ge=0, le=99_999)
    block_id: CanonicalUuid
    kind: BlockKind
    trust_zone: TrustZone
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = Field(default=None, ge=0)
    slide: int | None = Field(default=None, ge=0)
    text_hash: Sha256Id
    indexed_at: UtcDatetime

    @model_validator(mode="after")
    def _line_range_is_valid(self) -> Self:
        if self.line_end < self.line_start:
            raise ValueError("line_end must not precede line_start")
        return self


class SearchQueryItem(DomainModel):
    """One validated bare term or quoted phrase from the bounded grammar."""

    value: str = Field(min_length=1, max_length=MAX_PHRASE_CHARACTERS)
    is_phrase: bool = False

    @model_validator(mode="after")
    def _item_bounds(self) -> Self:
        if self.is_phrase:
            if len(self.value) > MAX_PHRASE_CHARACTERS:
                raise ValueError("phrase exceeds maximum length")
        elif len(self.value) > MAX_TERM_CHARACTERS or _TERM_FORBIDDEN.search(self.value):
            raise ValueError("term is invalid")
        return self


class SearchQuery(DomainModel):
    """Bounded operator query of terms and quoted phrases."""

    terms: tuple[SearchQueryItem, ...] = Field(min_length=1, max_length=MAX_QUERY_ITEMS)

    def match_expression(self) -> str:
        """Translate into one deterministic FTS5 MATCH expression (bound parameter only)."""
        return " ".join(f'"{_escape_fts_string(item.value)}"' for item in self.terms)

    @classmethod
    def parse(cls, raw: str) -> SearchQuery:
        """Parse untrusted operator input into a validated query."""
        if not isinstance(raw, str):
            raise SearchQueryRejected("query must be a string")
        if len(raw) > MAX_QUERY_CHARACTERS:
            raise SearchQueryRejected("query exceeds maximum length")
        stripped = raw.strip()
        if not stripped:
            raise SearchQueryRejected("query is empty")
        items: list[SearchQueryItem] = []
        index = 0
        length = len(stripped)
        while index < length:
            while index < length and stripped[index].isspace():
                index += 1
            if index >= length:
                break
            if stripped[index] == '"':
                index += 1
                chars: list[str] = []
                closed = False
                while index < length:
                    char = stripped[index]
                    if char == '"':
                        if index + 1 < length and stripped[index + 1] == '"':
                            chars.append('"')
                            index += 2
                            continue
                        closed = True
                        index += 1
                        break
                    chars.append(char)
                    index += 1
                if not closed:
                    raise SearchQueryRejected("query has unbalanced quotes")
                phrase = "".join(chars)
                if not phrase:
                    raise SearchQueryRejected("phrase item is empty")
                if len(phrase) > MAX_PHRASE_CHARACTERS:
                    raise SearchQueryRejected("phrase exceeds maximum length")
                items.append(SearchQueryItem(value=phrase, is_phrase=True))
            else:
                start = index
                while index < length and not stripped[index].isspace() and stripped[index] != '"':
                    index += 1
                term = stripped[start:index]
                if not term:
                    raise SearchQueryRejected("term item is empty")
                if len(term) > MAX_TERM_CHARACTERS:
                    raise SearchQueryRejected("term exceeds maximum length")
                items.append(SearchQueryItem(value=term, is_phrase=False))
        if not items:
            raise SearchQueryRejected("query is empty")
        if len(items) > MAX_QUERY_ITEMS:
            raise SearchQueryRejected("query exceeds maximum item count")
        return cls(terms=tuple(items))


class SearchFilters(DomainModel):
    """Optional scope and classification filters for one search invocation."""

    document_id: UUID | None = None
    version_id: Sha256Id | None = None
    include_history: bool = False
    kind: BlockKind | None = None
    trust_zone: TrustZone | None = None
    page: int | None = Field(default=None, ge=0)
    slide: int | None = Field(default=None, ge=0)
    limit: int = Field(default=DEFAULT_SEARCH_LIMIT, ge=MIN_SEARCH_LIMIT, le=MAX_SEARCH_LIMIT)

    @model_validator(mode="after")
    def _filter_coupling(self) -> Self:
        if self.version_id is not None and self.document_id is None:
            raise ValueError("version filter requires a document scope")
        if self.trust_zone is not None and self.trust_zone not in SEARCH_TRUST_ZONES:
            raise ValueError("trust filter is outside the searchable trust vocabulary")
        return self


class SearchHit(DomainModel):
    """Body-minimizing evidence reference with a bounded verified snippet."""

    scope: RepresentationScope
    block_id: CanonicalUuid
    kind: BlockKind
    trust_zone: TrustZone
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = Field(default=None, ge=0)
    slide: int | None = Field(default=None, ge=0)
    rank: float
    order_index: int = Field(ge=0)
    snippet: str = Field(max_length=MAX_SNIPPET_CHARACTERS)

    @field_validator("rank")
    @classmethod
    def _rank_is_finite(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("rank must be finite")
        return value


class SearchOutcome(DomainModel):
    """Deterministic ranked page of hits with explicit truncation metadata."""

    hits: tuple[SearchHit, ...]
    truncated: bool
    returned: int = Field(ge=0, le=MAX_SEARCH_LIMIT)
    available: int = Field(ge=0)
    query_echo: str = Field(max_length=MAX_QUERY_CHARACTERS)

    @model_validator(mode="after")
    def _counts_match_hits(self) -> Self:
        if self.returned != len(self.hits):
            raise ValueError("returned count must equal hit count")
        if self.available < self.returned:
            raise ValueError("available count must not be less than returned")
        if self.truncated and self.available <= self.returned:
            raise ValueError("truncated requires available greater than returned")
        if not self.truncated and self.available != self.returned:
            raise ValueError("non-truncated outcome requires available equal to returned")
        return self


class IndexCoverage(DomainModel):
    """Deterministic structural comparison of READY projections vs index rows."""

    scope: RepresentationScope
    ready_ordinals: tuple[int, ...]
    indexed_ordinals: tuple[int, ...]
    missing: tuple[int, ...]
    orphaned: tuple[int, ...]

    @property
    def is_covered(self) -> bool:
        """Return whether every READY ordinal has exactly one index entry."""
        return not self.missing and not self.orphaned

    @model_validator(mode="after")
    def _sets_are_consistent(self) -> Self:
        if self.ready_ordinals != tuple(sorted(set(self.ready_ordinals))):
            raise ValueError("ready_ordinals must be sorted unique")
        if self.indexed_ordinals != tuple(sorted(set(self.indexed_ordinals))):
            raise ValueError("indexed_ordinals must be sorted unique")
        ready = set(self.ready_ordinals)
        indexed = set(self.indexed_ordinals)
        if self.missing != tuple(sorted(ready - indexed)):
            raise ValueError("missing ordinals are inconsistent")
        if self.orphaned != tuple(sorted(indexed - ready)):
            raise ValueError("orphaned ordinals are inconsistent")
        return self


class ReindexOutcome(StrEnum):
    """Bounded per-scope outcome of one explicit reindex attempt."""

    CURRENT = "current"
    REBUILT = "rebuilt"
    FAILED = "failed"


class ReindexScopeReport(DomainModel):
    """Body-free outcome for one READY representation scope."""

    scope: RepresentationScope
    outcome: ReindexOutcome
    failure_code: str | None = Field(default=None, max_length=128)
    entry_count: int = Field(ge=0, le=100_000)

    @model_validator(mode="after")
    def _failure_shape(self) -> Self:
        if self.outcome is ReindexOutcome.FAILED:
            if not self.failure_code:
                raise ValueError("failed reindex requires a failure code")
        elif self.failure_code is not None:
            raise ValueError("non-failed reindex cannot carry a failure code")
        return self


class ReindexReport(DomainModel):
    """Deterministic ordered collection of per-scope reindex outcomes."""

    scopes: tuple[ReindexScopeReport, ...]

    @model_validator(mode="after")
    def _scopes_are_ordered(self) -> Self:
        keys = [
            (str(item.scope.document_id), item.scope.version_id, item.scope.representation_id)
            for item in self.scopes
        ]
        if keys != sorted(keys):
            raise ValueError("reindex report scopes must be ordered by identity")
        return self


class SearchMatchRow(DomainModel):
    """One catalog match row before CAS verification and snippet construction."""

    entry_id: int = Field(ge=1)
    scope: RepresentationScope
    ordinal: int = Field(ge=0, le=99_999)
    block_id: CanonicalUuid
    kind: BlockKind
    trust_zone: TrustZone
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = Field(default=None, ge=0)
    slide: int | None = Field(default=None, ge=0)
    text_hash: Sha256Id
    rank: float
    object_id: Sha256Id
    object_byte_length: int = Field(ge=0)


class SearchMatchPage(DomainModel):
    """Total-ordered match page returned from one catalog read transaction."""

    rows: tuple[SearchMatchRow, ...]
    available: int = Field(ge=0)
    limit: int = Field(ge=MIN_SEARCH_LIMIT, le=MAX_SEARCH_LIMIT)

    @model_validator(mode="after")
    def _page_bounds(self) -> Self:
        if len(self.rows) > self.limit:
            raise ValueError("match page exceeds limit")
        if self.available < len(self.rows):
            raise ValueError("available count must cover returned rows")
        return self


def indexed_text_hash(text: str) -> str:
    """Return the SHA-256 identity of exact indexed UTF-8 block text."""
    if len(text) > MAX_INDEXED_TEXT_CHARACTERS:
        raise ValueError("indexed text exceeds maximum length")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def block_text_for_index(text: str | None) -> str:
    """Normalize optional block text into the exact indexed string."""
    if text is None:
        return ""
    if len(text) > MAX_INDEXED_TEXT_CHARACTERS:
        raise ValueError("indexed text exceeds maximum length")
    return text


def build_snippet(text: str, query: SearchQuery, *, limit: int = MAX_SNIPPET_CHARACTERS) -> str:
    """Build a bounded snippet around the first query match in verified text."""
    if limit < 1:
        raise ValueError("snippet limit must be positive")
    if not text:
        return ""
    lowered = text.casefold()
    position = -1
    match_length = 0
    for item in query.terms:
        needle = item.value.casefold()
        if not needle:
            continue
        found = lowered.find(needle)
        if found >= 0 and (position < 0 or found < position):
            position = found
            match_length = len(item.value)
    if position < 0:
        # Tokenizer-exact match may differ from byte casefold; use a head window.
        return text[:limit]
    half = max((limit - match_length) // 2, 0)
    start = max(position - half, 0)
    end = min(start + limit, len(text))
    start = max(end - limit, 0)
    return text[start:end]


def _escape_fts_string(value: str) -> str:
    return value.replace('"', '""')


__all__ = [
    "DEFAULT_SEARCH_LIMIT",
    "MAX_INDEXED_TEXT_CHARACTERS",
    "MAX_PHRASE_CHARACTERS",
    "MAX_QUERY_CHARACTERS",
    "MAX_QUERY_ITEMS",
    "MAX_SEARCH_LIMIT",
    "MAX_SNIPPET_CHARACTERS",
    "MAX_TERM_CHARACTERS",
    "MIN_SEARCH_LIMIT",
    "SEARCH_TRUST_ZONES",
    "IndexCoverage",
    "ReindexOutcome",
    "ReindexReport",
    "ReindexScopeReport",
    "SearchFilters",
    "SearchHit",
    "SearchIndexEntry",
    "SearchMatchPage",
    "SearchMatchRow",
    "SearchOutcome",
    "SearchQuery",
    "SearchQueryItem",
    "SearchQueryRejected",
    "block_text_for_index",
    "build_snippet",
    "indexed_text_hash",
]
