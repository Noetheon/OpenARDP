"""Deterministic BagIt-profile ZIP codec and hostile-package verifier."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import zipfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from openardp.domain.common import validate_json
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.interchange import (
    INTERCHANGE_PROFILE_IDENTIFIER,
    INTERCHANGE_PROFILE_VERSION,
    AssetDisposition,
    InterchangeLimits,
    InterchangePackage,
    PackageInventoryEntry,
    VerifiedPackage,
    payload_path,
    validate_portable_path,
)
from openardp.ports.interchange import (
    AssetByteSource,
    InterchangeIntegrityInvalid,
    InterchangePolicyRejected,
    InterchangeRelationshipInvalid,
    InterchangeResourceExceeded,
    InterchangeSourceChanged,
    MalformedPackage,
    UnsupportedInterchangeVersion,
)

_CHUNK_SIZE = 1024 * 1024
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)
_REGULAR_MODE = (stat.S_IFREG | 0o644) << 16
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
_TAG_MANIFEST_PATHS = frozenset(_REQUIRED_TAGS - {"tagmanifest-sha256.txt"})
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


class LocalAssetSource:
    """Read exact operator-selected local files without exporting their paths."""

    def __init__(self, paths: Mapping[str, Path]) -> None:
        """Capture an exact object-ID-to-path selection."""
        self._paths = dict(paths)

    def iter_asset(self, asset: object, *, chunk_size: int) -> Iterator[bytes]:
        """Stream one safe stable regular file selected by object identity."""
        from openardp.domain.interchange import PortableAsset

        if not isinstance(asset, PortableAsset) or chunk_size <= 0:
            raise InterchangeSourceChanged("export source is invalid")
        path = self._paths.get(asset.object_id)
        if path is None:
            raise InterchangeSourceChanged("included export source is missing")
        raw = path.expanduser().absolute()
        try:
            metadata = raw.lstat()
            if _is_link_or_junction(raw, metadata) or not stat.S_ISREG(metadata.st_mode):
                raise InterchangeSourceChanged("export source is not a safe regular file")
            with raw.open("rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise InterchangeSourceChanged("export source is not a safe regular file")
                while chunk := stream.read(chunk_size):
                    yield chunk
                after = os.fstat(stream.fileno())
        except InterchangeSourceChanged:
            raise
        except OSError:
            raise InterchangeSourceChanged("export source could not be read") from None
        if _file_identity(before) != _file_identity(after) or before.st_size != after.st_size:
            raise InterchangeSourceChanged("export source changed during observation")


class BagItPackageAdapter:
    """Profile writer and independent verifier over ordinary local ZIP files."""

    def write_staged(
        self,
        package: InterchangePackage,
        source: AssetByteSource,
        staging: Path,
        *,
        limits: InterchangeLimits,
    ) -> None:
        """Write deterministic profile bytes to one operation-owned fresh file."""
        included = tuple(
            asset for asset in package.assets if asset.disposition is AssetDisposition.INCLUDED
        )
        payload_manifest = _manifest_bytes(
            {
                asset.payload_path: asset.object_id.removeprefix("sha256:")
                for asset in included
                if asset.payload_path is not None
            }
        )
        record_bytes = canonical_json_bytes(package.model_dump(mode="json"))
        payload_bytes = sum(asset.byte_length for asset in included)
        bag_info = _bag_info(package.package_id, payload_bytes, len(included))
        tags: dict[str, bytes] = {
            "bag-info.txt": bag_info,
            "bagit.txt": _BAGIT,
            "manifest-sha256.txt": payload_manifest,
            "openardp-package.json": record_bytes,
        }
        tags["tagmanifest-sha256.txt"] = _manifest_bytes(
            {path: hashlib.sha256(data).hexdigest() for path, data in tags.items()}
        )
        if sum(len(item) for item in tags.values()) > limits.max_metadata_bytes:
            raise InterchangeResourceExceeded("normative metadata exceeds configured limit")
        entry_count = len(tags) + len(included)
        if entry_count > limits.max_entry_count:
            raise InterchangeResourceExceeded("entry count exceeds configured limit")
        if payload_bytes + sum(len(item) for item in tags.values()) > limits.max_expanded_bytes:
            raise InterchangeResourceExceeded("expanded bytes exceed configured limit")

        payload_paths = [asset.payload_path for asset in included if asset.payload_path is not None]
        entries = sorted((*tags, *payload_paths))
        try:
            with (
                staging.open("w+b") as raw,
                zipfile.ZipFile(
                    raw,
                    mode="w",
                    compression=zipfile.ZIP_STORED,
                    allowZip64=True,
                    strict_timestamps=True,
                ) as archive,
            ):
                for member in entries:
                    assert member is not None
                    info = _zip_info(member)
                    if member in tags:
                        _write_bytes(archive, info, tags[member])
                    else:
                        asset = next(item for item in included if item.payload_path == member)
                        self._write_asset(archive, info, asset, source, limits=limits)
            if staging.stat().st_size > limits.max_archive_bytes:
                raise InterchangeResourceExceeded("archive bytes exceed configured limit")
        except (InterchangeResourceExceeded, InterchangeSourceChanged):
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError):
            raise MalformedPackage("package staging failed") from None

    def verify(self, package: Path, *, limits: InterchangeLimits) -> VerifiedPackage:
        """Verify complete profile structure and bytes without extraction."""
        archive_hash, archive_bytes = _hash_safe_file(package, limits.max_archive_bytes)
        try:
            with package.open("rb") as raw, zipfile.ZipFile(raw, mode="r") as archive:
                if archive.comment:
                    raise InterchangePolicyRejected("archive comment is forbidden")
                infos = archive.infolist()
                self._validate_infos(infos, limits=limits)
                by_name = {item.filename: item for item in infos}
                record_bytes = self._read_metadata(
                    archive,
                    by_name["openardp-package.json"],
                    limits=limits,
                )
                try:
                    record = validate_json(InterchangePackage, record_bytes)
                except ValidationError as error:
                    message = str(error)
                    if "version" in message and (
                        "not installed" in message or "supported" in message
                    ):
                        raise UnsupportedInterchangeVersion(
                            "package version is not installed"
                        ) from None
                    if "relationship" in message or "derived_from" in message:
                        raise InterchangeRelationshipInvalid(
                            "package relationships are invalid"
                        ) from None
                    if (
                        "extension policy" in message
                        or "redistribution" in message
                        or "instruction_execution_allowed" in message
                    ):
                        raise InterchangePolicyRejected(
                            "package semantic policy is invalid"
                        ) from None
                    if "credential" in message or "license" in message or "reference" in message:
                        raise InterchangePolicyRejected(
                            "package semantic policy is invalid"
                        ) from None
                    raise MalformedPackage("package record is invalid") from None
                if canonical_json_bytes(record.model_dump(mode="json")) != record_bytes:
                    raise MalformedPackage("package record is not canonical JSON")
                if len(record.relationships) > limits.max_relationships:
                    raise InterchangeResourceExceeded("relationship count exceeds configured limit")
                self._validate_profile_tags(archive, by_name, record, limits=limits)
                inventory = self._verify_inventory(archive, infos, record, limits=limits)
            replay_hash, replay_bytes = _hash_safe_file(package, limits.max_archive_bytes)
            if (replay_hash, replay_bytes) != (archive_hash, archive_bytes):
                raise InterchangeSourceChanged("package changed during verification")
        except (
            InterchangeIntegrityInvalid,
            InterchangePolicyRejected,
            InterchangeResourceExceeded,
            MalformedPackage,
            UnsupportedInterchangeVersion,
        ):
            raise
        except (OSError, EOFError, KeyError, UnicodeError, zipfile.BadZipFile):
            raise MalformedPackage("package is malformed") from None
        payload = tuple(item for item in inventory if item.kind == "payload")
        tags = tuple(item for item in inventory if item.kind == "tag")
        return VerifiedPackage(
            package=record,
            archive_sha256=archive_hash,
            archive_bytes=archive_bytes,
            payload_count=len(payload),
            payload_bytes=sum(item.byte_length for item in payload),
            tag_count=len(tags),
            tag_bytes=sum(item.byte_length for item in tags),
            inventory=inventory,
        )

    def copy_verified_snapshot(
        self,
        package: Path,
        verified: VerifiedPackage,
        staging: Path,
        *,
        limits: InterchangeLimits,
    ) -> None:
        """Copy only preflight-allowlisted members and reverify exact bytes."""
        current = self.verify(package, limits=limits)
        if current != verified:
            raise InterchangeSourceChanged("package changed after preflight")
        expected = {item.path: item for item in verified.inventory}
        try:
            with package.open("rb") as raw, zipfile.ZipFile(raw, mode="r") as archive:
                for path in sorted(expected):
                    destination = staging.joinpath(*path.split("/"))
                    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    digest = hashlib.sha256()
                    length = 0
                    with archive.open(path, mode="r") as source, destination.open("xb") as output:
                        while chunk := source.read(_CHUNK_SIZE):
                            output.write(chunk)
                            digest.update(chunk)
                            length += len(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                    item = expected[path]
                    if length != item.byte_length or digest.hexdigest() != item.sha256:
                        raise InterchangeIntegrityInvalid(
                            "copied package entry failed verification"
                        )
        except (InterchangeIntegrityInvalid, InterchangeSourceChanged):
            raise
        except (OSError, zipfile.BadZipFile):
            raise MalformedPackage("verified snapshot copy failed") from None

    def verify_snapshot(
        self,
        destination: Path,
        verified: VerifiedPackage,
    ) -> bool:
        """Return whether an existing directory equals the complete verified inventory."""
        if not destination.is_dir() or destination.is_symlink():
            return False
        expected = {item.path: item for item in verified.inventory}
        actual: set[str] = set()
        try:
            for root, directories, files in os.walk(destination, followlinks=False):
                root_path = Path(root)
                for name in (*directories, *files):
                    candidate = root_path / name
                    metadata = candidate.lstat()
                    if _is_link_or_junction(candidate, metadata):
                        return False
                for name in files:
                    candidate = root_path / name
                    relative = candidate.relative_to(destination).as_posix()
                    actual.add(relative)
                    item = expected.get(relative)
                    if item is None:
                        return False
                    digest, length = _hash_safe_file(candidate, item.byte_length)
                    if length != item.byte_length or digest != item.sha256:
                        return False
        except OSError:
            return False
        return actual == set(expected)

    def _write_asset(
        self,
        archive: zipfile.ZipFile,
        info: zipfile.ZipInfo,
        asset: object,
        source: AssetByteSource,
        *,
        limits: InterchangeLimits,
    ) -> None:
        from openardp.domain.interchange import PortableAsset

        assert isinstance(asset, PortableAsset)
        if asset.byte_length > limits.max_entry_bytes:
            raise InterchangeResourceExceeded("entry bytes exceed configured limit")
        digest = hashlib.sha256()
        length = 0
        with archive.open(
            info,
            mode="w",
            force_zip64=asset.byte_length >= zipfile.ZIP64_LIMIT,
        ) as out:
            for chunk in source.iter_asset(asset, chunk_size=_CHUNK_SIZE):
                if not isinstance(chunk, bytes):
                    raise InterchangeSourceChanged("export source returned non-bytes")
                length += len(chunk)
                if length > asset.byte_length or length > limits.max_entry_bytes:
                    raise InterchangeSourceChanged("export source length changed")
                digest.update(chunk)
                out.write(chunk)
        if length != asset.byte_length or f"sha256:{digest.hexdigest()}" != asset.object_id:
            raise InterchangeSourceChanged("export source digest or length changed")

    def _validate_infos(
        self,
        infos: list[zipfile.ZipInfo],
        *,
        limits: InterchangeLimits,
    ) -> None:
        if len(infos) > limits.max_entry_count:
            raise InterchangeResourceExceeded("entry count exceeds configured limit")
        if len(infos) < len(_REQUIRED_TAGS):
            raise MalformedPackage("required profile tags are missing")
        names = tuple(item.filename for item in infos)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise MalformedPackage("archive members must be sorted and unique")
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
                raise InterchangePolicyRejected("archive paths collide by portable case rules")
            folded.add(key)
            is_tag = info.filename in _REQUIRED_TAGS
            if not is_tag and _PAYLOAD_PATH.fullmatch(info.filename) is None:
                raise InterchangePolicyRejected("archive contains an undeclared path")
            if info.is_dir() or info.compress_type != zipfile.ZIP_STORED:
                raise InterchangePolicyRejected("archive entry type or compression is forbidden")
            if info.flag_bits & (0x1 | 0x8):
                raise InterchangePolicyRejected("encrypted or descriptor entries are forbidden")
            if info.date_time != _FIXED_TIME or info.extra or info.comment:
                raise InterchangePolicyRejected("archive metadata is not profile canonical")
            mode = (info.external_attr >> 16) & 0xFFFF
            if info.create_system != 3 or mode != (stat.S_IFREG | 0o644):
                raise InterchangePolicyRejected("archive member is not a canonical regular file")
            if info.file_size != info.compress_size or info.file_size > limits.max_entry_bytes:
                raise InterchangeResourceExceeded("entry bytes exceed configured limit")
            expanded += info.file_size
            if is_tag:
                metadata += info.file_size
        if expanded > limits.max_expanded_bytes or metadata > limits.max_metadata_bytes:
            raise InterchangeResourceExceeded("expanded or metadata bytes exceed configured limit")
        if not _REQUIRED_TAGS.issubset(names):
            raise MalformedPackage("required profile tags are missing")

    def _read_metadata(
        self,
        archive: zipfile.ZipFile,
        info: zipfile.ZipInfo,
        *,
        limits: InterchangeLimits,
    ) -> bytes:
        if info.file_size > limits.max_metadata_bytes:
            raise InterchangeResourceExceeded("metadata entry exceeds configured limit")
        try:
            with archive.open(info, mode="r") as stream:
                data = stream.read(info.file_size + 1)
        except zipfile.BadZipFile:
            raise InterchangeIntegrityInvalid("metadata checksum is invalid") from None
        if len(data) != info.file_size:
            raise InterchangeIntegrityInvalid("metadata length is inconsistent")
        return data

    def _validate_profile_tags(
        self,
        archive: zipfile.ZipFile,
        by_name: dict[str, zipfile.ZipInfo],
        record: InterchangePackage,
        *,
        limits: InterchangeLimits,
    ) -> None:
        if self._read_metadata(archive, by_name["bagit.txt"], limits=limits) != _BAGIT:
            raise MalformedPackage("bagit declaration is invalid")
        included = tuple(
            asset for asset in record.assets if asset.disposition is AssetDisposition.INCLUDED
        )
        expected_info = _bag_info(
            record.package_id,
            sum(item.byte_length for item in included),
            len(included),
        )
        if self._read_metadata(archive, by_name["bag-info.txt"], limits=limits) != expected_info:
            raise MalformedPackage("bag-info declaration is invalid")
        payload_manifest = _parse_manifest(
            self._read_metadata(archive, by_name["manifest-sha256.txt"], limits=limits)
        )
        expected_payload = {
            item.payload_path: item.object_id.removeprefix("sha256:")
            for item in included
            if item.payload_path is not None
        }
        if payload_manifest != expected_payload:
            raise InterchangeIntegrityInvalid("payload manifest disagrees with package record")
        tag_manifest = _parse_manifest(
            self._read_metadata(archive, by_name["tagmanifest-sha256.txt"], limits=limits)
        )
        if set(tag_manifest) != _TAG_MANIFEST_PATHS:
            raise InterchangeIntegrityInvalid("tag manifest is incomplete")
        for path, expected in tag_manifest.items():
            data = self._read_metadata(archive, by_name[path], limits=limits)
            if hashlib.sha256(data).hexdigest() != expected:
                raise InterchangeIntegrityInvalid("tag manifest digest mismatch")

    def _verify_inventory(
        self,
        archive: zipfile.ZipFile,
        infos: list[zipfile.ZipInfo],
        record: InterchangePackage,
        *,
        limits: InterchangeLimits,
    ) -> tuple[PackageInventoryEntry, ...]:
        expected_assets = {
            item.payload_path: item
            for item in record.assets
            if item.disposition is AssetDisposition.INCLUDED and item.payload_path is not None
        }
        inventory: list[PackageInventoryEntry] = []
        for info in infos:
            digest = hashlib.sha256()
            length = 0
            try:
                with archive.open(info, mode="r") as stream:
                    while chunk := stream.read(_CHUNK_SIZE):
                        length += len(chunk)
                        if length > info.file_size or length > limits.max_entry_bytes:
                            raise InterchangeResourceExceeded(
                                "entry expanded beyond configured limit"
                            )
                        digest.update(chunk)
            except zipfile.BadZipFile:
                raise InterchangeIntegrityInvalid("entry checksum is invalid") from None
            if length != info.file_size:
                raise InterchangeIntegrityInvalid("entry length mismatch")
            hexdigest = digest.hexdigest()
            kind: Literal["payload", "tag"] = (
                "tag" if info.filename in _REQUIRED_TAGS else "payload"
            )
            if kind == "payload":
                asset = expected_assets.get(info.filename)
                if asset is not None and asset.media_type in _ARCHIVE_MEDIA_TYPES:
                    raise InterchangePolicyRejected("nested archive assets are forbidden")
                if (
                    asset is None
                    or asset.byte_length != length
                    or asset.object_id != f"sha256:{hexdigest}"
                ):
                    raise InterchangeIntegrityInvalid("payload identity or policy mismatch")
                if payload_path(asset.object_id) != info.filename:
                    raise InterchangeIntegrityInvalid("payload path does not match identity")
            inventory.append(
                PackageInventoryEntry(
                    path=info.filename,
                    byte_length=length,
                    sha256=hexdigest,
                    kind=kind,
                )
            )
        if {item.path for item in inventory if item.kind == "payload"} != set(expected_assets):
            raise InterchangeIntegrityInvalid("payload inventory is not exhaustive")
        return tuple(inventory)


def _zip_info(path: str) -> zipfile.ZipInfo:
    validate_portable_path(path)
    info = zipfile.ZipInfo(path, date_time=_FIXED_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = _REGULAR_MODE
    info.flag_bits = 0
    info.extra = b""
    info.comment = b""
    return info


def _write_bytes(archive: zipfile.ZipFile, info: zipfile.ZipInfo, data: bytes) -> None:
    with archive.open(info, mode="w", force_zip64=len(data) >= zipfile.ZIP64_LIMIT) as stream:
        stream.write(data)


def _manifest_bytes(entries: Mapping[str, str]) -> bytes:
    return b"".join(f"{digest}  {path}\n".encode() for path, digest in sorted(entries.items()))


def _parse_manifest(data: bytes) -> dict[str, str]:
    if not data.endswith(b"\n") and data:
        raise MalformedPackage("manifest must end with LF")
    result: dict[str, str] = {}
    for raw_line in data.splitlines():
        matched = _MANIFEST_LINE.fullmatch(raw_line)
        if matched is None:
            raise MalformedPackage("manifest line is invalid")
        try:
            path = matched.group(2).decode("utf-8")
        except UnicodeDecodeError:
            raise MalformedPackage("manifest path is not UTF-8") from None
        validate_portable_path(path)
        if path in result:
            raise MalformedPackage("manifest path is duplicated")
        result[path] = matched.group(1).decode("ascii")
    if tuple(result) != tuple(sorted(result)):
        raise MalformedPackage("manifest paths are not sorted")
    return result


def _bag_info(package_id: str, payload_bytes: int, payload_count: int) -> bytes:
    text = (
        f"BagIt-Profile-Identifier: {INTERCHANGE_PROFILE_IDENTIFIER}\n"
        f"OpenARDP-Export-Profile: {INTERCHANGE_PROFILE_VERSION}\n"
        f"OpenARDP-Package-Id: {package_id}\n"
        f"Payload-Oxum: {payload_bytes}.{payload_count}\n"
    )
    return text.encode("ascii")


def _hash_safe_file(path: Path, limit: int) -> tuple[str, int]:
    raw = path.expanduser().absolute()
    try:
        metadata = raw.lstat()
        if _is_link_or_junction(raw, metadata) or not stat.S_ISREG(metadata.st_mode):
            raise MalformedPackage("package entrypoint is not a safe regular file")
        if metadata.st_size > limit:
            raise InterchangeResourceExceeded("archive bytes exceed configured limit")
        digest = hashlib.sha256()
        length = 0
        with raw.open("rb") as stream:
            before = os.fstat(stream.fileno())
            while chunk := stream.read(_CHUNK_SIZE):
                length += len(chunk)
                if length > limit:
                    raise InterchangeResourceExceeded("archive bytes exceed configured limit")
                digest.update(chunk)
            after = os.fstat(stream.fileno())
    except (InterchangeResourceExceeded, MalformedPackage):
        raise
    except OSError:
        raise MalformedPackage("package could not be read") from None
    if _file_identity(before) != _file_identity(after) or before.st_size != after.st_size:
        raise InterchangeSourceChanged("package changed during verification")
    return digest.hexdigest(), length


def _file_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    if os.name != "nt":
        return False
    return bool(getattr(metadata, "st_reparse_tag", 0)) or path.is_symlink()


def sync_directory(path: Path) -> None:
    """Synchronize a directory where supported without weakening publication errors."""
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def owned_temporary_file(destination: Path) -> Iterator[Path]:
    """Yield one fresh sibling staging file and remove only that owned path."""
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.export-", suffix=".part", dir=destination.parent
    )
    os.close(descriptor)
    path = Path(name)
    try:
        yield path
    finally:
        with suppress(OSError):
            path.unlink(missing_ok=True)


__all__ = [
    "BagItPackageAdapter",
    "LocalAssetSource",
    "owned_temporary_file",
    "sync_directory",
]
