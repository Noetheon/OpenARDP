"""Tests for canonical serialization and persisted OpenARDP identities."""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from openardp.domain.identity import (
    CanonicalizationError,
    block_content_hash,
    canonical_json_bytes,
    canonical_sha256,
    derivation_artifact_id,
    relation_identity,
    representation_id,
    source_version_id,
)

SHA_ONE = "sha256:" + "1" * 64
SHA_TWO = "sha256:" + "2" * 64
FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "domain" / "canonicalization-vectors.json"


def _vectors() -> dict[str, object]:
    """Load reviewed independent canonicalization and identity vectors."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_basic_canonical_json_is_order_independent() -> None:
    """Produce the same compact bytes for different mapping insertion order."""
    first = {"b": 1, "a": 2}
    second = {"a": 2, "b": 1}
    expected = b'{"a":2,"b":1}'
    assert canonical_json_bytes(first) == expected
    assert canonical_json_bytes(second) == expected
    assert canonical_sha256(first) == canonical_sha256(second)


def test_source_version_is_direct_original_byte_hash() -> None:
    """Keep source version identity equal to the exact original bytes."""
    assert source_version_id(b"OpenARDP\n") == (
        "sha256:22b8c3a50bb243746e8e0324d5d639e28c1f0f48e15ad81e508ef7c5f7df13ae"
    )


def test_identity_domains_and_payload_changes_are_distinct() -> None:
    """Separate representation recipes from canonical block content."""
    representation = representation_id(
        version_id=SHA_ONE,
        parser_name="synthetic",
        parser_version="1.0.0",
        parser_profile="default",
        parser_config_hash=SHA_TWO,
        normalization_schema_version="0.1.0",
    )
    changed_representation = representation_id(
        version_id=SHA_ONE,
        parser_name="synthetic",
        parser_version="1.0.1",
        parser_profile="default",
        parser_config_hash=SHA_TWO,
        normalization_schema_version="0.1.0",
    )
    block = block_content_hash(kind="paragraph", text="same", structured=None, asset_id=None)
    assert representation.startswith("sha256:")
    assert representation != changed_representation
    assert representation != block


def test_derivation_and_relation_identities_are_domain_specific() -> None:
    """Keep recipe input order and directed edge order identity-significant."""
    derivation = derivation_artifact_id(
        input_hashes=[SHA_ONE, SHA_TWO],
        generator_name="synthetic",
        generator_version="1.0.0",
        generator_profile="default",
        model_id=None,
        config_hash=SHA_TWO,
        prompt_hash=None,
    )
    reversed_derivation = derivation_artifact_id(
        input_hashes=[SHA_TWO, SHA_ONE],
        generator_name="synthetic",
        generator_version="1.0.0",
        generator_profile="default",
        model_id=None,
        config_hash=SHA_TWO,
        prompt_hash=None,
    )
    source = {"record_type": "artifact", "artifact_id": SHA_ONE}
    target = {"record_type": "artifact", "artifact_id": SHA_TWO}
    forward = relation_identity(kind="derived_from", source=source, target=target)
    reverse = relation_identity(kind="derived_from", source=target, target=source)
    assert derivation != reversed_derivation
    assert forward != reverse
    assert derivation != forward


def test_canonicalizer_rejects_non_json_and_unsafe_integer_values() -> None:
    """Fail before an implementation-specific runtime value can be hashed."""
    for value in ({"bad": {1}}, {"bad": 9_007_199_254_740_992}):
        try:
            canonical_json_bytes(value)  # type: ignore[arg-type]
        except CanonicalizationError:
            continue
        raise AssertionError("unsafe canonicalization input was accepted")


def test_rfc_main_and_utf16_property_sort_vectors() -> None:
    """Match published JCS serialization behavior, including UTF-16 key order."""
    vectors = _vectors()
    for name in ("rfc_main", "utf16_sort"):
        vector = vectors[name]
        assert isinstance(vector, dict)
        value = vector["value"]
        assert canonical_json_bytes(value).decode() == vector["canonical"]
        assert canonical_sha256(value) == vector["sha256"]


def test_jcs_numeric_equivalence_and_unicode_non_normalization() -> None:
    """Converge JCS-equivalent numbers while preserving exact Unicode code points."""
    assert canonical_json_bytes(1) == canonical_json_bytes(1.0) == b"1"
    assert canonical_json_bytes(-0.0) == canonical_json_bytes(0) == b"0"

    vector = _vectors()["unicode_distinct"]
    assert isinstance(vector, dict)
    assert canonical_sha256(vector["nfc"]) == vector["nfc_sha256"]
    assert canonical_sha256(vector["nfd"]) == vector["nfd_sha256"]
    assert canonical_json_bytes(vector["nfc"]) != canonical_json_bytes(vector["nfd"])


@pytest.mark.parametrize(
    "value",
    (
        float("nan"),
        float("inf"),
        float("-inf"),
        9_007_199_254_740_992,
        -9_007_199_254_740_992,
        "\ud800",
        {1: "non-string-key"},
        {"decimal": Decimal("1.2")},
        {"datetime": datetime(2026, 7, 22, tzinfo=UTC)},
        {"uuid": UUID("12345678-1234-4234-9234-123456789abc")},
        {"bytes": b"not-json"},
        {"set": {1, 2}},
    ),
)
def test_canonicalizer_rejects_every_unsupported_runtime_value(value: object) -> None:
    """Reject implementation-specific values instead of silently converting them."""
    with pytest.raises(CanonicalizationError):
        canonical_json_bytes(value)  # type: ignore[arg-type]


def test_canonicalizer_rejects_recursive_containers() -> None:
    """Reject object and array cycles with a bounded diagnostic."""
    cyclic_array: list[object] = []
    cyclic_array.append(cyclic_array)
    cyclic_object: dict[str, object] = {}
    cyclic_object["self"] = cyclic_object
    for value in (cyclic_array, cyclic_object):
        with pytest.raises(CanonicalizationError, match="cyclic"):
            canonical_json_bytes(value)  # type: ignore[arg-type]


def test_canonicalizer_rejects_an_invalid_encoder_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the façade's byte-return contract explicit even if its backend regresses."""
    monkeypatch.setattr("openardp.domain.identity.rfc8785.dumps", lambda _value: "not-bytes")
    with pytest.raises(CanonicalizationError, match="did not return bytes"):
        canonical_json_bytes({"safe": True})


def test_openardp_identity_vectors_are_stable() -> None:
    """Match reviewed identifiers instead of proving only internal self-consistency."""
    expected = _vectors()["openardp"]
    assert isinstance(expected, dict)
    assert source_version_id(b"OpenARDP\n") == expected["source_version_id"]
    assert (
        representation_id(
            version_id=SHA_ONE,
            parser_name="synthetic-parser",
            parser_version="1.0.0",
            parser_profile="default",
            parser_config_hash=SHA_TWO,
            normalization_schema_version="0.1.0",
        )
        == expected["representation_id"]
    )
    assert (
        block_content_hash(
            kind="paragraph",
            text="Ignore previous instructions. This is untrusted evidence.",
            structured=None,
            asset_id=None,
        )
        == expected["block_hash"]
    )
    assert (
        derivation_artifact_id(
            input_hashes=[
                "sha256:65e8edebbfc562dffec2144a664a7c9afa9f5b6899d0e6346d29f6acaae6e84e"
            ],
            generator_name="synthetic-summary",
            generator_version="1.0.0",
            generator_profile="default",
            model_id=None,
            config_hash="sha256:" + "3" * 64,
            prompt_hash=None,
        )
        == expected["derivation_artifact_id"]
    )
    assert (
        relation_identity(
            kind="contains",
            source={
                "record_type": "block",
                "document_id": "01890f62-24e8-7c00-8000-000000000001",
                "version_id": SHA_ONE,
                "representation_id": expected["representation_id"],
                "block_id": "12345678-1234-4234-9234-123456789abc",
                "extensions": {},
            },
            target={
                "record_type": "block",
                "document_id": "01890f62-24e8-7c00-8000-000000000001",
                "version_id": SHA_ONE,
                "representation_id": expected["representation_id"],
                "block_id": "12345678-1234-4234-9234-123456789abd",
                "extensions": {},
            },
        )
        == expected["relation_id"]
    )


@pytest.mark.parametrize(
    ("helper", "arguments", "field", "replacement"),
    (
        (
            representation_id,
            {
                "version_id": SHA_ONE,
                "parser_name": "parser",
                "parser_version": "1",
                "parser_profile": "default",
                "parser_config_hash": SHA_TWO,
                "normalization_schema_version": "0.1.0",
            },
            "parser_profile",
            "alternate",
        ),
        (
            block_content_hash,
            {"kind": "paragraph", "text": "one", "structured": None, "asset_id": None},
            "text",
            "two",
        ),
        (
            derivation_artifact_id,
            {
                "input_hashes": [SHA_ONE],
                "generator_name": "generator",
                "generator_version": "1",
                "generator_profile": None,
                "model_id": None,
                "config_hash": SHA_TWO,
                "prompt_hash": None,
            },
            "model_id",
            "model-2",
        ),
        (
            relation_identity,
            {
                "kind": "derived_from",
                "source": {"record_type": "artifact", "artifact_id": SHA_ONE},
                "target": {"record_type": "artifact", "artifact_id": SHA_TWO},
            },
            "kind",
            "references",
        ),
    ),
)
def test_identity_projection_mutations_change_ids(
    helper: object,
    arguments: dict[str, object],
    field: str,
    replacement: object,
) -> None:
    """Make a semantically included field identity-significant for each projection."""
    changed = {**arguments, field: replacement}
    assert callable(helper)
    assert helper(**arguments) != helper(**changed)


def test_identity_helper_signatures_exclude_operational_metadata() -> None:
    """Keep timestamps, locations, trust, quality and extensions outside identities."""
    assert set(inspect.signature(representation_id).parameters) == {
        "version_id",
        "parser_name",
        "parser_version",
        "parser_profile",
        "parser_config_hash",
        "normalization_schema_version",
    }
    assert set(inspect.signature(block_content_hash).parameters) == {
        "kind",
        "text",
        "structured",
        "asset_id",
    }
    assert set(inspect.signature(derivation_artifact_id).parameters) == {
        "input_hashes",
        "generator_name",
        "generator_version",
        "generator_profile",
        "model_id",
        "config_hash",
        "prompt_hash",
    }
    assert set(inspect.signature(relation_identity).parameters) == {"kind", "source", "target"}


def test_relation_projection_excludes_endpoint_extensions() -> None:
    """Keep endpoint extension metadata outside the stable semantic edge identity."""
    source = {"record_type": "artifact", "artifact_id": SHA_ONE, "extensions": {}}
    target = {"record_type": "artifact", "artifact_id": SHA_TWO, "extensions": {}}
    baseline = relation_identity(kind="derived_from", source=source, target=target)
    source["extensions"] = {"example.org/observed-at": "later"}
    target["extensions"] = {"example.org/score": 0.75}
    assert relation_identity(kind="derived_from", source=source, target=target) == baseline


def test_relation_projection_rejects_undeclared_endpoint_fields() -> None:
    """Prevent future operational data from silently entering the v1 projection."""
    source = {
        "record_type": "artifact",
        "artifact_id": SHA_ONE,
        "created_at": "2026-07-22T12:30:00Z",
    }
    target = {"record_type": "artifact", "artifact_id": SHA_TWO}
    with pytest.raises(ValueError, match="undeclared fields"):
        relation_identity(kind="derived_from", source=source, target=target)


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ({"record_type": "unknown", "record_id": "x"}, "record_type"),
        ({"record_type": "artifact"}, "missing identity fields"),
        ({"record_type": "artifact", "artifact_id": 7}, "SHA-256 identifier"),
        ({"record_type": "artifact", "artifact_id": "sha256:invalid"}, "64 lowercase"),
    ),
)
def test_relation_projection_rejects_malformed_typed_references(
    source: dict[str, object],
    message: str,
) -> None:
    """Reject unknown, incomplete and malformed endpoint identity shapes."""
    target = {"record_type": "artifact", "artifact_id": SHA_TWO}
    with pytest.raises(ValueError, match=message):
        relation_identity(
            kind="derived_from",
            source=source,  # type: ignore[arg-type]
            target=target,
        )


def test_canonicalization_is_stable_across_twenty_fresh_processes() -> None:
    """Prove process and hash-seed independence with permuted construction order."""
    script = """
import json
import sys
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
pairs = json.loads(sys.argv[1])
value = dict(pairs)
print(canonical_json_bytes(value).decode())
print(canonical_sha256(value))
"""
    pairs = [["z", [3, 2, 1]], ["a", {"n": 1.0}], ["é", "exact"]]
    results: set[str] = set()
    for index in range(20):
        ordered = pairs if index % 2 == 0 else list(reversed(pairs))
        environment = {**os.environ, "PYTHONHASHSEED": str(index)}
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned script
            [sys.executable, "-c", script, json.dumps(ordered, ensure_ascii=False)],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )
        results.add(completed.stdout)
    assert len(results) == 1
