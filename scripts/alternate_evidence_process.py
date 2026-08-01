"""Independent stdlib-only F006 evidence consumer and alternate TXT/CSV producer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path, PurePosixPath

PROFILE_VERSION = "0.1.0"
CONTRACT_VERSION = "0.1.0"
IDENTITY_VERSION = 1
MAX_SAFE_INTEGER = 9_007_199_254_740_991
PPM = 1_000_000
FIXED_CREATED_AT = "2026-08-01T00:00:00Z"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
MEDIA_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$"
)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class ConformanceFailure(Exception):
    """One stable body-free conformance failure."""

    def __init__(self, category: str) -> None:
        """Initialize the failure with one allowlisted category."""
        super().__init__(category)
        self.category = category


def _fail(category: str) -> None:
    raise ConformanceFailure(category)


def _safe_json(value: object) -> None:
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str):
            for character in value:
                if 0xD800 <= ord(character) <= 0xDFFF:
                    _fail("unsupported_json")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_SAFE_INTEGER:
            _fail("unsupported_json")
        return
    if isinstance(value, float):
        _fail("unsupported_json")
    if isinstance(value, list):
        for item in value:
            _safe_json(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("unsupported_json")
            _safe_json(key)
            _safe_json(item)
        return
    _fail("unsupported_json")


def canonical_bytes(value: object) -> bytes:
    """Return canonical bytes for the contract's declared JCS-safe subset."""
    _safe_json(value)
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return rendered.encode("utf-8", errors="strict")
    except (UnicodeEncodeError, ValueError, TypeError):
        _fail("unsupported_json")


def _raw_sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: object) -> str:
    return _raw_sha256(canonical_bytes(value))


def _identity(domain: str, payload: dict[str, object]) -> str:
    return _canonical_sha256(
        {
            "canonicalization": "RFC8785",
            "domain": domain,
            "identity_version": IDENTITY_VERSION,
            "payload": payload,
        }
    )


def _load_json_bytes(payload: bytes) -> object:
    def closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                _fail("duplicate_json_key")
            result[key] = value
        return result

    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=closed_object,
            parse_constant=lambda _value: _fail("json"),
        )
    except ConformanceFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("json")


def _object(value: object, category: str = "structure") -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _fail(category)
    return value


def _array(value: object, category: str = "structure") -> list[object]:
    if not isinstance(value, list):
        _fail(category)
    return value


def _exact_fields(
    value: dict[str, object],
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    allowed = required | (optional or set())
    if set(value) - allowed:
        _fail("unknown_field")
    if required - set(value):
        _fail("missing_field")


def _string(value: object, *, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        _fail("type_or_bounds")
    return value


def _integer(value: object, *, minimum: int = 0, maximum: int = MAX_SAFE_INTEGER) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail("type_or_bounds")
    return value


def _sha256(value: object) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        _fail("sha256")
    return value


def _semver(value: object) -> str:
    if not isinstance(value, str) or SEMVER_RE.fullmatch(value) is None:
        _fail("semver")
    return value


def _media_type(value: object) -> str:
    if not isinstance(value, str) or MEDIA_RE.fullmatch(value) is None:
        _fail("media_type")
    return value


def _common(record: dict[str, object]) -> None:
    version = record.get("contract_version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        _fail("contract_version")
    if not version.startswith("0.") or version != CONTRACT_VERSION:
        _fail("contract_version")
    if record.get("stability") != "experimental":
        _fail("stability")
    extensions = _object(record.get("extensions"), "extensions")
    for namespace, extension in extensions.items():
        if URI_RE.fullmatch(namespace) is None:
            _fail("extension_namespace")
        _safe_json(extension)


def _provider(value: object) -> dict[str, object]:
    provider = _object(value)
    _exact_fields(provider, {"name", "version", "profile", "profile_version", "config_hash"})
    _string(provider["name"])
    _string(provider["version"])
    _string(provider["profile"])
    _semver(provider["profile_version"])
    _sha256(provider["config_hash"])
    return provider


def _pointer(value: object) -> dict[str, object]:
    pointer = _object(value)
    _exact_fields(
        pointer,
        {"provider_profile", "provider_profile_version", "pointer_format", "pointer"},
    )
    _string(pointer["provider_profile"])
    _semver(pointer["provider_profile_version"])
    _string(pointer["pointer_format"])
    target = _string(pointer["pointer"], maximum=2048)
    if CONTROL_RE.search(target):
        _fail("pointer_control")
    return pointer


def _anchor(value: object) -> dict[str, object]:
    anchor = _object(value)
    anchor_type = anchor.get("anchor_type")
    if anchor_type == "text_span":
        _exact_fields(anchor, {"anchor_type", "coordinate_system", "start", "end"}, {"text_length"})
        if anchor["coordinate_system"] != "unicode_code_points":
            _fail("coordinate_system")
        start = _integer(anchor["start"])
        end = _integer(anchor["end"])
        if end <= start:
            _fail("text_bounds")
        if (
            "text_length" in anchor
            and anchor["text_length"] is not None
            and end > _integer(anchor["text_length"])
        ):
            _fail("text_bounds")
    elif anchor_type == "page_region":
        _exact_fields(
            anchor,
            {"anchor_type", "coordinate_system", "page_number", "x", "y", "width", "height"},
        )
        if anchor["coordinate_system"] != "normalized_ppm_top_left":
            _fail("coordinate_system")
        _integer(anchor["page_number"], minimum=1)
        x = _integer(anchor["x"], maximum=PPM - 1)
        y = _integer(anchor["y"], maximum=PPM - 1)
        width = _integer(anchor["width"], minimum=1, maximum=PPM)
        height = _integer(anchor["height"], minimum=1, maximum=PPM)
        if x + width > PPM or y + height > PPM:
            _fail("page_bounds")
    elif anchor_type == "table_cell":
        _exact_fields(
            anchor,
            {"anchor_type", "table", "row_index", "column_index"},
            {"row_span", "column_span"},
        )
        _pointer(anchor["table"])
        row = _integer(anchor["row_index"])
        column = _integer(anchor["column_index"])
        row_span = _integer(anchor.get("row_span", 1), minimum=1)
        column_span = _integer(anchor.get("column_span", 1), minimum=1)
        if row + row_span > MAX_SAFE_INTEGER or column + column_span > MAX_SAFE_INTEGER:
            _fail("table_bounds")
    elif anchor_type == "provider_pointer":
        _exact_fields(anchor, {"anchor_type", "target"})
        _pointer(anchor["target"])
    else:
        _fail("anchor_type")
    return anchor


def _native_identity(record: dict[str, object]) -> str:
    provider = _object(record["provider"])
    return _identity(
        "openardp:native-representation",
        {
            "source_version_id": record["source_version_id"],
            "native_artifact_id": record["native_artifact_id"],
            "native_artifact_media_type": record["native_artifact_media_type"],
            "provider": {
                "name": provider["name"],
                "version": provider["version"],
                "profile": provider["profile"],
                "profile_version": provider["profile_version"],
                "config_hash": provider["config_hash"],
            },
        },
    )


def _reference_identity(record: dict[str, object]) -> str:
    return _identity(
        "openardp:evidence-reference",
        {
            "source_version_id": record["source_version_id"],
            "native_representation_id": record["native_representation_id"],
            "anchor": record["anchor"],
        },
    )


def _projection_identity(record: dict[str, object]) -> str:
    reference = _object(record["reference"])
    retrieval = _object(record["retrieval"])
    provenance = _object(record["provenance"])
    return _identity(
        "openardp:evidence-projection",
        {
            "source_version_id": record["source_version_id"],
            "native_representation_id": record["native_representation_id"],
            "evidence_reference_id": reference["evidence_reference_id"],
            "retrieval": {
                "artifact_id": retrieval["artifact_id"],
                "media_type": retrieval["media_type"],
            },
            "parent_projection_id": record["parent_projection_id"],
            "ordinal": record["ordinal"],
            "generator": {
                "name": provenance["generator_name"],
                "version": provenance["generator_version"],
                "config_hash": provenance["generator_config_hash"],
            },
        },
    )


def _validate_native(value: object) -> dict[str, object]:
    record = _object(value)
    _exact_fields(
        record,
        {
            "contract_version",
            "stability",
            "extensions",
            "native_representation_id",
            "source_version_id",
            "native_artifact_id",
            "native_artifact_media_type",
            "native_artifact_byte_length",
            "provider",
            "created_at",
        },
    )
    _common(record)
    _sha256(record["native_representation_id"])
    _sha256(record["source_version_id"])
    _sha256(record["native_artifact_id"])
    _media_type(record["native_artifact_media_type"])
    _integer(record["native_artifact_byte_length"])
    _provider(record["provider"])
    if not isinstance(record["created_at"], str) or not record["created_at"].endswith("Z"):
        _fail("timestamp")
    if record["native_representation_id"] != _native_identity(record):
        _fail("identity_mismatch")
    return record


def _validate_reference(value: object) -> dict[str, object]:
    record = _object(value)
    _exact_fields(
        record,
        {
            "contract_version",
            "stability",
            "extensions",
            "evidence_reference_id",
            "source_version_id",
            "native_representation_id",
            "anchor",
        },
    )
    _common(record)
    _sha256(record["evidence_reference_id"])
    _sha256(record["source_version_id"])
    _sha256(record["native_representation_id"])
    _anchor(record["anchor"])
    if record["evidence_reference_id"] != _reference_identity(record):
        _fail("identity_mismatch")
    return record


def _validate_trust(value: object) -> dict[str, object]:
    record = _object(value)
    _exact_fields(
        record,
        {
            "contract_version",
            "stability",
            "extensions",
            "origin_zone",
            "effective_zone",
            "role",
            "instruction_execution_allowed",
            "integrity",
            "sensitivity",
        },
    )
    _common(record)
    zones = {"local_trusted", "organization_trusted", "external_untrusted", "model_derived"}
    if record["origin_zone"] not in zones or record["effective_zone"] not in zones:
        _fail("trust_zone")
    if record["role"] != "data" or record["instruction_execution_allowed"] is not False:
        _fail("instruction_authority")
    if record["integrity"] not in {"verified_sha256", "unverified"}:
        _fail("integrity")
    if record["sensitivity"] not in {"public", "internal", "confidential", "restricted", "unknown"}:
        _fail("sensitivity")
    rank = {"external_untrusted": 0, "organization_trusted": 1, "local_trusted": 2}
    origin = record["origin_zone"]
    effective = record["effective_zone"]
    if origin == "model_derived" and effective != "model_derived":
        _fail("trust_escalation")
    if (
        origin != "model_derived"
        and effective != "model_derived"
        and rank[str(effective)] > rank[str(origin)]
    ):
        _fail("trust_escalation")
    return record


def _validate_projection(value: object) -> dict[str, object]:
    record = _object(value)
    _exact_fields(
        record,
        {
            "contract_version",
            "stability",
            "extensions",
            "evidence_projection_id",
            "source_version_id",
            "native_representation_id",
            "reference",
            "retrieval",
            "parent_projection_id",
            "ordinal",
            "trust",
            "provenance",
        },
    )
    _common(record)
    _sha256(record["evidence_projection_id"])
    _sha256(record["source_version_id"])
    _sha256(record["native_representation_id"])
    reference = _validate_reference(record["reference"])
    retrieval = _object(record["retrieval"])
    _exact_fields(retrieval, {"artifact_id", "media_type", "byte_length"})
    _sha256(retrieval["artifact_id"])
    _media_type(retrieval["media_type"])
    _integer(retrieval["byte_length"])
    if record["parent_projection_id"] is not None:
        _sha256(record["parent_projection_id"])
    _integer(record["ordinal"])
    _validate_trust(record["trust"])
    provenance = _object(record["provenance"])
    _exact_fields(
        provenance, {"generator_name", "generator_version", "generator_config_hash", "created_at"}
    )
    _string(provenance["generator_name"])
    _string(provenance["generator_version"])
    _sha256(provenance["generator_config_hash"])
    if not isinstance(provenance["created_at"], str) or not provenance["created_at"].endswith("Z"):
        _fail("timestamp")
    if (
        reference["source_version_id"] != record["source_version_id"]
        or reference["native_representation_id"] != record["native_representation_id"]
    ):
        _fail("scope_mismatch")
    if record["evidence_projection_id"] != _projection_identity(record):
        _fail("identity_mismatch")
    return record


VALIDATORS = {
    "native_representation": _validate_native,
    "evidence_reference": _validate_reference,
    "evidence_projection": _validate_projection,
    "trust_classification": _validate_trust,
}


class ConfinedReader:
    """Read only declared regular files below one root within cumulative limits."""

    def __init__(self, root: Path, limits: dict[str, object]) -> None:
        """Bind one resolved root and closed cumulative read budget."""
        if not root.is_absolute() or root.is_symlink():
            _fail("root")
        try:
            self.root = root.resolve(strict=True)
        except OSError:
            _fail("root")
        if not self.root.is_dir() or self.root.is_symlink():
            _fail("root")
        self.max_files = _integer(limits.get("max_files"), minimum=1)
        self.max_total = _integer(limits.get("max_total_bytes"), minimum=1)
        self.max_file = _integer(limits.get("max_file_bytes"), minimum=1)
        self.files = 0
        self.total = 0

    def read(self, relative: object, expected_sha256: object | None = None) -> bytes:
        """Read one confined regular file and optionally verify its SHA-256."""
        if not isinstance(relative, str):
            _fail("path")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts or "." in pure.parts:
            _fail("path")
        candidate = self.root.joinpath(*pure.parts)
        current = self.root
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                _fail("path")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.root)
        except (FileNotFoundError, ValueError):
            _fail("path")
        if not resolved.is_file():
            _fail("path")
        before = resolved.stat()
        size = before.st_size
        if (
            size > self.max_file
            or self.files + 1 > self.max_files
            or self.total + size > self.max_total
        ):
            _fail("resource_limit")
        payload = resolved.read_bytes()
        after = resolved.stat()
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if len(payload) != size or before_identity != after_identity:
            _fail("read_race")
        self.files += 1
        self.total += size
        if expected_sha256 is not None and _raw_sha256(payload) != _sha256(expected_sha256):
            _fail("digest_mismatch")
        return payload


def _manifest_entry(value: object) -> dict[str, object]:
    entry = _object(value, "manifest")
    return entry


def _observation(case_id: str, kind: str, expected: object, observed: object) -> dict[str, object]:
    return {
        "case_id": case_id,
        "direction": "reference_to_alternate",
        "expected": expected,
        "kind": kind,
        "observed": observed,
        "status": "pass" if expected == observed else "fail",
    }


def _consume(request: dict[str, object], implementation_id: str) -> dict[str, object]:
    reader = ConfinedReader(
        Path(_string(request.get("root"), maximum=4096)), _object(request.get("limits"))
    )
    evidence_bytes = reader.read(
        request.get("evidence_manifest"), request.get("evidence_manifest_sha256")
    )
    evidence = _object(_load_json_bytes(evidence_bytes), "manifest")
    if evidence.get("contract_version") != CONTRACT_VERSION:
        _fail("contract_version")
    observations: list[dict[str, object]] = []
    anchors: set[str] = set()
    models: set[str] = set()
    invalid_categories = _object(request.get("invalid_categories"), "manifest")
    for kind, expected_outcome in (("valid", "accept"), ("invalid", "reject")):
        for raw_entry in _array(evidence.get(kind), "manifest"):
            entry = _manifest_entry(raw_entry)
            model = _string(entry.get("model"))
            path = _string(entry.get("path"), maximum=1024)
            if model not in VALIDATORS:
                _fail("manifest")
            payload = reader.read(
                PurePosixPath(str(request["evidence_manifest"])).parent.joinpath(path).as_posix()
            )
            value = _load_json_bytes(payload)
            models.add(model)
            if isinstance(value, dict) and model == "evidence_reference":
                anchor = value.get("anchor")
                if isinstance(anchor, dict) and isinstance(anchor.get("anchor_type"), str):
                    anchors.add(anchor["anchor_type"])
            if kind == "valid":
                try:
                    VALIDATORS[model](value)
                    observed: object = "accept"
                except ConformanceFailure as error:
                    observed = {"reject": error.category}
            else:
                expected_category = invalid_categories.get(path)
                if not isinstance(expected_category, str):
                    _fail("manifest")
                expected_outcome = {"reject": expected_category}
                try:
                    VALIDATORS[model](value)
                    observed = "accept"
                except ConformanceFailure as error:
                    observed = {"reject": error.category}
            observations.append(
                _observation(f"{kind}:{path}", f"root_{kind}", expected_outcome, observed)
            )

    for index, raw_set in enumerate(_array(evidence.get("record_sets"), "manifest")):
        item = _manifest_entry(raw_set)
        base = PurePosixPath(str(request["evidence_manifest"])).parent
        native = _validate_native(
            _load_json_bytes(
                reader.read(base.joinpath(_string(item.get("native"), maximum=1024)).as_posix())
            )
        )
        references = [
            _validate_reference(
                _load_json_bytes(reader.read(base.joinpath(_string(path, maximum=1024)).as_posix()))
            )
            for path in _array(item.get("references"), "manifest")
        ]
        projections = [
            _validate_projection(
                _load_json_bytes(reader.read(base.joinpath(_string(path, maximum=1024)).as_posix()))
            )
            for path in _array(item.get("projections"), "manifest")
        ]
        expected_source = item.get("expected_source_version_id")
        if expected_source is not None and native["source_version_id"] != expected_source:
            _fail("scope_mismatch")
        reference_ids: dict[object, dict[str, object]] = {}
        for reference in references:
            if (
                reference["source_version_id"] != native["source_version_id"]
                or reference["native_representation_id"] != native["native_representation_id"]
            ):
                _fail("scope_mismatch")
            prior = reference_ids.setdefault(reference["evidence_reference_id"], reference)
            if prior != reference:
                _fail("identity_collision")
        projection_ids: dict[object, dict[str, object]] = {}
        for projection in projections:
            reference = _object(projection["reference"])
            if (
                projection["source_version_id"] != native["source_version_id"]
                or projection["native_representation_id"] != native["native_representation_id"]
            ):
                _fail("scope_mismatch")
            if reference["evidence_reference_id"] not in reference_ids:
                _fail("scope_mismatch")
            prior = projection_ids.setdefault(projection["evidence_projection_id"], projection)
            if prior != projection:
                _fail("identity_collision")
        observations.append(_observation(f"record_set:{index}", "record_set", "accept", "accept"))

    vector_path = _string(evidence.get("canonicalization_vectors"), maximum=1024)
    vectors_bytes = reader.read(
        PurePosixPath(str(request["evidence_manifest"])).parent.joinpath(vector_path).as_posix(),
        request.get("identity_vectors_sha256"),
    )
    vectors = _object(_load_json_bytes(vectors_bytes), "vectors")
    if (
        vectors.get("contract_version") != CONTRACT_VERSION
        or vectors.get("canonicalization") != "RFC8785"
        or vectors.get("identity_version") != IDENTITY_VERSION
    ):
        _fail("vectors")
    for raw_case in _array(vectors.get("cases"), "vectors"):
        case = _object(raw_case, "vectors")
        name = _string(case.get("name"))
        envelope = case.get("envelope")
        expected = {"canonical": case.get("canonical"), "sha256": case.get("sha256")}
        observed = {
            "canonical": canonical_bytes(envelope).decode("utf-8"),
            "sha256": _canonical_sha256(envelope),
        }
        observations.append(_observation(f"vector:{name}", "identity_vector", expected, observed))

    observations.sort(key=lambda item: (str(item["kind"]), str(item["case_id"])))
    return {
        "command": "consume",
        "coverage": {
            "anchors": sorted(anchors),
            "identity_vectors": len(_array(vectors.get("cases"))),
            "invalid_roots": len(_array(evidence.get("invalid"))),
            "models": sorted(models),
            "record_sets": len(_array(evidence.get("record_sets"))),
            "valid_roots": len(_array(evidence.get("valid"))),
        },
        "implementation_sha256": implementation_id,
        "observations": observations,
        "outputs": {},
        "profile_version": PROFILE_VERSION,
    }


def _base_record() -> dict[str, object]:
    return {"contract_version": CONTRACT_VERSION, "extensions": {}, "stability": "experimental"}


def _trust() -> dict[str, object]:
    return {
        **_base_record(),
        "effective_zone": "external_untrusted",
        "instruction_execution_allowed": False,
        "integrity": "verified_sha256",
        "origin_zone": "external_untrusted",
        "role": "data",
        "sensitivity": "internal",
    }


def _make_reference(source_id: str, native_id: str, anchor: dict[str, object]) -> dict[str, object]:
    record = {
        **_base_record(),
        "source_version_id": source_id,
        "native_representation_id": native_id,
        "anchor": anchor,
    }
    record["evidence_reference_id"] = _reference_identity(record)
    return record


def _make_projection(
    source_id: str,
    native_id: str,
    reference: dict[str, object],
    payload: bytes,
    media_type: str,
    ordinal: int,
    config_hash: str,
) -> tuple[dict[str, object], dict[str, object]]:
    artifact_id = _raw_sha256(payload)
    artifact = {
        "artifact_id": artifact_id,
        "byte_length": len(payload),
        "media_type": media_type,
        "payload_hex": payload.hex(),
    }
    record = {
        **_base_record(),
        "source_version_id": source_id,
        "native_representation_id": native_id,
        "reference": reference,
        "retrieval": {
            "artifact_id": artifact_id,
            "byte_length": len(payload),
            "media_type": media_type,
        },
        "parent_projection_id": None,
        "ordinal": ordinal,
        "trust": _trust(),
        "provenance": {
            "generator_name": "stdlib-text-csv-projector",
            "generator_version": "0.1.0",
            "generator_config_hash": config_hash,
            "created_at": FIXED_CREATED_AT,
        },
    }
    record["evidence_projection_id"] = _projection_identity(record)
    return record, artifact


def _produce_one(key: str, kind: str, media_type: str, payload: bytes) -> dict[str, object]:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail("source_encoding")
    if "\r" in text:
        _fail("source_newline")
    if kind == "text":
        native_value: dict[str, object] = {
            "format": "plain-text",
            "newline": "lf",
            "source_byte_length": len(payload),
            "text": text,
        }
        first_line = text.splitlines()[0]
        anchors = [
            {
                "anchor_type": "text_span",
                "coordinate_system": "unicode_code_points",
                "start": 0,
                "end": len(first_line),
                "text_length": len(text),
            },
            {
                "anchor_type": "page_region",
                "coordinate_system": "normalized_ppm_top_left",
                "page_number": 1,
                "x": 0,
                "y": 0,
                "width": PPM,
                "height": 250000,
            },
        ]
        retrieval_payloads = [first_line.encode(), payload]
    elif kind == "csv":
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
        except csv.Error:
            _fail("source_csv")
        if not rows or any(not row for row in rows):
            _fail("source_csv")
        width = max(len(row) for row in rows)
        if any(len(row) != width for row in rows):
            _fail("source_csv")
        native_value = {
            "dialect": {"delimiter": ",", "doublequote": True, "quotechar": '"'},
            "format": "rfc4180-table",
            "page_view": {"columns": width, "page_number": 1, "rows": len(rows)},
            "rows": rows,
            "source_byte_length": len(payload),
        }
        flattened = "\n".join("\t".join(row) for row in rows)
        cell = rows[1][1]
        anchors = [
            {
                "anchor_type": "text_span",
                "coordinate_system": "unicode_code_points",
                "start": 0,
                "end": len(flattened),
                "text_length": len(flattened),
            },
            {
                "anchor_type": "page_region",
                "coordinate_system": "normalized_ppm_top_left",
                "page_number": 1,
                "x": 0,
                "y": 0,
                "width": PPM,
                "height": PPM,
            },
            {
                "anchor_type": "table_cell",
                "table": {
                    "provider_profile": "deterministic-grid",
                    "provider_profile_version": "0.1.0",
                    "pointer_format": "stdlib-table-key",
                    "pointer": "tables/main",
                },
                "row_index": 1,
                "column_index": 1,
                "row_span": 1,
                "column_span": 1,
            },
            {
                "anchor_type": "provider_pointer",
                "target": {
                    "provider_profile": "deterministic-grid",
                    "provider_profile_version": "0.1.0",
                    "pointer_format": "stdlib-table-key",
                    "pointer": "tables/main",
                },
            },
        ]
        retrieval_payloads = [
            flattened.encode(),
            canonical_bytes(rows),
            cell.encode(),
            canonical_bytes(native_value),
        ]
    else:
        _fail("source_kind")

    native_payload = canonical_bytes(native_value)
    source_id = _raw_sha256(payload)
    native_artifact_id = _raw_sha256(native_payload)
    config_hash = _canonical_sha256(
        {
            "kind": kind,
            "media_type": media_type,
            "profile": "deterministic-grid",
            "profile_version": "0.1.0",
        }
    )
    native = {
        **_base_record(),
        "source_version_id": source_id,
        "native_artifact_id": native_artifact_id,
        "native_artifact_media_type": "application/json",
        "native_artifact_byte_length": len(native_payload),
        "provider": {
            "name": "stdlib-text-csv",
            "version": "3.12",
            "profile": "deterministic-grid",
            "profile_version": "0.1.0",
            "config_hash": config_hash,
        },
        "created_at": FIXED_CREATED_AT,
    }
    native["native_representation_id"] = _native_identity(native)
    references = [
        _make_reference(source_id, str(native["native_representation_id"]), anchor)
        for anchor in anchors
    ]
    projections: list[dict[str, object]] = []
    artifacts: list[dict[str, object]] = []
    for ordinal, (reference, retrieval_payload) in enumerate(
        zip(references, retrieval_payloads, strict=True)
    ):
        projection, artifact = _make_projection(
            source_id,
            str(native["native_representation_id"]),
            reference,
            retrieval_payload,
            "text/plain" if ordinal == 0 else "application/json",
            ordinal,
            config_hash,
        )
        projections.append(projection)
        artifacts.append(artifact)
    return {
        "key": key,
        "native": native,
        "native_artifact": {
            "artifact_id": native_artifact_id,
            "byte_length": len(native_payload),
            "media_type": "application/json",
            "payload_hex": native_payload.hex(),
        },
        "projections": projections,
        "references": references,
        "retrieval_artifacts": artifacts,
        "source_version_id": source_id,
    }


def _produce(request: dict[str, object], implementation_id: str) -> dict[str, object]:
    reader = ConfinedReader(
        Path(_string(request.get("root"), maximum=4096)), _object(request.get("limits"))
    )
    outputs: dict[str, object] = {}
    observations: list[dict[str, object]] = []
    anchors: set[str] = set()
    for raw_source in _array(request.get("sources"), "manifest"):
        source = _object(raw_source, "manifest")
        _exact_fields(source, {"key", "kind", "media_type", "path", "sha256"})
        key = _string(source["key"])
        if key in outputs:
            _fail("duplicate_source")
        payload = reader.read(source["path"], source["sha256"])
        output = _produce_one(
            key, _string(source["kind"]), _media_type(source["media_type"]), payload
        )
        outputs[key] = output
        for reference in _array(_object(output)["references"]):
            anchors.add(str(_object(_object(reference)["anchor"])["anchor_type"]))
        observations.append(
            {
                "case_id": f"producer:{key}",
                "direction": "alternate_to_reference",
                "expected": "produce",
                "kind": "producer_source",
                "observed": "produce",
                "status": "pass",
            }
        )
    observations.sort(key=lambda item: str(item["case_id"]))
    return {
        "command": "produce",
        "coverage": {
            "anchors": sorted(anchors),
            "source_kinds": sorted(
                {str(_object(item)["kind"]) for item in _array(request.get("sources"))}
            ),
        },
        "implementation_sha256": implementation_id,
        "observations": observations,
        "outputs": outputs,
        "profile_version": PROFILE_VERSION,
    }


def _self_check(implementation_id: str) -> dict[str, object]:
    unavailable = []
    for name in ("openardp", "pydantic", "rfc8785"):
        if importlib.util.find_spec(name) is None:
            unavailable.append(name)
    if unavailable != ["openardp", "pydantic", "rfc8785"]:
        _fail("isolation")
    return {
        "command": "self-check",
        "implementation_sha256": implementation_id,
        "imports_unavailable": unavailable,
        "isolated": bool(sys.flags.isolated),
        "no_site": bool(sys.flags.no_site),
        "profile_version": PROFILE_VERSION,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("consume", "produce"))
    parser.add_argument("--request", type=Path)
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run exactly one closed independent conformance operation."""
    try:
        args = _parse_args()
        implementation_id = _raw_sha256(Path(__file__).resolve().read_bytes())
        if args.self_check:
            if args.command is not None or args.request is not None:
                _fail("request")
            response = _self_check(implementation_id)
        else:
            if args.command is None or args.request is None or not args.request.is_absolute():
                _fail("request")
            if (
                args.request.is_symlink()
                or not args.request.is_file()
                or args.request.stat().st_size > 1_048_576
            ):
                _fail("request")
            request = _object(_load_json_bytes(args.request.read_bytes()), "request")
            common = {"profile_version", "root", "limits"}
            if args.command == "consume":
                _exact_fields(
                    request,
                    common
                    | {
                        "evidence_manifest",
                        "evidence_manifest_sha256",
                        "identity_vectors_sha256",
                        "invalid_categories",
                    },
                )
            else:
                _exact_fields(request, common | {"sources"})
            if request["profile_version"] != PROFILE_VERSION:
                _fail("profile_version")
            response = (
                _consume(request, implementation_id)
                if args.command == "consume"
                else _produce(request, implementation_id)
            )
        output = canonical_bytes(response) + b"\n"
        if len(output) > 1_048_576:
            _fail("resource_limit")
        sys.stdout.buffer.write(output)
        return 0
    except ConformanceFailure as error:
        sys.stderr.buffer.write(f"ALTERNATE_CONFORMANCE_ERROR:{error.category}\n".encode("ascii"))
        return 2
    except Exception:
        sys.stderr.buffer.write(b"ALTERNATE_CONFORMANCE_ERROR:internal\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
