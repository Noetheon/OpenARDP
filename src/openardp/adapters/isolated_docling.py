"""Killable spawned-process boundary for the optional Docling provider."""

from __future__ import annotations

import math
import multiprocessing
import os
import queue
import shutil
import socket
import sys
import tempfile
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import TracebackType
from typing import NoReturn, Protocol, Self, cast

from pydantic import JsonValue, ValidationError

from openardp.domain.ingestion import RichMediaType
from openardp.domain.rich_ingestion import (
    ModelBundleManifest,
    RichParseOutput,
    RichParserLimits,
    RichParserRecipe,
)
from openardp.ports.parser import (
    InvalidRichParserOutput,
    ParserError,
    ParserProcessCrashed,
    ParserTimedOut,
    RichParserCancelled,
    RichParserDependencyUnavailable,
    RichParserMalformedDocument,
    RichParserModelAssetsInvalid,
    RichParserModelAssetsRequired,
    RichParserNetworkDenied,
    RichParserPartialConversion,
    RichParserResourceLimitExceeded,
    UnsupportedRichMedia,
)

_MESSAGE_MEDIA = "media_type"
_MESSAGE_CHUNK = "chunk"
_MESSAGE_END = "end"
_RESULT_OK = "ok"
_RESULT_ERROR = "error"


class _BlockedSocket(socket.socket):
    """Socket-compatible class whose construction is denied."""

    def __new__(cls, *args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("network access disabled")


class _IpcConnection(Protocol):
    """Cross-platform structural subset shared by multiprocessing pipe endpoints."""

    def close(self) -> None:
        """Close this endpoint."""
        ...

    def send(self, obj: object) -> None:
        """Send one picklable protocol value."""
        ...

    def recv(self) -> object:
        """Receive one protocol value."""
        ...

    def poll(self, timeout: float = 0.0) -> bool:
        """Return whether one value is available within the timeout."""
        ...


@dataclass(frozen=True, slots=True)
class _WorkerConfig:
    limits_json: str
    model_root: str | None
    model_manifest_json: str | None


_WorkerBehavior = Callable[[_IpcConnection, _IpcConnection, _WorkerConfig], None]


class _WorkerGuard:
    """Own a child and both parent IPC handles through guaranteed cleanup."""

    def __init__(
        self,
        process: BaseProcess,
        input_sender: _IpcConnection,
        result_receiver: _IpcConnection,
    ) -> None:
        self.process = process
        self.input_sender = input_sender
        self.result_receiver = result_receiver

    def __enter__(self) -> Self:
        """Return active worker resources."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close IPC and terminate, kill and reap as needed."""
        self.input_sender.close()
        self.result_receiver.close()
        self.process.join(timeout=0.25)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1.0)
        if self.process.is_alive():  # pragma: no cover - platform emergency path
            self.process.kill()
            self.process.join(timeout=1.0)
        self.process.close()


class IsolatedDoclingAdapter:
    """Rich parser adapter streaming bytes to one restricted spawned worker."""

    def __init__(
        self,
        *,
        limits: RichParserLimits | None = None,
        model_root: Path | None = None,
        model_manifest: ModelBundleManifest | None = None,
        _worker_behavior: _WorkerBehavior | None = None,
    ) -> None:
        """Validate configuration before granting a worker any provider authority."""
        selected_limits = limits or RichParserLimits()
        if (model_root is None) != (model_manifest is None):
            raise RichParserModelAssetsInvalid("rich parser model assets invalid")
        validated_root: Path | None = None
        if model_root is not None and model_manifest is not None:
            from openardp.adapters.docling_native import validate_model_bundle

            validated_root = validate_model_bundle(model_root, model_manifest)
        from openardp.adapters.docling_native import build_docling_recipe

        self._recipe = build_docling_recipe(
            limits=selected_limits,
            model_bundle_id=(model_manifest.bundle_id if model_manifest is not None else None),
        )
        self._limits = selected_limits
        self._config = _WorkerConfig(
            limits_json=selected_limits.model_dump_json(),
            model_root=str(validated_root) if validated_root is not None else None,
            model_manifest_json=(
                model_manifest.model_dump_json() if model_manifest is not None else None
            ),
        )
        self._worker_behavior = _worker_behavior or _parse_worker_behavior

    @property
    def recipe(self) -> RichParserRecipe:
        """Return the exact recipe used by the spawned worker."""
        return self._recipe

    def supports(self, media_type: str) -> bool:
        """Return whether media belongs to the closed F007 allowlist."""
        return media_type in {item.value for item in RichMediaType}

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> RichParseOutput:
        """Stream source bytes through bounded IPC and validate the complete result."""
        if not self.supports(media_type):
            raise UnsupportedRichMedia("unsupported rich media")
        selected_media = RichMediaType(media_type)
        if selected_media is RichMediaType.PDF and self._config.model_root is None:
            raise RichParserModelAssetsRequired("rich parser model assets required")

        context = multiprocessing.get_context("spawn")
        child_input, parent_input = context.Pipe(duplex=False)
        parent_result, child_result = context.Pipe(duplex=False)
        process = context.Process(
            target=_worker_entry,
            args=(
                child_input,
                child_result,
                self._config,
                self._limits.timeout_seconds,
                self._worker_behavior,
            ),
            daemon=True,
        )
        process.start()
        child_input.close()
        child_result.close()
        parent_input.send((_MESSAGE_MEDIA, media_type))
        sender_failures: queue.SimpleQueue[str] = queue.SimpleQueue()
        sender = threading.Thread(
            target=_send_chunks,
            args=(parent_input, chunks, sender_failures),
            name="openardp-docling-input",
            daemon=True,
        )
        sender.start()

        with _WorkerGuard(process, parent_input, parent_result) as worker:
            try:
                if not worker.result_receiver.poll(self._limits.timeout_seconds):
                    raise ParserTimedOut("parser timed out")
                try:
                    message = worker.result_receiver.recv()
                except (EOFError, OSError) as error:
                    raise ParserProcessCrashed("parser process crashed") from error
                sender.join(timeout=0.25)
                if not sender_failures.empty():
                    raise ParserProcessCrashed("parser input stream failed")
                return _decode_worker_result(message)
            except KeyboardInterrupt as error:
                raise RichParserCancelled("rich parser cancelled") from error

    def resolve(
        self,
        native_document: dict[str, object],
        *,
        pointer: str,
    ) -> object:
        """Resolve one adapter-issued pointer without importing Docling."""
        from openardp.adapters.docling_native import resolve_json_pointer

        return resolve_json_pointer(
            cast("dict[str, JsonValue]", native_document),
            pointer,
            max_resolved_bytes=self._limits.max_retrieval_body_bytes,
        )


def _send_chunks(
    connection: _IpcConnection,
    chunks: Iterable[bytes],
    failures: queue.SimpleQueue[str],
) -> None:
    try:
        for chunk in chunks:
            if not isinstance(chunk, bytes):
                failures.put("invalid_chunk")
                break
            connection.send((_MESSAGE_CHUNK, chunk))
        connection.send((_MESSAGE_END, b""))
    except (BrokenPipeError, EOFError, OSError):
        failures.put("ipc_closed")
    except Exception:
        failures.put("input_stream_failed")


def _worker_entry(
    input_receiver: _IpcConnection,
    result_sender: _IpcConnection,
    config: _WorkerConfig,
    timeout_seconds: float,
    behavior: _WorkerBehavior,
) -> None:
    """Apply offline/resource restrictions before importing provider behavior."""
    cache_root: Path | None = None
    try:
        cache_root = Path(tempfile.mkdtemp(prefix="openardp-docling-cache-"))
        _apply_offline_environment(cache_root)
        _apply_thread_environment()
        _apply_resource_limits(config, timeout_seconds)
        _disable_network_access()
        behavior(input_receiver, result_sender, config)
    except BaseException:
        _safe_send(result_sender, (_RESULT_ERROR, "worker_failed"))
    finally:
        input_receiver.close()
        result_sender.close()
        if cache_root is not None:
            shutil.rmtree(cache_root, ignore_errors=True)


def _parse_worker_behavior(
    input_receiver: _IpcConnection,
    result_sender: _IpcConnection,
    config: _WorkerConfig,
) -> None:
    """Import and execute the optional provider only after child restrictions."""
    try:
        limits = RichParserLimits.model_validate_json(config.limits_json)
        media_type = RichMediaType(_receive_media_type(input_receiver))
        source_bytes = b"".join(
            _receive_chunks(
                input_receiver,
                max_source_bytes=limits.max_source_bytes,
            )
        )
        manifest = (
            ModelBundleManifest.model_validate_json(config.model_manifest_json)
            if config.model_manifest_json is not None
            else None
        )
        from openardp.adapters.docling_native import convert_docling_bytes

        result = convert_docling_bytes(
            source_bytes,
            media_type=media_type,
            limits=limits,
            model_root=Path(config.model_root) if config.model_root is not None else None,
            model_manifest=manifest,
        )
    except ParserError as error:
        _safe_send(result_sender, (_RESULT_ERROR, _parser_error_code(error)))
        return
    except (ValidationError, ValueError):
        _safe_send(result_sender, (_RESULT_ERROR, "invalid_output"))
        return
    _safe_send(result_sender, (_RESULT_OK, result.model_dump_json()))


def _receive_media_type(input_receiver: _IpcConnection) -> str:
    message = input_receiver.recv()
    if (
        not isinstance(message, tuple)
        or len(message) != 2
        or message[0] != _MESSAGE_MEDIA
        or not isinstance(message[1], str)
    ):
        raise InvalidRichParserOutput("rich parser input protocol invalid")
    return message[1]


def _receive_chunks(
    input_receiver: _IpcConnection,
    *,
    max_source_bytes: int,
) -> Iterator[bytes]:
    byte_length = 0
    while True:
        try:
            message = input_receiver.recv()
        except (EOFError, OSError) as error:
            raise ParserProcessCrashed("parser input stream closed") from error
        if not isinstance(message, tuple) or len(message) != 2:
            raise InvalidRichParserOutput("rich parser input protocol invalid")
        kind, payload = message
        if kind == _MESSAGE_END:
            return
        if kind != _MESSAGE_CHUNK or not isinstance(payload, bytes):
            raise InvalidRichParserOutput("rich parser input protocol invalid")
        byte_length += len(payload)
        if byte_length > max_source_bytes:
            raise RichParserResourceLimitExceeded("rich parser resource limit exceeded")
        yield payload


def _safe_send(connection: _IpcConnection, message: tuple[str, str]) -> None:
    try:
        connection.send(message)
    except (BrokenPipeError, EOFError, OSError):
        return


def _decode_worker_result(message: object) -> RichParseOutput:
    if not isinstance(message, tuple) or len(message) != 2:
        raise InvalidRichParserOutput("rich parser output invalid")
    kind, payload = message
    if not isinstance(kind, str) or not isinstance(payload, str):
        raise InvalidRichParserOutput("rich parser output invalid")
    if kind == _RESULT_ERROR:
        raise _error_from_code(payload)
    if kind != _RESULT_OK:
        raise InvalidRichParserOutput("rich parser output invalid")
    try:
        return RichParseOutput.model_validate_json(payload)
    except ValidationError as error:
        raise InvalidRichParserOutput("rich parser output invalid") from error


def _parser_error_code(error: ParserError) -> str:
    if isinstance(error, UnsupportedRichMedia):
        return "unsupported_media"
    if isinstance(error, RichParserDependencyUnavailable):
        return "dependency_unavailable"
    if isinstance(error, RichParserModelAssetsRequired):
        return "model_assets_required"
    if isinstance(error, RichParserModelAssetsInvalid):
        return "model_assets_invalid"
    if isinstance(error, RichParserMalformedDocument):
        return "malformed_document"
    if isinstance(error, RichParserPartialConversion):
        return "partial_conversion"
    if isinstance(error, RichParserNetworkDenied):
        return "network_denied"
    if isinstance(error, RichParserResourceLimitExceeded):
        return "resource_limit"
    if isinstance(error, RichParserCancelled):
        return "cancelled"
    if isinstance(error, InvalidRichParserOutput):
        return "invalid_output"
    return "worker_failed"


def _error_from_code(code: str) -> ParserError:
    errors: dict[str, ParserError] = {
        "unsupported_media": UnsupportedRichMedia("unsupported rich media"),
        "dependency_unavailable": RichParserDependencyUnavailable(
            "rich parser dependency unavailable"
        ),
        "model_assets_required": RichParserModelAssetsRequired("rich parser model assets required"),
        "model_assets_invalid": RichParserModelAssetsInvalid("rich parser model assets invalid"),
        "malformed_document": RichParserMalformedDocument("rich parser document malformed"),
        "partial_conversion": RichParserPartialConversion("rich parser partial conversion"),
        "network_denied": RichParserNetworkDenied("rich parser network denied"),
        "resource_limit": RichParserResourceLimitExceeded("rich parser resource limit exceeded"),
        "cancelled": RichParserCancelled("rich parser cancelled"),
        "invalid_output": InvalidRichParserOutput("rich parser output invalid"),
        "worker_failed": ParserProcessCrashed("parser process crashed"),
    }
    try:
        return errors[code]
    except KeyError as error:
        raise InvalidRichParserOutput("rich parser output invalid") from error


def _apply_offline_environment(cache_root: Path) -> None:
    """Force common provider/model clients into explicit offline operation."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HOME"] = str(cache_root / "huggingface")
    os.environ["HF_HUB_CACHE"] = str(cache_root / "huggingface" / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(cache_root / "huggingface" / "transformers")
    os.environ["XDG_CACHE_HOME"] = str(cache_root / "xdg")


# Numeric libraries size per-thread buffers from the host core count at import time.
# The reviewed provider profile already runs inference on one CPU thread, so pinning
# every BLAS/OpenMP pool to one thread keeps worker memory independent of the host.
_SINGLE_THREAD_ENVIRONMENT = (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def _apply_thread_environment() -> None:
    """Pin numeric thread pools before any provider import sizes its buffers."""
    for name in _SINGLE_THREAD_ENVIRONMENT:
        os.environ[name] = "1"


def _memory_limit_resource(resource_module: object, platform: str) -> int | None:
    """Select the kernel limit that bounds actual worker memory on this platform.

    Linux counts reserved but unused address space in RLIMIT_AS; GPU-enabled numeric
    runtimes reserve several GiB they never touch. RLIMIT_DATA bounds private writable
    memory instead, so it still stops runaway allocations without rejecting imports.
    """
    names = ("RLIMIT_DATA", "RLIMIT_AS") if platform.startswith("linux") else ("RLIMIT_AS",)
    for name in names:
        value = getattr(resource_module, name, None)
        if isinstance(value, int):
            return value
    return None


def _disable_network_access() -> None:
    def blocked(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("network access disabled")

    socket.socket = _BlockedSocket  # type: ignore[misc,assignment]
    socket.create_connection = blocked
    socket.socketpair = blocked
    if hasattr(socket, "fromfd"):
        socket.fromfd = blocked


def _apply_resource_limits(config: _WorkerConfig, timeout_seconds: float) -> None:
    if sys.platform == "win32":
        return
    import resource

    limits = RichParserLimits.model_validate_json(config.limits_json)
    desired: list[tuple[int, int]] = [
        (resource.RLIMIT_CPU, max(1, math.ceil(timeout_seconds) + 1)),
        (resource.RLIMIT_NOFILE, limits.max_open_files),
    ]
    memory_resource = _memory_limit_resource(resource, sys.platform)
    if memory_resource is not None:
        desired.append((memory_resource, limits.max_address_space_bytes))
    for resource_kind, soft_limit in desired:
        try:
            _, hard_limit = resource.getrlimit(resource_kind)
            bounded = (
                soft_limit if hard_limit == resource.RLIM_INFINITY else min(soft_limit, hard_limit)
            )
            resource.setrlimit(resource_kind, (bounded, hard_limit))
        except (OSError, ValueError):
            continue


__all__ = ["IsolatedDoclingAdapter"]
