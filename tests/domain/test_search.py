"""Pure domain tests for the F005 lexical search contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.block import BlockKind
from openardp.domain.common import TrustZone
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.search import (
    DEFAULT_SEARCH_LIMIT,
    MAX_QUERY_CHARACTERS,
    MAX_SEARCH_LIMIT,
    MAX_SNIPPET_CHARACTERS,
    IndexCoverage,
    SearchFilters,
    SearchHit,
    SearchOutcome,
    SearchQuery,
    SearchQueryRejected,
    build_snippet,
    indexed_text_hash,
)

SCOPE = RepresentationScope(
    document_id=UUID("01900000-0000-7000-8000-000000000001"),
    version_id="sha256:" + ("a" * 64),
    representation_id="sha256:" + ("b" * 64),
)
NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


def test_parse_terms_phrases_and_operator_literals() -> None:
    """Treat operator lookalikes as literal terms and quote every MATCH item."""
    query = SearchQuery.parse('alpha "beta gamma" AND OR *')
    assert [item.value for item in query.terms] == ["alpha", "beta gamma", "AND", "OR", "*"]
    assert query.match_expression() == '"alpha" "beta gamma" "AND" "OR" "*"'


def test_parse_escaped_quotes_inside_phrases() -> None:
    """Unescape doubled quotes inside a phrase item."""
    query = SearchQuery.parse('"say ""hello"""')
    assert query.terms[0].value == 'say "hello"'
    assert query.match_expression() == '"say ""hello"""'


def test_parse_rejects_empty_unbalanced_and_oversized() -> None:
    """Reject empty, unbalanced and oversized operator input."""
    with pytest.raises(SearchQueryRejected):
        SearchQuery.parse("   ")
    with pytest.raises(SearchQueryRejected):
        SearchQuery.parse('"unclosed')
    with pytest.raises(SearchQueryRejected):
        SearchQuery.parse("x" * (MAX_QUERY_CHARACTERS + 1))


def test_filters_defaults_and_coupling() -> None:
    """Keep filter defaults and reject invalid coupling or vocabulary."""
    filters = SearchFilters()
    assert filters.limit == DEFAULT_SEARCH_LIMIT
    assert filters.include_history is False
    with pytest.raises(ValidationError):
        SearchFilters(version_id="sha256:" + ("c" * 64))
    with pytest.raises(ValidationError):
        SearchFilters(limit=MAX_SEARCH_LIMIT + 1)
    with pytest.raises(ValidationError):
        SearchFilters(trust_zone=TrustZone.MODEL_DERIVED)


def test_outcome_and_coverage_invariants() -> None:
    """Enforce hit counts, coverage set math and text hashes."""
    hit = SearchHit(
        scope=SCOPE,
        block_id=UUID("01900000-0000-7000-8000-000000000099"),
        kind=BlockKind.PARAGRAPH,
        trust_zone=TrustZone.LOCAL_TRUSTED,
        line_start=1,
        line_end=2,
        rank=-0.5,
        order_index=0,
        snippet="hello",
    )
    outcome = SearchOutcome(
        hits=(hit,),
        truncated=False,
        returned=1,
        available=1,
        query_echo="hello",
    )
    assert outcome.returned == 1
    coverage = IndexCoverage(
        scope=SCOPE,
        ready_ordinals=(0, 1),
        indexed_ordinals=(0,),
        missing=(1,),
        orphaned=(),
    )
    assert coverage.is_covered is False
    assert indexed_text_hash("hello").startswith("sha256:")


def test_build_snippet_bounds_and_match_window() -> None:
    """Keep snippets bounded and centered near the first match."""
    text = "prefix " + ("word " * 40) + "target token " + ("tail " * 40)
    query = SearchQuery.parse("target")
    snippet = build_snippet(text, query)
    assert "target" in snippet
    assert len(snippet) <= MAX_SNIPPET_CHARACTERS
