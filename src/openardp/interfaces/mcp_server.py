"""Least-privilege read-only MCP stdio session loop and tool dispatch.

The server composes the pure protocol codec with the existing verified application
services. It owns framing, lifecycle, deadlines, cancellation, argument validation,
untrusted-content envelopes, response caps and body-free audit records; it contains
no selection, verification or persistence logic and never resolves a client-supplied
filesystem path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from queue import Full, Queue
from threading import Thread
from typing import Any, BinaryIO
from uuid import UUID

from pydantic import JsonValue

from openardp.adapters.context_estimators import BUILT_IN_ESTIMATORS
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompileRequest,
    ContextEvidenceItem,
    ContextSelectionPolicy,
    EstimatorIdentity,
    UntrustedContentEnvelope,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.interfaces.mcp_protocol import (
    METHOD_INITIALIZE,
    METHOD_NOTIFICATION_CANCELLED,
    METHOD_NOTIFICATION_INITIALIZED,
    METHOD_PING,
    METHOD_TOOLS_CALL,
    METHOD_TOOLS_LIST,
    CancellationRegistry,
    LineBuffer,
    McpErrorCategory,
    McpFailure,
    Notification,
    Request,
    RequestDeadline,
    SessionLifecycle,
    SessionLimits,
    ToolDescriptor,
    decode_message,
    encode_message,
    ensure_within_response_cap,
    error_result,
    map_service_error,
    parse_envelope,
    parse_tool_call,
    require_tool,
    success_result,
    tools_list_result,
)
from openardp.ports.context import (
    CancellationCheck,
    ContextCompilationCancelled,
    ContextEstimator,
)
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.rich_evidence import RichEvidenceService
from openardp.services.search import SearchService

_LOGGER = logging.getLogger("openardp.mcp")

MAX_LIST_ITEMS = 256
MAX_OUTLINE_ITEMS = 1_000
MAX_EVIDENCE_ITEMS = 256
MAX_BODY_BYTES = 262_144
_READ_CHUNK_BYTES = 65_536
_MAX_PENDING_FRAMES = 64

_UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_SHA256_ID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ServerCaps:
    """Documented per-tool output bounds; overridable only for boundary tests."""

    list_items: int = MAX_LIST_ITEMS
    outline_items: int = MAX_OUTLINE_ITEMS
    evidence_items: int = MAX_EVIDENCE_ITEMS
    body_bytes: int = MAX_BODY_BYTES


AuditSink = Callable[[Mapping[str, JsonValue]], None]
ToolHandler = Callable[[dict[str, JsonValue], RequestDeadline, CancellationCheck], dict[str, Any]]
CompilerFactory = Callable[[ContextEstimator], ContextCompilerService]


def _default_audit(record: Mapping[str, JsonValue]) -> None:
    """Write one body-free structured audit record to the server log."""
    _LOGGER.info(
        "%s",
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def _bounded_page(items: Sequence[Any], cap: int) -> tuple[Sequence[Any], bool]:
    """Return one deterministic page and the explicit truncation flag."""
    return items[:cap], len(items) > cap


def _untrusted_envelope(body: str, caps: ServerCaps) -> dict[str, Any]:
    """Wrap one verified body in the structural data-only envelope, never truncated."""
    if len(body.encode("utf-8")) > caps.body_bytes:
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    envelope = UntrustedContentEnvelope(media_type="text/plain", body=body)
    return envelope.model_dump(mode="json")


def _validate_value(spec: Mapping[str, JsonValue], value: JsonValue) -> None:
    """Validate one argument value against its bounded schema fragment."""
    expected = spec.get("type")
    if expected == "string":
        if not isinstance(value, str):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        min_length = spec.get("minLength")
        max_length = spec.get("maxLength")
        if isinstance(min_length, int) and len(value) < min_length:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        if isinstance(max_length, int) and len(value) > max_length:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        if "\x00" in value or "\n" in value or "\r" in value:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        pattern = spec.get("pattern")
        if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        enum = spec.get("enum")
        if isinstance(enum, list) and value not in enum:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        return
    if expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        minimum = spec.get("minimum")
        maximum = spec.get("maximum")
        if isinstance(minimum, int) and value < minimum:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        if isinstance(maximum, int) and value > maximum:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        return
    if expected == "boolean":
        if not isinstance(value, bool):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        return
    if expected == "array":
        if not isinstance(value, list):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        min_items = spec.get("minItems")
        max_items = spec.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        if isinstance(max_items, int) and len(value) > max_items:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        if spec.get("uniqueItems") is True:
            serialized = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(set(serialized)) != len(serialized):
                raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        item_spec = spec.get("items")
        if isinstance(item_spec, dict):
            for item in value:
                _validate_value(item_spec, item)
        return
    raise McpFailure(McpErrorCategory.INVALID_PARAMS)


def _validate_arguments(
    descriptor: ToolDescriptor,
    arguments: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    """Validate a closed bounded argument set before any service reach."""
    schema = descriptor.input_schema
    properties = schema["properties"]
    required = schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise McpFailure(McpErrorCategory.INTERNAL)
    unknown = set(arguments) - set(properties)
    missing = set(required) - set(arguments)
    if unknown or missing:
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    for key, value in arguments.items():
        spec = properties[key]
        if not isinstance(spec, dict):
            raise McpFailure(McpErrorCategory.INTERNAL)
        _validate_value(spec, value)
    return arguments


def _uuid_value(value: JsonValue) -> UUID:
    """Return one validated UUID value without any path interpretation."""
    if not isinstance(value, str) or _UUID_PATTERN.fullmatch(value) is None:
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    return UUID(value)


def _uuid_argument(arguments: Mapping[str, JsonValue], name: str) -> UUID:
    """Return one validated UUID argument without any path interpretation."""
    return _uuid_value(arguments[name])


def _optional_version(arguments: Mapping[str, JsonValue]) -> str | None:
    """Return the optional exact version identifier in stored digest form."""
    value = arguments.get("version_id")
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256_ID_PATTERN.fullmatch(value) is None:
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    return value


def _optional_str(arguments: Mapping[str, JsonValue], name: str) -> str | None:
    """Return one optional bounded string argument after schema validation."""
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    return value


def _optional_int(arguments: Mapping[str, JsonValue], name: str) -> int | None:
    """Return one optional bounded integer argument after schema validation."""
    value = arguments.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    return value


def _required_str(arguments: Mapping[str, JsonValue], name: str) -> str:
    """Return one required string argument after schema validation."""
    value = arguments[name]
    if not isinstance(value, str):
        raise McpFailure(McpErrorCategory.INVALID_PARAMS)
    return value


def _estimator_for_unit(unit: str) -> ContextEstimator:
    """Resolve one exact built-in estimator for the enum-bounded unit name."""
    for estimator in BUILT_IN_ESTIMATORS:
        if estimator.identity.unit.value == unit:
            return estimator
    raise McpFailure(McpErrorCategory.INVALID_PARAMS)


def _check_bundle_item_caps(
    items: tuple[ContextEvidenceItem, ...],
    caps: ServerCaps,
) -> None:
    """Fail closed when one opted-in bundle item body exceeds the body cap."""
    for item in items:
        if item.content is None:
            continue
        body = item.content.body
        size = (
            len(body.encode("utf-8")) if isinstance(body, str) else len(canonical_json_bytes(body))
        )
        if size > caps.body_bytes:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)


class McpServer:
    """One single-user read-only MCP session over the pinned protocol codec."""

    def __init__(
        self,
        document_query: DocumentQueryService,
        rich_evidence: RichEvidenceService,
        *,
        search: SearchService,
        compiler_factory: CompilerFactory,
        semantic_compiler_factory: CompilerFactory | None = None,
        limits: SessionLimits | None = None,
        caps: ServerCaps | None = None,
        clock: Callable[[], float] = time.monotonic,
        audit: AuditSink | None = None,
    ) -> None:
        """Compose the session over existing verified read-only services."""
        self._query = document_query
        self._rich_evidence = rich_evidence
        self._search = search
        self._compiler_factory = compiler_factory
        self._semantic_compiler_factory = semantic_compiler_factory
        self._semantic_compiler_slot: tuple[EstimatorIdentity, ContextCompilerService] | None = None
        self._limits = limits if limits is not None else SessionLimits()
        self._caps = caps if caps is not None else ServerCaps()
        self._clock = clock
        self._audit = audit if audit is not None else _default_audit
        self._lifecycle = SessionLifecycle()
        self._registry = CancellationRegistry()
        self._dispatch: dict[str, ToolHandler] = {
            "list_documents": self._list_documents,
            "get_source_status": self._get_source_status,
            "get_document_outline": self._get_document_outline,
            "get_block": self._get_block,
            "search_document": self._search_document,
            "list_evidence": self._list_evidence,
            "get_evidence": self._get_evidence,
            "compile_context": self._compile_context,
            "get_context_receipt": self._get_context_receipt,
        }

    @property
    def lifecycle(self) -> SessionLifecycle:
        """Return the session lifecycle for state inspection."""
        return self._lifecycle

    def handle_line(self, line: bytes) -> bytes | None:
        """Process one inbound payload line and return the response, if any."""
        try:
            envelope = parse_envelope(decode_message(line))
        except McpFailure as failure:
            return encode_message(error_result(None, failure))
        if isinstance(envelope, Notification):
            self._handle_notification(envelope)
            return None
        self._registry.begin(envelope.request_id)
        return self._handle_request(envelope)

    def serve(self, source: BinaryIO, sink: BinaryIO) -> int:
        """Serve frames while reading cancellation notifications concurrently."""
        inbound: Queue[bytes | McpFailure | None] = Queue(maxsize=_MAX_PENDING_FRAMES)

        def _enqueue(item: bytes | McpFailure) -> bool:
            try:
                inbound.put_nowait(item)
            except Full:
                self._registry.cancel_all()
                inbound.put(McpFailure(McpErrorCategory.INVALID_REQUEST))
                return False
            return True

        def _read_input() -> None:
            buffer = LineBuffer(self._limits.max_line_bytes)
            while True:
                chunk = source.read(_READ_CHUNK_BYTES)
                if not chunk:
                    break
                try:
                    lines = buffer.feed(chunk)
                except McpFailure as failure:
                    if not _enqueue(failure):
                        inbound.put(None)
                        return
                    buffer = LineBuffer(self._limits.max_line_bytes)
                    continue
                for line in lines:
                    if self._consume_concurrent_cancellation(line):
                        continue
                    self._register_queued_request(line)
                    if not _enqueue(line):
                        inbound.put(None)
                        return
            buffer.close()
            inbound.put(None)

        reader = Thread(target=_read_input, name="openardp-mcp-stdin", daemon=True)
        reader.start()
        while True:
            item = inbound.get()
            if item is None:
                break
            response = (
                encode_message(error_result(None, item))
                if isinstance(item, McpFailure)
                else self.handle_line(item)
            )
            if response is not None:
                sink.write(response)
                sink.flush()
        reader.join()
        self._lifecycle.close()
        return 0

    def _consume_concurrent_cancellation(self, line: bytes) -> bool:
        """Consume one valid cancellation notification on the reader thread."""
        try:
            envelope = parse_envelope(decode_message(line))
        except McpFailure:
            return False
        if not isinstance(envelope, Notification):
            return False
        if envelope.method != METHOD_NOTIFICATION_CANCELLED:
            return False
        self._record_cancellation(envelope.params)
        return True

    def _register_queued_request(self, line: bytes) -> None:
        """Make a queued request cancellable before dispatch begins."""
        try:
            envelope = parse_envelope(decode_message(line))
        except McpFailure:
            return
        if isinstance(envelope, Request):
            self._registry.begin(envelope.request_id)

    def _handle_notification(self, notification: Notification) -> None:
        """Process lifecycle and cancellation notifications without a response."""
        try:
            if notification.method == METHOD_NOTIFICATION_INITIALIZED:
                self._lifecycle.notify_initialized()
            elif notification.method == METHOD_NOTIFICATION_CANCELLED:
                self._record_cancellation(notification.params)
        except McpFailure:
            # Notifications carry no response channel; the session stays usable.
            _LOGGER.debug("discarded invalid notification")

    def _record_cancellation(self, params: Mapping[str, JsonValue] | None) -> None:
        """Record cooperative cancellation for one named request identifier."""
        if params is None:
            return
        request_id = params.get("requestId")
        if isinstance(request_id, bool):
            return
        if isinstance(request_id, str | int):
            self._registry.cancel(request_id)

    def _handle_request(self, request: Request) -> bytes:
        """Dispatch one request with deadline, cancellation and sanitized errors."""
        deadline = RequestDeadline(self._limits.deadline_ms, clock=self._clock)
        started = self._clock()
        tool_name: str | None = None
        semantic_compilation = False
        try:
            if request.method == METHOD_INITIALIZE:
                result = self._lifecycle.initialize(request.params)
            elif request.method == METHOD_PING:
                result = self._lifecycle.ping()
            elif request.method == METHOD_TOOLS_LIST:
                self._lifecycle.require_ready()
                result = tools_list_result()
            elif request.method == METHOD_TOOLS_CALL:
                self._lifecycle.require_ready()
                tool_name, raw_arguments = parse_tool_call(request.params)
                descriptor = require_tool(tool_name)
                # The dispatch covers the complete published tool set; a missing
                # entry would reduce to the sanitized internal category below.
                handler = self._dispatch[tool_name]
                arguments = _validate_arguments(descriptor, raw_arguments)
                semantic_compilation = (
                    tool_name == "compile_context"
                    and arguments.get("retrieval_profile") == "semantic"
                )
                deadline.check()
                self._registry.check(request.request_id)
                cancel = self._registry.cancellation_check(request.request_id, deadline)
                result = handler(arguments, deadline, cancel)
                deadline.check()
                self._registry.check(request.request_id)
            else:
                raise McpFailure(McpErrorCategory.INVALID_REQUEST, jsonrpc_code=-32601)
            encoded = ensure_within_response_cap(
                encode_message(success_result(request.request_id, result)),
                self._limits,
            )
            self._emit_audit(tool_name or request.method, request.request_id, "ok", started)
            self._registry.finish(request.request_id)
            return encoded
        except McpFailure as failure:
            if semantic_compilation:
                self._semantic_compiler_slot = None
            self._emit_audit(
                tool_name or request.method,
                request.request_id,
                failure.category.value,
                started,
            )
            self._registry.finish(request.request_id)
            return encode_message(error_result(request.request_id, failure))
        except Exception as error:
            if semantic_compilation:
                self._semantic_compiler_slot = None
            mapped = (
                McpFailure(McpErrorCategory.DEADLINE_EXCEEDED)
                if isinstance(error, ContextCompilationCancelled) and deadline.is_expired
                else map_service_error(error)
            )
            self._emit_audit(
                tool_name or request.method,
                request.request_id,
                mapped.category.value,
                started,
            )
            self._registry.finish(request.request_id)
            return encode_message(error_result(request.request_id, mapped))

    def _emit_audit(
        self,
        tool: str,
        request_id: str | int,
        outcome: str,
        started: float,
    ) -> None:
        """Emit one body-free audit record with digests, codes and timings."""
        digest = hashlib.sha256(str(request_id).encode("utf-8")).hexdigest()
        record: dict[str, JsonValue] = {
            "tool": tool,
            "request_id_digest": f"sha256:{digest}",
            "outcome": outcome,
            "duration_ms": max(0, int((self._clock() - started) * 1_000)),
        }
        self._audit(record)

    def _list_documents(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return bounded body-free document summaries."""
        del arguments, deadline, cancel
        summaries = self._query.list_documents()
        page, truncated = _bounded_page(summaries, self._caps.list_items)
        return {
            "documents": [summary.model_dump(mode="json") for summary in page],
            "returned": len(page),
            "available": len(summaries),
            "truncated": truncated,
        }

    def _get_source_status(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return identifier-scoped freshness without any path target."""
        del deadline, cancel
        document_id = _uuid_argument(arguments, "document_id")
        status = self._query.status(str(document_id))
        return status.model_dump(mode="json")

    def _get_document_outline(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return bounded structural outline items for one exact document."""
        del deadline, cancel
        document_id = _uuid_argument(arguments, "document_id")
        version_id = _optional_version(arguments)
        outline = self._query.outline(document_id, version_id=version_id)
        page, truncated = _bounded_page(outline, self._caps.outline_items)
        return {
            "items": [item.model_dump(mode="json") for item in page],
            "returned": len(page),
            "available": len(outline),
            "truncated": truncated,
        }

    def _get_block(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return one verified block with its body inside the data envelope."""
        del deadline, cancel
        block_id = _uuid_argument(arguments, "block_id")
        block = self._query.get(block_id)
        projected = block.model_dump(mode="json")
        projected["text"] = _untrusted_envelope(block.text or "", self._caps)
        return projected

    def _search_document(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return verified hits with enveloped snippets and no query echo."""
        del deadline, cancel
        document_id = (
            str(_uuid_argument(arguments, "document_id")) if "document_id" in arguments else None
        )
        outcome = self._search.search(
            _required_str(arguments, "query"),
            document=document_id,
            version_id=_optional_str(arguments, "version_id"),
            kind=_optional_str(arguments, "kind"),
            trust=_optional_str(arguments, "trust"),
            page=_optional_int(arguments, "page"),
            slide=_optional_int(arguments, "slide"),
            limit=_optional_int(arguments, "limit"),
        )
        return {
            "hits": [
                {
                    **hit.model_dump(mode="json", exclude={"snippet"}),
                    "snippet": _untrusted_envelope(hit.snippet, self._caps),
                }
                for hit in outcome.hits
            ],
            "returned": outcome.returned,
            "available": outcome.available,
            "truncated": outcome.truncated,
        }

    def _list_evidence(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return bounded body-free accepted rich evidence for one document."""
        del deadline, cancel
        document_id = _uuid_argument(arguments, "document_id")
        version_id = _optional_version(arguments)
        projections = self._rich_evidence.list(document_id, version_id=version_id)
        page, truncated = _bounded_page(projections, self._caps.evidence_items)
        return {
            "projections": [item.model_dump(mode="json") for item in page],
            "returned": len(page),
            "available": len(projections),
            "truncated": truncated,
        }

    def _get_evidence(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return one verified rich body inside the data-only envelope."""
        del deadline, cancel
        projection_id = arguments["evidence_projection_id"]
        if not isinstance(projection_id, str):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        document: UUID | None = None
        if "document_id" in arguments:
            document = _uuid_argument(arguments, "document_id")
        retrieved = self._rich_evidence.get(projection_id, document_id=document)
        return {
            "projection": retrieved.projection.model_dump(mode="json"),
            "body": _untrusted_envelope(retrieved.body, self._caps),
        }

    def _compile_context(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Compile via the exact F008 path and return handles first."""
        del deadline
        raw_ids = arguments["document_ids"]
        budget_limit = arguments["budget_limit"]
        if not isinstance(raw_ids, list) or isinstance(budget_limit, bool):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        if not isinstance(budget_limit, int):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        document_ids = tuple(sorted({_uuid_value(value) for value in raw_ids}, key=str))
        mode_value = _optional_str(arguments, "mode") or "mixed"
        include_bundle = arguments.get("include_bundle", False)
        if not isinstance(include_bundle, bool):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        try:
            mode = ContextMode(mode_value)
        except ValueError as error:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS) from error
        estimator = _estimator_for_unit(_required_str(arguments, "unit"))
        request = ContextCompileRequest(
            task=_required_str(arguments, "task"),
            document_ids=document_ids,
            budget_limit=budget_limit,
            estimator=estimator.identity,
            # The local single-owner server admits every sensitivity of the
            # owner's own corpus and records the classified trust body-free,
            # exactly like the CLI path; instruction execution stays disabled
            # structurally for every selected body.
            policy=ContextSelectionPolicy(
                mode=mode,
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
        )
        retrieval_profile = _optional_str(arguments, "retrieval_profile") or "lexical"
        if retrieval_profile == "lexical":
            compiler = self._compiler_factory(estimator)
        elif retrieval_profile == "semantic":
            compiler = self._semantic_compiler(estimator)
        else:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        persisted = compiler.compile_and_persist(request, cancel=cancel)
        result = persisted.result
        receipt = result.receipt
        summary: dict[str, Any] = {
            "bundle_id": str(result.bundle.bundle_id),
            "receipt_id": receipt.receipt_id,
            "persisted": True,
            "created_at": receipt.model_dump(mode="json")["created_at"],
            "mode": receipt.policy.mode.value,
            "estimator": receipt.estimator.model_dump(mode="json"),
            "scopes": [scope.model_dump(mode="json") for scope in receipt.corpus_snapshot],
            "budget": receipt.budget.model_dump(mode="json"),
            "counts": {
                "selected": len(receipt.selected),
                "omitted": len(receipt.omitted),
                "rejected": len(receipt.rejected),
                "stale": len(receipt.stale),
            },
            "truncated": receipt.truncated,
            "notices": [notice.model_dump(mode="json") for notice in receipt.notices],
            "warnings": [warning.model_dump(mode="json") for warning in result.bundle.warnings],
            "missing_evidence": [
                missing.model_dump(mode="json") for missing in result.bundle.missing_evidence
            ],
        }
        if include_bundle:
            _check_bundle_item_caps(result.bundle.items, self._caps)
            summary["bundle"] = result.bundle.model_dump(mode="json")
        return summary

    def _semantic_compiler(self, estimator: ContextEstimator) -> ContextCompilerService:
        """Retain one disposable compiler for the complete estimator identity."""
        if self._semantic_compiler_factory is None:
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        slot = self._semantic_compiler_slot
        if slot is None or slot[0] != estimator.identity:
            self._semantic_compiler_slot = None
            compiler = self._semantic_compiler_factory(estimator)
            self._semantic_compiler_slot = (estimator.identity, compiler)
            return compiler
        return slot[1]

    def _get_context_receipt(
        self,
        arguments: dict[str, JsonValue],
        deadline: RequestDeadline,
        cancel: CancellationCheck,
    ) -> dict[str, Any]:
        """Return one receipt only after the complete verification chain."""
        del deadline, cancel
        receipt_id = arguments["receipt_id"]
        if not isinstance(receipt_id, str):
            raise McpFailure(McpErrorCategory.INVALID_PARAMS)
        compiler = self._compiler_factory(_estimator_for_unit("bytes"))
        result = compiler.load_verified(receipt_id)
        return result.receipt.model_dump(mode="json")


__all__ = [
    "MAX_BODY_BYTES",
    "MAX_EVIDENCE_ITEMS",
    "MAX_LIST_ITEMS",
    "MAX_OUTLINE_ITEMS",
    "AuditSink",
    "CompilerFactory",
    "McpServer",
    "ServerCaps",
]
