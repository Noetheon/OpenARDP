"""Typed directed relation contract."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, cast

from pydantic import Field, JsonValue, model_validator

from openardp.domain.common import (
    CanonicalUuid,
    DocumentId,
    ExtensibleModel,
    GenerationProvenance,
    NonEmptyStr,
    Sha256Id,
    SupportedSchemaVersion,
)
from openardp.domain.identity import relation_identity


class RelationKind(StrEnum):
    """Supported structural, provenance and semantic edge kinds."""

    CONTAINS = "contains"
    PRECEDES = "precedes"
    CAPTION_OF = "caption_of"
    SOURCE_FOR = "source_for"
    DERIVED_FROM = "derived_from"
    MENTIONS = "mentions"
    SUPERSEDES = "supersedes"
    SAME_LOGICAL_BLOCK_AS = "same_logical_block_as"


class BlockReference(ExtensibleModel):
    """Exact block reference including source and representation scope."""

    record_type: Literal["block"]
    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id
    block_id: CanonicalUuid


class ArtifactReference(ExtensibleModel):
    """Reference to a content-addressed or derivation-key artifact."""

    record_type: Literal["artifact"]
    artifact_id: Sha256Id


class DocumentVersionReference(ExtensibleModel):
    """Reference to one logical document's exact source bytes."""

    record_type: Literal["document_version"]
    document_id: DocumentId
    version_id: Sha256Id


class ExternalReference(ExtensibleModel):
    """Namespaced opaque external entity reference with no fetch authority."""

    record_type: Literal["external"]
    namespace: NonEmptyStr
    record_id: NonEmptyStr


RecordReference = Annotated[
    BlockReference | ArtifactReference | DocumentVersionReference | ExternalReference,
    Field(discriminator="record_type"),
]


class Relation(ExtensibleModel):
    """One typed directed edge with deterministic semantic identity."""

    schema_version: SupportedSchemaVersion
    relation_id: Sha256Id
    kind: RelationKind
    source: RecordReference
    target: RecordReference
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    algorithm_version: NonEmptyStr | None = None
    provenance: GenerationProvenance

    @model_validator(mode="after")
    def _endpoints_kind_and_identity_are_consistent(self) -> Relation:
        if self.source == self.target:
            raise ValueError("self relation is not allowed for supported relation kinds")

        structural = {
            RelationKind.CONTAINS,
            RelationKind.PRECEDES,
            RelationKind.CAPTION_OF,
        }
        if self.kind in structural:
            if not isinstance(self.source, BlockReference) or not isinstance(
                self.target, BlockReference
            ):
                raise ValueError("structural relation requires two block references")
            source_scope = (
                self.source.document_id,
                self.source.version_id,
                self.source.representation_id,
            )
            target_scope = (
                self.target.document_id,
                self.target.version_id,
                self.target.representation_id,
            )
            if source_scope != target_scope:
                raise ValueError(
                    "structural relation endpoints require the same "
                    "document/version/representation scope"
                )
        elif self.kind is RelationKind.SAME_LOGICAL_BLOCK_AS:
            if not isinstance(self.source, BlockReference) or not isinstance(
                self.target, BlockReference
            ):
                raise ValueError("same_logical_block_as requires two block references")
            if self.source.document_id != self.target.document_id:
                raise ValueError("same_logical_block_as requires the same logical document")
            if (
                self.source.version_id,
                self.source.representation_id,
            ) == (
                self.target.version_id,
                self.target.representation_id,
            ):
                raise ValueError("same_logical_block_as requires distinct source scopes")
            if self.confidence is None or self.algorithm_version is None:
                raise ValueError("same_logical_block_as requires confidence and algorithm_version")
        elif self.kind in {RelationKind.DERIVED_FROM, RelationKind.SOURCE_FOR} and not (
            isinstance(self.source, ArtifactReference) or isinstance(self.target, ArtifactReference)
        ):
            raise ValueError("derived_from/source_for requires at least one artifact reference")

        source_json = cast(dict[str, JsonValue], self.source.model_dump(mode="json"))
        target_json = cast(dict[str, JsonValue], self.target.model_dump(mode="json"))
        expected = relation_identity(kind=self.kind.value, source=source_json, target=target_json)
        if self.relation_id != expected:
            raise ValueError("relation_id does not match kind and directed endpoints")
        return self
