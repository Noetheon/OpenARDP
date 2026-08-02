"""Integration tests for progressive persisted document navigation."""

from __future__ import annotations

import os
import sqlite3
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
from openardp.domain.ingestion import (
    IntegrityCoverage,
    ParsedTextDocument,
    ParserRecipe,
    SourceFreshness,
    StatusMode,
)
from openardp.domain.storage import ObjectInventory, SourceKey, StoredObject, uuid7_from_parts
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
        self.verified_object_ids: list[str] = []

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
        self.verified_object_ids.append(object_id)
        return self.delegate.verify(object_id, expected_length=expected_length)

    def inventory(self) -> ObjectInventory:
        return self.delegate.inventory()

    def reset_reads(self) -> None:
        self.read_object_ids.clear()
        self.verified_object_ids.clear()


class _CatalogSpy:
    """Delegate catalog calls while exposing aggregate-materialization count."""

    def __init__(self, delegate: SQLiteCatalog) -> None:
        self.delegate = delegate
        self.aggregate_loads = 0

    def __getattr__(self, name: str) -> object:
        return getattr(self.delegate, name)

    def load_representation(self, scope: object) -> object:
        self.aggregate_loads += 1
        return self.delegate.load_representation(scope)  # type: ignore[arg-type]


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


def _object_path(root: Path, object_id: str) -> Path:
    digest = object_id.removeprefix("sha256:")
    return root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]


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
    ingestion, query, store, catalog, parser = _services(tmp_path)
    result = ingestion.ingest(source)
    catalog_spy = _CatalogSpy(catalog)
    query._catalog = catalog_spy
    parser_calls = parser.calls
    object_count = len(store.inventory().objects)
    store.reset_reads()

    current = query.status(str(source))
    assert current.freshness is SourceFreshness.CURRENT
    assert current.integrity_coverage is IntegrityCoverage.HEAD
    assert query.status(str(result.scope.document_id)).freshness is SourceFreshness.CURRENT
    original = source.stat()
    source.write_text("B", encoding="utf-8")
    os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))
    changed_metadata = source.stat()
    assert changed_metadata.st_size == original.st_size
    assert changed_metadata.st_mtime_ns == original.st_mtime_ns
    changed = query.status(str(source))
    assert changed.freshness is SourceFreshness.SOURCE_CHANGED
    assert changed.integrity_coverage is IntegrityCoverage.HEAD
    source.unlink()
    assert query.status(str(result.scope.document_id)).freshness is SourceFreshness.SOURCE_MISSING
    unknown = tmp_path / "unknown.txt"
    unknown.write_text("unknown", encoding="utf-8")
    assert query.status(str(unknown)).freshness is SourceFreshness.NOT_REGISTERED
    assert parser.calls == parser_calls
    assert catalog_spy.aggregate_loads == 0
    assert store.read_object_ids == []
    assert store.verified_object_ids == []
    assert len(store.inventory().objects) == object_count


def test_status_full_integrity_is_explicit(tmp_path: Path) -> None:
    """Run the complete existing verifier only for an explicit full request."""
    source = tmp_path / "full.txt"
    source.write_text("# heading\n\nbody", encoding="utf-8")
    ingestion, query, store, catalog, _ = _services(tmp_path)
    result = ingestion.ingest(source)
    catalog_spy = _CatalogSpy(catalog)
    query._catalog = catalog_spy
    store.reset_reads()

    default = query.status(str(result.scope.document_id))
    complete = query.status(str(result.scope.document_id), mode=StatusMode.FULL)

    assert default.integrity_coverage is IntegrityCoverage.HEAD
    assert complete.freshness is SourceFreshness.CURRENT
    assert complete.integrity_coverage is IntegrityCoverage.FULL
    assert catalog_spy.aggregate_loads == 1
    assert store.verified_object_ids


def test_status_fails_closed_for_unprepared_and_non_local_documents(tmp_path: Path) -> None:
    """Do not fabricate freshness or integrity when no inspectable READY source exists."""
    _, query, _, catalog, _ = _services(tmp_path)
    local = tmp_path / "registered-only.txt"
    local.write_text("not prepared", encoding="utf-8")
    local_document = catalog.register_document(
        LocalSource(local).source_key,
        document_id=uuid7_from_parts(timestamp_ms=1_720_000_000_000, random_bits=20),
        now=NOW,
    )
    remote_document = catalog.register_document(
        SourceKey(connector="graph", locator="opaque-remote-source"),
        document_id=uuid7_from_parts(timestamp_ms=1_720_000_000_001, random_bits=21),
        now=NOW,
    )

    unprepared = query.status(str(local_document.document_id))
    remote = query.status(str(remote_document.document_id))

    assert unprepared.freshness is SourceFreshness.NO_READY_REPRESENTATION
    assert unprepared.integrity_coverage is IntegrityCoverage.NONE
    assert remote.freshness is SourceFreshness.INTEGRITY_ERROR
    assert remote.integrity_coverage is IntegrityCoverage.NONE


@pytest.mark.parametrize("artifact", ["native", "manifest", "block", "projection"])
def test_full_status_detects_each_persisted_corruption_class(
    tmp_path: Path,
    artifact: str,
) -> None:
    """Keep default coverage bounded while full mode detects every required class."""
    source = tmp_path / f"corrupt-{artifact}.txt"
    source.write_text("first\n\nsecond", encoding="utf-8")
    ingestion, query, store, catalog, _ = _services(tmp_path)
    result = ingestion.ingest(source)
    aggregate = catalog.load_representation(result.scope)
    assert aggregate is not None
    if artifact == "projection":
        with sqlite3.connect(catalog.path) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "DELETE FROM representation_blocks WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ? AND ordinal = 0",
                (
                    str(result.scope.document_id),
                    result.scope.version_id,
                    result.scope.representation_id,
                ),
            )
    else:
        selected = {
            "native": aggregate.representation.native_object,
            "manifest": aggregate.representation.manifest_object,
            "block": aggregate.blocks[0].object,
        }[artifact]
        assert selected is not None
        _object_path(store.delegate.root, selected.object_id).write_bytes(b"corrupt")

    bounded = query.status(str(result.scope.document_id))
    complete = query.status(str(result.scope.document_id), mode=StatusMode.FULL)

    assert bounded.freshness is SourceFreshness.CURRENT
    assert bounded.integrity_coverage is IntegrityCoverage.HEAD
    assert complete.freshness is SourceFreshness.INTEGRITY_ERROR
    assert complete.integrity_coverage is IntegrityCoverage.HEAD


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
