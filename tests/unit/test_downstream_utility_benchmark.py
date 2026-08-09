"""Pure F036 evidence-review utility tests."""

from __future__ import annotations

from scripts.downstream_utility_benchmark import evaluate_observation


def _observation() -> dict[str, object]:
    return {
        "question_id": "Q1",
        "required_atom_count": 2,
        "required_source_count": 2,
        "abstained": False,
        "wall_ns": 100,
        "selected": [
            {
                "order": 0,
                "relevant": True,
                "citation_valid": True,
                "covered_atom_ids": ["A01"],
                "source_key": "source-1",
                "source_fitness_score": 9,
                "source_fitness_max": 10,
            },
            {
                "order": 1,
                "relevant": True,
                "citation_valid": False,
                "covered_atom_ids": ["A02"],
                "source_key": "source-2",
                "source_fitness_score": 8,
                "source_fitness_max": 10,
            },
            {
                "order": 2,
                "relevant": True,
                "citation_valid": True,
                "covered_atom_ids": ["A02"],
                "source_key": "source-2",
                "source_fitness_score": 9,
                "source_fitness_max": 10,
            },
        ],
    }


def test_answerable_completion_uses_only_trusted_prefix_evidence() -> None:
    """Invalid citations cannot contribute atoms or sources to completion."""
    before = evaluate_observation(_observation(), budget=2)
    complete = evaluate_observation(_observation(), budget=3)

    assert before["answerable_completion"] is False
    assert before["trusted_atom_count"] == 1
    assert complete["answerable_completion"] is True
    assert complete["trusted_atom_count"] == 2
    assert complete["trusted_source_count"] == 2
    assert complete["source_fitness_score"] == 18
    assert complete["source_fitness_max"] == 20


def test_unsupported_completion_requires_abstention_and_empty_selection() -> None:
    """Unsupported tasks fail when a packet contains speculative evidence."""
    safe = {
        "question_id": "Q0",
        "required_atom_count": 0,
        "required_source_count": 0,
        "abstained": True,
        "wall_ns": 10,
        "selected": [],
    }
    unsafe = {**safe, "selected": [_observation()["selected"][0]]}

    assert evaluate_observation(safe, budget=3)["safe_unsupported_completion"] is True
    assert evaluate_observation(unsafe, budget=3)["safe_unsupported_completion"] is False


def test_one_item_covering_multiple_atoms_counts_once_for_effort() -> None:
    """Review effort counts evidence items while atom coverage deduplicates atom IDs."""
    observation = _observation()
    selected = observation["selected"]
    assert isinstance(selected, list)
    selected[0]["covered_atom_ids"] = ["A01", "A02", "A02"]
    selected[0]["source_key"] = "source-2"

    result = evaluate_observation(observation, budget=1)

    assert result["inspected_count"] == 1
    assert result["trusted_atom_count"] == 2
    assert result["trusted_source_count"] == 1
    assert result["answerable_completion"] is False
