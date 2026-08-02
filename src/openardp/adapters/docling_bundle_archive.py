"""Deterministic ZIP transfer and bounded installation for PDF model bundles."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath
from zipfile import ZIP_STORED, BadZipFile, ZipFile, ZipInfo

from pydantic import Field

from openardp.adapters.docling_bundle import (
    ASSET_DIRECTORY,
    MANIFEST_FILENAME,
    PROVENANCE_FILENAME,
    SOURCE_LOCK_FILENAME,
    BundleValidationError,
    PdfModelSourceLock,
    load_source_lock,
    safe_relative_path,
    verify_installation,
)
from openardp.domain.common import DomainModel, Sha256Id

PACKAGE_PREFIX = "openardp-pdf-bundle"
MAX_PACKAGE_ENTRIES = 128
MAX_PACKAGE_BYTES = 500 * 1024 * 1024
MAX_PACKAGE_OVERHEAD_BYTES = 1024 * 1024
_CHUNK_BYTES = 1024 * 1024
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)
_REGULAR_MODE = stat.S_IFREG | 0o644


class BundlePackageResult(DomainModel):
    """Body-free identity and size result for one deterministic package."""

    source_lock_id: Sha256Id
    bundle_id: Sha256Id
    package_id: Sha256Id
    package_bytes: int = Field(strict=True, gt=0)
    installation_bytes: int = Field(strict=True, gt=0)
    entry_count: int = Field(strict=True, gt=0)


def _expected_paths(lock: PdfModelSourceLock) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                SOURCE_LOCK_FILENAME,
                MANIFEST_FILENAME,
                PROVENANCE_FILENAME,
                *(item.path for item in lock.review_files),
                *(f"{ASSET_DIRECTORY}/{item.destination_path}" for item in lock.files),
            }
        )
    )


def _package_member(path: str) -> str:
    return f"{PACKAGE_PREFIX}/{path}"


def _zip_info(name: str, *, size: int) -> ZipInfo:
    info = ZipInfo(filename=name, date_time=_FIXED_TIME)
    info.compress_type = ZIP_STORED
    info.create_system = 3
    info.external_attr = _REGULAR_MODE << 16
    info.flag_bits = 0x800
    info.file_size = size
    return info


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return "sha256:" + digest.hexdigest(), size


def _publish_absent_file(staging: Path, destination: Path) -> None:
    try:
        if sys.platform == "win32":
            os.rename(staging, destination)
        else:
            os.link(staging, destination)
            staging.unlink()
    except OSError:
        raise BundleValidationError from None


def create_bundle_package(
    install_root: Path,
    output_path: Path,
    *,
    expected_source_lock: Path,
) -> BundlePackageResult:
    """Create one byte-deterministic uncompressed ZIP from a verified installation."""
    verification = verify_installation(
        install_root,
        expected_source_lock=expected_source_lock,
    )
    lock = load_source_lock(expected_source_lock)
    paths = _expected_paths(lock)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() or output_path.is_symlink():
        raise BundleValidationError
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.staging-",
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with ZipFile(temporary, "w", compression=ZIP_STORED, allowZip64=False) as archive:
            archive.comment = b""
            for relative in paths:
                source = install_root.joinpath(*relative.split("/"))
                size = source.stat(follow_symlinks=False).st_size
                info = _zip_info(_package_member(relative), size=size)
                with source.open("rb") as reader, archive.open(info, "w") as writer:
                    while chunk := reader.read(_CHUNK_BYTES):
                        writer.write(chunk)
        # Windows requires a write-capable descriptor for fsync; the file is
        # already closed by ZipFile and is not modified through this handle.
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        package_id, package_bytes = _hash_file(temporary)
        if package_bytes > verification.installation_bytes + MAX_PACKAGE_OVERHEAD_BYTES:
            raise BundleValidationError
        _publish_absent_file(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise BundleValidationError from None
    return BundlePackageResult(
        source_lock_id=verification.source_lock_id,
        bundle_id=verification.bundle_id,
        package_id=package_id,
        package_bytes=package_bytes,
        installation_bytes=verification.installation_bytes,
        entry_count=len(paths),
    )


def _reject_trailing_bytes(path: Path) -> None:
    size = path.stat(follow_symlinks=False).st_size
    if size < 22:
        raise BundleValidationError
    with path.open("rb") as handle:
        handle.seek(-22, os.SEEK_END)
        tail = handle.read(22)
    if tail[:4] != b"PK\x05\x06" or tail[-2:] != b"\x00\x00":
        raise BundleValidationError


def _validate_member(info: ZipInfo) -> str:
    if (
        info.is_dir()
        or info.compress_type != ZIP_STORED
        or info.date_time != _FIXED_TIME
        or info.comment
        or info.extra
        or info.file_size <= 0
        or info.file_size > MAX_PACKAGE_BYTES
        or info.compress_size != info.file_size
    ):
        raise BundleValidationError
    mode = info.external_attr >> 16
    if stat.S_IFMT(mode) != stat.S_IFREG or stat.S_IMODE(mode) != 0o644:
        raise BundleValidationError
    prefix = f"{PACKAGE_PREFIX}/"
    if not info.filename.startswith(prefix):
        raise BundleValidationError
    relative = info.filename[len(prefix) :]
    safe_relative_path(relative)
    return relative


def _preflight_archive(
    archive: ZipFile,
    *,
    expected_paths: tuple[str, ...],
) -> tuple[tuple[ZipInfo, str], ...]:
    infos = archive.infolist()
    if not infos or len(infos) > MAX_PACKAGE_ENTRIES:
        raise BundleValidationError
    members = tuple((info, _validate_member(info)) for info in infos)
    paths = tuple(relative for _info, relative in members)
    if paths != expected_paths:
        raise BundleValidationError
    keys = tuple(unicodedata.normalize("NFC", path).casefold() for path in paths)
    if len(paths) != len(set(paths)) or len(keys) != len(set(keys)):
        raise BundleValidationError
    if sum(info.file_size for info, _relative in members) > MAX_PACKAGE_BYTES:
        raise BundleValidationError
    return members


def _extract_regular(archive: ZipFile, info: ZipInfo, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    observed = 0
    try:
        with archive.open(info, "r") as reader, target.open("xb") as writer:
            while chunk := reader.read(_CHUNK_BYTES):
                observed += len(chunk)
                if observed > info.file_size:
                    raise BundleValidationError
                writer.write(chunk)
    except (OSError, BadZipFile, BundleValidationError):
        raise BundleValidationError from None
    if observed != info.file_size:
        raise BundleValidationError


def install_bundle_package(
    package_path: Path,
    destination: Path,
    *,
    expected_source_lock: Path,
) -> BundlePackageResult:
    """Safely extract, fully verify and atomically publish one package."""
    lock = load_source_lock(expected_source_lock)
    expected_paths = _expected_paths(lock)
    if destination.exists() or destination.is_symlink():
        raise BundleValidationError
    try:
        package_metadata = package_path.lstat()
        if package_path.is_symlink() or not stat.S_ISREG(package_metadata.st_mode):
            raise BundleValidationError
        if package_metadata.st_size > MAX_PACKAGE_BYTES + MAX_PACKAGE_OVERHEAD_BYTES:
            raise BundleValidationError
        _reject_trailing_bytes(package_path)
        package_id, package_bytes = _hash_file(package_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.staging-",
                dir=destination.parent,
            )
        )
        with ZipFile(package_path, "r") as archive:
            members = _preflight_archive(archive, expected_paths=expected_paths)
            for info, relative in members:
                target = staging.joinpath(*PurePosixPath(relative).parts)
                _extract_regular(archive, info, target)
        verification = verify_installation(
            staging,
            expected_source_lock=expected_source_lock,
        )
        if package_bytes > verification.installation_bytes + MAX_PACKAGE_OVERHEAD_BYTES:
            raise BundleValidationError
        if destination.exists() or destination.is_symlink():
            raise BundleValidationError
        os.rename(staging, destination)
    except Exception:
        if "staging" in locals() and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise BundleValidationError from None
    return BundlePackageResult(
        source_lock_id=verification.source_lock_id,
        bundle_id=verification.bundle_id,
        package_id=package_id,
        package_bytes=package_bytes,
        installation_bytes=verification.installation_bytes,
        entry_count=len(expected_paths),
    )


__all__ = [
    "MAX_PACKAGE_BYTES",
    "MAX_PACKAGE_ENTRIES",
    "MAX_PACKAGE_OVERHEAD_BYTES",
    "PACKAGE_PREFIX",
    "BundlePackageResult",
    "create_bundle_package",
    "install_bundle_package",
]
