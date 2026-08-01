"""Spawn lifecycle and strict IPC tests for the optional visual worker."""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path

import pytest

from openardp.adapters.isolated_visual import (
    IsolatedVisualRenderer,
    _decode_result,
    _encode_result,
    _WorkerRequest,
)
from openardp.adapters.visual_pdfium import canonical_visual_recipe
from openardp.domain.visual import VisualRenderLimits
from openardp.ports.visual import (
    RenderedVisualCrop,
    VisualCancelled,
    VisualProcessCrashed,
    VisualResourceLimitExceeded,
    VisualTimedOut,
)

ROOT = Path(__file__).parents[2]
PDF = ROOT / "tests/fixtures/rich/synthetic.pdf"


def _hang(sender: object, request: _WorkerRequest) -> None:
    del sender, request
    time.sleep(10)


def _crash(sender: object, request: _WorkerRequest) -> None:
    del sender, request
    os._exit(23)


def _attempt_network(sender: object, request: _WorkerRequest) -> None:
    del request
    socket.socket()
    sender.send_bytes(b"network unexpectedly available")  # type: ignore[attr-defined]


def test_isolated_worker_renders_and_crops_exactly() -> None:
    """Prove byte-identical page/crop output across twenty fresh worker pairs."""
    renderer = IsolatedVisualRenderer()
    outputs = []
    for _ in range(20):
        page = renderer.render_page(PDF.read_bytes(), media_type="application/pdf", page_number=1)
        crop = renderer.crop_page(page.png_bytes, bounds=(0, 0, 100, 100))
        outputs.append((page.png_bytes, crop.png_bytes))
    assert len(set(outputs)) == 1
    assert (page.pixel_width, page.pixel_height) == (1_224, 1_584)
    assert (crop.pixel_width, crop.pixel_height) == (100, 100)


def test_worker_timeout_crash_and_egress_are_sanitized_and_reaped() -> None:
    """Map hostile worker behavior to body-free parent failures."""
    recipe = canonical_visual_recipe(VisualRenderLimits(timeout_seconds=0.1))
    with pytest.raises(VisualTimedOut):
        IsolatedVisualRenderer(recipe=recipe, _worker_behavior=_hang).render_page(
            PDF.read_bytes(), media_type="application/pdf", page_number=1
        )
    lifecycle_recipe = canonical_visual_recipe(VisualRenderLimits(timeout_seconds=2.0))
    with pytest.raises(VisualProcessCrashed):
        IsolatedVisualRenderer(recipe=lifecycle_recipe, _worker_behavior=_crash).render_page(
            PDF.read_bytes(), media_type="application/pdf", page_number=1
        )
    with pytest.raises(VisualProcessCrashed):
        IsolatedVisualRenderer(
            recipe=lifecycle_recipe, _worker_behavior=_attempt_network
        ).render_page(PDF.read_bytes(), media_type="application/pdf", page_number=1)


def test_worker_stream_is_bounded_and_cancellation_reaps_child() -> None:
    """Cancel during bounded chunk transfer without retaining a spawned process."""
    renderer = IsolatedVisualRenderer()
    with pytest.raises(VisualCancelled, match="cancelled"):
        renderer.render_page(
            PDF.read_bytes(),
            media_type="application/pdf",
            page_number=1,
            cancellation_check=lambda: True,
        )


def test_worker_result_protocol_is_closed_bounded_and_pickle_free() -> None:
    """Decode only the reviewed JSON-metadata plus raw-PNG frame shape."""
    result = RenderedVisualCrop(b"\x89PNG synthetic", 2, 3)
    frame = _encode_result("ok", result)
    assert not frame.startswith(b"\x80")
    assert _decode_result(frame, max_output_bytes=100, max_metadata_bytes=1_000) == result
    with pytest.raises(VisualResourceLimitExceeded, match="metadata"):
        _decode_result(b"not a frame", max_output_bytes=100, max_metadata_bytes=1_000)
    duplicate = b'{"status":"ok","status":"error"}'
    with pytest.raises(VisualProcessCrashed, match="protocol"):
        _decode_result(
            len(duplicate).to_bytes(8, "big") + duplicate,
            max_output_bytes=100,
            max_metadata_bytes=1_000,
        )
