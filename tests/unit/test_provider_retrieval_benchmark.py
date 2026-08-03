"""Frozen producer-side F029 protocol and comparison invariants."""

from __future__ import annotations

from pathlib import Path

from scripts.provider_retrieval_benchmark import load_protocol


def test_all_provider_protocol_revisions_remain_exact_and_linked(
    repository_root: Path,
) -> None:
    """Retain both unfavorable runs and bind each structural correction explicitly."""
    first = load_protocol(repository_root, "0.1.0")
    second = load_protocol(repository_root, "0.2.0")
    third = load_protocol(repository_root, "0.3.0")

    assert second["parent_protocol_id"] == first["protocol_id"]
    assert third["parent_protocol_id"] == second["protocol_id"]
    assert "retrieval_profile" not in first
    assert second["retrieval_profile"]["hybrid_lexical_fallback"] is True
    assert third["retrieval_profile"]["representation_precedence"] == "rich_then_text"
    for protocol in (first, second, third):
        assert protocol["semantic_policy"]["minimum_score_millionths"] == 800_000
        assert protocol["model"]["model_revision"] == ("f470c6a1a906014160ece1968c484b275f0396de")
        assert protocol["question_set_id"] == first["question_set_id"]
