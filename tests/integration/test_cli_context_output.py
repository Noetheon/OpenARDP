"""Human opt-in evidence rendering without changing persisted or JSON contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from openardp.domain.context_compilation import ContextBundleV020
from openardp.interfaces.cli import main
from openardp.interfaces.cli_output import safe_text, success
from tests.integration.test_cli_context import _WorkspaceCorpus

_ORDINARY_UNICODE = "Übergröße, Öl, süß — 中文"
_BIDI_CONTROLS = (0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A))
_CONTROLS = "".join(chr(code) for code in (*range(32), *range(0x7F, 0xA0), *_BIDI_CONTROLS))


def _summary(repository_root: Path) -> dict[str, object]:
    """Return a validated synthetic bundle and its ordinary CLI summary."""
    fixture = repository_root / "tests/fixtures/context/context-bundle-0.2.0.json"
    bundle = ContextBundleV020.model_validate_json(fixture.read_bytes()).model_dump(mode="json")
    return {
        "receipt_id": "sha256:" + "a" * 64,
        "bundle_id": bundle["bundle_id"],
        "counts": {"selected": 1, "omitted": 0, "rejected": 0, "stale": 0},
        "budget": {
            "bundle_used": 1400,
            "bundle_ceiling": 9000,
            "unit": "bytes",
            "limit": 10000,
        },
        "truncated": False,
        "warnings": [],
        "missing_evidence": [],
        "bundle": bundle,
    }


def _run(capsys: pytest.CaptureFixture[str], arguments: list[str]) -> str:
    """Run one successful real CLI invocation and retain its exact output bytes."""
    assert main(arguments) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def test_opted_in_human_context_shows_exact_text_rich_ids_and_preserves_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Read real text/rich evidence while sources, receipts and JSON stay byte-identical."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    original = corpus.text_path.read_bytes()
    arguments = corpus.context_arguments()
    before = _run(capsys, [*arguments, "--include-bundle", "--json"])
    data = json.loads(before)["data"]
    receipt_arguments = [
        "context-receipt",
        data["receipt_id"],
        "--store",
        str(corpus.store),
        "--json",
    ]
    receipt_before = _run(capsys, receipt_arguments)

    default = _run(capsys, arguments)
    human = _run(capsys, [*arguments, "--include-bundle"])

    assert human.startswith(default)
    assert "alpha text evidence alpha" in human
    assert "alpha rich evidence alpha" in human
    assert "Evidence 1 [untrusted_data]" in human
    assert "Evidence 2 [untrusted_data]" in human
    for item in data["bundle"]["items"]:
        provenance = item["provenance"]
        for field in ("document_id", "version_id", "representation_id"):
            assert provenance[field] in human
        if provenance["record_type"] == "block":
            assert f"block={provenance['block_id']}" in human
            assert "openardp.text" in human and "line_start" in human
        else:
            assert f"projection={provenance['evidence_projection_id']}" in human
            assert f"reference={provenance['evidence_reference_id']}" in human
    assert "alpha text evidence" not in default
    assert "alpha rich evidence" not in default
    assert _run(capsys, [*arguments, "--include-bundle", "--json"]) == before
    assert _run(capsys, receipt_arguments) == receipt_before
    assert corpus.text_path.read_bytes() == original


def test_human_structured_content_and_handles_are_rendered_without_mutation(
    repository_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Render structured bodies and optional handles in their original ordered items."""
    summary = _summary(repository_root)
    item = summary["bundle"]["items"][0]
    item["representation"] = "structured"
    item["content"]["media_type"] = "application/json"
    item["content"]["body"] = {"z": [2, 1], "a": _ORDINARY_UNICODE}
    item["artifact_handle"] = "openardp:verified-context-object"
    item["artifact_id"] = "sha256:" + "b" * 64
    before = copy.deepcopy(summary)

    success("context", summary, json_output=False)
    human = capsys.readouterr().out

    expected_json = json.dumps(item["content"]["body"], ensure_ascii=False, sort_keys=True)
    assert safe_text(expected_json) in human
    assert "content (application/json):" in human
    assert "artifact=openardp:verified-context-object" in human
    assert "artifact_id=sha256:" + "b" * 64 in human
    assert summary == before
    success("context", summary, json_output=True)
    assert json.loads(capsys.readouterr().out)["data"] == before


def test_human_handle_only_item_does_not_invent_body_or_source_details(
    repository_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Display a rich visual handle as a handle, without fabricated pages or block IDs."""
    summary = _summary(repository_root)
    item = summary["bundle"]["items"][0]
    old = item["provenance"]
    item["provenance"] = {
        "record_type": "evidence_projection",
        "document_id": old["document_id"],
        "version_id": old["version_id"],
        "representation_id": old["representation_id"],
        "source_version_id": old["version_id"],
        "native_representation_id": "sha256:" + "3" * 64,
        "evidence_projection_id": "sha256:" + "4" * 64,
        "evidence_reference_id": "sha256:" + "5" * 64,
    }
    item["representation"] = "visual_handle"
    item["content"] = None
    item["artifact_handle"] = "openardp:visual:verified-object"
    success("context", summary, json_output=False)
    human = capsys.readouterr().out

    assert "artifact=openardp:visual:verified-object" in human
    assert "native_representation=sha256:" + "3" * 64 in human
    assert "content (" not in human
    assert "block=" not in human
    assert "source=" not in human
    assert "page=" not in human


def test_empty_opted_in_context_explains_absent_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty real selection remains an explicit absence, not an answer."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    arguments = corpus.context_arguments()
    arguments[1] = "zzznolexicalmatch"
    human = _run(capsys, [*arguments, "--include-bundle"])
    assert "No evidence selected." in human
    assert "selected=0" in human
    assert "Evidence 1" not in human


def test_safe_text_escapes_terminal_and_bidi_controls_and_retains_ordinary_unicode() -> None:
    """C0, DEL, C1 and explicit bidi controls cannot reach terminal output unescaped."""
    escaped = safe_text(_CONTROLS + _ORDINARY_UNICODE)
    assert all(character not in escaped for character in _CONTROLS)
    assert _ORDINARY_UNICODE in escaped
    for code in (*range(0x7F, 0xA0), *_BIDI_CONTROLS):
        assert f"\\u{code:04x}" in escaped
    assert safe_text('line one\nline two\t"quoted"\\') == 'line one\\nline two\\t\\"quoted\\"\\\\'


@pytest.mark.parametrize("body", ["text", "structured"])
def test_human_context_escapes_untrusted_contents_locators_and_handles(
    repository_root: Path, capsys: pytest.CaptureFixture[str], body: str
) -> None:
    """Escape attacks in each displayed data field and keep ordinary evidence legible."""
    summary = _summary(repository_root)
    item = summary["bundle"]["items"][0]
    marker = "start" + _CONTROLS + _ORDINARY_UNICODE + "end"
    item["content"]["body"] = marker if body == "text" else {marker: marker}
    item["provenance"]["source"]["native_id"] = marker
    item["artifact_handle"] = marker
    success("context", summary, json_output=False)
    human = capsys.readouterr().out

    assert _ORDINARY_UNICODE in human
    assert "artifact=start" in human
    assert "native_id" in human
    assert "start\x00" not in human
    assert all(chr(code) not in human for code in (*range(0x7F, 0xA0), *_BIDI_CONTROLS))
    assert not any(chr(code) in human for code in range(32) if code != 10)
    assert safe_text(marker) in human
    success("context", summary, json_output=True)
    assert json.loads(capsys.readouterr().out)["data"] == summary
