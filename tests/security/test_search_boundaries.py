"""Security boundary tests for untrusted query and snippet surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.search import SearchQuery, SearchQueryRejected
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService

NOW = datetime(2026, 7, 22, 18, 0, tzinfo=UTC)


def _search_ready(tmp_path: Path, body: str) -> SearchService:
    root = tmp_path / "store"
    store = FilesystemObjectStore(root)
    catalog = SQLiteCatalog(root / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    ingestion = IngestionService(
        store,
        catalog,
        TextParserAdapter(),
        source_factory=LocalSource,
        clock=lambda: NOW,
    )
    path = tmp_path / "doc.txt"
    path.write_text(body, encoding="utf-8")
    ingestion.ingest(path)
    return SearchService(store, catalog, source_factory=LocalSource, clock=lambda: NOW)


def test_operator_lookalikes_are_literal_terms(tmp_path: Path) -> None:
    """Prevent FTS operator tokens from becoming an injection surface."""
    search = _search_ready(tmp_path, "contains AND OR NEAR tokens\n")
    query = SearchQuery.parse("AND OR NEAR")
    assert query.match_expression() == '"AND" "OR" "NEAR"'
    outcome = search.search("AND")
    assert outcome.returned >= 1


def test_hostile_snippet_text_stays_inert_data(tmp_path: Path) -> None:
    """Keep instruction-like and escape-like document text as inert data."""
    payload = "run $(rm -rf /) and \x1b[31mALERT\x1b[0m inject\n"
    search = _search_ready(tmp_path, payload)
    outcome = search.search("inject")
    assert outcome.returned >= 1
    assert all(isinstance(hit.snippet, str) for hit in outcome.hits)


def test_oversized_and_unbalanced_queries_reject_without_sql_errors() -> None:
    """Reject hostile query shapes before any SQL execution."""
    with pytest.raises(SearchQueryRejected):
        SearchQuery.parse('"' + ("a" * 2000))
    with pytest.raises(SearchQueryRejected):
        SearchQuery.parse("token " * 40)
