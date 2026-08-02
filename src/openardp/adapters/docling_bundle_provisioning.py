"""Explicit connected provisioning for one immutable Docling PDF bundle."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import Field

from openardp.adapters.docling_bundle import (
    ASSET_DIRECTORY,
    BundleValidationError,
    BundleVerificationResult,
    PdfModelSourceFile,
    load_source_lock,
    materialize_control_files,
    verify_installation,
)


class BundleProvisioningResult(BundleVerificationResult):
    """Exact installation result plus connected transfer measurement."""

    provision_duration_ns: int = Field(strict=True, gt=0)
    downloaded_bytes: int = Field(strict=True, ge=0)
    downloaded_file_count: int = Field(strict=True, ge=0)


FetchFile = Callable[[str, str, str, Path], None]
_CHUNK_BYTES = 1_048_576


class ProvisioningError(RuntimeError):
    """Report a sanitized connected-provisioning failure."""

    def __init__(self) -> None:
        """Initialize the stable public failure message."""
        super().__init__("PDF model bundle provisioning failed")


def _copy_stream(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        while chunk := reader.read(_CHUNK_BYTES):
            writer.write(chunk)


def _huggingface_fetcher(cache_root: Path) -> FetchFile:
    def fetch(repository_id: str, revision: str, source_path: str, destination: Path) -> None:
        try:
            from huggingface_hub import hf_hub_download

            downloaded = Path(
                hf_hub_download(
                    repo_id=repository_id,
                    revision=revision,
                    filename=source_path,
                    cache_dir=cache_root,
                )
            )
            _copy_stream(downloaded, destination)
        except Exception:
            raise ProvisioningError from None

    return fetch


def _verify_download(path: Path, item: PdfModelSourceFile) -> None:
    digest = hashlib.sha256()
    observed = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK_BYTES):
                observed += len(chunk)
                if observed > item.byte_length:
                    raise ProvisioningError
                digest.update(chunk)
    except (OSError, ProvisioningError):
        raise ProvisioningError from None
    if observed != item.byte_length or "sha256:" + digest.hexdigest() != item.sha256:
        raise ProvisioningError


def _sync_regular_files(root: Path) -> None:
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        with path.open("rb") as handle:
            os.fsync(handle.fileno())
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def provision_bundle(
    source_lock_path: Path,
    destination: Path,
    *,
    fetch_file: FetchFile | None = None,
) -> BundleProvisioningResult:
    """Provision and atomically publish one complete bundle into an absent destination."""
    started = time.monotonic_ns()
    try:
        lock = load_source_lock(source_lock_path)
        destination = destination.absolute()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            raise ProvisioningError
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.staging-",
                dir=destination.parent,
            )
        )
    except (OSError, BundleValidationError, ProvisioningError):
        raise ProvisioningError from None

    try:
        cache_root = staging / ".downloads"
        selected_fetch = fetch_file or _huggingface_fetcher(cache_root)
        for item in lock.files:
            target = staging / ASSET_DIRECTORY / Path(*item.destination_path.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            selected_fetch(item.repository_id, item.revision, item.source_path, target)
            _verify_download(target, item)
        if cache_root.exists():
            shutil.rmtree(cache_root)
        materialize_control_files(staging, lock_path=source_lock_path)
        result = verify_installation(staging, expected_source_lock=source_lock_path)
        _sync_regular_files(staging)
        if destination.exists() or destination.is_symlink():
            raise ProvisioningError
        os.rename(staging, destination)
        return BundleProvisioningResult(
            **result.model_dump(),
            provision_duration_ns=time.monotonic_ns() - started,
            downloaded_bytes=result.asset_bytes,
            downloaded_file_count=result.asset_file_count,
        )
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise ProvisioningError from None


__all__ = [
    "BundleProvisioningResult",
    "FetchFile",
    "ProvisioningError",
    "provision_bundle",
]
