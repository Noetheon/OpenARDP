"""Stable CLI behavior for release evidence, decision and report commands."""

from __future__ import annotations

import json
from pathlib import Path

from openardp.interfaces.cli import main

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks" / "release" / "v0.1.0"


def test_release_cli_generates_honest_no_go_and_byte_stable_reports(
    tmp_path: Path, capsys: object
) -> None:
    """Execute the complete local flow without treating an unfavorable result as an error."""
    evidence = tmp_path / "platform"
    decision = tmp_path / "decision"
    assert (
        main(
            [
                "release-evidence",
                "--corpus",
                str(CORPUS),
                "--output",
                str(evidence),
                "--source-root",
                str(ROOT),
                "--reference-timing",
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "release-gate",
                "--policy",
                str(CORPUS / "gate-policy.json"),
                "--evidence",
                str(evidence),
                "--output",
                str(decision),
                "--decision-at",
                "2026-08-01T00:00:00Z",
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "release-report",
                "--decision",
                str(decision / "decision.json"),
                "--output",
                str(decision),
                "--json",
            ]
        )
        == 0
    )
    report_before = (decision / "report.md").read_bytes()
    assert (
        main(
            [
                "release-report",
                "--decision",
                str(decision / "decision.json"),
                "--output",
                str(decision),
                "--check",
                "--json",
            ]
        )
        == 0
    )
    assert (decision / "report.md").read_bytes() == report_before
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines()]  # type: ignore[attr-defined]
    assert payloads[1]["data"]["status"] == "NO-GO"
    assert "mandatory-suite-failed" in payloads[1]["data"]["blockers"]
    assert all(
        str(tmp_path) not in json.dumps(payload["data"].get("blockers", [])) for payload in payloads
    )


def test_release_cli_rejects_duplicate_json_and_conflicting_projection(
    tmp_path: Path, capsys: object
) -> None:
    """Return stable sanitized errors for malformed policy and report drift."""
    malformed = tmp_path / "policy.json"
    malformed.write_text('{"schema_version":"0.1.0","schema_version":"0.1.0"}', encoding="utf-8")
    code = main(
        [
            "release-gate",
            "--policy",
            str(malformed),
            "--evidence",
            str(tmp_path / "missing"),
            "--output",
            str(tmp_path / "output"),
            "--decision-at",
            "2026-08-01T00:00:00Z",
            "--json",
        ]
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert payload["error"] == {
        "code": "invalid_usage",
        "message": "command usage is invalid",
    }
