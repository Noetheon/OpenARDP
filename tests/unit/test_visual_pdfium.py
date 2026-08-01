"""Deterministic PDFium/Pillow renderer tests over a synthetic local PDF."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image

from openardp.adapters.visual_pdfium import PdfiumVisualRenderer, canonical_visual_recipe
from openardp.domain.visual import VisualRenderLimits
from openardp.ports.visual import (
    UnsupportedVisualMedia,
    VisualMalformedInput,
    VisualResourceLimitExceeded,
)

ROOT = Path(__file__).parents[2]
PDF = ROOT / "tests/fixtures/rich/synthetic.pdf"


def test_pdf_page_and_crop_are_deterministic_stripped_rgb_pngs() -> None:
    """Pin dimensions, bytes, mode, metadata and half-open crop behavior."""
    renderer = PdfiumVisualRenderer()
    source = PDF.read_bytes()
    first = renderer.render_page(source, media_type="application/pdf", page_number=1)
    second = renderer.render_page(source, media_type="application/pdf", page_number=1)
    assert first == second
    assert first.page_count == 1
    assert (first.source_width_mpt, first.source_height_mpt) == (612_000, 792_000)
    assert (first.pixel_width, first.pixel_height) == (1_224, 1_584)
    assert hashlib.sha256(second.png_bytes).digest() == hashlib.sha256(first.png_bytes).digest()
    with Image.open(io.BytesIO(first.png_bytes)) as image:
        assert image.mode == "RGB"
        assert image.size == (1_224, 1_584)
        assert image.info == {}
        assert getattr(image, "n_frames", 1) == 1

    crop = renderer.crop_page(first.png_bytes, bounds=(100, 200, 500, 700))
    repeated_crop = renderer.crop_page(second.png_bytes, bounds=(100, 200, 500, 700))
    assert crop == repeated_crop
    assert (crop.pixel_width, crop.pixel_height) == (400, 500)
    with Image.open(io.BytesIO(crop.png_bytes)) as image:
        assert image.mode == "RGB"
        assert image.size == (400, 500)
        assert image.info == {}


def test_canonical_recipe_binds_exact_installed_wheel_artifacts() -> None:
    """Separate cache identities when platform-specific native wheels can differ."""
    first = canonical_visual_recipe()
    second = canonical_visual_recipe()
    assert first == second
    assert re.fullmatch(r"pdf-rgb-v1\+wheel-sha256:[0-9a-f]{64}", first.renderer.profile or "")
    assert re.fullmatch(r"png-rgb-v1\+wheel-sha256:[0-9a-f]{64}", first.encoder.profile or "")


def test_renderer_rejects_unsupported_malformed_absent_and_oversized_inputs() -> None:
    """Fail closed before or during native decoding with sanitized errors."""
    renderer = PdfiumVisualRenderer()
    with pytest.raises(UnsupportedVisualMedia):
        renderer.render_page(PDF.read_bytes(), media_type="image/png", page_number=1)
    with pytest.raises(VisualMalformedInput):
        renderer.render_page(b"not a pdf", media_type="application/pdf", page_number=1)
    with pytest.raises(VisualMalformedInput):
        renderer.render_page(PDF.read_bytes(), media_type="application/pdf", page_number=2)
    with pytest.raises(VisualMalformedInput):
        renderer.crop_page(b"not png", bounds=(0, 0, 1, 1))

    limits = VisualRenderLimits(max_encoded_bytes=10)
    bounded = PdfiumVisualRenderer(recipe=canonical_visual_recipe(limits))
    with pytest.raises(VisualResourceLimitExceeded):
        bounded.render_page(PDF.read_bytes(), media_type="application/pdf", page_number=1)


def test_crop_rejects_out_of_bounds_and_limit_excess() -> None:
    """Never clamp a requested crop or decode beyond the configured caps."""
    renderer = PdfiumVisualRenderer()
    page = renderer.render_page(PDF.read_bytes(), media_type="application/pdf", page_number=1)
    with pytest.raises(VisualMalformedInput):
        renderer.crop_page(page.png_bytes, bounds=(-1, 0, 10, 10))
    limits = VisualRenderLimits(max_crop_dimension=100, max_crop_pixels=10_000)
    bounded = PdfiumVisualRenderer(recipe=canonical_visual_recipe(limits))
    with pytest.raises(VisualResourceLimitExceeded):
        bounded.crop_page(page.png_bytes, bounds=(0, 0, 101, 10))


@pytest.mark.parametrize(
    ("rotation", "expected_source", "expected_pixels"),
    (
        (0, (612_000, 792_000), (1_224, 1_584)),
        (90, (612_000, 792_000), (1_584, 1_224)),
        (180, (612_000, 792_000), (1_224, 1_584)),
        (270, (612_000, 792_000), (1_584, 1_224)),
    ),
)
def test_pdf_intrinsic_rotation_records_raw_page_and_display_raster(
    rotation: int,
    expected_source: tuple[int, int],
    expected_pixels: tuple[int, int],
) -> None:
    """Keep intrinsic source geometry distinct from the rotated display raster."""
    document = pdfium.PdfDocument.new()
    page = document.new_page(612, 792)
    page.set_rotation(rotation)
    target = io.BytesIO()
    document.save(target)
    page.close()
    document.close()

    rendered = PdfiumVisualRenderer().render_page(
        target.getvalue(), media_type="application/pdf", page_number=1
    )

    assert (rendered.source_width_mpt, rendered.source_height_mpt) == expected_source
    assert rendered.source_rotation == rotation
    assert (rendered.pixel_width, rendered.pixel_height) == expected_pixels
