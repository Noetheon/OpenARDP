"""Adversarial F035 evidence-reconciliation tests."""

from __future__ import annotations

import pytest

from scripts.profiled_retrieval_benchmark import ProfiledRetrievalError, validate_phases


def test_phase_validator_rejects_nested_time_exceeding_authoritative_parent() -> None:
    """Fail closed when a producer double-counts or fabricates provider phases."""
    observations = [
        {
            "suite": "f025_development",
            "run": 0,
            "profile": "f035_candidate",
            "ordinal": 0,
            "observation": {},
        }
    ]
    phases = [
        {
            "suite": "f025_development",
            "run": 0,
            "profile": "f035_candidate",
            "ordinal": 0,
            "wall_ns": 100,
            "compiler": {
                "snapshot_ns": 1,
                "discovery_ns": 10,
                "classification_ns": 1,
                "materialization_ns": 1,
                "budgeting_ns": 1,
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
                "passage_encode_ns": 3,
                "query_encode_ns": 2,
                "similarity_ns": 1,
            },
        }
    ]

    with pytest.raises(ProfiledRetrievalError, match="provider_phase_reconciliation"):
        validate_phases(phases, observations)
