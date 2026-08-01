"""Structural contracts for the bounded F013 maintenance authority."""

from __future__ import annotations

from typing import assert_type

from openardp.ports.maintenance import (
    MaintenanceBusy,
    MaintenanceCatalog,
    MaintenanceError,
    MaintenanceStore,
    RecoveryRequired,
)
from openardp.ports.object_store import ObjectStore


def test_maintenance_authority_is_separate_from_immutable_object_store() -> None:
    """Do not broaden every ordinary CAS consumer with destructive methods."""
    assert not issubclass(MaintenanceStore, ObjectStore)
    assert hasattr(MaintenanceStore, "transition")
    assert hasattr(MaintenanceStore, "remove")
    assert not hasattr(ObjectStore, "remove")


def test_catalog_contract_exposes_snapshot_and_durable_intent() -> None:
    """Keep cross-resource authority behind one narrow provider-neutral port."""
    assert hasattr(MaintenanceCatalog, "retention_snapshot")
    assert hasattr(MaintenanceCatalog, "claim_operation")
    assert hasattr(MaintenanceCatalog, "finalize_operation")
    assert_type(MaintenanceCatalog, type[MaintenanceCatalog])


def test_maintenance_errors_are_sanitized_closed_types() -> None:
    """Expose stable classifications without provider exception text."""
    busy = MaintenanceBusy("maintenance_busy")
    recovery = RecoveryRequired("maintenance_recovery_required")
    assert isinstance(busy, MaintenanceError)
    assert isinstance(recovery, MaintenanceError)
    assert busy.args == ("maintenance_busy",)
