"""Public JSON Schema parity for the F014 interchange tag record."""

from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from openardp.domain.interchange import INTERCHANGE_SCHEMA_VERSION
from scripts.generate_schemas import (
    DRAFT_2020_12,
    INTERCHANGE_ROOT_CONTRACTS,
    build_schemas,
    render_schema,
)

ROOT = Path(__file__).parents[2]


def test_interchange_schema_is_closed_versioned_and_deterministic() -> None:
    """Publish one reviewed deterministic Draft 2020-12 schema."""
    name, contract = next(iter(INTERCHANGE_ROOT_CONTRACTS.items()))
    schema = build_schemas()[name]
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == contract.schema_id
    assert schema["x-openardp-export-profile-version"] == INTERCHANGE_SCHEMA_VERSION
    assert schema["properties"]["schema_version"]["const"] == INTERCHANGE_SCHEMA_VERSION
    assert schema["additionalProperties"] is False
    assert (ROOT / "schemas" / name).read_bytes() == render_schema(schema)
