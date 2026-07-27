"""Stable local CLI workflows for context compilation and receipt inspection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.interfaces.cli import main
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.ingestion import IngestionService
from openardp.services.rich_ingestion import RichIngestionService
from tests.integration.test_rich_ingestion import _Clock, _Parser

TASK = "alpha evidence"
TASK_MARKER = "ZZCLITASKMARKER"
BODY_MARKER = "ZZCLIBODYMARKER"
PATH_MARKER = "zzclipathmarker"


def _invoke_json(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, dict[str, object], str]:
    """Run one JSON command and return code, envelope and stderr."""
    code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1
    return code, json.loads(lines[0]), captured.err


def _invoke_human(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, str, str]:
    """Run one human command and return code, stdout and stderr."""
    code = main(arguments)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class _WorkspaceCorpus:
    """One initialized workspace with mixed text and rich evidence."""

    def __init__(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self.store = tmp_path / "store"
        code, payload, _stderr = _invoke_json(capsys, ["init", "--store", str(self.store)])
        assert code == 0 and payload["ok"] is True
        object_store = FilesystemObjectStore(self.store)
        catalog = SQLiteCatalog(self.store / "catalog.sqlite3")
        clock = _Clock()
        self.text_ingestion = IngestionService(
            object_store,
            catalog,
            TextParserAdapter(),
            source_factory=LocalSource,
            clock=clock,
        )
        parser = _Parser()
        parser.text = "alpha rich evidence alpha"
        rich_ingestion = RichIngestionService(
            object_store,
            catalog,
            parser,
            source_factory=LocalSource,
            clock=clock,
            owner_id_factory=lambda: "cli-worker",
            lease_token_factory=lambda: "cli-capability-000000000000001",
            random_bits=lambda: 1,
        )
        self.text_path = tmp_path / "notes.md"
        self.text_path.write_text("alpha text evidence alpha\n", encoding="utf-8")
        text_result = self.text_ingestion.ingest(self.text_path)
        rich_path = tmp_path / "report.docx"
        rich_path.write_bytes(b"report-v1")
        rich_result = rich_ingestion.ingest(rich_path)
        self.document_ids = tuple(
            sorted(
                (text_result.scope.document_id, rich_result.scope.document_id),
                key=str,
            )
        )
        self.object_store = object_store
        self.catalog = catalog

    def context_arguments(self) -> list[str]:
        """Return the stable bounded compile argument vector."""
        return [
            "context",
            TASK,
            "--document",
            str(self.document_ids[0]),
            "--document",
            str(self.document_ids[1]),
            "--budget",
            "1000000",
            "--unit",
            "bytes",
            "--mode",
            "exact",
            "--store",
            str(self.store),
        ]


def test_context_json_contract_and_stable_repeat(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Compile through the stable JSON envelope with handles and accounting."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)

    code, payload, stderr = _invoke_json(capsys, corpus.context_arguments())

    assert code == 0
    assert stderr == ""
    assert payload["ok"] is True
    assert payload["command"] == "context"
    data = payload["data"]
    assert isinstance(data, dict)
    assert set(data) == {
        "bundle_id",
        "receipt_id",
        "persisted",
        "replayed",
        "created_at",
        "mode",
        "estimator",
        "scopes",
        "budget",
        "counts",
        "truncated",
        "notices",
        "warnings",
        "missing_evidence",
    }
    assert data["persisted"] is True
    assert data["replayed"] is False
    assert data["mode"] == "exact"
    budget = data["budget"]
    assert isinstance(budget, dict)
    assert budget["bundle_used"] + budget["response_reserved"] <= 1_000_000
    assert budget["bundle_used"] == budget["base_bundle_used"] + budget["selected_incremental_used"]
    counts = data["counts"]
    assert isinstance(counts, dict)
    assert counts["selected"] >= 1
    scopes = data["scopes"]
    assert isinstance(scopes, list)
    assert [str(scope["document_id"]) for scope in scopes] == sorted(
        str(item) for item in corpus.document_ids
    )
    raw = json.dumps(payload)
    assert TASK not in raw
    assert "alpha text evidence" not in raw

    repeated_code, repeated, _ = _invoke_json(capsys, corpus.context_arguments())
    assert repeated_code == 0
    assert repeated["data"] == data


def test_context_include_bundle_returns_explicit_bounded_payload(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return the full untrusted-envelope bundle only on explicit request."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)

    code, payload, _stderr = _invoke_json(
        capsys,
        [*corpus.context_arguments(), "--include-bundle"],
    )

    assert code == 0
    data = payload["data"]
    assert isinstance(data, dict)
    bundle = data["bundle"]
    assert isinstance(bundle, dict)
    assert bundle["bundle_id"] == data["bundle_id"]
    items = bundle["items"]
    assert isinstance(items, list) and items
    for item in items:
        content = item["content"]
        assert content["content_role"] == "untrusted_data"
        assert content["delimiter"] == "openardp-evidence-v1"
        assert item["trust"]["instruction_execution_allowed"] is False


def test_context_receipt_json_is_exact_body_free_and_deterministic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inspect the verified body-free receipt in deterministic JSON order."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    code, payload, _ = _invoke_json(capsys, corpus.context_arguments())
    assert code == 0
    data = payload["data"]
    assert isinstance(data, dict)
    receipt_id = str(data["receipt_id"])

    first = main(["context-receipt", receipt_id, "--store", str(corpus.store), "--json"])
    out_first = capsys.readouterr().out
    second = main(["context-receipt", receipt_id, "--store", str(corpus.store), "--json"])
    out_second = capsys.readouterr().out

    assert first == 0 and second == 0
    assert out_first == out_second
    envelope = json.loads(out_first)
    assert envelope["ok"] is True
    assert envelope["command"] == "context-receipt"
    receipt = envelope["data"]
    assert receipt["receipt_id"] == receipt_id
    assert receipt["contract_version"] == "0.1.0"
    assert receipt["task_digest"].startswith("sha256:")
    assert receipt["policy"]["mode"] == "exact"
    assert len(receipt["corpus_snapshot"]) == 2
    assert receipt["budget"]["bundle_used"] <= receipt["budget"]["bundle_ceiling"]
    assert isinstance(receipt["selected"], list)
    assert TASK not in out_first
    assert "alpha text evidence" not in out_first
    assert str(tmp_path) not in out_first


def test_context_human_outputs_summarize_without_bodies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Summarize selections, warnings and receipts without dumping bodies."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)

    code, out, err = _invoke_human(capsys, corpus.context_arguments())

    assert code == 0
    assert err == ""
    lines = out.splitlines()
    assert lines[0].startswith("receipt=sha256:")
    assert lines[1].startswith("bundle=")
    assert any(line.startswith("selected=") for line in lines)
    assert any(line.startswith("budget=") for line in lines)
    assert TASK not in out
    assert "alpha text evidence" not in out

    receipt_id = lines[0].removeprefix("receipt=")
    receipt_code, receipt_out, receipt_err = _invoke_human(
        capsys,
        ["context-receipt", receipt_id, "--store", str(corpus.store)],
    )
    assert receipt_code == 0
    assert receipt_err == ""
    receipt_lines = receipt_out.splitlines()
    assert receipt_lines[0] == lines[0]
    assert any(line.startswith("task_digest=sha256:") for line in receipt_lines)
    assert any(line.startswith("mode=exact") for line in receipt_lines)
    assert TASK not in receipt_out
    assert "alpha text evidence" not in receipt_out


def test_context_replay_json_is_byte_identical_and_pinned(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Replay the recorded snapshot through the CLI with identical identities."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    code, payload, _ = _invoke_json(capsys, corpus.context_arguments())
    assert code == 0
    data = payload["data"]
    assert isinstance(data, dict)
    receipt_id = str(data["receipt_id"])

    replay_code, replay, replay_err = _invoke_json(
        capsys,
        ["context", TASK, "--replay", receipt_id, "--store", str(corpus.store)],
    )

    assert replay_code == 0
    assert replay_err == ""
    replay_data = replay["data"]
    assert isinstance(replay_data, dict)
    assert replay_data["replayed"] is True
    assert replay_data["receipt_id"] == receipt_id
    assert replay_data["bundle_id"] == data["bundle_id"]
    assert replay_data["budget"] == data["budget"]
    assert replay_data["scopes"] == data["scopes"]


def test_context_no_match_reports_missing_evidence_honestly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return an honest empty result with body-free missing evidence."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    arguments = corpus.context_arguments()
    arguments[1] = "zzznolexicalmatch"

    code, payload, _ = _invoke_json(capsys, arguments)

    assert code == 0
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["counts"] == {"selected": 0, "omitted": 0, "rejected": 0, "stale": 0}
    missing = data["missing_evidence"]
    assert isinstance(missing, list) and missing
    assert all(entry["reason_code"] == "required_evidence_unavailable" for entry in missing)


def test_context_failures_map_into_stable_sanitized_envelopes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Map limit, mismatch, cancellation, corruption and usage faults stably."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    code, payload, _ = _invoke_json(capsys, corpus.context_arguments())
    assert code == 0
    data = payload["data"]
    assert isinstance(data, dict)
    receipt_id = str(data["receipt_id"])

    tiny = corpus.context_arguments()
    tiny[tiny.index("--budget") + 1] = "1"
    code, payload, _ = _invoke_json(capsys, tiny)
    assert code == 4
    assert payload["error"] == {"code": "rejected_input", "message": "input was rejected"}

    code, payload, _ = _invoke_json(
        capsys,
        ["context", "different task", "--replay", receipt_id, "--store", str(corpus.store)],
    )
    assert code == 5
    assert payload["error"] == {
        "code": "conflict",
        "message": "operation conflicts with current state",
    }

    code, payload, _ = _invoke_json(
        capsys,
        [
            "context",
            TASK,
            "--replay",
            receipt_id,
            "--unit",
            "characters",
            "--store",
            str(corpus.store),
        ],
    )
    assert code == 5
    assert payload["error"] == {
        "code": "conflict",
        "message": "operation conflicts with current state",
    }

    # Corrupted receipt object fails closed as workspace/integrity damage.
    hex_id = receipt_id.removeprefix("sha256:")
    object_path = corpus.store / "objects" / "sha256" / hex_id[:2] / hex_id[2:4] / hex_id[4:]
    object_path.write_bytes(b"corrupted")
    code, payload, _ = _invoke_json(
        capsys,
        ["context-receipt", receipt_id, "--store", str(corpus.store)],
    )
    assert code == 6
    assert payload["error"] == {
        "code": "integrity_or_workspace",
        "message": "workspace or persisted evidence is invalid",
    }

    code, payload, _ = _invoke_json(
        capsys,
        ["context-receipt", "not-a-receipt", "--store", str(corpus.store)],
    )
    assert code == 2
    assert payload["error"] == {"code": "invalid_usage", "message": "command usage is invalid"}

    code, payload, _ = _invoke_json(
        capsys,
        ["context", TASK, "--budget", "100", "--store", str(corpus.store)],
    )
    assert code == 2
    assert payload["error"] == {"code": "invalid_usage", "message": "command usage is invalid"}


def test_context_cancellation_maps_to_stable_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Surface bounded cancellation through the existing conflict envelope."""
    from openardp.ports.context import ContextCompilationCancelled

    corpus = _WorkspaceCorpus(tmp_path, capsys)

    def _cancelled(self: ContextCompilerService, *args: object, **kwargs: object) -> object:
        raise ContextCompilationCancelled("cancelled_before_snapshot")

    monkeypatch.setattr(ContextCompilerService, "compile_and_persist", _cancelled)

    code, payload, _ = _invoke_json(capsys, corpus.context_arguments())
    assert code == 5
    assert payload["error"] == {
        "code": "conflict",
        "message": "operation conflicts with current state",
    }

    human_code, out, err = _invoke_human(capsys, corpus.context_arguments())
    assert human_code == 5
    assert out == ""
    assert err == "error[conflict]: operation conflicts with current state\n"


def test_context_outputs_and_errors_never_leak_task_bodies_or_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Redact task, body and path markers from every CLI surface."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    marked_path = tmp_path / f"{PATH_MARKER}.md"
    marked_path.write_text(f"alpha text evidence {BODY_MARKER}\n", encoding="utf-8")
    marked = corpus.text_ingestion.ingest(marked_path)
    task = f"alpha evidence {TASK_MARKER}"
    arguments = [
        "context",
        task,
        "--document",
        str(marked.scope.document_id),
        "--budget",
        "1000000",
        "--unit",
        "bytes",
        "--mode",
        "exact",
        "--store",
        str(corpus.store),
    ]

    surfaces: list[str] = []
    code, out, err = _invoke_human(capsys, arguments)
    assert code == 0
    surfaces.extend((out, err))

    json_code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    assert json_code == 0
    surfaces.extend((captured.out, captured.err))
    envelope = json.loads(captured.out)
    data = envelope["data"]
    receipt_id = data["receipt_id"]

    receipt_code = main(["context-receipt", receipt_id, "--store", str(corpus.store), "--json"])
    captured = capsys.readouterr()
    assert receipt_code == 0
    surfaces.extend((captured.out, captured.err))

    failing = [
        "context",
        task,
        "--budget",
        "1",
        "--document",
        str(marked.scope.document_id),
        "--store",
        str(corpus.store),
    ]
    fail_code, fail_out, fail_err = _invoke_human(capsys, failing)
    assert fail_code == 4
    surfaces.extend((fail_out, fail_err))

    combined = "".join(surfaces)
    assert TASK_MARKER not in combined
    assert BODY_MARKER not in combined
    assert PATH_MARKER not in combined
    assert str(tmp_path) not in combined

    include_code = main([*arguments, "--include-bundle", "--json"])
    captured = capsys.readouterr()
    assert include_code == 0
    # Positive control: the explicitly requested bundle legitimately carries
    # task and body as delimited untrusted data.
    assert TASK_MARKER in captured.out
    assert BODY_MARKER in captured.out


def test_prior_cli_commands_remain_stable_in_mixed_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Keep every prior text/rich/search/evidence envelope unchanged."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)

    code, payload, _ = _invoke_json(capsys, ["list", "--store", str(corpus.store)])
    assert code == 0
    assert payload["ok"] is True
    assert payload["command"] == "list"
    documents = payload["data"]
    assert isinstance(documents, list) and len(documents) == 2

    code, payload, _ = _invoke_json(
        capsys,
        ["search", "alpha", "--store", str(corpus.store)],
    )
    assert code == 0
    assert payload["command"] == "search"
    search_data = payload["data"]
    assert isinstance(search_data, dict)
    assert search_data["returned"] >= 1

    code, payload, _ = _invoke_json(
        capsys,
        ["outline", str(corpus.document_ids[0]), "--store", str(corpus.store)],
    )
    assert code == 0
    assert payload["command"] == "outline"

    code, payload, _ = _invoke_json(
        capsys,
        ["evidence", str(corpus.document_ids[1]), "--store", str(corpus.store)],
    )
    assert code == 0
    assert payload["command"] == "evidence"
    evidence = payload["data"]
    assert isinstance(evidence, list) and evidence

    list_code, list_out, list_err = _invoke_human(capsys, ["list", "--store", str(corpus.store)])
    assert list_code == 0
    assert list_err == ""
    human_lines = [line for line in list_out.splitlines() if line]
    assert len(human_lines) == 2
    assert all(len(line.split("\t")) == 3 for line in human_lines)

    search_code, search_out, _ = _invoke_human(
        capsys,
        ["search", "alpha", "--store", str(corpus.store)],
    )
    assert search_code == 0
    assert "returned=" in search_out.splitlines()[-1]
