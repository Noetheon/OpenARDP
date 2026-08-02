"""Unit tests for F023 exact bundle verification and provisioning."""

from __future__ import annotations

from pathlib import Path

import pytest

from openardp.adapters.docling_bundle import BundleValidationError, verify_installation
from openardp.adapters.docling_bundle_provisioning import (
    ProvisioningError,
    _sync_regular_files,
    provision_bundle,
)
from tests.fixtures.pdf_bundle import MODEL_PAYLOADS, write_installation, write_source_material


def test_closed_tree_rejects_extra_missing_tampered_and_linked_files(tmp_path: Path) -> None:
    """Treat the manifest as a closed allowlist rather than a partial integrity list."""
    root, lock_path = write_installation(tmp_path / "bundle")
    extra = root / "assets" / "extra.bin"
    extra.write_bytes(b"extra")
    with pytest.raises(BundleValidationError):
        verify_installation(root, expected_source_lock=lock_path)
    extra.unlink()

    target = root / "assets" / next(iter(MODEL_PAYLOADS))
    original = target.read_bytes()
    target.write_bytes(original + b"x")
    with pytest.raises(BundleValidationError):
        verify_installation(root, expected_source_lock=lock_path)
    target.unlink()
    target.symlink_to(root / "manifest.json")
    with pytest.raises(BundleValidationError):
        verify_installation(root, expected_source_lock=lock_path)


def test_provisioner_publishes_only_complete_exact_destination(tmp_path: Path) -> None:
    """Stream exact locked bytes through staging and atomically publish once."""
    source_lock = write_source_material(tmp_path / "source")

    def fetch(repository_id: str, revision: str, source_path: str, destination: Path) -> None:
        del repository_id, revision
        by_source = {
            "config.json": MODEL_PAYLOADS["docling-project--docling-layout-heron/config.json"],
            "model_artifacts/tableformer/accurate/tm_config.json": MODEL_PAYLOADS[
                "docling-project--docling-models/model_artifacts/tableformer/accurate/tm_config.json"
            ],
        }
        destination.write_bytes(by_source[source_path])

    result = provision_bundle(source_lock, tmp_path / "installed", fetch_file=fetch)
    assert result.asset_file_count == 2
    assert result.downloaded_file_count == 2
    assert result.downloaded_bytes == result.asset_bytes
    assert result.provision_duration_ns > 0
    verify_installation(tmp_path / "installed", expected_source_lock=source_lock)

    with pytest.raises(ProvisioningError):
        provision_bundle(source_lock, tmp_path / "installed", fetch_file=fetch)


def test_provisioner_does_not_publish_failed_staging(tmp_path: Path) -> None:
    """Keep a failed retrieval outside the accepted destination boundary."""
    source_lock = write_source_material(tmp_path / "source")

    def corrupt(_repository: str, _revision: str, _source: str, destination: Path) -> None:
        destination.write_bytes(b"wrong")

    destination = tmp_path / "installed"
    with pytest.raises(ProvisioningError):
        provision_bundle(source_lock, destination, fetch_file=corrupt)
    assert not destination.exists()


def test_windows_file_sync_uses_supported_file_descriptors_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flush write-capable files on Windows without a POSIX directory descriptor."""
    (tmp_path / "control.json").write_bytes(b"{}\n")
    monkeypatch.setattr("openardp.adapters.docling_bundle_provisioning.sys.platform", "win32")
    monkeypatch.setattr(
        "openardp.adapters.docling_bundle_provisioning.os.open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("directory opened")),
    )

    _sync_regular_files(tmp_path)
