"""Hostile archive, privacy and authority boundaries for F014."""

from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.domain.interchange import (
    AssetDisposition,
    AssetRole,
    InterchangePackage,
    PortableAsset,
    package_identity,
)
from openardp.ports.interchange import (
    InterchangeIntegrityInvalid,
    InterchangePolicyRejected,
    MalformedPackage,
)
from openardp.services.interchange import InterchangeService
from tests.integration.test_bagit_interchange import _export
from tests.interchange_factory import sha, synthetic_package

_FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _info(name: str, *, mode: int = stat.S_IFREG | 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = mode << 16
    return info


def _rewrite(
    source: Path,
    destination: Path,
    *,
    rename: dict[str, str] | None = None,
    replace: dict[str, bytes] | None = None,
    omit: set[str] | None = None,
    duplicate: str | None = None,
    archive_comment: bytes = b"",
    mode_override: dict[str, int] | None = None,
) -> None:
    rename = rename or {}
    replace = replace or {}
    omit = omit or set()
    mode_override = mode_override or {}
    with zipfile.ZipFile(source) as current:
        entries = [
            (rename.get(name, name), replace.get(name, current.read(name)), name)
            for name in current.namelist()
            if name not in omit
        ]
    if duplicate is not None:
        original = next(item for item in entries if item[2] == duplicate)
        entries.append(original)
    entries.sort(key=lambda item: item[0])
    with zipfile.ZipFile(destination, "w") as target:
        target.comment = archive_comment
        for name, data, original in entries:
            mode = mode_override.get(original, stat.S_IFREG | 0o644)
            target.writestr(_info(name, mode=mode), data)


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "C:/drive", "data\\evil"])
def test_unsafe_paths_are_rejected_before_publication(tmp_path: Path, unsafe: str) -> None:
    """Reject traversal, absolute, drive and backslash archive paths."""
    package, _ = _export(tmp_path)
    hostile = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(package) as archive:
        payload = next(name for name in archive.namelist() if name.startswith("data/"))
    _rewrite(package, hostile, rename={payload: unsafe})
    with pytest.raises(InterchangePolicyRejected):
        InterchangeService().verify(hostile)


def test_duplicate_member_is_malformed(tmp_path: Path) -> None:
    """Reject duplicate central-directory names even when bytes agree."""
    package, _ = _export(tmp_path)
    hostile = tmp_path / "duplicate.zip"
    with pytest.warns(UserWarning):
        _rewrite(package, hostile, duplicate="bagit.txt")
    with pytest.raises(MalformedPackage):
        InterchangeService().verify(hostile)


def test_archive_comment_and_link_mode_are_policy_rejected(tmp_path: Path) -> None:
    """Reject non-canonical comments and link-like external attributes."""
    package, _ = _export(tmp_path)
    commented = tmp_path / "commented.zip"
    linked = tmp_path / "linked.zip"
    _rewrite(package, commented, archive_comment=b"hidden metadata")
    _rewrite(package, linked, mode_override={"bagit.txt": stat.S_IFLNK | 0o777})
    with pytest.raises(InterchangePolicyRejected):
        InterchangeService().verify(commented)
    with pytest.raises(InterchangePolicyRejected):
        InterchangeService().verify(linked)


def test_payload_digest_conflict_is_integrity_invalid(tmp_path: Path) -> None:
    """Reject payload bytes that disagree with both semantic and BagIt inventory."""
    package, _ = _export(tmp_path)
    hostile = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(package) as archive:
        payload = next(name for name in archive.namelist() if name.startswith("data/"))
    _rewrite(package, hostile, replace={payload: b"different exact bytes"})
    with pytest.raises(InterchangeIntegrityInvalid):
        InterchangeService().verify(hostile)


def test_missing_required_tag_is_malformed(tmp_path: Path) -> None:
    """Reject a bag whose required declaration is absent."""
    package, _ = _export(tmp_path)
    hostile = tmp_path / "missing.zip"
    _rewrite(package, hostile, omit={"bagit.txt"})
    with pytest.raises(MalformedPackage):
        InterchangeService().verify(hostile)


@pytest.mark.parametrize(
    "facts",
    [
        {"local_path": "/Users/example/private.txt"},
        {"token": "top-secret"},
        {"nested": {"filename": "private.txt"}},
        {"value": "https://user:password@example.invalid/data"},
    ],
)
def test_portable_record_rejects_local_or_secret_shaped_facts(facts: dict[str, object]) -> None:
    """Prevent local paths, credentials and body-like fields entering metadata."""
    value = synthetic_package().model_dump(mode="json")
    value["records"][0]["facts"] = facts
    value["package_id"] = package_identity(value)
    with pytest.raises(ValidationError):
        InterchangePackage.model_validate_json(json.dumps(value))


def test_extension_names_are_explicitly_namespaced() -> None:
    """Reject ambiguous extension keys outside the closed core."""
    value = synthetic_package().model_dump(mode="json")
    value["extension_policy"] = "preserve"
    value["extensions"] = {"quality": 1}
    value["package_id"] = package_identity(value)
    with pytest.raises(ValidationError, match="namespaced"):
        InterchangePackage.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("reference", ["private-native.bin", "file:///private/native.bin"])
def test_referenced_assets_reject_local_filename_authority(reference: str) -> None:
    """Require a non-file absolute URI so local filenames cannot leak as references."""
    with pytest.raises(ValidationError, match="non-file absolute URI"):
        PortableAsset(
            object_id=sha(b"reference"),
            byte_length=9,
            media_type="application/octet-stream",
            role=AssetRole.PROVIDER_NATIVE,
            disposition=AssetDisposition.REFERENCED,
            reference=reference,
        )
