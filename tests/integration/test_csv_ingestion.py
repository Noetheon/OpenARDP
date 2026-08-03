"""End-to-end stable CSV ingestion, persistence and retrieval tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openardp.adapters.csv_parser import CsvParserAdapter
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import validate_json
from openardp.domain.ingestion import IngestionDisposition
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService

NOW = datetime(2026, 8, 3, 3, 0, tzinfo=UTC)


class _Clock:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> datetime:
        value = NOW + timedelta(seconds=self.calls)
        self.calls += 1
        return value


def _services(
    tmp_path: Path,
) -> tuple[IngestionService, SearchService, FilesystemObjectStore, SQLiteCatalog]:
    root = tmp_path / "store"
    store = FilesystemObjectStore(root)
    catalog = SQLiteCatalog(root / "catalog.sqlite3")
    clock = _Clock()
    catalog.initialize(now=clock())
    ingestion = IngestionService(
        store,
        catalog,
        CsvParserAdapter(),
        source_factory=LocalSource,
        clock=clock,
        owner_id_factory=lambda: "csv-test",
        lease_token_factory=lambda: "c" * 64,
        random_bits=lambda: 1,
    )
    return ingestion, SearchService(store, catalog, clock=clock), store, catalog


def test_csv_ingest_preserves_native_cells_provenance_search_and_cache(tmp_path: Path) -> None:
    """Exercise the ordinary immutable product path without benchmark conversion."""
    source = tmp_path / "evidence.csv"
    payload = (
        b"cveID,requiredAction,dueDate,requiredAction\n"
        b'CVE-2021-44228,"Apply updates; OR 2) remove affected assets from agency networks",'
        b"2021-12-24,\n"
        b"CVE-2024-3400,Apply mitigations,2024-04-19,Known\n"
    )
    source.write_bytes(payload)
    before = source.stat()
    ingestion, search, store, catalog = _services(tmp_path)

    first = ingestion.ingest(source)
    second = ingestion.ingest(source)

    assert first.disposition is IngestionDisposition.COMMITTED
    assert second.disposition is IngestionDisposition.CACHE_HIT
    assert first.scope == second.scope
    assert first.block_count == 3
    assert b"".join(store.iter_chunks(first.scope.version_id)) == payload
    after = source.stat()
    assert (after.st_size, after.st_mtime_ns, after.st_mode) == (
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )

    aggregate = catalog.load_representation(first.scope)
    assert aggregate is not None
    ingestion.verify_ready_representation(aggregate)
    blocks = [
        validate_json(ContentBlock, b"".join(store.iter_chunks(item.object.object_id)))
        for item in aggregate.blocks
    ]
    assert all(block.kind is BlockKind.TABLE for block in blocks)
    assert all(block.source.extraction_method == "openardp-csv-v1" for block in blocks)
    assert all(block.trust.instruction_execution_allowed is False for block in blocks)
    assert [block.source.extensions["openardp.csv"] for block in blocks] == [
        {"record": 1},
        {"record": 2},
        {"record": 3},
    ]
    assert json.loads(blocks[1].text or "null")["fields"] == [
        ["cveID", "CVE-2021-44228"],
        ["requiredAction", "Apply updates; OR 2) remove affected assets from agency networks"],
        ["dueDate", "2021-12-24"],
        ["requiredAction", ""],
    ]

    outcome = search.search('"CVE-2021-44228" "2021-12-24"')
    assert outcome.returned == 1
    assert outcome.hits[0].block_id == blocks[1].block_id


def test_installed_cli_ingests_and_retrieves_inert_csv_cells(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Route `.csv` through the installed composition without Docling assets."""
    from openardp.interfaces.cli import main

    workspace = tmp_path / "workspace"
    source = tmp_path / "formula.csv"
    source.write_text("kind,value\nformula,=2+3\n", encoding="utf-8")
    assert main(["init", "--store", str(workspace)]) == 0
    capsys.readouterr()

    assert main(["ingest", str(source), "--store", str(workspace), "--json"]) == 0
    ingested = json.loads(capsys.readouterr().out)
    assert ingested["data"]["block_count"] == 2

    assert main(["search", "formula", "--store", str(workspace), "--json"]) == 0
    searched = json.loads(capsys.readouterr().out)
    block_id = searched["data"]["hits"][0]["block_id"]
    assert main(["get", block_id, "--store", str(workspace), "--json"]) == 0
    block = json.loads(capsys.readouterr().out)["data"]
    assert json.loads(block["text"])["fields"] == [
        ["kind", "formula"],
        ["value", "=2+3"],
    ]
