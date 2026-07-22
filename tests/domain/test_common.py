"""Tests for strict shared OpenARDP domain value contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.common import (
    CanonicalUuid,
    DocumentId,
    ExtensibleModel,
    InstructionExecutionAllowed,
    Sha256Id,
    SourceLocator,
    SupportedSchemaVersion,
    TrustClassification,
    UtcDatetime,
    validate_json,
)

DOCUMENT_ID = "01890f62-24e8-7c00-8000-000000000001"
BLOCK_ID = "12345678-1234-4234-9234-123456789abc"
DIGEST = "sha256:" + "1" * 64


class StrictEnvelope(ExtensibleModel):
    """Synthetic model exercising the shared public value types."""

    schema_version: SupportedSchemaVersion
    document_id: DocumentId
    block_id: CanonicalUuid
    created_at: UtcDatetime
    digest: Sha256Id
    count: int
    enabled: InstructionExecutionAllowed = False


def _valid_payload() -> dict[str, object]:
    """Return a valid Python-mode payload with already typed values."""
    return {
        "schema_version": "0.1.0",
        "document_id": UUID(DOCUMENT_ID),
        "block_id": UUID(BLOCK_ID),
        "created_at": datetime(2026, 7, 22, 12, 30, tzinfo=UTC),
        "digest": DIGEST,
        "count": 4,
        "extensions": {"example.org/flag": True, "nested": [1, "z", None]},
    }


def test_shared_values_validate_and_serialize_canonically() -> None:
    """Accept typed Python values and emit canonical UUID/UTC text."""
    model = StrictEnvelope.model_validate(_valid_payload())
    dumped = model.model_dump(mode="json")
    assert dumped["document_id"] == DOCUMENT_ID
    assert dumped["block_id"] == BLOCK_ID
    assert dumped["created_at"] == "2026-07-22T12:30:00Z"
    assert dumped["extensions"] == {"example.org/flag": True, "nested": [1, "z", None]}
    with pytest.raises(ValidationError, match="frozen"):
        model.count = 5


@pytest.mark.parametrize(
    ("version", "message"),
    (
        ("not-semver", "semantic version"),
        ("1.0.0", "unsupported schema major"),
        ("0.2.0", "is not installed"),
    ),
)
def test_schema_versions_fail_with_actionable_categories(version: str, message: str) -> None:
    """Distinguish malformed, unsupported-major and uninstalled releases."""
    payload = _valid_payload()
    payload["schema_version"] = version
    with pytest.raises(ValidationError, match=message):
        StrictEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "created_at",
    (
        datetime(2026, 7, 22, 12, 30),
        datetime.fromisoformat("2026-07-22T14:30:00+02:00"),
        1_753_184_600,
    ),
)
def test_non_utc_or_numeric_timestamps_are_rejected(created_at: object) -> None:
    """Require explicit UTC instants instead of local or epoch interpretation."""
    payload = _valid_payload()
    payload["created_at"] = created_at
    with pytest.raises(ValidationError, match=r"UTC|timestamp"):
        StrictEnvelope.model_validate(payload)


def test_json_mode_accepts_zero_offset_and_emits_z() -> None:
    """Accept either RFC 3339 UTC spelling while emitting one spelling."""
    raw = (
        '{"schema_version":"0.1.0","document_id":"'
        + DOCUMENT_ID
        + '","block_id":"'
        + BLOCK_ID
        + '","created_at":"2026-07-22T12:30:00+00:00","digest":"'
        + DIGEST
        + '","count":4,"extensions":{}}'
    )
    model = validate_json(StrictEnvelope, raw)
    assert model.model_dump(mode="json")["created_at"] == "2026-07-22T12:30:00Z"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("document_id", UUID(BLOCK_ID), "UUIDv7"),
        ("document_id", DOCUMENT_ID.upper(), "canonical lowercase"),
        ("block_id", BLOCK_ID.upper(), "canonical lowercase"),
        ("digest", "sha256:" + "A" * 64, "string_pattern_mismatch"),
        ("count", "4", "valid integer"),
        ("enabled", 0, "valid boolean"),
    ),
)
def test_shared_values_do_not_silently_coerce(
    field: str,
    value: object,
    message: str,
) -> None:
    """Reject alternate spellings and scalar type coercion."""
    payload = _valid_payload()
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        StrictEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "extensions",
    (
        {"not-json": {1, 2}},
        {"unsafe-int": 9_007_199_254_740_992},
        {1: "non-string-key"},
    ),
)
def test_extensions_accept_only_interoperable_json(extensions: object) -> None:
    """Reject runtime-only or non-interoperable extension values."""
    payload = _valid_payload()
    payload["extensions"] = extensions
    with pytest.raises(ValidationError, match=r"JSON|safe integer|string key"):
        StrictEnvelope.model_validate(payload)


def test_unknown_direct_fields_are_rejected() -> None:
    """Route extensions explicitly instead of ignoring misspelled core fields."""
    payload = _valid_payload()
    payload["surprise"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StrictEnvelope.model_validate(payload)


def test_duplicate_json_names_are_rejected_before_model_validation() -> None:
    """Prevent parser-dependent last-name-wins behavior at public boundaries."""
    raw = (
        '{"schema_version":"0.1.0","schema_version":"0.1.0",'
        f'"document_id":"{DOCUMENT_ID}","block_id":"{BLOCK_ID}",'
        f'"created_at":"2026-07-22T12:30:00Z","digest":"{DIGEST}",'
        '"count":4,"extensions":{}}'
    )
    with pytest.raises(ValueError, match="duplicate JSON object name"):
        validate_json(StrictEnvelope, raw)


@pytest.mark.parametrize(
    ("fragment", "message"),
    (
        ("NaN", "non-standard JSON numeric constant"),
        ("Infinity", "non-standard JSON numeric constant"),
        ("-Infinity", "non-standard JSON numeric constant"),
        ("9007199254740992", "safe integer range"),
        ("-9007199254740992", "safe integer range"),
    ),
)
def test_raw_json_rejects_ambiguous_numeric_values(fragment: str, message: str) -> None:
    """Reject non-standard constants and unsafe integers before model validation."""
    raw = (
        '{"schema_version":"0.1.0","document_id":"'
        + DOCUMENT_ID
        + '","block_id":"'
        + BLOCK_ID
        + '","created_at":"2026-07-22T12:30:00Z","digest":"'
        + DIGEST
        + '","count":'
        + fragment
        + ',"extensions":{}}'
    )
    with pytest.raises(ValueError, match=message):
        validate_json(StrictEnvelope, raw)


def test_raw_json_rejects_lone_surrogates_and_scalar_coercion() -> None:
    """Keep malformed Unicode and JSON string-to-number coercion out of the boundary."""
    base = (
        '{"schema_version":"0.1.0","document_id":"'
        + DOCUMENT_ID
        + '","block_id":"'
        + BLOCK_ID
        + '","created_at":"2026-07-22T12:30:00Z","digest":"'
        + DIGEST
    )
    with pytest.raises(ValueError, match="invalid Unicode"):
        validate_json(StrictEnvelope, base + '","count":4,"extensions":{"bad":"\\ud800"}}')
    with pytest.raises(ValidationError, match="valid integer"):
        validate_json(StrictEnvelope, base + '","count":"4","extensions":{}}')


def test_document_content_can_never_authorize_instruction_execution() -> None:
    """Keep the document boundary fixed to data regardless of input."""
    trust = {
        "zone": "external_untrusted",
        "role": "data",
        "instruction_execution_allowed": True,
        "integrity": "verified_sha256",
        "sensitivity": "internal",
    }
    with pytest.raises(ValidationError, match="False"):
        TrustClassification.model_validate(trust)


@pytest.mark.parametrize(
    ("created_at", "message"),
    (
        ("2026-07-22T12:30:00", "ending in Z"),
        ("2026-99-99T99:99:99Z", "valid RFC 3339"),
    ),
)
def test_raw_json_rejects_invalid_utc_text(created_at: str, message: str) -> None:
    """Exercise both the UTC suffix and calendar/time validation branches."""
    raw = (
        '{"schema_version":"0.1.0","document_id":"'
        + DOCUMENT_ID
        + '","block_id":"'
        + BLOCK_ID
        + '","created_at":"'
        + created_at
        + '","digest":"'
        + DIGEST
        + '","count":4,"extensions":{}}'
    )
    with pytest.raises(ValidationError, match=message):
        validate_json(StrictEnvelope, raw)


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ({"page": 1, "slide": 1}, "both page and slide"),
        ({"bbox": (0.0, 0.0, 1.0, 1.0)}, "requires a page or slide"),
        ({"page": 1, "bbox": (2.0, 0.0, 1.0, 1.0)}, "x_min <= x_max"),
    ),
)
def test_source_locator_rejects_ambiguous_coordinates(
    change: dict[str, object],
    message: str,
) -> None:
    """Reject ambiguous and inverted source-coordinate descriptions."""
    payload: dict[str, object] = {"extraction_method": "synthetic", **change}
    with pytest.raises(ValidationError, match=message):
        SourceLocator.model_validate(payload)


def test_source_locator_accepts_a_coordinate_free_native_location() -> None:
    """Allow non-paginated formats to identify a native object without a box."""
    locator = SourceLocator.model_validate(
        {"extraction_method": "office-xml", "native_id": "paragraph-1"}
    )
    assert locator.page is None
    assert locator.slide is None
    assert locator.bbox is None
