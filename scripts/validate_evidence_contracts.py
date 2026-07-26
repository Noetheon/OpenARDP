"""Validate the public F006 evidence conformance corpus without runtime adapters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ValidationError

from openardp.domain.common import validate_json
from openardp.domain.evidence import (
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    TrustClassification,
    validate_evidence_records,
)
from openardp.domain.identity import canonical_json_bytes, canonical_sha256

MODEL_TYPES: dict[str, type[BaseModel]] = {
    "native_representation": NativeRepresentation,
    "evidence_reference": EvidenceReference,
    "evidence_projection": EvidenceProjection,
    "trust_classification": TrustClassification,
}


def _confined_path(root: Path, relative: object) -> Path:
    if not isinstance(relative, str):
        raise ValueError("fixture path must be a string")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError("fixture path must be relative and traversal-free")
    candidate = (root / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("fixture path escapes the conformance root") from error
    if not candidate.is_file():
        raise ValueError(f"fixture path is not a regular file: {relative}")
    return candidate


def _load_manifest(path: Path) -> tuple[Path, dict[str, Any]]:
    manifest_path = path.resolve()
    if not manifest_path.is_file():
        raise ValueError("manifest is not a regular file")
    decoded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("manifest root must be an object")
    return manifest_path.parent, decoded


def _entry(entry: object) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("manifest entry must be an object")
    return entry


def _model(entry: dict[str, Any]) -> type[BaseModel]:
    name = entry.get("model")
    if not isinstance(name, str) or name not in MODEL_TYPES:
        raise ValueError("manifest entry has an unsupported model")
    return MODEL_TYPES[name]


def _validate_valid(root: Path, entries: object) -> int:
    if not isinstance(entries, list):
        raise ValueError("valid manifest entries must be an array")
    for raw_entry in entries:
        entry = _entry(raw_entry)
        validate_json(_model(entry), _confined_path(root, entry.get("path")).read_bytes())
    return len(entries)


def _validate_invalid(root: Path, entries: object) -> int:
    if not isinstance(entries, list):
        raise ValueError("invalid manifest entries must be an array")
    for raw_entry in entries:
        entry = _entry(raw_entry)
        expected = entry.get("error_contains")
        if not isinstance(expected, str) or not expected:
            raise ValueError("invalid entry requires error_contains")
        try:
            validate_json(_model(entry), _confined_path(root, entry.get("path")).read_bytes())
        except (ValidationError, ValueError) as error:
            if expected not in str(error):
                raise ValueError("invalid fixture failed for an unexpected category") from error
        else:
            raise ValueError("invalid fixture was accepted")
    return len(entries)


def _typed_record[RecordT: BaseModel](
    model: type[RecordT],
    root: Path,
    relative: object,
) -> RecordT:
    return validate_json(model, _confined_path(root, relative).read_bytes())


def _validate_record_sets(root: Path, entries: object) -> int:
    if not isinstance(entries, list):
        raise ValueError("record_sets must be an array")
    for raw_entry in entries:
        entry = _entry(raw_entry)
        reference_paths = entry.get("references")
        projection_paths = entry.get("projections")
        if not isinstance(reference_paths, list) or not isinstance(projection_paths, list):
            raise ValueError("record set references and projections must be arrays")
        native = _typed_record(NativeRepresentation, root, entry.get("native"))
        references = [
            _typed_record(EvidenceReference, root, relative) for relative in reference_paths
        ]
        projections = [
            _typed_record(EvidenceProjection, root, relative) for relative in projection_paths
        ]
        expected = entry.get("expected_source_version_id")
        if expected is not None and not isinstance(expected, str):
            raise ValueError("expected_source_version_id must be a string")
        validate_evidence_records(
            native,
            references,
            projections,
            expected_source_version_id=expected,
        )
    return len(entries)


def _validate_vectors(root: Path, manifest: dict[str, Any]) -> int:
    vectors_path = _confined_path(root, manifest.get("canonicalization_vectors"))
    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
    if not isinstance(vectors, dict):
        raise ValueError("canonicalization vectors must be an object")
    if (
        vectors.get("contract_version") != "0.1.0"
        or vectors.get("canonicalization") != "RFC8785"
        or vectors.get("identity_version") != 1
    ):
        raise ValueError("canonicalization vector metadata mismatch")
    cases = vectors.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("canonicalization vector cases must be a non-empty array")
    names: set[str] = set()
    for raw_case in cases:
        case = _entry(raw_case)
        name = case.get("name")
        envelope = case.get("envelope")
        canonical = case.get("canonical")
        digest = case.get("sha256")
        if not isinstance(name, str) or not isinstance(envelope, dict):
            raise ValueError("canonicalization vector case is malformed")
        if name in names:
            raise ValueError("canonicalization vector names must be unique")
        names.add(name)
        if not isinstance(canonical, str) or not isinstance(digest, str):
            raise ValueError("canonicalization vector outputs must be strings")
        if canonical_json_bytes(envelope).decode() != canonical:
            raise ValueError("canonical JSON vector mismatch")
        if canonical_sha256(envelope) != digest:
            raise ValueError("canonical SHA-256 vector mismatch")
    return len(cases)


def validate_manifest(path: Path) -> tuple[int, int, int, int]:
    """Validate one confined manifest and return deterministic category counts."""
    root, manifest = _load_manifest(path)
    if manifest.get("contract_version") != "0.1.0":
        raise ValueError("manifest contract_version must be 0.1.0")
    return (
        _validate_valid(root, manifest.get("valid")),
        _validate_invalid(root, manifest.get("invalid")),
        _validate_record_sets(root, manifest.get("record_sets")),
        _validate_vectors(root, manifest),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    return parser


def main() -> int:
    """Run adapter-independent evidence conformance validation."""
    counts = validate_manifest(_parser().parse_args().manifest)
    print(
        "Evidence conformance passed: "
        f"{counts[0]} valid, {counts[1]} invalid, "
        f"{counts[2]} record set, {counts[3]} identity vectors."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
