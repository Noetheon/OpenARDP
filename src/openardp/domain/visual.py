"""Pure contracts and integer geometry for exact visual evidence."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, StringConstraints, field_validator, model_validator

from openardp.domain.common import (
    MAX_SAFE_INTEGER,
    ComponentDescriptor,
    DocumentId,
    DomainModel,
    Sha256Id,
    UtcDatetime,
    ensure_json_value,
)
from openardp.domain.evidence import (
    EvidenceAnchor,
    EvidenceContractVersion,
    OpaqueProviderPointerAnchor,
    PageRegionAnchor,
    ProviderPointer,
    ProviderRecipe,
    TableCellAnchor,
    TextSpanAnchor,
    TrustClassification,
)
from openardp.domain.identity import (
    canonical_json_bytes,
    canonical_sha256,
    visual_evidence_id,
    visual_raster_id,
)
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.storage import MachineToken, StoredObject

VISUAL_CONTRACT_VERSION = "0.1.0"
VISUAL_IDENTITY_VERSION: Literal[1] = 1
NORMALIZED_PPM_SCALE = 1_000_000
CANONICAL_ASPECT_ERROR_PPM = 1_000

_ABSOLUTE_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_LICENSE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+():/_ -]{0,255}$")

Rotation = Literal[0, 90, 180, 270]
Rgb = tuple[
    Annotated[int, Field(strict=True, ge=0, le=255)],
    Annotated[int, Field(strict=True, ge=0, le=255)],
    Annotated[int, Field(strict=True, ge=0, le=255)],
]


class VisualContractModel(DomainModel):
    """Closed experimental visual root metadata with inert URI extensions."""

    contract_version: EvidenceContractVersion = VISUAL_CONTRACT_VERSION
    stability: Literal["experimental"] = "experimental"
    identity_version: Literal[1] = VISUAL_IDENTITY_VERSION
    extensions: dict[
        Annotated[str, StringConstraints(strict=True, pattern=_ABSOLUTE_URI.pattern)],
        JsonValue,
    ] = Field(default_factory=dict, json_schema_extra={"additionalProperties": False})

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_namespaced_json(cls, value: object) -> object:
        ensure_json_value(value, path="$.extensions")
        if not isinstance(value, dict):
            raise ValueError("extensions must be a JSON object")
        return value


class VisualGranularity(StrEnum):
    """Truthful precision of one resolved visual region."""

    PAGE_EXACT = "page_exact"
    REGION_EXACT = "region_exact"
    CELL_EXACT = "cell_exact"
    TABLE_FALLBACK = "table_fallback"


class VisualUsageScope(StrEnum):
    """Trusted effective use boundary for one visual artifact."""

    LOCAL_ONLY = "local_only"
    EXPORT_ALLOWED = "export_allowed"


class VisualRenderLimits(DomainModel):
    """Independent hard bounds for rendering, decoding and IPC output."""

    max_encoded_bytes: int = Field(default=104_857_600, strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_pages: int = Field(default=2_000, strict=True, gt=0, le=10_000)
    max_page_dimension: int = Field(default=20_000, strict=True, gt=0, le=100_000)
    max_page_pixels: int = Field(default=100_000_000, strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_crop_dimension: int = Field(default=10_000, strict=True, gt=0, le=100_000)
    max_crop_pixels: int = Field(default=25_000_000, strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_decoded_bytes: int = Field(default=300_000_000, strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_output_bytes: int = Field(default=104_857_600, strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_metadata_bytes: int = Field(default=65_536, strict=True, ge=0, le=MAX_SAFE_INTEGER)
    max_frames: Literal[1] = 1
    timeout_seconds: float = Field(default=120.0, strict=True, gt=0, le=3_600)
    max_address_space_bytes: int = Field(
        default=4_294_967_296,
        strict=True,
        gt=0,
        le=MAX_SAFE_INTEGER,
    )
    max_open_files: int = Field(default=64, strict=True, ge=16, le=4_096)

    @model_validator(mode="after")
    def _limits_are_coherent(self) -> Self:
        if self.max_crop_dimension > self.max_page_dimension:
            raise ValueError("crop dimension cannot exceed page dimension")
        if self.max_crop_pixels > self.max_page_pixels:
            raise ValueError("crop pixels cannot exceed page pixels")
        if self.max_decoded_bytes < self.max_page_pixels * 3:
            raise ValueError("decoded byte limit must contain one RGB page")
        return self


def _json_value(value: object) -> JsonValue:
    if isinstance(value, DomainModel):
        return value.model_dump(mode="json")
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    ensure_json_value(value)
    return value  # type: ignore[return-value]


def visual_render_config_hash(values: Mapping[str, object]) -> str:
    """Hash every output- or admission-affecting render recipe field."""
    payload = {key: _json_value(value) for key, value in values.items() if key != "config_hash"}
    return canonical_sha256(payload)


class VisualRenderRecipe(DomainModel):
    """Complete deterministic page-render and crop-encoding profile."""

    renderer: ComponentDescriptor
    encoder: ComponentDescriptor
    scale_numerator: int = Field(strict=True, gt=0, le=10_000)
    scale_denominator: int = Field(strict=True, gt=0, le=10_000)
    color_mode: Literal["RGB"] = "RGB"
    background_rgb: Rgb = (255, 255, 255)
    draw_annotations: Literal[False] = False
    draw_forms: Literal[False] = False
    metadata_policy: Literal["strip"] = "strip"
    max_page_aspect_error_ppm: Literal[1000] = 1000
    limits: VisualRenderLimits
    config_hash: Sha256Id

    @model_validator(mode="after")
    def _config_hash_matches(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"config_hash"})
        if self.config_hash != visual_render_config_hash(payload):
            raise ValueError("config_hash does not match render recipe")
        return self


class VisualUsagePolicy(DomainModel):
    """Trusted effective local/export policy independent of document metadata."""

    scope: VisualUsageScope
    export_allowed: bool
    license_id: (
        Annotated[
            str,
            StringConstraints(strict=True, min_length=1, max_length=256),
        ]
        | None
    ) = None
    restriction_codes: tuple[MachineToken, ...]
    policy_provider: ComponentDescriptor
    policy_config_hash: Sha256Id

    @field_validator("license_id")
    @classmethod
    def _license_is_bounded_reviewable_text(cls, value: str | None) -> str | None:
        if value is not None and _LICENSE_VALUE.fullmatch(value) is None:
            raise ValueError("license_id must be a bounded reviewed license expression")
        return value

    @model_validator(mode="after")
    def _scope_and_restrictions_are_consistent(self) -> Self:
        if self.restriction_codes != tuple(sorted(set(self.restriction_codes))):
            raise ValueError("restriction codes must be sorted and unique")
        if self.export_allowed != (self.scope is VisualUsageScope.EXPORT_ALLOWED):
            raise ValueError("export flag does not match usage scope")
        if self.scope is VisualUsageScope.LOCAL_ONLY and not self.restriction_codes:
            raise ValueError("local-only policy requires a restriction code")
        return self


def pixel_bounds(
    region: PageRegionAnchor,
    *,
    raster_width: int,
    raster_height: int,
) -> tuple[int, int, int, int]:
    """Map normalized PPM to strict half-open pixels using integer floor/ceiling."""
    if raster_width <= 0 or raster_height <= 0:
        raise ValueError("raster dimensions must be positive")
    left = region.x * raster_width // NORMALIZED_PPM_SCALE
    top = region.y * raster_height // NORMALIZED_PPM_SCALE
    right_numerator = (region.x + region.width) * raster_width
    bottom_numerator = (region.y + region.height) * raster_height
    right = (right_numerator + NORMALIZED_PPM_SCALE - 1) // NORMALIZED_PPM_SCALE
    bottom = (bottom_numerator + NORMALIZED_PPM_SCALE - 1) // NORMALIZED_PPM_SCALE
    if not (0 <= left < right <= raster_width and 0 <= top < bottom <= raster_height):
        raise ValueError("pixel bounds are outside the raster")
    return left, top, right, bottom


def _rotated_dimensions(width: int, height: int, rotation: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ValueError("dimensions must be positive")
    if rotation not in {0, 90, 180, 270}:
        raise ValueError("rotation must be 0, 90, 180 or 270")
    return (height, width) if rotation in {90, 270} else (width, height)


def aspect_error_ppm(
    *,
    source_width: int,
    source_height: int,
    source_rotation: int,
    raster_width: int,
    raster_height: int,
    applied_rotation: int,
) -> int:
    """Return ceiling relative aspect error in PPM after declared rotations."""
    source_w, source_h = _rotated_dimensions(
        source_width,
        source_height,
        source_rotation,
    )
    raster_w, raster_h = _rotated_dimensions(
        raster_width,
        raster_height,
        applied_rotation,
    )
    source_cross = source_w * raster_h
    raster_cross = raster_w * source_h
    denominator = max(source_cross, raster_cross)
    difference = abs(source_cross - raster_cross)
    return (difference * NORMALIZED_PPM_SCALE + denominator - 1) // denominator


class ResolvedVisualRegion(DomainModel):
    """Exact page crop plus truthful table-cell granularity."""

    page_region: PageRegionAnchor
    granularity: VisualGranularity
    table_cell: TableCellAnchor | None = None
    provider_pointer: ProviderPointer | None = None
    cell_geometry_explicit: bool = False
    warning_codes: tuple[MachineToken, ...] = ()

    @model_validator(mode="after")
    def _granularity_is_truthful(self) -> Self:
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("warning codes must be sorted and unique")
        table_granularity = self.granularity in {
            VisualGranularity.CELL_EXACT,
            VisualGranularity.TABLE_FALLBACK,
        }
        if table_granularity != (self.table_cell is not None):
            raise ValueError("table granularity requires exactly one table cell")
        if self.granularity is VisualGranularity.CELL_EXACT and not self.cell_geometry_explicit:
            raise ValueError("cell geometry must be explicit for cell_exact")
        if self.granularity is VisualGranularity.TABLE_FALLBACK:
            if "table_geometry_fallback" not in self.warning_codes:
                raise ValueError("table fallback requires the fallback warning")
            if self.cell_geometry_explicit:
                raise ValueError("table fallback cannot claim explicit cell geometry")
        elif "table_geometry_fallback" in self.warning_codes:
            raise ValueError("fallback warning is valid only for table fallback")
        if self.granularity is VisualGranularity.PAGE_EXACT and self.page_region.model_dump() != {
            "anchor_type": "page_region",
            "coordinate_system": "normalized_ppm_top_left",
            "page_number": self.page_region.page_number,
            "x": 0,
            "y": 0,
            "width": NORMALIZED_PPM_SCALE,
            "height": NORMALIZED_PPM_SCALE,
        }:
            raise ValueError("page_exact requires the full page region")
        return self


class VisualPageRaster(DomainModel):
    """One deterministic registered full-page RGB PNG derived from exact source bytes."""

    raster_id: Sha256Id
    scope: RepresentationScope
    source_object: StoredObject
    native_representation_id: Sha256Id
    page_number: int = Field(strict=True, ge=1, le=10_000)
    source_width: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    source_height: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    source_rotation: Rotation
    applied_rotation: Rotation
    pixel_width: int = Field(strict=True, gt=0, le=100_000)
    pixel_height: int = Field(strict=True, gt=0, le=100_000)
    media_type: Literal["image/png"] = "image/png"
    color_mode: Literal["RGB"] = "RGB"
    raster_object: StoredObject
    recipe: VisualRenderRecipe
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _scope_recipe_and_identity_match(self) -> Self:
        if self.source_object.object_id != self.scope.version_id:
            raise ValueError("raster source object does not match scope source")
        if self.pixel_width > self.recipe.limits.max_page_dimension:
            raise ValueError("raster width exceeds render limits")
        if self.pixel_height > self.recipe.limits.max_page_dimension:
            raise ValueError("raster height exceeds render limits")
        if self.pixel_width * self.pixel_height > self.recipe.limits.max_page_pixels:
            raise ValueError("raster pixels exceed render limits")
        expected = visual_raster_id(
            source_version_id=self.scope.version_id,
            representation_id=self.scope.representation_id,
            native_representation_id=self.native_representation_id,
            page_number=self.page_number,
            recipe=self.recipe.model_dump(mode="json"),
        )
        if self.raster_id != expected:
            raise ValueError("raster_id does not match exact page render recipe")
        return self


class VisualPixelTransform(DomainModel):
    """Auditable exact mapping from normalized page coordinates to display pixels."""

    normalized_region: PageRegionAnchor
    source_width: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    source_height: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    source_rotation: Rotation
    applied_rotation: Rotation
    scale_numerator: int = Field(strict=True, gt=0, le=10_000)
    scale_denominator: int = Field(strict=True, gt=0, le=10_000)
    raster_width: int = Field(strict=True, gt=0, le=100_000)
    raster_height: int = Field(strict=True, gt=0, le=100_000)
    left: int = Field(strict=True, ge=0, le=100_000)
    top: int = Field(strict=True, ge=0, le=100_000)
    right: int = Field(strict=True, gt=0, le=100_000)
    bottom: int = Field(strict=True, gt=0, le=100_000)
    aspect_error_ppm: int = Field(strict=True, ge=0, le=NORMALIZED_PPM_SCALE)
    max_aspect_error_ppm: Literal[1000] = 1000

    @model_validator(mode="after")
    def _mapping_and_aspect_are_exact(self) -> Self:
        expected_bounds = pixel_bounds(
            self.normalized_region,
            raster_width=self.raster_width,
            raster_height=self.raster_height,
        )
        if (self.left, self.top, self.right, self.bottom) != expected_bounds:
            raise ValueError("pixel transform bounds do not match normalized region")
        expected_error = aspect_error_ppm(
            source_width=self.source_width,
            source_height=self.source_height,
            source_rotation=self.source_rotation,
            raster_width=self.raster_width,
            raster_height=self.raster_height,
            applied_rotation=self.applied_rotation,
        )
        if self.aspect_error_ppm != expected_error:
            raise ValueError("aspect error does not match declared dimensions")
        if self.aspect_error_ppm > self.max_aspect_error_ppm:
            raise ValueError("page geometry mismatch exceeds aspect admission bound")
        return self


class VisualEvidenceDescriptor(VisualContractModel):
    """Thin immutable visual evidence root for one accepted F006 projection."""

    visual_evidence_id: Sha256Id
    document_id: DocumentId
    source_version_id: Sha256Id
    representation_id: Sha256Id
    native_representation_id: Sha256Id
    evidence_reference_id: Sha256Id
    evidence_projection_id: Sha256Id
    target_anchor: EvidenceAnchor
    resolved_region: ResolvedVisualRegion
    page_raster: VisualPageRaster
    transform: VisualPixelTransform
    crop_object: StoredObject
    crop_media_type: Literal["image/png"] = "image/png"
    crop_width: int = Field(strict=True, gt=0, le=100_000)
    crop_height: int = Field(strict=True, gt=0, le=100_000)
    color_mode: Literal["RGB"] = "RGB"
    recipe: VisualRenderRecipe
    trust: TrustClassification
    usage_policy: VisualUsagePolicy
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _scope_geometry_objects_and_identity_match(self) -> Self:
        scope = self.page_raster.scope
        if (
            self.document_id != scope.document_id
            or self.source_version_id != scope.version_id
            or self.representation_id != scope.representation_id
            or self.native_representation_id != self.page_raster.native_representation_id
        ):
            raise ValueError("visual descriptor source scope does not match page raster")
        if self.resolved_region.page_region != self.transform.normalized_region:
            raise ValueError("visual resolved region does not match pixel transform")
        if self.resolved_region.page_region.page_number != self.page_raster.page_number:
            raise ValueError("visual page does not match page raster")
        if isinstance(self.target_anchor, TableCellAnchor):
            if self.resolved_region.table_cell != self.target_anchor:
                raise ValueError("visual table target does not match resolved cell")
        elif isinstance(self.target_anchor, PageRegionAnchor):
            if self.target_anchor != self.resolved_region.page_region:
                raise ValueError("visual region target does not match resolved page region")
        elif isinstance(self.target_anchor, OpaqueProviderPointerAnchor):
            if self.resolved_region.provider_pointer != self.target_anchor.target:
                raise ValueError("visual provider target does not match resolved pointer")
        elif isinstance(self.target_anchor, TextSpanAnchor):
            raise ValueError("text span is not a visual target")
        if self.recipe != self.page_raster.recipe:
            raise ValueError("visual recipe does not match page raster")
        transform = self.transform
        raster = self.page_raster
        if (
            transform.source_width != raster.source_width
            or transform.source_height != raster.source_height
            or transform.source_rotation != raster.source_rotation
            or transform.applied_rotation != raster.applied_rotation
            or transform.scale_numerator != self.recipe.scale_numerator
            or transform.scale_denominator != self.recipe.scale_denominator
            or transform.raster_width != raster.pixel_width
            or transform.raster_height != raster.pixel_height
        ):
            raise ValueError("visual transform does not match raster recipe")
        if (
            self.crop_width != transform.right - transform.left
            or self.crop_height != transform.bottom - transform.top
        ):
            raise ValueError("crop dimensions do not match pixel transform")
        if self.crop_width > self.recipe.limits.max_crop_dimension:
            raise ValueError("crop width exceeds render limits")
        if self.crop_height > self.recipe.limits.max_crop_dimension:
            raise ValueError("crop height exceeds render limits")
        if self.crop_width * self.crop_height > self.recipe.limits.max_crop_pixels:
            raise ValueError("crop pixels exceed render limits")
        if self.created_at != self.page_raster.created_at:
            raise ValueError("visual creation time must equal deterministic raster time")
        expected = visual_evidence_id(
            source_version_id=self.source_version_id,
            representation_id=self.representation_id,
            native_representation_id=self.native_representation_id,
            evidence_reference_id=self.evidence_reference_id,
            evidence_projection_id=self.evidence_projection_id,
            target_anchor=self.target_anchor.model_dump(mode="json"),
            resolved_region=self.resolved_region.model_dump(mode="json"),
            raster_id=self.page_raster.raster_id,
            transform=self.transform.model_dump(mode="json"),
            crop_object_id=self.crop_object.object_id,
            crop_media_type=self.crop_media_type,
            recipe=self.recipe.model_dump(mode="json"),
            usage_policy=self.usage_policy.model_dump(mode="json"),
        )
        if self.visual_evidence_id != expected:
            raise ValueError("visual_evidence_id does not match canonical identity")
        return self


def _canonical_object(model: DomainModel) -> StoredObject:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


class VisualEvidenceCommit(DomainModel):
    """Complete CAS-published material requested for one atomic visual commit."""

    page_raster: VisualPageRaster
    descriptor: VisualEvidenceDescriptor
    raster_record_object: StoredObject
    descriptor_object: StoredObject
    crop_object: StoredObject

    @model_validator(mode="after")
    def _canonical_objects_match(self) -> Self:
        if self.descriptor.page_raster != self.page_raster:
            raise ValueError("descriptor page raster does not match commit raster")
        if self.descriptor.crop_object != self.crop_object:
            raise ValueError("descriptor crop object does not match commit crop")
        if self.raster_record_object != _canonical_object(self.page_raster):
            raise ValueError("raster record object does not match canonical page raster")
        if self.descriptor_object != _canonical_object(self.descriptor):
            raise ValueError("descriptor object does not match canonical descriptor")
        return self


class VisualEvidenceRecord(DomainModel):
    """Body-free catalog projection for one complete visual descriptor."""

    visual_evidence_id: Sha256Id
    scope: RepresentationScope
    evidence_projection_id: Sha256Id
    raster_id: Sha256Id
    raster_record_object: StoredObject
    descriptor_object: StoredObject
    crop_object: StoredObject
    page_number: int = Field(strict=True, ge=1, le=10_000)
    granularity: VisualGranularity
    canonical_context_profile: bool
    created_at: UtcDatetime
    row_fingerprint: Sha256Id

    @model_validator(mode="after")
    def _row_identity_matches(self) -> Self:
        if self.row_fingerprint != visual_record_fingerprint(self):
            raise ValueError("row_fingerprint does not match visual record")
        return self


def visual_record_fingerprint(record: VisualEvidenceRecord) -> str:
    """Hash every visual catalog fact except the fingerprint itself."""
    return canonical_sha256(record.model_dump(mode="json", exclude={"row_fingerprint"}))


class VisualInterpretationOperation(StrEnum):
    """Closed optional interpretation operations."""

    OCR = "ocr"
    CAPTION = "caption"


class VisualInterpretationRequest(DomainModel):
    """Exact bounded request for one explicitly selected interpretation provider."""

    visual_evidence_id: Sha256Id
    descriptor_object_id: Sha256Id
    crop_object_id: Sha256Id
    operation: VisualInterpretationOperation
    provider: ProviderRecipe
    prompt_hash: Sha256Id
    max_output_characters: int = Field(default=32_768, strict=True, gt=0, le=1_000_000)
    max_warning_codes: int = Field(default=32, strict=True, ge=0, le=1_000)


class VisualInterpretationResult(DomainModel):
    """Bounded untrusted text returned by an optional OCR/caption provider."""

    operation: VisualInterpretationOperation
    text: Annotated[str, StringConstraints(strict=True, max_length=1_000_000)]
    confidence_ppm: int | None = Field(
        default=None,
        strict=True,
        ge=0,
        le=NORMALIZED_PPM_SCALE,
    )
    language: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64)] | None = (
        None
    )
    region_hint: PageRegionAnchor | None = None
    warning_codes: tuple[MachineToken, ...] = ()

    @model_validator(mode="after")
    def _warnings_are_canonical(self) -> Self:
        if self.warning_codes != tuple(sorted(set(self.warning_codes))):
            raise ValueError("warning codes must be sorted and unique")
        return self


__all__ = [
    "CANONICAL_ASPECT_ERROR_PPM",
    "NORMALIZED_PPM_SCALE",
    "VISUAL_CONTRACT_VERSION",
    "ResolvedVisualRegion",
    "VisualEvidenceCommit",
    "VisualEvidenceDescriptor",
    "VisualEvidenceRecord",
    "VisualGranularity",
    "VisualInterpretationOperation",
    "VisualInterpretationRequest",
    "VisualInterpretationResult",
    "VisualPageRaster",
    "VisualPixelTransform",
    "VisualRenderLimits",
    "VisualRenderRecipe",
    "VisualUsagePolicy",
    "VisualUsageScope",
    "aspect_error_ppm",
    "pixel_bounds",
    "visual_record_fingerprint",
    "visual_render_config_hash",
]
