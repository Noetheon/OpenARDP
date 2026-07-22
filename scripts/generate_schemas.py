"""Build, check and explicitly write deterministic public domain schemas."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from openardp.domain.block import ContentBlock
from openardp.domain.common import SCHEMA_VERSION
from openardp.domain.context import ContextBundle
from openardp.domain.derivation import DerivationRecord
from openardp.domain.manifest import DocumentManifest
from openardp.domain.relation import Relation

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas"
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True, slots=True)
class RootContract:
    """Metadata connecting one root model, fixture and public schema."""

    model: type[BaseModel]
    fixture_name: str
    schema_id: str
    title: str
    version_field: str


ROOT_CONTRACTS: dict[str, RootContract] = {
    "block.schema.json": RootContract(
        ContentBlock,
        "block.json",
        "https://openardp.example/schema/block-0.1.0.json",
        "OpenARDP Content Block",
        "schema_version",
    ),
    "context-bundle.schema.json": RootContract(
        ContextBundle,
        "context-bundle.json",
        "https://openardp.example/schema/context-bundle-0.1.0.json",
        "OpenARDP Context Bundle",
        "schema_version",
    ),
    "derivation.schema.json": RootContract(
        DerivationRecord,
        "derivation.json",
        "https://openardp.example/schema/derivation-0.1.0.json",
        "OpenARDP Derivation Record",
        "schema_version",
    ),
    "manifest.schema.json": RootContract(
        DocumentManifest,
        "manifest.json",
        "https://openardp.example/schema/manifest-0.1.0.json",
        "OpenARDP Manifest",
        "spec_version",
    ),
    "relation.schema.json": RootContract(
        Relation,
        "relation.json",
        "https://openardp.example/schema/relation-0.1.0.json",
        "OpenARDP Relation",
        "schema_version",
    ),
}


def _add_block_payload_constraint(schema: dict[str, Any]) -> None:
    schema["anyOf"] = [
        {"properties": {"text": {"type": "string"}}, "required": ["text"]},
        {
            "properties": {"structured": {"type": ["object", "array"]}},
            "required": ["structured"],
        },
        {
            "properties": {"asset_id": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}},
            "required": ["asset_id"],
        },
    ]


def build_schemas() -> dict[str, dict[str, Any]]:
    """Return fresh deterministic Draft 2020-12 schemas for every public root."""
    schemas: dict[str, dict[str, Any]] = {}
    for filename, contract in ROOT_CONTRACTS.items():
        schema = contract.model.model_json_schema(
            mode="validation",
            ref_template="#/$defs/{model}",
        )
        schema["$schema"] = DRAFT_2020_12
        schema["$id"] = contract.schema_id
        schema["title"] = contract.title
        schema["x-openardp-schema-version"] = SCHEMA_VERSION
        if filename == "block.schema.json":
            _add_block_payload_constraint(schema)
        schemas[filename] = schema
    return schemas


def render_schema(schema: dict[str, Any]) -> bytes:
    """Render one schema with stable UTF-8, ordering, indentation and newline."""
    text = json.dumps(
        schema,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )
    return f"{text}\n".encode()


def check_schemas(directory: Path = SCHEMA_DIRECTORY) -> list[str]:
    """Return filenames whose committed bytes differ from generated contracts."""
    drift: list[str] = []
    for filename, schema in build_schemas().items():
        path = directory / filename
        if not path.is_file() or path.read_bytes() != render_schema(schema):
            drift.append(filename)
    return drift


def write_schemas(directory: Path = SCHEMA_DIRECTORY) -> None:
    """Explicitly write every generated schema for human review."""
    directory.mkdir(parents=True, exist_ok=True)
    for filename, schema in build_schemas().items():
        (directory / filename).write_bytes(render_schema(schema))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when committed schemas drift")
    mode.add_argument("--write", action="store_true", help="write generated schemas explicitly")
    return parser


def main() -> int:
    """Run schema check or explicit generation from command-line arguments."""
    arguments = _parser().parse_args()
    if arguments.write:
        write_schemas()
        print(f"wrote {len(ROOT_CONTRACTS)} schemas")
        return 0
    drift = check_schemas()
    if drift:
        print("schema drift: " + ", ".join(drift))
        return 1
    print(f"all {len(ROOT_CONTRACTS)} schemas are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
