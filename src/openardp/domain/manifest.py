"""Canonical document manifest contract."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from openardp.domain.common import (
    DocumentId,
    DomainModel,
    ExtensibleModel,
    NonEmptyStr,
    ParserDescriptor,
    Sha256Hex,
    Sha256Id,
    SupportedSchemaVersion,
    UtcDatetime,
)
from openardp.domain.identity import representation_id


class ManifestState(StrEnum):
    """Lifecycle state recorded for a document representation."""

    STAGING = "STAGING"
    READY = "READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class SourceDescriptor(ExtensibleModel):
    """Immutable source facts carried by a manifest."""

    connector: NonEmptyStr
    locator: NonEmptyStr
    media_type: NonEmptyStr
    byte_length: int = Field(ge=0)
    sha256: Sha256Hex
    modified_at: UtcDatetime | None = None


class SchemaVersions(DomainModel):
    """Installed representation-record schema releases."""

    block: SupportedSchemaVersion
    derivation: SupportedSchemaVersion
    relation: SupportedSchemaVersion


class DocumentManifest(ExtensibleModel):
    """One logical document's exact source and representation revision."""

    spec_version: SupportedSchemaVersion
    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id
    title: str | None = None
    state: ManifestState
    created_at: UtcDatetime
    source: SourceDescriptor
    parser: ParserDescriptor
    schema_versions: SchemaVersions

    @model_validator(mode="after")
    def _identities_match_declared_source_and_recipe(self) -> DocumentManifest:
        expected_version = f"sha256:{self.source.sha256}"
        if self.version_id != expected_version:
            raise ValueError("version_id must equal sha256: plus source.sha256")
        expected_representation = representation_id(
            version_id=self.version_id,
            parser_name=self.parser.name,
            parser_version=self.parser.version,
            parser_profile=self.parser.profile,
            parser_config_hash=self.parser.config_hash,
            normalization_schema_version=self.schema_versions.block,
        )
        if self.representation_id != expected_representation:
            raise ValueError("representation_id does not match the declared processing recipe")
        return self
