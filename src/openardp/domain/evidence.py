"""Experimental provider-neutral native and evidence contracts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Annotated, Literal, Self

from pydantic import (
    BeforeValidator,
    Field,
    JsonValue,
    StringConstraints,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from openardp.domain.common import (
    MAX_SAFE_INTEGER,
    ContentRole,
    DomainModel,
    IntegrityState,
    Sensitivity,
    Sha256Id,
    TrustZone,
    UtcDatetime,
    ensure_json_value,
)
from openardp.domain.identity import (
    evidence_projection_id,
    evidence_reference_id,
    native_representation_id,
)

EVIDENCE_CONTRACT_VERSION = "0.1.0"
SUPPORTED_EVIDENCE_CONTRACT_VERSIONS = frozenset({EVIDENCE_CONTRACT_VERSION})
SUPPORTED_EVIDENCE_CONTRACT_MAJOR = 0
NORMALIZED_PPM_SCALE = 1_000_000

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_ABSOLUTE_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_MEDIA_TYPE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$"
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _validate_contract_version(value: object) -> object:
    if not isinstance(value, str) or _SEMVER.fullmatch(value) is None:
        raise ValueError("contract version must be semantic version MAJOR.MINOR.PATCH")
    major = int(value.split(".", maxsplit=1)[0])
    if major != SUPPORTED_EVIDENCE_CONTRACT_MAJOR:
        raise ValueError(
            "unsupported contract major "
            f"{major}; supported major: {SUPPORTED_EVIDENCE_CONTRACT_MAJOR}"
        )
    if value not in SUPPORTED_EVIDENCE_CONTRACT_VERSIONS:
        installed = ", ".join(sorted(SUPPORTED_EVIDENCE_CONTRACT_VERSIONS))
        raise ValueError(f"contract version {value} is not installed; supported: {installed}")
    return value


def _validate_semver(value: object) -> object:
    if not isinstance(value, str) or _SEMVER.fullmatch(value) is None:
        raise ValueError("value must be semantic version MAJOR.MINOR.PATCH")
    return value


EvidenceContractVersion = Annotated[
    str,
    BeforeValidator(_validate_contract_version),
    StringConstraints(strict=True),
    WithJsonSchema(
        {"type": "string", "const": EVIDENCE_CONTRACT_VERSION},
        mode="validation",
    ),
]
SemanticVersion = Annotated[
    str,
    BeforeValidator(_validate_semver),
    StringConstraints(strict=True),
    WithJsonSchema(
        {"type": "string", "pattern": _SEMVER.pattern},
        mode="validation",
    ),
]
MediaType = Annotated[
    str,
    StringConstraints(strict=True, pattern=_MEDIA_TYPE.pattern),
]
ExtensionNamespace = Annotated[
    str,
    StringConstraints(strict=True, pattern=_ABSOLUTE_URI.pattern),
]
BoundedName = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128),
]
BoundedVersion = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128),
]
SafeNonNegativeInt = Annotated[int, Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)]


class EvidenceContractModel(DomainModel):
    """Closed root metadata shared by the experimental evidence family."""

    contract_version: EvidenceContractVersion = EVIDENCE_CONTRACT_VERSION
    stability: Literal["experimental"] = "experimental"
    extensions: dict[ExtensionNamespace, JsonValue] = Field(
        default_factory=dict,
        json_schema_extra={"additionalProperties": False},
    )

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_namespaced_json(cls, value: object) -> object:
        ensure_json_value(value, path="$.extensions")
        if not isinstance(value, dict):
            raise ValueError("extensions must be a JSON object")
        for key in value:
            if _ABSOLUTE_URI.fullmatch(key) is None:
                raise ValueError("extension keys must be absolute URI namespace identifiers")
        return value


class ProviderRecipe(DomainModel):
    """Provider recipe that generated a retained native artifact."""

    name: BoundedName
    version: BoundedVersion
    profile: BoundedName
    profile_version: SemanticVersion
    config_hash: Sha256Id


class ProviderPointer(DomainModel):
    """Opaque pointer whose meaning is scoped to one provider profile."""

    provider_profile: BoundedName
    provider_profile_version: SemanticVersion
    pointer_format: BoundedName
    pointer: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=2048)]

    @field_validator("pointer")
    @classmethod
    def _pointer_has_no_controls(cls, value: str) -> str:
        if _CONTROL_CHARACTER.search(value) is not None:
            raise ValueError("provider pointer must not contain control characters")
        return value


class TextSpanAnchor(DomainModel):
    """Half-open code-point offsets in a provider-profile text view."""

    anchor_type: Literal["text_span"]
    coordinate_system: Literal["unicode_code_points"]
    start: SafeNonNegativeInt
    end: SafeNonNegativeInt
    text_length: SafeNonNegativeInt | None = None

    @model_validator(mode="after")
    def _span_is_non_empty_and_bounded(self) -> Self:
        if self.end <= self.start:
            raise ValueError("text span requires end greater than start")
        if self.text_length is not None and self.end > self.text_length:
            raise ValueError("text span exceeds declared text_length")
        return self


class PageRegionAnchor(DomainModel):
    """Exact fixed-point normalized rectangle on a one-based page."""

    anchor_type: Literal["page_region"]
    coordinate_system: Literal["normalized_ppm_top_left"]
    page_number: int = Field(strict=True, ge=1, le=MAX_SAFE_INTEGER)
    x: int = Field(strict=True, ge=0, lt=NORMALIZED_PPM_SCALE)
    y: int = Field(strict=True, ge=0, lt=NORMALIZED_PPM_SCALE)
    width: int = Field(strict=True, gt=0, le=NORMALIZED_PPM_SCALE)
    height: int = Field(strict=True, gt=0, le=NORMALIZED_PPM_SCALE)

    @model_validator(mode="after")
    def _rectangle_fits_page(self) -> Self:
        if self.x + self.width > NORMALIZED_PPM_SCALE:
            raise ValueError("page region exceeds horizontal page bounds")
        if self.y + self.height > NORMALIZED_PPM_SCALE:
            raise ValueError("page region exceeds vertical page bounds")
        return self


class TableCellAnchor(DomainModel):
    """Zero-based table cell scoped to an opaque native table pointer."""

    anchor_type: Literal["table_cell"]
    table: ProviderPointer
    row_index: SafeNonNegativeInt
    column_index: SafeNonNegativeInt
    row_span: int = Field(default=1, strict=True, ge=1, le=MAX_SAFE_INTEGER)
    column_span: int = Field(default=1, strict=True, ge=1, le=MAX_SAFE_INTEGER)

    @model_validator(mode="after")
    def _cell_arithmetic_is_interoperable(self) -> Self:
        if self.row_index + self.row_span > MAX_SAFE_INTEGER:
            raise ValueError("table row index and span exceed the safe integer range")
        if self.column_index + self.column_span > MAX_SAFE_INTEGER:
            raise ValueError("table column index and span exceed the safe integer range")
        return self


class OpaqueProviderPointerAnchor(DomainModel):
    """Provider-specific target that the neutral core never interprets."""

    anchor_type: Literal["provider_pointer"]
    target: ProviderPointer


EvidenceAnchor = Annotated[
    TextSpanAnchor | PageRegionAnchor | TableCellAnchor | OpaqueProviderPointerAnchor,
    Field(discriminator="anchor_type"),
]


class NativeRepresentation(EvidenceContractModel):
    """Immutable metadata for one complete retained provider-native artifact."""

    native_representation_id: Sha256Id
    source_version_id: Sha256Id
    native_artifact_id: Sha256Id
    native_artifact_media_type: MediaType
    native_artifact_byte_length: SafeNonNegativeInt
    provider: ProviderRecipe
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _declared_identity_matches(self) -> Self:
        expected = native_representation_id(
            source_version_id=self.source_version_id,
            native_artifact_id=self.native_artifact_id,
            native_artifact_media_type=self.native_artifact_media_type,
            provider_name=self.provider.name,
            provider_version=self.provider.version,
            provider_profile=self.provider.profile,
            provider_profile_version=self.provider.profile_version,
            provider_config_hash=self.provider.config_hash,
        )
        if self.native_representation_id != expected:
            raise ValueError("native_representation_id does not match canonical identity")
        return self


class EvidenceReference(EvidenceContractModel):
    """One source/native-bound provider-neutral evidence anchor."""

    evidence_reference_id: Sha256Id
    source_version_id: Sha256Id
    native_representation_id: Sha256Id
    anchor: EvidenceAnchor

    @model_validator(mode="after")
    def _declared_identity_matches(self) -> Self:
        anchor = self.anchor.model_dump(mode="json")
        expected = evidence_reference_id(
            source_version_id=self.source_version_id,
            native_representation_id=self.native_representation_id,
            anchor=anchor,
        )
        if self.evidence_reference_id != expected:
            raise ValueError("evidence_reference_id does not match canonical identity")
        return self


_TRUST_RANK = {
    TrustZone.EXTERNAL_UNTRUSTED: 0,
    TrustZone.ORGANIZATION_TRUSTED: 1,
    TrustZone.LOCAL_TRUSTED: 2,
}


class TrustClassification(EvidenceContractModel):
    """Data-only trust state that rejects evidence authority promotion."""

    origin_zone: TrustZone
    effective_zone: TrustZone
    role: Literal[ContentRole.DATA]
    instruction_execution_allowed: Literal[False] = False
    integrity: IntegrityState
    sensitivity: Sensitivity

    @model_validator(mode="after")
    def _effective_zone_does_not_promote(self) -> Self:
        if self.origin_zone is TrustZone.MODEL_DERIVED:
            if self.effective_zone is not TrustZone.MODEL_DERIVED:
                raise ValueError("trust promotion from model_derived is prohibited")
            return self
        if self.effective_zone is TrustZone.MODEL_DERIVED:
            return self
        if _TRUST_RANK[self.effective_zone] > _TRUST_RANK[self.origin_zone]:
            raise ValueError("trust promotion is prohibited")
        return self


class RetrievalHandle(DomainModel):
    """Content-addressed retrieval material without an access path."""

    artifact_id: Sha256Id
    media_type: MediaType
    byte_length: SafeNonNegativeInt


class ProjectionProvenance(DomainModel):
    """Projection recipe and immutable creation time."""

    generator_name: BoundedName
    generator_version: BoundedVersion
    generator_config_hash: Sha256Id
    created_at: UtcDatetime


class EvidenceProjection(EvidenceContractModel):
    """Thin identity, navigation, retrieval, trust, and lifecycle projection."""

    evidence_projection_id: Sha256Id
    source_version_id: Sha256Id
    native_representation_id: Sha256Id
    reference: EvidenceReference
    retrieval: RetrievalHandle
    parent_projection_id: Sha256Id | None = None
    ordinal: SafeNonNegativeInt
    trust: TrustClassification
    provenance: ProjectionProvenance

    @model_validator(mode="after")
    def _scope_and_identity_match(self) -> Self:
        if self.reference.source_version_id != self.source_version_id:
            raise ValueError("projection reference source does not match projection source")
        if self.reference.native_representation_id != self.native_representation_id:
            raise ValueError("projection reference native representation does not match projection")
        expected = evidence_projection_id(
            source_version_id=self.source_version_id,
            native_representation_id=self.native_representation_id,
            evidence_reference_id=self.reference.evidence_reference_id,
            retrieval_artifact_id=self.retrieval.artifact_id,
            retrieval_media_type=self.retrieval.media_type,
            parent_projection_id=self.parent_projection_id,
            ordinal=self.ordinal,
            generator_name=self.provenance.generator_name,
            generator_version=self.provenance.generator_version,
            generator_config_hash=self.provenance.generator_config_hash,
        )
        if self.evidence_projection_id != expected:
            raise ValueError("evidence_projection_id does not match canonical identity")
        return self


def _reject_semantic_collisions[RecordT: DomainModel](
    records: Sequence[RecordT],
    *,
    identifier: str,
) -> None:
    observed: dict[str, dict[str, object]] = {}
    for record in records:
        record_id = getattr(record, identifier)
        if not isinstance(record_id, str):
            raise TypeError(f"{identifier} must be a string")
        payload = record.model_dump(mode="json")
        previous = observed.setdefault(record_id, payload)
        if previous != payload:
            raise ValueError(f"duplicate {identifier} has non-identical records")


def validate_evidence_records(
    native: NativeRepresentation,
    references: Sequence[EvidenceReference],
    projections: Sequence[EvidenceProjection],
    *,
    expected_source_version_id: str | None = None,
) -> None:
    """Validate one native artifact and its source-bound evidence records without I/O."""
    if (
        expected_source_version_id is not None
        and native.source_version_id != expected_source_version_id
    ):
        raise ValueError("native record does not match expected source version")

    for reference in references:
        if reference.source_version_id != native.source_version_id:
            raise ValueError("evidence reference does not match native source version")
        if reference.native_representation_id != native.native_representation_id:
            raise ValueError("evidence reference does not match native representation")
        if (
            expected_source_version_id is not None
            and reference.source_version_id != expected_source_version_id
        ):
            raise ValueError("evidence reference does not match expected source version")

    reference_records = {record.evidence_reference_id: record for record in references}
    for projection in projections:
        if projection.source_version_id != native.source_version_id:
            raise ValueError("evidence projection does not match native source version")
        if projection.native_representation_id != native.native_representation_id:
            raise ValueError("evidence projection does not match native representation")
        if projection.reference.evidence_reference_id not in reference_records:
            raise ValueError("evidence projection reference is absent from record set")
        if (
            expected_source_version_id is not None
            and projection.source_version_id != expected_source_version_id
        ):
            raise ValueError("evidence projection does not match expected source version")

    _reject_semantic_collisions(references, identifier="evidence_reference_id")
    _reject_semantic_collisions(projections, identifier="evidence_projection_id")
