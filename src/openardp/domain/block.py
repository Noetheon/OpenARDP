"""Canonical content block contract."""

from __future__ import annotations

from enum import StrEnum

from pydantic import JsonValue, field_validator, model_validator

from openardp.domain.common import (
    CanonicalUuid,
    DataTrustClassification,
    DocumentId,
    ExtensibleModel,
    Sha256Id,
    SourceLocator,
    SupportedSchemaVersion,
    ensure_json_value,
)
from openardp.domain.identity import block_content_hash


class BlockKind(StrEnum):
    """Normalized source-backed block categories."""

    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    CODE = "code"
    EQUATION = "equation"
    PICTURE = "picture"
    CHART = "chart"
    NOTE = "note"
    PAGE = "page"
    SLIDE = "slide"
    OTHER = "other"


class ContentBlock(ExtensibleModel):
    """One canonical content unit pinned to a source representation."""

    schema_version: SupportedSchemaVersion
    block_id: CanonicalUuid
    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id
    parent_id: CanonicalUuid | None = None
    kind: BlockKind
    order: int
    text: str | None = None
    structured: dict[str, JsonValue] | list[JsonValue] | None = None
    asset_id: Sha256Id | None = None
    canonical_hash: Sha256Id
    source: SourceLocator
    trust: DataTrustClassification

    @field_validator("order")
    @classmethod
    def _order_is_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("order must be non-negative")
        return value

    @field_validator("structured", mode="before")
    @classmethod
    def _structured_is_json_container(cls, value: object) -> object:
        if value is not None and type(value) not in (dict, list):
            raise ValueError("structured content must be a JSON object or array")
        return ensure_json_value(value, path="$.structured")

    @model_validator(mode="after")
    def _content_and_identity_are_consistent(self) -> ContentBlock:
        if self.text is None and self.structured is None and self.asset_id is None:
            raise ValueError("block requires at least one non-null content representation")
        if self.parent_id == self.block_id:
            raise ValueError("block parent_id cannot equal block_id")
        expected = block_content_hash(
            kind=self.kind.value,
            text=self.text,
            structured=self.structured,
            asset_id=self.asset_id,
        )
        if self.canonical_hash != expected:
            raise ValueError("canonical_hash does not match canonical block content")
        return self
