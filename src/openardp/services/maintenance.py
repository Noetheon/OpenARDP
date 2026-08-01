"""Explicit bounded retention planning and maintenance orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from openardp.domain.identity import canonical_sha256
from openardp.domain.maintenance import (
    InventoryLimits,
    MaintenanceInventory,
    MaintenanceOperation,
    MaintenanceOperationKind,
    MaintenanceOperationState,
    QuarantineBatch,
    QuarantineBatchState,
    ReclamationCandidate,
    ReclamationPlan,
    RetentionClassification,
    RetentionExplanation,
    RetentionHold,
    RetentionInventoryReport,
    RetentionPolicy,
    RetentionSnapshot,
    StorageDiagnostic,
)
from openardp.ports.maintenance import (
    AcknowledgementRequired,
    GraceActive,
    MaintenanceRuntimeCatalog,
    MaintenanceStore,
    RecoveryRequired,
    StalePlan,
    StoreInconsistent,
)

IRREVERSIBLE_ACKNOWLEDGEMENT = "I UNDERSTAND THIS REMOVAL CANNOT BE UNDONE"


class MaintenanceService:
    """Coordinate read-only planning before any explicit durable mutation."""

    def __init__(
        self,
        store: MaintenanceStore,
        catalog: MaintenanceRuntimeCatalog,
        *,
        fault: Callable[[str], None] | None = None,
    ) -> None:
        """Bind the isolated filesystem and catalog maintenance boundaries."""
        self._store = store
        self._catalog = catalog
        self._fault = fault or (lambda _point: None)

    def inventory(
        self,
        *,
        policy: RetentionPolicy,
        now: datetime,
    ) -> RetentionInventoryReport:
        """Explain every verified object without changing workspace state."""
        snapshot, inventory = self._observe(policy.limits, now=now)
        return self._report(snapshot, inventory, policy=policy, now=now)

    @staticmethod
    def _report(
        snapshot: RetentionSnapshot,
        inventory: MaintenanceInventory,
        *,
        policy: RetentionPolicy,
        now: datetime,
    ) -> RetentionInventoryReport:
        """Classify one exact already-observed catalog/filesystem pair."""
        root_reasons: dict[str, set[str]] = {}
        for root in snapshot.roots:
            root_reasons.setdefault(root.object_id, set()).add(root.reason.value)
        held = {hold.object_id for hold in snapshot.holds if hold.active_at(now)}
        cutoff = now - timedelta(seconds=policy.candidate_min_age_seconds)
        explanations: list[RetentionExplanation] = []
        for item in inventory.active:
            reasons = root_reasons.get(item.object_id, set())
            if item.object_id in held:
                reasons.add("active_hold")
            if reasons:
                classification = RetentionClassification.PROTECTED
            elif item.modified_at > cutoff:
                reasons.add("unreferenced_min_age_pending")
                classification = RetentionClassification.PROTECTED
            else:
                reasons.add("unreferenced_min_age_elapsed")
                classification = RetentionClassification.CANDIDATE
            explanations.append(
                RetentionExplanation(
                    object_id=item.object_id,
                    byte_length=item.byte_length,
                    classification=classification,
                    reasons=tuple(sorted(reasons)),
                )
            )
        for item in inventory.quarantined:
            explanations.append(
                RetentionExplanation(
                    object_id=item.object_id,
                    byte_length=item.byte_length,
                    classification=RetentionClassification.QUARANTINED,
                    reasons=("quarantined",),
                )
            )
        return RetentionInventoryReport(
            observed_at=now,
            catalog_schema_version=snapshot.catalog_schema_version,
            root_snapshot_id=snapshot.root_snapshot_id,
            hold_snapshot_id=snapshot.hold_snapshot_id,
            inventory_id=inventory.inventory_id,
            explanations=tuple(sorted(explanations, key=lambda item: item.object_id)),
            anomalies=inventory.anomalies,
        )

    def plan(self, *, policy: RetentionPolicy, now: datetime) -> ReclamationPlan:
        """Return an exact actionable plan only for a complete consistent inventory."""
        snapshot, inventory = self._observe(policy.limits, now=now)
        if inventory.anomalies:
            raise StoreInconsistent("managed storage is inconsistent")
        report = self._report(snapshot, inventory, policy=policy, now=now)
        active = {item.object_id: item for item in inventory.active}
        candidates = tuple(
            ReclamationCandidate(
                item=active[explanation.object_id],
                reason="unreferenced_min_age_elapsed",
            )
            for explanation in report.explanations
            if explanation.classification is RetentionClassification.CANDIDATE
        )
        return ReclamationPlan.create(
            policy=policy,
            catalog_schema_version=snapshot.catalog_schema_version,
            root_snapshot_id=snapshot.root_snapshot_id,
            hold_snapshot_id=snapshot.hold_snapshot_id,
            inventory=inventory,
            candidates=candidates,
            observed_at=now,
        )

    def diagnostics(
        self,
        *,
        policy: RetentionPolicy,
        now: datetime,
    ) -> StorageDiagnostic:
        """Return exact body-free filesystem, catalog, index and reserve facts."""
        index_count, index_bytes = self._catalog.search_index_diagnostics()
        return self._store.diagnostics(
            reserve_bytes=policy.reserve_bytes,
            observed_at=now,
            index_count=index_count,
            index_bytes=index_bytes,
        )

    def add_hold(
        self,
        object_id: str,
        *,
        reason: str,
        now: datetime,
        expires_at: datetime | None = None,
    ) -> RetentionHold:
        """Protect one currently verified managed object with an explicit reason."""
        inventory = self._store.inventory(
            InventoryLimits(max_entries=1_000_000, max_bytes=9_007_199_254_740_991)
        )
        if object_id not in {
            item.object_id for item in (*inventory.active, *inventory.quarantined)
        }:
            raise StoreInconsistent("hold target is not a verified managed object")
        hold = RetentionHold(
            hold_id=canonical_sha256(
                {
                    "domain": "openardp:retention-hold-v1",
                    "object_id": object_id,
                    "reason": reason,
                    "created_at": now.isoformat(),
                    "expires_at": expires_at.isoformat() if expires_at is not None else None,
                }
            ),
            object_id=object_id,
            reason=reason,
            created_at=now,
            expires_at=expires_at,
        )
        return self._catalog.add_retention_hold(hold)

    def release_hold(self, hold_id: str, *, now: datetime) -> RetentionHold:
        """Release one exact operator hold without deleting its history."""
        return self._catalog.release_retention_hold(hold_id, now=now)

    def quarantine(self, plan: ReclamationPlan, *, now: datetime) -> QuarantineBatch:
        """Reproduce one exact plan, persist intent, then quarantine every entry."""
        existing = self._catalog.quarantine_batch_for_plan(plan.plan_id)
        if existing is not None and existing.state is QuarantineBatchState.QUARANTINED:
            return existing
        if existing is not None:
            active = self._catalog.active_maintenance_operation()
            if (
                active is not None
                and active.kind is MaintenanceOperationKind.QUARANTINE
                and active.subject_id == plan.plan_id
            ):
                return self._apply_move(active, now=now)
            raise RecoveryRequired("quarantine batch requires explicit recovery")
        current = self.plan(policy=plan.policy, now=now)
        if current.plan_id != plan.plan_id:
            existing = self._catalog.quarantine_batch_for_plan(plan.plan_id)
            if existing is not None and existing.state is QuarantineBatchState.QUARANTINED:
                return existing
            if existing is not None:
                active = self._catalog.active_maintenance_operation()
                if (
                    active is not None
                    and active.kind is MaintenanceOperationKind.QUARANTINE
                    and active.subject_id == plan.plan_id
                ):
                    return self._apply_move(active, now=now)
                refreshed = self._catalog.quarantine_batch_for_plan(plan.plan_id)
                if refreshed is not None and refreshed.state is QuarantineBatchState.QUARANTINED:
                    return refreshed
                raise RecoveryRequired("quarantine batch requires explicit recovery")
            raise StalePlan("reclamation plan no longer matches workspace state")
        operation = self._catalog.claim_quarantine(plan, now=now)
        self._fault("after_quarantine_claim")
        return self._apply_move(operation, now=now)

    def restore(self, batch_id: UUID, *, now: datetime) -> QuarantineBatch:
        """Persist exact restore intent and return every entry to active storage."""
        batch = self._catalog.quarantine_batch(batch_id)
        if batch is not None and batch.state is QuarantineBatchState.RESTORED:
            return batch
        operation = self._catalog.claim_restore(batch_id, now=now)
        self._fault("after_restore_claim")
        return self._apply_move(operation, now=now)

    def commit(
        self,
        batch_id: UUID,
        *,
        acknowledgement: str,
        now: datetime,
    ) -> QuarantineBatch:
        """Commit one named expired batch under exact separate authority."""
        if acknowledgement != IRREVERSIBLE_ACKNOWLEDGEMENT:
            raise AcknowledgementRequired("irreversible acknowledgement is required")
        batch = self._catalog.quarantine_batch(batch_id)
        if batch is None:
            raise RecoveryRequired("quarantine batch does not exist")
        if batch.state is QuarantineBatchState.QUARANTINED and now < batch.not_before:
            raise GraceActive("quarantine grace period is active")
        if batch is not None and batch.state in {
            QuarantineBatchState.COMMITTED,
            QuarantineBatchState.BLOCKED,
        }:
            return batch
        operation = self._catalog.claim_commit(
            batch_id,
            acknowledgement_digest=canonical_sha256({"acknowledgement": acknowledgement}),
            now=now,
        )
        self._fault("after_commit_claim")
        return self._apply_commit(operation, now=now)

    def recover(self, *, now: datetime) -> MaintenanceOperation | None:
        """Replay only the one already persisted reversible maintenance intent."""
        operation = self._catalog.active_maintenance_operation()
        if operation is None:
            return None
        if operation.kind is MaintenanceOperationKind.COMMIT:
            self._apply_commit(operation, now=now)
        elif operation.kind in {
            MaintenanceOperationKind.QUARANTINE,
            MaintenanceOperationKind.RESTORE,
        }:
            self._apply_move(operation, now=now)
        else:
            raise RecoveryRequired("active maintenance operation requires explicit recovery")
        completed = self._catalog.active_maintenance_operation()
        if completed is not None:
            raise RecoveryRequired("maintenance recovery did not reach terminal state")
        return operation

    def _apply_commit(
        self,
        operation: MaintenanceOperation,
        *,
        now: datetime,
    ) -> QuarantineBatch:
        operation = self._catalog.mark_operation_applying(operation.operation_id, now=now)
        try:
            for entry in operation.entries:
                self._fault(f"before_commit_{entry.sequence}")
                if entry.action.value == "DELETE":
                    self._store.remove(entry.object_id, byte_length=entry.byte_length)
                else:
                    self._store.transition(
                        entry.object_id,
                        to_quarantine=False,
                        byte_length=entry.byte_length,
                    )
                self._fault(f"after_commit_{entry.sequence}")
            self._fault("before_commit_finalize")
        except Exception as error:
            raise RecoveryRequired("maintenance recovery is required") from error
        return self._catalog.complete_commit(operation.operation_id, now=now)

    def _apply_move(
        self,
        operation: MaintenanceOperation,
        *,
        now: datetime,
    ) -> QuarantineBatch:
        if operation.state is MaintenanceOperationState.SUCCEEDED:
            batch = self._catalog.quarantine_batch_for_plan(operation.subject_id)
            if batch is None:
                raise RecoveryRequired("terminal maintenance batch is missing")
            return batch
        operation = self._catalog.mark_operation_applying(operation.operation_id, now=now)
        to_quarantine = operation.kind is MaintenanceOperationKind.QUARANTINE
        try:
            for entry in operation.entries:
                self._fault(f"before_transition_{entry.sequence}")
                self._store.transition(
                    entry.object_id,
                    to_quarantine=to_quarantine,
                    byte_length=entry.byte_length,
                )
                self._fault(f"after_transition_{entry.sequence}")
            self._fault("before_move_finalize")
        except Exception as error:
            raise RecoveryRequired("maintenance recovery is required") from error
        if to_quarantine:
            return self._catalog.complete_quarantine(operation.operation_id, now=now)
        return self._catalog.complete_restore(operation.operation_id, now=now)

    def _observe(
        self,
        limits: InventoryLimits,
        *,
        now: datetime,
    ) -> tuple[RetentionSnapshot, MaintenanceInventory]:
        before = self._catalog.retention_snapshot(observed_at=now)
        inventory = self._store.inventory(limits)
        after = self._catalog.retention_snapshot(observed_at=now)
        if (
            before.catalog_schema_version != after.catalog_schema_version
            or before.root_snapshot_id != after.root_snapshot_id
            or before.hold_snapshot_id != after.hold_snapshot_id
        ):
            raise StalePlan("catalog changed during maintenance inventory")
        return after, inventory


__all__ = ["IRREVERSIBLE_ACKNOWLEDGEMENT", "MaintenanceService"]
