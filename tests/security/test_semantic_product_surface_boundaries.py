"""Security and privacy boundaries for opt-in semantic product surfaces."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import openardp.interfaces.cli as cli
from openardp.interfaces.mcp_protocol import require_tool
from openardp.ports.semantic_retrieval import SemanticProviderUnavailable
from tests.integration.test_cli_context import _invoke_json, _WorkspaceCorpus
from tests.integration.test_mcp_server import (
    _call_tool,
    _compile_arguments,
    _Corpus,
    _error,
    _server,
)

BODY_MARKER = "ZZSEMANTICBODYMARKER"
PATH_MARKER = "/private/ZZSEMANTICPATH"


def test_cli_provider_failure_is_stable_and_body_free(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reduce provider construction failures to one path-free public category."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)

    def fail(_configuration: tuple[Path, Path]) -> None:
        raise SemanticProviderUnavailable(f"{BODY_MARKER} {PATH_MARKER}")

    monkeypatch.setattr(cli, "_open_semantic_provider", fail)
    code, payload, stderr = _invoke_json(
        capsys,
        [
            *corpus.context_arguments(),
            "--retrieval-profile",
            "semantic",
            "--semantic-bundle",
            PATH_MARKER,
            "--semantic-source-lock",
            f"{PATH_MARKER}/lock.json",
        ],
    )
    serialized = json.dumps(payload)
    assert code == 5 and stderr == ""
    assert payload["error"] == {
        "code": "semantic_provider_rejected",
        "message": "semantic provider is unavailable or rejected",
    }
    assert BODY_MARKER not in serialized and PATH_MARKER not in serialized


def test_mcp_semantic_runtime_failure_does_not_leak_provider_details(tmp_path: Path) -> None:
    """Map unexpected semantic factory failures into the closed MCP error taxonomy."""
    corpus = _Corpus(tmp_path)

    def fail(_estimator: object) -> None:
        raise RuntimeError(f"{BODY_MARKER} {PATH_MARKER}")

    server = _server(corpus, semantic_compiler_factory=fail)
    envelope = _call_tool(
        server,
        "compile_context",
        _compile_arguments(corpus, retrieval_profile="semantic"),
    )
    serialized = json.dumps(envelope)
    assert _error(envelope)["data"]["category"] == "internal"
    assert BODY_MARKER not in serialized and PATH_MARKER not in serialized


def test_mcp_semantic_selector_has_no_path_or_provider_authority() -> None:
    """Keep the complete semantic authority boundary outside client input."""
    descriptor = require_tool("compile_context")
    properties = descriptor.input_schema["properties"]
    assert isinstance(properties, dict)
    assert properties["retrieval_profile"] == {
        "type": "string",
        "enum": ["lexical", "semantic"],
    }
    forbidden = {"path", "bundle", "source_lock", "provider", "model", "policy", "limits"}
    assert forbidden.isdisjoint(properties)
