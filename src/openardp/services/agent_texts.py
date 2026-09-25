"""Build disposable agent texts from authoritative catalog, CAS and native artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from openardp.domain.agent_text import (
    SOURCE_TEXT_RENDERER,
    AgentPassage,
    AgentTextRecord,
    PageLabel,
    analyze_structure,
    build_passages,
    decode_source_text,
    estimate_tokens,
    page_marker,
)
from openardp.domain.evidence import PageRegionAnchor, TableCellAnchor
from openardp.domain.ingestion import (
    DocumentSummary,
    RepresentationAggregate,
    RepresentationScope,
    RepresentationState,
    RichMediaType,
    TextMediaType,
)
from openardp.domain.rich_ingestion import RichRepresentationArtifacts
from openardp.domain.storage import DocumentVersion, LogicalDocument, StoredObject
from openardp.ports.agent import AgentRenderUnavailable, AgentTextRenderer
from openardp.ports.catalog import RepresentationIntegrityError
from openardp.ports.object_store import ObjectStore, ObjectStoreError

PROJECTION_TEXT_RENDERER = "openardp-projection-text/1"

RendererFactory = Callable[[], AgentTextRenderer]


class AgentTextCatalog(Protocol):
    """Catalog reads the agent layer needs; all return committed immutable facts."""

    def list_document_summaries(self) -> tuple[DocumentSummary, ...]:
        """Return every registered document with its current head."""
        ...

    def get_document(self, document_id: UUID) -> LogicalDocument | None:
        """Return one logical document."""
        ...

    def get_version(self, document_id: UUID, version_id: str) -> DocumentVersion | None:
        """Return one exact source version."""
        ...

    def list_versions(self, document_id: UUID) -> tuple[DocumentVersion, ...]:
        """Return every retained source version of one document."""
        ...

    def resolve_ready_representation(
        self,
        document_id: UUID,
        *,
        version_id: str | None,
    ) -> RepresentationAggregate | None:
        """Return the READY representation of one version, or of the current head."""
        ...

    def load_rich_representation(
        self,
        scope: RepresentationScope,
    ) -> RichRepresentationArtifacts | None:
        """Return accepted rich artifacts for one scope, if the scope is rich."""
        ...

    def accepted_rich_native_object(self, scope: RepresentationScope) -> StoredObject | None:
        """Return the accepted provider-native object of one rich scope."""
        ...


@dataclass(frozen=True, slots=True)
class BuiltText:
    """One agent text with its record facts and retrieval passages."""

    record: AgentTextRecord
    passages: tuple[AgentPassage, ...]


def short_id(document_id: str) -> str:
    """Return the random tail of a UUIDv7 as a compact, distinctive handle."""
    return document_id.replace("-", "")[-8:]


def document_label(locator: str) -> str:
    """Return the file name shown to agents for one source locator."""
    name = PurePath(locator.replace("\\", "/")).name
    return name or locator


def media_kind(media_type: str) -> str:
    """Return the short file type used in compact listings."""
    return {
        TextMediaType.PLAIN.value: "txt",
        TextMediaType.MARKDOWN.value: "md",
        TextMediaType.CSV.value: "csv",
        RichMediaType.PDF.value: "pdf",
        RichMediaType.DOCX.value: "docx",
        RichMediaType.PPTX.value: "pptx",
    }.get(media_type, media_type)


class AgentTextBuilder:
    """Derive exact-source or rendered agent texts for prepared document versions."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: AgentTextCatalog,
        *,
        renderer_factory: RendererFactory | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Bind authoritative reads and the optional provider renderer."""
        self._object_store = object_store
        self._catalog = catalog
        self._renderer_factory = renderer_factory
        self._renderer: AgentTextRenderer | None = None
        self._renderer_failed = False
        self._clock = clock or (lambda: datetime.now(UTC))

    def ready_summaries(self) -> tuple[DocumentSummary, ...]:
        """Return summaries whose head is a READY representation."""
        return tuple(
            summary
            for summary in self._catalog.list_document_summaries()
            if summary.head is not None and summary.state is RepresentationState.READY
        )

    def all_summaries(self) -> tuple[DocumentSummary, ...]:
        """Return every registered document, prepared or not."""
        return self._catalog.list_document_summaries()

    def version(self, document_id: UUID, version_id: str) -> DocumentVersion | None:
        """Return one exact retained source version."""
        return self._catalog.get_version(document_id, version_id)

    def version_ids(self, document_id: UUID) -> tuple[str, ...]:
        """Return every retained source version identifier of one document."""
        return tuple(version.version_id for version in self._catalog.list_versions(document_id))

    def expected_renderer(self, media_type: str) -> str:
        """Return the renderer identity a fresh text for this media type would carry."""
        if media_type in {item.value for item in TextMediaType}:
            return SOURCE_TEXT_RENDERER
        renderer = self._provider_renderer()
        return renderer.renderer_id if renderer is not None else PROJECTION_TEXT_RENDERER

    def build(self, summary: DocumentSummary) -> BuiltText:
        """Build the agent text and passages of one READY document head."""
        if summary.head is None:
            raise RepresentationIntegrityError("document has no prepared head")
        scope = summary.head
        version = self._catalog.get_version(scope.document_id, scope.version_id)
        if version is None:
            raise RepresentationIntegrityError("head version is missing")
        text, renderer = self.text_for_scope(scope, version)
        return self._assemble(summary.source_key.locator, scope, version, text, renderer)

    def text_for_version(self, document_id: UUID, version_id: str) -> str | None:
        """Return the agent text of one retained version, or None when unavailable."""
        version = self._catalog.get_version(document_id, version_id)
        if version is None:
            return None
        scope = self._scope_for_version(document_id, version_id)
        if scope is None:
            return None
        try:
            return self.text_for_scope(scope, version)[0]
        except (RepresentationIntegrityError, AgentRenderUnavailable):
            return None

    def summary_for(self, document_id: str) -> DocumentSummary | None:
        """Return the READY summary of one document, if it still has one."""
        for summary in self.ready_summaries():
            if str(summary.document_id) == document_id:
                return summary
        return None

    def source_text(self, version: DocumentVersion) -> str:
        """Return the exact decoded text of one text-source version from CAS."""
        return decode_source_text(self._verified_bytes(version.source))

    def text_for_scope(
        self,
        scope: RepresentationScope,
        version: DocumentVersion,
    ) -> tuple[str, str]:
        """Return the agent text and renderer identity of one exact scope."""
        if version.media_type in {item.value for item in TextMediaType}:
            return self.source_text(version), SOURCE_TEXT_RENDERER
        renderer = self._provider_renderer()
        if renderer is not None:
            native = self._native_document(scope)
            return renderer.render(native, media_type=version.media_type), renderer.renderer_id
        artifacts = self._catalog.load_rich_representation(scope)
        if artifacts is None:
            raise RepresentationIntegrityError("rich representation is missing")
        return self._projection_text(artifacts, version.media_type), PROJECTION_TEXT_RENDERER

    def _scope_for_version(self, document_id: UUID, version_id: str) -> RepresentationScope | None:
        aggregate = self._catalog.resolve_ready_representation(document_id, version_id=version_id)
        if aggregate is None:
            return None
        return aggregate.representation.scope

    def _assemble(
        self,
        locator: str,
        scope: RepresentationScope,
        version: DocumentVersion,
        text: str,
        renderer: str,
    ) -> BuiltText:
        lines = text.split("\n") if text else []
        is_text_source = version.media_type in {item.value for item in TextMediaType}
        structure = analyze_structure(
            lines,
            markdown=version.media_type != TextMediaType.CSV.value
            and version.media_type != TextMediaType.PLAIN.value,
            pages=not is_text_source,
        )
        document_id = str(scope.document_id)
        record = AgentTextRecord(
            document_id=document_id,
            version_id=scope.version_id,
            representation_id=scope.representation_id,
            locator=locator,
            label=document_label(locator),
            media_type=version.media_type,
            renderer=renderer,
            text_sha256="sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
            token_estimate=estimate_tokens(text),
            line_count=len(lines),
            page_label=structure.page_label,
            page_count=len(structure.pages),
            heading_count=len(structure.headings),
            source_byte_length=version.source.byte_length,
            source_modified_at=version.source_modified_at,
            indexed_at=self._clock(),
            text=text,
            pages=structure.pages,
            headings=structure.headings,
        )
        passages = build_passages(
            document_id,
            lines,
            structure,
            csv=version.media_type == TextMediaType.CSV.value,
        )
        return BuiltText(record=record, passages=passages)

    def _provider_renderer(self) -> AgentTextRenderer | None:
        if self._renderer is not None or self._renderer_failed:
            return self._renderer
        if self._renderer_factory is None:
            self._renderer_failed = True
            return None
        try:
            self._renderer = self._renderer_factory()
        except AgentRenderUnavailable:
            self._renderer_failed = True
        return self._renderer

    def _projection_text(self, artifacts: RichRepresentationArtifacts, media_type: str) -> str:
        """Render provider-free text from accepted projections when no renderer exists."""
        label = PageLabel.SLIDE if media_type == RichMediaType.PPTX.value else PageLabel.PAGE
        parts: list[str] = []
        current_page: int | None = None
        tables: dict[str, dict[int, dict[int, str]]] = defaultdict(lambda: defaultdict(dict))
        for record in artifacts.bundle.records:
            projection = record.projection
            if projection.retrieval.media_type != "text/plain":
                continue
            body = self._verified_bytes(record.retrieval_object).decode("utf-8")
            anchor = projection.reference.anchor
            if isinstance(anchor, TableCellAnchor):
                tables[anchor.table.pointer][anchor.row_index][anchor.column_index] = body
                continue
            if isinstance(anchor, PageRegionAnchor) and anchor.page_number != current_page:
                current_page = anchor.page_number
                parts.append(page_marker(label, current_page))
            parts.append(body.strip())
        for pointer in sorted(tables):
            parts.append(_table_markdown(tables[pointer]))
        return "\n\n".join(part for part in parts if part)

    def _native_document(self, scope: RepresentationScope) -> dict[str, JsonValue]:
        """Load the accepted provider-native JSON, verified against catalog and CAS.

        Only the one object the text derives from is read; the catalog names it and its
        SHA-256 is rechecked, so the complete evidence bundle need not be rebuilt.
        """
        stored = self._catalog.accepted_rich_native_object(scope)
        if stored is None:
            raise RepresentationIntegrityError("accepted rich attempt is missing")
        try:
            native = json.loads(self._verified_bytes(stored))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RepresentationIntegrityError("provider native JSON is invalid") from error
        if not isinstance(native, dict):
            raise RepresentationIntegrityError("provider native JSON is not an object")
        return native

    def _verified_bytes(self, stored: StoredObject) -> bytes:
        try:
            self._object_store.verify(stored.object_id, expected_length=stored.byte_length)
            payload = b"".join(self._object_store.iter_chunks(stored.object_id))
        except ObjectStoreError as error:
            raise RepresentationIntegrityError("agent source object is invalid") from error
        if "sha256:" + hashlib.sha256(payload).hexdigest() != stored.object_id:
            raise RepresentationIntegrityError("agent source object changed")
        return payload


def _table_markdown(rows: dict[int, dict[int, str]]) -> str:
    width = max((max(cells) + 1 for cells in rows.values() if cells), default=0)
    if not width:
        return ""
    rendered: list[str] = []
    for position, row_index in enumerate(sorted(rows)):
        cells = [" ".join(rows[row_index].get(column, "").split()) for column in range(width)]
        rendered.append("| " + " | ".join(cells) + " |")
        if position == 0:
            rendered.append("|" + "---|" * width)
    return "\n".join(rendered)


__all__ = [
    "PROJECTION_TEXT_RENDERER",
    "AgentTextBuilder",
    "AgentTextCatalog",
    "BuiltText",
    "document_label",
    "media_kind",
    "short_id",
]
