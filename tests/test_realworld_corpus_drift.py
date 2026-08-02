"""Committed F024 corpus and reference-result drift gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.realworld_corpus import verify_corpus
from scripts.validate_realworld_corpus_benchmark import validate

ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "corpora/realworld/v0.1.0"
BENCHMARK = ROOT / "benchmarks/realworld-corpus/v0.1.0"
RESULT = BENCHMARK / "results/reference-macos-arm64"


def test_committed_corpus_and_reference_decision_remain_exact() -> None:
    """Fail normal CI on source, rights, observation, summary or decision drift."""
    corpus = verify_corpus(CORPUS)
    decision = validate(ROOT, RESULT)

    assert corpus.corpus_id == (
        "sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd"
    )
    assert decision["decision"] == "REALWORLD_BASELINE_READY"
    assert decision["failure_codes"] == []


def test_reference_retains_bounded_pptx_pointer_without_overclaim() -> None:
    """Keep the unfavorable 8 MiB pointer-bound fact visible in committed evidence."""
    summary = json.loads((RESULT / "summary.json").read_bytes())
    pptx = next(item for item in summary["assets"] if item["format"] == "pptx")
    report = (RESULT / "report.md").read_text(encoding="utf-8")

    assert pptx["pointer_bounded_count"] == 1
    assert pptx["retrieval_complete"] is True
    assert "semantic answer correctness" in report
    assert "legal certainty" in report
