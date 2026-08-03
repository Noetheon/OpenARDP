"""Pure contracts for text ingestion, representations and document navigation."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, JsonValue, SecretStr, StringConstraints, model_validator

from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import (
    CanonicalUuid,
    DocumentId,
    DomainModel,
    NonEmptyStr,
    Sha256Id,
    SupportedSchemaVersion,
    UtcDatetime,
)
from openardp.domain.identity import canonical_json_bytes, representation_id
from openardp.domain.manifest import DocumentManifest, ManifestState
from openardp.domain.storage import LogicalDocument, MachineToken, OwnerId, SourceKey, StoredObject

MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_LINE_CHARACTERS = 1024 * 1024
MAX_NORMALIZED_BLOCKS = 100_000
DEFAULT_PARSER_TIMEOUT_SECONDS = 30.0

StructuralPathPart = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=512)]
OutlineLabel = Annotated[str, StringConstraints(strict=True, max_length=512)]


class TextMediaType(StrEnum):
    """Text media types supported by stable built-in parser adapters."""

    PLAIN = "text/plain"
    MARKDOWN = "text/markdown"
    CSV = "text/csv"


class RichMediaType(StrEnum):
    """Closed rich media allowlist supported by the F007 adapter."""

    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


SourceMediaType = TextMediaType | RichMediaType


class SourceSnapshot(DomainModel):
    """Exact immutable object and metadata from one stable local-source read."""

    source_key: SourceKey
    media_type: SourceMediaType
    object: StoredObject
    modified_at: UtcDatetime
    observed_at: UtcDatetime

    @model_validator(mode="after")
    def _source_is_local(self) -> SourceSnapshot:
        if self.source_key.connector != "local":
            raise ValueError("local source snapshot requires local connector")
        return self


class SourceInspection(DomainModel):
    """Non-publishing exact digest and metadata from one stable source read."""

    source_key: SourceKey
    media_type: SourceMediaType
    version_id: Sha256Id
    byte_length: int = Field(ge=0, le=MAX_SOURCE_BYTES)
    modified_at: UtcDatetime
    observed_at: UtcDatetime

    @model_validator(mode="after")
    def _inspection_is_local(self) -> SourceInspection:
        if self.source_key.connector != "local":
            raise ValueError("local source inspection requires local connector")
        return self


class ParserRecipe(DomainModel):
    """Exact parser and normalization recipe for one representation."""

    name: NonEmptyStr
    version: NonEmptyStr
    profile: NonEmptyStr
    config_hash: Sha256Id
    normalization_schema_version: SupportedSchemaVersion

    def representation_id_for(self, version_id: str) -> str:
        """Return the accepted ADR-0006 identity for this recipe and source."""
        return representation_id(
            version_id=version_id,
            parser_name=self.name,
            parser_version=self.version,
            parser_profile=self.profile,
            parser_config_hash=self.config_hash,
            normalization_schema_version=self.normalization_schema_version,
        )


class ParsedBlock(DomainModel):
    """Source-backed parser candidate before document-specific IDs are assigned."""

    kind: BlockKind
    text: str
    parent_index: int | None = Field(default=None, ge=0)
    order: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    structural_path: tuple[StructuralPathPart, ...]

    @model_validator(mode="after")
    def _candidate_is_source_backed(self) -> ParsedBlock:
        if self.line_end < self.line_start:
            raise ValueError("line_end must not precede line_start")
        if not self.structural_path:
            raise ValueError("structural_path must not be empty")
        if self.kind is not BlockKind.CODE and not self.text:
            raise ValueError("non-code parsed block text must not be empty")
        return self


class ParsedTextDocument(DomainModel):
    """Deterministic bounded output of one text parser invocation."""

    media_type: TextMediaType
    blocks: tuple[ParsedBlock, ...]
    warnings: tuple[MachineToken, ...]
    bom_present: bool

    @model_validator(mode="after")
    def _aggregate_is_deterministic(self) -> ParsedTextDocument:
        if len(self.blocks) > MAX_NORMALIZED_BLOCKS:
            raise ValueError("parsed document exceeds block limit")
        if self.warnings != tuple(sorted(set(self.warnings))):
            raise ValueError("warnings must be sorted and unique")
        sibling_orders: dict[int | None, list[int]] = defaultdict(list)
        for index, block in enumerate(self.blocks):
            if block.parent_index is not None and block.parent_index >= index:
                raise ValueError("parsed block parent must precede its child")
            sibling_orders[block.parent_index].append(block.order)
        for orders in sibling_orders.values():
            if tuple(orders) != tuple(range(len(orders))):
                raise ValueError("parsed block sibling orders must be contiguous")
        return self


def deterministic_block_id(
    *,
    document_id: UUID,
    structural_path: tuple[str, ...],
    kind: BlockKind,
    canonical_hash: str,
    line_start: int,
    line_end: int,
    occurrence: int,
) -> UUID:
    """Derive the documented SHA-256-based version-8 block handle."""
    if document_id.version != 7:
        raise ValueError("document_id must be UUIDv7")
    if not structural_path or any(
        not isinstance(part, str) or not part for part in structural_path
    ):
        raise ValueError("structural_path must contain non-empty strings")
    if not canonical_hash.startswith("sha256:") or len(canonical_hash) != 71:
        raise ValueError("canonical_hash must be a SHA-256 identifier")
    if line_start < 1 or line_end < line_start:
        raise ValueError("line range is invalid")
    if occurrence < 0:
        raise ValueError("occurrence must be non-negative")
    envelope: dict[str, JsonValue] = {
        "canonicalization": "RFC8785",
        "domain": "openardp:text-block-handle",
        "identity_version": 1,
        "payload": {
            "document_id": str(document_id),
            "structural_path": list(structural_path),
            "kind": kind.value,
            "canonical_hash": canonical_hash,
            "line_start": line_start,
            "line_end": line_end,
            "occurrence": occurrence,
        },
    }
    value = bytearray(hashlib.sha256(canonical_json_bytes(envelope)).digest()[:16])
    value[6] = (value[6] & 0x0F) | 0x80
    value[8] = (value[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(value))


class RepresentationScope(DomainModel):
    """Document-scoped source and parser representation identity."""

    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id


class RepresentationState(StrEnum):
    """Persisted representation lifecycle states."""

    STAGING = "STAGING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentRepresentation(DomainModel):
    """Current immutable or in-progress projection for one representation scope."""

    scope: RepresentationScope
    recipe: ParserRecipe
    state: RepresentationState
    attempt_count: int = Field(ge=1)
    revision: int = Field(ge=1)
    active_owner_id: OwnerId | None = None
    lease_expires_at: UtcDatetime | None = None
    last_failure_code: MachineToken | None = None
    manifest_object: StoredObject | None = None
    native_object: StoredObject | None = None
    block_count: int = Field(ge=0, le=MAX_NORMALIZED_BLOCKS)
    warning_codes: tuple[MachineToken, ...] = ()
    created_at: UtcDatetime
    updated_at: UtcDatetime
    ready_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _state_shape_and_recipe_are_consistent(self) -> DocumentRepresentation:
        if self.recipe.representation_id_for(self.scope.version_id) != self.scope.representation_id:
            raise ValueError("representation scope does not match parser recipe")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("warning codes must be sorted and unique")
        if self.state is RepresentationState.STAGING:
            if self.active_owner_id is None or self.lease_expires_at is None:
                raise ValueError("STAGING representation requires active owner and lease")
            if self.lease_expires_at <= self.updated_at:
                raise ValueError("STAGING lease must extend beyond updated_at")
            if (
                any(
                    value is not None
                    for value in (
                        self.last_failure_code,
                        self.manifest_object,
                        self.native_object,
                        self.ready_at,
                    )
                )
                or self.block_count != 0
            ):
                raise ValueError("STAGING representation cannot expose ready or failed data")
        elif self.state is RepresentationState.FAILED:
            if self.active_owner_id is not None or self.lease_expires_at is not None:
                raise ValueError("FAILED representation cannot retain a lease")
            if self.last_failure_code is None:
                raise ValueError("FAILED representation requires a failure code")
            if any(
                value is not None
                for value in (self.manifest_object, self.native_object, self.ready_at)
            ):
                raise ValueError("FAILED representation cannot expose ready artifacts")
            if self.block_count != 0 or self.warning_codes:
                raise ValueError(
                    "FAILED representation cannot expose normalized blocks or warnings"
                )
        else:
            if self.active_owner_id is not None or self.lease_expires_at is not None:
                raise ValueError("READY representation cannot retain a lease")
            if self.last_failure_code is not None:
                raise ValueError("READY representation cannot retain a failure")
            if self.manifest_object is None or self.native_object is None or self.ready_at is None:
                raise ValueError("READY representation requires complete artifacts and ready_at")
            if self.ready_at < self.created_at:
                raise ValueError("ready_at must not precede created_at")
        return self


class RepresentationLease(DomainModel):
    """STAGING representation plus a masked raw fencing capability."""

    representation: DocumentRepresentation
    lease_token: SecretStr

    @model_validator(mode="after")
    def _lease_is_active_and_strong(self) -> RepresentationLease:
        if self.representation.state is not RepresentationState.STAGING:
            raise ValueError("representation lease requires STAGING state")
        if len(self.lease_token.get_secret_value()) < 16:
            raise ValueError("lease token must contain at least 16 characters")
        return self


class RepresentationAcquireDisposition(StrEnum):
    """Outcome of one representation ownership attempt."""

    CLAIMED = "CLAIMED"
    READY = "READY"
    BUSY = "BUSY"


class RepresentationAcquireResult(DomainModel):
    """One unambiguous representation acquire outcome."""

    disposition: RepresentationAcquireDisposition
    representation: DocumentRepresentation
    lease: RepresentationLease | None = None

    @model_validator(mode="after")
    def _disposition_matches_shape(self) -> RepresentationAcquireResult:
        if self.disposition is RepresentationAcquireDisposition.CLAIMED:
            if self.lease is None or self.lease.representation != self.representation:
                raise ValueError("CLAIMED acquisition requires its matching lease")
        elif self.lease is not None:
            raise ValueError("READY or BUSY acquisition cannot expose a lease")
        if (
            self.disposition is RepresentationAcquireDisposition.READY
            and self.representation.state is not RepresentationState.READY
        ):
            raise ValueError("READY acquisition requires READY representation")
        if (
            self.disposition is RepresentationAcquireDisposition.BUSY
            and self.representation.state is not RepresentationState.STAGING
        ):
            raise ValueError("BUSY acquisition requires STAGING representation")
        return self


def _canonical_model_object(model: ContentBlock | DocumentManifest) -> StoredObject:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


class PreparedRepresentationBlock(DomainModel):
    """Canonical F002 block and exact CAS object requested for READY commit."""

    block: ContentBlock
    object: StoredObject
    ordinal: int = Field(ge=0, le=MAX_NORMALIZED_BLOCKS - 1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)

    @model_validator(mode="after")
    def _projection_matches_exact_block(self) -> PreparedRepresentationBlock:
        if self.line_end < self.line_start:
            raise ValueError("line_end must not precede line_start")
        details = self.block.source.extensions.get("openardp.text")
        if not isinstance(details, dict) or details != {
            "line_start": self.line_start,
            "line_end": self.line_end,
        }:
            raise ValueError("block line provenance does not match its source extension")
        if self.object != _canonical_model_object(self.block):
            raise ValueError("block object does not match canonical serialized block")
        return self


class RepresentationBlock(DomainModel):
    """Body-free persisted catalog projection for one canonical block object."""

    scope: RepresentationScope
    block_id: CanonicalUuid
    object: StoredObject
    ordinal: int = Field(ge=0, le=MAX_NORMALIZED_BLOCKS - 1)
    parent_id: CanonicalUuid | None = None
    kind: BlockKind
    order: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)

    @model_validator(mode="after")
    def _line_range_and_parent_are_valid(self) -> RepresentationBlock:
        if self.line_end < self.line_start:
            raise ValueError("line_end must not precede line_start")
        if self.parent_id == self.block_id:
            raise ValueError("block parent_id cannot equal block_id")
        return self


class ReadyRepresentationCommit(DomainModel):
    """Complete verified aggregate requested for one atomic READY commit."""

    scope: RepresentationScope
    recipe: ParserRecipe
    manifest: DocumentManifest
    manifest_object: StoredObject
    native_object: StoredObject
    blocks: tuple[PreparedRepresentationBlock, ...]
    warning_codes: tuple[MachineToken, ...]
    source_observed_at: UtcDatetime
    ready_at: UtcDatetime

    @model_validator(mode="after")
    def _aggregate_is_complete_and_scoped(self) -> ReadyRepresentationCommit:
        if self.recipe.representation_id_for(self.scope.version_id) != self.scope.representation_id:
            raise ValueError("representation scope does not match parser recipe")
        if self.ready_at < self.source_observed_at:
            raise ValueError("ready_at must not precede source observation")
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("warning codes must be sorted and unique")
        if len(self.blocks) > MAX_NORMALIZED_BLOCKS:
            raise ValueError("ready aggregate exceeds block limit")
        if self.manifest.state is not ManifestState.READY:
            raise ValueError("ready aggregate requires a READY manifest")
        if (
            self.manifest.document_id != self.scope.document_id
            or self.manifest.version_id != self.scope.version_id
            or self.manifest.representation_id != self.scope.representation_id
        ):
            raise ValueError("manifest scope does not match ready aggregate")
        if (
            self.manifest.parser.name != self.recipe.name
            or self.manifest.parser.version != self.recipe.version
            or self.manifest.parser.profile != self.recipe.profile
            or self.manifest.parser.config_hash != self.recipe.config_hash
            or self.manifest.schema_versions.block != self.recipe.normalization_schema_version
        ):
            raise ValueError("manifest parser recipe does not match ready aggregate")
        if self.manifest_object != _canonical_model_object(self.manifest):
            raise ValueError("manifest object does not match canonical serialized manifest")
        if (
            self.native_object.object_id != self.scope.version_id
            or self.native_object.byte_length != self.manifest.source.byte_length
        ):
            raise ValueError("native object must equal exact manifest source")

        ordinals = tuple(item.ordinal for item in self.blocks)
        if ordinals != tuple(range(len(self.blocks))):
            raise ValueError("block ordinals must be contiguous from zero")
        identifiers = tuple(item.block.block_id for item in self.blocks)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("block identities must be unique within a representation")
        identifier_set = set(identifiers)
        sibling_orders: dict[UUID | None, list[int]] = defaultdict(list)
        for item in self.blocks:
            block = item.block
            if (
                block.document_id != self.scope.document_id
                or block.version_id != self.scope.version_id
                or block.representation_id != self.scope.representation_id
            ):
                raise ValueError("block scope does not match ready aggregate")
            if block.parent_id is not None and block.parent_id not in identifier_set:
                raise ValueError("block parent is missing from ready aggregate")
            sibling_orders[block.parent_id].append(block.order)
        for orders in sibling_orders.values():
            if tuple(sorted(orders)) != tuple(range(len(orders))):
                raise ValueError("block sibling orders must be contiguous from zero")

        parents = {item.block.block_id: item.block.parent_id for item in self.blocks}
        for block_id in identifiers:
            seen: set[UUID] = set()
            current: UUID | None = block_id
            while current is not None:
                if current in seen:
                    raise ValueError("block hierarchy must be acyclic")
                seen.add(current)
                current = parents.get(current)
        return self


class RepresentationAggregate(DomainModel):
    """One catalog representation header with its complete block projections."""

    representation: DocumentRepresentation
    blocks: tuple[RepresentationBlock, ...]

    @model_validator(mode="after")
    def _ready_block_count_matches(self) -> RepresentationAggregate:
        if self.representation.state is RepresentationState.READY:
            if len(self.blocks) != self.representation.block_count:
                raise ValueError("ready representation block count is incomplete")
        elif self.blocks:
            raise ValueError("non-ready representation cannot expose blocks")
        return self


class IngestionDisposition(StrEnum):
    """Successful ingestion/cache classifications."""

    COMMITTED = "COMMITTED"
    CACHE_HIT = "CACHE_HIT"
    FORCED_REPARSE = "FORCED_REPARSE"
    CONVERGED = "CONVERGED"


class DocumentHead(DomainModel):
    """Mutable current successful source observation for one document."""

    scope: RepresentationScope
    source_observed_at: UtcDatetime
    last_ingested_at: UtcDatetime
    last_disposition: IngestionDisposition
    revision: int = Field(ge=1)

    @model_validator(mode="after")
    def _times_are_monotonic(self) -> DocumentHead:
        if self.last_ingested_at < self.source_observed_at:
            raise ValueError("last_ingested_at must not precede source_observed_at")
        return self


class DocumentStatusSnapshot(DomainModel):
    """One transactionally consistent document, head and header-only projection."""

    document: LogicalDocument
    head: DocumentHead | None = None
    representation: DocumentRepresentation | None = None

    @model_validator(mode="after")
    def _status_scope_is_consistent(self) -> DocumentStatusSnapshot:
        if self.head is not None and self.head.scope.document_id != self.document.document_id:
            raise ValueError("status head must match document")
        if self.representation is not None:
            if self.head is None:
                raise ValueError("status representation requires a head")
            if self.representation.scope != self.head.scope:
                raise ValueError("status representation must match head scope")
        return self


class IngestionEvent(DomainModel):
    """Append-only successful ingest evidence without document bodies."""

    document_id: DocumentId
    sequence: int = Field(ge=1)
    scope: RepresentationScope
    disposition: IngestionDisposition
    parser_invoked: bool
    head_advanced: bool
    occurred_at: UtcDatetime
    source_observed_at: UtcDatetime

    @model_validator(mode="after")
    def _event_is_truthful(self) -> IngestionEvent:
        if self.scope.document_id != self.document_id:
            raise ValueError("ingestion event scope must match document")
        if self.occurred_at < self.source_observed_at:
            raise ValueError("event time must not precede source observation")
        if (self.disposition is IngestionDisposition.CACHE_HIT) == self.parser_invoked:
            raise ValueError("cache-hit parser invocation classification is inconsistent")
        return self


class IngestionResult(DomainModel):
    """Bounded application result for one successful ingest observation."""

    scope: RepresentationScope
    disposition: IngestionDisposition
    parser_invoked: bool
    cache_hit: bool
    head_advanced: bool
    block_count: int = Field(ge=0, le=MAX_NORMALIZED_BLOCKS)
    warning_codes: tuple[MachineToken, ...]
    ingested_at: UtcDatetime

    @model_validator(mode="after")
    def _cache_flags_are_consistent(self) -> IngestionResult:
        expected_cache = self.disposition is IngestionDisposition.CACHE_HIT
        if self.cache_hit != expected_cache or self.parser_invoked == expected_cache:
            raise ValueError("cache and parser flags do not match disposition")
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("warning codes must be sorted and unique")
        return self


class SourceFreshness(StrEnum):
    """Operator-visible source and prepared-representation relationship."""

    NOT_REGISTERED = "NOT_REGISTERED"
    NO_READY_REPRESENTATION = "NO_READY_REPRESENTATION"
    CURRENT = "CURRENT"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    SOURCE_MISSING = "SOURCE_MISSING"
    INTEGRITY_ERROR = "INTEGRITY_ERROR"


class IntegrityCoverage(StrEnum):
    """Persisted-evidence assurance actually completed by one status request."""

    NONE = "NONE"
    HEAD = "HEAD"
    FULL = "FULL"


class StatusMode(StrEnum):
    """Requested persisted-evidence assurance for a source status operation."""

    HEAD = "HEAD"
    FULL = "FULL"


class DocumentSummary(DomainModel):
    """Body-free deterministic document list projection."""

    document_id: DocumentId
    source_key: SourceKey
    head: RepresentationScope | None = None
    state: RepresentationState | None = None
    block_count: int = Field(default=0, ge=0, le=MAX_NORMALIZED_BLOCKS)
    warning_count: int = Field(default=0, ge=0)
    last_ingested_at: UtcDatetime | None = None


class SourceStatus(DomainModel):
    """Body-free source freshness result obtained without parser invocation."""

    freshness: SourceFreshness
    integrity_coverage: IntegrityCoverage
    document_id: DocumentId | None = None
    head: RepresentationScope | None = None
    observed_version_id: Sha256Id | None = None
    checked_at: UtcDatetime

    @model_validator(mode="after")
    def _freshness_shape_is_consistent(self) -> SourceStatus:
        if self.freshness is SourceFreshness.NOT_REGISTERED:
            if self.document_id is not None or self.head is not None:
                raise ValueError("unregistered status cannot identify a document head")
            if self.integrity_coverage is not IntegrityCoverage.NONE:
                raise ValueError("unregistered status requires NONE integrity coverage")
        elif self.document_id is None:
            raise ValueError("registered status requires document_id")
        if self.head is not None and self.head.document_id != self.document_id:
            raise ValueError("status head must match document_id")
        if self.integrity_coverage is not IntegrityCoverage.NONE and self.head is None:
            raise ValueError("integrity coverage requires a document head")
        if (
            self.freshness is SourceFreshness.INTEGRITY_ERROR
            and self.integrity_coverage is IntegrityCoverage.FULL
        ):
            raise ValueError("failed integrity cannot claim FULL coverage")
        return self


class OutlineItem(DomainModel):
    """Bounded hierarchy handle returned before full body content."""

    block_id: CanonicalUuid
    kind: BlockKind
    parent_id: CanonicalUuid | None = None
    order: int = Field(ge=0)
    depth: int = Field(ge=0)
    label: OutlineLabel
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)

    @model_validator(mode="after")
    def _line_range_is_valid(self) -> OutlineItem:
        if self.line_end < self.line_start:
            raise ValueError("outline line_end must not precede line_start")
        return self


class RepresentationCommitResult(DomainModel):
    """Atomic ready-commit result including head/event outcome."""

    aggregate: RepresentationAggregate
    head: DocumentHead
    event: IngestionEvent


class DocumentHeadUpdate(DomainModel):
    """Result of a verified READY reuse observation."""

    head: DocumentHead
    event: IngestionEvent


__all__ = [
    "DEFAULT_PARSER_TIMEOUT_SECONDS",
    "MAX_LINE_CHARACTERS",
    "MAX_NORMALIZED_BLOCKS",
    "MAX_SOURCE_BYTES",
    "DocumentHead",
    "DocumentHeadUpdate",
    "DocumentRepresentation",
    "DocumentStatusSnapshot",
    "DocumentSummary",
    "IngestionDisposition",
    "IngestionEvent",
    "IngestionResult",
    "IntegrityCoverage",
    "OutlineItem",
    "ParsedBlock",
    "ParsedTextDocument",
    "ParserRecipe",
    "PreparedRepresentationBlock",
    "ReadyRepresentationCommit",
    "RepresentationAcquireDisposition",
    "RepresentationAcquireResult",
    "RepresentationAggregate",
    "RepresentationBlock",
    "RepresentationCommitResult",
    "RepresentationLease",
    "RepresentationScope",
    "RepresentationState",
    "SourceFreshness",
    "SourceInspection",
    "SourceSnapshot",
    "SourceStatus",
    "StatusMode",
    "TextMediaType",
    "deterministic_block_id",
]
