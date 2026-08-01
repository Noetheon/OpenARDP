"""Provider-neutral boundary for explicit bounded workspace maintenance."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from openardp.domain.maintenance import (
    CapacityReport,
    InventoryLimits,
    MaintenanceInventory,
    MaintenanceOperation,
    QuarantineBatch,
    ReclamationPlan,
    RetentionHold,
    RetentionSnapshot,
    StorageDiagnostic,
)


class MaintenanceError(RuntimeError):
    """Base class for sanitized maintenance failures."""


class MaintenanceBusy(MaintenanceError):
    """Raised when another exact maintenance intent is active."""


class RecoveryRequired(MaintenanceError):
    """Raised when durable intent must be recovered before normal writes."""


class InventoryOverflow(MaintenanceError):
    """Raised without partial authority when an inventory bound is exceeded."""


class StoreInconsistent(MaintenanceError):
    """Raised when unsafe managed storage state prevents an actionable plan."""


class StalePlan(MaintenanceError):
    """Raised when supplied dry-run facts no longer reproduce exactly."""


class InsufficientSpace(MaintenanceError):
    """Raised before publication when required bytes plus reserve are unavailable."""


class GraceActive(MaintenanceError):
    """Raised when irreversible removal is requested before its not-before time."""


class AcknowledgementRequired(MaintenanceError):
    """Raised unless the exact separate irreversible acknowledgement is supplied."""


@runtime_checkable
class MaintenanceStore(Protocol):
    """Exact-object filesystem authority isolated from ordinary immutable CAS use."""

    def inventory(self, limits: InventoryLimits) -> MaintenanceInventory:
        """Return one complete bounded active and quarantine inventory."""
        ...

    def transition(self, object_id: str, *, to_quarantine: bool, byte_length: int) -> None:
        """Move exact verified bytes between active and quarantine without overwrite."""
        ...

    def remove(self, object_id: str, *, byte_length: int) -> None:
        """Remove exact verified quarantined bytes under prior durable authority."""
        ...

    def capacity(self, required_bytes: int, reserve_bytes: int) -> CapacityReport:
        """Return exact current local admission facts without mutating storage."""
        ...

    def diagnostics(
        self,
        *,
        reserve_bytes: int,
        observed_at: datetime,
        index_count: int,
        index_bytes: int,
    ) -> StorageDiagnostic:
        """Return bounded exact logical categories and local capacity."""
        ...


@runtime_checkable
class RetentionCatalog(Protocol):
    """Read/hold catalog boundary needed before mutation authority."""

    def retention_snapshot(self, *, observed_at: datetime) -> RetentionSnapshot:
        """Return exact current roots and active holds in one read transaction."""
        ...

    def add_retention_hold(self, hold: RetentionHold) -> RetentionHold:
        """Create or return one exact operator hold."""
        ...

    def release_retention_hold(self, hold_id: str, *, now: datetime) -> RetentionHold:
        """Release one exact hold idempotently."""
        ...


@runtime_checkable
class MaintenanceCatalog(RetentionCatalog, Protocol):
    """Catalog snapshot and durable-intent authority for maintenance services."""

    def claim_operation(self, plan: ReclamationPlan, *, now: datetime) -> str:
        """Persist complete exact maintenance intent before filesystem mutation."""
        ...

    def finalize_operation(self, operation_id: str, *, now: datetime) -> None:
        """Publish verified terminal catalog/audit state."""
        ...


@runtime_checkable
class MaintenanceRuntimeCatalog(RetentionCatalog, Protocol):
    """Exact F013 quarantine/restore operation journal contract."""

    def quarantine_batch_for_plan(self, plan_id: str) -> QuarantineBatch | None:
        """Return a prior exact batch for idempotent plan retry."""
        ...

    def quarantine_batch(self, batch_id: UUID) -> QuarantineBatch | None:
        """Return one named batch and exact entries."""
        ...

    def claim_quarantine(self, plan: ReclamationPlan, *, now: datetime) -> MaintenanceOperation:
        """Persist complete quarantine intent before any object transition."""
        ...

    def claim_restore(self, batch_id: UUID, *, now: datetime) -> MaintenanceOperation:
        """Persist complete restore intent before any object transition."""
        ...

    def claim_commit(
        self,
        batch_id: UUID,
        *,
        acknowledgement_digest: str,
        now: datetime,
    ) -> MaintenanceOperation:
        """Persist exact delete-or-restore actions after final protection checks."""
        ...

    def mark_operation_applying(self, operation_id: UUID, *, now: datetime) -> MaintenanceOperation:
        """Mark exact durable intent as actively replaying."""
        ...

    def active_maintenance_operation(self) -> MaintenanceOperation | None:
        """Return the one restart-persistent active intent."""
        ...

    def complete_quarantine(self, operation_id: UUID, *, now: datetime) -> QuarantineBatch:
        """Publish complete verified quarantine state."""
        ...

    def complete_restore(self, operation_id: UUID, *, now: datetime) -> QuarantineBatch:
        """Publish complete verified restore state."""
        ...

    def complete_commit(self, operation_id: UUID, *, now: datetime) -> QuarantineBatch:
        """Publish exact removed/retained outcomes and clear the write fence."""
        ...

    def search_index_diagnostics(self) -> tuple[int, int]:
        """Return exact disposable lexical mapping count and logical bytes."""
        ...


__all__ = [
    "AcknowledgementRequired",
    "GraceActive",
    "InsufficientSpace",
    "InventoryOverflow",
    "MaintenanceBusy",
    "MaintenanceCatalog",
    "MaintenanceError",
    "MaintenanceRuntimeCatalog",
    "MaintenanceStore",
    "RecoveryRequired",
    "RetentionCatalog",
    "StalePlan",
    "StoreInconsistent",
]
