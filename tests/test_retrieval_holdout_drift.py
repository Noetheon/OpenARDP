"""Frozen identity and policy drift guards for F034."""

from __future__ import annotations

from pathlib import Path

from scripts.retrieval_holdout import load_holdout


def test_f034_inputs_remain_frozen(repository_root: Path) -> None:
    """Prevent result-led edits to the milestone-only corpus, questions or targets."""
    inputs = load_holdout(repository_root)
    assert inputs.corpus["corpus_id"].startswith("sha256:")
    assert inputs.question_set["question_set_id"].startswith("sha256:")
    assert inputs.protocol["protocol_id"].startswith("sha256:")
    assert inputs.protocol["thresholds"] == {
        "full_support": [80, 100],
        "atom_recall": [90, 100],
        "source_recall": [90, 100],
        "evidence_precision": [60, 100],
        "mrr": [80, 100],
        "citation_integrity": [100, 100],
        "unsupported_abstention": [80, 100],
        "german_atom_recall": [50, 100],
        "spanish_atom_recall": [50, 100],
    }
