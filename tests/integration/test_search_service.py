"""Service-level tests for exact lexical search and reindex."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.block import BlockKind
from openardp.domain.search import ReindexOutcome, SearchQueryRejected
from openardp.ports.catalog import SearchIndexIncomplete
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService

NOW = datetime(2026, 7, 22, 18, 0, tzinfo=UTC)


class _Clock:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> datetime:
        value = NOW + timedelta(seconds=self.calls)
        self.calls += 1
        return value


def _services(tmp_path: Path) -> tuple[IngestionService, SearchService, Path]:
    root = tmp_path / "store"
    store = FilesystemObjectStore(root)
    catalog = SQLiteCatalog(root / "catalog.sqlite3")
    clock = _Clock()
    catalog.initialize(now=clock())
    parser = TextParserAdapter()
    ingestion = IngestionService(
        store,
        catalog,
        parser,
        source_factory=LocalSource,
        clock=clock,
    )
    search = SearchService(store, catalog, source_factory=LocalSource, clock=clock)
    return ingestion, search, root


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_term_and_phrase_search_return_source_backed_hits(tmp_path: Path) -> None:
    """Match exact terms and adjacent phrases with scoped hit provenance."""
    ingestion, search, _ = _services(tmp_path)
    source = _write(
        tmp_path / "doc.md",
        "# Title\n\nThe alpha token lives here.\n\nSeparately alpha and beta appear.\n",
    )
    result = ingestion.ingest(source)
    assert result.block_count >= 2

    term = search.search("alpha")
    assert term.returned >= 1
    assert all(hit.scope.document_id == result.scope.document_id for hit in term.hits)
    assert all(hit.snippet for hit in term.hits)

    phrase = search.search('"alpha token"')
    assert phrase.returned >= 1
    assert all("alpha token" in hit.snippet.casefold() for hit in phrase.hits)

    non_adjacent = search.search('"alpha beta"')
    assert non_adjacent.returned == 0


def test_repeated_queries_are_deterministic(tmp_path: Path) -> None:
    """Return byte-identical outcomes for identical queries on a fixed corpus."""
    ingestion, search, _ = _services(tmp_path)
    ingestion.ingest(_write(tmp_path / "a.txt", "gamma signal one\n\ngamma signal two\n"))
    first = search.search("gamma")
    for _ in range(20):
        again = search.search("gamma")
        assert again.model_dump(mode="json") == first.model_dump(mode="json")


def test_history_filter_and_kind_filter(tmp_path: Path) -> None:
    """Exclude superseded versions by default and honor kind filters."""
    ingestion, search, _ = _services(tmp_path)
    path = tmp_path / "versioned.md"
    _write(path, "# Heading\n\nold unique_term version\n")
    first = ingestion.ingest(path)
    _write(path, "# Heading\n\nnew unique_term version\n")
    second = ingestion.ingest(path)
    assert first.scope.version_id != second.scope.version_id

    current = search.search("unique_term")
    assert current.returned >= 1
    assert all(hit.scope.version_id == second.scope.version_id for hit in current.hits)

    historical = search.search("unique_term", include_history=True)
    versions = {hit.scope.version_id for hit in historical.hits}
    assert first.scope.version_id in versions
    assert second.scope.version_id in versions

    headings = search.search("Heading", kind=BlockKind.HEADING.value)
    assert headings.returned >= 1
    assert all(hit.kind is BlockKind.HEADING for hit in headings.hits)


def test_document_scope_limit_and_page_filter(tmp_path: Path) -> None:
    """Scope by document, truncate deterministically and accept page filters."""
    ingestion, search, _ = _services(tmp_path)
    one = ingestion.ingest(_write(tmp_path / "one.txt", "shared_token in document one\n"))
    two = ingestion.ingest(_write(tmp_path / "two.txt", "shared_token in document two\n"))
    scoped = search.search("shared_token", document=str(one.scope.document_id))
    assert scoped.returned >= 1
    assert all(hit.scope.document_id == one.scope.document_id for hit in scoped.hits)
    assert two.scope.document_id not in {hit.scope.document_id for hit in scoped.hits}

    limited = search.search("shared_token", limit=1)
    assert limited.returned == 1
    assert limited.available >= 1
    if limited.available > 1:
        assert limited.truncated is True

    page_filtered = search.search("shared_token", page=1)
    assert page_filtered.returned == 0


def test_empty_and_rejected_queries(tmp_path: Path) -> None:
    """Return empty outcomes for no matches and reject invalid queries/filters."""
    ingestion, search, _ = _services(tmp_path)
    ingestion.ingest(_write(tmp_path / "doc.txt", "content here\n"))
    empty = search.search("missing_term_zzz")
    assert empty.returned == 0
    assert empty.truncated is False
    with pytest.raises(SearchQueryRejected):
        search.search("")
    with pytest.raises(SearchQueryRejected):
        search.search("token", kind="not-a-kind")


def test_reindex_is_idempotent_and_repairs_missing_entries(tmp_path: Path) -> None:
    """Rebuild incomplete indexes and report CURRENT on an idempotent second run."""
    ingestion, search, root = _services(tmp_path)
    result = ingestion.ingest(_write(tmp_path / "doc.txt", "repairable token here\n"))
    catalog = SQLiteCatalog(root / "catalog.sqlite3")
    with catalog._write_connection() as connection:
        rows = connection.execute(
            "SELECT entry_id FROM representation_blocks WHERE indexed_at IS NOT NULL"
        ).fetchall()
        for row in rows:
            connection.execute(
                "DELETE FROM block_search_index WHERE rowid = ?",
                (int(row["entry_id"]),),
            )
        connection.execute(
            "UPDATE representation_blocks SET trust_zone=NULL, page=NULL, slide=NULL, "
            "text_hash=NULL, indexed_at=NULL"
        )

    with pytest.raises(SearchIndexIncomplete):
        search.search("repairable")

    report = search.reindex()
    assert report.scopes
    assert report.scopes[0].outcome is ReindexOutcome.REBUILT
    assert report.scopes[0].scope.document_id == result.scope.document_id

    second = search.reindex()
    assert second.scopes[0].outcome is ReindexOutcome.CURRENT
    hits = search.search("repairable")
    assert hits.returned >= 1


def test_search_works_after_source_removed(tmp_path: Path) -> None:
    """Serve hits from verified CAS evidence after the original source is gone."""
    ingestion, search, _ = _services(tmp_path)
    path = _write(tmp_path / "ephemeral.txt", "orphan_source token\n")
    ingestion.ingest(path)
    path.unlink()
    outcome = search.search("orphan_source")
    assert outcome.returned >= 1
