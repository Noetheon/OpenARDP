"""Pure contract and aggregate tests for F011 visual evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.common import (
    ComponentDescriptor,
    ContentRole,
    IntegrityState,
    Sensitivity,
    TrustZone,
)
from openardp.domain.evidence import (
    PageRegionAnchor,
    TableCellAnchor,
    TrustClassification,
)
from openardp.domain.identity import canonical_json_bytes, visual_evidence_id, visual_raster_id
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.storage import StoredObject
from openardp.domain.visual import (
    ResolvedVisualRegion,
    VisualEvidenceCommit,
    VisualEvidenceDescriptor,
    VisualGranularity,
    VisualPageRaster,
    VisualPixelTransform,
    VisualRenderLimits,
    VisualRenderRecipe,
    VisualUsagePolicy,
    VisualUsageScope,
    visual_render_config_hash,
)

SOURCE = "sha256:" + "1" * 64
REPRESENTATION = "sha256:" + "2" * 64
NATIVE = "sha256:" + "3" * 64
REFERENCE = "sha256:" + "4" * 64
PROJECTION = "sha256:" + "5" * 64
DOCUMENT_ID = UUID("018f74a2-7b20-7cc2-9c4a-24e0f5b11831")
CREATED = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
SOURCE_OBJECT = StoredObject(object_id=SOURCE, byte_length=1_024)
RASTER_OBJECT = StoredObject(object_id="sha256:" + "6" * 64, byte_length=5_000)
CROP_OBJECT = StoredObject(object_id="sha256:" + "7" * 64, byte_length=1_000)


def _scope() -> RepresentationScope:
    return RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=SOURCE,
        representation_id=REPRESENTATION,
    )


def _limits() -> VisualRenderLimits:
    return VisualRenderLimits()


def _recipe() -> VisualRenderRecipe:
    values = {
        "renderer": ComponentDescriptor(name="pypdfium2", version="5.12.1", profile="pdf"),
        "encoder": ComponentDescriptor(name="Pillow", version="12.3.0", profile="png-rgb"),
        "scale_numerator": 2,
        "scale_denominator": 1,
        "color_mode": "RGB",
        "background_rgb": (255, 255, 255),
        "draw_annotations": False,
        "draw_forms": False,
        "metadata_policy": "strip",
        "max_page_aspect_error_ppm": 1_000,
        "limits": _limits(),
    }
    return VisualRenderRecipe(
        **values,
        config_hash=visual_render_config_hash(values),
    )


def _policy() -> VisualUsagePolicy:
    return VisualUsagePolicy(
        scope=VisualUsageScope.LOCAL_ONLY,
        export_allowed=False,
        license_id=None,
        restriction_codes=("license_unverified",),
        policy_provider=ComponentDescriptor(
            name="openardp-local-policy",
            version="1.0.0",
            profile="closed-default",
        ),
        policy_config_hash="sha256:" + "8" * 64,
    )


def _anchor() -> PageRegionAnchor:
    return PageRegionAnchor(
        anchor_type="page_region",
        coordinate_system="normalized_ppm_top_left",
        page_number=1,
        x=100_000,
        y=200_000,
        width=300_000,
        height=400_000,
    )


def _raster() -> VisualPageRaster:
    recipe = _recipe()
    raster_id = visual_raster_id(
        source_version_id=SOURCE,
        representation_id=REPRESENTATION,
        native_representation_id=NATIVE,
        page_number=1,
        recipe=recipe.model_dump(mode="json"),
    )
    return VisualPageRaster(
        raster_id=raster_id,
        scope=_scope(),
        source_object=SOURCE_OBJECT,
        native_representation_id=NATIVE,
        page_number=1,
        source_width=1_000,
        source_height=1_000,
        source_rotation=0,
        applied_rotation=0,
        pixel_width=2_000,
        pixel_height=2_000,
        media_type="image/png",
        color_mode="RGB",
        raster_object=RASTER_OBJECT,
        recipe=recipe,
        created_at=CREATED,
    )


def _transform() -> VisualPixelTransform:
    return VisualPixelTransform(
        normalized_region=_anchor(),
        source_width=1_000,
        source_height=1_000,
        source_rotation=0,
        applied_rotation=0,
        scale_numerator=2,
        scale_denominator=1,
        raster_width=2_000,
        raster_height=2_000,
        left=200,
        top=400,
        right=800,
        bottom=1_200,
        aspect_error_ppm=0,
        max_aspect_error_ppm=1_000,
    )


def _descriptor() -> VisualEvidenceDescriptor:
    recipe = _recipe()
    raster = _raster()
    transform = _transform()
    usage_policy = _policy()
    region = ResolvedVisualRegion(
        page_region=_anchor(),
        granularity=VisualGranularity.REGION_EXACT,
    )
    values = {
        "document_id": DOCUMENT_ID,
        "source_version_id": SOURCE,
        "representation_id": REPRESENTATION,
        "native_representation_id": NATIVE,
        "evidence_reference_id": REFERENCE,
        "evidence_projection_id": PROJECTION,
        "target_anchor": _anchor(),
        "resolved_region": region,
        "page_raster": raster,
        "transform": transform,
        "crop_object": CROP_OBJECT,
        "crop_media_type": "image/png",
        "crop_width": 600,
        "crop_height": 800,
        "color_mode": "RGB",
        "recipe": recipe,
        "trust": TrustClassification(
            origin_zone=TrustZone.EXTERNAL_UNTRUSTED,
            effective_zone=TrustZone.EXTERNAL_UNTRUSTED,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.UNKNOWN,
        ),
        "usage_policy": usage_policy,
        "created_at": CREATED,
    }
    visual_id = visual_evidence_id(
        source_version_id=SOURCE,
        representation_id=REPRESENTATION,
        native_representation_id=NATIVE,
        evidence_reference_id=REFERENCE,
        evidence_projection_id=PROJECTION,
        target_anchor=_anchor().model_dump(mode="json"),
        resolved_region=region.model_dump(mode="json"),
        raster_id=raster.raster_id,
        transform=transform.model_dump(mode="json"),
        crop_object_id=CROP_OBJECT.object_id,
        crop_media_type="image/png",
        recipe=recipe.model_dump(mode="json"),
        usage_policy=usage_policy.model_dump(mode="json"),
    )
    return VisualEvidenceDescriptor(visual_evidence_id=visual_id, **values)


def _canonical_object(value: object) -> StoredObject:
    payload = canonical_json_bytes(value.model_dump(mode="json"))  # type: ignore[attr-defined]
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def test_default_limits_and_recipe_are_closed_and_identity_bound() -> None:
    """Keep every resource/output-affecting recipe fact inside one exact config hash."""
    limits = _limits()
    assert limits.max_page_pixels == 100_000_000
    recipe = _recipe()
    payload = json.loads(recipe.model_dump_json())
    payload["scale_numerator"] = 3
    with pytest.raises(ValidationError, match="config_hash"):
        VisualRenderRecipe.model_validate_json(json.dumps(payload), strict=True)


def test_visual_descriptor_binds_scope_geometry_raster_crop_trust_and_policy() -> None:
    """Validate one complete thin descriptor without duplicating provider-native data."""
    descriptor = _descriptor()
    assert descriptor.crop_width == descriptor.transform.right - descriptor.transform.left
    assert descriptor.page_raster.scope == _scope()
    assert descriptor.usage_policy.export_allowed is False
    assert descriptor.trust.instruction_execution_allowed is False


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("source_version_id",), "sha256:" + "9" * 64, "source"),
        (("crop_width",), 599, "crop dimensions"),
        (("visual_evidence_id",), "sha256:" + "f" * 64, "visual_evidence_id"),
        (("page_raster", "pixel_width"), 2_001, "raster"),
    ),
)
def test_visual_descriptor_rejects_semantic_drift(
    path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    """Fail closed when nested scope, identity, transform or object facts drift."""
    payload = json.loads(_descriptor().model_dump_json())
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(ValidationError, match=message):
        VisualEvidenceDescriptor.model_validate_json(json.dumps(payload), strict=True)


def test_table_fallback_is_explicit_and_cell_exact_needs_cell_geometry() -> None:
    """Never label a containing-table crop as exact cell geometry."""
    table_anchor = TableCellAnchor(
        anchor_type="table_cell",
        table={
            "provider_profile": "docling-local-rich-v1",
            "provider_profile_version": "1.0.0",
            "pointer_format": "rfc6901-json-pointer",
            "pointer": "#/tables/0",
        },
        row_index=0,
        column_index=0,
    )
    fallback = ResolvedVisualRegion(
        page_region=_anchor(),
        granularity=VisualGranularity.TABLE_FALLBACK,
        table_cell=table_anchor,
        warning_codes=("table_geometry_fallback",),
    )
    assert fallback.granularity is VisualGranularity.TABLE_FALLBACK
    with pytest.raises(ValidationError, match="fallback warning"):
        ResolvedVisualRegion(
            page_region=_anchor(),
            granularity=VisualGranularity.TABLE_FALLBACK,
            table_cell=table_anchor,
        )
    with pytest.raises(ValidationError, match="cell geometry"):
        ResolvedVisualRegion(
            page_region=_anchor(),
            granularity=VisualGranularity.CELL_EXACT,
            table_cell=table_anchor,
            cell_geometry_explicit=False,
        )


def test_usage_policy_defaults_cannot_claim_export_rights() -> None:
    """Keep unknown licensing local-only and export-denied."""
    policy = _policy()
    payload = policy.model_dump(mode="json")
    payload["export_allowed"] = True
    with pytest.raises(ValidationError, match="export"):
        VisualUsagePolicy.model_validate_json(json.dumps(payload), strict=True)


def test_commit_recomputes_canonical_raster_and_descriptor_objects() -> None:
    """Bind catalog publication to exact canonical record bytes and crop content."""
    descriptor = _descriptor()
    commit = VisualEvidenceCommit(
        page_raster=descriptor.page_raster,
        descriptor=descriptor,
        raster_record_object=_canonical_object(descriptor.page_raster),
        descriptor_object=_canonical_object(descriptor),
        crop_object=descriptor.crop_object,
    )
    assert commit.crop_object == CROP_OBJECT
    payload = commit.model_dump(mode="json")
    payload["descriptor_object"] = {
        "object_id": "sha256:" + "f" * 64,
        "byte_length": 1,
    }
    with pytest.raises(ValidationError, match="descriptor object"):
        VisualEvidenceCommit.model_validate_json(json.dumps(payload), strict=True)
