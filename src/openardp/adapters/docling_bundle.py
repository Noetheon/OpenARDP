"""Closed contracts and exact local verification for the Docling PDF bundle."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Annotated, Self, cast

from pydantic import Field, JsonValue, StringConstraints, field_validator, model_validator

from openardp.domain.common import MAX_SAFE_INTEGER, DomainModel, Sha256Id
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.rich_ingestion import ModelBundleFile, ModelBundleManifest

SOURCE_LOCK_SCHEMA_VERSION = "0.1.0"
PROVENANCE_SCHEMA_VERSION = "0.1.0"
SOURCE_LOCK_FILENAME = "source-lock.json"
MANIFEST_FILENAME = "manifest.json"
PROVENANCE_FILENAME = "provenance.json"
ASSET_DIRECTORY = "assets"
MAX_CONTROL_FILE_BYTES = 1_048_576
_READ_CHUNK_BYTES = 1_048_576
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_LICENSE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+():/_ -]{0,255}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

BoundedName = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]


class BundleValidationError(ValueError):
    """Report a sanitized invalid-bundle classification."""

    def __init__(self) -> None:
        """Initialize the stable public failure message."""
        super().__init__("PDF model bundle invalid")


def safe_relative_path(value: str) -> str:
    """Validate one control-free traversal-free relative POSIX path."""
    if not isinstance(value, str) or _CONTROL.search(value) is not None or "\\" in value:
        raise ValueError("bundle path invalid")
    path = PurePosixPath(value)
    parts = value.split("/")
    if (
        path.is_absolute()
        or not parts
        or any(part in {"", ".", ".."} for part in parts)
        or path.as_posix() != value
    ):
        raise ValueError("bundle path invalid")
    return value


def _collision_key(path: str) -> str:
    return unicodedata.normalize("NFC", path).casefold()


def _validate_path_set(paths: tuple[str, ...]) -> None:
    if len(paths) != len(set(paths)):
        raise ValueError("bundle paths must be unique")
    keys = tuple(_collision_key(path) for path in paths)
    if len(keys) != len(set(keys)):
        raise ValueError("bundle paths must not collide")


class PdfModelSource(DomainModel):
    """One reviewed immutable upstream model repository."""

    repository_id: BoundedName
    revision: BoundedName
    license_id: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256)]
    license_evidence_url: Annotated[
        str, StringConstraints(strict=True, min_length=8, max_length=2048)
    ]

    @field_validator("repository_id")
    @classmethod
    def _repository_is_bounded(cls, value: str) -> str:
        if _REPOSITORY.fullmatch(value) is None:
            raise ValueError("repository identifier invalid")
        return value

    @field_validator("revision")
    @classmethod
    def _revision_is_immutable(cls, value: str) -> str:
        if _REVISION.fullmatch(value) is None:
            raise ValueError("revision must be a full immutable identifier")
        return value

    @field_validator("license_id")
    @classmethod
    def _license_is_reviewable(cls, value: str) -> str:
        if _LICENSE.fullmatch(value) is None:
            raise ValueError("license identifier invalid")
        return value

    @field_validator("license_evidence_url")
    @classmethod
    def _evidence_url_is_https_without_query(cls, value: str) -> str:
        if not value.startswith("https://") or "?" in value or "#" in value:
            raise ValueError("license evidence URL invalid")
        return value


class PdfModelSourceFile(DomainModel):
    """One exact source-to-runtime file mapping."""

    repository_id: BoundedName
    revision: BoundedName
    source_path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]
    destination_path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]
    sha256: Sha256Id
    byte_length: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    license_id: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256)]

    @field_validator("source_path", "destination_path")
    @classmethod
    def _paths_are_safe(cls, value: str) -> str:
        return safe_relative_path(value)

    @field_validator("revision")
    @classmethod
    def _revision_is_immutable(cls, value: str) -> str:
        if _REVISION.fullmatch(value) is None:
            raise ValueError("revision must be a full immutable identifier")
        return value

    @classmethod
    def validate_destination_set(cls, paths: tuple[str, ...]) -> None:
        """Reject exact, case-folded and Unicode-normalized aliases."""
        for path in paths:
            safe_relative_path(path)
        _validate_path_set(paths)


class PdfBundleReviewFile(DomainModel):
    """One exact local license or notice file copied into an installation."""

    path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]
    sha256: Sha256Id
    byte_length: int = Field(strict=True, gt=0, le=MAX_CONTROL_FILE_BYTES)

    @field_validator("path")
    @classmethod
    def _path_is_safe(cls, value: str) -> str:
        return safe_relative_path(value)


class PdfModelSourceLock(DomainModel):
    """Canonical immutable source and review contract for one PDF bundle."""

    schema_version: str = SOURCE_LOCK_SCHEMA_VERSION
    bundle_name: BoundedName
    bundle_version: BoundedName
    docling_version: BoundedName
    provider_profile: BoundedName
    provider_profile_version: BoundedName
    max_file_bytes: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    max_total_asset_bytes: int = Field(strict=True, gt=0, le=MAX_SAFE_INTEGER)
    sources: tuple[PdfModelSource, ...]
    files: tuple[PdfModelSourceFile, ...]
    review_files: tuple[PdfBundleReviewFile, ...]

    @model_validator(mode="after")
    def _inventory_is_closed_sorted_and_reconciled(self) -> Self:
        if self.schema_version != SOURCE_LOCK_SCHEMA_VERSION:
            raise ValueError("source lock schema unsupported")
        source_ids = tuple(source.repository_id for source in self.sources)
        if source_ids != tuple(sorted(source_ids)) or len(source_ids) != len(set(source_ids)):
            raise ValueError("sources must be sorted and unique")
        by_id = {source.repository_id: source for source in self.sources}
        destinations = tuple(item.destination_path for item in self.files)
        if destinations != tuple(sorted(destinations)):
            raise ValueError("source files must be sorted by destination")
        PdfModelSourceFile.validate_destination_set(destinations)
        if sum(item.byte_length for item in self.files) > self.max_total_asset_bytes:
            raise ValueError("aggregate asset limit exceeded")
        for item in self.files:
            source = by_id.get(item.repository_id)
            if (
                source is None
                or source.revision != item.revision
                or source.license_id != item.license_id
                or item.byte_length > self.max_file_bytes
            ):
                raise ValueError("source file does not reconcile")
        review_paths = tuple(item.path for item in self.review_files)
        if review_paths != tuple(sorted(review_paths)):
            raise ValueError("review files must be sorted")
        _validate_path_set(review_paths)
        return self

    @property
    def lock_id(self) -> str:
        """Return the path-independent canonical source-lock identity."""
        return canonical_sha256(self.model_dump(mode="json"))


class BundleVerificationResult(DomainModel):
    """Body-free exact verification result for one installed bundle."""

    source_lock_id: Sha256Id
    bundle_id: Sha256Id
    asset_file_count: int = Field(strict=True, ge=0)
    asset_bytes: int = Field(strict=True, ge=0)
    installation_file_count: int = Field(strict=True, ge=0)
    installation_bytes: int = Field(strict=True, ge=0)


def _canonical_bytes(model: DomainModel) -> bytes:
    return canonical_json_bytes(model.model_dump(mode="json")) + b"\n"


def _read_regular(path: Path, *, limit: int) -> bytes:
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise BundleValidationError
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_ino != metadata.st_ino:
                raise BundleValidationError
            payload = handle.read(limit + 1)
    except (OSError, BundleValidationError):
        raise BundleValidationError from None
    if len(payload) > limit:
        raise BundleValidationError
    return payload


def load_source_lock(path: Path) -> PdfModelSourceLock:
    """Load one bounded regular canonical source lock without following links."""
    payload = _read_regular(path, limit=MAX_CONTROL_FILE_BYTES)
    try:
        lock = PdfModelSourceLock.model_validate_json(payload)
    except (ValueError, TypeError):
        raise BundleValidationError from None
    if payload != _canonical_bytes(lock):
        raise BundleValidationError
    return lock


def build_model_manifest(lock: PdfModelSourceLock) -> ModelBundleManifest:
    """Project a source lock into the existing F007 model manifest contract."""
    return ModelBundleManifest(
        bundle_name=lock.bundle_name,
        bundle_version=lock.bundle_version,
        files=tuple(
            ModelBundleFile(
                path=item.destination_path,
                sha256=item.sha256,
                byte_length=item.byte_length,
                license_id=item.license_id,
            )
            for item in lock.files
        ),
        extensions={
            "https://openardp.org/ns/pdf-model-source-lock": lock.lock_id,
        },
    )


def _provenance_bytes(lock: PdfModelSourceLock, manifest: ModelBundleManifest) -> bytes:
    value = {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "source_lock_id": lock.lock_id,
        "bundle_id": manifest.bundle_id,
        "sources": [source.model_dump(mode="json") for source in lock.sources],
        "files": [item.model_dump(mode="json") for item in lock.files],
    }
    return canonical_json_bytes(cast(JsonValue, value)) + b"\n"


def materialize_control_files(install_root: Path, *, lock_path: Path) -> ModelBundleManifest:
    """Write deterministic control/review files beside an already staged asset tree."""
    lock = load_source_lock(lock_path)
    manifest = build_model_manifest(lock)
    install_root.joinpath(SOURCE_LOCK_FILENAME).write_bytes(_canonical_bytes(lock))
    install_root.joinpath(MANIFEST_FILENAME).write_bytes(_canonical_bytes(manifest))
    install_root.joinpath(PROVENANCE_FILENAME).write_bytes(_provenance_bytes(lock, manifest))
    review_root = lock_path.parent
    for item in lock.review_files:
        payload = _read_regular(review_root / item.path, limit=item.byte_length)
        if len(payload) != item.byte_length or _sha256(payload) != item.sha256:
            raise BundleValidationError
        target = install_root.joinpath(*item.path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return manifest


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _hash_regular(path: Path, *, expected_length: int) -> str:
    digest = hashlib.sha256()
    observed = 0
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise BundleValidationError
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_ino != metadata.st_ino:
                raise BundleValidationError
            while chunk := handle.read(_READ_CHUNK_BYTES):
                observed += len(chunk)
                if observed > expected_length:
                    raise BundleValidationError
                digest.update(chunk)
    except (OSError, BundleValidationError):
        raise BundleValidationError from None
    if observed != expected_length:
        raise BundleValidationError
    return "sha256:" + digest.hexdigest()


def _expected_installation_files(lock: PdfModelSourceLock) -> dict[str, tuple[int, str]]:
    manifest = build_model_manifest(lock)
    expected: dict[str, tuple[int, str]] = {
        SOURCE_LOCK_FILENAME: (len(_canonical_bytes(lock)), _sha256(_canonical_bytes(lock))),
        MANIFEST_FILENAME: (len(_canonical_bytes(manifest)), _sha256(_canonical_bytes(manifest))),
        PROVENANCE_FILENAME: (
            len(_provenance_bytes(lock, manifest)),
            _sha256(_provenance_bytes(lock, manifest)),
        ),
    }
    expected.update({item.path: (item.byte_length, item.sha256) for item in lock.review_files})
    expected.update(
        {
            f"{ASSET_DIRECTORY}/{item.destination_path}": (item.byte_length, item.sha256)
            for item in lock.files
        }
    )
    return expected


def _inventory_regular_tree(root: Path) -> tuple[dict[str, Path], set[str]]:
    files: dict[str, Path] = {}
    directories: set[str] = set()
    try:
        root_metadata = root.lstat()
        if root.is_symlink() or not stat.S_ISDIR(root_metadata.st_mode):
            raise BundleValidationError
        pending = [(root, "")]
        while pending:
            directory, relative = pending.pop()
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
            for entry in entries:
                child_relative = f"{relative}/{entry.name}" if relative else entry.name
                safe_relative_path(child_relative)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    raise BundleValidationError
                if stat.S_ISDIR(metadata.st_mode):
                    directories.add(child_relative)
                    pending.append((Path(entry.path), child_relative))
                elif stat.S_ISREG(metadata.st_mode):
                    files[child_relative] = Path(entry.path)
                else:
                    raise BundleValidationError
    except (OSError, ValueError, BundleValidationError):
        raise BundleValidationError from None
    _validate_path_set(tuple(files))
    _validate_path_set(tuple(directories))
    return files, directories


def _expected_directories(paths: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for path in paths:
        parts = path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            result.add("/".join(parts[:index]))
    return result


def verify_installation(
    install_root: Path,
    *,
    expected_source_lock: Path,
) -> BundleVerificationResult:
    """Verify one exact closed installation against an independent source lock."""
    lock = load_source_lock(expected_source_lock)
    internal_lock = _read_regular(
        install_root / SOURCE_LOCK_FILENAME,
        limit=MAX_CONTROL_FILE_BYTES,
    )
    if internal_lock != _canonical_bytes(lock):
        raise BundleValidationError
    expected = _expected_installation_files(lock)
    observed, directories = _inventory_regular_tree(install_root)
    if set(observed) != set(expected):
        raise BundleValidationError
    if directories != _expected_directories(tuple(expected)):
        raise BundleValidationError
    for path, (length, digest) in expected.items():
        if _hash_regular(observed[path], expected_length=length) != digest:
            raise BundleValidationError
    manifest_payload = _read_regular(
        install_root / MANIFEST_FILENAME,
        limit=MAX_CONTROL_FILE_BYTES,
    )
    manifest = build_model_manifest(lock)
    if manifest_payload != _canonical_bytes(manifest):
        raise BundleValidationError
    return BundleVerificationResult(
        source_lock_id=lock.lock_id,
        bundle_id=manifest.bundle_id,
        asset_file_count=len(lock.files),
        asset_bytes=sum(item.byte_length for item in lock.files),
        installation_file_count=len(expected),
        installation_bytes=sum(length for length, _digest in expected.values()),
    )


def verify_model_asset_tree(root: Path, manifest: ModelBundleManifest) -> Path:
    """Verify an exact manifest-closed model root without source-lock control files."""
    expected = {item.path: (item.byte_length, item.sha256) for item in manifest.files}
    paths = tuple(expected)
    if paths != tuple(sorted(paths)):
        raise BundleValidationError
    try:
        _validate_path_set(paths)
        observed, directories = _inventory_regular_tree(root)
    except (ValueError, BundleValidationError):
        raise BundleValidationError from None
    if set(observed) != set(expected) or directories != _expected_directories(paths):
        raise BundleValidationError
    for path, (length, digest) in expected.items():
        if _hash_regular(observed[path], expected_length=length) != digest:
            raise BundleValidationError
    return root


__all__ = [
    "ASSET_DIRECTORY",
    "MANIFEST_FILENAME",
    "SOURCE_LOCK_FILENAME",
    "BundleValidationError",
    "BundleVerificationResult",
    "PdfBundleReviewFile",
    "PdfModelSource",
    "PdfModelSourceFile",
    "PdfModelSourceLock",
    "build_model_manifest",
    "load_source_lock",
    "materialize_control_files",
    "safe_relative_path",
    "verify_installation",
    "verify_model_asset_tree",
]
