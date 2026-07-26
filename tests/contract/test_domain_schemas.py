"""Contract tests aligning Pydantic records and public JSON Schemas."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

from openardp.domain import validate_json
from scripts.generate_schemas import (
    DRAFT_2020_12,
    ROOT_CONTRACTS,
    build_schemas,
    check_schemas,
    render_schema,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
FIXTURE_DIR = REPOSITORY_ROOT / "tests" / "fixtures" / "domain"


@pytest.mark.parametrize("schema_name", sorted(ROOT_CONTRACTS))
def test_golden_fixture_validates_and_round_trips(schema_name: str) -> None:
    """Keep executable models and reviewed Draft 2020-12 roots aligned."""
    contract = ROOT_CONTRACTS[schema_name]
    fixture_path = FIXTURE_DIR / contract.fixture_name
    instance: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    schema = build_schemas()[schema_name]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(instance)

    record = validate_json(contract.model, fixture_path.read_bytes())
    validator.validate(record.model_dump(mode="json"))
    assert validate_json(contract.model, record.model_dump_json()) == record


@pytest.mark.parametrize("schema_name", sorted(ROOT_CONTRACTS))
def test_unknown_direct_property_fails_schema_and_model(schema_name: str) -> None:
    """Agree on every schema-expressible closed-object boundary."""
    contract = ROOT_CONTRACTS[schema_name]
    fixture_path = FIXTURE_DIR / contract.fixture_name
    instance: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    instance["unexpected"] = True
    schema = build_schemas()[schema_name]
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        validate_json(contract.model, json.dumps(instance))


def test_record_semantic_invariant_is_honestly_model_only() -> None:
    """Do not claim JSON Schema can compare manifest digest fields dynamically."""
    contract = ROOT_CONTRACTS["manifest.schema.json"]
    fixture_path = FIXTURE_DIR / contract.fixture_name
    instance: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    instance["version_id"] = "sha256:" + "9" * 64
    schema = build_schemas()["manifest.schema.json"]
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)
    with pytest.raises(ValidationError, match="version_id"):
        validate_json(contract.model, json.dumps(instance))


def test_block_non_null_content_is_schema_expressible() -> None:
    """Reject the former all-null payload defect in both validation layers."""
    contract = ROOT_CONTRACTS["block.schema.json"]
    fixture_path = FIXTURE_DIR / contract.fixture_name
    instance: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    for field in ("text", "structured", "asset_id"):
        instance[field] = None
    schema = build_schemas()["block.schema.json"]
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)
    with pytest.raises(ValidationError, match="content"):
        validate_json(contract.model, json.dumps(instance))


def test_schema_builder_returns_independent_values() -> None:
    """Prevent one consumer from mutating a later schema generation result."""
    first = build_schemas()
    mutated = deepcopy(first)
    mutated["manifest.schema.json"]["title"] = "changed"
    assert build_schemas() == first


@pytest.mark.parametrize("schema_name", sorted(ROOT_CONTRACTS))
@pytest.mark.parametrize(
    ("version", "message"),
    (
        ("invalid", "semantic version"),
        ("0.2.0", "is not installed"),
        ("1.0.0", "unsupported schema major"),
    ),
)
def test_every_root_distinguishes_version_failure_categories(
    schema_name: str,
    version: str,
    message: str,
) -> None:
    """Reject malformed, uninstalled and unsupported-major contracts distinctly."""
    contract = ROOT_CONTRACTS[schema_name]
    fixture_path = FIXTURE_DIR / contract.fixture_name
    instance: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    instance[contract.version_field] = version

    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()[schema_name]).validate(instance)
    with pytest.raises(ValidationError, match=message):
        validate_json(contract.model, json.dumps(instance))


def test_generated_schemas_are_valid_stable_reviewed_bytes() -> None:
    """Make generator drift and invalid Draft 2020-12 output fail byte-for-byte."""
    first = build_schemas()
    second = build_schemas()
    assert first == second
    assert check_schemas() == []

    for schema_name, contract in ROOT_CONTRACTS.items():
        generated = first[schema_name]
        Draft202012Validator.check_schema(generated)
        assert generated["$schema"] == DRAFT_2020_12
        assert generated["$id"] == contract.schema_id
        assert generated["title"] == contract.title
        assert generated["x-openardp-schema-version"] == "0.1.0"
        assert generated["properties"][contract.version_field]["const"] == "0.1.0"
        committed = REPOSITORY_ROOT / "schemas" / schema_name
        assert committed.read_bytes() == render_schema(generated)


def test_schema_check_mode_does_not_write_files() -> None:
    """Keep verification read-only while proving the command-line contract."""
    schema_paths = [REPOSITORY_ROOT / "schemas" / name for name in ROOT_CONTRACTS]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in schema_paths}
    completed = subprocess.run(
        [sys.executable, "scripts/generate_schemas.py", "--check"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in schema_paths}
    assert completed.stdout == "all 9 schemas are current\n"
    assert after == before


def test_public_root_traceability_is_complete() -> None:
    """Map every root to one model, reviewed schema, golden and shared test matrix."""
    expected = {
        "block.schema.json": "block.json",
        "context-bundle.schema.json": "context-bundle.json",
        "derivation.schema.json": "derivation.json",
        "manifest.schema.json": "manifest.json",
        "relation.schema.json": "relation.json",
    }
    assert {name: contract.fixture_name for name, contract in ROOT_CONTRACTS.items()} == expected
    for schema_name, fixture_name in expected.items():
        contract = ROOT_CONTRACTS[schema_name]
        assert (REPOSITORY_ROOT / "schemas" / schema_name).is_file()
        assert (FIXTURE_DIR / fixture_name).is_file()
        assert contract.model.__module__.startswith("openardp.domain.")
        assert contract.version_field in {"spec_version", "schema_version"}


@pytest.mark.parametrize(
    ("schema_name", "trust_path"),
    (
        ("block.schema.json", ("trust",)),
        ("derivation.schema.json", ("trust",)),
        ("context-bundle.schema.json", ("items", 0, "trust")),
    ),
)
def test_content_trust_role_is_data_in_schema_and_model(
    schema_name: str,
    trust_path: tuple[str | int, ...],
) -> None:
    """Reject metadata authority labels on every content-bearing root."""
    contract = ROOT_CONTRACTS[schema_name]
    fixture_path = FIXTURE_DIR / contract.fixture_name
    instance: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    target: Any = instance
    for part in trust_path:
        target = target[part]
    target["role"] = "metadata"

    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(build_schemas()[schema_name]).validate(instance)
    with pytest.raises(ValidationError):
        validate_json(contract.model, json.dumps(instance))
