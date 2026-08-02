"""Body-minimizing document status, outline and exact-block queries."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import validate_json
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import (
    DocumentRepresentation,
    DocumentStatusSnapshot,
    DocumentSummary,
    IntegrityCoverage,
    OutlineItem,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationScope,
    RepresentationState,
    SourceFreshness,
    SourceInspection,
    SourceStatus,
    StatusMode,
)
from openardp.domain.storage import LogicalDocument, SourceKey, StoredObject
from openardp.ports.catalog import (
    AmbiguousBlock,
    BlockNotFound,
    Catalog,
    CatalogError,
    DocumentNotFound,
    RepresentationIntegrityError,
    RepresentationNotFound,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError

_OUTLINE_KINDS = {
    BlockKind.TITLE,
    BlockKind.HEADING,
    BlockKind.LIST,
    BlockKind.LIST_ITEM,
}


class _InspectSource(Protocol):
    """Narrow non-publishing local-source inspection boundary."""

    @property
    def source_key(self) -> SourceKey:
        """Return the exact source identity."""
        ...

    def inspect(self, *, observed_at: datetime) -> SourceInspection:
        """Hash the current source without CAS publication or parsing."""
        ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class DocumentQueryService:
    """Navigate exact persisted evidence without search or live-source fallback."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: Catalog,
        *,
        source_factory: Callable[[Path], _InspectSource],
        representation_verifier: Callable[[RepresentationAggregate], None],
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """Bind query-only ports and the non-parsing freshness boundary."""
        self._object_store = object_store
        self._catalog = catalog
        self._source_factory = source_factory
        self._representation_verifier = representation_verifier
        self._clock = clock

    def list_documents(self) -> tuple[DocumentSummary, ...]:
        """Return deterministic current document metadata without bodies."""
        return self._catalog.list_document_summaries()

    def status(
        self,
        target: str,
        *,
        mode: StatusMode = StatusMode.HEAD,
    ) -> SourceStatus:
        """Compare exact source bytes to one current head at the requested assurance."""
        mode = StatusMode(mode)
        checked_at = self._clock()
        document, source_boundary = self._resolve_status_target(target)
        if document is None:
            return SourceStatus(
                freshness=SourceFreshness.NOT_REGISTERED,
                integrity_coverage=IntegrityCoverage.NONE,
                checked_at=checked_at,
            )
        try:
            snapshot = self._catalog.get_document_status_snapshot(document.document_id)
        except (CatalogError, ValidationError, ValueError):
            return SourceStatus(
                freshness=SourceFreshness.INTEGRITY_ERROR,
                integrity_coverage=IntegrityCoverage.NONE,
                document_id=document.document_id,
                checked_at=checked_at,
            )
        if snapshot is None:
            return SourceStatus(
                freshness=SourceFreshness.NOT_REGISTERED,
                integrity_coverage=IntegrityCoverage.NONE,
                checked_at=checked_at,
            )
        document = snapshot.document
        head = snapshot.head
        header_coverage = self._header_coverage(snapshot)
        if source_boundary is None:
            return SourceStatus(
                freshness=SourceFreshness.INTEGRITY_ERROR,
                integrity_coverage=header_coverage,
                document_id=document.document_id,
                head=head.scope if head is not None else None,
                checked_at=checked_at,
            )
        try:
            inspection = source_boundary.inspect(observed_at=checked_at)
        except FileNotFoundError:
            return SourceStatus(
                freshness=SourceFreshness.SOURCE_MISSING,
                integrity_coverage=header_coverage,
                document_id=document.document_id,
                head=head.scope if head is not None else None,
                checked_at=checked_at,
            )
        if head is None:
            return SourceStatus(
                freshness=SourceFreshness.NO_READY_REPRESENTATION,
                integrity_coverage=IntegrityCoverage.NONE,
                document_id=document.document_id,
                observed_version_id=inspection.version_id,
                checked_at=checked_at,
            )
        representation = snapshot.representation
        if representation is None or representation.state is not RepresentationState.READY:
            return SourceStatus(
                freshness=SourceFreshness.NO_READY_REPRESENTATION,
                integrity_coverage=IntegrityCoverage.NONE,
                document_id=document.document_id,
                head=head.scope,
                observed_version_id=inspection.version_id,
                checked_at=checked_at,
            )
        coverage = IntegrityCoverage.HEAD
        if mode is StatusMode.FULL:
            if not self._verify_complete_representation(representation):
                return self._integrity_error(
                    document.document_id,
                    head.scope,
                    inspection.version_id,
                    checked_at,
                )
            coverage = IntegrityCoverage.FULL
        freshness = (
            SourceFreshness.CURRENT
            if inspection.version_id == head.scope.version_id
            else SourceFreshness.SOURCE_CHANGED
        )
        return SourceStatus(
            freshness=freshness,
            integrity_coverage=coverage,
            document_id=document.document_id,
            head=head.scope,
            observed_version_id=inspection.version_id,
            checked_at=checked_at,
        )

    def _resolve_status_target(
        self,
        target: str,
    ) -> tuple[LogicalDocument | None, _InspectSource | None]:
        try:
            document_id = UUID(target)
        except ValueError:
            source = self._source_factory(Path(target))
            return self._catalog.get_document_by_source(source.source_key), source
        document = self._catalog.get_document(document_id)
        resolved_source = (
            self._source_factory(Path(document.source_key.locator))
            if document is not None and document.source_key.connector == "local"
            else None
        )
        return document, resolved_source

    def _verify_complete_representation(self, representation: DocumentRepresentation) -> bool:
        try:
            aggregate = self._catalog.load_representation(representation.scope)
        except (CatalogError, ValidationError, ValueError):
            return False
        if aggregate is None or aggregate.representation != representation:
            return False
        try:
            self._representation_verifier(aggregate)
        except (RepresentationIntegrityError, ObjectStoreError, ValidationError, ValueError):
            return False
        return True

    @staticmethod
    def _integrity_error(
        document_id: UUID,
        head: RepresentationScope,
        observed_version_id: str,
        checked_at: datetime,
    ) -> SourceStatus:
        return SourceStatus(
            freshness=SourceFreshness.INTEGRITY_ERROR,
            integrity_coverage=IntegrityCoverage.HEAD,
            document_id=document_id,
            head=head,
            observed_version_id=observed_version_id,
            checked_at=checked_at,
        )

    @staticmethod
    def _header_coverage(snapshot: DocumentStatusSnapshot) -> IntegrityCoverage:
        representation = snapshot.representation
        if representation is None or representation.state is not RepresentationState.READY:
            return IntegrityCoverage.NONE
        return IntegrityCoverage.HEAD

    def outline(
        self,
        document_id: UUID,
        *,
        version_id: str | None = None,
    ) -> tuple[OutlineItem, ...]:
        """Load only persisted structural records for one exact READY scope."""
        aggregate = self._catalog.resolve_ready_representation(
            document_id,
            version_id=version_id,
        )
        if aggregate is None:
            if self._catalog.get_document(document_id) is None:
                raise DocumentNotFound(str(document_id))
            raise RepresentationNotFound("ready representation does not exist")
        by_id = {item.block_id: item for item in aggregate.blocks}
        depths: dict[UUID, int] = {}

        def depth_for(item: RepresentationBlock) -> int:
            if item.block_id in depths:
                return depths[item.block_id]
            seen: set[UUID] = set()
            depth = 0
            current = item.parent_id
            while current is not None:
                if current in seen or current not in by_id:
                    raise RepresentationIntegrityError("outline hierarchy is inconsistent")
                seen.add(current)
                depth += 1
                current = by_id[current].parent_id
            depths[item.block_id] = depth
            return depth

        outline: list[OutlineItem] = []
        for projection in aggregate.blocks:
            if projection.kind not in _OUTLINE_KINDS:
                continue
            block = self._load_block(projection)
            label = (block.text or block.kind.value).splitlines()[0][:512]
            outline.append(
                OutlineItem(
                    block_id=block.block_id,
                    kind=block.kind,
                    parent_id=block.parent_id,
                    order=block.order,
                    depth=depth_for(projection),
                    label=label,
                    line_start=projection.line_start,
                    line_end=projection.line_end,
                )
            )
        return tuple(outline)

    def get(self, block_id: UUID) -> ContentBlock:
        """Return one unambiguous current exact block from verified CAS evidence."""
        matches = self._catalog.find_current_blocks(block_id)
        if not matches:
            raise BlockNotFound(str(block_id))
        if len(matches) > 1:
            raise AmbiguousBlock(str(block_id))
        return self._load_block(matches[0])

    def _load_block(self, projection: RepresentationBlock) -> ContentBlock:
        try:
            payload = self._read_object(projection.object)
            block = validate_json(ContentBlock, payload)
            if payload != canonical_json_bytes(block.model_dump(mode="json")):
                raise RepresentationIntegrityError("block record is non-canonical")
        except RepresentationIntegrityError:
            raise
        except (ObjectStoreError, ValidationError, ValueError) as error:
            raise RepresentationIntegrityError("block integrity failed") from error
        if (
            block.document_id != projection.scope.document_id
            or block.version_id != projection.scope.version_id
            or block.representation_id != projection.scope.representation_id
            or block.block_id != projection.block_id
            or block.parent_id != projection.parent_id
            or block.kind != projection.kind
            or block.order != projection.order
            or block.source.extensions.get("openardp.text")
            != {
                "line_start": projection.line_start,
                "line_end": projection.line_end,
            }
        ):
            raise RepresentationIntegrityError("block does not match catalog projection")
        return block

    def _read_object(self, stored: StoredObject) -> bytes:
        verified = self._object_store.verify(
            stored.object_id,
            expected_length=stored.byte_length,
        )
        payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        if len(payload) != verified.byte_length:
            raise RepresentationIntegrityError("object length changed during read")
        return payload


__all__ = ["DocumentQueryService"]
