"""Public JSON Schema parity for F015 release evidence."""

from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from openardp.domain.release import RELEASE_EVIDENCE_VERSION
from scripts.generate_schemas import (
    DRAFT_2020_12,
    RELEASE_ROOT_CONTRACTS,
    build_schemas,
    render_schema,
)

ROOT = Path(__file__).parents[2]


def test_release_schema_is_closed_versioned_and_deterministic() -> None:
    """Publish one reviewed deterministic Draft 2020-12 release root."""
    name, contract = next(iter(RELEASE_ROOT_CONTRACTS.items()))
    schema = build_schemas()[name]
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == contract.schema_id
    assert schema["x-openardp-release-evidence-version"] == RELEASE_EVIDENCE_VERSION
    assert schema["properties"]["schema_version"]["const"] == RELEASE_EVIDENCE_VERSION
    assert schema["additionalProperties"] is False
    assert (ROOT / "schemas" / name).read_bytes() == render_schema(schema)


def test_release_schema_contains_closed_policy_observation_and_decision_defs() -> None:
    """Keep all machine evidence types inside the single public contract family."""
    name = next(iter(RELEASE_ROOT_CONTRACTS))
    definitions = build_schemas()[name]["$defs"]
    assert {
        "BenchmarkObservation",
        "PlatformEvidence",
        "ReleaseDecision",
        "ReleaseGatePolicy",
    } <= set(definitions)
    for definition in definitions.values():
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False
