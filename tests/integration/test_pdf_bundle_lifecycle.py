"""Integration tests for deterministic F023 package transfer."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest

from openardp.adapters.docling_bundle import BundleValidationError, verify_installation
from openardp.adapters.docling_bundle_archive import create_bundle_package, install_bundle_package
from tests.fixtures.pdf_bundle import write_installation


def test_ordinary_rich_adapter_import_never_imports_connected_provisioning() -> None:
    """Keep the connected downloader outside ordinary import and parser authority."""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import openardp.adapters.isolated_docling; "
            "assert 'openardp.adapters.docling_bundle_provisioning' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_package_is_byte_deterministic_and_installs_exactly(tmp_path: Path) -> None:
    """Reproduce exact package bytes and safely publish a fresh verified installation."""
    root, lock_path = write_installation(tmp_path / "bundle")
    first = create_bundle_package(root, tmp_path / "first.zip", expected_source_lock=lock_path)
    second = create_bundle_package(root, tmp_path / "second.zip", expected_source_lock=lock_path)

    assert first.package_id == second.package_id
    assert (tmp_path / "first.zip").read_bytes() == (tmp_path / "second.zip").read_bytes()
    installed = install_bundle_package(
        tmp_path / "first.zip",
        tmp_path / "offline",
        expected_source_lock=lock_path,
    )
    assert installed.bundle_id == first.bundle_id
    verify_installation(tmp_path / "offline", expected_source_lock=lock_path)


def test_package_install_rejects_traversal_and_trailing_data(tmp_path: Path) -> None:
    """Reject hostile members and bytes outside the deterministic archive envelope."""
    source = tmp_path / "hostile.zip"
    with ZipFile(source, "w", compression=ZIP_STORED) as archive:
        info = ZipInfo("openardp-pdf-bundle/../escape")
        info.external_attr = 0o100644 << 16
        archive.writestr(info, b"escape")
    with pytest.raises(BundleValidationError):
        install_bundle_package(source, tmp_path / "target", expected_source_lock=tmp_path / "x")
    assert not (tmp_path / "target").exists()

    root, lock_path = write_installation(tmp_path / "bundle")
    create_bundle_package(root, tmp_path / "valid.zip", expected_source_lock=lock_path)
    (tmp_path / "valid.zip").write_bytes((tmp_path / "valid.zip").read_bytes() + b"trailing")
    with pytest.raises(BundleValidationError):
        install_bundle_package(
            tmp_path / "valid.zip",
            tmp_path / "target-two",
            expected_source_lock=lock_path,
        )
    assert hashlib.sha256(b"trailing").hexdigest() not in str(tmp_path)
