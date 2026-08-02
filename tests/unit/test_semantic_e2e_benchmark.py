"""Contract and pure-policy tests for the frozen F025 benchmark."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from scripts.semantic_e2e_benchmark import (
    SemanticBenchmarkError,
    atom_matches,
    load_inputs,
    make_observation,
    normalize_atom,
)
from scripts.semantic_e2e_evaluation import CONDITIONAL, NOT_READY, READY, decide, summarize

ROOT = Path(__file__).parents[2]


def test_frozen_inputs_have_closed_coverage_and_exact_identities() -> None:
    """Load all questions, languages, strata, formats and canonical identities."""
    inputs = load_inputs(ROOT)

    assert tuple(inputs.by_id) == tuple(f"Q{value:02d}" for value in range(1, 20))
    assert {item["language"] for item in inputs.by_id.values()} == {"de", "en"}
    assert {item["stratum"] for item in inputs.by_id.values()} == {
        "cross_language",
        "direct",
        "multi_source",
        "paraphrase",
        "source_discrimination",
        "unsupported",
    }
    assert {value for item in inputs.by_id.values() for value in item["required_formats"]} == {
        "csv",
        "docx",
        "md",
        "pdf",
        "pptx",
        "txt",
    }


def test_atom_normalization_is_deliberately_narrow() -> None:
    """Normalize Unicode case and whitespace without punctuation removal or translation."""
    assert normalize_atom("  A\u0308  VALUE\n") == "ä value"
    assert atom_matches("NASA\n  Framework", ["nasa framework"])
    assert not atom_matches("scientifically robust", ["scientifically, robust"])
    assert not atom_matches("Menschen bleiben verantwortlich", ["humans remain in charge"])


def test_input_identity_and_unknown_question_field_fail_closed(tmp_path: Path) -> None:
    """Reject both semantic mutation and closed-schema drift."""
    shutil.copytree(ROOT / "benchmarks/semantic-e2e", tmp_path / "benchmarks/semantic-e2e")
    fixture = tmp_path / "benchmarks/semantic-e2e/v0.1.0/questions.json"
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["questions"][0]["unexpected"] = True
    fixture.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(SemanticBenchmarkError, match="question_schema"):
        load_inputs(tmp_path)


def _rows(
    *, direct: str, operator: str
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    inputs = load_inputs(ROOT)
    rows: list[dict[str, object]] = []
    for question in inputs.by_id.values():
        for treatment, behavior in (
            ("openardp_direct", direct),
            ("openardp_operator", operator),
        ):
            selected = []
            if question["answerable"] and behavior == "full":
                fitness = {entry["source_key"]: entry for entry in question["source_fitness"]}
                atoms_by_source: dict[str, list[str]] = {}
                for atom in question["support_atoms"]:
                    atoms_by_source.setdefault(atom["source_key"], []).append(atom["atom_id"])
                for order, (source, atom_ids) in enumerate(sorted(atoms_by_source.items())):
                    selected.append(
                        {
                            "order": order,
                            "evidence_id": "sha256:" + f"{order + 1:064x}",
                            "source_key": source,
                            "representation": "exact",
                            "anchor_type": "synthetic",
                            "covered_atom_ids": sorted(atom_ids),
                            "relevant": True,
                            "citation_valid": True,
                            "source_fitness_score": sum(
                                fitness[source][key]
                                for key in (
                                    "publisher_authority",
                                    "directness",
                                    "temporal_fit",
                                    "integrity",
                                    "reuse_basis",
                                )
                            ),
                            "source_fitness_max": 10,
                        }
                    )
            rows.append(make_observation(question, treatment, selected))
    return rows, inputs.by_id


def _summary(
    rows: list[dict[str, object]], questions: dict[str, dict[str, object]]
) -> dict[str, object]:
    inputs = load_inputs(ROOT)
    return summarize(
        rows,
        questions,
        corpus_id=inputs.protocol["corpus_id"],
        question_set_id=inputs.questions["question_set_id"],
        protocol_id=inputs.protocol["protocol_id"],
        supported_formats_ingested=("docx", "md", "pdf", "pptx", "txt"),
        semantic_runs_identical=True,
    )


def test_policy_proves_ready_conditional_and_not_ready_paths() -> None:
    """Exercise all three frozen decisions without floating-point thresholds."""
    inputs = load_inputs(ROOT)
    ready_rows, questions = _rows(direct="full", operator="full")
    ready_summary = _summary(ready_rows, questions)
    assert decide(ready_summary, inputs.protocol, hard_failures=[])["decision"] == READY

    conditional_summary = copy.deepcopy(ready_summary)
    direct = conditional_summary["treatments"]["openardp_direct"]
    direct["full_support"] = {"numerator": 7, "denominator": 17, "ratio": "0.411765"}
    direct["atom_recall"] = {"numerator": 20, "denominator": 43, "ratio": "0.465116"}
    direct["source_recall"] = {"numerator": 7, "denominator": 18, "ratio": "0.388889"}
    direct["mrr"] = {"numerator": 7, "denominator": 17, "ratio": "0.411765"}
    assert decide(conditional_summary, inputs.protocol, hard_failures=[])["decision"] == CONDITIONAL

    assert (
        decide(ready_summary, inputs.protocol, hard_failures=["integrity_failure"])["decision"]
        == NOT_READY
    )


def test_unsupported_irrelevant_selection_penalizes_abstention_and_precision() -> None:
    """Treat generic irrelevant context as a false positive rather than an answer."""
    inputs = load_inputs(ROOT)
    question = inputs.by_id["Q17"]
    irrelevant = {
        "order": 0,
        "evidence_id": "sha256:" + "1" * 64,
        "source_key": "nasa-ethical-ai-framework",
        "representation": "exact",
        "anchor_type": "text",
        "covered_atom_ids": [],
        "relevant": False,
        "citation_valid": True,
        "source_fitness_score": 0,
        "source_fitness_max": 0,
    }
    row = make_observation(question, "openardp_direct", [irrelevant])

    assert row["abstained"] is False
    assert row["relevant_count"] == 0
    assert row["full_support"] is False


def test_failed_product_row_is_stable_and_body_free() -> None:
    """Reduce parser, network or resource exceptions to a closed failure category."""
    question = load_inputs(ROOT).by_id["Q01"]
    row = make_observation(
        question,
        "openardp_direct",
        [],
        outcome="failed",
        failure_category="product_runtime_failure",
    )

    assert row["outcome"] == "failed"
    assert row["failure_category"] == "product_runtime_failure"
    assert "exception" not in row
    assert "body" not in row
