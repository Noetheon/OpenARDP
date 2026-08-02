"""Hostile path, tree and archive tests for F023."""

from __future__ import annotations

import unicodedata
from copy import copy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipInfo

import pytest
from pydantic import ValidationError

from openardp.adapters.docling_bundle import (
    BundleValidationError,
    PdfModelSourceFile,
    load_source_lock,
    safe_relative_path,
    verify_installation,
)
from openardp.adapters.docling_bundle_archive import _validate_member
from tests.fixtures.pdf_bundle import write_installation, write_source_material


@pytest.mark.parametrize(
    "path",
    ("/absolute", "../escape", "a/../b", "a\\b", "./a", "a//b", "a/\x00b", "a/"),
)
def test_source_and_destination_paths_are_closed_posix_paths(path: str) -> None:
    """Reject paths that can escape or acquire platform-dependent meaning."""
    with pytest.raises((ValueError, ValidationError)):
        safe_relative_path(path)


def test_normalization_and_case_collisions_are_detectable() -> None:
    """Do not let two manifest entries alias on common filesystems."""
    composed = "models/é.bin"
    decomposed = unicodedata.normalize("NFD", composed)
    assert safe_relative_path(composed) != safe_relative_path(decomposed)
    with pytest.raises(ValueError):
        PdfModelSourceFile.validate_destination_set((composed, decomposed))
    with pytest.raises(ValueError):
        PdfModelSourceFile.validate_destination_set(("Models/A.bin", "models/a.bin"))


def _valid_zip_info() -> ZipInfo:
    info = ZipInfo("openardp-pdf-bundle/manifest.json", (1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_STORED
    info.external_attr = 0o100644 << 16
    info.file_size = 1
    info.compress_size = 1
    return info


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("compress_type", ZIP_DEFLATED),
        ("date_time", (2026, 1, 1, 0, 0, 0)),
        ("comment", b"comment"),
        ("extra", b"\x01\x00\x00\x00"),
        ("external_attr", 0o120777 << 16),
        ("file_size", 0),
        ("compress_size", 2),
        ("filename", "wrong-prefix/manifest.json"),
    ),
)
def test_archive_member_profile_rejects_every_unreviewed_property(
    field: str,
    value: object,
) -> None:
    """Enforce type, metadata, compression, size and namespace before extraction."""
    info = copy(_valid_zip_info())
    setattr(info, field, value)
    with pytest.raises(BundleValidationError):
        _validate_member(info)


def test_source_lock_loader_rejects_noncanonical_link_and_oversized_controls(
    tmp_path: Path,
) -> None:
    """Treat even local control material as bounded untrusted input."""
    lock = write_source_material(tmp_path / "source")
    canonical = lock.read_bytes()
    lock.write_bytes(b" " + canonical)
    with pytest.raises(BundleValidationError):
        load_source_lock(lock)

    lock.write_bytes(canonical)
    linked = tmp_path / "linked.json"
    linked.symlink_to(lock)
    with pytest.raises(BundleValidationError):
        load_source_lock(linked)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * 1_048_577)
    with pytest.raises(BundleValidationError):
        load_source_lock(oversized)


@pytest.mark.parametrize("mutation", ("notice", "internal_lock", "empty_directory"))
def test_installation_rejects_control_drift_and_extra_directories(
    tmp_path: Path,
    mutation: str,
) -> None:
    """Close both file and directory inventories around reviewed assets and controls."""
    root, lock = write_installation(tmp_path / "bundle")
    if mutation == "notice":
        (root / "THIRD_PARTY_NOTICES.md").write_bytes(b"tampered")
    elif mutation == "internal_lock":
        (root / "source-lock.json").write_bytes(b"{}\n")
    else:
        (root / "unexpected-empty-directory").mkdir()
    with pytest.raises(BundleValidationError):
        verify_installation(root, expected_source_lock=lock)
