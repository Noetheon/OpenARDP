"""Provider-native visual target resolution tests."""

from __future__ import annotations

import pytest

from openardp.domain.evidence import (
    OpaqueProviderPointerAnchor,
    PageRegionAnchor,
    ProviderPointer,
    TableCellAnchor,
    TextSpanAnchor,
)
from openardp.domain.visual import VisualGranularity
from openardp.ports.visual import VisualTargetUnavailable
from openardp.services.visual_evidence import resolve_visual_region


def _pointer(value: str) -> ProviderPointer:
    return ProviderPointer(
        provider_profile="docling-local-rich-v1",
        provider_profile_version="1.0.0",
        pointer_format="rfc6901-json-pointer",
        pointer=value,
    )


def _provenance(*, left: int, top: int, right: int, bottom: int) -> dict[str, object]:
    return {
        "page_no": 1,
        "bbox": {
            "l": left,
            "t": top,
            "r": right,
            "b": bottom,
            "coord_origin": "TOPLEFT",
        },
    }


def _native(*, cell_geometry: bool = True) -> dict[str, object]:
    cell: dict[str, object] = {
        "start_row_offset_idx": 0,
        "start_col_offset_idx": 1,
        "row_span": 1,
        "col_span": 1,
    }
    if cell_geometry:
        cell["prov"] = [_provenance(left=20, top=40, right=40, bottom=60)]
    return {
        "pages": {"1": {"page_no": 1, "size": {"width": 100, "height": 200}}},
        "pictures": [{"prov": [_provenance(left=10, top=20, right=30, bottom=60)]}],
        "tables": [
            {
                "prov": [_provenance(left=10, top=20, right=90, bottom=100)],
                "data": {"table_cells": [cell]},
            }
        ],
    }


def test_page_region_and_provider_pointer_resolve_exactly() -> None:
    """Preserve direct PPM geometry and resolve exactly one native picture rectangle."""
    page = PageRegionAnchor(
        anchor_type="page_region",
        coordinate_system="normalized_ppm_top_left",
        page_number=1,
        x=0,
        y=0,
        width=1_000_000,
        height=1_000_000,
    )
    assert resolve_visual_region(page, native=_native()).granularity is VisualGranularity.PAGE_EXACT
    picture = OpaqueProviderPointerAnchor(
        anchor_type="provider_pointer",
        target=_pointer("#/pictures/0"),
    )
    resolved = resolve_visual_region(picture, native=_native())
    assert resolved.granularity is VisualGranularity.REGION_EXACT
    assert resolved.page_region.model_dump(mode="json") == {
        "anchor_type": "page_region",
        "coordinate_system": "normalized_ppm_top_left",
        "page_number": 1,
        "x": 100_000,
        "y": 100_000,
        "width": 200_000,
        "height": 200_000,
    }


def test_table_cell_is_exact_only_with_explicit_cell_geometry() -> None:
    """Fall back truthfully to containing table geometry when cell geometry is absent."""
    cell = TableCellAnchor(
        anchor_type="table_cell",
        table=_pointer("#/tables/0"),
        row_index=0,
        column_index=1,
    )
    exact = resolve_visual_region(cell, native=_native())
    assert exact.granularity is VisualGranularity.CELL_EXACT
    assert exact.cell_geometry_explicit is True
    fallback = resolve_visual_region(cell, native=_native(cell_geometry=False))
    assert fallback.granularity is VisualGranularity.TABLE_FALLBACK
    assert fallback.warning_codes == ("table_geometry_fallback",)


def test_missing_ambiguous_and_text_targets_fail_closed() -> None:
    """Reject absent/multiple provenance and targets without visual geometry."""
    picture = OpaqueProviderPointerAnchor(
        anchor_type="provider_pointer",
        target=_pointer("#/pictures/0"),
    )
    native = _native()
    native["pictures"][0]["prov"].append(_provenance(left=1, top=1, right=2, bottom=2))  # type: ignore[index,union-attr]
    with pytest.raises(VisualTargetUnavailable, match="ambiguous"):
        resolve_visual_region(picture, native=native)
    with pytest.raises(VisualTargetUnavailable, match="unavailable"):
        resolve_visual_region(
            picture.model_copy(update={"target": _pointer("#/pictures/99")}),
            native=_native(),
        )
    text = TextSpanAnchor(
        anchor_type="text_span",
        coordinate_system="unicode_code_points",
        start=0,
        end=1,
    )
    with pytest.raises(VisualTargetUnavailable, match="no exact visual geometry"):
        resolve_visual_region(text, native=_native())
