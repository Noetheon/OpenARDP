"""Unit contracts for the independent F034 retrieval holdout."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.retrieval_holdout import (
    HoldoutError,
    evaluate_verdict,
    load_holdout,
    load_json,
    verify_holdout,
)


def test_committed_holdout_has_exact_independent_coverage(repository_root: Path) -> None:
    """Verify every frozen byte, oracle atom and predeclared coverage slice."""
    verification = verify_holdout(repository_root)
    inputs = load_holdout(repository_root)
    questions = list(inputs.questions.values())

    assert verification.source_count == 20
    assert verification.question_count == 100
    assert inputs.question_set["license"] == "CC-BY-SA-4.0"
    assert (
        inputs.question_set["upstream_lock_id"]
        == "sha256:60368f2d36aac7708231c8128586550079efb629f09b46ee37df26674f5f1c64"
    )
    assert Counter(question["language"] for question in questions) == {
        "en": 50,
        "de": 25,
        "es": 25,
    }
    assert Counter(question["stratum"] for question in questions) == {
        "direct": 30,
        "cross_language": 40,
        "source_discrimination": 10,
        "multi_source": 10,
        "unsupported": 10,
    }
    assert sum(bool(question["answerable"]) for question in questions) == 90
    assert sum(len(question["required_sources"]) == 2 for question in questions) == 10


def test_closed_json_rejects_duplicate_members(tmp_path: Path) -> None:
    """Reject ambiguous JSON before trusting identities or policy."""
    path = tmp_path / "duplicate.json"
    path.write_text('{"value":1,"value":2}', encoding="utf-8")
    with pytest.raises(HoldoutError, match="json_duplicate_key"):
        load_json(path)


def test_validity_and_quality_verdicts_are_independent() -> None:
    """Publish valid unfavorable evidence without weakening absolute targets."""
    decision = evaluate_verdict(
        validity_checks={"coverage": True, "citations": True},
        quality_checks={"atom_recall": False, "abstention": True},
        failures=(),
        summary_id="sha256:" + "1" * 64,
    )
    assert decision["validity"] == "HOLDOUT_BASELINE_VALID"
    assert decision["quality"] == "HOLDOUT_BELOW_TARGETS"
    assert decision["quality_blockers"] == ["atom_recall"]

    invalid = evaluate_verdict(
        validity_checks={"coverage": False},
        quality_checks={"atom_recall": True},
        failures=("runtime_failure",),
        summary_id="sha256:" + "2" * 64,
    )
    assert invalid["validity"] == "HOLDOUT_BASELINE_INVALID"
    assert invalid["quality"] == "HOLDOUT_QUALITY_NOT_EVALUABLE"
