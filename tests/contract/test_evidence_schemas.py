"""Contract parity and deterministic generation for F006 evidence roots."""

from __future__ import annotations

import hashlib
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
    EVIDENCE_ROOT_CONTRACTS,
    build_schemas,
    render_schema,
)

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "conformance" / "evidence" / "v0.1.0" / "valid"


@pytest.mark.parametrize("schema_name", sorted(EVIDENCE_ROOT_CONTRACTS))
def test_evidence_roots_validate_golden_json_in_schema_and_model(schema_name: str) -> None:
    """Keep independent schemas and executable strict models in parity."""
    contract = EVIDENCE_ROOT_CONTRACTS[schema_name]
    data = (FIXTURES / contract.fixture_name).read_bytes()
    instance: dict[str, Any] = json.loads(data)
    schema = build_schemas()[schema_name]
    Draft202012Validator(schema).validate(instance)
    record = validate_json(contract.model, data)
    assert record.model_dump(mode="json") == instance


@pytest.mark.parametrize("schema_name", sorted(EVIDENCE_ROOT_CONTRACTS))
def test_evidence_roots_reject_unknown_direct_fields(schema_name: str) -> None:
    """Keep installed experimental roots closed."""
    contract = EVIDENCE_ROOT_CONTRACTS[schema_name]
    instance = json.loads((FIXTURES / contract.fixture_name).read_bytes())
    instance["unknown"] = True
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()[schema_name]).validate(instance)
    with pytest.raises(ValidationError):
        validate_json(contract.model, json.dumps(instance))


@pytest.mark.parametrize("schema_name", sorted(EVIDENCE_ROOT_CONTRACTS))
@pytest.mark.parametrize(
    ("version", "message"),
    (
        ("invalid", "semantic version"),
        ("0.2.0", "not installed"),
        ("1.0.0", "unsupported contract major"),
    ),
)
def test_every_evidence_root_distinguishes_version_failures(
    schema_name: str,
    version: str,
    message: str,
) -> None:
    """Keep installed-version behavior explicit on every public root."""
    contract = EVIDENCE_ROOT_CONTRACTS[schema_name]
    instance = json.loads((FIXTURES / contract.fixture_name).read_bytes())
    instance["contract_version"] = version
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()[schema_name]).validate(instance)
    with pytest.raises(ValidationError, match=message):
        validate_json(contract.model, json.dumps(instance))


def test_evidence_schemas_have_reviewed_metadata_and_bytes() -> None:
    """Generate valid deterministic Draft 2020-12 schema bytes."""
    first = build_schemas()
    assert first == build_schemas()
    for schema_name, contract in EVIDENCE_ROOT_CONTRACTS.items():
        schema = first[schema_name]
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == DRAFT_2020_12
        assert schema["$id"] == contract.schema_id
        assert schema["x-openardp-contract-version"] == "0.1.0"
        assert schema["properties"]["contract_version"]["const"] == "0.1.0"
        assert schema["properties"]["stability"]["const"] == "experimental"
        assert (ROOT / "schemas" / schema_name).read_bytes() == render_schema(schema)


def test_trust_schema_rejects_unnamespaced_extensions() -> None:
    """Express the extension namespace boundary for independent validators."""
    contract = EVIDENCE_ROOT_CONTRACTS["trust-classification.schema.json"]
    instance = json.loads((FIXTURES / contract.fixture_name).read_bytes())
    instance["extensions"] = {"quality": 1}
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()["trust-classification.schema.json"]).validate(instance)


def test_existing_schema_bytes_match_f005a_baseline_hashes() -> None:
    """Protect the five prior public schemas from additive F006 drift."""
    expected = {
        "manifest.schema.json": "1995cc1062e5322405a00adba8e47c7f3bed9fa294de6920dc27476c5a36dfd4",
        "block.schema.json": "413d725016a9f4f261e384efff3f82906a08c7e3b73a25bc8f96963a10861562",
        "derivation.schema.json": (
            "56e8fc17050584b6d4bfc430d5f8d24de03237e5ef2b96fc7d9f6afd61f3e88a"
        ),
        "relation.schema.json": "00b581b077089e6534f4cc0c3af511fa2caa8ede6b81649ee5094f0b60bca142",
        "context-bundle.schema.json": (
            "e6cea129f58bd11ec52e1f63ef87258d8ec9c01ac37ff7fa933b08e96790a31a"
        ),
    }

    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / "schemas" / name).read_bytes()).hexdigest() == digest
