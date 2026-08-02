"""Contract tests for the F023 source lock and installed bundle."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.adapters.docling_bundle import (
    PdfModelSourceLock,
    build_model_manifest,
    load_source_lock,
    verify_installation,
)
from openardp.domain.identity import canonical_json_bytes
from tests.fixtures.pdf_bundle import (
    MODEL_PAYLOADS,
    source_lock_dict,
    write_installation,
    write_source_material,
)

ROOT = Path(__file__).parents[2]


def test_source_lock_round_trips_canonically_and_builds_existing_manifest(tmp_path: Path) -> None:
    """Keep one path-independent identity and exact F007 model manifest projection."""
    lock_path = write_source_material(tmp_path / "source")
    lock = load_source_lock(lock_path)
    reconstructed = PdfModelSourceLock.model_validate_json(lock.model_dump_json())

    assert reconstructed == lock
    assert reconstructed.lock_id == lock.lock_id
    manifest = build_model_manifest(lock)
    assert manifest.bundle_name == "synthetic-docling-pdf"
    assert manifest.bundle_id.startswith("sha256:")
    assert tuple(item.path for item in manifest.files) == tuple(
        sorted(item.path for item in manifest.files)
    )


@pytest.mark.parametrize(
    "mutation",
    ("mutable_revision", "duplicate_destination", "license_conflict", "unsorted_files"),
)
def test_source_lock_rejects_ambiguous_or_mutable_authority(mutation: str) -> None:
    """Reject source facts that cannot define one immutable closed bundle."""
    value = source_lock_dict()
    sources = value["sources"]
    files = value["files"]
    assert isinstance(sources, list) and isinstance(files, list)
    if mutation == "mutable_revision":
        sources[0]["revision"] = "main"
    elif mutation == "duplicate_destination":
        files[1]["destination_path"] = files[0]["destination_path"]
    elif mutation == "license_conflict":
        files[0]["license_id"] = "MIT"
    else:
        value["files"] = list(reversed(files))
    with pytest.raises(ValidationError):
        PdfModelSourceLock.model_validate(value)


def test_installation_verification_reconciles_control_and_asset_trees(tmp_path: Path) -> None:
    """Verify one complete installation against an independently supplied source lock."""
    root, lock_path = write_installation(tmp_path / "bundle")
    result = verify_installation(root, expected_source_lock=lock_path)

    assert result.asset_file_count == 2
    assert result.asset_bytes == sum(len(payload) for payload in MODEL_PAYLOADS.values())
    assert result.bundle_id.startswith("sha256:")


def test_committed_real_lock_and_manifest_are_exact_reviewed_projections() -> None:
    """Freeze the five real runtime files, source/license assertions and bundle identity."""
    bundle_root = ROOT / "model-bundles/pdf-docling-2.114.0-v1"
    lock = load_source_lock(bundle_root / "source-lock.json")
    manifest = build_model_manifest(lock)

    assert lock.lock_id == "sha256:232a68ac675fc8c6801b652a20e2f6adffc311aa7847e7dfb6d0759efb2bc5cb"
    assert (
        manifest.bundle_id
        == "sha256:442ab96f3d56146c63e6e98dfb7452a679571b4343e9b01e2bdb02b3eb0c74b8"
    )
    assert len(lock.files) == 5
    assert sum(item.byte_length for item in lock.files) == 384_428_156
    assert {source.license_id for source in lock.sources} == {
        "Apache-2.0",
        "CDLA-Permissive-2.0",
    }
    assert (bundle_root / "manifest.json").read_bytes() == (
        canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n"
    )
