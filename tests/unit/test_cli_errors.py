"""Fixed actionable hints on sanitized CLI failures."""

from __future__ import annotations

import json

import pytest

from openardp.adapters.local_workspace import WorkspaceMissing
from openardp.interfaces.cli_arguments import ContextCommandUsageError
from openardp.interfaces.cli_errors import SUPPORTED_TYPES_HINT, classify, hint_for, render_failure
from openardp.ports.agent import AgentDocumentAmbiguous, AgentDocumentNotFound
from openardp.ports.context import ContextLimitExceeded
from openardp.ports.parser import (
    ParserProcessCrashed,
    RichParserDependencyUnavailable,
    RichParserModelAssetsRequired,
    UnsupportedTextMedia,
)


@pytest.mark.parametrize(
    ("error", "fragment"),
    [
        (RichParserModelAssetsRequired("x"), "--docling-model-root"),
        (RichParserDependencyUnavailable("x"), "uv sync --extra docling"),
        (ParserProcessCrashed("x"), "crashed"),
        (UnsupportedTextMedia("x"), ".pptx"),
        (ContextLimitExceeded("x"), "openardp find"),
        (WorkspaceMissing("x"), "openardp init"),
        (AgentDocumentNotFound("x"), "openardp docs"),
        (AgentDocumentAmbiguous("x", candidates=["a.md (id 1)"]), "document ID"),
        (ContextCommandUsageError("x"), "--help"),
    ],
)
def test_known_failures_carry_fixed_actionable_hints(error: Exception, fragment: str) -> None:
    """Map each reviewed failure class to one fixed hint naming the next action."""
    hint = hint_for(error)
    assert hint is not None and fragment in hint
    assert classify(error).hint == hint


def test_unknown_failures_have_no_hint_and_stable_classification() -> None:
    """Keep the historical code and exit classification for unhinted failures."""
    failure = classify(RuntimeError("private /secret/path"))
    assert (failure.exit_code, failure.code, failure.hint) == (1, "unexpected_failure", None)
    assert hint_for(UnsupportedTextMedia("x")) == SUPPORTED_TYPES_HINT


def test_agent_reference_failures_are_not_found_or_conflict() -> None:
    """Classify unresolved and ambiguous document references distinctly."""
    assert classify(AgentDocumentNotFound("x")).exit_code == 3
    assert classify(AgentDocumentAmbiguous("x")).exit_code == 5


def test_rendered_failures_never_echo_error_details(capsys: pytest.CaptureFixture[str]) -> None:
    """Write the fixed hint in both output modes without the exception text."""
    error = RichParserModelAssetsRequired("/private/report.pdf")
    assert render_failure("ingest", error, json_output=True) == 4
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["error"]["hint"] == hint_for(error)
    assert "/private/report.pdf" not in json.dumps(envelope)

    assert render_failure("ingest", error, json_output=False) == 4
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "error[rejected_input]: input was rejected",
        f"hint: {hint_for(error)}",
    ]
