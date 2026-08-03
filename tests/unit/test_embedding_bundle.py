"""Exact offline embedding-bundle verification and provisioning tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from openardp.adapters.embedding_bundle import (
    EmbeddingBundleError,
    verify_embedding_bundle,
)
from openardp.adapters.embedding_bundle_provisioning import (
    EmbeddingProvisioningError,
    provision_embedding_bundle,
)
from openardp.domain.identity import canonical_json_bytes


def _lock(tmp_path: Path, payload: bytes = b"safe-model") -> Path:
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    value = {
        "bundle_name": "fixture-embedding",
        "bundle_version": "1.0.0-v1",
        "dimensions": 3,
        "files": [
            {
                "byte_length": len(payload),
                "destination_path": "model.safetensors",
                "license_id": "MIT",
                "repository_id": "fixture/model",
                "revision": "a" * 40,
                "sha256": digest,
                "source_path": "model.safetensors",
            }
        ],
        "license_evidence_url": "https://huggingface.co/fixture/model",
        "license_id": "MIT",
        "max_tokens": 16,
        "max_total_asset_bytes": 1024,
        "model_id": "fixture/model",
        "model_revision": "a" * 40,
        "schema_version": "0.1.0",
    }
    path = tmp_path / "source-lock.json"
    path.write_bytes(canonical_json_bytes(value) + b"\n")
    return path


def test_provision_and_verify_exact_embedding_bundle(tmp_path: Path) -> None:
    """Publish one absent bundle atomically and verify it without provider imports."""
    payload = b"safe-model"
    lock = _lock(tmp_path, payload)

    def fetch(_repository: str, _revision: str, _source: str, destination: Path) -> None:
        destination.write_bytes(payload)

    destination = tmp_path / "bundle"
    result = provision_embedding_bundle(lock, destination, fetch_file=fetch)
    verified = verify_embedding_bundle(destination, expected_source_lock=lock)
    assert verified == result
    assert verified.asset_file_count == 1
    assert verified.asset_bytes == len(payload)


def test_embedding_bundle_rejects_corruption_extra_files_and_links(tmp_path: Path) -> None:
    """Fail closed on every physical inventory/integrity deviation."""
    lock = _lock(tmp_path)

    def fetch(_repository: str, _revision: str, _source: str, destination: Path) -> None:
        destination.write_bytes(b"safe-model")

    for mode in ("corrupt", "extra", "link"):
        destination = tmp_path / mode
        provision_embedding_bundle(lock, destination, fetch_file=fetch)
        asset = destination / "assets/model.safetensors"
        if mode == "corrupt":
            asset.write_bytes(b"evil-model")
        elif mode == "extra":
            (destination / "assets/extra.bin").write_bytes(b"extra")
        else:
            target = tmp_path / "outside.bin"
            target.write_bytes(b"safe-model")
            asset.unlink()
            asset.symlink_to(target)
        with pytest.raises(EmbeddingBundleError):
            verify_embedding_bundle(destination, expected_source_lock=lock)


def test_embedding_provisioning_rejects_changed_download_and_existing_destination(
    tmp_path: Path,
) -> None:
    """Never publish mismatched bytes or overwrite an existing destination."""
    lock = _lock(tmp_path)

    def changed(_repository: str, _revision: str, _source: str, destination: Path) -> None:
        destination.write_bytes(b"changed")

    with pytest.raises(EmbeddingProvisioningError):
        provision_embedding_bundle(lock, tmp_path / "bad", fetch_file=changed)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(EmbeddingProvisioningError):
        provision_embedding_bundle(lock, existing, fetch_file=changed)
