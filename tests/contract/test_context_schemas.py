"""Contract parity and deterministic generation for F008 context roots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

from openardp.domain.common import validate_json
from openardp.domain.identity import selection_receipt_id
from scripts.generate_schemas import (
    CONTEXT_ROOT_CONTRACTS,
    DRAFT_2020_12,
    build_schemas,
    render_schema,
)

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "context"
UNINSTALLED_VERSIONS = {
    "context-bundle-0.2.0.schema.json": "0.3.0",
    "selection-receipt.schema.json": "0.2.0",
}


def _instance(schema_name: str) -> dict[str, Any]:
    contract = CONTEXT_ROOT_CONTRACTS[schema_name]
    instance: dict[str, Any] = json.loads((FIXTURES / contract.fixture_name).read_bytes())
    return instance


@pytest.mark.parametrize("schema_name", sorted(CONTEXT_ROOT_CONTRACTS))
def test_context_roots_validate_golden_json_in_schema_and_model(schema_name: str) -> None:
    """Keep independent schemas and executable strict models in parity."""
    contract = CONTEXT_ROOT_CONTRACTS[schema_name]
    data = (FIXTURES / contract.fixture_name).read_bytes()
    instance: dict[str, Any] = json.loads(data)
    schema = build_schemas()[schema_name]
    Draft202012Validator(schema).validate(instance)
    record = validate_json(contract.model, data)
    assert record.model_dump(mode="json") == instance


@pytest.mark.parametrize("schema_name", sorted(CONTEXT_ROOT_CONTRACTS))
def test_context_roots_reject_unknown_direct_fields(schema_name: str) -> None:
    """Keep installed experimental roots closed in both validation layers."""
    contract = CONTEXT_ROOT_CONTRACTS[schema_name]
    instance = _instance(schema_name)
    instance["unknown"] = True
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()[schema_name]).validate(instance)
    with pytest.raises(ValidationError):
        validate_json(contract.model, json.dumps(instance))


@pytest.mark.parametrize("schema_name", sorted(CONTEXT_ROOT_CONTRACTS))
@pytest.mark.parametrize(
    ("version", "message"),
    (
        ("invalid", "semantic version"),
        ("uninstalled", "not installed"),
        ("1.0.0", "unsupported"),
    ),
)
def test_every_context_root_distinguishes_version_failures(
    schema_name: str,
    version: str,
    message: str,
) -> None:
    """Reject malformed, uninstalled and unsupported-major contracts distinctly."""
    contract = CONTEXT_ROOT_CONTRACTS[schema_name]
    instance = _instance(schema_name)
    instance[contract.version_field] = (
        UNINSTALLED_VERSIONS[schema_name] if version == "uninstalled" else version
    )
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()[schema_name]).validate(instance)
    with pytest.raises(ValidationError, match=message):
        validate_json(contract.model, json.dumps(instance))


def test_context_schemas_have_reviewed_metadata_and_bytes() -> None:
    """Generate valid deterministic Draft 2020-12 schema bytes for both roots."""
    first = build_schemas()
    assert first == build_schemas()
    for schema_name, contract in CONTEXT_ROOT_CONTRACTS.items():
        schema = first[schema_name]
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == DRAFT_2020_12
        assert schema["$id"] == contract.schema_id
        assert schema["title"] == contract.title
        assert schema[contract.metadata_key] == contract.version
        assert schema["properties"][contract.version_field]["const"] == contract.version
        assert (ROOT / "schemas" / schema_name).read_bytes() == render_schema(schema)
    receipt_schema = first["selection-receipt.schema.json"]
    assert receipt_schema["x-openardp-contract-version"] == "0.1.0"
    assert receipt_schema["properties"]["stability"]["const"] == "experimental"
    bundle_schema = first["context-bundle-0.2.0.schema.json"]
    assert bundle_schema["x-openardp-schema-version"] == "0.2.0"


def test_selection_receipt_schema_is_body_free_by_shape() -> None:
    """Offer no task, body, path or credential fields in the public audit root."""
    schema = build_schemas()["selection-receipt.schema.json"]
    forbidden = {"task", "body", "query", "path", "secret", "credential"}
    assert forbidden.isdisjoint(schema["properties"])
    fixture_text = (FIXTURES / "selection-receipt.json").read_text(encoding="utf-8")
    assert "Explain exact evidence" not in fixture_text
    assert '"body"' not in fixture_text


def test_selection_receipt_accepts_namespaced_body_free_relevance_audit() -> None:
    """Keep F026 audit additive inside the existing extension point."""
    contract = CONTEXT_ROOT_CONTRACTS["selection-receipt.schema.json"]
    instance = _instance("selection-receipt.schema.json")
    extension = {
        "matched_signals": 2,
        "matched_weight": 5,
        "meets_minimum": True,
        "policy_id": "sha256:" + "a" * 64,
        "score_millionths": 500_000,
        "total_signals": 4,
        "total_weight": 10,
        "volatile_time_matched": True,
    }
    instance["selected"][0]["extensions"] = {
        "https://openardp.example/ns/context-relevance/v1": extension
    }
    instance["receipt_id"] = selection_receipt_id(
        {key: value for key, value in instance.items() if key != "receipt_id"}
    )

    Draft202012Validator(build_schemas()["selection-receipt.schema.json"]).validate(instance)
    record = validate_json(contract.model, json.dumps(instance))
    assert record.selected[0].extensions == instance["selected"][0]["extensions"]


def test_context_bundle_020_trust_role_is_data_in_schema_and_model() -> None:
    """Reject metadata authority labels on 0.2.0 evidence in both layers."""
    contract = CONTEXT_ROOT_CONTRACTS["context-bundle-0.2.0.schema.json"]
    instance = _instance("context-bundle-0.2.0.schema.json")
    instance["items"][0]["trust"]["role"] = "metadata"
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()["context-bundle-0.2.0.schema.json"]).validate(instance)
    with pytest.raises(ValidationError):
        validate_json(contract.model, json.dumps(instance))


def test_context_bundle_020_provenance_union_is_closed_in_schema() -> None:
    """Reject cross-branch provenance fields for independent validators."""
    instance = _instance("context-bundle-0.2.0.schema.json")
    instance["items"][0]["provenance"]["evidence_projection_id"] = "sha256:" + "7" * 64
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()["context-bundle-0.2.0.schema.json"]).validate(instance)

    instance = _instance("context-bundle-0.2.0.schema.json")
    del instance["items"][0]["provenance"]["record_type"]
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()["context-bundle-0.2.0.schema.json"]).validate(instance)


def test_untrusted_content_envelope_is_structural_in_schema() -> None:
    """Require the delimiter envelope on every embedded 0.2.0 evidence body."""
    instance = _instance("context-bundle-0.2.0.schema.json")
    instance["items"][0]["content"] = {
        "content_role": "trusted_instruction",
        "delimiter": "openardp-evidence-v1",
        "media_type": "text/plain",
        "body": "raw",
    }
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()["context-bundle-0.2.0.schema.json"]).validate(instance)
