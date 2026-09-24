"""Disposable SQLite agent index: round trip, search filters and self-healing."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from openardp.adapters.agent_index import INDEX_FORMAT, SQLiteAgentIndex
from openardp.domain.agent_query import plan_query
from openardp.domain.agent_text import (
    AgentHeading,
    AgentPage,
    AgentPassage,
    AgentTextRecord,
    PageLabel,
)


def _record(document_id: str, text: str) -> AgentTextRecord:
    return AgentTextRecord(
        document_id=document_id,
        version_id="sha256:" + "1" * 64,
        representation_id="sha256:" + "2" * 64,
        locator=f"/docs/{document_id}.md",
        label=f"{document_id}.md",
        media_type="text/markdown",
        renderer="openardp-source-text/1",
        text_sha256="sha256:" + "3" * 64,
        token_estimate=len(text) // 4,
        line_count=text.count("\n") + 1,
        page_label=PageLabel.PAGE,
        page_count=1,
        heading_count=1,
        source_byte_length=len(text),
        source_modified_at=datetime(2026, 9, 1, tzinfo=UTC),
        indexed_at=datetime(2026, 9, 2, tzinfo=UTC),
        text=text,
        pages=(AgentPage(number=1, line=1),),
        headings=(AgentHeading(line=2, level=1, text="Title"),),
    )


def _passage(document_id: str, text: str, ordinal: int = 0) -> AgentPassage:
    return AgentPassage(
        document_id=document_id,
        ordinal=ordinal,
        line_start=3,
        line_end=3,
        page=1,
        heading="Title",
        text=text,
    )


def test_documents_round_trip_and_search_respects_filters(tmp_path: Path) -> None:
    """Store complete records, search passages by rank and filter by document."""
    index = SQLiteAgentIndex.for_workspace(tmp_path)
    index.replace_document(
        _record("a", "x\n# Title\nAlpha sensor text"), [_passage("a", "alpha sensor")]
    )
    index.replace_document(
        _record("b", "y\n# Title\nBeta sensor text"), [_passage("b", "beta sensor")]
    )
    loaded = index.load_text("a")
    assert loaded is not None and loaded.text.endswith("Alpha sensor text")
    assert loaded.pages == (AgentPage(number=1, line=1),)
    assert [document.document_id for document in index.indexed_documents()] == ["a", "b"]
    expression = plan_query("sensor").match_expression()
    assert {
        passage.document_id for passage, _ in index.search(expression, document_ids=None, limit=10)
    } == {"a", "b"}
    only_b = index.search(expression, document_ids=["b"], limit=10)
    assert [passage.document_id for passage, _rank in only_b] == ["b"]
    assert index.search(expression, document_ids=[], limit=10) == ()
    assert index.search("", document_ids=None, limit=10) == ()
    assert index.search('"unterminated', document_ids=None, limit=10) == ()
    index.replace_document(_record("a", "new"), [])
    assert index.search(plan_query("alpha").match_expression(), document_ids=None, limit=5) == ()
    index.remove_documents(["a"])
    index.remove_documents([])
    assert index.load_text("a") is None


def test_foreign_format_and_corrupt_files_are_rebuilt(tmp_path: Path) -> None:
    """Discard an index of another format or an unreadable file instead of failing."""
    index = SQLiteAgentIndex.for_workspace(tmp_path)
    index.replace_document(_record("a", "text"), [_passage("a", "some text")])
    with sqlite3.connect(index.path) as connection:
        connection.execute("UPDATE meta SET value = 'old-format' WHERE key = 'format'")
    assert index.indexed_documents() == ()
    with sqlite3.connect(index.path) as connection:
        assert connection.execute("SELECT value FROM meta").fetchone()[0] == INDEX_FORMAT
    index.path.write_bytes(b"not a sqlite database" * 100)
    assert index.indexed_documents() == ()
    index.clear()
    assert not index.path.exists()
