"""Exact offline trust boundary for one optional semantic model bundle."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path, PurePosixPath
from typing import Self

from pydantic import Field, model_validator

from openardp.domain.common import DomainModel, Sha256Id, validate_json
from openardp.domain.identity import canonical_json_bytes, canonical_sha256

EMBEDDING_ASSET_DIRECTORY = "assets"
EMBEDDING_BUNDLE_MANIFEST = "manifest.json"
EMBEDDING_BUNDLE_SOURCE_LOCK = "source-lock.json"
_CHUNK_BYTES = 1_048_576


class EmbeddingBundleError(ValueError):
    """Sanitized invalid or incomplete embedding-bundle failure."""


class EmbeddingSourceFile(DomainModel):
    """One immutable upstream model file and exact destination."""

    repository_id: str = Field(min_length=3, max_length=256)
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_path: str = Field(min_length=1, max_length=512)
    destination_path: str = Field(min_length=1, max_length=512)
    byte_length: int = Field(strict=True, ge=1, le=512 * 1024 * 1024)
    sha256: Sha256Id
    license_id: str = Field(pattern=r"^MIT$")

    @model_validator(mode="after")
    def _paths_are_safe_relative_files(self) -> Self:
        for value in (self.source_path, self.destination_path):
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or "." in path.parts or not path.name:
                raise ValueError("embedding source paths must be normalized relative files")
        return self


class EmbeddingBundleSourceLock(DomainModel):
    """Committed independent trust root for one external model package."""

    schema_version: str = Field(pattern=r"^0\.1\.0$")
    bundle_name: str = Field(min_length=1, max_length=128)
    bundle_version: str = Field(min_length=1, max_length=64)
    model_id: str = Field(min_length=3, max_length=256)
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    license_id: str = Field(pattern=r"^MIT$")
    license_evidence_url: str = Field(pattern=r"^https://huggingface\.co/")
    dimensions: int = Field(strict=True, ge=1, le=65_536)
    max_tokens: int = Field(strict=True, ge=1, le=131_072)
    max_total_asset_bytes: int = Field(strict=True, ge=1, le=1024 * 1024 * 1024)
    files: tuple[EmbeddingSourceFile, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _file_inventory_is_canonical_and_bounded(self) -> Self:
        paths = tuple(item.destination_path for item in self.files)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("embedding source files must be sorted and unique")
        if any(
            item.repository_id != self.model_id
            or item.revision != self.model_revision
            or item.license_id != self.license_id
            for item in self.files
        ):
            raise ValueError("embedding file source facts must match bundle source")
        if sum(item.byte_length for item in self.files) > self.max_total_asset_bytes:
            raise ValueError("embedding source files exceed bundle byte limit")
        return self

    @property
    def source_lock_id(self) -> Sha256Id:
        """Return the exact canonical source-lock identity."""
        return canonical_sha256(self.model_dump(mode="json"))


class EmbeddingBundleFile(DomainModel):
    """One runtime file retained in the canonical bundle manifest."""

    path: str = Field(min_length=1, max_length=512)
    byte_length: int = Field(strict=True, ge=1)
    sha256: Sha256Id
    license_id: str = Field(pattern=r"^MIT$")


class EmbeddingBundleManifest(DomainModel):
    """Canonical runtime manifest derived only from the independent source lock."""

    schema_version: str = Field(pattern=r"^0\.1\.0$")
    bundle_name: str
    bundle_version: str
    model_id: str
    model_revision: str
    source_lock_id: Sha256Id
    dimensions: int = Field(strict=True, ge=1)
    max_tokens: int = Field(strict=True, ge=1)
    files: tuple[EmbeddingBundleFile, ...]

    @property
    def bundle_id(self) -> Sha256Id:
        """Return the model-specific canonical bundle identity."""
        return canonical_sha256(self.model_dump(mode="json"))


class EmbeddingBundleVerification(DomainModel):
    """Body-free exact offline installation evidence."""

    bundle_id: Sha256Id
    source_lock_id: Sha256Id
    asset_bytes: int = Field(strict=True, ge=1)
    asset_file_count: int = Field(strict=True, ge=1)
    model_id: str
    model_revision: str
    dimensions: int = Field(strict=True, ge=1)
    max_tokens: int = Field(strict=True, ge=1)


def load_embedding_source_lock(path: Path) -> EmbeddingBundleSourceLock:
    """Load a canonical committed source lock from one explicit regular file."""
    payload = _read_regular(path)
    try:
        lock = validate_json(EmbeddingBundleSourceLock, payload)
    except (ValueError, TypeError) as error:
        raise EmbeddingBundleError("embedding source lock invalid") from error
    if canonical_json_bytes(lock.model_dump(mode="json")) + b"\n" != payload:
        raise EmbeddingBundleError("embedding source lock is not canonical")
    return lock


def expected_embedding_manifest(lock: EmbeddingBundleSourceLock) -> EmbeddingBundleManifest:
    """Derive the only accepted runtime manifest from committed source facts."""
    return EmbeddingBundleManifest(
        schema_version="0.1.0",
        bundle_name=lock.bundle_name,
        bundle_version=lock.bundle_version,
        model_id=lock.model_id,
        model_revision=lock.model_revision,
        source_lock_id=lock.source_lock_id,
        dimensions=lock.dimensions,
        max_tokens=lock.max_tokens,
        files=tuple(
            EmbeddingBundleFile(
                path=item.destination_path,
                byte_length=item.byte_length,
                sha256=item.sha256,
                license_id=item.license_id,
            )
            for item in lock.files
        ),
    )


def verify_embedding_bundle(
    bundle: Path,
    *,
    expected_source_lock: Path,
) -> EmbeddingBundleVerification:
    """Verify one complete bundle independently without importing model libraries."""
    lock = load_embedding_source_lock(expected_source_lock)
    root = bundle.absolute()
    _require_directory(root)
    expected_root = {
        EMBEDDING_ASSET_DIRECTORY,
        EMBEDDING_BUNDLE_MANIFEST,
        EMBEDDING_BUNDLE_SOURCE_LOCK,
    }
    try:
        if {item.name for item in root.iterdir()} != expected_root:
            raise EmbeddingBundleError("embedding bundle root inventory differs")
    except OSError as error:
        raise EmbeddingBundleError("embedding bundle inventory failed") from error
    internal_lock = _read_regular(root / EMBEDDING_BUNDLE_SOURCE_LOCK)
    external_lock = _read_regular(expected_source_lock)
    if internal_lock != external_lock:
        raise EmbeddingBundleError("embedding bundle source lock differs")
    manifest_payload = _read_regular(root / EMBEDDING_BUNDLE_MANIFEST)
    try:
        manifest = validate_json(EmbeddingBundleManifest, manifest_payload)
    except (ValueError, TypeError) as error:
        raise EmbeddingBundleError("embedding bundle manifest invalid") from error
    if canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n" != manifest_payload:
        raise EmbeddingBundleError("embedding bundle manifest is not canonical")
    expected_manifest = expected_embedding_manifest(lock)
    if manifest != expected_manifest:
        raise EmbeddingBundleError("embedding bundle manifest differs from source lock")
    assets = root / EMBEDDING_ASSET_DIRECTORY
    _require_directory(assets)
    observed = tuple(
        path.relative_to(assets).as_posix()
        for path in sorted(assets.rglob("*"))
        if path.is_file() or path.is_symlink()
    )
    expected = tuple(item.destination_path for item in lock.files)
    if observed != expected:
        raise EmbeddingBundleError("embedding bundle asset inventory differs")
    for item in lock.files:
        _verify_file(assets / Path(*PurePosixPath(item.destination_path).parts), item)
    return EmbeddingBundleVerification(
        bundle_id=manifest.bundle_id,
        source_lock_id=lock.source_lock_id,
        asset_bytes=sum(item.byte_length for item in lock.files),
        asset_file_count=len(lock.files),
        model_id=lock.model_id,
        model_revision=lock.model_revision,
        dimensions=lock.dimensions,
        max_tokens=lock.max_tokens,
    )


def materialize_embedding_control_files(stage: Path, source_lock_path: Path) -> None:
    """Publish canonical manifest and exact external source lock into a staging root."""
    lock = load_embedding_source_lock(source_lock_path)
    manifest = expected_embedding_manifest(lock)
    (stage / EMBEDDING_BUNDLE_MANIFEST).write_bytes(
        canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n"
    )
    (stage / EMBEDDING_BUNDLE_SOURCE_LOCK).write_bytes(_read_regular(source_lock_path))


def _verify_file(path: Path, expected: EmbeddingSourceFile) -> None:
    payload_hash = hashlib.sha256()
    observed = 0
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise EmbeddingBundleError("embedding asset is not a private regular file")
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK_BYTES):
                observed += len(chunk)
                if observed > expected.byte_length:
                    raise EmbeddingBundleError("embedding asset exceeds expected bytes")
                payload_hash.update(chunk)
    except OSError as error:
        raise EmbeddingBundleError("embedding asset read failed") from error
    if observed != expected.byte_length or "sha256:" + payload_hash.hexdigest() != expected.sha256:
        raise EmbeddingBundleError("embedding asset integrity differs")


def _require_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise EmbeddingBundleError("embedding bundle directory missing") from error
    if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
        raise EmbeddingBundleError("embedding bundle directory invalid")


def _read_regular(path: Path) -> bytes:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise EmbeddingBundleError("embedding control file is not private regular data")
        with path.open("rb") as handle:
            return handle.read(4 * 1024 * 1024 + 1)
    except OSError as error:
        raise EmbeddingBundleError("embedding control file read failed") from error


__all__ = [
    "EMBEDDING_ASSET_DIRECTORY",
    "EMBEDDING_BUNDLE_MANIFEST",
    "EMBEDDING_BUNDLE_SOURCE_LOCK",
    "EmbeddingBundleError",
    "EmbeddingBundleManifest",
    "EmbeddingBundleSourceLock",
    "EmbeddingBundleVerification",
    "EmbeddingSourceFile",
    "expected_embedding_manifest",
    "load_embedding_source_lock",
    "materialize_embedding_control_files",
    "verify_embedding_bundle",
]
