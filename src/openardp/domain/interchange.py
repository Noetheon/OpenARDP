"""Closed experimental BagIt interchange contracts and invariants."""

from __future__ import annotations

import re
import unicodedata
from enum import Enum, StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from openardp.domain.common import (
    MAX_SAFE_INTEGER,
    DataTrustClassification,
    DomainModel,
    Sha256Id,
    ensure_json_value,
)
from openardp.domain.identity import canonical_sha256

INTERCHANGE_PROFILE_VERSION = "0.1.0"
INTERCHANGE_SCHEMA_VERSION = "0.1.0"
INTERCHANGE_PROFILE_IDENTIFIER = "https://openardp.org/profiles/bagit/0.1.0"
INTERCHANGE_IDENTITY_ALGORITHM = "sha256-rfc8785-v1"

_MEDIA_TYPE = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$")
_MACHINE_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_REFERENCE_CREDENTIAL = re.compile(
    r"(?i)(?:[?&](?:access_token|api[_-]?key|password|secret|token)=|://[^/@\s]+:[^/@\s]+@)"
)
_REFERENCE_URI = re.compile(r"^(?P<scheme>[a-z][a-z0-9+.-]{1,31}):[^\s]+$")
_ABSOLUTE_PATH = re.compile(r"^(?:/|\\\\|[A-Za-z]:[\\/])")
_EXTENSION_NAME = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)+$")
_FORBIDDEN_FACT_KEYS = frozenset(
    {
        "absolutepath",
        "apikey",
        "authorization",
        "body",
        "cookie",
        "credential",
        "credentials",
        "filepath",
        "filename",
        "localpath",
        "log",
        "logs",
        "password",
        "rawbody",
        "secret",
        "sourcepath",
        "token",
    }
)
_WINDOWS_RESERVED = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def _exact_version(value: object, *, field: str, installed: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} version must be semantic version text")
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value):
        raise ValueError(f"{field} version must be semantic version MAJOR.MINOR.PATCH")
    if value != installed:
        raise ValueError(f"{field} version {value} is not installed; supported: {installed}")
    return value


class ExtensionPolicy(StrEnum):
    """Closed handling of explicitly namespaced JSON extensions."""

    REJECT = "reject"
    PRESERVE = "preserve"


class PortableRecordType(StrEnum):
    """Portable thin-record families admitted by profile 0.1.0."""

    SOURCE = "source"
    NATIVE_PROJECTION = "native_projection"
    EVIDENCE_PROJECTION = "evidence_projection"
    DERIVATION = "derivation"


class AssetRole(StrEnum):
    """Independent original/provider-native asset roles."""

    SOURCE = "source"
    PROVIDER_NATIVE = "provider_native"


class AssetDisposition(StrEnum):
    """Closed byte-distribution decision."""

    INCLUDED = "included"
    REFERENCED = "referenced"
    OMITTED = "omitted"


class OmissionReason(StrEnum):
    """Body-free reason for absent portable bytes."""

    PERMISSION_UNKNOWN = "permission_unknown"
    REDISTRIBUTION_PROHIBITED = "redistribution_prohibited"
    OPERATOR_EXCLUDED = "operator_excluded"
    NOT_AVAILABLE = "not_available"


class RelationshipPredicate(StrEnum):
    """Portable relationship vocabulary."""

    DESCRIBES = "describes"
    PROJECTS = "projects"
    DERIVED_FROM = "derived_from"
    USES_ASSET = "uses_asset"
    HAS_NATIVE_ASSET = "has_native_asset"


class InterchangeOperation(StrEnum):
    """Explicit trusted-operator interchange operations."""

    EXPORT = "export"
    VERIFY = "verify"
    IMPORT = "import"


class InterchangeOutcome(StrEnum):
    """Body-free terminal outcomes."""

    COMPLETE = "complete"
    CONVERGED = "converged"


class InterchangeErrorCode(StrEnum):
    """Stable sanitized failure classifications."""

    MALFORMED_PACKAGE = "MALFORMED_PACKAGE"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    POLICY_REJECTED = "POLICY_REJECTED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INTEGRITY_INVALID = "INTEGRITY_INVALID"
    RELATIONSHIP_INVALID = "RELATIONSHIP_INVALID"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    DESTINATION_CONFLICT = "DESTINATION_CONFLICT"
    PUBLICATION_FAILED = "PUBLICATION_FAILED"


MachineToken = Annotated[str, StringConstraints(strict=True, pattern=_MACHINE_TOKEN.pattern)]
MediaType = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=255)]


def validate_portable_path(value: str, *, max_bytes: int = 512, max_depth: int = 16) -> str:
    """Validate one already-canonical portable member path."""
    if not isinstance(value, str) or not value:
        raise ValueError("portable path must be non-empty text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("portable path must be valid UTF-8") from error
    if len(encoded) > max_bytes:
        raise ValueError("portable path exceeds byte limit")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("portable path must already use NFC normalization")
    if value.startswith(("/", "\\")) or "\\" in value or ":" in value:
        raise ValueError("portable path must be relative POSIX text")
    parts = value.split("/")
    if len(parts) > max_depth or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("portable path depth or segment is invalid")
    for part in parts:
        if any(ord(character) < 32 or ord(character) == 127 for character in part):
            raise ValueError("portable path contains control characters")
        if part.endswith((".", " ")):
            raise ValueError("portable path has a non-portable trailing character")
        if part.casefold().split(".", maxsplit=1)[0] in _WINDOWS_RESERVED:
            raise ValueError("portable path contains a reserved platform name")
    return value


def payload_path(object_id: str) -> str:
    """Return the unique profile path for one SHA-256 object."""
    if re.fullmatch(r"sha256:[0-9a-f]{64}", object_id) is None:
        raise ValueError("object_id must be a lowercase SHA-256 identity")
    digest = object_id.removeprefix("sha256:")
    return f"data/objects/sha256/{digest[:2]}/{digest[2:]}"


def _portable_json(value: object, *, path: str, extensions: bool = False) -> object:
    ensure_json_value(value, path=path)
    if isinstance(value, str):
        if _ABSOLUTE_PATH.match(value) or _REFERENCE_CREDENTIAL.search(value):
            raise ValueError(f"{path} contains local-path or credential-shaped data")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            _portable_json(item, path=f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
            if normalized in _FORBIDDEN_FACT_KEYS:
                raise ValueError(f"{path} contains forbidden local or sensitive field")
            if extensions and _EXTENSION_NAME.fullmatch(key) is None:
                raise ValueError("extension names must be lowercase namespaced tokens")
            if not extensions and _MACHINE_TOKEN.fullmatch(key) is None:
                raise ValueError(f"{path} keys must be canonical machine tokens")
            _portable_json(item, path=f"{path}.{key}")
    return value


class PortableRecord(DomainModel):
    """Thin provider-neutral record carried by one package."""

    record_type: PortableRecordType
    contract_version: str
    record_id: Sha256Id
    trust: DataTrustClassification
    facts: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("contract_version")
    @classmethod
    def _contract_is_installed(cls, value: str) -> str:
        return _exact_version(value, field="contract", installed=INTERCHANGE_SCHEMA_VERSION)

    @field_validator("facts", "extensions", mode="before")
    @classmethod
    def _json_maps(cls, value: object, info: Any) -> object:
        return _portable_json(
            value,
            path=f"$.{info.field_name}",
            extensions=info.field_name == "extensions",
        )


class PortableAsset(DomainModel):
    """Exact asset identity plus explicit distribution policy."""

    object_id: Sha256Id
    byte_length: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    media_type: MediaType
    role: AssetRole
    disposition: AssetDisposition
    payload_path: str | None = Field(default=None, max_length=512)
    reference: str | None = Field(default=None, strict=True, min_length=1, max_length=2048)
    omission_reason: OmissionReason | None = None
    redistribution_asserted: bool = False
    license_assertion: str | None = Field(default=None, strict=True, min_length=1, max_length=1024)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("media_type")
    @classmethod
    def _media_type_is_normalized(cls, value: str) -> str:
        if _MEDIA_TYPE.fullmatch(value) is None:
            raise ValueError("media_type must be normalized lowercase type/subtype")
        return value

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_json(cls, value: object) -> object:
        return _portable_json(value, path="$.extensions", extensions=True)

    @field_validator("reference", "license_assertion")
    @classmethod
    def _strings_are_inert_and_portable(cls, value: str | None) -> str | None:
        if value is not None:
            _portable_json(value, path="$.asset_assertion")
        return value

    @model_validator(mode="after")
    def _disposition_is_closed(self) -> Self:
        if self.disposition is AssetDisposition.INCLUDED:
            if (
                self.payload_path != payload_path(self.object_id)
                or self.reference is not None
                or self.omission_reason is not None
                or not self.redistribution_asserted
            ):
                raise ValueError(
                    "included asset requires canonical payload path and affirmative redistribution"
                )
        elif self.disposition is AssetDisposition.REFERENCED:
            if (
                self.payload_path is not None
                or self.reference is None
                or self.omission_reason is not None
                or self.redistribution_asserted
            ):
                raise ValueError("referenced asset requires only one inert reference")
            if _REFERENCE_CREDENTIAL.search(self.reference):
                raise ValueError("reference contains credential-shaped data")
            matched = _REFERENCE_URI.fullmatch(self.reference)
            if matched is None or matched.group("scheme") == "file":
                raise ValueError("reference must be an inert non-file absolute URI")
        elif (
            self.payload_path is not None
            or self.reference is not None
            or self.omission_reason is None
            or self.redistribution_asserted
        ):
            raise ValueError("omitted asset requires only one closed omission reason")
        if self.payload_path is not None:
            validate_portable_path(self.payload_path)
        return self


class PortableRelationship(DomainModel):
    """One closed portable relationship between record/asset identities."""

    subject_id: Sha256Id
    predicate: RelationshipPredicate
    object_id: Sha256Id


class InterchangePackage(DomainModel):
    """Identity-bearing canonical OpenARDP tag record."""

    profile_version: Literal["0.1.0"]
    schema_version: Literal["0.1.0"]
    package_id: Sha256Id
    identity_algorithm: Literal["sha256-rfc8785-v1"]
    scope_id: Sha256Id
    extension_policy: ExtensionPolicy
    records: tuple[PortableRecord, ...]
    assets: tuple[PortableAsset, ...]
    relationships: tuple[PortableRelationship, ...]
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("profile_version", mode="before")
    @classmethod
    def _profile_is_installed(cls, value: object) -> object:
        return _exact_version(value, field="profile", installed=INTERCHANGE_PROFILE_VERSION)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _schema_is_installed(cls, value: object) -> object:
        return _exact_version(value, field="schema", installed=INTERCHANGE_SCHEMA_VERSION)

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_json(cls, value: object) -> object:
        return _portable_json(value, path="$.extensions", extensions=True)

    @model_validator(mode="after")
    def _aggregate_is_canonical(self) -> Self:
        record_keys = tuple((item.record_type.value, item.record_id) for item in self.records)
        asset_ids = tuple(item.object_id for item in self.assets)
        relationship_keys = tuple(
            (item.subject_id, item.predicate.value, item.object_id) for item in self.relationships
        )
        if record_keys != tuple(sorted(set(record_keys))):
            raise ValueError("records must be sorted and unique")
        if asset_ids != tuple(sorted(set(asset_ids))):
            raise ValueError("assets must be sorted and unique")
        if relationship_keys != tuple(sorted(set(relationship_keys))):
            raise ValueError("relationships must be sorted and unique")
        if self.extension_policy is ExtensionPolicy.REJECT and (
            self.extensions
            or any(item.extensions for item in self.records)
            or any(item.extensions for item in self.assets)
        ):
            raise ValueError("reject extension policy requires empty extensions")
        identities = {item.record_id for item in self.records} | set(asset_ids)
        for relation in self.relationships:
            if relation.subject_id not in identities or relation.object_id not in identities:
                raise ValueError("relationship endpoint is absent from the package")
        self._reject_derivation_cycles()
        if self.package_id != package_identity(self.model_dump(mode="json")):
            raise ValueError("package_id does not match canonical package facts")
        return self

    def _reject_derivation_cycles(self) -> None:
        graph: dict[str, set[str]] = {}
        for relation in self.relationships:
            if relation.predicate is RelationshipPredicate.DERIVED_FROM:
                graph.setdefault(relation.subject_id, set()).add(relation.object_id)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("derived_from relationships must be acyclic")
            if node in visited:
                return
            visiting.add(node)
            for dependency in sorted(graph.get(node, ())):
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in sorted(graph):
            visit(node)


def package_identity(value: InterchangePackage | dict[str, JsonValue] | dict[str, object]) -> str:
    """Hash every semantic package field except its declared package identifier."""
    payload: object = (
        value.model_dump(mode="json", exclude={"package_id"})
        if isinstance(value, InterchangePackage)
        else {key: item for key, item in value.items() if key != "package_id"}
    )
    return canonical_sha256(_jsonable(payload))


def _jsonable(value: object) -> JsonValue:
    """Project models/enums/tuples into the strict JSON identity domain."""
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if value is None or isinstance(value, (bool, str, int, float)):
        ensure_json_value(value)
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("package identity object requires string keys")
        return {str(key): _jsonable(item) for key, item in value.items()}
    raise ValueError("package identity contains a non-JSON value")


class InterchangeLimits(DomainModel):
    """Installed local resource limits for hostile archive validation."""

    max_archive_bytes: int = Field(
        default=2_147_483_648, strict=True, ge=1_048_576, le=17_179_869_184
    )
    max_expanded_bytes: int = Field(
        default=2_147_483_648, strict=True, ge=1_048_576, le=17_179_869_184
    )
    max_entry_count: int = Field(default=10_000, strict=True, ge=6, le=100_000)
    max_entry_bytes: int = Field(default=1_073_741_824, strict=True, ge=1_024, le=8_589_934_592)
    max_metadata_bytes: int = Field(default=16_777_216, strict=True, ge=65_536, le=268_435_456)
    max_path_bytes: int = Field(default=512, strict=True, ge=64, le=4_096)
    max_path_depth: int = Field(default=16, strict=True, ge=2, le=64)
    max_relationships: int = Field(default=100_000, strict=True, ge=1, le=1_000_000)


class PackageInventoryEntry(DomainModel):
    """Verified relative package entry without body content."""

    path: str
    byte_length: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    sha256: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
    kind: Literal["payload", "tag"]

    @field_validator("path")
    @classmethod
    def _path_is_portable(cls, value: str) -> str:
        return validate_portable_path(value)


class VerifiedPackage(DomainModel):
    """Complete body-free verification result and immutable import input."""

    package: InterchangePackage
    archive_sha256: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
    archive_bytes: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    payload_count: int = Field(strict=True, ge=0)
    payload_bytes: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    tag_count: int = Field(strict=True, ge=5)
    tag_bytes: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    inventory: tuple[PackageInventoryEntry, ...]


class ImportPlan(DomainModel):
    """Immutable, target-bound authority for one verified snapshot publication."""

    plan_id: Sha256Id
    package_id: Sha256Id
    archive_sha256: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
    target_id: Sha256Id
    limits: InterchangeLimits
    inventory: tuple[PackageInventoryEntry, ...]

    @model_validator(mode="after")
    def _identity_matches_facts(self) -> Self:
        paths = tuple(item.path for item in self.inventory)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("import plan inventory must be sorted and unique")
        if self.plan_id != import_plan_identity(self.model_dump(mode="json")):
            raise ValueError("plan_id does not match canonical import facts")
        return self


def import_plan_identity(value: ImportPlan | dict[str, object]) -> str:
    """Hash one verified import authority without persisting its local target path."""
    payload: object = (
        value.model_dump(mode="json", exclude={"plan_id"})
        if isinstance(value, ImportPlan)
        else {key: item for key, item in value.items() if key != "plan_id"}
    )
    return canonical_sha256(_jsonable(payload))


class InterchangeResult(DomainModel):
    """Sanitized operator result without local paths or content."""

    operation: InterchangeOperation
    outcome: InterchangeOutcome
    package_id: Sha256Id
    profile_version: Literal["0.1.0"]
    schema_version: Literal["0.1.0"]
    archive_sha256: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
    archive_bytes: int = Field(strict=True, ge=0)
    entry_count: int = Field(strict=True, ge=5)
    payload_bytes: int = Field(strict=True, ge=0)
    record_count: int = Field(strict=True, ge=0)
    asset_count: int = Field(strict=True, ge=0)
    relationship_count: int = Field(strict=True, ge=0)


__all__ = [
    "INTERCHANGE_IDENTITY_ALGORITHM",
    "INTERCHANGE_PROFILE_IDENTIFIER",
    "INTERCHANGE_PROFILE_VERSION",
    "INTERCHANGE_SCHEMA_VERSION",
    "AssetDisposition",
    "AssetRole",
    "ExtensionPolicy",
    "ImportPlan",
    "InterchangeErrorCode",
    "InterchangeLimits",
    "InterchangeOperation",
    "InterchangeOutcome",
    "InterchangePackage",
    "InterchangeResult",
    "OmissionReason",
    "PackageInventoryEntry",
    "PortableAsset",
    "PortableRecord",
    "PortableRecordType",
    "PortableRelationship",
    "RelationshipPredicate",
    "VerifiedPackage",
    "import_plan_identity",
    "package_identity",
    "payload_path",
    "validate_portable_path",
]
