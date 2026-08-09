"""Pure F035 phase, quality and decision tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.profiled_retrieval_benchmark import PROFILES, decide, load_protocol, summarize


def test_frozen_protocol_binds_parent_inputs_and_candidate_execution() -> None:
    """Reject accidental drift in the committed post-profiling decision boundary."""
    protocol = load_protocol(Path.cwd())

    assert protocol["f025_parent"]["context"]["max_scopes"] == 6
    assert protocol["candidate"]["semantic_policy"]["top_k"] == 128
    assert protocol["candidate"]["retrieval_profile"] == {
        "budgeting": "additive_canonical_prefix_v1",
        "hybrid_lexical_fallback": True,
        "prepared_corpus": "process_local_exact_snapshot_v1",
        "representation_precedence": "rich_then_text",
        "semantic_max_per_document": 64,
        "semantic_ranked_prefix": 4,
        "source_balanced_semantic_admission": True,
    }


def _question(answerable: bool) -> dict[str, Any]:
    return {
        "answerable": answerable,
        "language": "en",
        "stratum": "direct" if answerable else "unsupported",
        "required_formats": ["md"],
    }


def _observation(question_id: str, *, candidate: bool, answerable: bool) -> dict[str, Any]:
    selected_count = 1 if candidate and answerable else 2 if answerable else 0
    selected = [{"citation_valid": True} for _ in range(selected_count)]
    return {
        "question_id": question_id,
        "selected_count": selected_count,
        "relevant_count": int(answerable),
        "selected": selected,
        "first_relevant_rank": 1 if answerable else None,
        "full_support": answerable,
        "covered_atom_ids": ["A01"] if answerable else [],
        "required_atom_count": int(answerable),
        "covered_source_keys": ["source"] if answerable else [],
        "required_source_count": int(answerable),
        "abstained": not answerable,
        "wall_ns": 50 if candidate else 100,
        "cpu_ns": 1,
    }


def _phase(suite: str, run: int, profile: str, ordinal: int, *, candidate: bool) -> dict[str, Any]:
    wall = 50 if candidate else 100
    return {
        "suite": suite,
        "run": run,
        "profile": profile,
        "ordinal": ordinal,
        "wall_ns": wall,
        "compiler": {
            "snapshot_ns": 1,
            "discovery_ns": 10,
            "classification_ns": 1,
            "materialization_ns": 2,
            "budgeting_ns": 2,
            "finalization_ns": 1,
            "compile_ns": 20,
        },
        "source": {
            "enumeration_ns": 1,
            "provider_ns": 4,
            "admission_ns": 1,
            "reconciliation_ns": 1,
        },
        "provider": {
            "passage_encode_ns": 1 if ordinal == 0 else 0,
            "query_encode_ns": 1,
            "similarity_ns": 1,
        },
    }


def test_summary_accepts_strict_quality_and_warm_latency_improvement() -> None:
    """Keep strict improvement, protected metrics and latency jointly gated."""
    f025 = {"Q1": _question(True), "Q2": _question(False)}
    f034 = {"H1": _question(True), "H2": _question(False)}
    observations: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    for run in range(2):
        for profile in PROFILES:
            candidate = profile == "f035_candidate"
            for ordinal, (question_id, question) in enumerate(f025.items()):
                observations.append(
                    {
                        "suite": "f025_development",
                        "run": run,
                        "profile": profile,
                        "ordinal": ordinal,
                        "observation": _observation(
                            question_id,
                            candidate=candidate,
                            answerable=bool(question["answerable"]),
                        ),
                    }
                )
                phases.append(
                    _phase("f025_development", run, profile, ordinal, candidate=candidate)
                )
        for ordinal, (question_id, question) in enumerate(f034.items()):
            observations.append(
                {
                    "suite": "f034_holdout",
                    "run": run,
                    "profile": "f035_candidate",
                    "ordinal": ordinal,
                    "observation": _observation(
                        question_id,
                        candidate=True,
                        answerable=bool(question["answerable"]),
                    ),
                }
            )
            phases.append(_phase("f034_holdout", run, "f035_candidate", ordinal, candidate=True))
    perfect = {
        "numerator": 1,
        "denominator": 1,
        "ratio": "1.000000",
    }
    protocol = {
        "protocol_id": "sha256:" + "1" * 64,
        "gates": {
            "protected_quality": [
                "full_support",
                "atom_recall",
                "source_recall",
                "evidence_precision",
                "mrr",
                "citation_integrity",
                "unsupported_abstention",
            ],
            "strict_improvement_any": ["evidence_precision"],
        },
        "holdout_baseline": {
            name: perfect
            for name in (
                "full_support",
                "atom_recall",
                "source_recall",
                "evidence_precision",
                "mrr",
                "citation_integrity",
                "unsupported_abstention",
            )
        },
    }

    summary = summarize(observations, phases, protocol, f025, f034)
    decision = decide(summary)

    assert decision["validity"] == "valid"
    assert decision["development_candidate"] == "accepted"
    assert decision["holdout_generalization"] == "positive"
