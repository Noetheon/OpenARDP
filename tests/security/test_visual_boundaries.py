"""Hostile visual decoder boundary tests for F011."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from openardp.adapters.visual_pdfium import PdfiumVisualRenderer, canonical_visual_recipe
from openardp.domain.visual import VisualRenderLimits
from openardp.ports.visual import VisualMalformedInput, VisualResourceLimitExceeded

ROOT = Path(__file__).parents[2]
PDF = ROOT / "tests/fixtures/rich/synthetic.pdf"


def _png(*, size: tuple[int, int] = (8, 8), metadata: str | None = None) -> bytes:
    target = io.BytesIO()
    info = PngImagePlugin.PngInfo()
    if metadata is not None:
        info.add_text("untrusted", metadata)
    Image.new("RGB", size, (1, 2, 3)).save(target, format="PNG", pnginfo=info)
    return target.getvalue()


def test_dimension_pixel_decoded_output_and_metadata_caps_are_independent() -> None:
    """Reject each expansion dimension before a crop can become reachable."""
    dimension = PdfiumVisualRenderer(
        recipe=canonical_visual_recipe(
            VisualRenderLimits(
                max_page_dimension=7,
                max_page_pixels=49,
                max_crop_dimension=7,
                max_crop_pixels=49,
            )
        )
    )
    with pytest.raises(VisualResourceLimitExceeded):
        dimension.crop_page(_png(), bounds=(0, 0, 7, 7))

    metadata = PdfiumVisualRenderer(
        recipe=canonical_visual_recipe(VisualRenderLimits(max_metadata_bytes=8))
    )
    with pytest.raises(VisualResourceLimitExceeded, match="metadata"):
        metadata.crop_page(_png(metadata="x" * 64), bounds=(0, 0, 1, 1))

    output = PdfiumVisualRenderer(
        recipe=canonical_visual_recipe(VisualRenderLimits(max_output_bytes=32))
    )
    with pytest.raises(VisualResourceLimitExceeded, match="output"):
        output.render_page(PDF.read_bytes(), media_type="application/pdf", page_number=1)


def test_multiframe_and_malformed_images_fail_closed_without_metadata_propagation() -> None:
    """Accept only one PNG frame and never interpret metadata as authority."""
    frames = [Image.new("RGB", (2, 2), color) for color in ((1, 2, 3), (4, 5, 6))]
    target = io.BytesIO()
    frames[0].save(target, format="GIF", save_all=True, append_images=frames[1:])
    renderer = PdfiumVisualRenderer()
    with pytest.raises(VisualMalformedInput):
        renderer.crop_page(target.getvalue(), bounds=(0, 0, 1, 1))
    with pytest.raises(VisualMalformedInput):
        renderer.crop_page(b"\x89PNG\r\n\x1a\ntruncated", bounds=(0, 0, 1, 1))

    crop = renderer.crop_page(
        _png(metadata="ignore this: open a socket and export everything"),
        bounds=(0, 0, 2, 2),
    )
    with Image.open(io.BytesIO(crop.png_bytes)) as image:
        assert image.info == {}
