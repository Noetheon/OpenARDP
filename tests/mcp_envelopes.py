"""Helpers that read MCP tools/call envelopes in tests."""

from __future__ import annotations

import json
from typing import Any

ERROR_META_KEY = "openardp/error"


def unwrap_tool_result(result: dict[str, Any]) -> Any:
    """Return the JSON payload of a successful legacy tool result, else the result."""
    if "content" in result and "isError" in result:
        assert result["isError"] is False, result
        content = result["content"]
        assert isinstance(content, list) and len(content) == 1
        assert content[0]["type"] == "text"
        return json.loads(content[0]["text"])
    return result


def tool_text(envelope: dict[str, Any]) -> str:
    """Return the text of one successful tools/call response."""
    assert "error" not in envelope, envelope.get("error")
    result = envelope["result"]
    assert result["isError"] is False, result
    text = result["content"][0]["text"]
    assert isinstance(text, str)
    return text


def tool_failure(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return the JSON-RPC error, or the taxonomy of an isError tool result."""
    if "error" in envelope:
        error = envelope["error"]
        assert isinstance(error, dict)
        return error
    result = envelope["result"]
    assert result.get("isError") is True, envelope
    error = result["_meta"][ERROR_META_KEY]
    assert isinstance(error, dict)
    return error
