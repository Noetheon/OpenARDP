"""Integration tests for progressive persisted document navigation."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.block import BlockKind
from openardp.domain.ingestion import ParsedTextDocument, ParserRecipe, SourceFreshness
from openardp.domain.storage import ObjectInventory, StoredObject
from openardp.ports.catalog import BlockNotFound, DocumentNotFound
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService

NOW = datetime(2026, 7, 22, 19, 0, tzinfo=UTC)


class _ParserSpy:
    def __init__(self) -> None:
        self._delegate = TextParserAdapter()
        self.calls = 0

    @property
    def recipe(self) -> ParserRecipe:
        return self._delegate.recipe

    def supports(self, media_type: str) -> bool:
        return self._delegate.supports(media_type)

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument:
        self.calls += 1
        return self._delegate.parse(chunks, media_type=media_type)


class _TrackingStore:
    def __init__(self, delegate: FilesystemObjectStore) -> None:
        self.delegate = delegate
        self.read_object_ids: list[str] = []

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        return self.delegate.put_chunks(chunks)

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        self.read_object_ids.append(object_id)
        return self.delegate.iter_chunks(object_id, chunk_size=chunk_size)

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject:
        return self.delegate.verify(object_id, expected_length=expected_length)

    def inventory(self) -> ObjectInventory:
        return self.delegate.inventory()

    def reset_reads(self) -> None:
        self.read_object_ids.clear()


def _services(
    tmp_path: Path,
) -> tuple[
    IngestionService,
    DocumentQueryService,
    _TrackingStore,
    SQLiteCatalog,
    _ParserSpy,
]:
    root = tmp_path / "store"
    store = _TrackingStore(FilesystemObjectStore(root))
    catalog = SQLiteCatalog(root / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    parser = _ParserSpy()
    ticks = iter(NOW + timedelta(seconds=index) for index in range(1000))
    ingestion = IngestionService(
        store,
        catalog,
        parser,
        source_factory=LocalSource,
        clock=lambda: next(ticks),
        owner_id_factory=lambda: "query-worker",
        lease_token_factory=lambda: "query-lease-token-value",
        random_bits=lambda: 7,
    )
    query = DocumentQueryService(
        store,
        catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
        clock=lambda: next(ticks),
    )
    return ingestion, query, store, catalog, parser


def test_list_is_deterministic_and_contains_no_body_text(tmp_path: Path) -> None:
    """Return source/head metadata in source-key order without normalized content."""
    first = tmp_path / "b.txt"
    second = tmp_path / "a.txt"
    first.write_text("TOP-SECRET-BODY-B", encoding="utf-8")
    second.write_text("TOP-SECRET-BODY-A", encoding="utf-8")
    ingestion, query, _, _, _ = _services(tmp_path)
    ingestion.ingest(first)
    ingestion.ingest(second)

    summaries = query.list_documents()
    serialized = str([summary.model_dump(mode="json") for summary in summaries])
    assert [Path(item.source_key.locator).name for item in summaries] == ["a.txt", "b.txt"]
    assert "TOP-SECRET-BODY" not in serialized


def test_status_distinguishes_current_changed_missing_and_not_registered(tmp_path: Path) -> None:
    """Hash current source bytes without parser calls or CAS publication."""
    source = tmp_path / "status.txt"
    source.write_text("A", encoding="utf-8")
    ingestion, query, store, _, parser = _services(tmp_path)
    result = ingestion.ingest(source)
    parser_calls = parser.calls
    object_count = len(store.inventory().objects)

    assert query.status(str(source)).freshness is SourceFreshness.CURRENT
    assert query.status(str(result.scope.document_id)).freshness is SourceFreshness.CURRENT
    source.write_text("B", encoding="utf-8")
    assert query.status(str(source)).freshness is SourceFreshness.SOURCE_CHANGED
    source.unlink()
    assert query.status(str(result.scope.document_id)).freshness is SourceFreshness.SOURCE_MISSING
    unknown = tmp_path / "unknown.txt"
    unknown.write_text("unknown", encoding="utf-8")
    assert query.status(str(unknown)).freshness is SourceFreshness.NOT_REGISTERED
    assert parser.calls == parser_calls
    assert len(store.inventory().objects) == object_count


def test_outline_reads_only_structural_block_objects(tmp_path: Path) -> None:
    """Skip unrelated paragraph bodies while returning exact hierarchy labels."""
    source = tmp_path / "outline.md"
    source.write_text(
        "# Root\n\nSECRET PARAGRAPH\n\n- first\n- second\n\n## Child\n\nOTHER SECRET",
        encoding="utf-8",
    )
    ingestion, query, store, catalog, _ = _services(tmp_path)
    result = ingestion.ingest(source)
    aggregate = catalog.load_representation(result.scope)
    assert aggregate is not None
    paragraph_ids = {
        item.object.object_id for item in aggregate.blocks if item.kind is BlockKind.PARAGRAPH
    }
    store.reset_reads()

    outline = query.outline(result.scope.document_id)

    assert [item.kind for item in outline] == [
        BlockKind.HEADING,
        BlockKind.LIST,
        BlockKind.LIST_ITEM,
        BlockKind.LIST_ITEM,
        BlockKind.HEADING,
    ]
    assert [item.label for item in outline] == ["Root", "- first", "first", "second", "Child"]
    assert paragraph_ids.isdisjoint(store.read_object_ids)


def test_historical_outline_and_get_survive_source_removal(tmp_path: Path) -> None:
    """Resolve exact historical/current CAS records without live-path fallback."""
    source = tmp_path / "history.md"
    source.write_text("# A\n\nbody A", encoding="utf-8")
    ingestion, query, _, catalog, _ = _services(tmp_path)
    first = ingestion.ingest(source)
    source.write_text("# B\n\nbody B", encoding="utf-8")
    second = ingestion.ingest(source)
    second_aggregate = catalog.load_representation(second.scope)
    assert second_aggregate is not None
    paragraph = next(item for item in second_aggregate.blocks if item.kind is BlockKind.PARAGRAPH)
    source.unlink()

    historical = query.outline(
        first.scope.document_id,
        version_id=first.scope.version_id,
    )
    block = query.get(paragraph.block_id)

    assert historical[0].label == "A"
    assert block.text == "body B"
    assert block.version_id == second.scope.version_id


def test_unknown_document_and_block_are_explicit(tmp_path: Path) -> None:
    """Return typed not-found failures rather than empty or cross-scope evidence."""
    _, query, _, _, _ = _services(tmp_path)
    unknown = UUID("01890f62-24e8-7c00-8000-000000000099")
    with pytest.raises(DocumentNotFound):
        query.outline(unknown)
    with pytest.raises(BlockNotFound):
        query.get(UUID("efe2cf3a-3c22-8c00-adcc-237de0936768"))
