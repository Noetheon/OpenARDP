"""Shared synthetic accepted-rich and visual-commit construction for F011 tests."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from pathlib import Path

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.visual_pdfium import canonical_visual_recipe
from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.evidence import OpaqueProviderPointerAnchor, PageRegionAnchor
from openardp.domain.identity import (
    canonical_json_bytes,
    visual_evidence_id,
    visual_raster_id,
)
from openardp.domain.storage import StoredObject
from openardp.domain.visual import (
    ResolvedVisualRegion,
    VisualEvidenceCommit,
    VisualEvidenceDescriptor,
    VisualGranularity,
    VisualPageRaster,
    VisualPixelTransform,
)
from tests.integration.test_rich_catalog import NOW, _commit_canonical, _setup


def _stored_model(value: object) -> StoredObject:
    payload = canonical_json_bytes(value.model_dump(mode="json"))  # type: ignore[attr-defined]
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def prepared_visual(
    tmp_path: Path,
) -> tuple[SQLiteCatalog, FilesystemObjectStore, VisualEvidenceCommit]:
    """Return a revision-8 catalog containing one accepted rich parent plus visual commit."""
    catalog, store, base, _ = _setup(tmp_path)
    _, result = _commit_canonical(catalog, store, base)
    rich = result.artifacts
    projection = rich.bundle.projections[0]
    assert isinstance(projection.reference.anchor, OpaqueProviderPointerAnchor)
    source_object = rich.aggregate.representation.native_object
    assert source_object is not None
    recipe = canonical_visual_recipe()
    page_region = PageRegionAnchor(
        anchor_type="page_region",
        coordinate_system="normalized_ppm_top_left",
        page_number=1,
        x=100_000,
        y=200_000,
        width=300_000,
        height=400_000,
    )
    resolved = ResolvedVisualRegion(
        page_region=page_region,
        granularity=VisualGranularity.REGION_EXACT,
        provider_pointer=projection.reference.anchor.target,
    )
    raster_object = store.put_chunks((b"synthetic raster",))
    crop_object = store.put_chunks((b"synthetic crop",))
    raster = VisualPageRaster(
        raster_id=visual_raster_id(
            source_version_id=base.scope.version_id,
            representation_id=base.scope.representation_id,
            native_representation_id=rich.bundle.native_representation.native_representation_id,
            page_number=1,
            recipe=recipe.model_dump(mode="json"),
        ),
        scope=base.scope,
        source_object=source_object,
        native_representation_id=rich.bundle.native_representation.native_representation_id,
        page_number=1,
        source_width=1_000,
        source_height=1_000,
        source_rotation=0,
        applied_rotation=0,
        pixel_width=2_000,
        pixel_height=2_000,
        raster_object=raster_object,
        recipe=recipe,
        created_at=NOW + timedelta(seconds=2),
    )
    transform = VisualPixelTransform(
        normalized_region=page_region,
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
    )
    policy = LocalOnlyVisualPolicy().evaluate(projection)
    identity = visual_evidence_id(
        source_version_id=base.scope.version_id,
        representation_id=base.scope.representation_id,
        native_representation_id=rich.bundle.native_representation.native_representation_id,
        evidence_reference_id=projection.reference.evidence_reference_id,
        evidence_projection_id=projection.evidence_projection_id,
        target_anchor=projection.reference.anchor.model_dump(mode="json"),
        resolved_region=resolved.model_dump(mode="json"),
        raster_id=raster.raster_id,
        transform=transform.model_dump(mode="json"),
        crop_object_id=crop_object.object_id,
        crop_media_type="image/png",
        recipe=recipe.model_dump(mode="json"),
        usage_policy=policy.model_dump(mode="json"),
    )
    descriptor = VisualEvidenceDescriptor(
        visual_evidence_id=identity,
        document_id=base.scope.document_id,
        source_version_id=base.scope.version_id,
        representation_id=base.scope.representation_id,
        native_representation_id=rich.bundle.native_representation.native_representation_id,
        evidence_reference_id=projection.reference.evidence_reference_id,
        evidence_projection_id=projection.evidence_projection_id,
        target_anchor=projection.reference.anchor,
        resolved_region=resolved,
        page_raster=raster,
        transform=transform,
        crop_object=crop_object,
        crop_width=600,
        crop_height=800,
        recipe=recipe,
        trust=projection.trust,
        usage_policy=policy,
        created_at=NOW + timedelta(seconds=2),
    )
    raster_record_object = store.put_chunks((canonical_json_bytes(raster.model_dump(mode="json")),))
    descriptor_object = store.put_chunks(
        (canonical_json_bytes(descriptor.model_dump(mode="json")),)
    )
    assert raster_record_object == _stored_model(raster)
    assert descriptor_object == _stored_model(descriptor)
    return (
        catalog,
        store,
        VisualEvidenceCommit(
            page_raster=raster,
            descriptor=descriptor,
            raster_record_object=raster_record_object,
            descriptor_object=descriptor_object,
            crop_object=crop_object,
        ),
    )
