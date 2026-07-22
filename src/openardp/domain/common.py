"""Shared pure value contracts for OpenARDP domain records."""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    PlainSerializer,
    Strict,
    StringConstraints,
    ValidationInfo,
    WithJsonSchema,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "0.1.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})
SUPPORTED_SCHEMA_MAJOR = 0
MAX_SAFE_INTEGER = 9_007_199_254_740_991

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_SHA256_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_CANONICAL_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_CANONICAL_UUID7 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_UTC_RFC3339_END = re.compile(r"T.+(?:Z|\+00:00)$")


def _validate_supported_schema_version(value: object) -> object:
    if not isinstance(value, str) or _SEMVER.fullmatch(value) is None:
        raise ValueError("schema version must be semantic version MAJOR.MINOR.PATCH")
    major = int(value.split(".", maxsplit=1)[0])
    if major != SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(
            f"unsupported schema major {major}; supported major: {SUPPORTED_SCHEMA_MAJOR}"
        )
    if value not in SUPPORTED_SCHEMA_VERSIONS:
        installed = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
        raise ValueError(f"schema version {value} is not installed; supported: {installed}")
    return value


def _validate_uuid_text(value: object) -> object:
    if isinstance(value, str) and _CANONICAL_UUID.fullmatch(value) is None:
        raise ValueError("UUID text must use canonical lowercase hyphenated form")
    return value


def _validate_uuid7_text(value: object) -> object:
    if isinstance(value, str) and _CANONICAL_UUID7.fullmatch(value) is None:
        raise ValueError("document_id must be a canonical lowercase UUIDv7")
    return value


def _ensure_uuid7(value: UUID) -> UUID:
    if value.version != 7:
        raise ValueError("document_id must be UUIDv7")
    return value


def _serialize_uuid(value: UUID) -> str:
    return str(value)


def _validate_datetime_input(value: object, info: ValidationInfo) -> object:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        raise ValueError("numeric timestamps are not accepted")
    if isinstance(value, str):
        if _UTC_RFC3339_END.search(value) is None:
            raise ValueError("timestamp must be an RFC 3339 UTC value ending in Z or +00:00")
        if info.mode == "json":
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError("timestamp must be a valid RFC 3339 value") from error
    return value


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must use UTC, not a non-zero offset")
    return value.astimezone(UTC)


def _serialize_utc(value: datetime) -> str:
    return value.isoformat(timespec="auto").replace("+00:00", "Z")


SupportedSchemaVersion = Annotated[
    str,
    BeforeValidator(_validate_supported_schema_version),
    StringConstraints(strict=True),
    WithJsonSchema({"type": "string", "const": SCHEMA_VERSION}, mode="validation"),
]
Sha256Id = Annotated[str, StringConstraints(strict=True, pattern=_SHA256_ID.pattern)]
Sha256Hex = Annotated[str, StringConstraints(strict=True, pattern=_SHA256_HEX.pattern)]
NonEmptyStr = Annotated[str, StringConstraints(strict=True, min_length=1)]
CanonicalUuid = Annotated[
    UUID,
    BeforeValidator(_validate_uuid_text),
    PlainSerializer(_serialize_uuid, return_type=str),
    WithJsonSchema(
        {"type": "string", "format": "uuid", "pattern": _CANONICAL_UUID.pattern},
        mode="validation",
    ),
]
DocumentId = Annotated[
    UUID,
    BeforeValidator(_validate_uuid7_text),
    AfterValidator(_ensure_uuid7),
    PlainSerializer(_serialize_uuid, return_type=str),
    WithJsonSchema(
        {"type": "string", "format": "uuid", "pattern": _CANONICAL_UUID7.pattern},
        mode="validation",
    ),
]
UtcDatetime = Annotated[
    datetime,
    BeforeValidator(_validate_datetime_input),
    AfterValidator(_ensure_utc),
    PlainSerializer(_serialize_utc, return_type=str),
    WithJsonSchema(
        {
            "type": "string",
            "format": "date-time",
            "pattern": r"T.+(?:Z|\+00:00)$",
        },
        mode="validation",
    ),
]


def _ensure_instruction_execution_false(value: bool) -> bool:
    if value is not False:
        raise ValueError("instruction_execution_allowed must be False")
    return value


InstructionExecutionAllowed = Annotated[
    bool,
    Strict(),
    AfterValidator(_ensure_instruction_execution_false),
    WithJsonSchema({"type": "boolean", "const": False}, mode="validation"),
]


class DomainModel(BaseModel):
    """Strict, attribute-frozen base for pure domain records."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        revalidate_instances="always",
        allow_inf_nan=False,
        hide_input_in_errors=True,
    )


def ensure_json_value(
    value: object,
    *,
    path: str = "$",
    _ancestors: set[int] | None = None,
) -> object:
    """Validate an in-memory value against the interoperable JCS/I-JSON subset."""
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as error:
                raise ValueError(f"{path} contains invalid Unicode, not a JSON string") from error
        return value
    if type(value) is int:
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise ValueError(f"{path} integer is outside the interoperable safe integer range")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite JSON numbers")
        return value

    ancestors = set() if _ancestors is None else _ancestors
    if type(value) is list:
        identity = id(value)
        if identity in ancestors:
            raise ValueError(f"{path} contains a cyclic JSON array")
        ancestors.add(identity)
        try:
            for index, item in enumerate(value):
                ensure_json_value(item, path=f"{path}[{index}]", _ancestors=ancestors)
        finally:
            ancestors.remove(identity)
        return value
    if type(value) is dict:
        identity = id(value)
        if identity in ancestors:
            raise ValueError(f"{path} contains a cyclic JSON object")
        ancestors.add(identity)
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{path} JSON object requires a string key")
                ensure_json_value(item, path=f"{path}.{key}", _ancestors=ancestors)
        finally:
            ancestors.remove(identity)
        return value
    raise ValueError(f"{path} must contain only JSON values")


class ExtensibleModel(DomainModel):
    """Strict model that preserves JSON-only namespaced extension data."""

    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_json(cls, value: object) -> object:
        return ensure_json_value(value, path="$.extensions")


class TrustZone(StrEnum):
    """Security boundary assigned to content or metadata."""

    LOCAL_TRUSTED = "local_trusted"
    ORGANIZATION_TRUSTED = "organization_trusted"
    EXTERNAL_UNTRUSTED = "external_untrusted"
    MODEL_DERIVED = "model_derived"


class ContentRole(StrEnum):
    """Authority role of a record at agent boundaries."""

    DATA = "data"
    METADATA = "metadata"


class IntegrityState(StrEnum):
    """Integrity evidence available for a record."""

    VERIFIED_SHA256 = "verified_sha256"
    UNVERIFIED = "unverified"


class Sensitivity(StrEnum):
    """Sensitivity classification carried with content."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class TrustClassification(DomainModel):
    """Non-authoritative trust metadata enforced for content-bearing records."""

    zone: TrustZone
    role: ContentRole
    instruction_execution_allowed: InstructionExecutionAllowed = False
    integrity: IntegrityState
    sensitivity: Sensitivity


class DataTrustClassification(TrustClassification):
    """Trust metadata for content that must remain non-authoritative data."""

    role: Literal[ContentRole.DATA]


class ComponentDescriptor(ExtensibleModel):
    """Provider-neutral identity of a component that produced a record."""

    name: NonEmptyStr
    version: NonEmptyStr
    profile: NonEmptyStr | None = None


class ParserDescriptor(ExtensibleModel):
    """Parser identity and configuration used for a representation."""

    name: NonEmptyStr
    version: NonEmptyStr
    profile: NonEmptyStr
    config_hash: Sha256Id


class GenerationProvenance(ExtensibleModel):
    """Component and time that generated a derived or inferred record."""

    component: ComponentDescriptor
    created_at: UtcDatetime


class SourceLocator(ExtensibleModel):
    """Precise source location treated as data rather than access authority."""

    extraction_method: NonEmptyStr
    native_id: NonEmptyStr | None = None
    page: int | None = Field(default=None, ge=1)
    slide: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None

    @model_validator(mode="after")
    def _coordinates_are_unambiguous(self) -> SourceLocator:
        if self.page is not None and self.slide is not None:
            raise ValueError("source locator cannot specify both page and slide")
        if self.bbox is not None:
            if self.page is None and self.slide is None:
                raise ValueError("bbox requires a page or slide source coordinate")
            x_min, y_min, x_max, y_max = self.bbox
            if x_min > x_max or y_min > y_max:
                raise ValueError("bbox requires x_min <= x_max and y_min <= y_max")
        return self


def _parse_json_int(value: str) -> int:
    parsed = int(value)
    ensure_json_value(parsed)
    return parsed


def _parse_json_float(value: str) -> float:
    parsed = float(value)
    ensure_json_value(parsed)
    return parsed


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON numeric constant is not allowed: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object name: {key}")
        result[key] = value
    return result


def validate_json[ModelT: BaseModel](
    model: type[ModelT],
    data: str | bytes | bytearray,
) -> ModelT:
    """Validate strict raw JSON without duplicate-name or numeric ambiguity."""
    decoded = json.loads(
        data,
        parse_int=_parse_json_int,
        parse_float=_parse_json_float,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_unique_json_object,
    )
    ensure_json_value(decoded)
    return model.model_validate_json(data, strict=True)
