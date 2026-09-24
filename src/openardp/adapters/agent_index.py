"""Disposable SQLite FTS5 index of agent texts and passages.

The index lives in ``<workspace>/agent-cache/`` next to, never inside, the authoritative
catalog. It holds no evidence authority: any unreadable, foreign-version or corrupt file
is discarded and rebuilt from the catalog, the content-addressed store and retained
provider-native artifacts. All SQL is static and parameterized.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
from collections.abc import Iterator, Sequence
from pathlib import Path

from openardp.domain.agent_text import (
    AGENT_TEXT_ALGORITHM,
    AgentPassage,
    AgentTextRecord,
    IndexedDocument,
)

CACHE_DIRECTORY = "agent-cache"
INDEX_FILENAME = "agent-index.sqlite3"
INDEX_FORMAT = f"openardp-agent-index/1+{AGENT_TEXT_ALGORITHM}"
_BUSY_TIMEOUT_SECONDS = 30.0
_MAX_FILTER_DOCUMENTS = 500

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT",
    """
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        facts TEXT NOT NULL,
        structure TEXT NOT NULL,
        text TEXT NOT NULL
    ) STRICT
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(
        text,
        heading,
        document_id UNINDEXED,
        ordinal UNINDEXED,
        line_start UNINDEXED,
        line_end UNINDEXED,
        page UNINDEXED,
        tokenize = 'unicode61 remove_diacritics 2',
        prefix = '2 3 4'
    )
    """,
)


class SQLiteAgentIndex:
    """One local disposable agent index file with automatic rebuild on mismatch."""

    def __init__(self, path: Path) -> None:
        """Bind the index file; the parent cache directory is created on demand."""
        self._path = path

    @classmethod
    def for_workspace(cls, workspace_root: Path) -> SQLiteAgentIndex:
        """Return the index inside one workspace's disposable cache directory."""
        return cls(workspace_root / CACHE_DIRECTORY / INDEX_FILENAME)

    @property
    def path(self) -> Path:
        """Return the index file location."""
        return self._path

    def indexed_documents(self) -> tuple[IndexedDocument, ...]:
        """Return body-free facts for every indexed document in identifier order."""
        with self._connection() as connection:
            rows = connection.execute("SELECT facts FROM documents ORDER BY document_id").fetchall()
        return tuple(IndexedDocument.model_validate_json(row[0]) for row in rows)

    def replace_document(self, record: AgentTextRecord, passages: Sequence[AgentPassage]) -> None:
        """Atomically replace one document text and all of its passages."""
        facts = json.dumps(
            record.model_dump(mode="json", exclude={"text", "pages", "headings"}),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        structure = json.dumps(
            {
                "pages": [page.model_dump(mode="json") for page in record.pages],
                "headings": [heading.model_dump(mode="json") for heading in record.headings],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connection() as connection, connection:
            connection.execute("DELETE FROM passages WHERE document_id = ?", (record.document_id,))
            connection.execute(
                "INSERT OR REPLACE INTO documents (document_id, facts, structure, text) "
                "VALUES (?, ?, ?, ?)",
                (record.document_id, facts, structure, record.text),
            )
            connection.executemany(
                "INSERT INTO passages "
                "(text, heading, document_id, ordinal, line_start, line_end, page) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        passage.text,
                        passage.heading,
                        passage.document_id,
                        passage.ordinal,
                        passage.line_start,
                        passage.line_end,
                        passage.page,
                    )
                    for passage in passages
                ],
            )

    def remove_documents(self, document_ids: Sequence[str]) -> None:
        """Remove documents that no longer have a prepared head."""
        if not document_ids:
            return
        with self._connection() as connection, connection:
            for document_id in document_ids:
                connection.execute("DELETE FROM passages WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))

    def load_text(self, document_id: str) -> AgentTextRecord | None:
        """Return one complete indexed text record."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT facts, structure, text FROM documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        structure = json.loads(row[1])
        payload.update(
            {
                "text": row[2],
                "pages": structure["pages"],
                "headings": structure["headings"],
            }
        )
        return AgentTextRecord.model_validate_json(json.dumps(payload, ensure_ascii=False))

    def search(
        self,
        match_expression: str,
        *,
        document_ids: Sequence[str] | None,
        limit: int,
    ) -> tuple[tuple[AgentPassage, float], ...]:
        """Return passages matching one bound FTS expression ordered by BM25 rank."""
        if not match_expression or limit < 1:
            return ()
        query = (
            "SELECT text, heading, document_id, ordinal, line_start, line_end, page, "
            "bm25(passages, 1.0, 0.35) AS rank FROM passages WHERE passages MATCH ?"
        )
        parameters: list[object] = [match_expression]
        if document_ids is not None:
            selected = list(dict.fromkeys(document_ids))[:_MAX_FILTER_DOCUMENTS]
            if not selected:
                return ()
            query += " AND document_id IN (" + ", ".join("?" for _ in selected) + ")"
            parameters.extend(selected)
        query += " ORDER BY rank LIMIT ?"
        parameters.append(limit)
        with self._connection() as connection:
            try:
                rows = connection.execute(query, parameters).fetchall()
            except sqlite3.OperationalError:
                return ()
        return tuple(
            (
                AgentPassage(
                    text=row[0],
                    heading=row[1],
                    document_id=row[2],
                    ordinal=int(row[3]),
                    line_start=int(row[4]),
                    line_end=int(row[5]),
                    page=None if row[6] is None else int(row[6]),
                ),
                float(row[7]),
            )
            for row in rows
        )

    def clear(self) -> None:
        """Delete the whole disposable index; the next use rebuilds it."""
        for suffix in ("", "-wal", "-shm", "-journal"):
            with contextlib.suppress(FileNotFoundError):
                Path(f"{self._path}{suffix}").unlink()

    @contextlib.contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._open()
        try:
            yield connection
        finally:
            connection.close()

    def _open(self) -> sqlite3.Connection:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            return self._open_current()
        except sqlite3.DatabaseError:
            self.clear()
            return self._open_current()

    def _open_current(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=_BUSY_TIMEOUT_SECONDS)
        try:
            with contextlib.suppress(OSError):
                os.chmod(self._path, 0o600)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            if self._format(connection) != INDEX_FORMAT:
                self._reset(connection)
            return connection
        except BaseException:
            connection.close()
            raise

    @staticmethod
    def _format(connection: sqlite3.Connection) -> str | None:
        try:
            row = connection.execute("SELECT value FROM meta WHERE key = 'format'").fetchone()
        except sqlite3.OperationalError:
            return None
        return None if row is None else str(row[0])

    @staticmethod
    def _reset(connection: sqlite3.Connection) -> None:
        with connection:
            for table in ("passages", "documents", "meta"):
                connection.execute(f"DROP TABLE IF EXISTS {table}")
            for statement in _SCHEMA:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO meta (key, value) VALUES ('format', ?)",
                (INDEX_FORMAT,),
            )


__all__ = ["CACHE_DIRECTORY", "INDEX_FILENAME", "INDEX_FORMAT", "SQLiteAgentIndex"]
