"""Schema parity and strict public-boundary tests for F011 visual evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

from openardp.domain.common import validate_json
from scripts.generate_schemas import (
    DRAFT_2020_12,
    VISUAL_ROOT_CONTRACTS,
    build_schemas,
    render_schema,
)

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests/fixtures/visual/contract/valid-descriptor.json"
SCHEMA_NAME = "visual-evidence-descriptor.schema.json"


def _instance() -> dict[str, Any]:
    return json.loads(FIXTURE.read_bytes())


def test_visual_descriptor_fixture_validates_in_schema_and_model() -> None:
    """Keep the independent schema and strict executable root in parity."""
    schema = build_schemas()[SCHEMA_NAME]
    instance = _instance()
    Draft202012Validator(schema).validate(instance)
    record = validate_json(VISUAL_ROOT_CONTRACTS[SCHEMA_NAME].model, FIXTURE.read_bytes())
    assert record.model_dump(mode="json") == instance


@pytest.mark.parametrize(
    ("path", "value", "schema_rejects"),
    (
        (("unknown",), True, True),
        (("contract_version",), "0.2.0", True),
        (("identity_version",), 2, True),
        (("visual_evidence_id",), "sha256:" + "f" * 64, False),
        (("usage_policy", "export_allowed"), True, False),
        (("trust", "instruction_execution_allowed"), True, True),
    ),
)
def test_visual_descriptor_rejects_invalid_public_fixtures(
    path: tuple[str, ...],
    value: object,
    schema_rejects: bool,
) -> None:
    """Reject structural, version, identity, policy and trust drift."""
    instance = _instance()
    target = instance
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    payload = json.dumps(instance)
    validator = Draft202012Validator(build_schemas()[SCHEMA_NAME])
    if schema_rejects:
        with pytest.raises(JsonSchemaValidationError):
            validator.validate(instance)
    else:
        validator.validate(instance)
    with pytest.raises(ValidationError):
        validate_json(VISUAL_ROOT_CONTRACTS[SCHEMA_NAME].model, payload)


@pytest.mark.parametrize(
    ("version", "message"),
    (
        ("invalid", "semantic version"),
        ("0.2.0", "not installed"),
        ("1.0.0", "unsupported contract major"),
    ),
)
def test_visual_contract_distinguishes_version_failures(
    version: str,
    message: str,
) -> None:
    """Keep malformed, uninstalled and unsupported-major failures distinct."""
    instance = _instance()
    instance["contract_version"] = version
    with pytest.raises(ValidationError, match=message):
        validate_json(VISUAL_ROOT_CONTRACTS[SCHEMA_NAME].model, json.dumps(instance))


def test_visual_schema_metadata_extensions_and_bytes_are_reviewed() -> None:
    """Generate one deterministic experimental Draft 2020-12 root."""
    schema = build_schemas()[SCHEMA_NAME]
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["x-openardp-contract-version"] == "0.1.0"
    assert schema["properties"]["contract_version"]["const"] == "0.1.0"
    assert schema["properties"]["stability"]["const"] == "experimental"
    assert (ROOT / "schemas" / SCHEMA_NAME).read_bytes() == render_schema(schema)

    instance = _instance()
    instance["extensions"] = {"quality": 1}
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema).validate(instance)
