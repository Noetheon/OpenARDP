"""Generate or drift-check deterministic synthetic F014 package vectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import tempfile
import warnings
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

from openardp.adapters.bagit_interchange import BagItPackageAdapter
from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    TrustZone,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.interchange import (
    AssetDisposition,
    AssetRole,
    ExtensionPolicy,
    InterchangeLimits,
    InterchangePackage,
    PortableAsset,
    PortableRecord,
    PortableRecordType,
    PortableRelationship,
    RelationshipPredicate,
    package_identity,
    payload_path,
)
from openardp.services.interchange import InterchangeService

ROOT = Path(__file__).resolve().parents[1]
VECTOR_ROOT = ROOT / "conformance" / "interchange" / "v0.1.0"
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)


class _MemorySource:
    def __init__(self, values: Mapping[str, bytes]) -> None:
        self._values = dict(values)

    def iter_asset(self, asset: PortableAsset, *, chunk_size: int) -> Iterator[bytes]:
        data = self._values[asset.object_id]
        for offset in range(0, len(data), chunk_size):
            yield data[offset : offset + chunk_size]


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _trust() -> DataTrustClassification:
    return DataTrustClassification(
        zone=TrustZone.EXTERNAL_UNTRUSTED,
        role=ContentRole.DATA,
        integrity=IntegrityState.VERIFIED_SHA256,
        sensitivity=Sensitivity.PUBLIC,
    )


def _package(
    assets: tuple[PortableAsset, ...],
    *,
    extensions: dict[str, object] | None = None,
    large_fact: str | None = None,
    extra_relationship: bool = False,
) -> InterchangePackage:
    record = PortableRecord(
        record_type=PortableRecordType.SOURCE,
        contract_version="0.1.0",
        record_id=_sha(b"vector-record"),
        trust=_trust(),
        facts={"fixture": True, **({"note": large_fact} if large_fact else {})},
    )
    relationships = [
        PortableRelationship(
            subject_id=record.record_id,
            predicate=RelationshipPredicate.USES_ASSET,
            object_id=asset.object_id,
        )
        for asset in assets
    ]
    if extra_relationship:
        relationships.append(
            PortableRelationship(
                subject_id=record.record_id,
                predicate=RelationshipPredicate.DESCRIBES,
                object_id=record.record_id,
            )
        )
    relationships.sort(key=lambda item: (item.subject_id, item.predicate.value, item.object_id))
    values: dict[str, object] = {
        "profile_version": "0.1.0",
        "schema_version": "0.1.0",
        "package_id": _sha(b"placeholder"),
        "identity_algorithm": "sha256-rfc8785-v1",
        "scope_id": _sha(b"vector-scope"),
        "extension_policy": ExtensionPolicy.PRESERVE if extensions else ExtensionPolicy.REJECT,
        "records": (record,),
        "assets": tuple(sorted(assets, key=lambda item: item.object_id)),
        "relationships": tuple(relationships),
        "extensions": extensions or {},
    }
    values["package_id"] = package_identity(values)
    return InterchangePackage.model_validate(values)


def _included(data: bytes, *, media_type: str = "text/plain") -> PortableAsset:
    object_id = _sha(data)
    return PortableAsset(
        object_id=object_id,
        byte_length=len(data),
        media_type=media_type,
        role=AssetRole.SOURCE,
        disposition=AssetDisposition.INCLUDED,
        payload_path=payload_path(object_id),
        redistribution_asserted=True,
        license_assertion="CC0-1.0 synthetic fixture",
    )


def _referenced() -> PortableAsset:
    return PortableAsset(
        object_id=_sha(b"referenced-only-object"),
        byte_length=22,
        media_type="application/octet-stream",
        role=AssetRole.PROVIDER_NATIVE,
        disposition=AssetDisposition.REFERENCED,
        reference="urn:example:synthetic-reference",
    )


def _write_valid(path: Path, package: InterchangePackage, values: Mapping[str, bytes]) -> None:
    InterchangeService().export(package, _MemorySource(values), path)


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
    extra: tuple[str, bytes] | None = None,
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
        entries.append(next(item for item in entries if item[2] == duplicate))
    if extra is not None:
        entries.append((extra[0], extra[1], extra[0]))
    entries.sort(key=lambda item: item[0])
    with zipfile.ZipFile(destination, "w") as target:
        target.comment = archive_comment
        for name, data, original in entries:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                target.writestr(
                    _info(name, mode=mode_override.get(original, stat.S_IFREG | 0o644)),
                    data,
                )


def _replace_record(source: Path, destination: Path, mutate: object) -> None:
    with zipfile.ZipFile(source) as archive:
        value = json.loads(archive.read("openardp-package.json"))
    assert callable(mutate)
    mutate(value)
    value["package_id"] = package_identity(value)
    _rewrite(
        source,
        destination,
        replace={"openardp-package.json": canonical_json_bytes(value)},
    )


def _patch_flags(source: Path, destination: Path, flag: int) -> None:
    data = bytearray(source.read_bytes())
    offset = 0
    while True:
        local = data.find(b"PK\x03\x04", offset)
        if local < 0:
            break
        current = int.from_bytes(data[local + 6 : local + 8], "little") | flag
        data[local + 6 : local + 8] = current.to_bytes(2, "little")
        offset = local + 4
    offset = 0
    while True:
        central = data.find(b"PK\x01\x02", offset)
        if central < 0:
            break
        current = int.from_bytes(data[central + 8 : central + 10], "little") | flag
        data[central + 8 : central + 10] = current.to_bytes(2, "little")
        offset = central + 4
    destination.write_bytes(data)


def _generate(directory: Path) -> None:
    valid = directory / "valid"
    invalid = directory / "invalid"
    valid.mkdir(parents=True)
    invalid.mkdir(parents=True)

    data = b"OpenARDP synthetic evidence\n"
    asset = _included(data)
    minimal = _package((asset,))
    _write_valid(valid / "minimal.zip", minimal, {asset.object_id: data})
    referenced = _package((_referenced(),))
    _write_valid(valid / "referenced-only.zip", referenced, {})
    extended = _package((asset,), extensions={"org.openardp.vector": {"value": 1}})
    _write_valid(valid / "preserved-extension.zip", extended, {asset.object_id: data})

    base = valid / "minimal.zip"
    with zipfile.ZipFile(base) as archive:
        payload = next(name for name in archive.namelist() if name.startswith("data/"))
    (invalid / "not-zip.zip").write_bytes(b"synthetic malformed archive")
    _rewrite(base, invalid / "compressed.zip")
    # Rewrite once more with DEFLATE because the profile helper is intentionally stored.
    with (
        zipfile.ZipFile(base) as source,
        zipfile.ZipFile(invalid / "compressed.zip", "w") as target,
    ):
        for name in source.namelist():
            info = _info(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, source.read(name))
    _rewrite(base, invalid / "comment.zip", archive_comment=b"hidden")
    _rewrite(base, invalid / "traversal.zip", rename={payload: "../escape"})
    _rewrite(base, invalid / "absolute.zip", rename={payload: "/absolute"})
    _rewrite(base, invalid / "reserved-path.zip", rename={payload: "data/CON/file"})
    _rewrite(base, invalid / "non-nfc-path.zip", rename={payload: "data/cafe\u0301/file"})
    _rewrite(base, invalid / "control-path.zip", rename={payload: "data/control\u0001/file"})
    _rewrite(base, invalid / "duplicate.zip", duplicate="bagit.txt")
    _rewrite(base, invalid / "case-collision.zip", extra=("BAGIT.TXT", b"collision"))
    _rewrite(base, invalid / "missing-tag.zip", omit={"bagit.txt"})
    _rewrite(base, invalid / "corrupt-payload.zip", replace={payload: b"different"})
    _rewrite(
        base,
        invalid / "link-mode.zip",
        mode_override={"bagit.txt": stat.S_IFLNK | 0o777},
    )
    _rewrite(
        base,
        invalid / "device-mode.zip",
        mode_override={"bagit.txt": stat.S_IFCHR | 0o600},
    )
    _rewrite(base, invalid / "undeclared-entry.zip", extra=("unexpected.txt", b"x"))
    _patch_flags(base, invalid / "encrypted-flag.zip", 0x1)
    _patch_flags(base, invalid / "descriptor-flag.zip", 0x8)
    _replace_record(
        base,
        invalid / "unsupported-version.zip",
        lambda value: value.__setitem__("profile_version", "0.2.0"),
    )
    _replace_record(
        base,
        invalid / "unsupported-schema-version.zip",
        lambda value: value.__setitem__("schema_version", "0.2.0"),
    )
    _replace_record(
        base,
        invalid / "unsupported-record-version.zip",
        lambda value: value["records"][0].__setitem__("contract_version", "0.2.0"),
    )
    _replace_record(
        base,
        invalid / "unknown-field.zip",
        lambda value: value.__setitem__("unknown", True),
    )
    _replace_record(
        base,
        invalid / "relationship-missing.zip",
        lambda value: value["relationships"][0].__setitem__("object_id", _sha(b"missing-endpoint")),
    )
    _replace_record(
        base,
        invalid / "relationship-cycle.zip",
        lambda value: value["relationships"][0].update(
            {
                "predicate": "derived_from",
                "object_id": value["records"][0]["record_id"],
            }
        ),
    )
    _replace_record(
        base,
        invalid / "redistribution-not-asserted.zip",
        lambda value: value["assets"][0].__setitem__("redistribution_asserted", False),
    )
    _replace_record(
        base,
        invalid / "credential-license.zip",
        lambda value: value["assets"][0].__setitem__(
            "license_assertion", "https://user:password@example.invalid/license"
        ),
    )
    _replace_record(
        base,
        invalid / "trust-elevation.zip",
        lambda value: value["records"][0]["trust"].__setitem__(
            "instruction_execution_allowed", True
        ),
    )
    _replace_record(
        base,
        invalid / "duplicate-object-id.zip",
        lambda value: value["assets"].append(dict(value["assets"][0])),
    )
    _replace_record(
        valid / "preserved-extension.zip",
        invalid / "extension-rejected.zip",
        lambda value: value.__setitem__("extension_policy", "reject"),
    )
    _replace_record(
        valid / "referenced-only.zip",
        invalid / "local-reference.zip",
        lambda value: value["assets"][0].__setitem__("reference", "private-native.bin"),
    )

    nested_data = b"PK\x03\x04synthetic nested archive"
    nested_asset = _included(nested_data, media_type="application/zip")
    nested_package = _package((nested_asset,))
    BagItPackageAdapter().write_staged(
        nested_package,
        _MemorySource({nested_asset.object_id: nested_data}),
        invalid / "nested-archive.zip",
        limits=InterchangeLimits(),
    )

    large_data = b"x" * 2_000
    large_asset = _included(large_data)
    _write_valid(
        invalid / "entry-limit.zip",
        _package((large_asset,)),
        {large_asset.object_id: large_data},
    )
    metadata_package = _package((asset,), large_fact="x" * 70_000)
    _write_valid(
        invalid / "metadata-limit.zip",
        metadata_package,
        {asset.object_id: data},
    )
    relationship_package = _package((asset,), extra_relationship=True)
    _write_valid(
        invalid / "relationship-limit.zip",
        relationship_package,
        {asset.object_id: data},
    )
    limit_data = b"z" * 1_100_000
    limit_asset = _included(limit_data)
    limit_package = _package((limit_asset,))
    _write_valid(
        invalid / "archive-limit.zip",
        limit_package,
        {limit_asset.object_id: limit_data},
    )
    _write_valid(
        invalid / "expanded-limit.zip",
        limit_package,
        {limit_asset.object_id: limit_data},
    )
    second_data = b"second object"
    second_asset = _included(second_data)
    _write_valid(
        invalid / "entry-count-limit.zip",
        _package(tuple(sorted((asset, second_asset), key=lambda item: item.object_id))),
        {asset.object_id: data, second_asset.object_id: second_data},
    )
    shutil.copyfile(base, invalid / "path-byte-limit.zip")
    shutil.copyfile(base, invalid / "path-depth-limit.zip")

    manifest = {
        "profile_version": "0.1.0",
        "valid": [
            {"path": "valid/minimal.zip"},
            {"path": "valid/preserved-extension.zip"},
            {"path": "valid/referenced-only.zip"},
        ],
        "invalid": [
            {"path": "invalid/absolute.zip", "error": "policy_rejected"},
            {
                "path": "invalid/archive-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_archive_bytes": 1_048_576},
            },
            {"path": "invalid/case-collision.zip", "error": "policy_rejected"},
            {"path": "invalid/comment.zip", "error": "policy_rejected"},
            {"path": "invalid/compressed.zip", "error": "policy_rejected"},
            {"path": "invalid/control-path.zip", "error": "policy_rejected"},
            {"path": "invalid/corrupt-payload.zip", "error": "integrity_invalid"},
            {"path": "invalid/credential-license.zip", "error": "policy_rejected"},
            {"path": "invalid/descriptor-flag.zip", "error": "policy_rejected"},
            {"path": "invalid/device-mode.zip", "error": "policy_rejected"},
            {"path": "invalid/duplicate.zip", "error": "malformed_package"},
            {"path": "invalid/duplicate-object-id.zip", "error": "malformed_package"},
            {"path": "invalid/encrypted-flag.zip", "error": "policy_rejected"},
            {
                "path": "invalid/entry-count-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_entry_count": 6},
            },
            {
                "path": "invalid/entry-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_entry_bytes": 1024},
            },
            {
                "path": "invalid/expanded-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_expanded_bytes": 1_048_576},
            },
            {"path": "invalid/extension-rejected.zip", "error": "policy_rejected"},
            {"path": "invalid/link-mode.zip", "error": "policy_rejected"},
            {"path": "invalid/local-reference.zip", "error": "policy_rejected"},
            {
                "path": "invalid/metadata-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_metadata_bytes": 65536},
            },
            {"path": "invalid/missing-tag.zip", "error": "malformed_package"},
            {"path": "invalid/nested-archive.zip", "error": "policy_rejected"},
            {"path": "invalid/non-nfc-path.zip", "error": "policy_rejected"},
            {"path": "invalid/not-zip.zip", "error": "malformed_package"},
            {
                "path": "invalid/path-byte-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_path_bytes": 64},
            },
            {
                "path": "invalid/path-depth-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_path_depth": 4},
            },
            {"path": "invalid/redistribution-not-asserted.zip", "error": "policy_rejected"},
            {
                "path": "invalid/relationship-limit.zip",
                "error": "resource_exhausted",
                "limits": {"max_relationships": 1},
            },
            {"path": "invalid/relationship-cycle.zip", "error": "relationship_invalid"},
            {"path": "invalid/relationship-missing.zip", "error": "relationship_invalid"},
            {"path": "invalid/reserved-path.zip", "error": "policy_rejected"},
            {"path": "invalid/traversal.zip", "error": "policy_rejected"},
            {"path": "invalid/trust-elevation.zip", "error": "policy_rejected"},
            {"path": "invalid/undeclared-entry.zip", "error": "policy_rejected"},
            {"path": "invalid/unknown-field.zip", "error": "malformed_package"},
            {
                "path": "invalid/unsupported-record-version.zip",
                "error": "unsupported_version",
            },
            {
                "path": "invalid/unsupported-schema-version.zip",
                "error": "unsupported_version",
            },
            {"path": "invalid/unsupported-version.zip", "error": "unsupported_version"},
        ],
    }
    (directory / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Write or compare the complete deterministic vector tree."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="openardp-vectors-") as temporary:
        generated = Path(temporary) / "v0.1.0"
        _generate(generated)
        if arguments.check:
            if _tree_bytes(generated) != _tree_bytes(VECTOR_ROOT):
                print("interchange vector drift")
                return 1
            print(f"all {len(_tree_bytes(generated))} interchange vectors are current")
            return 0
        if VECTOR_ROOT.exists():
            shutil.rmtree(VECTOR_ROOT)
        VECTOR_ROOT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(generated, VECTOR_ROOT)
    print(f"wrote {len(_tree_bytes(VECTOR_ROOT))} interchange vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
