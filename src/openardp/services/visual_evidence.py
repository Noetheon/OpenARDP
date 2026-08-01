"""Verified explicit visual materialization and inspection orchestration."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from datetime import datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from typing import cast

from pydantic import JsonValue

from openardp.adapters.docling_native import page_region_from_provenance, resolve_json_pointer
from openardp.domain.evidence import (
    EvidenceAnchor,
    EvidenceProjection,
    OpaqueProviderPointerAnchor,
    PageRegionAnchor,
    TableCellAnchor,
    TextSpanAnchor,
)
from openardp.domain.identity import (
    canonical_json_bytes,
    visual_evidence_id,
    visual_raster_id,
)
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.storage import StoredObject
from openardp.domain.visual import (
    ResolvedVisualRegion,
    VisualEvidenceCommit,
    VisualEvidenceDescriptor,
    VisualGranularity,
    VisualPageRaster,
    VisualPixelTransform,
    aspect_error_ppm,
    pixel_bounds,
)
from openardp.ports.catalog import RichCatalog, VisualCatalog
from openardp.ports.object_store import ObjectStore, ObjectStoreError
from openardp.ports.parser import ParserError
from openardp.ports.visual import (
    VisualCancelled,
    VisualGeometryMismatch,
    VisualIntegrityError,
    VisualRenderer,
    VisualRightsPolicy,
    VisualTargetUnavailable,
)


def _never_cancel() -> bool:
    return False


def resolve_visual_region(
    anchor: EvidenceAnchor,
    *,
    native: Mapping[str, JsonValue],
) -> ResolvedVisualRegion:
    """Resolve one accepted F006 anchor without importing provider runtime code."""
    pages = native.get("pages")
    if not isinstance(pages, dict):
        raise VisualTargetUnavailable("native page geometry is unavailable")
    if isinstance(anchor, PageRegionAnchor):
        granularity = (
            VisualGranularity.PAGE_EXACT
            if (anchor.x, anchor.y, anchor.width, anchor.height) == (0, 0, 1_000_000, 1_000_000)
            else VisualGranularity.REGION_EXACT
        )
        return ResolvedVisualRegion(page_region=anchor, granularity=granularity)
    if isinstance(anchor, TextSpanAnchor):
        raise VisualTargetUnavailable("text spans have no exact visual geometry")
    if isinstance(anchor, OpaqueProviderPointerAnchor):
        node = _resolved_mapping(native, anchor.target.pointer)
        region = _region_from_node(node, pages=pages)
        return ResolvedVisualRegion(
            page_region=region,
            granularity=VisualGranularity.REGION_EXACT,
            provider_pointer=anchor.target,
        )
    table = _resolved_mapping(native, anchor.table.pointer)
    data = table.get("data")
    if not isinstance(data, dict):
        raise VisualTargetUnavailable("native table data is unavailable")
    cells = data.get("table_cells")
    if not isinstance(cells, list):
        raise VisualTargetUnavailable("native table cells are unavailable")
    matches = [cell for cell in cells if isinstance(cell, dict) and _cell_matches(cell, anchor)]
    if len(matches) != 1:
        raise VisualTargetUnavailable("native table cell is absent or ambiguous")
    try:
        region = _region_from_node(matches[0], pages=pages)
    except VisualTargetUnavailable:
        region = _region_from_node(table, pages=pages)
        return ResolvedVisualRegion(
            page_region=region,
            granularity=VisualGranularity.TABLE_FALLBACK,
            table_cell=anchor,
            warning_codes=("table_geometry_fallback",),
        )
    return ResolvedVisualRegion(
        page_region=region,
        granularity=VisualGranularity.CELL_EXACT,
        table_cell=anchor,
        cell_geometry_explicit=True,
    )


def _resolved_mapping(native: Mapping[str, JsonValue], pointer: str) -> dict[str, JsonValue]:
    try:
        value = resolve_json_pointer(
            dict(native),
            pointer,
            max_resolved_bytes=8_388_608,
        )
    except (ParserError, TypeError, ValueError) as error:
        raise VisualTargetUnavailable("native visual pointer is unavailable") from error
    if not isinstance(value, dict):
        raise VisualTargetUnavailable("native visual pointer is not an object")
    return value


def _region_from_node(
    node: Mapping[str, JsonValue],
    *,
    pages: Mapping[str, JsonValue],
) -> PageRegionAnchor:
    provenance = node.get("prov")
    if not isinstance(provenance, list) or len(provenance) != 1:
        raise VisualTargetUnavailable("native visual provenance is absent or ambiguous")
    item = provenance[0]
    if not isinstance(item, dict):
        raise VisualTargetUnavailable("native visual provenance is malformed")
    try:
        return page_region_from_provenance(item, pages=pages)
    except (TypeError, ValueError) as error:
        raise VisualTargetUnavailable("native visual provenance is malformed") from error


def _cell_matches(cell: Mapping[str, JsonValue], anchor: TableCellAnchor) -> bool:
    return (
        cell.get("start_row_offset_idx") == anchor.row_index
        and cell.get("start_col_offset_idx") == anchor.column_index
        and cell.get("row_span", 1) == anchor.row_span
        and cell.get("col_span", 1) == anchor.column_span
    )


class VisualEvidenceService:
    """Materialize and inspect current accepted visual evidence explicitly."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: RichCatalog | VisualCatalog,
        renderer: VisualRenderer,
        rights_policy: VisualRightsPolicy,
    ) -> None:
        """Bind provider-neutral persistence, rendering and trusted-rights ports."""
        self._object_store = object_store
        self._catalog = cast("RichCatalog", catalog)
        self._visual_catalog = cast("VisualCatalog", catalog)
        self._renderer = renderer
        self._rights_policy = rights_policy

    def materialize(
        self,
        scope: RepresentationScope,
        evidence_projection_id: str,
        *,
        created_at: datetime,
        cancellation_check: Callable[[], bool] = _never_cancel,
    ) -> VisualEvidenceDescriptor:
        """Explicitly render/crop one accepted projection and atomically register it."""
        self._check_cancelled(cancellation_check)
        artifacts = self._catalog.load_rich_representation(scope)
        if artifacts is None:
            raise VisualTargetUnavailable("accepted rich representation is unavailable")
        projection = next(
            (
                item
                for item in artifacts.bundle.projections
                if item.evidence_projection_id == evidence_projection_id
            ),
            None,
        )
        if projection is None:
            raise VisualTargetUnavailable("accepted evidence projection is unavailable")
        self._verify_projection_scope(
            scope, artifacts.bundle.native_representation.source_version_id, projection
        )
        version = self._catalog.get_version(scope.document_id, scope.version_id)
        if version is None:
            raise VisualIntegrityError("visual source version is unavailable")
        if not self._renderer.supports(version.media_type):
            raise VisualTargetUnavailable("visual source media is unsupported")
        source = self._read_exact(version.source)
        native = self._read_native(artifacts.accepted_attempt.provider_native_object)
        self._check_cancelled(cancellation_check)
        self._verify_pointer_profile(
            projection,
            artifacts.bundle.native_representation.provider.profile,
            artifacts.bundle.native_representation.provider.profile_version,
        )
        resolved = resolve_visual_region(projection.reference.anchor, native=native)
        native_width, native_height = _native_page_dimensions(
            native,
            resolved.page_region.page_number,
        )
        recipe = self._renderer.recipe
        raster_id = visual_raster_id(
            source_version_id=scope.version_id,
            representation_id=scope.representation_id,
            native_representation_id=projection.native_representation_id,
            page_number=resolved.page_region.page_number,
            recipe=recipe.model_dump(mode="json"),
        )
        existing_raster = self._visual_catalog.load_visual_raster(raster_id)
        if existing_raster is None:
            rendered = self._renderer.render_page(
                source,
                media_type=version.media_type,
                page_number=resolved.page_region.page_number,
                cancellation_check=cancellation_check,
            )
            native_error = aspect_error_ppm(
                source_width=native_width,
                source_height=native_height,
                source_rotation=0,
                raster_width=rendered.pixel_width,
                raster_height=rendered.pixel_height,
                applied_rotation=0,
            )
            renderer_error = aspect_error_ppm(
                source_width=rendered.source_width_mpt,
                source_height=rendered.source_height_mpt,
                source_rotation=rendered.source_rotation,
                raster_width=rendered.pixel_width,
                raster_height=rendered.pixel_height,
                applied_rotation=rendered.applied_rotation,
            )
            if max(native_error, renderer_error) > recipe.max_page_aspect_error_ppm:
                raise VisualGeometryMismatch("visual page geometry mismatch")
            self._check_cancelled(cancellation_check)
            raster_object = self._put_exact(rendered.png_bytes)
            self._check_cancelled(cancellation_check)
            raster = VisualPageRaster(
                raster_id=raster_id,
                scope=scope,
                source_object=version.source,
                native_representation_id=projection.native_representation_id,
                page_number=resolved.page_region.page_number,
                source_width=rendered.source_width_mpt,
                source_height=rendered.source_height_mpt,
                source_rotation=rendered.source_rotation,
                applied_rotation=rendered.applied_rotation,
                pixel_width=rendered.pixel_width,
                pixel_height=rendered.pixel_height,
                raster_object=raster_object,
                recipe=recipe,
                created_at=created_at,
            )
        else:
            raster = existing_raster
            if (
                raster.scope != scope
                or raster.native_representation_id != projection.native_representation_id
            ):
                raise VisualIntegrityError("cached visual raster scope drifted")
            self._verify_model_object(raster, self._canonical_object(raster))

        exact = next(
            (
                record
                for record in self._visual_catalog.list_visual_evidence(scope)
                if record.evidence_projection_id == evidence_projection_id
                and record.raster_id == raster.raster_id
            ),
            None,
        )
        if exact is not None:
            return self.inspect(exact.visual_evidence_id)

        raster_png = self._read_exact(raster.raster_object)
        self._check_cancelled(cancellation_check)
        bounds = pixel_bounds(
            resolved.page_region,
            raster_width=raster.pixel_width,
            raster_height=raster.pixel_height,
        )
        cropped = self._renderer.crop_page(
            raster_png,
            bounds=bounds,
            cancellation_check=cancellation_check,
        )
        self._check_cancelled(cancellation_check)
        crop_object = self._put_exact(cropped.png_bytes)
        self._check_cancelled(cancellation_check)
        transform = VisualPixelTransform(
            normalized_region=resolved.page_region,
            source_width=raster.source_width,
            source_height=raster.source_height,
            source_rotation=raster.source_rotation,
            applied_rotation=raster.applied_rotation,
            scale_numerator=recipe.scale_numerator,
            scale_denominator=recipe.scale_denominator,
            raster_width=raster.pixel_width,
            raster_height=raster.pixel_height,
            left=bounds[0],
            top=bounds[1],
            right=bounds[2],
            bottom=bounds[3],
            aspect_error_ppm=aspect_error_ppm(
                source_width=raster.source_width,
                source_height=raster.source_height,
                source_rotation=raster.source_rotation,
                raster_width=raster.pixel_width,
                raster_height=raster.pixel_height,
                applied_rotation=raster.applied_rotation,
            ),
        )
        policy = self._rights_policy.evaluate(projection)
        visual_id = visual_evidence_id(
            source_version_id=scope.version_id,
            representation_id=scope.representation_id,
            native_representation_id=projection.native_representation_id,
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
            visual_evidence_id=visual_id,
            document_id=scope.document_id,
            source_version_id=scope.version_id,
            representation_id=scope.representation_id,
            native_representation_id=projection.native_representation_id,
            evidence_reference_id=projection.reference.evidence_reference_id,
            evidence_projection_id=projection.evidence_projection_id,
            target_anchor=projection.reference.anchor,
            resolved_region=resolved,
            page_raster=raster,
            transform=transform,
            crop_object=crop_object,
            crop_width=cropped.pixel_width,
            crop_height=cropped.pixel_height,
            recipe=recipe,
            trust=projection.trust,
            usage_policy=policy,
            created_at=raster.created_at,
        )
        commit = VisualEvidenceCommit(
            page_raster=raster,
            descriptor=descriptor,
            raster_record_object=self._put_model(raster),
            descriptor_object=self._put_model(descriptor),
            crop_object=crop_object,
        )
        self._check_cancelled(cancellation_check)
        self._visual_catalog.commit_visual_evidence(commit)
        return self.inspect(visual_id)

    @staticmethod
    def _check_cancelled(cancellation_check: Callable[[], bool]) -> None:
        if cancellation_check():
            raise VisualCancelled("visual operation cancelled")

    def inspect(self, visual_evidence_id: str) -> VisualEvidenceDescriptor:
        """Load and fully verify one descriptor, records, source scope and CAS objects."""
        commit = self._visual_catalog.load_visual_evidence(visual_evidence_id)
        if commit is None:
            raise VisualTargetUnavailable("visual evidence is unavailable")
        self._verify_model_object(commit.page_raster, commit.raster_record_object)
        self._verify_model_object(commit.descriptor, commit.descriptor_object)
        self._read_exact(commit.page_raster.raster_object)
        self._read_exact(commit.crop_object)
        artifacts = self._catalog.load_rich_representation(commit.page_raster.scope)
        if artifacts is None or not any(
            item.evidence_projection_id == commit.descriptor.evidence_projection_id
            and item.reference.evidence_reference_id == commit.descriptor.evidence_reference_id
            and item.reference.anchor == commit.descriptor.target_anchor
            for item in artifacts.bundle.projections
        ):
            raise VisualIntegrityError("visual evidence parent projection is unavailable")
        return commit.descriptor

    @staticmethod
    def _verify_projection_scope(
        scope: RepresentationScope,
        native_source_version_id: str,
        projection: EvidenceProjection,
    ) -> None:
        if (
            projection.source_version_id != scope.version_id
            or native_source_version_id != scope.version_id
        ):
            raise VisualIntegrityError("visual projection source scope drifted")

    @staticmethod
    def _verify_pointer_profile(
        projection: EvidenceProjection,
        profile: str,
        profile_version: str,
    ) -> None:
        anchor = projection.reference.anchor
        pointer = None
        if isinstance(anchor, OpaqueProviderPointerAnchor):
            pointer = anchor.target
        elif isinstance(anchor, TableCellAnchor):
            pointer = anchor.table
        if pointer is not None and (
            pointer.provider_profile != profile
            or pointer.provider_profile_version != profile_version
            or pointer.pointer_format != "rfc6901-json-pointer"
        ):
            raise VisualIntegrityError("visual pointer profile drifted")

    def _read_native(self, stored: StoredObject) -> dict[str, JsonValue]:
        payload = self._read_exact(stored)
        try:
            native = json.loads(payload)
            if not isinstance(native, dict) or canonical_json_bytes(native) != payload:
                raise ValueError
            return cast("dict[str, JsonValue]", native)
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise VisualIntegrityError("visual native record is invalid") from error

    def _read_exact(self, stored: StoredObject) -> bytes:
        try:
            verified = self._object_store.verify(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        except ObjectStoreError as error:
            raise VisualIntegrityError("visual object verification failed") from error
        if len(payload) != verified.byte_length:
            raise VisualIntegrityError("visual object length changed")
        return payload

    def _put_exact(self, payload: bytes) -> StoredObject:
        try:
            stored = self._object_store.put_chunks((payload,))
            return self._object_store.verify(
                stored.object_id,
                expected_length=len(payload),
            )
        except ObjectStoreError as error:
            raise VisualIntegrityError("visual object publication failed") from error

    def _put_model(self, model: VisualPageRaster | VisualEvidenceDescriptor) -> StoredObject:
        return self._put_exact(canonical_json_bytes(model.model_dump(mode="json")))

    @staticmethod
    def _canonical_object(model: VisualPageRaster | VisualEvidenceDescriptor) -> StoredObject:
        payload = canonical_json_bytes(model.model_dump(mode="json"))
        return StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )

    def _verify_model_object(
        self,
        model: VisualPageRaster | VisualEvidenceDescriptor,
        stored: StoredObject,
    ) -> None:
        expected = self._canonical_object(model)
        if stored != expected or self._read_exact(stored) != canonical_json_bytes(
            model.model_dump(mode="json")
        ):
            raise VisualIntegrityError("visual canonical record drifted")


def _native_page_dimensions(
    native: Mapping[str, JsonValue],
    page_number: int,
) -> tuple[int, int]:
    try:
        pages = native["pages"]
        if not isinstance(pages, dict):
            raise ValueError
        page = pages[str(page_number)]
        if not isinstance(page, dict):
            raise ValueError
        size = page["size"]
        if not isinstance(size, dict):
            raise ValueError
        width = Decimal(str(size["width"]))
        height = Decimal(str(size["height"]))
        if not width.is_finite() or not height.is_finite() or width <= 0 or height <= 0:
            raise ValueError
        width_mpt = int((width * 1_000).to_integral_value(rounding=ROUND_CEILING))
        height_mpt = int((height * 1_000).to_integral_value(rounding=ROUND_CEILING))
        if not all(
            math.isfinite(value) and 0 < value <= 9_007_199_254_740_991
            for value in (width_mpt, height_mpt)
        ):
            raise ValueError
        return width_mpt, height_mpt
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise VisualTargetUnavailable("native page dimensions are unavailable") from error


__all__ = ["VisualEvidenceService", "resolve_visual_region"]
