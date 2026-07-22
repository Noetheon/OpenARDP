"""Killable spawned-process boundary for the built-in text parser."""

from __future__ import annotations

import math
import multiprocessing
import queue
import socket
import sys
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from multiprocessing.process import BaseProcess
from types import TracebackType
from typing import NoReturn, Protocol, Self

from pydantic import ValidationError

from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.ingestion import (
    DEFAULT_PARSER_TIMEOUT_SECONDS,
    MAX_LINE_CHARACTERS,
    MAX_NORMALIZED_BLOCKS,
    MAX_SOURCE_BYTES,
    ParsedTextDocument,
    ParserRecipe,
)
from openardp.ports.parser import (
    InvalidParserOutput,
    ParserError,
    ParserProcessCrashed,
    ParserTimedOut,
    TextDecodingError,
    TextResourceLimitExceeded,
    UnsafeTextContent,
    UnsupportedTextMedia,
)

_MESSAGE_CHUNK = "chunk"
_MESSAGE_END = "end"
_RESULT_OK = "ok"
_RESULT_ERROR = "error"


class _IpcConnection(Protocol):
    """Cross-platform structural subset shared by Connection and PipeConnection."""

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
    profile: str
    max_source_bytes: int
    max_line_characters: int
    max_blocks: int


_WorkerBehavior = Callable[[_IpcConnection, _IpcConnection, _WorkerConfig], None]


class _WorkerGuard:
    """Own one child process and its IPC handles through deterministic cleanup."""

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
        """Return the active worker resources."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close IPC and guarantee that the child no longer runs."""
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


class IsolatedParserAdapter:
    """Product parser adapter that streams bytes to a spawned bounded worker."""

    def __init__(
        self,
        *,
        profile: str = "default",
        max_source_bytes: int = MAX_SOURCE_BYTES,
        max_line_characters: int = MAX_LINE_CHARACTERS,
        max_blocks: int = MAX_NORMALIZED_BLOCKS,
        timeout_seconds: float = DEFAULT_PARSER_TIMEOUT_SECONDS,
        _worker_behavior: _WorkerBehavior | None = None,
    ) -> None:
        """Configure a recipe-identical worker and its wall-clock deadline."""
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        parser = TextParserAdapter(
            profile=profile,
            max_source_bytes=max_source_bytes,
            max_line_characters=max_line_characters,
            max_blocks=max_blocks,
        )
        self._recipe = parser.recipe
        self._config = _WorkerConfig(
            profile=profile,
            max_source_bytes=max_source_bytes,
            max_line_characters=max_line_characters,
            max_blocks=max_blocks,
        )
        self._timeout_seconds = timeout_seconds
        self._worker_behavior = _worker_behavior or _parse_worker_behavior

    @property
    def recipe(self) -> ParserRecipe:
        """Return the exact recipe used inside the worker."""
        return self._recipe

    def supports(self, media_type: str) -> bool:
        """Return whether the built-in worker accepts the media type."""
        return media_type in {"text/plain", "text/markdown"}

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument:
        """Stream bytes through bounded IPC and return strictly validated output."""
        if not self.supports(media_type):
            raise UnsupportedTextMedia("unsupported text media")
        context = multiprocessing.get_context("spawn")
        child_input, parent_input = context.Pipe(duplex=False)
        parent_result, child_result = context.Pipe(duplex=False)
        process = context.Process(
            target=_worker_entry,
            args=(
                child_input,
                child_result,
                self._config,
                media_type,
                self._timeout_seconds,
                self._worker_behavior,
            ),
            daemon=True,
        )
        process.start()
        child_input.close()
        child_result.close()
        parent_input.send(("media_type", media_type))
        sender_failures: queue.SimpleQueue[str] = queue.SimpleQueue()
        sender = threading.Thread(
            target=_send_chunks,
            args=(parent_input, chunks, sender_failures),
            name="openardp-parser-input",
            daemon=True,
        )
        sender.start()

        with _WorkerGuard(process, parent_input, parent_result) as worker:
            if not worker.result_receiver.poll(self._timeout_seconds):
                raise ParserTimedOut("parser timed out")
            try:
                message = worker.result_receiver.recv()
            except (EOFError, OSError) as error:
                raise ParserProcessCrashed("parser process crashed") from error
            sender.join(timeout=0.25)
            if not sender_failures.empty():
                raise ParserProcessCrashed("parser input stream failed")
            return _decode_worker_result(message)


def _send_chunks(
    connection: _IpcConnection,
    chunks: Iterable[bytes],
    failures: queue.SimpleQueue[str],
) -> None:
    """Feed bounded IPC without allowing a blocked child to block the caller thread."""
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
    media_type: str,
    timeout_seconds: float,
    behavior: _WorkerBehavior,
) -> None:
    """Apply child restrictions before delegating to the selected worker behavior."""
    try:
        _apply_resource_limits(timeout_seconds)
        _disable_network_access()
        behavior(input_receiver, result_sender, config)
    except BaseException:
        _safe_send(result_sender, (_RESULT_ERROR, "worker_failed"))
    finally:
        input_receiver.close()
        result_sender.close()


def _parse_worker_behavior(
    input_receiver: _IpcConnection,
    result_sender: _IpcConnection,
    config: _WorkerConfig,
) -> None:
    """Run the pure parser against the parent-provided byte-message stream."""
    parser = TextParserAdapter(
        profile=config.profile,
        max_source_bytes=config.max_source_bytes,
        max_line_characters=config.max_line_characters,
        max_blocks=config.max_blocks,
    )
    try:
        result = parser.parse(
            _receive_chunks(input_receiver),
            media_type=_receive_media_type(input_receiver),
        )
    except ParserError as error:
        _safe_send(result_sender, (_RESULT_ERROR, _parser_error_code(error)))
        return
    _safe_send(result_sender, (_RESULT_OK, result.model_dump_json()))


def _receive_media_type(input_receiver: _IpcConnection) -> str:
    """Read the leading media declaration from the worker stream."""
    message = input_receiver.recv()
    if (
        not isinstance(message, tuple)
        or len(message) != 2
        or message[0] != "media_type"
        or not isinstance(message[1], str)
    ):
        raise InvalidParserOutput("parser input protocol invalid")
    return message[1]


def _receive_chunks(input_receiver: _IpcConnection) -> Iterator[bytes]:
    """Yield only well-formed byte messages from the parent."""
    while True:
        try:
            message = input_receiver.recv()
        except (EOFError, OSError) as error:
            raise ParserProcessCrashed("parser input stream closed") from error
        if not isinstance(message, tuple) or len(message) != 2:
            raise InvalidParserOutput("parser input protocol invalid")
        kind, payload = message
        if kind == _MESSAGE_END:
            return
        if kind != _MESSAGE_CHUNK or not isinstance(payload, bytes):
            raise InvalidParserOutput("parser input protocol invalid")
        yield payload


def _safe_send(connection: _IpcConnection, message: tuple[str, str]) -> None:
    """Best-effort send a body-free worker result."""
    try:
        connection.send(message)
    except (BrokenPipeError, EOFError, OSError):
        return


def _decode_worker_result(message: object) -> ParsedTextDocument:
    """Validate the narrow child result protocol and strict domain payload."""
    if not isinstance(message, tuple) or len(message) != 2:
        raise InvalidParserOutput("parser output invalid")
    kind, payload = message
    if not isinstance(kind, str) or not isinstance(payload, str):
        raise InvalidParserOutput("parser output invalid")
    if kind == _RESULT_ERROR:
        raise _error_from_code(payload)
    if kind != _RESULT_OK:
        raise InvalidParserOutput("parser output invalid")
    try:
        return ParsedTextDocument.model_validate_json(payload)
    except ValidationError as error:
        raise InvalidParserOutput("parser output invalid") from error


def _parser_error_code(error: ParserError) -> str:
    """Map a typed parser failure to one body-free machine code."""
    if isinstance(error, UnsupportedTextMedia):
        return "unsupported_media"
    if isinstance(error, TextDecodingError):
        return "decoding_failed"
    if isinstance(error, UnsafeTextContent):
        return "unsafe_content"
    if isinstance(error, TextResourceLimitExceeded):
        return "resource_limit"
    return "parser_failed"


def _error_from_code(code: str) -> ParserError:
    """Reconstitute only reviewed public parser error classes."""
    errors: dict[str, ParserError] = {
        "unsupported_media": UnsupportedTextMedia("unsupported text media"),
        "decoding_failed": TextDecodingError("text decoding failed"),
        "unsafe_content": UnsafeTextContent("unsafe text content"),
        "resource_limit": TextResourceLimitExceeded("text resource limit exceeded"),
        "worker_failed": ParserProcessCrashed("parser process crashed"),
        "parser_failed": ParserProcessCrashed("parser process failed"),
    }
    try:
        return errors[code]
    except KeyError as error:
        raise InvalidParserOutput("parser output invalid") from error


def _disable_network_access() -> None:
    """Deny socket construction inside the parser process."""

    def blocked(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("network access disabled")

    socket.socket = blocked  # type: ignore[misc,assignment]
    socket.create_connection = blocked


def _apply_resource_limits(timeout_seconds: float) -> None:
    """Apply portable parser bounds plus POSIX defense in depth when available."""
    if sys.platform == "win32":
        return

    import resource

    desired: list[tuple[int, int]] = [
        (resource.RLIMIT_CPU, max(1, math.ceil(timeout_seconds) + 1)),
        (resource.RLIMIT_NOFILE, 32),
    ]
    if hasattr(resource, "RLIMIT_AS"):
        desired.append((resource.RLIMIT_AS, 1024 * 1024 * 1024))
    for resource_kind, soft_limit in desired:
        try:
            _, hard_limit = resource.getrlimit(resource_kind)
            bounded = (
                soft_limit
                if hard_limit == resource.RLIM_INFINITY
                else min(
                    soft_limit,
                    hard_limit,
                )
            )
            resource.setrlimit(resource_kind, (bounded, hard_limit))
        except (OSError, ValueError):
            continue


__all__ = ["IsolatedParserAdapter"]
