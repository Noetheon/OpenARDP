"""Exact lexical search and explicit reindex over verified READY evidence."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from openardp.adapters.local_source import LocalSource
from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import TrustZone, validate_json
from openardp.domain.ingestion import (
    RepresentationScope,
    RepresentationState,
)
from openardp.domain.search import (
    DEFAULT_SEARCH_LIMIT,
    ReindexOutcome,
    ReindexReport,
    ReindexScopeReport,
    SearchFilters,
    SearchHit,
    SearchIndexEntry,
    SearchOutcome,
    SearchQuery,
    SearchQueryRejected,
    block_text_for_index,
    build_snippet,
    indexed_text_hash,
)
from openardp.domain.storage import StoredObject
from openardp.ports.catalog import (
    Catalog,
    DocumentNotFound,
    RepresentationIntegrityError,
    RepresentationNotFound,
    SearchIndexDrifted,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SearchService:
    """Grammar-bounded search and verified reindex over the local catalog and CAS."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: Catalog,
        *,
        source_factory: Callable[[Path], LocalSource] = LocalSource,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """Bind verified-read ports for search and reindex."""
        self._object_store = object_store
        self._catalog = catalog
        self._source_factory = source_factory
        self._clock = clock

    def search(
        self,
        raw_query: str,
        *,
        document: str | None = None,
        version_id: str | None = None,
        include_history: bool = False,
        kind: str | None = None,
        trust: str | None = None,
        page: int | None = None,
        slide: int | None = None,
        limit: int | None = None,
    ) -> SearchOutcome:
        """Parse, filter, match and verify hits with bounded snippets."""
        query = SearchQuery.parse(raw_query)
        filters = self._resolve_filters(
            document=document,
            version_id=version_id,
            include_history=include_history,
            kind=kind,
            trust=trust,
            page=page,
            slide=slide,
            limit=limit,
        )
        page_result = self._catalog.search_block_entries(
            match=query.match_expression(),
            filters=filters,
        )
        hits: list[SearchHit] = []
        for order_index, row in enumerate(page_result.rows):
            text = self._verified_block_text(
                row.object_id,
                row.object_byte_length,
                row.text_hash,
            )
            snippet = build_snippet(text, query)
            hits.append(
                SearchHit(
                    scope=row.scope,
                    block_id=row.block_id,
                    kind=row.kind,
                    trust_zone=row.trust_zone,
                    line_start=row.line_start,
                    line_end=row.line_end,
                    page=row.page,
                    slide=row.slide,
                    rank=row.rank,
                    order_index=order_index,
                    snippet=snippet,
                )
            )
        returned = len(hits)
        return SearchOutcome(
            hits=tuple(hits),
            truncated=page_result.available > returned,
            returned=returned,
            available=page_result.available,
            query_echo=raw_query[:4096],
        )

    def reindex(self, *, document: str | None = None) -> ReindexReport:
        """Rebuild index rows for READY scopes from verified CAS blocks only."""
        document_id = self._resolve_document_id(document) if document is not None else None
        scopes = self._catalog.list_ready_scopes(document_id=document_id)
        reports: list[ReindexScopeReport] = []
        now = self._clock()
        for scope in scopes:
            try:
                entry_count, outcome = self._reindex_scope(scope, now=now)
                reports.append(
                    ReindexScopeReport(
                        scope=scope,
                        outcome=outcome,
                        failure_code=None,
                        entry_count=entry_count,
                    )
                )
            except (
                RepresentationIntegrityError,
                RepresentationNotFound,
                ObjectStoreError,
                SearchIndexDrifted,
                ValidationError,
                ValueError,
            ):
                reports.append(
                    ReindexScopeReport(
                        scope=scope,
                        outcome=ReindexOutcome.FAILED,
                        failure_code="reindex_failed",
                        entry_count=0,
                    )
                )
        reports.sort(
            key=lambda item: (
                str(item.scope.document_id),
                item.scope.version_id,
                item.scope.representation_id,
            )
        )
        return ReindexReport(scopes=tuple(reports))

    def _reindex_scope(
        self,
        scope: RepresentationScope,
        *,
        now: datetime,
    ) -> tuple[int, ReindexOutcome]:
        aggregate = self._catalog.load_representation(scope)
        if aggregate is None or aggregate.representation.state is not RepresentationState.READY:
            raise RepresentationNotFound("ready representation does not exist")
        entries: list[SearchIndexEntry] = []
        texts: list[str] = []
        for projection in aggregate.blocks:
            payload = self._read_object(projection.object)
            block = validate_json(ContentBlock, payload)
            if (
                block.block_id != projection.block_id
                or block.kind != projection.kind
                or block.document_id != scope.document_id
                or block.version_id != scope.version_id
                or block.representation_id != scope.representation_id
            ):
                raise RepresentationIntegrityError("block does not match catalog projection")
            text = block_text_for_index(block.text)
            entries.append(
                SearchIndexEntry(
                    scope=scope,
                    ordinal=projection.ordinal,
                    block_id=projection.block_id,
                    kind=projection.kind,
                    trust_zone=block.trust.zone,
                    line_start=projection.line_start,
                    line_end=projection.line_end,
                    page=None,
                    slide=None,
                    text_hash=indexed_text_hash(text),
                    indexed_at=now,
                )
            )
            texts.append(text)
        coverage = self._catalog.index_coverage(scopes=(scope,))
        stored = self._catalog.list_scope_index_entries(scope)
        if (
            coverage
            and coverage[0].is_covered
            and {item.ordinal: item.text_hash for item in stored}
            == {item.ordinal: item.text_hash for item in entries}
        ):
            return len(entries), ReindexOutcome.CURRENT
        count = self._catalog.replace_scope_index(
            scope,
            tuple(entries),
            tuple(texts),
            now=now,
        )
        return count, ReindexOutcome.REBUILT

    def _resolve_filters(
        self,
        *,
        document: str | None,
        version_id: str | None,
        include_history: bool,
        kind: str | None,
        trust: str | None,
        page: int | None,
        slide: int | None,
        limit: int | None,
    ) -> SearchFilters:
        document_id = self._resolve_document_id(document) if document is not None else None
        if version_id is not None and document_id is None:
            raise SearchQueryRejected("version filter requires a document scope")
        try:
            kind_value = None if kind is None else BlockKind(kind)
            trust_value = None if trust is None else TrustZone(trust)
            return SearchFilters(
                document_id=document_id,
                version_id=version_id,
                include_history=include_history or version_id is not None,
                kind=kind_value,
                trust_zone=trust_value,
                page=page,
                slide=slide,
                limit=DEFAULT_SEARCH_LIMIT if limit is None else limit,
            )
        except (ValueError, ValidationError) as error:
            raise SearchQueryRejected("search filter is invalid") from error

    def _resolve_document_id(self, target: str) -> UUID:
        try:
            document_id = UUID(target)
        except ValueError:
            source = self._source_factory(Path(target))
            document = self._catalog.get_document_by_source(source.source_key)
            if document is None:
                raise DocumentNotFound(target) from None
            return document.document_id
        document = self._catalog.get_document(document_id)
        if document is None:
            raise DocumentNotFound(str(document_id))
        return document_id

    def _verified_block_text(
        self,
        object_id: str,
        byte_length: int,
        text_hash: str,
    ) -> str:
        payload = self._read_object(StoredObject(object_id=object_id, byte_length=byte_length))
        try:
            block = validate_json(ContentBlock, payload)
        except (ValidationError, ValueError) as error:
            raise SearchIndexDrifted("indexed block payload is invalid") from error
        text = block_text_for_index(block.text)
        if indexed_text_hash(text) != text_hash:
            raise SearchIndexDrifted("indexed text hash does not match verified block")
        return text

    def _read_object(self, stored: StoredObject) -> bytes:
        verified = self._object_store.verify(
            stored.object_id,
            expected_length=stored.byte_length,
        )
        payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        if len(payload) != verified.byte_length:
            raise RepresentationIntegrityError("object length changed during read")
        return payload


__all__ = ["SearchService"]
