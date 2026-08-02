"""Read-only SQLite projections for document navigation and status."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from uuid import UUID

from openardp.domain.ingestion import (
    DocumentHead,
    DocumentRepresentation,
    DocumentStatusSnapshot,
    DocumentSummary,
    RepresentationScope,
    RepresentationState,
)
from openardp.domain.storage import LogicalDocument, SourceKey, decode_storage_datetime


def load_document_head(
    connection: sqlite3.Connection,
    document_id: UUID,
    *,
    convert: Callable[[sqlite3.Row], DocumentHead],
) -> DocumentHead | None:
    """Load one current head from an enclosing read transaction."""
    row = connection.execute(
        "SELECT * FROM document_heads WHERE document_id = ?",
        (str(document_id),),
    ).fetchone()
    return convert(row) if row is not None else None


def load_document_status_snapshot(
    connection: sqlite3.Connection,
    document_id: UUID,
    *,
    load_document: Callable[[sqlite3.Connection, UUID], LogicalDocument | None],
    load_representation_row: Callable[
        [sqlite3.Connection, RepresentationScope], sqlite3.Row | None
    ],
    convert_head: Callable[[sqlite3.Row], DocumentHead],
    convert_representation: Callable[[sqlite3.Row], DocumentRepresentation],
) -> DocumentStatusSnapshot | None:
    """Load one document/head/header tuple from an enclosing read transaction."""
    document = load_document(connection, document_id)
    if document is None:
        return None
    head = load_document_head(connection, document_id, convert=convert_head)
    if head is None:
        return DocumentStatusSnapshot(document=document)
    row = load_representation_row(connection, head.scope)
    return DocumentStatusSnapshot(
        document=document,
        head=head,
        representation=convert_representation(row) if row is not None else None,
    )


def list_document_summaries(
    connection: sqlite3.Connection,
    *,
    warning_codes: Callable[[str], tuple[str, ...]],
) -> tuple[DocumentSummary, ...]:
    """Project all body-free current document summaries from one read transaction."""
    rows = connection.execute(
        "SELECT d.*, h.version_id, h.representation_id, h.last_ingested_at, "
        "r.state, r.block_count, r.warning_codes_json FROM documents AS d "
        "LEFT JOIN document_heads AS h ON h.document_id = d.document_id "
        "LEFT JOIN document_representations AS r ON r.document_id = h.document_id "
        "AND r.version_id = h.version_id AND r.representation_id = h.representation_id "
        "ORDER BY d.connector, d.source_locator, d.document_id"
    ).fetchall()
    summaries: list[DocumentSummary] = []
    for row in rows:
        document_id = UUID(str(row["document_id"]))
        has_head = row["representation_id"] is not None
        warnings = warning_codes(str(row["warning_codes_json"])) if has_head else ()
        summaries.append(
            DocumentSummary(
                document_id=document_id,
                source_key=SourceKey(
                    connector=str(row["connector"]),
                    locator=str(row["source_locator"]),
                ),
                head=(
                    RepresentationScope(
                        document_id=document_id,
                        version_id=str(row["version_id"]),
                        representation_id=str(row["representation_id"]),
                    )
                    if has_head
                    else None
                ),
                state=RepresentationState(str(row["state"])) if has_head else None,
                block_count=int(row["block_count"]) if has_head else 0,
                warning_count=len(warnings),
                last_ingested_at=(
                    decode_storage_datetime(str(row["last_ingested_at"])) if has_head else None
                ),
            )
        )
    return tuple(summaries)


__all__ = [
    "list_document_summaries",
    "load_document_head",
    "load_document_status_snapshot",
]
