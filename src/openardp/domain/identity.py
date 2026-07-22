"""RFC 8785 canonicalization and explicit SHA-256 domain identities."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

import rfc8785
from pydantic import JsonValue

from openardp.domain.common import ensure_json_value

CANONICALIZATION_ALGORITHM = "RFC8785"
IDENTITY_VERSION = 1

_SHA256_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_RELATION_REFERENCE_FIELDS = {
    "artifact": frozenset({"record_type", "artifact_id"}),
    "block": frozenset(
        {"record_type", "document_id", "version_id", "representation_id", "block_id"}
    ),
    "document_version": frozenset({"record_type", "document_id", "version_id"}),
    "external": frozenset({"record_type", "namespace", "record_id"}),
}
_RELATION_REFERENCE_HASH_FIELDS = frozenset({"artifact_id", "version_id", "representation_id"})


class CanonicalizationError(ValueError):
    """Raised when a value is outside the supported canonical JSON domain."""


def canonical_json_bytes(value: JsonValue) -> bytes:
    """Serialize one JCS/I-JSON value to RFC 8785 canonical UTF-8 bytes."""
    try:
        ensure_json_value(value)
        encoded = rfc8785.dumps(value)
    except (ValueError, rfc8785.CanonicalizationError, RecursionError) as error:
        raise CanonicalizationError(str(error)) from error
    if not isinstance(encoded, bytes):
        raise CanonicalizationError("RFC 8785 encoder did not return bytes")
    return encoded


def canonical_sha256(value: JsonValue) -> str:
    """Return a lowercase SHA-256 identifier over canonical JSON bytes."""
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def source_version_id(source_bytes: bytes) -> str:
    """Return the documented direct SHA-256 identity of original source bytes."""
    return "sha256:" + hashlib.sha256(source_bytes).hexdigest()


def _require_sha256_id(value: str, *, field: str) -> str:
    if _SHA256_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be sha256: followed by 64 lowercase hexadecimal characters")
    return value


def _identity_sha256(domain: str, payload: dict[str, JsonValue]) -> str:
    envelope: dict[str, JsonValue] = {
        "canonicalization": CANONICALIZATION_ALGORITHM,
        "domain": domain,
        "identity_version": IDENTITY_VERSION,
        "payload": payload,
    }
    return canonical_sha256(envelope)


def representation_id(
    *,
    version_id: str,
    parser_name: str,
    parser_version: str,
    parser_profile: str,
    parser_config_hash: str,
    normalization_schema_version: str,
) -> str:
    """Hash the exact source, parser recipe and normalization contract."""
    payload: dict[str, JsonValue] = {
        "version_id": _require_sha256_id(version_id, field="version_id"),
        "parser": {
            "name": parser_name,
            "version": parser_version,
            "profile": parser_profile,
            "config_hash": _require_sha256_id(parser_config_hash, field="parser_config_hash"),
        },
        "normalization_schema_version": normalization_schema_version,
    }
    return _identity_sha256("openardp:representation", payload)


def block_content_hash(
    *,
    kind: str,
    text: str | None,
    structured: dict[str, JsonValue] | list[JsonValue] | None,
    asset_id: str | None,
) -> str:
    """Hash normalized block content without location or operational metadata."""
    payload: dict[str, JsonValue] = {
        "kind": kind,
        "text": text,
        "structured": structured,
        "asset_id": (
            _require_sha256_id(asset_id, field="asset_id") if asset_id is not None else None
        ),
    }
    return _identity_sha256("openardp:block-content", payload)


def derivation_artifact_id(
    *,
    input_hashes: Sequence[str],
    generator_name: str,
    generator_version: str,
    generator_profile: str | None,
    model_id: str | None,
    config_hash: str,
    prompt_hash: str | None,
) -> str:
    """Hash an ordered derivation recipe independently of its produced bytes."""
    inputs: list[JsonValue] = [
        _require_sha256_id(value, field="input_hashes") for value in input_hashes
    ]
    payload: dict[str, JsonValue] = {
        "input_hashes": inputs,
        "generator": {
            "name": generator_name,
            "version": generator_version,
            "profile": generator_profile,
        },
        "model_id": model_id,
        "config_hash": _require_sha256_id(config_hash, field="config_hash"),
        "prompt_hash": (
            _require_sha256_id(prompt_hash, field="prompt_hash")
            if prompt_hash is not None
            else None
        ),
    }
    return _identity_sha256("openardp:derivation", payload)


def _relation_reference_payload(
    reference: dict[str, JsonValue],
    *,
    field: str,
) -> dict[str, JsonValue]:
    """Return one allowlisted v1 relation endpoint identity projection."""
    ensure_json_value(reference, path=f"$.{field}")
    record_type = reference.get("record_type")
    if not isinstance(record_type, str) or record_type not in _RELATION_REFERENCE_FIELDS:
        supported = ", ".join(sorted(_RELATION_REFERENCE_FIELDS))
        raise ValueError(f"{field}.record_type must be one of: {supported}")
    expected = _RELATION_REFERENCE_FIELDS[record_type]
    provided = set(reference).difference({"extensions"})
    missing = expected.difference(provided)
    if missing:
        raise ValueError(f"{field} is missing identity fields: {', '.join(sorted(missing))}")
    undeclared = provided.difference(expected)
    if undeclared:
        raise ValueError(f"{field} contains undeclared fields: {', '.join(sorted(undeclared))}")

    payload: dict[str, JsonValue] = {}
    for name in expected:
        value = reference[name]
        if name in _RELATION_REFERENCE_HASH_FIELDS:
            if not isinstance(value, str):
                raise ValueError(f"{field}.{name} must be a SHA-256 identifier")
            value = _require_sha256_id(value, field=f"{field}.{name}")
        payload[name] = value
    return payload


def relation_identity(
    *,
    kind: str,
    source: dict[str, JsonValue],
    target: dict[str, JsonValue],
) -> str:
    """Hash one directed semantic edge from its complete typed references."""
    payload: dict[str, JsonValue] = {
        "kind": kind,
        "source": _relation_reference_payload(source, field="source"),
        "target": _relation_reference_payload(target, field="target"),
    }
    return _identity_sha256("openardp:relation", payload)
