"""Committed release bundle validation and tamper tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.validate_release_evidence import ReleaseValidationError, validate

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "release" / "evidence" / "v0.1.0"


def test_committed_release_evidence_is_complete_and_projection_consistent() -> None:
    """Validate every committed manifest/hash/identity/projection relationship."""
    validate(EVIDENCE)


def test_release_evidence_tamper_and_extra_file_fail_closed(tmp_path: Path) -> None:
    """Reject both digest drift and undeclared entries without repairing evidence."""
    copied = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, copied)
    (copied / "report.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ReleaseValidationError, match="digest mismatch"):
        validate(copied)
    shutil.copytree(EVIDENCE, tmp_path / "extra")
    (tmp_path / "extra" / "unknown.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ReleaseValidationError, match="inventory"):
        validate(tmp_path / "extra")
