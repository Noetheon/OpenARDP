"""Restart-persistent quarantine and restore recovery tests."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.identity import canonical_sha256
from openardp.domain.maintenance import (
    InventoryLimits,
    QuarantineBatchState,
    RetentionHold,
    RetentionPolicy,
)
from openardp.domain.storage import StoredObject
from openardp.interfaces.cli import main
from openardp.ports.catalog import MaintenanceRecoveryRequired
from openardp.ports.maintenance import RecoveryRequired
from openardp.services.maintenance import (
    IRREVERSIBLE_ACKNOWLEDGEMENT,
    MaintenanceService,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def _candidate_workspace(
    tmp_path: Path,
) -> tuple[LocalWorkspace, RetentionPolicy, StoredObject]:
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"recoverable",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = NOW - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))
    policy = RetentionPolicy(limits=InventoryLimits(max_entries=10, max_bytes=100))
    return workspace, policy, stored


def test_crash_after_move_keeps_write_fence_until_explicit_recovery(tmp_path: Path) -> None:
    """Replay persisted intent rather than inferring authority from quarantine bytes."""
    workspace, policy, stored = _candidate_workspace(tmp_path)
    plan = MaintenanceService(workspace.maintenance_store, workspace.catalog).plan(
        policy=policy, now=NOW
    )

    def fail(point: str) -> None:
        if point == "after_transition_1":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RecoveryRequired):
        MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
            fault=fail,
        ).quarantine(plan, now=NOW)
    assert workspace.catalog.active_maintenance_operation() is not None
    with pytest.raises(MaintenanceRecoveryRequired):
        workspace.catalog.add_retention_hold(
            RetentionHold(
                hold_id=canonical_sha256({"blocked": 1}),
                object_id=stored.object_id,
                reason="operator_hold",
                created_at=NOW,
            )
        )

    recovered = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    assert recovered.recover(now=NOW) is not None
    assert workspace.catalog.active_maintenance_operation() is None
    batch = workspace.catalog.quarantine_batch_for_plan(plan.plan_id)
    assert batch is not None
    assert batch.state is QuarantineBatchState.QUARANTINED
    inventory = workspace.maintenance_store.inventory(policy.limits)
    assert inventory.active == ()
    assert inventory.quarantined[0].object_id == stored.object_id

    restored = recovered.restore(batch.batch_id, now=NOW + timedelta(hours=1))
    assert restored.state is QuarantineBatchState.RESTORED
    inventory = workspace.maintenance_store.inventory(policy.limits)
    assert inventory.quarantined == ()
    assert inventory.active[0].object_id == stored.object_id


def test_twenty_same_plan_quarantines_converge_to_one_batch(tmp_path: Path) -> None:
    """Serialize duplicate callers into one exact lifecycle and terminal outcome."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    plan = MaintenanceService(workspace.maintenance_store, workspace.catalog).plan(
        policy=policy,
        now=NOW,
    )

    def quarantine(_: int) -> str:
        batch = MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
        ).quarantine(plan, now=NOW)
        return str(batch.batch_id)

    with ThreadPoolExecutor(max_workers=10) as executor:
        batch_ids = tuple(executor.map(quarantine, range(20)))
    assert len(set(batch_ids)) == 1
    batch = workspace.catalog.quarantine_batch_for_plan(plan.plan_id)
    assert batch is not None
    assert batch.state is QuarantineBatchState.QUARANTINED
    assert workspace.catalog.active_maintenance_operation() is None


def test_late_same_plan_caller_converges_after_stale_initial_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the exact winner when publication lands between reads."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    plan = service.plan(policy=policy, now=NOW)
    winner = service.quarantine(plan, now=NOW)
    lookup = workspace.catalog.quarantine_batch_for_plan
    calls = 0

    def initially_stale(plan_id: str) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return lookup(plan_id)

    monkeypatch.setattr(workspace.catalog, "quarantine_batch_for_plan", initially_stale)
    converged = MaintenanceService(
        workspace.maintenance_store,
        workspace.catalog,
    ).quarantine(plan, now=NOW)

    assert converged == winner
    assert calls == 2
    assert workspace.catalog.claim_quarantine(plan, now=NOW).state.value == "SUCCEEDED"


def test_prepared_batch_read_converges_when_operation_finishes_before_active_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-read the batch when an active operation becomes terminal between snapshots."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    plan = service.plan(policy=policy, now=NOW)
    winner = service.quarantine(plan, now=NOW)
    stale = winner.model_copy(update={"state": QuarantineBatchState.PREPARED})
    lookup = workspace.catalog.quarantine_batch_for_plan
    calls = 0

    def initially_prepared(plan_id: str) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            return stale
        return lookup(plan_id)

    monkeypatch.setattr(workspace.catalog, "quarantine_batch_for_plan", initially_prepared)
    converged = MaintenanceService(
        workspace.maintenance_store,
        workspace.catalog,
    ).quarantine(plan, now=NOW)

    assert converged == winner
    assert calls == 2
    assert workspace.catalog.active_maintenance_operation() is None


def test_twenty_same_batch_restores_converge(tmp_path: Path) -> None:
    """Serialize duplicate restores into one exact active ownership state."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)

    def restore(_: int) -> str:
        result = MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
        ).restore(batch.batch_id, now=NOW + timedelta(hours=1))
        return result.state.value

    with ThreadPoolExecutor(max_workers=10) as executor:
        states = tuple(executor.map(restore, range(20)))
    assert states == ("RESTORED",) * 20
    assert workspace.catalog.active_maintenance_operation() is None


@pytest.mark.parametrize(
    "boundary",
    (
        "after_quarantine_claim",
        "before_transition_1",
        "after_transition_1",
        "before_move_finalize",
    ),
)
def test_every_quarantine_boundary_recovers(
    tmp_path: Path,
    boundary: str,
) -> None:
    """Replay quarantine intent after each exposed durable/filesystem boundary."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    plan = MaintenanceService(workspace.maintenance_store, workspace.catalog).plan(
        policy=policy,
        now=NOW,
    )

    def fail(point: str) -> None:
        if point == boundary:
            raise RuntimeError("synthetic quarantine boundary")

    with pytest.raises((RecoveryRequired, RuntimeError)):
        MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
            fault=fail,
        ).quarantine(plan, now=NOW)
    MaintenanceService(workspace.maintenance_store, workspace.catalog).recover(now=NOW)
    batch = workspace.catalog.quarantine_batch_for_plan(plan.plan_id)
    assert batch is not None
    assert batch.state is QuarantineBatchState.QUARANTINED


@pytest.mark.parametrize(
    "boundary",
    (
        "after_restore_claim",
        "before_transition_1",
        "after_transition_1",
        "before_move_finalize",
    ),
)
def test_every_restore_boundary_recovers(tmp_path: Path, boundary: str) -> None:
    """Replay restore intent after each exposed durable/filesystem boundary."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)

    def fail(point: str) -> None:
        if point == boundary:
            raise RuntimeError("synthetic restore boundary")

    with pytest.raises((RecoveryRequired, RuntimeError)):
        MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
            fault=fail,
        ).restore(batch.batch_id, now=NOW + timedelta(hours=1))
    service.recover(now=NOW + timedelta(hours=1))
    restored = workspace.catalog.quarantine_batch(batch.batch_id)
    assert restored is not None
    assert restored.state is QuarantineBatchState.RESTORED


@pytest.mark.parametrize(
    "boundary",
    (
        "after_commit_claim",
        "before_commit_1",
        "after_commit_1",
        "before_commit_finalize",
    ),
)
def test_every_commit_boundary_recovers_forward(tmp_path: Path, boundary: str) -> None:
    """Replay persisted irreversible intent forward after each exposed boundary."""
    workspace, _policy, _stored = _candidate_workspace(tmp_path)
    policy = RetentionPolicy(
        quarantine_grace_seconds=86_400,
        limits=InventoryLimits(max_entries=10, max_bytes=100),
    )
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)

    def fail(point: str) -> None:
        if point == boundary:
            raise RuntimeError("synthetic commit boundary")

    with pytest.raises((RecoveryRequired, RuntimeError)):
        MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
            fault=fail,
        ).commit(
            batch.batch_id,
            acknowledgement=IRREVERSIBLE_ACKNOWLEDGEMENT,
            now=NOW + timedelta(days=1),
        )
    service.recover(now=NOW + timedelta(days=1))
    committed = workspace.catalog.quarantine_batch(batch.batch_id)
    assert committed is not None
    assert committed.state is QuarantineBatchState.COMMITTED


def test_commit_crash_after_remove_recovers_forward_idempotently(tmp_path: Path) -> None:
    """A persisted delete intent can finish after bytes were already unlinked."""
    workspace, _policy, _stored = _candidate_workspace(tmp_path)
    policy = RetentionPolicy(
        quarantine_grace_seconds=86_400,
        limits=InventoryLimits(max_entries=10, max_bytes=100),
    )
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)

    def fail(point: str) -> None:
        if point == "after_commit_1":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RecoveryRequired):
        MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
            fault=fail,
        ).commit(
            batch.batch_id,
            acknowledgement=IRREVERSIBLE_ACKNOWLEDGEMENT,
            now=NOW + timedelta(days=1),
        )
    assert workspace.catalog.active_maintenance_operation() is not None

    assert service.recover(now=NOW + timedelta(days=1)) is not None
    completed = workspace.catalog.quarantine_batch(batch.batch_id)
    assert completed is not None
    assert completed.state is QuarantineBatchState.COMMITTED


def test_twenty_same_batch_commits_converge(tmp_path: Path) -> None:
    """Concurrent duplicate irreversible authority produces one terminal outcome."""
    workspace, _policy, _stored = _candidate_workspace(tmp_path)
    policy = RetentionPolicy(
        quarantine_grace_seconds=86_400,
        limits=InventoryLimits(max_entries=10, max_bytes=100),
    )
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)

    def commit(_: int) -> str:
        result = MaintenanceService(
            workspace.maintenance_store,
            workspace.catalog,
        ).commit(
            batch.batch_id,
            acknowledgement=IRREVERSIBLE_ACKNOWLEDGEMENT,
            now=NOW + timedelta(days=1),
        )
        return result.state.value

    with ThreadPoolExecutor(max_workers=10) as executor:
        states = tuple(executor.map(commit, range(20)))
    assert states == ("COMMITTED",) * 20


def test_quarantine_and_restore_cli_accept_exact_plan_and_batch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose the reversible lifecycle through explicit named CLI values."""
    workspace, policy, _stored = _candidate_workspace(tmp_path)
    plan = MaintenanceService(workspace.maintenance_store, workspace.catalog).plan(
        policy=policy,
        now=NOW,
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")
    assert (
        main(
            [
                "storage-quarantine",
                "--plan",
                str(plan_path),
                "--store",
                str(workspace.root),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    batch_id = str(payload["data"]["batch_id"])
    assert (
        main(
            [
                "storage-restore",
                "--batch",
                batch_id,
                "--store",
                str(workspace.root),
                "--json",
            ]
        )
        == 0
    )
    restored = json.loads(capsys.readouterr().out)
    assert restored["data"]["state"] == "RESTORED"
