"""Stable foreground watcher and body-free job control CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openardp.interfaces import cli
from openardp.interfaces.cli import main
from tests.error_envelopes import without_hint


def _json_call(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[int, dict[str, object], str]:
    code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    return code, json.loads(captured.out), captured.err


def _locations(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    root.mkdir()
    assert main(["init", "--store", str(workspace)]) == 0
    return workspace, root


def test_watch_once_ingests_text_and_returns_only_body_free_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose exact one-cycle counts/handles without root, filename or content."""
    workspace, root = _locations(tmp_path)
    capsys.readouterr()
    source = root / "private-name.txt"
    source.write_text("DO-NOT-LEAK-WATCH-BODY", encoding="utf-8")
    code, payload, stderr = _json_call(
        capsys,
        [
            "watch",
            str(root),
            "--store",
            str(workspace),
            "--once",
            "--stability-ms",
            "0",
        ],
    )
    assert code == 0 and stderr == ""
    assert payload["command"] == "watch" and payload["ok"] is True
    encoded = json.dumps(payload)
    assert str(root) not in encoded
    assert "private-name" not in encoded
    assert "DO-NOT-LEAK" not in encoded
    data = payload["data"]
    assert isinstance(data, dict)
    counts = data["counts"]
    assert isinstance(counts, dict)
    assert counts["scheduled"] == 1 and counts["succeeded"] == 1
    jobs = data["jobs"]
    assert isinstance(jobs, dict)
    succeeded = jobs["succeeded"]
    assert isinstance(succeeded, list)
    code, conflict, _ = _json_call(
        capsys,
        ["job-cancel", str(succeeded[0]), "--store", str(workspace)],
    )
    assert code == 5
    assert without_hint(conflict["error"]) == {
        "code": "conflict",
        "message": "operation conflicts with current state",
    }


def test_jobs_and_cancel_are_bounded_and_hide_private_fields(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inspect/cancel queued work without paths, keys, owners or tokens."""
    workspace, root = _locations(tmp_path)
    capsys.readouterr()
    (root / "secret-file.txt").write_text("secret-body", encoding="utf-8")
    code, watched, _ = _json_call(
        capsys,
        [
            "watch",
            str(root),
            "--store",
            str(workspace),
            "--once",
            "--stability-ms",
            "0",
            "--max-jobs-per-cycle",
            "0",
        ],
    )
    assert code == 0
    watch_data = watched["data"]
    assert isinstance(watch_data, dict)
    jobs = watch_data["jobs"]
    assert isinstance(jobs, dict)
    scheduled = jobs["scheduled"]
    assert isinstance(scheduled, list)
    job_id = str(scheduled[0])

    code, listed, _ = _json_call(
        capsys,
        ["jobs", "--store", str(workspace), "--state", "QUEUED", "--limit", "10"],
    )
    assert code == 0
    encoded = json.dumps(listed)
    for forbidden in (str(root), "secret-file", "secret-body", "deduplication", "owner", "token"):
        assert forbidden not in encoded

    code, cancelled, _ = _json_call(
        capsys,
        ["job-cancel", job_id, "--store", str(workspace)],
    )
    assert code == 0
    cancel_data = cancelled["data"]
    assert isinstance(cancel_data, dict)
    assert cancel_data["state"] == "CANCELLED"
    code, replayed, _ = _json_call(
        capsys,
        ["job-cancel", job_id, "--store", str(workspace)],
    )
    assert code == 0 and replayed["data"] == cancel_data
    code, missing, _ = _json_call(
        capsys,
        [
            "job-cancel",
            "018f7e6a-4c00-4000-8000-000000000404",
            "--store",
            str(workspace),
        ],
    )
    assert code == 3
    assert without_hint(missing["error"]) == {
        "code": "not_found",
        "message": "requested evidence was not found",
    }


def test_watch_rejects_overlap_and_bad_bounds_with_sanitized_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fail before traversal without echoing private authority."""
    workspace = tmp_path / "workspace"
    assert main(["init", "--store", str(workspace)]) == 0
    capsys.readouterr()
    code, overlap, stderr = _json_call(
        capsys,
        ["watch", str(tmp_path), "--store", str(workspace), "--once"],
    )
    assert code == 4 and stderr == ""
    assert overlap["error"] == {
        "code": "rejected_input",
        "message": "input was rejected",
        "hint": "The watched folder and the workspace (--store) must not contain each other.",
    }
    assert str(tmp_path) not in json.dumps(overlap)

    root = tmp_path / "documents"
    root.mkdir()
    code, invalid, _ = _json_call(
        capsys,
        [
            "watch",
            str(root),
            "--store",
            str(workspace),
            "--once",
            "--max-entries",
            "0",
        ],
    )
    assert code == 4
    assert without_hint(invalid["error"]) == without_hint(overlap["error"])

    code, rich_invalid, _ = _json_call(
        capsys,
        [
            "watch",
            str(root),
            "--store",
            str(workspace),
            "--once",
            "--docling-model-root",
            str(root),
        ],
    )
    assert code == 4
    assert without_hint(rich_invalid["error"]) == without_hint(overlap["error"])


def test_watch_help_and_continuous_interrupt_are_operationally_truthful(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Advertise bounded controls and map foreground interruption to status 130."""
    assert main(["watch", "--help"]) == 0
    help_output = capsys.readouterr().out
    for option in (
        "--once",
        "--poll-ms",
        "--stability-ms",
        "--max-entries",
        "--max-active-jobs",
        "--max-jobs-per-cycle",
    ):
        assert option in help_output

    workspace, root = _locations(tmp_path)
    capsys.readouterr()

    class _InterruptedService:
        def run_forever(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_watch_service", lambda *_args: _InterruptedService())
    assert main(["watch", str(root), "--store", str(workspace)]) == 130
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_watcher_human_output_is_compact_and_body_free(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Show opaque status and counts rather than private locators."""
    workspace, root = _locations(tmp_path)
    capsys.readouterr()
    (root / "human.txt").write_text("private human body", encoding="utf-8")
    assert (
        main(
            [
                "watch",
                str(root),
                "--store",
                str(workspace),
                "--once",
                "--stability-ms",
                "0",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "root=sha256:" in captured.out
    assert "scheduled=1 succeeded=1" in captured.out
    assert "human.txt" not in captured.out
    assert "private human body" not in captured.out
    assert captured.err == ""
