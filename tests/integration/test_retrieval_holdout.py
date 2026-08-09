"""Integration contracts for F034 evidence publication and validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_holdout_validator_uses_body_free_failure(repository_root: Path, tmp_path: Path) -> None:
    """Reject missing evidence with one stable category and no local path."""
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        (
            sys.executable,
            "scripts/validate_retrieval_holdout.py",
            "--result",
            str(tmp_path / "missing"),
        ),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 6
    assert completed.stdout == "holdout_evidence_invalid\n"
    assert completed.stderr == ""
    assert str(tmp_path) not in completed.stdout


def test_committed_holdout_result_recomputes_independently(repository_root: Path) -> None:
    """Recompute the reference summary and honest dual verdict from raw rows."""
    completed = subprocess.run(
        (
            sys.executable,
            "scripts/validate_retrieval_holdout.py",
            "--result",
            "benchmarks/retrieval-holdout/v0.1.0/results/reference-macos-arm64",
        ),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == ("validity=HOLDOUT_BASELINE_VALID quality=HOLDOUT_BELOW_TARGETS\n")
    assert completed.stderr == ""
