"""Complete all-or-prior lexical index replacement tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


class _FaultCatalog(SQLiteCatalog):
    fail_at: str | None = None

    def _fault_point(self, point: str) -> None:
        if point == self.fail_at:
            raise RuntimeError("synthetic index fault")


def _populated(tmp_path: Path) -> tuple[Path, FilesystemObjectStore, SQLiteCatalog]:
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
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("alpha authoritative\n", encoding="utf-8")
    second.write_text("beta authoritative\n", encoding="utf-8")
    ingestion.ingest(first)
    ingestion.ingest(second)
    return root, store, catalog


def _index_dump(path: Path) -> tuple[tuple[object, ...], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            connection.execute(
                "SELECT e.document_id, e.version_id, e.representation_id, e.ordinal, "
                "e.text_hash, i.block_text FROM representation_block_projection AS e "
                "JOIN block_search_index AS i ON i.rowid=e.entry_id "
                "ORDER BY e.document_id, e.version_id, e.representation_id, e.ordinal"
            ).fetchall()
        )


def test_global_rebuild_removes_drift_and_matches_authoritative_search(tmp_path: Path) -> None:
    """Replace missing/orphaned rows together after verifying every READY block."""
    _root, store, catalog = _populated(tmp_path)
    objects_before = {item.object_id: item.byte_length for item in store.inventory().objects}
    with catalog._write_connection() as connection:
        entry_id = int(
            connection.execute(
                "SELECT entry_id FROM representation_blocks ORDER BY entry_id LIMIT 1"
            ).fetchone()[0]
        )
        connection.execute("DELETE FROM block_search_index WHERE rowid=?", (entry_id,))
        connection.execute(
            "UPDATE representation_blocks SET trust_zone=NULL, page=NULL, slide=NULL, "
            "text_hash=NULL, indexed_at=NULL WHERE entry_id=?",
            (entry_id,),
        )

    search = SearchService(store, catalog, clock=lambda: NOW)
    report = search.rebuild_global()

    assert len(report.scopes) == 2
    assert all(item.is_covered for item in catalog.index_coverage())
    assert search.search("alpha").returned == 1
    assert search.search("beta").returned == 1
    objects_after = {item.object_id: item.byte_length for item in store.inventory().objects}
    assert objects_after == objects_before


def test_global_rebuild_fault_rolls_back_to_prior_complete_index(tmp_path: Path) -> None:
    """A fault after global deletion leaves the previously visible index byte-exact."""
    root, store, _catalog = _populated(tmp_path)
    before = _index_dump(root / "catalog.sqlite3")
    faulted = _FaultCatalog(root / "catalog.sqlite3")
    faulted.fail_at = "after_global_search_index_delete"

    with pytest.raises(RuntimeError, match="synthetic index fault"):
        SearchService(store, faulted, clock=lambda: NOW).rebuild_global()

    assert _index_dump(root / "catalog.sqlite3") == before


def test_rebuild_capacity_rejection_publishes_nothing(tmp_path: Path) -> None:
    """Invoke reserve admission only after verification and before catalog mutation."""
    root, store, catalog = _populated(tmp_path)
    before = _index_dump(root / "catalog.sqlite3")
    observed: list[int] = []

    def reject(required: int) -> None:
        observed.append(required)
        raise RuntimeError("reserve rejected")

    with pytest.raises(RuntimeError, match="reserve rejected"):
        SearchService(store, catalog, clock=lambda: NOW).rebuild_global(admit=reject)
    assert observed and observed[0] > 0
    assert _index_dump(root / "catalog.sqlite3") == before
