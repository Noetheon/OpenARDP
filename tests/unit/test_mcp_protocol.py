"""Pure bounded MCP stdio protocol codec tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.adapters.local_workspace import WorkspaceError
from openardp.domain.search import SearchQueryRejected
from openardp.interfaces.mcp_protocol import (
    DEFAULT_DEADLINE_MS,
    DEFAULT_RESPONSE_CAP_BYTES,
    MAX_DEADLINE_MS,
    MAX_LINE_BYTES,
    MAX_RESPONSE_CAP_BYTES,
    MCP_ERROR_VERSION,
    MCP_INTERFACE_VERSION,
    MIN_DEADLINE_MS,
    MIN_RESPONSE_CAP_BYTES,
    PROTOCOL_REVISION,
    SERVER_NAME,
    TOOL_DESCRIPTORS,
    TOOL_NAMES,
    CancellationRegistry,
    LineBuffer,
    McpErrorCategory,
    McpFailure,
    Notification,
    Request,
    RequestDeadline,
    SessionLifecycle,
    SessionLimits,
    SessionState,
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
from openardp.ports.catalog import (
    AmbiguousBlock,
    BlockNotFound,
    DocumentNotFound,
    RepresentationConflict,
    RepresentationIntegrityError,
    RepresentationNotFound,
    SearchIndexDrifted,
)
from openardp.ports.context import (
    CancellationCheck,
    ContextCompilationCancelled,
    ContextConfigurationMismatch,
    ContextIntegrityFailure,
    ContextLimitExceeded,
    ContextNotFound,
)
from openardp.ports.object_store import ObjectStoreError

EXPECTED_TOOL_ORDER = (
    "list_documents",
    "get_source_status",
    "get_document_outline",
    "get_block",
    "search_document",
    "list_evidence",
    "get_evidence",
    "compile_context",
    "get_context_receipt",
)

EXPECTED_DEFAULT_CODES = {
    McpErrorCategory.INVALID_REQUEST: -32600,
    McpErrorCategory.UNSUPPORTED_PROTOCOL_VERSION: -32602,
    McpErrorCategory.UNKNOWN_TOOL: -32602,
    McpErrorCategory.INVALID_PARAMS: -32602,
    McpErrorCategory.NOT_FOUND: -32000,
    McpErrorCategory.CONFLICT: -32001,
    McpErrorCategory.INTEGRITY_OR_WORKSPACE: -32002,
    McpErrorCategory.CANCELLED: -32003,
    McpErrorCategory.DEADLINE_EXCEEDED: -32004,
    McpErrorCategory.INTERNAL: -32603,
}


def _failure(category: McpErrorCategory, code: int) -> None:
    raise AssertionError(f"unreachable {category} {code}")


# T007 — bounded newline framing reader


def test_line_buffer_returns_complete_lines_without_terminator() -> None:
    """Split newline-delimited frames while preserving buffered fragments."""
    buffer = LineBuffer()
    assert buffer.feed(b'{"a":1}\n{"b":2}\n') == (b'{"a":1}', b'{"b":2}')
    assert buffer.feed(b"") == ()


def test_line_buffer_stitches_fragmented_frames() -> None:
    """Reassemble one message split across arbitrary feed boundaries."""
    buffer = LineBuffer()
    assert buffer.feed(b'{"split"') == ()
    assert buffer.feed(b":true}\n") == (b'{"split":true}',)
    assert buffer.close() == b""


def test_line_buffer_accepts_line_at_exact_cap() -> None:
    """Accept a complete line whose bytes including terminator equal the cap."""
    payload = b'{"pad":"' + b"x" * (MAX_LINE_BYTES - 1 - len(b'{"pad":""}')) + b'"}'
    assert len(payload) == MAX_LINE_BYTES - 1
    assert LineBuffer().feed(payload + b"\n") == (payload,)


def test_line_buffer_rejects_one_byte_over_cap() -> None:
    """Fail one oversized message with a stable framing category."""
    buffer = LineBuffer()
    with pytest.raises(McpFailure) as captured:
        buffer.feed(b"x" * MAX_LINE_BYTES)
    assert captured.value.category is McpErrorCategory.INVALID_REQUEST
    assert captured.value.jsonrpc_code == -32600


def test_line_buffer_rejects_completed_line_over_cap() -> None:
    """Fail a newline-terminated message whose complete line exceeds the cap."""
    buffer = LineBuffer()
    with pytest.raises(McpFailure) as captured:
        buffer.feed(b"x" * MAX_LINE_BYTES + b"\n")
    assert captured.value.category is McpErrorCategory.INVALID_REQUEST


def test_line_buffer_reports_partial_message_on_eof() -> None:
    """Return leftover bytes at EOF so the caller can discard them cleanly."""
    buffer = LineBuffer()
    assert buffer.feed(b'{"truncated"') == ()
    assert buffer.close() == b'{"truncated"'
    assert buffer.feed(b'{"after":1}\n') == (b'{"after":1}',)


# T008 — single-object JSON-RPC envelope validation


def test_decode_message_accepts_one_json_object() -> None:
    """Decode exactly one JSON object per line."""
    message = decode_message(b'{"jsonrpc":"2.0","id":1,"method":"ping"}')
    assert message["method"] == "ping"


@pytest.mark.parametrize(
    "line",
    (
        b"not json",
        b"[1,2]",
        b'"scalar"',
        b"42",
        b"null",
        b'{"a":1}\xef\xbf',
    ),
)
def test_decode_message_rejects_non_object_and_malformed_input(line: bytes) -> None:
    """Reject batch arrays, scalars, malformed JSON and truncated UTF-8."""
    with pytest.raises(McpFailure) as captured:
        decode_message(line)
    assert captured.value.category is McpErrorCategory.INVALID_REQUEST


def test_decode_message_rejects_oversized_line() -> None:
    """Apply the byte cap defensively at decode time as well."""
    with pytest.raises(McpFailure):
        decode_message(b'{"pad":"' + b"x" * MAX_LINE_BYTES + b'"}')


def test_parse_envelope_shapes_requests_and_notifications() -> None:
    """Distinguish requests with identifiers from identifier-free notifications."""
    request = parse_envelope({"jsonrpc": "2.0", "id": "abc", "method": "tools/list"})
    assert isinstance(request, Request)
    assert request.request_id == "abc"
    numeric = parse_envelope({"jsonrpc": "2.0", "id": 7, "method": "ping"})
    assert isinstance(numeric, Request)
    assert numeric.request_id == 7
    notification = parse_envelope({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert isinstance(notification, Notification)


@pytest.mark.parametrize(
    "message",
    (
        {"id": 1, "method": "ping"},
        {"jsonrpc": "1.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1},
        {"jsonrpc": "2.0", "id": 1, "method": ""},
        {"jsonrpc": "2.0", "id": 1, "method": 42},
        {"jsonrpc": "2.0", "id": 1, "method": "x" * 129},
        {"jsonrpc": "2.0", "id": True, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1.5, "method": "ping"},
        {"jsonrpc": "2.0", "id": None, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1]},
    ),
)
def test_parse_envelope_rejects_invalid_envelopes(message: dict[str, object]) -> None:
    """Reject wrong versions, missing or malformed methods, ids and params."""
    with pytest.raises(McpFailure) as captured:
        parse_envelope(message)
    assert captured.value.category is McpErrorCategory.INVALID_REQUEST


def test_encode_message_is_canonical_single_line_json() -> None:
    """Serialize deterministic sorted compact JSON with one trailing newline."""
    payload = {"b": [2, 1], "a": {"z": "é\n汉"}}
    encoded = encode_message(payload)
    assert encoded.endswith(b"\n")
    assert encoded.count(b"\n") == 1
    body = encoded[:-1].decode("utf-8")
    assert body == json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert encode_message(payload) == encoded


def test_encode_message_fails_closed_on_raw_newline_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the single-line framing invariant enforced if serialization drifts."""
    monkeypatch.setattr(json, "dumps", lambda *args, **kwargs: '{"a":1}\n{"b":2}')
    with pytest.raises(McpFailure) as captured:
        encode_message({"a": 1})
    assert captured.value.category is McpErrorCategory.INTERNAL


# T009 — pinned-revision lifecycle state machine


def _initialize_params(revision: str = PROTOCOL_REVISION) -> dict[str, object]:
    return {
        "protocolVersion": revision,
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    }


def test_initialize_handshake_reports_identity_and_tools_only() -> None:
    """Answer initialize with pinned revision, identity and tools-only capabilities."""
    lifecycle = SessionLifecycle()
    assert lifecycle.state is SessionState.START
    result = lifecycle.initialize(_initialize_params())
    assert lifecycle.state is SessionState.INITIALIZING
    assert result["protocolVersion"] == PROTOCOL_REVISION
    server_info = result["serverInfo"]
    assert server_info == {"name": SERVER_NAME, "version": MCP_INTERFACE_VERSION}
    assert set(result["capabilities"]) == {"tools"}


def test_initialize_rejects_other_revisions_and_missing_version() -> None:
    """Fail closed on revision mismatch with the stable version category."""
    lifecycle = SessionLifecycle()
    with pytest.raises(McpFailure) as captured:
        lifecycle.initialize(_initialize_params("2024-11-05"))
    assert captured.value.category is McpErrorCategory.UNSUPPORTED_PROTOCOL_VERSION
    with pytest.raises(McpFailure) as missing:
        lifecycle.initialize({"capabilities": {}})
    assert missing.value.category is McpErrorCategory.INVALID_REQUEST
    with pytest.raises(McpFailure):
        lifecycle.initialize(None)
    assert lifecycle.state is SessionState.START


def test_tool_calls_require_completed_initialization() -> None:
    """Reject tool access before the initialized notification arrives."""
    lifecycle = SessionLifecycle()
    with pytest.raises(McpFailure) as captured:
        lifecycle.require_ready()
    assert captured.value.category is McpErrorCategory.INVALID_REQUEST
    lifecycle.initialize(_initialize_params())
    with pytest.raises(McpFailure):
        lifecycle.require_ready()
    lifecycle.notify_initialized()
    assert lifecycle.state is SessionState.READY
    lifecycle.require_ready()


def test_lifecycle_rejects_out_of_order_transitions() -> None:
    """Fail a second initialize and an unexpected initialized notification."""
    lifecycle = SessionLifecycle()
    with pytest.raises(McpFailure):
        lifecycle.notify_initialized()
    lifecycle.initialize(_initialize_params())
    with pytest.raises(McpFailure) as captured:
        lifecycle.initialize(_initialize_params())
    assert captured.value.category is McpErrorCategory.INVALID_REQUEST
    lifecycle.notify_initialized()
    lifecycle.close()
    assert lifecycle.state is SessionState.CLOSED


def test_ping_is_answered_in_every_state() -> None:
    """Keep ping available before, during and after initialization."""
    lifecycle = SessionLifecycle()
    assert lifecycle.ping() == {}
    lifecycle.initialize(_initialize_params())
    assert lifecycle.ping() == {}
    lifecycle.notify_initialized()
    assert lifecycle.ping() == {}


# T010 — versioned error taxonomy and sanitized envelopes


def test_every_category_has_fixed_message_and_default_code() -> None:
    """Pin the complete taxonomy to the reviewed contract table."""
    assert set(EXPECTED_DEFAULT_CODES) == set(McpErrorCategory)
    assert len(McpErrorCategory) == 10
    for category, code in EXPECTED_DEFAULT_CODES.items():
        failure = McpFailure(category)
        assert failure.jsonrpc_code == code
        assert failure.message
        assert failure.category.value in failure.message or failure.message.islower()


def test_error_envelope_shape_is_versioned_and_body_free() -> None:
    """Serialize one stable versioned error envelope per failure."""
    envelope = error_result("req-1", McpFailure(McpErrorCategory.NOT_FOUND))
    assert envelope["jsonrpc"] == "2.0"
    assert envelope["id"] == "req-1"
    error = envelope["error"]
    assert error["code"] == -32000
    assert error["data"] == {
        "mcp_error_version": MCP_ERROR_VERSION,
        "category": "not_found",
    }
    assert MCP_ERROR_VERSION == 1
    unknown_id = error_result(None, McpFailure(McpErrorCategory.INVALID_REQUEST))
    assert unknown_id["id"] is None


@pytest.mark.parametrize(
    ("error", "category"),
    (
        (SearchQueryRejected("zyq-marker"), McpErrorCategory.INVALID_PARAMS),
        (ContextLimitExceeded("zyq-marker"), McpErrorCategory.INVALID_PARAMS),
        (ValueError("zyq-marker"), McpErrorCategory.INVALID_PARAMS),
        (DocumentNotFound("zyq-marker"), McpErrorCategory.NOT_FOUND),
        (RepresentationNotFound("zyq-marker"), McpErrorCategory.NOT_FOUND),
        (BlockNotFound("zyq-marker"), McpErrorCategory.NOT_FOUND),
        (ContextNotFound("zyq-marker"), McpErrorCategory.NOT_FOUND),
        (AmbiguousBlock("zyq-marker"), McpErrorCategory.CONFLICT),
        (RepresentationConflict("zyq-marker"), McpErrorCategory.CONFLICT),
        (ContextConfigurationMismatch("zyq-marker"), McpErrorCategory.CONFLICT),
        (RepresentationIntegrityError("zyq-marker"), McpErrorCategory.INTEGRITY_OR_WORKSPACE),
        (SearchIndexDrifted("zyq-marker"), McpErrorCategory.INTEGRITY_OR_WORKSPACE),
        (ObjectStoreError("zyq-marker"), McpErrorCategory.INTEGRITY_OR_WORKSPACE),
        (WorkspaceError("zyq-marker"), McpErrorCategory.INTEGRITY_OR_WORKSPACE),
        (ContextIntegrityFailure("zyq-marker"), McpErrorCategory.INTEGRITY_OR_WORKSPACE),
        (ContextCompilationCancelled("zyq-marker"), McpErrorCategory.CANCELLED),
        (RuntimeError("zyq-marker"), McpErrorCategory.INTERNAL),
    ),
)
def test_service_failures_map_to_documented_categories(
    error: Exception,
    category: McpErrorCategory,
) -> None:
    """Map every service failure family to exactly one taxonomy category."""
    failure = map_service_error(error)
    assert failure.category is category
    assert "zyq-marker" not in failure.message


def test_error_envelopes_match_committed_golden_fixture(repository_root: Path) -> None:
    """Prove byte-stable taxonomy output against the reviewed fixture."""
    fixture_path = repository_root / "tests" / "fixtures" / "mcp" / "error-envelopes.json"
    golden = json.loads(fixture_path.read_text(encoding="utf-8"))
    for category in McpErrorCategory:
        envelope = error_result(1, McpFailure(category))
        assert envelope["error"] == golden[category.value]


# T011 — fixed tool descriptors and deterministic tools/list


def test_tool_surface_is_exactly_the_nine_contract_tools() -> None:
    """Publish exactly nine read-only tools in canonical contract order."""
    assert tuple(descriptor.name for descriptor in TOOL_DESCRIPTORS) == EXPECTED_TOOL_ORDER
    assert frozenset(EXPECTED_TOOL_ORDER) == TOOL_NAMES


def test_every_descriptor_declares_bounds_and_untrusted_notice() -> None:
    """Require version, closed input schema, bounds and the data-only notice."""
    for descriptor in TOOL_DESCRIPTORS:
        assert descriptor.interface_version == MCP_INTERFACE_VERSION
        assert "untrusted" in descriptor.description.casefold()
        assert "read-only" in descriptor.description.casefold()
        schema = descriptor.input_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert isinstance(schema["properties"], dict)
        bounds = descriptor.output_bounds
        assert bounds
        assert all(isinstance(value, int | str | bool) for value in bounds.values())


def test_require_tool_returns_descriptor_or_stable_unknown_category() -> None:
    """Resolve known tools and fail unknown names with one stable category."""
    descriptor = require_tool("compile_context")
    assert descriptor.name == "compile_context"
    assert descriptor.interface_version == "0.2.0"
    assert descriptor.input_schema["properties"]["retrieval_profile"] == {
        "type": "string",
        "enum": ["lexical", "semantic"],
    }
    with pytest.raises(McpFailure) as captured:
        require_tool("delete_document")
    assert captured.value.category is McpErrorCategory.UNKNOWN_TOOL
    assert captured.value.jsonrpc_code == -32602


def test_parse_tool_call_validates_envelope_and_arguments() -> None:
    """Extract bounded tool name and object arguments from call params."""
    name, arguments = parse_tool_call({"name": "list_documents"})
    assert name == "list_documents"
    assert arguments == {}
    name, arguments = parse_tool_call({"name": "get_block", "arguments": {"block_id": "x"}})
    assert arguments == {"block_id": "x"}
    for params in (None, {}, {"name": 7}, {"name": "get_block", "arguments": [1]}):
        with pytest.raises(McpFailure) as captured:
            parse_tool_call(params)
        assert captured.value.category is McpErrorCategory.INVALID_REQUEST
        assert captured.value.jsonrpc_code == -32602


def test_tools_list_result_is_deterministic_and_matches_golden(repository_root: Path) -> None:
    """Pin descriptor bytes against the reviewed canonical fixture."""
    first = encode_message(tools_list_result())
    again = encode_message(tools_list_result())
    assert first == again
    fixture_path = repository_root / "tests" / "fixtures" / "mcp" / "tools-list.json"
    assert first[:-1] == fixture_path.read_bytes()


# T012 — session limits, deadlines and cooperative cancellation


def test_session_limits_enforce_documented_ranges() -> None:
    """Bound deadline and response cap to the published configuration range."""
    limits = SessionLimits()
    assert limits.deadline_ms == DEFAULT_DEADLINE_MS
    assert limits.response_cap_bytes == DEFAULT_RESPONSE_CAP_BYTES
    assert limits.max_line_bytes == MAX_LINE_BYTES
    SessionLimits(deadline_ms=MIN_DEADLINE_MS, response_cap_bytes=MAX_RESPONSE_CAP_BYTES)
    SessionLimits(deadline_ms=MAX_DEADLINE_MS, response_cap_bytes=MIN_RESPONSE_CAP_BYTES)
    for invalid in (
        {"deadline_ms": MIN_DEADLINE_MS - 1},
        {"deadline_ms": MAX_DEADLINE_MS + 1},
        {"response_cap_bytes": MIN_RESPONSE_CAP_BYTES - 1},
        {"response_cap_bytes": MAX_RESPONSE_CAP_BYTES + 1},
        {"max_line_bytes": MAX_LINE_BYTES + 1},
    ):
        with pytest.raises(ValidationError):
            SessionLimits(**invalid)


def test_response_cap_admits_exact_fit_and_rejects_overflow() -> None:
    """Measure the complete serialized response against the configured cap."""
    limits = SessionLimits(response_cap_bytes=MIN_RESPONSE_CAP_BYTES)
    assert ensure_within_response_cap(b"x" * MIN_RESPONSE_CAP_BYTES, limits) is not None
    with pytest.raises(McpFailure) as captured:
        ensure_within_response_cap(b"x" * (MIN_RESPONSE_CAP_BYTES + 1), limits)
    assert captured.value.category is McpErrorCategory.INVALID_PARAMS


def test_request_deadline_uses_injected_monotonic_clock() -> None:
    """Expire deterministically at the declared deadline without wall-clock sleeps."""
    now = [100.0]
    deadline = RequestDeadline(1_000, clock=lambda: now[0])
    assert not deadline.is_expired
    assert deadline.remaining_ms == 1_000
    deadline.check()
    now[0] += 0.5
    assert deadline.elapsed_ms == 500
    assert deadline.remaining_ms == 500
    now[0] += 0.5
    assert deadline.is_expired
    assert deadline.remaining_ms == 0
    with pytest.raises(McpFailure) as captured:
        deadline.check()
    assert captured.value.category is McpErrorCategory.DEADLINE_EXCEEDED
    assert captured.value.jsonrpc_code == -32004


def test_cancellation_registry_tracks_named_requests_only() -> None:
    """Cancel one request without affecting others or unknown identifiers."""
    registry = CancellationRegistry()
    registry.begin("req-1")
    registry.cancel("req-1")
    registry.cancel("unknown")
    assert registry.is_cancelled("req-1")
    assert not registry.is_cancelled("req-2")
    assert not registry.is_cancelled("unknown")
    with pytest.raises(McpFailure) as captured:
        registry.check("req-1")
    assert captured.value.category is McpErrorCategory.CANCELLED
    assert captured.value.jsonrpc_code == -32003
    registry.check("req-2")
    registry.finish("req-1")
    assert not registry.is_cancelled("req-1")


def test_cancellation_registry_can_unwind_all_active_requests() -> None:
    """Cancel all and only active requests during a bounded-session shutdown."""
    registry = CancellationRegistry()
    registry.begin("req-1")
    registry.begin("req-2")
    registry.cancel_all()
    assert registry.is_cancelled("req-1")
    assert registry.is_cancelled("req-2")
    assert not registry.is_cancelled("unknown")


def test_cancellation_bridge_feeds_the_compiler_port() -> None:
    """Expose one cooperative cancellation check honoring flag and deadline."""
    now = [0.0]
    registry = CancellationRegistry()
    registry.begin("req-1")
    deadline = RequestDeadline(1_000, clock=lambda: now[0])
    check = registry.cancellation_check("req-1", deadline)
    assert isinstance(check, CancellationCheck)
    assert check() is False
    registry.cancel("req-1")
    assert check() is True
    registry.finish("req-1")
    assert check() is False
    now[0] = 2.0
    assert check() is True


def test_success_result_envelope_echoes_request_identity() -> None:
    """Serialize success envelopes with the exact request identifier."""
    envelope = success_result(9, {"tools": []})
    assert envelope == {"jsonrpc": "2.0", "id": 9, "result": {"tools": []}}


def test_failure_messages_are_fixed_and_never_echo_input() -> None:
    """Construct failures without accepting attacker-controlled message text."""
    failure = McpFailure(McpErrorCategory.NOT_FOUND)
    again = McpFailure(McpErrorCategory.NOT_FOUND)
    assert failure.message == again.message
    assert failure.args == ()
