"""Pure F013 maintenance identity and invariant tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from openardp.domain.maintenance import (
    InventoryLimits,
    MaintenanceInventory,
    MaintenanceObject,
    ObjectLocation,
    ReclamationCandidate,
    ReclamationPlan,
    RetentionPolicy,
    StorageOptimizationItem,
    StorageOptimizationOutcome,
    StorageOptimizationReport,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
OBJECT_ID = "sha256:" + "1" * 64


def test_retention_policy_enforces_conservative_time_floors() -> None:
    """Operators may extend but never shorten the v0.1 protection windows."""
    policy = RetentionPolicy(limits=InventoryLimits(max_entries=10, max_bytes=1000))
    assert policy.candidate_min_age_seconds == 86_400
    assert policy.quarantine_grace_seconds == 604_800
    with pytest.raises(ValidationError):
        RetentionPolicy(
            candidate_min_age_seconds=86_399,
            limits=InventoryLimits(max_entries=10, max_bytes=1000),
        )
    with pytest.raises(ValidationError):
        RetentionPolicy(
            quarantine_grace_seconds=86_399,
            limits=InventoryLimits(max_entries=10, max_bytes=1000),
        )


def test_reclamation_plan_identity_excludes_reporting_time() -> None:
    """Same semantic facts retain one identity at different reporting instants."""
    policy = RetentionPolicy(limits=InventoryLimits(max_entries=10, max_bytes=1000))
    item = MaintenanceObject(
        object_id=OBJECT_ID,
        byte_length=3,
        modified_at=NOW - timedelta(days=2),
        location=ObjectLocation.ACTIVE,
    )
    candidate = ReclamationCandidate(item=item, reason="unreferenced_min_age_elapsed")
    inventory = MaintenanceInventory(
        active=(item,),
        quarantined=(),
        anomalies=(),
        scanned_entries=1,
        scanned_bytes=3,
    )
    first = ReclamationPlan.create(
        policy=policy,
        catalog_schema_version=10,
        root_snapshot_id="sha256:" + "2" * 64,
        hold_snapshot_id="sha256:" + "3" * 64,
        inventory=inventory,
        candidates=(candidate,),
        observed_at=NOW,
    )
    second = ReclamationPlan.create(
        policy=policy,
        catalog_schema_version=10,
        root_snapshot_id="sha256:" + "2" * 64,
        hold_snapshot_id="sha256:" + "3" * 64,
        inventory=inventory,
        candidates=(candidate,),
        observed_at=NOW + timedelta(hours=1),
    )
    assert first.plan_id == second.plan_id
    assert first.observed_at != second.observed_at


def test_maintenance_records_reject_naive_time_and_unsorted_objects() -> None:
    """Require UTC and canonical ordering at the pure-domain boundary."""
    with pytest.raises(ValidationError):
        MaintenanceObject(
            object_id=OBJECT_ID,
            byte_length=1,
            modified_at=datetime(2026, 8, 1),
            location=ObjectLocation.ACTIVE,
        )
    high = MaintenanceObject(
        object_id="sha256:" + "f" * 64,
        byte_length=1,
        modified_at=NOW,
        location=ObjectLocation.ACTIVE,
    )
    low = MaintenanceObject(
        object_id="sha256:" + "0" * 64,
        byte_length=1,
        modified_at=NOW,
        location=ObjectLocation.ACTIVE,
    )
    with pytest.raises(ValidationError, match="sorted"):
        MaintenanceInventory(
            active=(high, low),
            quarantined=(),
            anomalies=(),
            scanned_entries=2,
            scanned_bytes=2,
        )


def test_storage_optimization_report_is_sorted_body_free_and_aggregated() -> None:
    """Expose deterministic closed counts without paths or document bodies."""
    item = StorageOptimizationItem(
        object_id=OBJECT_ID,
        outcome=StorageOptimizationOutcome.COMPACTED,
        logical_bytes=100,
        stored_bytes_before=90,
        stored_bytes_after=40,
    )
    report = StorageOptimizationReport(
        workspace_revision=11,
        items=(item,),
        catalog_bytes_before=1000,
        catalog_bytes_after=700,
    )

    assert report.model_dump(mode="json") == {
        "catalog_bytes_after": 700,
        "catalog_bytes_before": 1000,
        "items": [
            {
                "logical_bytes": 100,
                "object_id": OBJECT_ID,
                "outcome": "compacted",
                "reason_code": None,
                "stored_bytes_after": 40,
                "stored_bytes_before": 90,
            }
        ],
        "workspace_revision": 11,
    }
    assert (report.eligible_count, report.completed_count, report.failed_count) == (1, 1, 0)
    assert report.stored_bytes_saved == 350
    with pytest.raises(ValidationError, match="sorted"):
        StorageOptimizationReport(
            workspace_revision=11,
            items=(item, item),
            catalog_bytes_before=0,
            catalog_bytes_after=0,
        )
