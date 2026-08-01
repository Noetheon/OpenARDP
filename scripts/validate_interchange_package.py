"""Independently validate one experimental OpenARDP BagIt-profile package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import zipfile
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from openardp.domain.common import validate_json
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.interchange import (
    INTERCHANGE_PROFILE_IDENTIFIER,
    INTERCHANGE_PROFILE_VERSION,
    AssetDisposition,
    InterchangeLimits,
    InterchangePackage,
    payload_path,
    validate_portable_path,
)
from openardp.ports.interchange import (
    InterchangeDestinationConflict,
    InterchangeError,
    InterchangeIntegrityInvalid,
    InterchangePolicyRejected,
    InterchangePublicationFailed,
    InterchangeRelationshipInvalid,
    InterchangeResourceExceeded,
    InterchangeSourceChanged,
    MalformedPackage,
    UnsupportedInterchangeVersion,
)

_CHUNK_SIZE = 1024 * 1024
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)
_PAYLOAD_PATH = re.compile(r"^data/objects/sha256/[0-9a-f]{2}/[0-9a-f]{62}$")
_MANIFEST_LINE = re.compile(rb"^([0-9a-f]{64})  ([^\r\n]+)$")
_REQUIRED_TAGS = frozenset(
    {
        "bagit.txt",
        "bag-info.txt",
        "manifest-sha256.txt",
        "openardp-package.json",
        "tagmanifest-sha256.txt",
    }
)
_TAG_MANIFEST_PATHS = _REQUIRED_TAGS - {"tagmanifest-sha256.txt"}
_BAGIT = b"BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n"
_ARCHIVE_MEDIA_TYPES = frozenset(
    {
        "application/gzip",
        "application/vnd.rar",
        "application/x-7z-compressed",
        "application/x-tar",
        "application/zip",
    }
)


def classify(error: InterchangeError) -> str:
    """Map one sanitized failure to the stable corpus category."""
    mappings: tuple[tuple[type[InterchangeError], str], ...] = (
        (UnsupportedInterchangeVersion, "unsupported_version"),
        (InterchangeResourceExceeded, "resource_exhausted"),
        (InterchangeIntegrityInvalid, "integrity_invalid"),
        (InterchangeRelationshipInvalid, "relationship_invalid"),
        (InterchangeSourceChanged, "source_changed"),
        (InterchangeDestinationConflict, "destination_conflict"),
        (InterchangePublicationFailed, "publication_failed"),
        (InterchangePolicyRejected, "policy_rejected"),
        (MalformedPackage, "malformed_package"),
    )
    return next(code for kind, code in mappings if isinstance(error, kind))


def validate(path: Path, *, limits: InterchangeLimits | None = None) -> dict[str, object]:
    """Return a body-free result from a stdlib/domain-only independent reader."""
    effective = limits or InterchangeLimits()
    archive_sha256, archive_bytes = _hash_archive(path, effective.max_archive_bytes)
    try:
        with path.open("rb") as raw, zipfile.ZipFile(raw, mode="r") as archive:
            if archive.comment:
                raise InterchangePolicyRejected("archive comment is forbidden")
            infos = archive.infolist()
            _validate_infos(infos, effective)
            by_name = {item.filename: item for item in infos}
            record_bytes = _read(archive, by_name["openardp-package.json"], effective)
            record = _parse_record(record_bytes)
            if len(record.relationships) > effective.max_relationships:
                raise InterchangeResourceExceeded("relationship limit exceeded")
            _validate_tags(archive, by_name, record, effective)
            payload_bytes = _verify_members(archive, infos, record, effective)
        replay_sha256, replay_bytes = _hash_archive(path, effective.max_archive_bytes)
        if (replay_sha256, replay_bytes) != (archive_sha256, archive_bytes):
            raise InterchangeSourceChanged("package changed during validation")
    except InterchangeError:
        raise
    except (OSError, EOFError, KeyError, UnicodeError, zipfile.BadZipFile):
        raise MalformedPackage("package is malformed") from None
    return {
        "archive_bytes": archive_bytes,
        "archive_sha256": archive_sha256,
        "asset_count": len(record.assets),
        "entry_count": len(infos),
        "outcome": "valid",
        "package_id": record.package_id,
        "payload_bytes": payload_bytes,
        "profile_version": record.profile_version,
        "record_count": len(record.records),
        "relationship_count": len(record.relationships),
        "schema_version": record.schema_version,
    }


def _parse_record(data: bytes) -> InterchangePackage:
    try:
        record = validate_json(InterchangePackage, data)
    except ValidationError as error:
        message = str(error)
        if "version" in message and ("not installed" in message or "supported" in message):
            raise UnsupportedInterchangeVersion("package version is not installed") from None
        if "relationship" in message or "derived_from" in message:
            raise InterchangeRelationshipInvalid("package relationships are invalid") from None
        if (
            "extension policy" in message
            or "redistribution" in message
            or "instruction_execution_allowed" in message
            or "credential" in message
            or "license" in message
            or "reference" in message
        ):
            raise InterchangePolicyRejected("package semantic policy is invalid") from None
        raise MalformedPackage("package record is invalid") from None
    if canonical_json_bytes(record.model_dump(mode="json")) != data:
        raise MalformedPackage("package record is not canonical")
    return record


def _validate_infos(infos: list[zipfile.ZipInfo], limits: InterchangeLimits) -> None:
    if len(infos) > limits.max_entry_count:
        raise InterchangeResourceExceeded("entry count exceeds configured limit")
    if len(infos) < len(_REQUIRED_TAGS):
        raise MalformedPackage("required tags are missing")
    names = tuple(item.filename for item in infos)
    if names != tuple(sorted(names)) or len(names) != len(set(names)):
        raise MalformedPackage("members must be sorted and unique")
    folded: set[str] = set()
    expanded = 0
    metadata = 0
    for info in infos:
        try:
            validate_portable_path(
                info.filename,
                max_bytes=4_096,
                max_depth=64,
            )
        except ValueError:
            raise InterchangePolicyRejected("archive path is not portable") from None
        if (
            len(info.filename.encode("utf-8")) > limits.max_path_bytes
            or len(info.filename.split("/")) > limits.max_path_depth
        ):
            raise InterchangeResourceExceeded("archive path exceeds configured limit")
        key = info.filename.casefold()
        if key in folded:
            raise InterchangePolicyRejected("archive paths collide")
        folded.add(key)
        is_tag = info.filename in _REQUIRED_TAGS
        if not is_tag and _PAYLOAD_PATH.fullmatch(info.filename) is None:
            raise InterchangePolicyRejected("archive path is undeclared")
        if info.is_dir() or info.compress_type != zipfile.ZIP_STORED:
            raise InterchangePolicyRejected("archive entry type is forbidden")
        if info.flag_bits & (0x1 | 0x8):
            raise InterchangePolicyRejected("archive entry flags are forbidden")
        if info.date_time != _FIXED_TIME or info.extra or info.comment:
            raise InterchangePolicyRejected("archive metadata is non-canonical")
        mode = (info.external_attr >> 16) & 0xFFFF
        if info.create_system != 3 or mode != (stat.S_IFREG | 0o644):
            raise InterchangePolicyRejected("archive entry is not a regular profile file")
        if info.file_size != info.compress_size or info.file_size > limits.max_entry_bytes:
            raise InterchangeResourceExceeded("entry bytes exceed configured limit")
        expanded += info.file_size
        if is_tag:
            metadata += info.file_size
    if expanded > limits.max_expanded_bytes or metadata > limits.max_metadata_bytes:
        raise InterchangeResourceExceeded("expanded or metadata limit exceeded")
    if not _REQUIRED_TAGS.issubset(names):
        raise MalformedPackage("required tags are missing")


def _validate_tags(
    archive: zipfile.ZipFile,
    by_name: dict[str, zipfile.ZipInfo],
    record: InterchangePackage,
    limits: InterchangeLimits,
) -> None:
    if _read(archive, by_name["bagit.txt"], limits) != _BAGIT:
        raise MalformedPackage("bagit declaration is invalid")
    included = tuple(
        asset for asset in record.assets if asset.disposition is AssetDisposition.INCLUDED
    )
    expected_info = _bag_info(
        record.package_id,
        sum(item.byte_length for item in included),
        len(included),
    )
    if _read(archive, by_name["bag-info.txt"], limits) != expected_info:
        raise MalformedPackage("bag-info is invalid")
    payload_manifest = _manifest(_read(archive, by_name["manifest-sha256.txt"], limits))
    expected_payload = {
        item.payload_path: item.object_id.removeprefix("sha256:")
        for item in included
        if item.payload_path is not None
    }
    if payload_manifest != expected_payload:
        raise InterchangeIntegrityInvalid("payload manifest disagrees")
    tag_manifest = _manifest(_read(archive, by_name["tagmanifest-sha256.txt"], limits))
    if set(tag_manifest) != _TAG_MANIFEST_PATHS:
        raise InterchangeIntegrityInvalid("tag manifest is incomplete")
    for name, expected in tag_manifest.items():
        if hashlib.sha256(_read(archive, by_name[name], limits)).hexdigest() != expected:
            raise InterchangeIntegrityInvalid("tag digest mismatch")


def _verify_members(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    record: InterchangePackage,
    limits: InterchangeLimits,
) -> int:
    expected = {
        item.payload_path: item
        for item in record.assets
        if item.disposition is AssetDisposition.INCLUDED and item.payload_path is not None
    }
    observed: set[str] = set()
    payload_bytes = 0
    for info in infos:
        digest = hashlib.sha256()
        length = 0
        try:
            with archive.open(info) as stream:
                while chunk := stream.read(_CHUNK_SIZE):
                    length += len(chunk)
                    if length > info.file_size or length > limits.max_entry_bytes:
                        raise InterchangeResourceExceeded("entry expanded beyond limit")
                    digest.update(chunk)
        except zipfile.BadZipFile:
            raise InterchangeIntegrityInvalid("entry checksum is invalid") from None
        if length != info.file_size:
            raise InterchangeIntegrityInvalid("entry length is invalid")
        if info.filename not in _REQUIRED_TAGS:
            asset = expected.get(info.filename)
            if asset is not None and asset.media_type in _ARCHIVE_MEDIA_TYPES:
                raise InterchangePolicyRejected("nested archive assets are forbidden")
            if (
                asset is None
                or asset.byte_length != length
                or asset.object_id != f"sha256:{digest.hexdigest()}"
                or payload_path(asset.object_id) != info.filename
            ):
                raise InterchangeIntegrityInvalid("payload identity is invalid")
            observed.add(info.filename)
            payload_bytes += length
    if observed != set(expected):
        raise InterchangeIntegrityInvalid("payload inventory is incomplete")
    return payload_bytes


def _read(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    limits: InterchangeLimits,
) -> bytes:
    if info.file_size > limits.max_metadata_bytes:
        raise InterchangeResourceExceeded("metadata entry exceeds limit")
    try:
        with archive.open(info) as stream:
            data = stream.read(info.file_size + 1)
    except zipfile.BadZipFile:
        raise InterchangeIntegrityInvalid("metadata checksum is invalid") from None
    if len(data) != info.file_size:
        raise InterchangeIntegrityInvalid("metadata length is invalid")
    return data


def _manifest(data: bytes) -> dict[str, str]:
    if data and not data.endswith(b"\n"):
        raise MalformedPackage("manifest must end with LF")
    result: dict[str, str] = {}
    for line in data.splitlines():
        matched = _MANIFEST_LINE.fullmatch(line)
        if matched is None:
            raise MalformedPackage("manifest line is invalid")
        try:
            path = matched.group(2).decode("utf-8")
            validate_portable_path(path)
        except (UnicodeDecodeError, ValueError):
            raise MalformedPackage("manifest path is invalid") from None
        if path in result:
            raise MalformedPackage("manifest path is duplicated")
        result[path] = matched.group(1).decode("ascii")
    if tuple(result) != tuple(sorted(result)):
        raise MalformedPackage("manifest is not sorted")
    return result


def _bag_info(package_id: str, payload_bytes: int, payload_count: int) -> bytes:
    return (
        f"BagIt-Profile-Identifier: {INTERCHANGE_PROFILE_IDENTIFIER}\n"
        f"OpenARDP-Export-Profile: {INTERCHANGE_PROFILE_VERSION}\n"
        f"OpenARDP-Package-Id: {package_id}\n"
        f"Payload-Oxum: {payload_bytes}.{payload_count}\n"
    ).encode("ascii")


def _hash_archive(path: Path, limit: int) -> tuple[str, int]:
    raw = path.expanduser().absolute()
    try:
        metadata = raw.lstat()
        if raw.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise MalformedPackage("package is not a regular file")
        if metadata.st_size > limit:
            raise InterchangeResourceExceeded("archive bytes exceed limit")
        digest = hashlib.sha256()
        length = 0
        with raw.open("rb") as stream:
            before = os.fstat(stream.fileno())
            while chunk := stream.read(_CHUNK_SIZE):
                length += len(chunk)
                if length > limit:
                    raise InterchangeResourceExceeded("archive bytes exceed limit")
                digest.update(chunk)
            after = os.fstat(stream.fileno())
    except InterchangeError:
        raise
    except OSError:
        raise MalformedPackage("package could not be read") from None
    if (before.st_dev, before.st_ino) != (
        after.st_dev,
        after.st_ino,
    ) or before.st_size != after.st_size:
        raise InterchangeSourceChanged("package changed during validation")
    return digest.hexdigest(), length


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate one package with stable body-free output and exit status."""
    arguments = _parser().parse_args(argv)
    try:
        result = validate(arguments.package)
    except InterchangeError as error:
        result = {"error": classify(error), "outcome": "invalid"}
        if arguments.json_output:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        else:
            print(f"invalid: {result['error']}")
        return 2
    if arguments.json_output:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"valid: {result['package_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
