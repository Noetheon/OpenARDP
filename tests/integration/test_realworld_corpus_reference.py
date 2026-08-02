"""Opt-in actual F024 six-format/PDF-bundle reference execution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.realworld_corpus_benchmark import execute
from scripts.validate_realworld_corpus_benchmark import validate

ROOT = Path(__file__).parents[2]


def test_actual_realworld_reference_is_offline_and_ready(tmp_path: Path) -> None:
    """Run only when a maintainer supplies the separately validated F023 bundle."""
    configured = os.environ.get("OPENARDP_REALWORLD_CORPUS_BUNDLE")
    if configured is None:
        pytest.skip("set OPENARDP_REALWORLD_CORPUS_BUNDLE for the actual reference run")
    output = tmp_path / "result"

    decision = execute(ROOT, pdf_bundle=Path(configured), output=output)

    assert decision["decision"] == "REALWORLD_BASELINE_READY"
    assert validate(ROOT, output) == decision
