"""Deterministic bounded PDFium/Pillow visual renderer."""

from __future__ import annotations

import hashlib
import io
import math
from collections.abc import Callable
from importlib import metadata
from typing import Any, cast

from openardp.domain.common import ComponentDescriptor
from openardp.domain.visual import (
    Rotation,
    VisualRenderLimits,
    VisualRenderRecipe,
    visual_render_config_hash,
)
from openardp.ports.visual import (
    RenderedVisualCrop,
    RenderedVisualPage,
    UnsupportedVisualMedia,
    VisualCancelled,
    VisualDependencyUnavailable,
    VisualEncryptedInput,
    VisualMalformedInput,
    VisualResourceLimitExceeded,
)

_WHEEL_FINGERPRINT_PROFILE = "{base}+wheel-sha256:{fingerprint}"


def _distribution_fingerprint(name: str, expected_version: str) -> str:
    """Fingerprint the exact installed distribution contents from RECORD hashes."""
    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError as error:
        raise VisualDependencyUnavailable("visual dependency unavailable") from error
    if distribution.version != expected_version:
        raise VisualDependencyUnavailable("visual dependency version mismatch")
    records: list[str] = []
    for file in distribution.files or ():
        digest = file.hash
        if digest is None:
            continue
        records.append(f"{file}\0{digest.mode}\0{digest.value}\0{file.size}")
    if not records:
        raise VisualDependencyUnavailable("visual dependency record unavailable")
    payload = "\n".join(sorted(records)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_visual_recipe(
    limits: VisualRenderLimits | None = None,
) -> VisualRenderRecipe:
    """Build the installed deterministic PDF/PNG recipe without importing providers."""
    renderer = ComponentDescriptor(
        name="pypdfium2",
        version="5.12.1",
        profile=_WHEEL_FINGERPRINT_PROFILE.format(
            base="pdf-rgb-v1",
            fingerprint=_distribution_fingerprint("pypdfium2", "5.12.1"),
        ),
    )
    encoder = ComponentDescriptor(
        name="Pillow",
        version="12.3.0",
        profile=_WHEEL_FINGERPRINT_PROFILE.format(
            base="png-rgb-v1",
            fingerprint=_distribution_fingerprint("Pillow", "12.3.0"),
        ),
    )
    render_limits = limits or VisualRenderLimits()
    values = {
        "renderer": renderer,
        "encoder": encoder,
        "scale_numerator": 2,
        "scale_denominator": 1,
        "color_mode": "RGB",
        "background_rgb": (255, 255, 255),
        "draw_annotations": False,
        "draw_forms": False,
        "metadata_policy": "strip",
        "max_page_aspect_error_ppm": 1_000,
        "limits": render_limits,
    }
    return VisualRenderRecipe(
        renderer=renderer,
        encoder=encoder,
        scale_numerator=2,
        scale_denominator=1,
        color_mode="RGB",
        background_rgb=(255, 255, 255),
        draw_annotations=False,
        draw_forms=False,
        metadata_policy="strip",
        max_page_aspect_error_ppm=1_000,
        limits=render_limits,
        config_hash=visual_render_config_hash(values),
    )


def _providers() -> tuple[Any, Any]:
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]
        from PIL import Image
    except ImportError as error:  # pragma: no cover - exercised in isolated core env
        raise VisualDependencyUnavailable("visual dependency unavailable") from error
    try:
        pdfium_version = metadata.version("pypdfium2")
        pillow_version = metadata.version("Pillow")
    except metadata.PackageNotFoundError as error:
        raise VisualDependencyUnavailable("visual dependency unavailable") from error
    if pdfium_version != "5.12.1" or pillow_version != "12.3.0":
        raise VisualDependencyUnavailable("visual dependency version mismatch")
    return pdfium, Image


def _canonical_png(image: Any, *, max_output_bytes: int) -> bytes:
    image = image.convert("RGB")
    target = io.BytesIO()
    image.save(
        target,
        format="PNG",
        optimize=False,
        compress_level=9,
    )
    payload = target.getvalue()
    if len(payload) > max_output_bytes:
        raise VisualResourceLimitExceeded("visual output exceeds byte limit")
    return payload


def _metadata_size(info: dict[Any, Any]) -> int:
    """Return a conservative encoded size for inert decoder metadata."""
    total = 0
    for key, value in info.items():
        total += len(str(key).encode("utf-8"))
        total += len(value if isinstance(value, bytes) else str(value).encode("utf-8"))
    return total


class PdfiumVisualRenderer:
    """Render exact PDF pages and crops with independent admission limits."""

    def __init__(self, *, recipe: VisualRenderRecipe | None = None) -> None:
        """Configure the exact reviewed render recipe."""
        self._recipe = recipe or canonical_visual_recipe()

    @property
    def recipe(self) -> VisualRenderRecipe:
        """Return the exact installed recipe."""
        return self._recipe

    def supports(self, media_type: str) -> bool:
        """Accept only exact PDF media."""
        return media_type == "application/pdf"

    def render_page(
        self,
        source: bytes,
        *,
        media_type: str,
        page_number: int,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualPage:
        """Decode and render one one-based PDF page to stripped RGB PNG bytes."""
        if cancellation_check is not None and cancellation_check():
            raise VisualCancelled("visual operation cancelled")
        if not self.supports(media_type):
            raise UnsupportedVisualMedia("unsupported visual media")
        limits = self._recipe.limits
        if not source or len(source) > limits.max_encoded_bytes:
            raise VisualResourceLimitExceeded("visual source exceeds byte limit")
        if page_number < 1 or page_number > limits.max_pages:
            raise VisualResourceLimitExceeded("visual page exceeds page limit")
        pdfium, _ = _providers()
        document = None
        page = None
        bitmap = None
        try:
            try:
                document = pdfium.PdfDocument(source, password=None, autoclose=False)
            except Exception as error:
                message = type(error).__name__.lower()
                if "password" in message or "security" in message:
                    raise VisualEncryptedInput("encrypted visual input") from error
                raise VisualMalformedInput("malformed visual input") from error
            page_count = len(document)
            if page_count > limits.max_pages:
                raise VisualResourceLimitExceeded("visual document exceeds page limit")
            if page_number > page_count:
                raise VisualMalformedInput("visual page is absent")
            page = document[page_number - 1]
            display_width, display_height = page.get_size()
            rotation = int(page.get_rotation())
            if (
                not math.isfinite(display_width)
                or not math.isfinite(display_height)
                or display_width <= 0
                or display_height <= 0
                or rotation not in {0, 90, 180, 270}
            ):
                raise VisualMalformedInput("visual page dimensions are invalid")
            width, height = (
                (display_height, display_width)
                if rotation in {90, 270}
                else (display_width, display_height)
            )
            source_width_mpt = math.ceil(width * 1_000)
            source_height_mpt = math.ceil(height * 1_000)
            scale = self._recipe.scale_numerator / self._recipe.scale_denominator
            predicted_width = math.ceil(display_width * scale)
            predicted_height = math.ceil(display_height * scale)
            if (
                predicted_width > limits.max_page_dimension
                or predicted_height > limits.max_page_dimension
                or predicted_width * predicted_height > limits.max_page_pixels
                or predicted_width * predicted_height * 3 > limits.max_decoded_bytes
            ):
                raise VisualResourceLimitExceeded("visual page exceeds decoded limits")
            bitmap = page.render(
                scale=scale,
                rotation=0,
                may_draw_forms=False,
                draw_annots=False,
                fill_color=(*self._recipe.background_rgb, 255),
                rev_byteorder=True,
            )
            image = bitmap.to_pil().convert("RGB")
            if image.size != (predicted_width, predicted_height):
                raise VisualMalformedInput("visual renderer dimensions drifted")
            payload = _canonical_png(image, max_output_bytes=limits.max_output_bytes)
            if cancellation_check is not None and cancellation_check():
                raise VisualCancelled("visual operation cancelled")
            return RenderedVisualPage(
                png_bytes=payload,
                page_count=page_count,
                source_width_mpt=source_width_mpt,
                source_height_mpt=source_height_mpt,
                source_rotation=cast("Rotation", rotation),
                applied_rotation=0,
                pixel_width=predicted_width,
                pixel_height=predicted_height,
            )
        except (
            VisualCancelled,
            VisualMalformedInput,
            VisualEncryptedInput,
            VisualResourceLimitExceeded,
        ):
            raise
        except Exception as error:
            raise VisualMalformedInput("malformed visual input") from error
        finally:
            if bitmap is not None:
                bitmap.close()
            if page is not None:
                page.close()
            if document is not None:
                document.close()

    def crop_page(
        self,
        page_png: bytes,
        *,
        bounds: tuple[int, int, int, int],
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualCrop:
        """Verify and crop one single-frame RGB PNG without metadata propagation."""
        if cancellation_check is not None and cancellation_check():
            raise VisualCancelled("visual operation cancelled")
        limits = self._recipe.limits
        if not page_png or len(page_png) > limits.max_output_bytes:
            raise VisualResourceLimitExceeded("visual raster exceeds byte limit")
        _, Image = _providers()
        try:
            with Image.open(io.BytesIO(page_png)) as image:
                if image.format != "PNG" or getattr(image, "n_frames", 1) != 1:
                    raise VisualMalformedInput("visual raster must be one PNG frame")
                if _metadata_size(image.info) > limits.max_metadata_bytes:
                    raise VisualResourceLimitExceeded("visual metadata exceeds byte limit")
                width, height = image.size
                if (
                    width > limits.max_page_dimension
                    or height > limits.max_page_dimension
                    or width * height > limits.max_page_pixels
                    or width * height * 3 > limits.max_decoded_bytes
                ):
                    raise VisualResourceLimitExceeded("visual raster exceeds decoded limits")
                left, top, right, bottom = bounds
                if not (0 <= left < right <= width and 0 <= top < bottom <= height):
                    raise VisualMalformedInput("visual crop bounds are outside raster")
                crop_width = right - left
                crop_height = bottom - top
                if (
                    crop_width > limits.max_crop_dimension
                    or crop_height > limits.max_crop_dimension
                    or crop_width * crop_height > limits.max_crop_pixels
                ):
                    raise VisualResourceLimitExceeded("visual crop exceeds decoded limits")
                cropped = image.convert("RGB").crop(bounds)
                payload = _canonical_png(cropped, max_output_bytes=limits.max_output_bytes)
                if cancellation_check is not None and cancellation_check():
                    raise VisualCancelled("visual operation cancelled")
                return RenderedVisualCrop(payload, crop_width, crop_height)
        except (VisualCancelled, VisualMalformedInput, VisualResourceLimitExceeded):
            raise
        except Exception as error:
            raise VisualMalformedInput("malformed visual raster") from error


__all__ = ["PdfiumVisualRenderer", "canonical_visual_recipe"]
