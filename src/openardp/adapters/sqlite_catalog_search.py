"""Verified lexical index persistence and coverage checks."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from openardp.adapters.sqlite_catalog_base import _SQLiteCatalogBase
from openardp.domain.block import BlockKind
from openardp.domain.common import TrustZone
from openardp.domain.ingestion import RepresentationScope, RepresentationState
from openardp.domain.search import (
    IndexCoverage,
    SearchFilters,
    SearchIndexEntry,
    SearchMatchPage,
    SearchMatchRow,
)
from openardp.domain.storage import decode_storage_datetime, encode_storage_datetime
from openardp.ports.catalog import (
    CatalogError,
    RepresentationIncomplete,
    RepresentationIntegrityError,
    RepresentationNotFound,
    SearchIndexDrifted,
    SearchIndexIncomplete,
)


class _SQLiteCatalogSearchMixin(_SQLiteCatalogBase):
    """Verified lexical index persistence and coverage checks."""

    def search_block_entries(
        self,
        *,
        match: str,
        filters: SearchFilters,
        offset: int = 0,
    ) -> SearchMatchPage:
        """Coverage-check scopes, MATCH the FTS index and return one total-ordered page."""
        if not match:
            raise ValueError("match expression is required")
        if type(offset) is not int or offset < 0:
            raise ValueError("search offset must be a non-negative integer")
        with self._read_connection() as connection:
            self._assert_in_scope_coverage(connection, filters)
            # Bound optional filters use NULL-sentinel predicates so the SQL text is static.
            current_heads_only = 0 if (filters.include_history or filters.version_id) else 1
            document_id = None if filters.document_id is None else str(filters.document_id)
            kind = None if filters.kind is None else filters.kind.value
            trust = None if filters.trust_zone is None else filters.trust_zone.value
            bound: list[object] = [
                match,
                document_id,
                document_id,
                filters.version_id,
                filters.version_id,
                current_heads_only,
                kind,
                kind,
                trust,
                trust,
                filters.page,
                filters.page,
                filters.slide,
                filters.slide,
            ]
            available = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM block_search_index AS i
                    INNER JOIN representation_block_projection AS e ON e.entry_id = i.rowid
                    WHERE block_search_index MATCH ?
                      AND (? IS NULL OR e.document_id = ?)
                      AND (? IS NULL OR e.version_id = ?)
                      AND (? = 0 OR EXISTS (
                            SELECT 1 FROM document_heads AS h
                            WHERE h.document_id = e.document_id
                              AND h.version_id = e.version_id
                              AND h.representation_id = e.representation_id
                      ))
                      AND (? IS NULL OR e.kind = ?)
                      AND (? IS NULL OR e.trust_zone = ?)
                      AND (? IS NULL OR e.page = ?)
                      AND (? IS NULL OR e.slide = ?)
                    """,
                    bound,
                ).fetchone()[0]
            )
            try:
                rows = connection.execute(
                    """
                    SELECT e.entry_id, e.document_id, e.version_id, e.representation_id,
                           e.ordinal, e.block_id, e.kind, e.trust_zone, e.line_start, e.line_end,
                           e.page, e.slide, e.text_hash, bm25(block_search_index) AS rank,
                           e.object_id, o.byte_length
                    FROM block_search_index AS i
                    INNER JOIN representation_block_projection AS e ON e.entry_id = i.rowid
                    INNER JOIN objects AS o ON o.object_id = e.object_id
                    WHERE block_search_index MATCH ?
                      AND (? IS NULL OR e.document_id = ?)
                      AND (? IS NULL OR e.version_id = ?)
                      AND (? = 0 OR EXISTS (
                            SELECT 1 FROM document_heads AS h
                            WHERE h.document_id = e.document_id
                              AND h.version_id = e.version_id
                              AND h.representation_id = e.representation_id
                      ))
                      AND (? IS NULL OR e.kind = ?)
                      AND (? IS NULL OR e.trust_zone = ?)
                      AND (? IS NULL OR e.page = ?)
                      AND (? IS NULL OR e.slide = ?)
                    ORDER BY rank ASC, e.document_id ASC, e.ordinal ASC
                    LIMIT ? OFFSET ?
                    """,
                    [*bound, filters.limit, offset],
                ).fetchall()
            except sqlite3.OperationalError as error:
                raise CatalogError("search query execution failed") from error
            match_rows = tuple(self._search_match_row(row) for row in rows)
            return SearchMatchPage(
                rows=match_rows,
                available=available,
                limit=filters.limit,
            )

    def index_coverage(
        self,
        *,
        scopes: tuple[RepresentationScope, ...] | None = None,
    ) -> tuple[IndexCoverage, ...]:
        """Return deterministic structural coverage without mutating catalog state."""
        with self._read_connection() as connection:
            selected = scopes if scopes is not None else self._list_ready_scopes(connection)
            reports: list[IndexCoverage] = []
            for scope in selected:
                ready_rows = connection.execute(
                    "SELECT ordinal FROM representation_block_projection "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                    "ORDER BY ordinal",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchall()
                indexed_rows = connection.execute(
                    "SELECT ordinal FROM representation_block_projection "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                    "AND indexed_at IS NOT NULL "
                    "ORDER BY ordinal",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchall()
                ready = tuple(int(row["ordinal"]) for row in ready_rows)
                indexed = tuple(int(row["ordinal"]) for row in indexed_rows)
                ready_set = set(ready)
                indexed_set = set(indexed)
                reports.append(
                    IndexCoverage(
                        scope=scope,
                        ready_ordinals=ready,
                        indexed_ordinals=indexed,
                        missing=tuple(sorted(ready_set - indexed_set)),
                        orphaned=tuple(sorted(indexed_set - ready_set)),
                    )
                )
            return tuple(reports)

    def replace_scope_index(
        self,
        scope: RepresentationScope,
        entries: tuple[SearchIndexEntry, ...],
        texts: tuple[str, ...],
        *,
        now: datetime,
    ) -> int:
        """Atomically replace one READY scope's mapping and FTS rows."""
        del now
        if len(entries) != len(texts):
            raise ValueError("entries and texts must have equal length")
        with self._write_connection() as connection:
            row = self._load_representation_row(connection, scope)
            if row is None:
                raise RepresentationNotFound("representation does not exist")
            if str(row["state"]) != RepresentationState.READY.value:
                raise RepresentationIncomplete("representation is not ready")
            for entry in entries:
                if entry.scope != scope:
                    raise RepresentationIntegrityError("index entry scope does not match")
            existing_ids = connection.execute(
                "SELECT entry_id FROM representation_block_projection "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            for existing in existing_ids:
                entry_id = int(existing["entry_id"])
                connection.execute(
                    "DELETE FROM block_search_index WHERE rowid = ?",
                    (entry_id,),
                )
            connection.execute(
                "UPDATE representation_blocks SET trust_zone = NULL, page = NULL, "
                "slide = NULL, text_hash = NULL, indexed_at = NULL WHERE scope_key = ("
                "SELECT scope_key FROM representation_scopes WHERE document_id = ? "
                "AND version_id = ? AND representation_id = ?)",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            )
            self._fault_point("after_search_index_delete")
            for entry, text in zip(entries, texts, strict=True):
                self._insert_search_entry(connection, entry, text)
                self._fault_point("after_search_index_entry")
            self._fault_point("after_search_index")
            return len(entries)

    def replace_global_index(
        self,
        entries: tuple[SearchIndexEntry, ...],
        texts: tuple[str, ...],
        *,
        now: datetime,
    ) -> int:
        """Verify and atomically replace the complete READY lexical accelerator."""
        del now
        if len(entries) != len(texts):
            raise ValueError("entries and texts must have equal length")
        keys = tuple(
            (
                str(entry.scope.document_id),
                entry.scope.version_id,
                entry.scope.representation_id,
                entry.ordinal,
                str(entry.block_id),
                entry.kind.value,
                entry.line_start,
                entry.line_end,
            )
            for entry in entries
        )
        if keys != tuple(sorted(set(keys))):
            raise RepresentationIntegrityError("global index entries are not canonical")
        with self._write_connection() as connection:
            expected = tuple(
                (
                    str(row["document_id"]),
                    str(row["version_id"]),
                    str(row["representation_id"]),
                    int(row["ordinal"]),
                    str(row["block_id"]),
                    str(row["kind"]),
                    int(row["line_start"]),
                    int(row["line_end"]),
                )
                for row in connection.execute(
                    "SELECT b.document_id, b.version_id, b.representation_id, b.ordinal, "
                    "b.block_id, b.kind, b.line_start, b.line_end "
                    "FROM representation_block_projection AS b "
                    "JOIN document_representations AS r ON r.document_id=b.document_id "
                    "AND r.version_id=b.version_id "
                    "AND r.representation_id=b.representation_id "
                    "WHERE r.state='READY' ORDER BY b.document_id, b.version_id, "
                    "b.representation_id, b.ordinal"
                ).fetchall()
            )
            if keys != expected:
                raise RepresentationIntegrityError(
                    "global index input does not match authoritative corpus"
                )
            connection.execute("DELETE FROM block_search_index")
            connection.execute(
                "UPDATE representation_blocks SET trust_zone = NULL, page = NULL, "
                "slide = NULL, text_hash = NULL, indexed_at = NULL"
            )
            self._fault_point("after_global_search_index_delete")
            for entry, body in zip(entries, texts, strict=True):
                self._insert_search_entry(connection, entry, body)
                self._fault_point("after_global_search_index_entry")
            self._fault_point("after_global_search_index")
            return len(entries)

    def search_index_diagnostics(self) -> tuple[int, int]:
        """Return mapping count and logical FTS UTF-8 bytes without body output."""
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT count(*) AS entry_count, "
                "coalesce(sum(length(CAST(block_text AS BLOB))), 0) AS byte_count "
                "FROM block_search_index"
            ).fetchone()
            return int(row["entry_count"]), int(row["byte_count"])

    def list_ready_scopes(
        self,
        *,
        document_id: UUID | None = None,
    ) -> tuple[RepresentationScope, ...]:
        """Return READY scopes in deterministic document/version/representation order."""
        with self._read_connection() as connection:
            return self._list_ready_scopes(connection, document_id=document_id)

    def list_scope_index_entries(
        self,
        scope: RepresentationScope,
    ) -> tuple[SearchIndexEntry, ...]:
        """Return stored index mapping rows for one scope in ordinal order."""
        with self._read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM representation_block_projection "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                "AND indexed_at IS NOT NULL "
                "ORDER BY ordinal",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchall()
            return tuple(self._search_index_entry(row) for row in rows)

    def _list_ready_scopes(
        self,
        connection: sqlite3.Connection,
        *,
        document_id: UUID | None = None,
    ) -> tuple[RepresentationScope, ...]:
        if document_id is None:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations WHERE state = 'READY' "
                "ORDER BY document_id, version_id, representation_id"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations WHERE state = 'READY' AND document_id = ? "
                "ORDER BY document_id, version_id, representation_id",
                (str(document_id),),
            ).fetchall()
        return tuple(
            RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            )
            for row in rows
        )

    def _assert_in_scope_coverage(
        self,
        connection: sqlite3.Connection,
        filters: SearchFilters,
    ) -> None:
        scopes = self._resolve_search_scopes(connection, filters)
        for scope in scopes:
            expected_row = connection.execute(
                "SELECT block_count FROM document_representations "
                "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                "AND state = 'READY'",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchone()
            if expected_row is None:
                raise SearchIndexDrifted("search scope is not a ready representation")
            ready_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM representation_block_projection "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ?",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchone()[0]
            )
            if ready_count != int(expected_row["block_count"]):
                raise SearchIndexDrifted("search block projection has drifted")
            indexed_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM representation_block_projection "
                    "WHERE document_id = ? AND version_id = ? AND representation_id = ? "
                    "AND indexed_at IS NOT NULL",
                    (str(scope.document_id), scope.version_id, scope.representation_id),
                ).fetchone()[0]
            )
            if ready_count != indexed_count:
                raise SearchIndexIncomplete("search index coverage is incomplete")
            missing = connection.execute(
                "SELECT b.ordinal FROM representation_block_projection AS b "
                "LEFT JOIN block_search_index AS i ON i.rowid = b.entry_id "
                "WHERE b.document_id = ? AND b.version_id = ? AND b.representation_id = ? "
                "AND (b.indexed_at IS NULL OR i.rowid IS NULL) LIMIT 1",
                (str(scope.document_id), scope.version_id, scope.representation_id),
            ).fetchone()
            if missing is not None:
                raise SearchIndexIncomplete("search index coverage is incomplete")

    def _resolve_search_scopes(
        self,
        connection: sqlite3.Connection,
        filters: SearchFilters,
    ) -> tuple[RepresentationScope, ...]:
        if filters.version_id is not None:
            assert filters.document_id is not None
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations "
                "WHERE state = 'READY' AND document_id = ? AND version_id = ? "
                "ORDER BY representation_id",
                (str(filters.document_id), filters.version_id),
            ).fetchall()
        elif filters.document_id is not None and not filters.include_history:
            rows = connection.execute(
                "SELECT h.document_id, h.version_id, h.representation_id "
                "FROM document_heads AS h "
                "INNER JOIN document_representations AS r "
                "ON r.document_id = h.document_id AND r.version_id = h.version_id "
                "AND r.representation_id = h.representation_id "
                "WHERE h.document_id = ? AND r.state = 'READY'",
                (str(filters.document_id),),
            ).fetchall()
        elif filters.document_id is not None:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations "
                "WHERE state = 'READY' AND document_id = ? "
                "ORDER BY version_id, representation_id",
                (str(filters.document_id),),
            ).fetchall()
        elif not filters.include_history:
            rows = connection.execute(
                "SELECT h.document_id, h.version_id, h.representation_id "
                "FROM document_heads AS h "
                "INNER JOIN document_representations AS r "
                "ON r.document_id = h.document_id AND r.version_id = h.version_id "
                "AND r.representation_id = h.representation_id "
                "WHERE r.state = 'READY' "
                "ORDER BY h.document_id"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT document_id, version_id, representation_id "
                "FROM document_representations WHERE state = 'READY' "
                "ORDER BY document_id, version_id, representation_id"
            ).fetchall()
        return tuple(
            RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            )
            for row in rows
        )

    def _insert_search_entry(
        self,
        connection: sqlite3.Connection,
        entry: SearchIndexEntry,
        text: str,
    ) -> int:
        cursor = connection.execute(
            "UPDATE representation_blocks SET trust_zone = ?, page = ?, slide = ?, "
            "text_hash = ?, indexed_at = ? WHERE scope_key = (SELECT scope_key FROM "
            "representation_scopes WHERE document_id = ? AND version_id = ? "
            "AND representation_id = ?) AND ordinal = ? AND block_id = ? AND kind = ? "
            "AND line_start = ? AND line_end = ?",
            (
                entry.trust_zone.value,
                entry.page,
                entry.slide,
                entry.text_hash,
                encode_storage_datetime(entry.indexed_at),
                str(entry.scope.document_id),
                entry.scope.version_id,
                entry.scope.representation_id,
                entry.ordinal,
                str(entry.block_id),
                entry.kind.value,
                entry.line_start,
                entry.line_end,
            ),
        )
        if cursor.rowcount != 1:
            raise RepresentationIntegrityError("search index entry does not match a block")
        row = connection.execute(
            "SELECT entry_id FROM representation_block_projection WHERE document_id = ? "
            "AND version_id = ? AND representation_id = ? AND ordinal = ?",
            (
                str(entry.scope.document_id),
                entry.scope.version_id,
                entry.scope.representation_id,
                entry.ordinal,
            ),
        ).fetchone()
        if row is None:
            raise RepresentationIntegrityError("search index block disappeared")
        entry_id = int(row["entry_id"])
        connection.execute(
            "INSERT INTO block_search_index(rowid, block_text) VALUES (?, ?)",
            (entry_id, text),
        )
        return entry_id

    @staticmethod
    def _search_match_row(row: sqlite3.Row) -> SearchMatchRow:
        return SearchMatchRow(
            entry_id=int(row["entry_id"]),
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            ordinal=int(row["ordinal"]),
            block_id=UUID(str(row["block_id"])),
            kind=BlockKind(str(row["kind"])),
            trust_zone=TrustZone(str(row["trust_zone"])),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
            page=int(row["page"]) if row["page"] is not None else None,
            slide=int(row["slide"]) if row["slide"] is not None else None,
            text_hash=str(row["text_hash"]),
            rank=float(row["rank"]),
            object_id=str(row["object_id"]),
            object_byte_length=int(row["byte_length"]),
        )

    @staticmethod
    def _search_index_entry(row: sqlite3.Row) -> SearchIndexEntry:
        return SearchIndexEntry(
            scope=RepresentationScope(
                document_id=UUID(str(row["document_id"])),
                version_id=str(row["version_id"]),
                representation_id=str(row["representation_id"]),
            ),
            ordinal=int(row["ordinal"]),
            block_id=UUID(str(row["block_id"])),
            kind=BlockKind(str(row["kind"])),
            trust_zone=TrustZone(str(row["trust_zone"])),
            line_start=int(row["line_start"]),
            line_end=int(row["line_end"]),
            page=int(row["page"]) if row["page"] is not None else None,
            slide=int(row["slide"]) if row["slide"] is not None else None,
            text_hash=str(row["text_hash"]),
            indexed_at=decode_storage_datetime(str(row["indexed_at"])),
        )


__all__ = ["_SQLiteCatalogSearchMixin"]
