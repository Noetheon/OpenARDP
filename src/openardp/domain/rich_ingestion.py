"""Pure provider-neutral contracts for bounded rich-document ingestion."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import (
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from openardp.domain.common import (
    MAX_SAFE_INTEGER,
    CanonicalUuid,
    DomainModel,
    Sha256Id,
    SupportedSchemaVersion,
    UtcDatetime,
    ensure_json_value,
)
from openardp.domain.evidence import (
    EvidenceAnchor,
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    ProviderPointer,
    ProviderRecipe,
    validate_evidence_records,
)
from openardp.domain.identity import canonical_json_bytes, model_bundle_id
from openardp.domain.ingestion import (
    DocumentHead,
    IngestionDisposition,
    IngestionEvent,
    ParserRecipe,
    ReadyRepresentationCommit,
    RepresentationAggregate,
    RepresentationScope,
    RichMediaType,
)
from openardp.domain.storage import MachineToken, StoredObject

RICH_SCHEMA_VERSION = "0.1.0"
DOCLING_NATIVE_MEDIA_TYPE = "application/vnd.docling.document+json"
NATIVE_EXPORT_PROFILE = "openardp-docling-document-json-v1"
PROJECTION_PROFILE = "openardp-docling-evidence-v1"

MAX_MODEL_BUNDLE_FILES = 10_000
MAX_RICH_PAGES = 2_000
MAX_COMPONENT_VERSIONS = 128

_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MEDIA_TYPE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$"
)
_LICENSE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+():/_ -]{0,255}$")
_EXTENSION_NAMESPACE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")

BoundedComponentValue = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128),
]
BoundedProfile = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128),
]
RetrievalMediaType = Annotated[
    str,
    StringConstraints(strict=True, pattern=_MEDIA_TYPE.pattern),
]


class RichParserLimits(DomainModel):
    """Portable source, worker and output bounds for one rich parse."""

    max_source_bytes: int = Field(default=104_857_600, strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_pages: int = Field(default=500, strict=True, gt=0, le=MAX_RICH_PAGES)
    timeout_seconds: float = Field(default=120.0, strict=True, gt=0, le=3_600)
    max_address_space_bytes: int = Field(
        default=4_294_967_296,
        strict=True,
        gt=0,
        le=MAX_SAFE_INTEGER,
    )
    max_open_files: int = Field(default=64, strict=True, ge=16, le=4_096)
    max_native_bytes: int = Field(
        default=268_435_456,
        strict=True,
        gt=0,
        le=MAX_SAFE_INTEGER,
    )
    max_projections: int = Field(default=100_000, strict=True, ge=0, le=1_000_000)
    max_retrieval_body_bytes: int = Field(
        default=8_388_608,
        strict=True,
        gt=0,
        le=MAX_SAFE_INTEGER,
    )
    max_total_retrieval_bytes: int = Field(
        default=268_435_456,
        strict=True,
        gt=0,
        le=MAX_SAFE_INTEGER,
    )

    @model_validator(mode="after")
    def _aggregate_limit_contains_one_body(self) -> Self:
        if self.max_total_retrieval_bytes < self.max_retrieval_body_bytes:
            raise ValueError("aggregate retrieval limit must contain one retrieval body")
        return self


class ModelBundleFile(DomainModel):
    """One reviewed regular file addressed relative to a local model root."""

    path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]
    sha256: Sha256Id
    byte_length: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    license_id: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256)]

    @field_validator("path")
    @classmethod
    def _path_is_relative_posix(cls, value: str) -> str:
        if _CONTROL_CHARACTER.search(value) is not None or "\\" in value:
            raise ValueError("model path must be a control-free relative POSIX path")
        path = PurePosixPath(value)
        parts = value.split("/")
        if (
            path.is_absolute()
            or not parts
            or any(part in {"", ".", ".."} for part in parts)
            or path.as_posix() != value
        ):
            raise ValueError("model path must be a traversal-free relative POSIX path")
        return value

    @field_validator("license_id")
    @classmethod
    def _license_is_bounded_reviewable_text(cls, value: str) -> str:
        if _LICENSE_VALUE.fullmatch(value) is None:
            raise ValueError("license_id must be a bounded SPDX expression or license reference")
        return value


class ModelBundleManifest(DomainModel):
    """Path-independent reviewed inventory for one local Docling model bundle."""

    schema_version: SupportedSchemaVersion = RICH_SCHEMA_VERSION
    bundle_name: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]
    bundle_version: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]
    files: tuple[ModelBundleFile, ...]
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_safe_namespaced_json(cls, value: object) -> object:
        ensure_json_value(value, path="$.extensions")
        if not isinstance(value, dict):
            raise ValueError("extensions must be a JSON object")
        if any(
            not isinstance(key, str) or _EXTENSION_NAMESPACE.fullmatch(key) is None for key in value
        ):
            raise ValueError("extension keys must be absolute URI namespace identifiers")
        return value

    @model_validator(mode="after")
    def _inventory_is_bounded_sorted_and_unique(self) -> Self:
        if len(self.files) > MAX_MODEL_BUNDLE_FILES:
            raise ValueError("model bundle file inventory exceeds limit")
        paths = tuple(item.path for item in self.files)
        if len(paths) != len(set(paths)):
            raise ValueError("model bundle paths must be unique")
        if paths != tuple(sorted(paths)):
            raise ValueError("model bundle files must be sorted by path")
        return self

    @property
    def bundle_id(self) -> str:
        """Return a path-independent RFC 8785 identity for this inventory."""
        return model_bundle_id(self.model_dump(mode="json"))


class ComponentVersion(DomainModel):
    """Body-free exact provider component version fact."""

    name: BoundedComponentValue
    version: BoundedComponentValue


class RichParserRecipe(DomainModel):
    """One aligned base-representation and F006 provider recipe."""

    parser: ParserRecipe
    provider: ProviderRecipe
    native_export_profile: BoundedProfile
    projection_profile: BoundedProfile
    supported_media: tuple[RichMediaType, ...]
    limits: RichParserLimits
    model_bundle_id: Sha256Id | None = None

    @model_validator(mode="after")
    def _recipe_is_closed_and_aligned(self) -> Self:
        if (
            self.parser.name != self.provider.name
            or self.parser.version != self.provider.version
            or self.parser.profile != self.provider.profile
            or self.parser.config_hash != self.provider.config_hash
        ):
            raise ValueError("parser and provider recipes must identify the same provider")
        if self.native_export_profile != NATIVE_EXPORT_PROFILE:
            raise ValueError("unsupported native export profile")
        if self.projection_profile != PROJECTION_PROFILE:
            raise ValueError("unsupported evidence projection profile")
        if self.supported_media != tuple(RichMediaType):
            raise ValueError("supported media must equal the sorted closed F007 allowlist")
        return self


class RichEvidenceKind(StrEnum):
    """Provider-neutral evidence candidate classifications."""

    TEXT = "text"
    HEADING = "heading"
    TABLE_CELL = "table_cell"
    PICTURE = "picture"
    PAGE = "page"
    NATIVE_POINTER = "native_pointer"


class RichEvidenceCandidate(DomainModel):
    """Bounded provider-neutral evidence candidate emitted by the worker."""

    ordinal: int = Field(strict=True, ge=0, le=1_000_000)
    parent_ordinal: int | None = Field(default=None, strict=True, ge=0, le=1_000_000)
    kind: RichEvidenceKind
    anchor: EvidenceAnchor
    retrieval_media_type: RetrievalMediaType
    retrieval_text: str
    native_pointer: ProviderPointer
    warning_codes: tuple[MachineToken, ...] = ()

    @model_validator(mode="after")
    def _candidate_is_ordered_and_sanitized(self) -> Self:
        if self.parent_ordinal is not None and self.parent_ordinal >= self.ordinal:
            raise ValueError("candidate parent must precede its child")
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("candidate warning codes must be sorted and unique")
        if isinstance(self.anchor, type(None)):
            raise ValueError("candidate anchor must be present")
        return self

    @property
    def retrieval_bytes(self) -> bytes:
        """Return the exact UTF-8 retrieval representation."""
        return self.retrieval_text.encode("utf-8")


class RichParseOutput(DomainModel):
    """Strict complete provider result crossing the isolated-worker boundary."""

    media_type: RichMediaType
    native_document: dict[str, JsonValue]
    candidates: tuple[RichEvidenceCandidate, ...]
    component_versions: tuple[ComponentVersion, ...]
    warning_codes: tuple[MachineToken, ...] = ()

    @field_validator("native_document", mode="before")
    @classmethod
    def _native_document_is_safe_json(cls, value: object) -> object:
        ensure_json_value(value, path="$.native_document")
        if not isinstance(value, dict):
            raise ValueError("native_document must be a JSON object")
        return value

    @model_validator(mode="after")
    def _output_is_deterministic(self) -> Self:
        ordinals = tuple(candidate.ordinal for candidate in self.candidates)
        if ordinals != tuple(range(len(self.candidates))):
            raise ValueError("candidate ordinals must be contiguous from zero")
        versions = tuple((item.name, item.version) for item in self.component_versions)
        if versions != tuple(sorted(set(versions))):
            raise ValueError("component versions must be sorted and unique")
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("output warning codes must be sorted and unique")
        return self

    @property
    def canonical_native_bytes(self) -> bytes:
        """Return the complete provider-native document as canonical JSON."""
        return canonical_json_bytes(self.native_document)


def _canonical_object(model: DomainModel) -> StoredObject:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


class NativeArtifactDescriptor(DomainModel):
    """Immutable, body-free reproducibility metadata for one native artifact."""

    schema_version: SupportedSchemaVersion = RICH_SCHEMA_VERSION
    source_version_id: Sha256Id
    native_representation: NativeRepresentation
    provider_native_object: StoredObject
    native_media_type: RetrievalMediaType
    native_export_profile: BoundedProfile
    projection_profile: BoundedProfile
    component_versions: tuple[ComponentVersion, ...]
    model_bundle_id: Sha256Id | None = None
    created_at: UtcDatetime
    nondeterminism: tuple[MachineToken, ...] = ()

    @model_validator(mode="after")
    def _descriptor_matches_native_artifact(self) -> Self:
        native = self.native_representation
        if native.source_version_id != self.source_version_id:
            raise ValueError("descriptor source does not match native representation")
        if (
            native.native_artifact_id != self.provider_native_object.object_id
            or native.native_artifact_byte_length != self.provider_native_object.byte_length
        ):
            raise ValueError("provider native object does not match native representation")
        if (
            self.native_media_type != DOCLING_NATIVE_MEDIA_TYPE
            or native.native_artifact_media_type != self.native_media_type
        ):
            raise ValueError("native media type does not match the F007 export profile")
        if self.native_export_profile != NATIVE_EXPORT_PROFILE:
            raise ValueError("unsupported native export profile")
        if self.projection_profile != PROJECTION_PROFILE:
            raise ValueError("unsupported evidence projection profile")
        versions = tuple((item.name, item.version) for item in self.component_versions)
        if versions != tuple(sorted(set(versions))):
            raise ValueError("component versions must be sorted and unique")
        if len(versions) > MAX_COMPONENT_VERSIONS:
            raise ValueError("component version inventory exceeds limit")
        if self.nondeterminism != tuple(sorted(set(self.nondeterminism))):
            raise ValueError("nondeterminism codes must be sorted and unique")
        return self

    @property
    def canonical_bytes(self) -> bytes:
        """Return the exact canonical descriptor bytes."""
        return canonical_json_bytes(self.model_dump(mode="json"))


class RichEvidenceRecord(DomainModel):
    """Body-free persistence projection for one complete evidence item."""

    ordinal: int = Field(strict=True, ge=0, le=1_000_000)
    parent_projection_id: Sha256Id | None = None
    reference: EvidenceReference
    projection: EvidenceProjection
    reference_object: StoredObject
    projection_object: StoredObject
    retrieval_object: StoredObject

    @model_validator(mode="after")
    def _record_objects_match_embedded_records(self) -> Self:
        if self.projection.ordinal != self.ordinal:
            raise ValueError("evidence record ordinal does not match projection")
        if self.projection.parent_projection_id != self.parent_projection_id:
            raise ValueError("evidence record parent does not match projection")
        if self.projection.reference != self.reference:
            raise ValueError("evidence record reference does not match projection")
        if self.reference_object != _canonical_object(self.reference):
            raise ValueError("reference object does not match canonical reference")
        if self.projection_object != _canonical_object(self.projection):
            raise ValueError("projection object does not match canonical projection")
        if (
            self.retrieval_object.object_id != self.projection.retrieval.artifact_id
            or self.retrieval_object.byte_length != self.projection.retrieval.byte_length
        ):
            raise ValueError("retrieval object does not match projection retrieval")
        return self


class RichEvidenceBundle(DomainModel):
    """Immutable root binding a representation to its complete F006 evidence."""

    schema_version: SupportedSchemaVersion = RICH_SCHEMA_VERSION
    scope: RepresentationScope
    descriptor: NativeArtifactDescriptor
    descriptor_object: StoredObject
    native_record_object: StoredObject
    native_representation: NativeRepresentation
    references: tuple[EvidenceReference, ...]
    projections: tuple[EvidenceProjection, ...]
    records: tuple[RichEvidenceRecord, ...] = ()
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _bundle_is_complete_and_scoped(self) -> Self:
        if self.scope.version_id != self.native_representation.source_version_id:
            raise ValueError("bundle source does not match representation scope")
        if self.descriptor.source_version_id != self.scope.version_id:
            raise ValueError("descriptor source does not match bundle scope")
        if self.descriptor.native_representation != self.native_representation:
            raise ValueError("descriptor native representation does not match bundle")
        if self.descriptor_object != _canonical_object(self.descriptor):
            raise ValueError("descriptor object does not match canonical descriptor")
        if self.native_record_object != _canonical_object(self.native_representation):
            raise ValueError("native record object does not match canonical native representation")
        validate_evidence_records(
            self.native_representation,
            self.references,
            self.projections,
            expected_source_version_id=self.scope.version_id,
        )
        projection_ordinals = tuple(item.ordinal for item in self.projections)
        if projection_ordinals != tuple(range(len(self.projections))):
            raise ValueError("evidence projection ordinals must be contiguous from zero")
        if self.records:
            record_ordinals = tuple(item.ordinal for item in self.records)
            if record_ordinals != tuple(range(len(self.records))):
                raise ValueError("evidence record ordinals must be contiguous from zero")
            if tuple(item.reference for item in self.records) != self.references:
                raise ValueError("evidence records do not match bundle references")
            if tuple(item.projection for item in self.records) != self.projections:
                raise ValueError("evidence records do not match bundle projections")
        elif self.projections:
            raise ValueError("projected evidence requires complete persistence records")
        return self

    @property
    def canonical_bytes(self) -> bytes:
        """Return the exact canonical evidence-bundle bytes."""
        return canonical_json_bytes(self.model_dump(mode="json"))


class RichAttemptOutcome(StrEnum):
    """Append-only classification of a complete rich parser execution."""

    CANONICAL = "CANONICAL"
    CONVERGED = "CONVERGED"
    DIVERGED = "DIVERGED"


class RichParseAttempt(DomainModel):
    """Body-free immutable reachability root for one complete provider execution."""

    attempt_id: CanonicalUuid
    scope: RepresentationScope
    outcome: RichAttemptOutcome
    descriptor_object: StoredObject
    provider_native_object: StoredObject
    native_record_object: StoredObject
    evidence_bundle_object: StoredObject
    projection_count: int = Field(strict=True, ge=0, le=1_000_000)
    created_at: UtcDatetime

    @field_validator("attempt_id")
    @classmethod
    def _attempt_id_is_uuid7(cls, value: object) -> object:
        if getattr(value, "version", None) != 7:
            raise ValueError("attempt_id must be UUIDv7")
        return value


class RichAttemptCommit(DomainModel):
    """Complete append-only attempt and its canonical evidence bundle."""

    attempt: RichParseAttempt
    bundle: RichEvidenceBundle

    @model_validator(mode="after")
    def _attempt_matches_bundle(self) -> Self:
        if self.attempt.scope != self.bundle.scope:
            raise ValueError("attempt scope does not match evidence bundle")
        if self.attempt.descriptor_object != self.bundle.descriptor_object:
            raise ValueError("attempt descriptor does not match evidence bundle")
        if self.attempt.provider_native_object != self.bundle.descriptor.provider_native_object:
            raise ValueError("attempt native object does not match evidence bundle")
        if self.attempt.native_record_object != self.bundle.native_record_object:
            raise ValueError("attempt native record does not match evidence bundle")
        if self.attempt.evidence_bundle_object != _canonical_object(self.bundle):
            raise ValueError("attempt bundle object does not match canonical evidence bundle")
        if self.attempt.projection_count != len(self.bundle.projections):
            raise ValueError("attempt projection count does not match evidence bundle")
        return self


class ReadyRichRepresentationCommit(DomainModel):
    """Existing READY aggregate plus its first canonical rich attempt."""

    base: ReadyRepresentationCommit
    rich: RichAttemptCommit

    @model_validator(mode="after")
    def _base_and_rich_scopes_match(self) -> Self:
        if self.base.scope != self.rich.attempt.scope:
            raise ValueError("base and rich representation scopes do not match")
        if self.base.blocks:
            raise ValueError("rich representation must not fabricate F002 text blocks")
        if self.rich.attempt.outcome is not RichAttemptOutcome.CANONICAL:
            raise ValueError("initial rich commit requires a canonical attempt")
        return self


class RichRepresentationArtifacts(DomainModel):
    """One verified READY representation and its accepted rich attempt."""

    aggregate: RepresentationAggregate
    accepted_attempt_id: CanonicalUuid
    accepted_attempt: RichParseAttempt
    bundle: RichEvidenceBundle

    @model_validator(mode="after")
    def _accepted_attempt_is_complete(self) -> Self:
        if self.aggregate.representation.scope != self.accepted_attempt.scope:
            raise ValueError("accepted attempt scope does not match representation")
        if self.accepted_attempt_id != self.accepted_attempt.attempt_id:
            raise ValueError("accepted attempt identifier does not match attempt")
        if self.accepted_attempt.outcome is not RichAttemptOutcome.CANONICAL:
            raise ValueError("accepted rich attempt must be canonical")
        if self.aggregate.blocks:
            raise ValueError("rich representation cannot expose fabricated F002 blocks")
        if self.bundle.scope != self.accepted_attempt.scope:
            raise ValueError("accepted bundle scope does not match attempt")
        return self


class RichRepresentationCommitResult(DomainModel):
    """Atomic canonical-rich commit result including head and event facts."""

    artifacts: RichRepresentationArtifacts
    head: DocumentHead
    event: IngestionEvent

    @model_validator(mode="after")
    def _result_scope_is_consistent(self) -> Self:
        scope = self.artifacts.accepted_attempt.scope
        if self.head.scope != scope or self.event.scope != scope:
            raise ValueError("rich commit head and event must match accepted scope")
        return self


class RichAttemptAppendResult(DomainModel):
    """Atomic non-canonical attempt append result and its ingestion event."""

    attempt: RichParseAttempt
    accepted_attempt_id: CanonicalUuid
    event: IngestionEvent

    @model_validator(mode="after")
    def _append_result_preserves_accepted_attempt(self) -> Self:
        if self.attempt.outcome is RichAttemptOutcome.CANONICAL:
            raise ValueError("append result requires converged or diverged attempt")
        if self.attempt.attempt_id == self.accepted_attempt_id:
            raise ValueError("appended attempt cannot replace the accepted attempt")
        if self.event.scope != self.attempt.scope:
            raise ValueError("attempt event scope does not match appended attempt")
        return self


class RichIngestionResult(DomainModel):
    """Bounded body-free result for one successful rich ingestion observation."""

    scope: RepresentationScope
    disposition: IngestionDisposition
    parser_invoked: bool
    cache_hit: bool
    head_advanced: bool
    native_representation_id: Sha256Id
    native_artifact_id: Sha256Id
    evidence_count: int = Field(strict=True, ge=0, le=1_000_000)
    warning_codes: tuple[MachineToken, ...]
    attempt_id: CanonicalUuid
    accepted_attempt_id: CanonicalUuid
    attempt_outcome: RichAttemptOutcome
    ingested_at: UtcDatetime

    @model_validator(mode="after")
    def _result_flags_and_attempts_are_truthful(self) -> Self:
        expected_cache = self.disposition is IngestionDisposition.CACHE_HIT
        if self.cache_hit != expected_cache or self.parser_invoked == expected_cache:
            raise ValueError("cache and parser flags do not match disposition")
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("warning codes must be sorted and unique")
        if self.attempt_outcome is RichAttemptOutcome.CANONICAL:
            if self.attempt_id != self.accepted_attempt_id:
                raise ValueError("canonical attempt must be the accepted attempt")
        elif self.attempt_id == self.accepted_attempt_id:
            raise ValueError("non-canonical attempt cannot replace the accepted attempt")
        return self


__all__ = [
    "DOCLING_NATIVE_MEDIA_TYPE",
    "NATIVE_EXPORT_PROFILE",
    "PROJECTION_PROFILE",
    "RICH_SCHEMA_VERSION",
    "ComponentVersion",
    "ModelBundleFile",
    "ModelBundleManifest",
    "NativeArtifactDescriptor",
    "ReadyRichRepresentationCommit",
    "RichAttemptAppendResult",
    "RichAttemptCommit",
    "RichAttemptOutcome",
    "RichEvidenceBundle",
    "RichEvidenceCandidate",
    "RichEvidenceKind",
    "RichEvidenceRecord",
    "RichIngestionResult",
    "RichMediaType",
    "RichParseAttempt",
    "RichParseOutput",
    "RichParserLimits",
    "RichParserRecipe",
    "RichRepresentationArtifacts",
    "RichRepresentationCommitResult",
]
