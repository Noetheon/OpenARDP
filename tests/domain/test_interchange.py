"""Pure experimental interchange contract tests."""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    TrustZone,
)
from openardp.domain.interchange import (
    AssetDisposition,
    AssetRole,
    ExtensionPolicy,
    ImportPlan,
    InterchangeLimits,
    InterchangePackage,
    PackageInventoryEntry,
    PortableAsset,
    PortableRecord,
    PortableRecordType,
    PortableRelationship,
    RelationshipPredicate,
    import_plan_identity,
    package_identity,
)


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _trust() -> DataTrustClassification:
    return DataTrustClassification(
        zone=TrustZone.EXTERNAL_UNTRUSTED,
        role=ContentRole.DATA,
        integrity=IntegrityState.VERIFIED_SHA256,
        sensitivity=Sensitivity.UNKNOWN,
    )


def package(*, extensions: dict[str, object] | None = None) -> InterchangePackage:
    """Build one canonical synthetic package."""
    data = b"synthetic"
    asset = PortableAsset(
        object_id=_sha(data),
        byte_length=len(data),
        media_type="text/plain",
        role=AssetRole.SOURCE,
        disposition=AssetDisposition.INCLUDED,
        payload_path=f"data/objects/sha256/{_sha(data)[7:9]}/{_sha(data)[9:]}",
        redistribution_asserted=True,
    )
    record = PortableRecord(
        record_type=PortableRecordType.SOURCE,
        contract_version="0.1.0",
        record_id=_sha(b"record"),
        trust=_trust(),
        facts={"title": "synthetic"},
    )
    relationship = PortableRelationship(
        subject_id=record.record_id,
        predicate=RelationshipPredicate.USES_ASSET,
        object_id=asset.object_id,
    )
    values = {
        "profile_version": "0.1.0",
        "schema_version": "0.1.0",
        "package_id": _sha(b"placeholder"),
        "identity_algorithm": "sha256-rfc8785-v1",
        "scope_id": _sha(b"scope"),
        "extension_policy": (ExtensionPolicy.PRESERVE if extensions else ExtensionPolicy.REJECT),
        "records": (record,),
        "assets": (asset,),
        "relationships": (relationship,),
        "extensions": extensions or {},
    }
    values["package_id"] = package_identity(values)
    return InterchangePackage.model_validate(values)


def test_package_identity_is_stable_and_recomputed() -> None:
    """Bind the identifier to every canonical semantic package fact."""
    first = package()
    assert first.package_id == package_identity(first.model_dump(mode="json"))
    assert first == package()


def test_package_rejects_wrong_identity_and_unsorted_records() -> None:
    """Reject a declared identity that does not match package facts."""
    value = package().model_dump(mode="json")
    value["package_id"] = _sha(b"wrong")
    with pytest.raises(ValidationError, match="package_id"):
        InterchangePackage.model_validate_json(json.dumps(value))


def test_asset_disposition_requires_exactly_one_location_policy() -> None:
    """Require affirmative permission and one included payload path."""
    with pytest.raises(ValidationError, match="included asset"):
        PortableAsset(
            object_id=_sha(b"x"),
            byte_length=1,
            media_type="text/plain",
            role=AssetRole.SOURCE,
            disposition=AssetDisposition.INCLUDED,
            redistribution_asserted=False,
        )


def test_reject_extension_policy_requires_empty_extensions() -> None:
    """Make extension rejection a whole-package rule."""
    value = package(extensions={"org.example.note": "kept"}).model_dump(mode="json")
    value["extension_policy"] = "reject"
    value["package_id"] = package_identity(value)
    with pytest.raises(ValidationError, match="reject extension policy"):
        InterchangePackage.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("version", ["0.2.0", "1.0.0", "latest"])
def test_reader_accepts_only_exact_installed_versions(version: str) -> None:
    """Reject uninstalled and malformed profile versions distinctly in validation."""
    value = package().model_dump(mode="json")
    value["profile_version"] = version
    value["package_id"] = package_identity(value)
    with pytest.raises(ValidationError, match="version"):
        InterchangePackage.model_validate_json(json.dumps(value))


def test_limits_enforce_installed_ranges() -> None:
    """Bound hostile-package resource configuration itself."""
    assert InterchangeLimits().max_entry_count == 10_000
    with pytest.raises(ValidationError):
        InterchangeLimits(max_entry_count=5)


def test_relationship_endpoints_and_derivation_cycles_fail_closed() -> None:
    """Reject relationships to identities outside the complete scope."""
    value = package().model_dump(mode="json")
    value["relationships"][0]["object_id"] = _sha(b"missing")
    value["package_id"] = package_identity(value)
    with pytest.raises(ValidationError, match="endpoint"):
        InterchangePackage.model_validate_json(json.dumps(value))


def test_imported_records_are_data_and_cannot_enable_instruction_execution() -> None:
    """Prevent integrity metadata from granting execution authority."""
    value = package().model_dump(mode="json")
    value["records"][0]["trust"]["instruction_execution_allowed"] = True
    value["package_id"] = package_identity(value)
    with pytest.raises(ValidationError, match="instruction_execution_allowed"):
        InterchangePackage.model_validate_json(json.dumps(value))


def test_import_plan_identity_binds_target_limits_and_inventory() -> None:
    """Reject a replayed plan whose target authority or verified facts changed."""
    values: dict[str, object] = {
        "plan_id": _sha(b"placeholder"),
        "package_id": package().package_id,
        "archive_sha256": hashlib.sha256(b"archive").hexdigest(),
        "target_id": _sha(b"target"),
        "limits": InterchangeLimits(),
        "inventory": (
            PackageInventoryEntry(
                path="bagit.txt",
                byte_length=1,
                sha256=hashlib.sha256(b"x").hexdigest(),
                kind="tag",
            ),
        ),
    }
    values["plan_id"] = import_plan_identity(values)
    plan = ImportPlan.model_validate(values)
    changed = plan.model_dump(mode="python")
    changed["target_id"] = _sha(b"other-target")
    with pytest.raises(ValidationError, match="plan_id"):
        ImportPlan.model_validate(changed)
