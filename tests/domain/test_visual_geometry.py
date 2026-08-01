"""Exact integer geometry tests for F011 visual evidence."""

from __future__ import annotations

import pytest

from openardp.domain.evidence import PageRegionAnchor
from openardp.domain.visual import aspect_error_ppm, pixel_bounds


def _anchor(
    *,
    x: int = 100_000,
    y: int = 200_000,
    width: int = 300_000,
    height: int = 400_000,
) -> PageRegionAnchor:
    return PageRegionAnchor(
        anchor_type="page_region",
        coordinate_system="normalized_ppm_top_left",
        page_number=1,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def test_pixel_bounds_use_floor_left_top_and_ceiling_right_bottom() -> None:
    """Map fixed PPM coordinates with exact half-open integer arithmetic."""
    assert pixel_bounds(_anchor(), raster_width=2_003, raster_height=997) == (
        200,
        199,
        802,
        599,
    )


def test_full_page_and_one_ppm_regions_need_no_clamping() -> None:
    """Keep every valid F006 rectangle strictly inside the raster by construction."""
    full = _anchor(x=0, y=0, width=1_000_000, height=1_000_000)
    assert pixel_bounds(full, raster_width=17, raster_height=11) == (0, 0, 17, 11)
    tiny = _anchor(x=999_999, y=999_999, width=1, height=1)
    assert pixel_bounds(tiny, raster_width=20_000, raster_height=20_000) == (
        19_999,
        19_999,
        20_000,
        20_000,
    )


@pytest.mark.parametrize(("width", "height"), ((0, 1), (1, 0), (-1, 1)))
def test_pixel_bounds_reject_invalid_raster_extents(width: int, height: int) -> None:
    """Reject invalid raster dimensions rather than producing repaired geometry."""
    with pytest.raises(ValueError, match="raster dimensions"):
        pixel_bounds(_anchor(), raster_width=width, raster_height=height)


def test_aspect_error_is_rotation_aware_and_uses_ceiling_ppm() -> None:
    """Compare display ratios exactly without persisted floating-point values."""
    assert (
        aspect_error_ppm(
            source_width=1_000,
            source_height=2_000,
            source_rotation=90,
            raster_width=2_000,
            raster_height=1_000,
            applied_rotation=0,
        )
        == 0
    )
    assert (
        aspect_error_ppm(
            source_width=2_000,
            source_height=1_000,
            source_rotation=0,
            raster_width=1_999,
            raster_height=1_000,
            applied_rotation=0,
        )
        == 500
    )


def test_aspect_error_exposes_mismatch_above_canonical_bound() -> None:
    """Make a 0.1-percent mismatch a hard, measurable admission boundary."""
    assert (
        aspect_error_ppm(
            source_width=2_000,
            source_height=1_000,
            source_rotation=0,
            raster_width=1_997,
            raster_height=1_000,
            applied_rotation=0,
        )
        == 1_500
    )


def test_one_hundred_case_integer_geometry_corpus_is_exact() -> None:
    """Exercise 100 labelled regions over varied dimensions without float arithmetic."""
    for index in range(100):
        x = (index * 7_919) % 700_000
        y = (index * 5_003) % 700_000
        width = 1 + ((index * 3_571) % (1_000_000 - x))
        height = 1 + ((index * 2_939) % (1_000_000 - y))
        raster_width = 97 + index * 13
        raster_height = 113 + index * 17
        bounds = pixel_bounds(
            _anchor(x=x, y=y, width=width, height=height),
            raster_width=raster_width,
            raster_height=raster_height,
        )
        expected = (
            x * raster_width // 1_000_000,
            y * raster_height // 1_000_000,
            ((x + width) * raster_width + 999_999) // 1_000_000,
            ((y + height) * raster_height + 999_999) // 1_000_000,
        )
        assert bounds == expected, f"geometry case {index} drifted"
