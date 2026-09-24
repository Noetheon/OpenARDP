"""Safe MCP session and read-only navigation tool tests."""

from __future__ import annotations

import io
import json
import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompileRequest,
    ContextSelectionPolicy,
)
from openardp.interfaces.cli import _context_summary, _json_value
from openardp.interfaces.mcp_protocol import (
    MAX_LINE_BYTES,
    MCP_INTERFACE_VERSION,
    PROTOCOL_REVISION,
    SERVER_NAME,
    McpErrorCategory,
    McpFailure,
    SessionLimits,
    ToolDescriptor,
)
from openardp.interfaces.mcp_server import (
    _MAX_PENDING_FRAMES,
    McpServer,
    ServerCaps,
    _check_bundle_item_caps,
    _default_audit,
    _estimator_for_unit,
    _optional_int,
    _optional_str,
    _optional_version,
    _required_str,
    _uuid_argument,
    _validate_arguments,
    _validate_value,
)
from openardp.ports.context import ContextCompilationCancelled, ContextEstimator
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.rich_evidence import RichEvidenceService
from openardp.services.rich_ingestion import RichIngestionService
from openardp.services.search import SearchService
from tests.integration.test_rich_ingestion import _Clock, _Parser, _TamperingStore
from tests.mcp_envelopes import tool_failure, unwrap_tool_result

RICH_BODY = "alpha rich evidence alpha"
UNKNOWN_UUID = "00000000-0000-4000-8000-000000000000"
UNKNOWN_UUID_V7 = "01890f62-24e8-7c00-8000-00000000dead"


class _Corpus:
    """One initialized workspace with text and rich evidence plus services."""

    def __init__(self, tmp_path: Path) -> None:
        self.store = tmp_path / "store"
        self.object_store = FilesystemObjectStore(self.store)
        self.catalog = SQLiteCatalog(self.store / "catalog.sqlite3")
        self.catalog.initialize(now=datetime.now(UTC))
        clock = _Clock()
        self.text_ingestion = IngestionService(
            self.object_store,
            self.catalog,
            TextParserAdapter(),
            source_factory=LocalSource,
            clock=clock,
        )
        self.text_path = tmp_path / "notes.md"
        self.text_path.write_text(
            "# alpha heading\n\nalpha text evidence alpha\n",
            encoding="utf-8",
        )
        text_result = self.text_ingestion.ingest(self.text_path)
        parser = _Parser()
        parser.text = RICH_BODY
        rich_ingestion = RichIngestionService(
            self.object_store,
            self.catalog,
            parser,
            source_factory=LocalSource,
            clock=clock,
            owner_id_factory=lambda: "mcp-worker",
            lease_token_factory=lambda: "mcp-capability-000000000000001",
            random_bits=lambda: 1,
        )
        rich_path = tmp_path / "report.docx"
        rich_path.write_bytes(b"report-v1")
        rich_result = rich_ingestion.ingest(rich_path)
        self.query = DocumentQueryService(
            self.object_store,
            self.catalog,
            source_factory=LocalSource,
            representation_verifier=self.text_ingestion.verify_ready_representation,
            clock=clock,
        )
        self.rich_evidence = RichEvidenceService(
            self.object_store,
            self.catalog,
            representation_verifier=rich_ingestion.verify_ready_representation,
        )
        self.search = SearchService(
            self.object_store,
            self.catalog,
            source_factory=LocalSource,
            clock=clock,
        )
        self._rich_verifier = rich_ingestion.verify_ready_representation
        self.text_document_id = text_result.scope.document_id
        self.rich_document_id = rich_result.scope.document_id

    def compiler_factory(self, estimator: ContextEstimator) -> ContextCompilerService:
        """Compose the exact F008 compiler for one request-scoped estimator."""
        return ContextCompilerService(
            self.object_store,
            self.catalog,
            estimator,
            (
                TextLexicalCandidateSource(self.object_store, self.catalog),
                RichLexicalCandidateSource(
                    self.object_store,
                    self.catalog,
                    representation_verifier=self._rich_verifier,
                ),
            ),
        )


def _server(corpus: _Corpus, **overrides: object) -> McpServer:
    """Compose one server with a deterministic injected clock."""
    clock_ticks = [1_000.0]

    def clock() -> float:
        clock_ticks[0] += 0.001
        return clock_ticks[0]

    chosen_clock = overrides.pop("clock", clock)
    chosen_audit = overrides.pop("audit", lambda record: None)
    chosen_search = overrides.pop("search", corpus.search)
    chosen_factory = overrides.pop("compiler_factory", corpus.compiler_factory)
    return McpServer(
        corpus.query,
        corpus.rich_evidence,
        search=chosen_search,  # type: ignore[arg-type]
        compiler_factory=chosen_factory,  # type: ignore[arg-type]
        clock=chosen_clock,  # type: ignore[arg-type]
        audit=chosen_audit,  # type: ignore[arg-type]
        **overrides,  # type: ignore[arg-type]
    )


class _CancellingCandidateSource:
    """Cancel one pinned request id mid-discovery, then delegate discovery."""

    def __init__(
        self,
        delegate: TextLexicalCandidateSource,
        server: McpServer,
        request_id: int,
    ) -> None:
        """Bind the delegate, the live session registry and the pinned id."""
        self._delegate = delegate
        self._server = server
        self._request_id = request_id

    def discover(
        self,
        task: str,
        snapshot: object,
        limits: object,
        cancel: object,
    ) -> object:
        """Record cancellation for the pinned request, then delegate exactly."""
        self._server._registry.cancel(self._request_id)
        return self._delegate.discover(task, snapshot, limits, cancel)  # type: ignore[arg-type]


def _line(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _request(
    method: str,
    params: dict[str, object] | None = None,
    *,
    request_id: int | str = 1,
) -> bytes:
    envelope: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        envelope["params"] = params
    return _line(envelope)


def _tool_call(
    name: str,
    arguments: dict[str, object] | None = None,
    *,
    request_id: int = 10,
) -> bytes:
    params: dict[str, object] = {"name": name}
    if arguments is not None:
        params["arguments"] = arguments
    return _request("tools/call", params, request_id=request_id)


def _initialize(server: McpServer) -> dict[str, object]:
    """Complete the handshake once and stay idempotent for later calls."""
    if server.lifecycle.state.value == "start":
        response = server.handle_line(
            _request(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_REVISION,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            )
        )
        assert response is not None
        envelope = json.loads(response)
        assert envelope.get("error") is None, envelope
        result: dict[str, object] = envelope["result"]
    else:
        result = {
            "protocolVersion": PROTOCOL_REVISION,
            "serverInfo": {"name": SERVER_NAME, "version": MCP_INTERFACE_VERSION},
            "capabilities": {"tools": {"listChanged": False}},
        }
    if server.lifecycle.state.value == "initializing":
        notification = server.handle_line(
            _line({"jsonrpc": "2.0", "method": "notifications/initialized"})
        )
        assert notification is None
    assert server.lifecycle.state.value == "ready"
    return result


def _call_tool(
    server: McpServer,
    name: str,
    arguments: dict[str, object] | None = None,
    *,
    request_id: int = 10,
) -> dict[str, object]:
    """Invoke one tool in a ready session and return the raw envelope."""
    _initialize(server)
    response = server.handle_line(_tool_call(name, arguments, request_id=request_id))
    assert response is not None
    envelope: dict[str, object] = json.loads(response)
    return envelope


def _result(envelope: dict[str, object]) -> dict[str, object]:
    assert "error" not in envelope, envelope.get("error")
    result = envelope["result"]
    assert isinstance(result, dict)
    return unwrap_tool_result(result)


def _error(envelope: dict[str, object]) -> dict[str, object]:
    error = tool_failure(envelope)
    assert isinstance(error, dict)
    return error


# T020 — session loop, handshake, shutdown


def test_handshake_reports_identity_and_tools_only(tmp_path: Path) -> None:
    """Complete the pinned handshake with server identity and tools capability."""
    server = _server(_Corpus(tmp_path))
    result = _initialize(server)
    assert result["protocolVersion"] == PROTOCOL_REVISION
    assert result["serverInfo"] == {"name": SERVER_NAME, "version": MCP_INTERFACE_VERSION}
    assert set(result["capabilities"]) == {"tools"}


def test_tool_calls_before_initialization_are_rejected(tmp_path: Path) -> None:
    """Fail tools/list and tools/call before the handshake completes."""
    server = _server(_Corpus(tmp_path))
    for payload in (_request("tools/list"), _tool_call("list_documents")):
        response = server.handle_line(payload)
        assert response is not None
        error = _error(json.loads(response))
        assert error["data"] == {"mcp_error_version": 1, "category": "invalid_request"}
    result = _initialize(server)
    assert result["protocolVersion"] == PROTOCOL_REVISION


def test_second_initialize_and_unknown_method_fail_stably(tmp_path: Path) -> None:
    """Reject a repeated handshake and unknown methods with stable codes."""
    server = _server(_Corpus(tmp_path))
    _initialize(server)
    repeated = server.handle_line(_request("initialize", {"protocolVersion": PROTOCOL_REVISION}))
    assert repeated is not None
    assert _error(json.loads(repeated))["data"]["category"] == "invalid_request"
    unknown = server.handle_line(_request("resources/list"))
    assert unknown is not None
    error = _error(json.loads(unknown))
    assert error["code"] == -32601
    assert error["data"]["category"] == "invalid_request"


def test_framing_failure_keeps_session_usable(tmp_path: Path) -> None:
    """Answer malformed lines with one stable error and keep serving."""
    server = _server(_Corpus(tmp_path))
    garbage = server.handle_line(b"not json at all")
    assert garbage is not None
    envelope = json.loads(garbage)
    assert envelope["id"] is None
    assert _error(envelope)["data"]["category"] == "invalid_request"
    batch = server.handle_line(b"[1,2,3]")
    assert batch is not None
    assert _error(json.loads(batch))["data"]["category"] == "invalid_request"
    result = _initialize(server)
    assert result["protocolVersion"] == PROTOCOL_REVISION


def test_serve_loop_exits_cleanly_on_eof_mid_message(tmp_path: Path) -> None:
    """Serve a full session from streams and discard a partial final frame."""
    server = _server(_Corpus(tmp_path))
    session = b"\n".join(
        [
            _request("initialize", {"protocolVersion": PROTOCOL_REVISION}),
            _line({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            _request("ping", request_id=2),
            b'{"jsonrpc":"2.0","id":3,"method":"ping"',
        ]
    )
    sink = io.BytesIO()
    assert server.serve(io.BytesIO(session), sink) == 0
    lines = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert len(lines) == 2
    assert lines[0]["result"]["protocolVersion"] == PROTOCOL_REVISION
    assert lines[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert server.lifecycle.state.value == "closed"


def test_tools_list_matches_contract_surface(tmp_path: Path) -> None:
    """Return the exact nine descriptor names in canonical order."""
    server = _server(_Corpus(tmp_path))
    _initialize(server)
    response = server.handle_line(_request("tools/list"))
    assert response is not None
    tools = _result(json.loads(response))["tools"]
    assert [tool["name"] for tool in tools] == [
        "list_documents",
        "get_source_status",
        "get_document_outline",
        "get_block",
        "search_document",
        "list_evidence",
        "get_evidence",
        "compile_context",
        "get_context_receipt",
    ]


# T021 — list_documents and identifier-only get_source_status


def test_list_documents_returns_bounded_body_free_summaries(tmp_path: Path) -> None:
    """List both registered documents without any body content."""
    corpus = _Corpus(tmp_path)
    result = _result(_call_tool(_server(corpus), "list_documents"))
    assert result["returned"] == 2
    assert result["available"] == 2
    assert result["truncated"] is False
    documents = result["documents"]
    assert isinstance(documents, list)
    identifiers = {item["document_id"] for item in documents}
    assert identifiers == {str(corpus.text_document_id), str(corpus.rich_document_id)}
    assert all("body" not in item and "text" not in item for item in documents)


def test_list_documents_truncates_explicitly_at_cap(tmp_path: Path) -> None:
    """Apply the documented list cap with an explicit truncation flag."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus, caps=ServerCaps(list_items=1))
    result = _result(_call_tool(server, "list_documents"))
    assert result["returned"] == 1
    assert result["available"] == 2
    assert result["truncated"] is True


def test_get_source_status_accepts_identifiers_only(tmp_path: Path) -> None:
    """Report freshness for a registered identifier and reject path input."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    result = _result(
        _call_tool(server, "get_source_status", {"document_id": str(corpus.text_document_id)})
    )
    assert result["freshness"] == "CURRENT"
    assert result["integrity_coverage"] == "HEAD"
    assert result["document_id"] == str(corpus.text_document_id)
    assert "checked_at" in result
    for hostile in ("/etc/passwd", "../store", str(corpus.text_path), "file:///x", "a" * 64):
        envelope = _call_tool(server, "get_source_status", {"document_id": hostile})
        error = _error(envelope)
        assert error["data"]["category"] == "invalid_params"
        assert hostile not in json.dumps(envelope)


def test_get_source_status_unknown_identifier_is_body_free(tmp_path: Path) -> None:
    """Answer an unknown but valid identifier without catalog detail."""
    corpus = _Corpus(tmp_path)
    result = _result(
        _call_tool(_server(corpus), "get_source_status", {"document_id": UNKNOWN_UUID})
    )
    assert result["freshness"] == "NOT_REGISTERED"
    assert result["integrity_coverage"] == "NONE"


# T022 — outline and enveloped get_block


def test_outline_returns_bounded_structural_items(tmp_path: Path) -> None:
    """Return the heading outline without any body text."""
    corpus = _Corpus(tmp_path)
    result = _result(
        _call_tool(
            _server(corpus),
            "get_document_outline",
            {"document_id": str(corpus.text_document_id)},
        )
    )
    assert result["returned"] >= 1
    assert result["truncated"] is False
    items = result["items"]
    assert isinstance(items, list)
    first = items[0]
    assert first["kind"] == "heading"
    assert "alpha heading" in first["label"]
    assert all("body" not in item and "text" not in item for item in items)


def test_outline_unknown_document_is_uniform_not_found(tmp_path: Path) -> None:
    """Map unknown outline targets to the uniform not-found envelope."""
    corpus = _Corpus(tmp_path)
    envelope = _call_tool(_server(corpus), "get_document_outline", {"document_id": UNKNOWN_UUID})
    error = _error(envelope)
    assert error["code"] == -32000
    assert error["data"] == {"mcp_error_version": 1, "category": "not_found"}
    assert error["message"] == "requested evidence was not found"


def test_get_block_returns_verified_body_inside_untrusted_envelope(tmp_path: Path) -> None:
    """Deliver exact block text only inside the structural data envelope."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    outline = _result(
        _call_tool(
            server,
            "get_document_outline",
            {"document_id": str(corpus.text_document_id)},
        )
    )
    items = outline["items"]
    assert isinstance(items, list)
    block_id = items[0]["block_id"]
    result = _result(_call_tool(server, "get_block", {"block_id": block_id}))
    assert result["block_id"] == block_id
    envelope = result["text"]
    assert envelope["content_role"] == "untrusted_data"
    assert envelope["delimiter"] == "openardp-evidence-v1"
    assert envelope["media_type"] == "text/plain"
    assert "alpha heading" in str(envelope["body"])


def test_get_block_rejects_malformed_and_unknown_identifiers(tmp_path: Path) -> None:
    """Fail malformed ids as invalid params and unknown ids as not found."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    malformed = _call_tool(server, "get_block", {"block_id": "../../etc/passwd"})
    assert _error(malformed)["data"]["category"] == "invalid_params"
    missing = _call_tool(server, "get_block", {"block_id": UNKNOWN_UUID})
    assert _error(missing)["data"]["category"] == "not_found"


def test_get_block_fails_closed_above_body_cap(tmp_path: Path) -> None:
    """Never truncate a body; fail oversized content with the stable category."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus, caps=ServerCaps(body_bytes=4))
    outline = _result(
        _call_tool(server, "get_document_outline", {"document_id": str(corpus.text_document_id)})
    )
    items = outline["items"]
    assert isinstance(items, list)
    block_id = items[0]["block_id"]
    envelope = _call_tool(server, "get_block", {"block_id": block_id})
    assert _error(envelope)["data"]["category"] == "invalid_params"


def test_outline_label_is_truncated_at_documented_bound(tmp_path: Path) -> None:
    """Bound outline labels to 512 characters inside the service contract."""
    corpus = _Corpus(tmp_path)
    long_heading = "# " + "z" * 600
    corpus.text_path.write_text(f"{long_heading}\n\nbody\n", encoding="utf-8")
    result = corpus.text_ingestion.ingest(corpus.text_path, force=True)
    outline = _result(
        _call_tool(
            _server(corpus),
            "get_document_outline",
            {"document_id": str(result.scope.document_id)},
        )
    )
    items = outline["items"]
    assert isinstance(items, list)
    assert all(len(item["label"]) <= 512 for item in items)


# T023 — rich evidence listing and enveloped verified retrieval


def test_list_evidence_returns_body_free_projections(tmp_path: Path) -> None:
    """List accepted rich evidence without retrieval bodies."""
    corpus = _Corpus(tmp_path)
    result = _result(
        _call_tool(_server(corpus), "list_evidence", {"document_id": str(corpus.rich_document_id)})
    )
    assert result["returned"] >= 1
    assert result["truncated"] is False
    projections = result["projections"]
    assert isinstance(projections, list)
    first = projections[0]
    assert first["evidence_projection_id"]
    assert "body" not in first


def test_get_evidence_returns_verified_body_inside_envelope(tmp_path: Path) -> None:
    """Retrieve the exact rich body only inside the untrusted envelope."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    listing = _result(
        _call_tool(server, "list_evidence", {"document_id": str(corpus.rich_document_id)})
    )
    projections = listing["projections"]
    assert isinstance(projections, list)
    projection_id = projections[0]["evidence_projection_id"]
    result = _result(_call_tool(server, "get_evidence", {"evidence_projection_id": projection_id}))
    projection = result["projection"]
    assert isinstance(projection, dict)
    assert projection["evidence_projection_id"] == projection_id
    envelope = result["body"]
    assert envelope["content_role"] == "untrusted_data"
    assert envelope["delimiter"] == "openardp-evidence-v1"
    assert envelope["body"] == RICH_BODY


def test_get_evidence_unknown_projection_is_not_found(tmp_path: Path) -> None:
    """Map unknown projections to the uniform not-found envelope."""
    corpus = _Corpus(tmp_path)
    envelope = _call_tool(
        _server(corpus),
        "get_evidence",
        {"evidence_projection_id": "evp_sha256:" + "0" * 64},
    )
    assert _error(envelope)["data"]["category"] == "not_found"


def test_get_evidence_ambiguity_maps_to_conflict(tmp_path: Path) -> None:
    """Map ambiguous evidence resolution to the stable conflict category."""
    from openardp.ports.catalog import RepresentationConflict

    class _AmbiguousEvidence:
        def list(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("unused in this test")

        def get(self, *args: object, **kwargs: object) -> object:
            raise RepresentationConflict("zyq-ambiguous")

    corpus = _Corpus(tmp_path)
    server = McpServer(
        corpus.query,
        _AmbiguousEvidence(),  # type: ignore[arg-type]
        search=corpus.search,
        compiler_factory=corpus.compiler_factory,
        audit=lambda record: None,
    )
    envelope = _call_tool(server, "get_evidence", {"evidence_projection_id": "evp_x"})
    error = _error(envelope)
    assert error["data"]["category"] == "conflict"
    assert "zyq-ambiguous" not in json.dumps(envelope)


# T025 — determinism modulo documented volatile fields


def _navigation_sequence(server: McpServer, corpus: _Corpus) -> list[bytes]:
    """Run one fixed navigation session and return every response line."""
    responses: list[bytes] = []
    _initialize(server)
    sequence = (
        _tool_call("list_documents", request_id=2),
        _tool_call(
            "get_document_outline",
            {"document_id": str(corpus.text_document_id)},
            request_id=3,
        ),
        _tool_call("list_evidence", {"document_id": str(corpus.rich_document_id)}, request_id=4),
    )
    for payload in sequence:
        response = server.handle_line(payload)
        assert response is not None
        responses.append(response)
    listing = unwrap_tool_result(json.loads(responses[-1])["result"])
    projection_id = listing["projections"][0]["evidence_projection_id"]
    final = server.handle_line(
        _tool_call("get_evidence", {"evidence_projection_id": projection_id}, request_id=5)
    )
    assert final is not None
    responses.append(final)
    return responses


def test_navigation_is_byte_identical_across_repeated_sessions(tmp_path: Path) -> None:
    """Prove twenty identical sessions produce byte-identical responses."""
    corpus = _Corpus(tmp_path)
    baseline: list[bytes] | None = None
    for _ in range(20):
        responses = _navigation_sequence(_server(corpus), corpus)
        if baseline is None:
            baseline = responses
        else:
            assert responses == baseline


def test_source_status_is_stable_modulo_checked_at(tmp_path: Path) -> None:
    """Keep the documented volatile observation timestamp the only difference."""
    corpus = _Corpus(tmp_path)
    seen: list[dict[str, object]] = []
    for _ in range(5):
        result = _result(
            _call_tool(
                _server(corpus),
                "get_source_status",
                {"document_id": str(corpus.text_document_id)},
            )
        )
        seen.append(dict(result))
    normalized = [{**entry, "checked_at": "volatile"} for entry in seen]
    assert all(entry == normalized[0] for entry in normalized)


# T031 — body-free structured audit logging and sanitized failures


def test_audit_records_contain_only_digests_codes_and_timings(tmp_path: Path) -> None:
    """Log tool, request-id digest, outcome and duration, never raw content."""
    corpus = _Corpus(tmp_path)
    records: list[dict[str, object]] = []
    server = McpServer(
        corpus.query,
        corpus.rich_evidence,
        search=corpus.search,
        compiler_factory=corpus.compiler_factory,
        audit=lambda record: records.append(dict(record)),
    )
    _call_tool(server, "get_source_status", {"document_id": str(corpus.text_document_id)})
    _call_tool(server, "get_block", {"block_id": "../hostile"}, request_id=11)
    assert len(records) == 3
    lifecycle, first, second = records
    assert lifecycle["tool"] == "initialize"
    assert lifecycle["outcome"] == "ok"
    assert first["tool"] == "get_source_status"
    assert first["outcome"] == "ok"
    assert isinstance(first["duration_ms"], int)
    digest = first["request_id_digest"]
    assert isinstance(digest, str)
    assert digest.startswith("sha256:")
    assert len(digest) == 71
    assert second["outcome"] == "invalid_params"
    serialized = json.dumps(records)
    assert "../hostile" not in serialized
    assert "alpha" not in serialized
    assert str(corpus.text_document_id) not in serialized


def test_unexpected_handler_failure_maps_to_internal(tmp_path: Path) -> None:
    """Reduce unclassified failures to the sanitized internal category."""

    class _ExplodingQuery:
        def list_documents(self) -> object:
            raise RuntimeError("zyq-secret-detail")

    corpus = _Corpus(tmp_path)
    server = McpServer(
        _ExplodingQuery(),  # type: ignore[arg-type]
        corpus.rich_evidence,
        search=corpus.search,
        compiler_factory=corpus.compiler_factory,
        audit=lambda record: None,
    )
    envelope = _call_tool(server, "list_documents")
    error = _error(envelope)
    assert error["code"] == -32603
    assert error["data"]["category"] == "internal"
    assert "zyq-secret-detail" not in json.dumps(envelope)


# T033-T036 — US2 search, compile and verified receipt


def test_search_document_returns_enveloped_hits_without_query_echo(tmp_path: Path) -> None:
    """Return verified hits with enveloped snippets and never re-broadcast the query."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    result = _result(_call_tool(server, "search_document", {"query": "alpha"}))
    assert result["returned"] >= 1
    assert result["available"] >= result["returned"]
    assert result["truncated"] is False
    assert "query_echo" not in result
    hits = result["hits"]
    assert isinstance(hits, list)
    for hit in hits:
        snippet = hit["snippet"]
        assert snippet["content_role"] == "untrusted_data"
        assert snippet["delimiter"] == "openardp-evidence-v1"
        assert "alpha" in snippet["body"].casefold()
    distinctive = "zyq-no-such-term probe"
    empty = _result(_call_tool(server, "search_document", {"query": distinctive}))
    assert empty["returned"] == 0
    assert distinctive not in json.dumps(empty)


def test_search_document_matches_service_parity_exactly(tmp_path: Path) -> None:
    """Match the CLI-facing SearchService outcome field for field."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    result = _result(
        _call_tool(
            server,
            "search_document",
            {"query": "alpha", "document_id": str(corpus.rich_document_id), "limit": 5},
        )
    )
    outcome = corpus.search.search(
        "alpha",
        document=str(corpus.rich_document_id),
        limit=5,
    )
    assert result["returned"] == outcome.returned
    assert result["available"] == outcome.available
    assert result["truncated"] == outcome.truncated
    hits = result["hits"]
    assert isinstance(hits, list)
    assert len(hits) == len(outcome.hits)
    for projected, hit in zip(hits, outcome.hits, strict=True):
        expected = hit.model_dump(mode="json", exclude={"snippet"})
        for key, value in expected.items():
            assert projected[key] == value
        assert projected["snippet"]["body"] == hit.snippet


def test_search_document_applies_bounded_filters(tmp_path: Path) -> None:
    """Apply kind, document and limit filters with explicit truncation."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    headings = _result(_call_tool(server, "search_document", {"query": "alpha", "kind": "heading"}))
    assert headings["returned"] >= 1
    heading_hits = headings["hits"]
    assert isinstance(heading_hits, list)
    assert all(hit["kind"] == "heading" for hit in heading_hits)
    limited = _result(_call_tool(server, "search_document", {"query": "alpha", "limit": 1}))
    assert limited["returned"] == 1
    assert limited["truncated"] is True
    assert limited["available"] > 1


def test_search_document_rejects_invalid_and_unknown_scope(tmp_path: Path) -> None:
    """Map filter rejection and unknown documents to stable body-free errors."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    unknown = _call_tool(server, "search_document", {"query": "alpha", "document_id": UNKNOWN_UUID})
    assert _error(unknown)["data"]["category"] == "not_found"
    bad_kind = _call_tool(server, "search_document", {"query": "alpha", "kind": "zyq"})
    assert _error(bad_kind)["data"]["category"] == "invalid_params"
    orphan_version = _call_tool(
        server, "search_document", {"query": "alpha", "version_id": "sha256:" + "0" * 64}
    )
    assert _error(orphan_version)["data"]["category"] == "invalid_params"
    for arguments in (
        {"query": "alpha", "limit": 0},
        {"query": "alpha", "limit": 101},
        {"query": "alpha", "page": -1},
        {"query": "line\nbreak"},
        {"query": ""},
    ):
        envelope = _call_tool(server, "search_document", arguments)
        assert _error(envelope)["data"]["category"] == "invalid_params"


def _compile_arguments(corpus: _Corpus, **overrides: object) -> dict[str, object]:
    """Return the stable bounded compile argument set for the shared corpus."""
    arguments: dict[str, object] = {
        "task": "alpha evidence",
        "document_ids": [str(corpus.text_document_id), str(corpus.rich_document_id)],
        "budget_limit": 1_000_000,
        "unit": "bytes",
    }
    arguments.update(overrides)
    return arguments


def test_compile_context_returns_handles_counts_and_persists(tmp_path: Path) -> None:
    """Compile handle-first, persist atomically and expose verified accounting."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    result = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    assert result["persisted"] is True
    assert isinstance(result["receipt_id"], str)
    assert result["receipt_id"].startswith("sha256:")
    assert isinstance(result["bundle_id"], str)
    assert result["mode"] == "mixed"
    assert "bundle" not in result
    counts = result["counts"]
    assert counts["selected"] >= 1
    assert counts["selected"] + counts["omitted"] + counts["rejected"] + counts["stale"] >= 1
    budget = result["budget"]
    assert budget["limit"] == 1_000_000
    assert budget["bundle_used"] <= budget["bundle_ceiling"]
    # The compilation is catalog-visible and survives the full verification load.
    records = corpus.catalog.list_context_compilations()
    assert [record.receipt_id for record in records] == [result["receipt_id"]]
    compiler = corpus.compiler_factory(Utf8ByteEstimator())
    verified = compiler.load_verified(result["receipt_id"])
    assert verified.receipt.receipt_id == result["receipt_id"]


def test_compile_context_matches_cli_projection_and_repeats(tmp_path: Path) -> None:
    """Match the exact CLI summary projection and repeat deterministically."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    first = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    second = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    assert first == second
    assert len(corpus.catalog.list_context_compilations()) == 1
    compiler = corpus.compiler_factory(Utf8ByteEstimator())
    cli_result = compiler.compile_and_persist(
        ContextCompileRequest(
            task="alpha evidence",
            document_ids=tuple(sorted((corpus.text_document_id, corpus.rich_document_id), key=str)),
            budget_limit=1_000_000,
            estimator=Utf8ByteEstimator().identity,
            policy=ContextSelectionPolicy(
                mode=ContextMode.MIXED,
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
        )
    )
    cli_summary = _json_value(
        _context_summary(cli_result.result, replayed=False, include_bundle=False)
    )
    expected = {key: value for key, value in cli_summary.items() if key != "replayed"}
    assert first == expected


def test_compile_context_maps_units_modes_and_rejects_bad_input(tmp_path: Path) -> None:
    """Map every unit to the exact estimator identity and reject bad shapes."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    for unit in ("bytes", "characters", "tokens"):
        result = _result(
            _call_tool(server, "compile_context", _compile_arguments(corpus, unit=unit))
        )
        assert result["estimator"]["unit"] == unit
    exact = _result(_call_tool(server, "compile_context", _compile_arguments(corpus, mode="exact")))
    assert exact["mode"] == "exact"
    for overrides, category in (
        ({"mode": "zyq"}, "invalid_params"),
        ({"unit": "zyq"}, "invalid_params"),
        ({"budget_limit": 0}, "invalid_params"),
        ({"budget_limit": True}, "invalid_params"),
        ({"include_bundle": "yes"}, "invalid_params"),
        ({"document_ids": []}, "invalid_params"),
        (
            {"document_ids": [str(corpus.text_document_id), str(corpus.text_document_id)]},
            "invalid_params",
        ),
        ({"document_ids": ["../hostile"]}, "invalid_params"),
        ({"document_ids": [UNKNOWN_UUID_V7]}, "not_found"),
    ):
        arguments = _compile_arguments(corpus)
        arguments.update(overrides)
        envelope = _call_tool(server, "compile_context", arguments)
        assert _error(envelope)["data"]["category"] == category, overrides


def test_compile_context_include_bundle_is_bounded_and_enveloped(tmp_path: Path) -> None:
    """Return the bundle only on explicit opt-in with enveloped item bodies."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    result = _result(
        _call_tool(server, "compile_context", _compile_arguments(corpus, include_bundle=True))
    )
    bundle = result["bundle"]
    assert isinstance(bundle, dict)
    assert str(bundle["bundle_id"]) == result["bundle_id"]
    items = bundle["items"]
    assert isinstance(items, list) and items
    for item in items:
        content = item["content"]
        assert content["content_role"] == "untrusted_data"
        assert content["delimiter"] == "openardp-evidence-v1"
        assert item["trust"]["instruction_execution_allowed"] is False
    cli_result = corpus.compiler_factory(Utf8ByteEstimator()).load_verified(result["receipt_id"])
    assert bundle == cli_result.bundle.model_dump(mode="json")
    _check_bundle_item_caps(cli_result.bundle.items, ServerCaps())
    with pytest.raises(McpFailure) as caught:
        _check_bundle_item_caps(cli_result.bundle.items, ServerCaps(body_bytes=1))
    assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_compile_context_stable_limit_category_for_tiny_budget(tmp_path: Path) -> None:
    """Fail closed with the stable limit category when the base bundle overflows."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    envelope = _call_tool(server, "compile_context", _compile_arguments(corpus, budget_limit=1))
    assert _error(envelope)["data"]["category"] == "invalid_params"
    assert corpus.catalog.list_context_compilations() == ()


def test_compile_context_response_cap_fails_closed_with_bundle(tmp_path: Path) -> None:
    """Fail the call instead of truncating when the bundle exceeds the response cap."""
    corpus = _Corpus(tmp_path)
    big_path = corpus.text_path.parent / "big.md"
    big_path.write_text("alpha " * 12_000 + "evidence\n", encoding="utf-8")
    big_result = corpus.text_ingestion.ingest(big_path)
    server = _server(corpus, limits=SessionLimits(response_cap_bytes=65_536))
    arguments = _compile_arguments(
        corpus,
        document_ids=[str(big_result.scope.document_id)],
        include_bundle=True,
    )
    envelope = _call_tool(server, "compile_context", arguments)
    assert _error(envelope)["data"]["category"] == "invalid_params"
    handle_only = _call_tool(
        server,
        "compile_context",
        _compile_arguments(corpus, document_ids=[str(big_result.scope.document_id)]),
    )
    assert "result" in handle_only


def test_get_context_receipt_returns_fully_verified_body_free_receipt(
    tmp_path: Path,
) -> None:
    """Return one receipt only after the complete F008 verification chain."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    compiled = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    receipt = _result(
        _call_tool(server, "get_context_receipt", {"receipt_id": compiled["receipt_id"]})
    )
    assert receipt["receipt_id"] == compiled["receipt_id"]
    assert receipt["task_digest"].startswith("sha256:")
    assert receipt["budget"]["limit"] == 1_000_000
    assert receipt["policy"]["mode"] == "mixed"
    assert len(receipt["selected"]) == compiled["counts"]["selected"]
    serialized = json.dumps(receipt)
    assert "alpha evidence" not in serialized
    assert "content_role" not in serialized


def test_get_context_receipt_unknown_and_malformed_are_stable(tmp_path: Path) -> None:
    """Map unknown and malformed receipt identifiers to uniform categories."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    unknown = _call_tool(server, "get_context_receipt", {"receipt_id": "sha256:" + "b" * 64})
    assert _error(unknown)["data"]["category"] == "not_found"
    for bad in ("md5:abc", "../hostile", "SHA256:" + "b" * 64, "sha256:" + "b" * 63):
        envelope = _call_tool(server, "get_context_receipt", {"receipt_id": bad})
        assert _error(envelope)["data"]["category"] == "invalid_params", bad


def test_get_context_receipt_detects_tampered_bundle_object(tmp_path: Path) -> None:
    """Fail closed with the integrity category when one CAS object is corrupt."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    compiled = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    commit = corpus.catalog.load_context_compilation(compiled["receipt_id"])
    assert commit is not None
    target = commit.record.bundle_object.object_id

    def tampered_factory(estimator: ContextEstimator) -> ContextCompilerService:
        return ContextCompilerService(
            _TamperingStore(corpus.object_store, target),  # type: ignore[arg-type]
            corpus.catalog,
            estimator,
            (),
        )

    tampered = _server(corpus, compiler_factory=tampered_factory)
    envelope = _call_tool(tampered, "get_context_receipt", {"receipt_id": compiled["receipt_id"]})
    assert _error(envelope)["data"]["category"] == "integrity_or_workspace"


# T038 — deadline and cancellation threading into the compiler


def test_compile_context_observes_expired_deadline_before_compiling(tmp_path: Path) -> None:
    """Fail with the deadline category before any compile side effect."""
    corpus = _Corpus(tmp_path)
    clock_ticks = [1_000.0]

    def jumped_clock() -> float:
        clock_ticks[0] += 2.0
        return clock_ticks[0]

    server = _server(
        corpus,
        clock=jumped_clock,
        limits=SessionLimits(deadline_ms=1_000),
    )
    envelope = _call_tool(server, "compile_context", _compile_arguments(corpus))
    assert _error(envelope)["data"]["category"] == "deadline_exceeded"
    assert corpus.catalog.list_context_compilations() == ()


def test_compile_context_cancellation_mid_discovery_leaves_no_partial_state(
    tmp_path: Path,
) -> None:
    """Thread the registry flag into the compiler and persist nothing on cancel."""
    corpus = _Corpus(tmp_path)
    holder: dict[str, McpServer] = {}

    def factory(estimator: ContextEstimator) -> ContextCompilerService:
        cancelling_source = _CancellingCandidateSource(
            TextLexicalCandidateSource(corpus.object_store, corpus.catalog),
            holder["server"],
            7,
        )
        return ContextCompilerService(
            corpus.object_store,
            corpus.catalog,
            estimator,
            (
                cancelling_source,
                RichLexicalCandidateSource(
                    corpus.object_store,
                    corpus.catalog,
                    representation_verifier=corpus._rich_verifier,
                ),
            ),
        )

    cancelling = _server(corpus, compiler_factory=factory)
    holder["server"] = cancelling
    _initialize(cancelling)
    response = cancelling.handle_line(
        _tool_call("compile_context", _compile_arguments(corpus), request_id=7)
    )
    assert response is not None
    assert _error(json.loads(response))["data"]["category"] == "cancelled"
    assert corpus.catalog.list_context_compilations() == ()
    # A retry without cancellation converges on the identical compilation.
    server_clocked = _server(corpus)
    result = _result(_call_tool(server_clocked, "compile_context", _compile_arguments(corpus)))
    assert result["persisted"] is True
    assert len(corpus.catalog.list_context_compilations()) == 1


def test_mid_compile_deadline_is_distinct_from_caller_cancellation(tmp_path: Path) -> None:
    """Map compiler cancellation caused by an elapsed deadline to deadline_exceeded."""
    corpus = _Corpus(tmp_path)
    now = [1_000.0]

    class _DeadlineCompiler:
        def compile_and_persist(self, _request: object, *, cancel: object) -> object:
            del cancel
            now[0] += 2.0
            raise ContextCompilationCancelled("cancelled")

    server = _server(
        corpus,
        clock=lambda: now[0],
        limits=SessionLimits(deadline_ms=1_000),
        compiler_factory=lambda estimator: _DeadlineCompiler(),  # type: ignore[arg-type]
    )
    envelope = _call_tool(server, "compile_context", _compile_arguments(corpus))
    assert _error(envelope)["data"]["category"] == "deadline_exceeded"
    assert corpus.catalog.list_context_compilations() == ()


def test_failed_followup_never_mutates_prior_valid_compilation(tmp_path: Path) -> None:
    """Keep an earlier verified result immutable across a cancelled follow-up."""
    corpus = _Corpus(tmp_path)
    valid = _server(corpus)
    first = _result(_call_tool(valid, "compile_context", _compile_arguments(corpus)))
    before = corpus.catalog.list_context_compilations()

    class _CancelledCompiler:
        def compile_and_persist(self, _request: object, *, cancel: object) -> object:
            del cancel
            raise ContextCompilationCancelled("cancelled")

    failing = _server(
        corpus,
        compiler_factory=lambda estimator: _CancelledCompiler(),  # type: ignore[arg-type]
    )
    envelope = _call_tool(
        failing,
        "compile_context",
        _compile_arguments(corpus, task="different followup"),
    )
    assert _error(envelope)["data"]["category"] == "cancelled"
    assert corpus.catalog.list_context_compilations() == before
    verified = corpus.compiler_factory(Utf8ByteEstimator()).load_verified(first["receipt_id"])
    assert verified.receipt.receipt_id == first["receipt_id"]


# T021/T023 — bounded validation helpers, notifications, serve-loop recovery


def test_validate_value_enforces_string_bounds_enum_and_pattern() -> None:
    """Enforce string bounds, enums and patterns before any service reach."""
    _validate_value({"type": "string", "minLength": 2, "maxLength": 4}, "abc")
    for spec, value in (
        ({"type": "string", "minLength": 2}, "a"),
        ({"type": "string", "maxLength": 2}, "abc"),
        ({"type": "string", "enum": ["a", "b"]}, "c"),
        ({"type": "string", "pattern": "^a+$"}, "ab"),
        ({"type": "string"}, "a\nb"),
        ({"type": "string"}, 7),
    ):
        with pytest.raises(McpFailure) as caught:
            _validate_value(spec, value)
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_validate_value_enforces_integer_bounds() -> None:
    """Reject booleans, non-integers and out-of-range integers."""
    _validate_value({"type": "integer", "minimum": 1, "maximum": 10}, 5)
    for value in (True, "5", 1.5):
        with pytest.raises(McpFailure) as caught:
            _validate_value({"type": "integer"}, value)
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS
    for spec, value in (
        ({"type": "integer", "minimum": 2}, 1),
        ({"type": "integer", "maximum": 2}, 3),
    ):
        with pytest.raises(McpFailure) as caught:
            _validate_value(spec, value)
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_validate_value_enforces_boolean_type() -> None:
    """Accept only strict JSON booleans for boolean properties."""
    _validate_value({"type": "boolean"}, False)
    with pytest.raises(McpFailure) as caught:
        _validate_value({"type": "boolean"}, 1)
    assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_validate_value_enforces_array_bounds_and_items() -> None:
    """Validate array cardinality and every nested item spec."""
    spec = {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string"}}
    _validate_value(spec, ["a"])
    _validate_value({"type": "array"}, ["anything", 7])
    for value in ("nope", [], ["a", "b", "c"], ["a", 7]):
        with pytest.raises(McpFailure) as caught:
            _validate_value(spec, value)
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_validate_value_rejects_unknown_property_types() -> None:
    """Fail closed on property types outside the bounded contract set."""
    with pytest.raises(McpFailure) as caught:
        _validate_value({"type": "object"}, {})
    assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def _broken_descriptor(schema: dict[str, object]) -> ToolDescriptor:
    """Build one defensively malformed descriptor for validator tests."""
    return ToolDescriptor(
        name="broken",
        interface_version=MCP_INTERFACE_VERSION,
        description="defensively broken schema",
        input_schema=schema,  # type: ignore[arg-type]
        output_bounds={},
    )


def test_validate_arguments_rejects_malformed_descriptor_schemas() -> None:
    """Fail closed with the internal category on broken published schemas."""
    for schema in (
        {"type": "object", "properties": "nope", "required": []},
        {"type": "object", "properties": {"x": "nope"}, "required": []},
    ):
        with pytest.raises(McpFailure) as caught:
            _validate_arguments(_broken_descriptor(schema), {"x": "y"})
        assert caught.value.category is McpErrorCategory.INTERNAL


def test_identifier_helpers_reject_malformed_values() -> None:
    """Accept only stored identifier forms, never paths or foreign digests."""
    assert _uuid_argument({"document_id": UNKNOWN_UUID}, "document_id") == UUID(UNKNOWN_UUID)
    assert _optional_version({}) is None
    digest = "sha256:" + "0" * 64
    assert _optional_version({"version_id": digest}) == digest
    for arguments in ({"document_id": "../hostile"}, {"document_id": 7}):
        with pytest.raises(McpFailure) as caught:
            _uuid_argument(arguments, "document_id")
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS
    for arguments in ({"version_id": "md5:abc"}, {"version_id": 7}):
        with pytest.raises(McpFailure) as caught:
            _optional_version(arguments)
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_optional_and_required_scalar_helpers_are_strict() -> None:
    """Keep handler extraction bounded to schema-validated scalar shapes."""
    assert _optional_str({}, "kind") is None
    assert _optional_str({"kind": "heading"}, "kind") == "heading"
    assert _optional_int({}, "limit") is None
    assert _optional_int({"limit": 20}, "limit") == 20
    assert _required_str({"query": "alpha"}, "query") == "alpha"
    for helper, arguments, name in (
        (_optional_str, {"kind": 7}, "kind"),
        (_optional_int, {"limit": True}, "limit"),
        (_required_str, {"query": 7}, "query"),
    ):
        with pytest.raises(McpFailure) as caught:
            helper(arguments, name)
        assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_estimator_unit_mapping_is_exact_and_closed() -> None:
    """Map every declared unit to the matching installed estimator only."""
    for unit in ("bytes", "characters", "tokens"):
        assert _estimator_for_unit(unit).identity.unit.value == unit
    with pytest.raises(McpFailure) as caught:
        _estimator_for_unit("zyq")
    assert caught.value.category is McpErrorCategory.INVALID_PARAMS


def test_default_audit_sink_emits_body_free_log(caplog: pytest.LogCaptureFixture) -> None:
    """Write the default audit record to the log without any bodies."""
    with caplog.at_level(logging.INFO, logger="openardp.mcp"):
        _default_audit({"tool": "ping", "outcome": "ok"})
    assert '"tool":"ping"' in caplog.text


def test_cancel_notification_is_cooperative_and_session_stays_usable(tmp_path: Path) -> None:
    """Ignore cancellation for non-active request ids and keep the session usable."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    _initialize(server)
    cancelled = {"jsonrpc": "2.0", "method": "notifications/cancelled"}
    assert server.handle_line(_line(cancelled)) is None
    assert server.handle_line(_line(cancelled | {"params": {"requestId": True}})) is None
    assert server.handle_line(_line(cancelled | {"params": {"requestId": ["x"]}})) is None
    assert server.handle_line(_line(cancelled | {"params": {"requestId": 99}})) is None
    envelope = _call_tool(server, "list_documents", request_id=99)
    assert "result" in envelope
    assert server.handle_line(_line(cancelled | {"params": {"requestId": "req-7"}})) is None
    response = server.handle_line(
        _line(
            {
                "jsonrpc": "2.0",
                "id": "req-7",
                "method": "tools/call",
                "params": {"name": "list_documents", "arguments": {}},
            }
        )
    )
    assert response is not None
    assert "result" in json.loads(response)


def test_serve_reads_cancellation_while_compilation_is_running(tmp_path: Path) -> None:
    """Route a real mid-flight stdio notification into the active compiler call."""
    corpus = _Corpus(tmp_path)
    started = threading.Event()

    class _BlockingCompiler:
        def compile_and_persist(self, _request: object, *, cancel: object) -> object:
            started.set()
            check = cancel
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if check():  # type: ignore[operator]
                    raise ContextCompilationCancelled("cancelled")
                time.sleep(0.001)
            pytest.fail("cancellation notification was not observed mid-flight")

    server = _server(corpus, compiler_factory=lambda _estimator: _BlockingCompiler())
    prefix = (
        b"\n".join(
            [
                _request("initialize", {"protocolVersion": PROTOCOL_REVISION}),
                _line({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                _request(
                    "tools/call",
                    {
                        "name": "compile_context",
                        "arguments": {
                            "task": "bounded cancellation",
                            "document_ids": [str(corpus.text_document_id)],
                            "budget_limit": 1_000,
                            "unit": "bytes",
                        },
                    },
                    request_id="active-compile",
                ),
            ]
        )
        + b"\n"
    )
    cancellation = (
        _line(
            {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled",
                "params": {"requestId": "active-compile"},
            }
        )
        + b"\n"
    )

    class _StagedSource:
        def __init__(self) -> None:
            self._step = 0

        def read(self, _size: int = -1) -> bytes:
            self._step += 1
            if self._step == 1:
                return prefix
            if self._step == 2:
                assert started.wait(timeout=1.0)
                return cancellation
            return b""

    sink = io.BytesIO()
    assert server.serve(_StagedSource(), sink) == 0  # type: ignore[arg-type]
    messages = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert len(messages) == 2
    assert messages[0]["result"]["protocolVersion"] == PROTOCOL_REVISION
    assert _error(messages[1])["data"]["category"] == "cancelled"


def test_serve_fails_closed_when_pending_frame_cap_is_exceeded(tmp_path: Path) -> None:
    """Bound pipelined frames and unwind active work instead of growing memory."""
    corpus = _Corpus(tmp_path)

    class _BlockingCompiler:
        def compile_and_persist(self, _request: object, *, cancel: object) -> object:
            check = cancel
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if check():  # type: ignore[operator]
                    raise ContextCompilationCancelled("cancelled")
                time.sleep(0.001)
            pytest.fail("pending-frame overflow did not unwind active work")

    server = _server(corpus, compiler_factory=lambda _estimator: _BlockingCompiler())
    messages = [
        _request("initialize", {"protocolVersion": PROTOCOL_REVISION}),
        _line({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        _request(
            "tools/call",
            {
                "name": "compile_context",
                "arguments": {
                    "task": "bounded queue",
                    "document_ids": [str(corpus.text_document_id)],
                    "budget_limit": 1_000,
                    "unit": "bytes",
                },
            },
            request_id="overflow-compile",
        ),
    ]
    messages.extend(
        _request("ping", request_id=1_000 + index) for index in range(_MAX_PENDING_FRAMES + 8)
    )
    source = io.BytesIO(b"\n".join(messages) + b"\n")
    sink = io.BytesIO()

    assert server.serve(source, sink) == 0
    responses = [json.loads(line) for line in sink.getvalue().splitlines()]
    compile_response = next(item for item in responses if item.get("id") == "overflow-compile")
    assert _error(compile_response)["data"]["category"] == "cancelled"
    terminal = responses[-1]
    assert terminal["id"] is None
    assert _error(terminal)["data"]["category"] == "invalid_request"
    assert len(responses) <= _MAX_PENDING_FRAMES + 1


def test_unknown_and_mistimed_notifications_are_discarded(tmp_path: Path) -> None:
    """Drop unknown or mistimed notifications without disturbing the session."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    unknown = {"jsonrpc": "2.0", "method": "notifications/unknown"}
    assert server.handle_line(_line(unknown)) is None
    mistimed = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    assert server.handle_line(_line(mistimed)) is None
    assert server.lifecycle.state.value == "start"
    _initialize(server)
    assert server.handle_line(_line(unknown)) is None
    assert server.lifecycle.state.value == "ready"


def test_serve_loop_recovers_from_oversize_frame(tmp_path: Path) -> None:
    """Fail one over-cap frame, then keep serving later well-formed frames."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    oversized = b"x" * (MAX_LINE_BYTES + 1)
    handshake = (
        _request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_REVISION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        )
        + b"\n"
    )
    sink = io.BytesIO()
    assert server.serve(io.BytesIO(oversized + b"\n" + handshake), sink) == 0
    sink.seek(0)
    responses = [json.loads(line) for line in sink.readlines() if line.strip()]
    assert _error(responses[0])["data"]["category"] == "invalid_request"
    assert responses[-1]["result"]["serverInfo"]["name"] == SERVER_NAME


def test_get_evidence_accepts_optional_document_scope(tmp_path: Path) -> None:
    """Resolve one projection scoped explicitly to its owning document."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    listing = _result(
        _call_tool(server, "list_evidence", {"document_id": str(corpus.rich_document_id)})
    )
    projections = listing["projections"]
    assert isinstance(projections, list)
    projection_id = projections[0]["evidence_projection_id"]
    result = _result(
        _call_tool(
            server,
            "get_evidence",
            {
                "evidence_projection_id": projection_id,
                "document_id": str(corpus.rich_document_id),
            },
        )
    )
    assert result["body"]["body"] == RICH_BODY


def test_get_evidence_rejects_non_string_projection_id(tmp_path: Path) -> None:
    """Reject non-string projection identifiers at the handler boundary."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    with pytest.raises(McpFailure) as caught:
        server._get_evidence({"evidence_projection_id": 7}, None, None)  # type: ignore[arg-type]
    assert caught.value.category is McpErrorCategory.INVALID_PARAMS
