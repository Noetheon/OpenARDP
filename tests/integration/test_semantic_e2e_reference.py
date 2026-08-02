"""Independent-validator and opt-in execution boundaries for F025."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_semantic_e2e_benchmark import ValidationFailure, validate_result

ROOT = Path(__file__).parents[2]
REFERENCE = ROOT / "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64"


def test_independent_validator_accepts_committed_reference() -> None:
    """Recompute the frozen result through the stdlib-only validator."""
    assert validate_result(ROOT, REFERENCE).startswith("SEMANTIC_E2E_")


@pytest.mark.parametrize(
    "name",
    ["decision.json", "observations.json", "report.md", "run-manifest.json", "summary.json"],
)
def test_independent_validator_rejects_every_result_file_tampering(
    tmp_path: Path, name: str
) -> None:
    """Reject drift in every independently manifest-bound result file."""
    result = tmp_path / "result"
    shutil.copytree(REFERENCE, result)
    target = result / name
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(ValidationFailure):
        validate_result(ROOT, result)


def test_missing_pdf_bundle_fails_before_product_execution(tmp_path: Path) -> None:
    """Map an absent explicit model installation to one body-free command failure."""
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and repository script.
        [
            sys.executable,
            str(ROOT / "scripts/run_semantic_e2e_benchmark.py"),
            "--repository-root",
            str(ROOT),
            "--pdf-bundle",
            str(tmp_path / "missing-bundle"),
            "--output",
            str(tmp_path / "result"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 6
    assert completed.stdout == "benchmark_execution_failed\n"
    assert completed.stderr == ""


@pytest.mark.skipif(
    not os.environ.get("OPENARDP_PDF_BUNDLE") or not os.environ.get("OPENARDP_SEMANTIC_E2E_RESULT"),
    reason="binding corpus execution is explicit and heavyweight",
)
def test_opt_in_actual_corpus_execution() -> None:
    """Run the explicit real corpus only when both external paths are supplied."""
    completed = subprocess.run(  # noqa: S603 - explicit maintainer opt-in paths.
        [
            sys.executable,
            str(ROOT / "scripts/run_semantic_e2e_benchmark.py"),
            "--repository-root",
            str(ROOT),
            "--pdf-bundle",
            os.environ["OPENARDP_PDF_BUNDLE"],
            "--output",
            os.environ["OPENARDP_SEMANTIC_E2E_RESULT"],
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=1_800,
    )
    assert completed.returncode == 0, completed.stdout
