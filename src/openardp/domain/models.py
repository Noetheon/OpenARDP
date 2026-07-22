"""Pure domain models for the initial OpenARDP vertical slice."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model with stable, strict serialization defaults."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class VersionState(StrEnum):
    STAGING = "STAGING"
    READY = "READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class TrustZone(StrEnum):
    LOCAL_TRUSTED = "local_trusted"
    ORGANIZATION_TRUSTED = "organization_trusted"
    EXTERNAL_UNTRUSTED = "external_untrusted"
    MODEL_DERIVED = "model_derived"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class TrustLabel(StrictModel):
    zone: TrustZone = TrustZone.EXTERNAL_UNTRUSTED
    role: str = "data"
    instruction_execution_allowed: bool = False
    integrity: str = "verified_sha256"
    sensitivity: Sensitivity = Sensitivity.UNKNOWN


class SourceDescriptor(StrictModel):
    connector: str = "local_file"
    locator: str
    media_type: str
    byte_length: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    modified_at: datetime | None = None


class ParserDescriptor(StrictModel):
    name: str
    version: str
    profile: str = "default"


class Manifest(StrictModel):
    spec_version: str = "0.1.0"
    document_id: UUID
    version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    representation_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    title: str | None = None
    state: VersionState = VersionState.READY
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: SourceDescriptor
    parser: ParserDescriptor
    schema_versions: dict[str, str] = Field(default_factory=lambda: {"block": "0.1.0"})
    extensions: dict[str, Any] = Field(default_factory=dict)


class BlockKind(StrEnum):
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


class SourceLocation(StrictModel):
    extraction_method: str
    native_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    slide: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None


class ContentBlock(StrictModel):
    block_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_id: UUID | None = None
    kind: BlockKind
    order: int = Field(ge=0)
    text: str | None = None
    structured: dict[str, Any] | list[Any] | None = None
    asset_id: str | None = None
    canonical_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source: SourceLocation
    trust: TrustLabel = Field(default_factory=TrustLabel)
    extensions: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.text is None and self.structured is None and self.asset_id is None:
            raise ValueError("A block needs text, structured content, or an asset reference")
