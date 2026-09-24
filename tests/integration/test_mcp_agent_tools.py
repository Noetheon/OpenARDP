"""Agent MCP tools, protocol negotiation and a real interactive stdio pipe."""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.interfaces.agent_composition import local_agent_access
from openardp.interfaces.cli import _mcp_server, main
from openardp.interfaces.mcp_agent_tools import AgentToolError, AgentWarmup
from openardp.interfaces.mcp_protocol import (
    LATEST_PROTOCOL_REVISION,
    McpErrorCategory,
    RequestDeadline,
    SessionLimits,
)
from openardp.interfaces.mcp_server import McpServer
from tests.mcp_envelopes import tool_failure, tool_text

GUIDE = """# Field guide

## Calibration

Calibrate the sensor every morning before the first measurement.
The reference weight is 500 grams.

## Storage

Store the sensor in a dry cabinet between 10 and 25 degrees.
"""
NOTES = """Meeting notes

The team agreed to publish the calibration log weekly.
"""


@pytest.fixture
def prepared_store(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """Prepare two small text documents through the public add command."""
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "guide.md").write_text(GUIDE, encoding="utf-8")
    (documents / "notes.txt").write_text(NOTES, encoding="utf-8")
    store = tmp_path / "store"
    assert main(["add", str(documents), "--store", str(store)]) == 0
    capsys.readouterr()
    return store


def _server(store: Path, toolset: str = "agent") -> McpServer:
    workspace = LocalWorkspace.open(store)
    return _mcp_server(workspace, SessionLimits(), toolset=toolset)


def _line(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload) + "\n").encode("utf-8")


def _initialize(server: McpServer, revision: str = "2025-06-18") -> dict[str, Any]:
    response = server.handle_line(
        _line(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": revision,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            }
        )
    )
    assert response is not None
    server.handle_line(_line({"jsonrpc": "2.0", "method": "notifications/initialized"}))
    result: dict[str, Any] = json.loads(response)["result"]
    return result


def _call(server: McpServer, name: str, arguments: dict[str, Any], request_id: int = 7) -> Any:
    response = server.handle_line(
        _line(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
    )
    assert response is not None
    return json.loads(response)


def test_agent_toolset_lists_five_read_only_tools_with_instructions(prepared_store: Path) -> None:
    """Publish a small spec-conformant tool list and server instructions."""
    server = _server(prepared_store)
    initialized = _initialize(server, revision="2025-11-25")
    assert initialized["protocolVersion"] == "2025-11-25"
    assert "verify_quote" in initialized["instructions"]
    response = server.handle_line(_line({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
    assert response is not None
    tools = json.loads(response)["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "list_documents",
        "find",
        "read",
        "outline",
        "verify_quote",
    ]
    for tool in tools:
        assert set(tool) == {"name", "title", "description", "inputSchema", "annotations"}
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["inputSchema"]["additionalProperties"] is False


def test_agent_tools_return_compact_located_text(prepared_store: Path) -> None:
    """Answer list, find, read, outline and verify with file and line locations."""
    server = _server(prepared_store)
    _initialize(server)
    listing = tool_text(_call(server, "list_documents", {}))
    assert "2 documents" in listing and "guide.md" in listing and "notes.txt" in listing

    found = tool_text(_call(server, "find", {"query": "How often must the sensor be calibrated?"}))
    assert found.startswith("1 of") or "matching passages" in found
    assert "guide.md:5-6" in found

    read = tool_text(_call(server, "read", {"document": "guide.md", "section": "Calibration"}))
    assert "5\tCalibrate the sensor every morning" in read
    assert "Store the sensor" not in read

    outline = tool_text(_call(server, "outline", {"document": "guide"}))
    assert "L3 ## Calibration" in outline and "L8 ## Storage" in outline

    verified = tool_text(
        _call(server, "verify_quote", {"quote": "The reference weight is 500 grams."})
    )
    assert verified.startswith("VERIFIED (exact): guide.md:6")
    missing = tool_text(
        _call(server, "verify_quote", {"quote": "The reference weight is 5 kilograms."})
    )
    assert missing.startswith("NOT FOUND") and "guide.md:5-6" in missing


@pytest.mark.parametrize(
    ("name", "arguments", "category", "fragment"),
    [
        ("read", {"document": "missing.pdf"}, "not_found", "list_documents"),
        ("read", {"document": "guide.md", "page": "2"}, "invalid_params", "no pages"),
        ("read", {"document": "guide.md", "lines": "999"}, "invalid_params", "beyond"),
        ("find", {"query": "sensor", "limit": 0}, "invalid_params", "input schema"),
        ("find", {"query": "sensor", "unknown": 1}, "invalid_params", "input schema"),
    ],
)
def test_agent_tool_failures_are_correctable_is_error_results(
    prepared_store: Path,
    name: str,
    arguments: dict[str, Any],
    category: str,
    fragment: str,
) -> None:
    """Return model-readable isError results carrying the versioned taxonomy."""
    server = _server(prepared_store)
    _initialize(server)
    envelope = _call(server, name, arguments)
    assert envelope["result"]["isError"] is True
    assert fragment in envelope["result"]["content"][0]["text"]
    assert tool_failure(envelope)["data"]["category"] == category


def test_unknown_tools_and_modern_probes_stay_protocol_errors(prepared_store: Path) -> None:
    """Keep JSON-RPC errors for unknown tools and a pre-initialize discovery probe."""
    server = _server(prepared_store)
    probe = server.handle_line(
        _line({"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {}})
    )
    assert probe is not None
    assert json.loads(probe)["error"]["code"] == -32601
    assert _initialize(server, revision="1999-01-01")["protocolVersion"] == (
        LATEST_PROTOCOL_REVISION
    )
    unknown = _call(server, "delete_everything", {})
    assert unknown["error"]["data"]["category"] == "unknown_tool"


def test_full_toolset_combines_agent_and_audit_tools(prepared_store: Path) -> None:
    """Offer the agent tools first and the audit tools without duplicate names."""
    server = _server(prepared_store, toolset="full")
    _initialize(server)
    response = server.handle_line(_line({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
    assert response is not None
    names = [tool["name"] for tool in json.loads(response)["result"]["tools"]]
    assert names[:5] == ["list_documents", "find", "read", "outline", "verify_quote"]
    assert "compile_context" in names and len(names) == len(set(names)) == 13


def test_agent_toolsets_require_an_agent_service(prepared_store: Path) -> None:
    """Reject an agent tool set without the service that implements it."""
    workspace = LocalWorkspace.open(prepared_store)
    template = _mcp_server(workspace, SessionLimits(), toolset="legacy")
    with pytest.raises(ValueError, match="agent access service"):
        McpServer(
            template._query,
            template._rich_evidence,
            search=template._search,
            compiler_factory=template._compiler_factory,
            toolset="agent",
        )


class _SlowAccess:
    def __init__(self) -> None:
        self.release = threading.Event()

    def refresh(self) -> None:
        self.release.wait(timeout=5)


def test_warmup_reports_still_preparing_within_the_request_deadline() -> None:
    """Answer promptly with a retryable isError while the first refresh still runs."""
    access = _SlowAccess()
    warmup = AgentWarmup(access)  # type: ignore[arg-type]
    warmup.start()
    now = [0.0]
    deadline = RequestDeadline(1_000, clock=lambda: now[0])
    now[0] = 0.9
    with pytest.raises(AgentToolError) as captured:
        warmup.wait(deadline)
    assert captured.value.category is McpErrorCategory.CONFLICT
    access.release.set()
    warmup.wait(RequestDeadline(10_000))
    warmup.start()


def test_warmup_failure_is_logged_and_retried_by_requests(
    prepared_store: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Never crash the session when the background refresh fails."""

    class _Broken:
        def refresh(self) -> None:
            raise RuntimeError("private detail")

    warmup = AgentWarmup(_Broken())  # type: ignore[arg-type]
    warmup.start()
    warmup.wait(RequestDeadline(10_000))
    assert "RuntimeError" in caplog.text and "private detail" not in caplog.text
    assert local_agent_access(LocalWorkspace.open(prepared_store)).refresh().indexed == 2


def test_interactive_pipe_session_answers_before_end_of_input(prepared_store: Path) -> None:
    """Answer each request while stdin stays open, as real agent hosts expect."""
    process = subprocess.Popen(  # noqa: S603 - current interpreter runs the local CLI module
        [sys.executable, "-m", "openardp.interfaces.cli", "mcp", "--store", str(prepared_store)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdin is not None and process.stdout is not None
    lines: queue.Queue[bytes] = queue.Queue()
    stdout = process.stdout
    threading.Thread(target=lambda: [lines.put(line) for line in stdout], daemon=True).start()

    def request(payload: dict[str, Any]) -> dict[str, Any]:
        assert process.stdin is not None
        process.stdin.write(_line(payload))
        process.stdin.flush()
        return dict(json.loads(lines.get(timeout=60)))

    try:
        initialized = request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {}},
            }
        )
        assert initialized["result"]["protocolVersion"] == "2025-11-25"
        process.stdin.write(_line({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        found = request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "find", "arguments": {"query": "reference weight"}},
            }
        )
        assert "guide.md:5-6" in tool_text(found)
    finally:
        process.stdin.close()
        assert process.wait(timeout=60) == 0
