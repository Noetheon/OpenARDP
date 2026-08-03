"""Explicit connected provisioning for one immutable embedding model bundle."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from openardp.adapters.embedding_bundle import (
    EMBEDDING_ASSET_DIRECTORY,
    EmbeddingBundleError,
    EmbeddingBundleVerification,
    EmbeddingSourceFile,
    load_embedding_source_lock,
    materialize_embedding_control_files,
    verify_embedding_bundle,
)

FetchEmbeddingFile = Callable[[str, str, str, Path], None]
_CHUNK_BYTES = 1_048_576


class EmbeddingProvisioningError(RuntimeError):
    """Sanitized connected-provisioning failure."""


def _hub_fetcher(cache_root: Path) -> FetchEmbeddingFile:
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
            destination.parent.mkdir(parents=True, exist_ok=True)
            with downloaded.open("rb") as source, destination.open("xb") as target:
                while chunk := source.read(_CHUNK_BYTES):
                    target.write(chunk)
        except Exception:
            raise EmbeddingProvisioningError("embedding bundle provisioning failed") from None

    return fetch


def provision_embedding_bundle(
    source_lock: Path,
    destination: Path,
    *,
    fetch_file: FetchEmbeddingFile | None = None,
) -> EmbeddingBundleVerification:
    """Download, verify and atomically publish one absent exact model bundle."""
    try:
        lock = load_embedding_source_lock(source_lock)
        destination = destination.absolute()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            raise EmbeddingProvisioningError("embedding bundle destination exists")
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.staging-",
                dir=destination.parent,
            )
        )
    except (OSError, EmbeddingBundleError, EmbeddingProvisioningError):
        raise EmbeddingProvisioningError("embedding bundle provisioning failed") from None
    try:
        cache = stage / ".downloads"
        fetch = fetch_file or _hub_fetcher(cache)
        for item in lock.files:
            target = stage / EMBEDDING_ASSET_DIRECTORY / item.destination_path
            target.parent.mkdir(parents=True, exist_ok=True)
            fetch(item.repository_id, item.revision, item.source_path, target)
            _verify_download(target, item)
        if cache.exists():
            shutil.rmtree(cache)
        materialize_embedding_control_files(stage, source_lock)
        result = verify_embedding_bundle(stage, expected_source_lock=source_lock)
        if destination.exists() or destination.is_symlink():
            raise EmbeddingProvisioningError("embedding bundle destination exists")
        os.rename(stage, destination)
        return result
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise EmbeddingProvisioningError("embedding bundle provisioning failed") from None


def _verify_download(path: Path, expected: EmbeddingSourceFile) -> None:
    digest = hashlib.sha256()
    observed = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK_BYTES):
                observed += len(chunk)
                if observed > expected.byte_length:
                    raise EmbeddingProvisioningError
                digest.update(chunk)
    except (OSError, EmbeddingProvisioningError):
        raise EmbeddingProvisioningError("embedding bundle provisioning failed") from None
    if observed != expected.byte_length or "sha256:" + digest.hexdigest() != expected.sha256:
        raise EmbeddingProvisioningError("embedding bundle provisioning failed")


__all__ = [
    "EmbeddingProvisioningError",
    "FetchEmbeddingFile",
    "provision_embedding_bundle",
]
