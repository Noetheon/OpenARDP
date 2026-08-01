"""Spawned killable offline boundary for optional visual decoding."""

from __future__ import annotations

import json
import math
import multiprocessing
import os
import socket
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from multiprocessing.process import BaseProcess
from types import TracebackType
from typing import Protocol, Self, cast

from openardp.adapters.visual_pdfium import PdfiumVisualRenderer, canonical_visual_recipe
from openardp.domain.visual import Rotation, VisualRenderRecipe
from openardp.ports.visual import (
    RenderedVisualCrop,
    RenderedVisualPage,
    UnsupportedVisualMedia,
    VisualCancelled,
    VisualDependencyUnavailable,
    VisualEncryptedInput,
    VisualError,
    VisualMalformedInput,
    VisualProcessCrashed,
    VisualResourceLimitExceeded,
    VisualTimedOut,
)

_RESULT_OK = "ok"
_RESULT_ERROR = "error"
_STREAM_CHUNK_BYTES = 1_048_576


class _IpcConnection(Protocol):
    """Cross-platform structural subset of multiprocessing connections."""

    def close(self) -> None:
        """Close the endpoint."""
        ...

    def send_bytes(self, buf: bytes) -> None:
        """Send one bounded byte frame without object deserialization."""
        ...

    def recv_bytes(self, maxlength: int | None = None) -> bytes:
        """Receive one bounded byte frame without object deserialization."""
        ...

    def poll(self, timeout: float = 0.0) -> bool:
        """Return whether input is available before the timeout."""
        ...


class _ResourceModule(Protocol):
    """Portable typed subset of the POSIX-only ``resource`` module."""

    def getrlimit(self, resource: int, /) -> tuple[int, int]:
        """Return the soft and hard limits for one resource."""
        ...

    def setrlimit(self, resource: int, limits: tuple[int, int], /) -> None:
        """Set the soft and hard limits for one resource."""
        ...


@dataclass(frozen=True, slots=True)
class _WorkerRequest:
    operation: str
    payload: bytes
    media_type: str | None
    page_number: int | None
    bounds: tuple[int, int, int, int] | None
    recipe_json: str


_WorkerBehavior = Callable[[_IpcConnection, _WorkerRequest], None]


class _WorkerGuard:
    """Own and always terminate/reap one child and both IPC endpoints."""

    def __init__(
        self,
        process: BaseProcess,
        receiver: _IpcConnection,
        child_sender: _IpcConnection,
        input_sender: _IpcConnection,
        child_receiver: _IpcConnection,
    ) -> None:
        self.process = process
        self.receiver = receiver
        self.child_sender = child_sender
        self.input_sender = input_sender
        self.child_receiver = child_receiver

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.receiver.close()
        self.child_sender.close()
        self.input_sender.close()
        self.child_receiver.close()
        self.process.join(timeout=0.25)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1.0)
        if self.process.is_alive():  # pragma: no cover - platform emergency path
            self.process.kill()
            self.process.join(timeout=1.0)
        self.process.close()


class IsolatedVisualRenderer:
    """Execute PDF/image native code in a spawned resource-bounded process."""

    def __init__(
        self,
        *,
        recipe: VisualRenderRecipe | None = None,
        _worker_behavior: _WorkerBehavior | None = None,
    ) -> None:
        """Configure one recipe-identical worker and optional test behavior."""
        self._recipe = recipe or canonical_visual_recipe()
        self._worker_behavior = _worker_behavior or _worker

    @property
    def recipe(self) -> VisualRenderRecipe:
        """Return the exact child recipe."""
        return self._recipe

    def supports(self, media_type: str) -> bool:
        """Accept only the concrete adapter's PDF capability."""
        return media_type == "application/pdf"

    def render_page(
        self,
        source: bytes,
        *,
        media_type: str,
        page_number: int,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualPage:
        """Render one page through a spawned worker."""
        if not self.supports(media_type):
            raise UnsupportedVisualMedia("unsupported visual media")
        request = _WorkerRequest(
            operation="render",
            payload=source,
            media_type=media_type,
            page_number=page_number,
            bounds=None,
            recipe_json=self._recipe.model_dump_json(),
        )
        result = self._execute(request, cancelled=cancellation_check)
        if not isinstance(result, RenderedVisualPage):
            raise VisualProcessCrashed("visual worker returned invalid result")
        return result

    def crop_page(
        self,
        page_png: bytes,
        *,
        bounds: tuple[int, int, int, int],
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualCrop:
        """Crop one raster through a separately spawned worker."""
        request = _WorkerRequest(
            operation="crop",
            payload=page_png,
            media_type=None,
            page_number=None,
            bounds=bounds,
            recipe_json=self._recipe.model_dump_json(),
        )
        result = self._execute(request, cancelled=cancellation_check)
        if not isinstance(result, RenderedVisualCrop):
            raise VisualProcessCrashed("visual worker returned invalid result")
        return result

    def _execute(
        self,
        request: _WorkerRequest,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> RenderedVisualPage | RenderedVisualCrop:
        limits = self._recipe.limits
        if len(request.payload) > limits.max_encoded_bytes:
            raise VisualResourceLimitExceeded("visual input exceeds byte limit")
        context = multiprocessing.get_context("spawn")
        receiver, child_sender = context.Pipe(duplex=False)
        child_receiver, input_sender = context.Pipe(duplex=False)
        header = replace(request, payload=b"")
        process = context.Process(
            target=_worker_entry,
            args=(child_sender, child_receiver, header, self._worker_behavior),
            daemon=True,
        )
        process.start()
        child_sender.close()
        child_receiver.close()
        deadline = time.monotonic() + limits.timeout_seconds
        with _WorkerGuard(
            process,
            receiver,
            child_sender,
            input_sender,
            child_receiver,
        ) as guard:
            for offset in range(0, len(request.payload), _STREAM_CHUNK_BYTES):
                if cancelled is not None and cancelled():
                    raise VisualCancelled("visual operation cancelled")
                try:
                    guard.input_sender.send_bytes(
                        request.payload[offset : offset + _STREAM_CHUNK_BYTES]
                    )
                except (BrokenPipeError, EOFError, OSError) as error:
                    raise VisualProcessCrashed("visual worker crashed") from error
            guard.input_sender.send_bytes(b"")
            guard.input_sender.close()
            while True:
                if cancelled is not None and cancelled():
                    raise VisualCancelled("visual operation cancelled")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise VisualTimedOut("visual operation timed out")
                if guard.receiver.poll(min(0.05, remaining)):
                    break
                if not guard.process.is_alive():
                    raise VisualProcessCrashed("visual worker crashed")
            try:
                message = guard.receiver.recv_bytes(
                    maxlength=limits.max_output_bytes + limits.max_metadata_bytes + 8
                )
            except EOFError as error:
                raise VisualProcessCrashed("visual worker crashed") from error
            except OSError as error:
                raise VisualResourceLimitExceeded(
                    "visual worker result exceeds byte limit"
                ) from error
        return _decode_result(
            message,
            max_output_bytes=limits.max_output_bytes,
            max_metadata_bytes=limits.max_metadata_bytes,
        )


def _worker_entry(
    sender: _IpcConnection,
    source_receiver: _IpcConnection,
    request: _WorkerRequest,
    behavior: _WorkerBehavior,
) -> None:
    try:
        recipe = VisualRenderRecipe.model_validate_json(request.recipe_json, strict=True)
        _apply_resource_limits(recipe)
        _disable_network()
        payload = _receive_bounded_payload(
            source_receiver,
            max_bytes=recipe.limits.max_encoded_bytes,
        )
        request = replace(request, payload=payload)
        behavior(sender, request)
    except VisualError as error:
        _safe_send(sender, _RESULT_ERROR, error.code)
    except BaseException:
        _safe_send(sender, _RESULT_ERROR, "visual_process_crashed")
    finally:
        source_receiver.close()
        sender.close()


def _receive_bounded_payload(receiver: _IpcConnection, *, max_bytes: int) -> bytes:
    """Receive only bounded byte chunks terminated by one sentinel."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = receiver.recv_bytes(maxlength=_STREAM_CHUNK_BYTES)
        if chunk == b"":
            return b"".join(chunks)
        if len(chunk) > _STREAM_CHUNK_BYTES:
            raise VisualMalformedInput("visual stream is malformed")
        total += len(chunk)
        if total > max_bytes:
            raise VisualResourceLimitExceeded("visual stream exceeds byte limit")
        chunks.append(chunk)


def _worker(sender: _IpcConnection, request: _WorkerRequest) -> None:
    try:
        recipe = VisualRenderRecipe.model_validate_json(request.recipe_json, strict=True)
        renderer = PdfiumVisualRenderer(recipe=recipe)
        if request.operation == "render":
            if request.media_type is None or request.page_number is None:
                raise VisualMalformedInput("visual request is malformed")
            result: RenderedVisualPage | RenderedVisualCrop = renderer.render_page(
                request.payload,
                media_type=request.media_type,
                page_number=request.page_number,
            )
        elif request.operation == "crop":
            if request.bounds is None:
                raise VisualMalformedInput("visual request is malformed")
            result = renderer.crop_page(request.payload, bounds=request.bounds)
        else:
            raise VisualMalformedInput("visual request is malformed")
        _safe_send(sender, _RESULT_OK, result)
    except VisualError as error:
        _safe_send(sender, _RESULT_ERROR, error.code)
    except BaseException:
        _safe_send(sender, _RESULT_ERROR, "visual_process_crashed")


def _safe_send(
    sender: _IpcConnection,
    status: str,
    payload: RenderedVisualPage | RenderedVisualCrop | str,
) -> None:
    with suppress(BrokenPipeError, EOFError, OSError):
        sender.send_bytes(_encode_result(status, payload))


def _encode_result(
    status: str,
    payload: RenderedVisualPage | RenderedVisualCrop | str,
) -> bytes:
    """Encode one closed JSON-metadata plus PNG frame without pickle."""
    body = b""
    if status == _RESULT_ERROR and isinstance(payload, str):
        metadata: dict[str, object] = {"code": payload, "status": status}
    elif status == _RESULT_OK and isinstance(payload, RenderedVisualPage):
        body = payload.png_bytes
        metadata = {
            "applied_rotation": payload.applied_rotation,
            "page_count": payload.page_count,
            "pixel_height": payload.pixel_height,
            "pixel_width": payload.pixel_width,
            "result_type": "page",
            "source_height_mpt": payload.source_height_mpt,
            "source_rotation": payload.source_rotation,
            "source_width_mpt": payload.source_width_mpt,
            "status": status,
        }
    elif status == _RESULT_OK and isinstance(payload, RenderedVisualCrop):
        body = payload.png_bytes
        metadata = {
            "pixel_height": payload.pixel_height,
            "pixel_width": payload.pixel_width,
            "result_type": "crop",
            "status": status,
        }
    else:
        metadata = {"code": "visual_process_crashed", "status": _RESULT_ERROR}
    header = json.dumps(
        metadata,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return len(header).to_bytes(8, "big") + header + body


_ERRORS: dict[str, type[VisualError]] = {
    cls.code: cls
    for cls in (
        UnsupportedVisualMedia,
        VisualDependencyUnavailable,
        VisualEncryptedInput,
        VisualMalformedInput,
        VisualCancelled,
        VisualProcessCrashed,
        VisualResourceLimitExceeded,
        VisualTimedOut,
    )
}


def _decode_result(
    message: bytes,
    *,
    max_output_bytes: int,
    max_metadata_bytes: int,
) -> RenderedVisualPage | RenderedVisualCrop:
    if len(message) < 8:
        raise VisualProcessCrashed("visual worker returned invalid protocol")
    header_length = int.from_bytes(message[:8], "big")
    if header_length <= 0 or header_length > max_metadata_bytes:
        raise VisualResourceLimitExceeded("visual worker metadata exceeds byte limit")
    if 8 + header_length > len(message):
        raise VisualProcessCrashed("visual worker returned invalid protocol")
    header_bytes = message[8 : 8 + header_length]
    body = message[8 + header_length :]
    try:
        metadata = json.loads(
            header_bytes,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise VisualProcessCrashed("visual worker returned invalid protocol") from error
    if not isinstance(metadata, dict) or not all(isinstance(key, str) for key in metadata):
        raise VisualProcessCrashed("visual worker returned invalid protocol")
    status = metadata.get("status")
    if status == _RESULT_ERROR and set(metadata) == {"code", "status"}:
        code = metadata.get("code")
        if not isinstance(code, str) or body:
            raise VisualProcessCrashed("visual worker returned invalid protocol")
        error_class = _ERRORS.get(code, VisualProcessCrashed)
        raise error_class("visual worker failed")
    if status != _RESULT_OK:
        raise VisualProcessCrashed("visual worker returned invalid protocol")
    if not body:
        raise VisualProcessCrashed("visual worker returned invalid protocol")
    if len(body) > max_output_bytes:
        raise VisualResourceLimitExceeded("visual worker output exceeds byte limit")
    result_type = metadata.get("result_type")
    try:
        if result_type == "page" and set(metadata) == {
            "applied_rotation",
            "page_count",
            "pixel_height",
            "pixel_width",
            "result_type",
            "source_height_mpt",
            "source_rotation",
            "source_width_mpt",
            "status",
        }:
            return RenderedVisualPage(
                png_bytes=body,
                page_count=_positive_int(metadata["page_count"]),
                source_width_mpt=_positive_int(metadata["source_width_mpt"]),
                source_height_mpt=_positive_int(metadata["source_height_mpt"]),
                source_rotation=_rotation(metadata["source_rotation"]),
                applied_rotation=_rotation(metadata["applied_rotation"]),
                pixel_width=_positive_int(metadata["pixel_width"]),
                pixel_height=_positive_int(metadata["pixel_height"]),
            )
        if result_type == "crop" and set(metadata) == {
            "pixel_height",
            "pixel_width",
            "result_type",
            "status",
        }:
            return RenderedVisualCrop(
                png_bytes=body,
                pixel_width=_positive_int(metadata["pixel_width"]),
                pixel_height=_positive_int(metadata["pixel_height"]),
            )
    except (TypeError, ValueError):
        pass
    raise VisualProcessCrashed("visual worker returned invalid protocol")


def _positive_int(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("visual protocol integer is invalid")
    return value


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate visual protocol key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    del value
    raise ValueError("non-finite visual protocol number")


def _rotation(value: object) -> Rotation:
    if value == 0:
        return 0
    if value == 90:
        return 90
    if value == 180:
        return 180
    if value == 270:
        return 270
    raise ValueError("visual protocol rotation is invalid")


def _disable_network() -> None:
    """Deny socket creation and remove inherited proxy authority inside the child."""
    for key in tuple(os.environ):
        if key.lower().endswith("_proxy") or key.lower() == "no_proxy":
            os.environ.pop(key, None)

    class _DeniedSocket:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            raise PermissionError("network disabled")

    socket.socket = _DeniedSocket  # type: ignore[assignment,misc]
    socket.create_connection = _deny_connection  # type: ignore[assignment]


def _deny_connection(*args: object, **kwargs: object) -> None:
    del args, kwargs
    raise PermissionError("network disabled")


def _apply_resource_limits(recipe: VisualRenderRecipe) -> None:
    """Apply available POSIX limits; Windows still retains wall/output caps."""
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows
        return
    resource_api = cast(_ResourceModule, resource)
    limits = recipe.limits
    cpu_seconds = max(1, math.ceil(limits.timeout_seconds))
    candidates = (
        (getattr(resource, "RLIMIT_CPU", None), cpu_seconds),
        (getattr(resource, "RLIMIT_AS", None), limits.max_address_space_bytes),
        (getattr(resource, "RLIMIT_NOFILE", None), limits.max_open_files),
    )
    for kind, value in candidates:
        if kind is None:
            continue
        try:
            _, current_hard = resource_api.getrlimit(kind)
            bounded = value if current_hard < 0 else min(value, current_hard)
            resource_api.setrlimit(kind, (bounded, current_hard))
        except (OSError, ValueError):
            continue


__all__ = ["IsolatedVisualRenderer"]
