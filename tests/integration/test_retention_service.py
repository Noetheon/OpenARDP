"""Conservative F013 inventory and deterministic dry-run service tests."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.maintenance import (
    InventoryLimits,
    QuarantineBatchState,
    RetentionClassification,
    RetentionPolicy,
)
from openardp.interfaces.cli import main
from openardp.ports.maintenance import AcknowledgementRequired, GraceActive
from openardp.services.maintenance import (
    IRREVERSIBLE_ACKNOWLEDGEMENT,
    MaintenanceService,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def test_old_unreferenced_object_has_stable_candidate_plan(tmp_path: Path) -> None:
    """Select only a verified old unreferenced object with stable semantic identity."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"candidate",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = NOW - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    policy = RetentionPolicy(limits=InventoryLimits(max_entries=10, max_bytes=100))

    report = service.inventory(policy=policy, now=NOW)
    assert report.explanations[0].classification is RetentionClassification.CANDIDATE
    plans = tuple(service.plan(policy=policy, now=NOW) for _ in range(20))
    assert {plan.plan_id for plan in plans} == {plans[0].plan_id}
    assert tuple(item.item.object_id for item in plans[0].candidates) == (stored.object_id,)


def test_hundred_repeated_and_twenty_concurrent_inventories_are_identical(
    tmp_path: Path,
) -> None:
    """Prove stable complete classification under repeated and concurrent readers."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    workspace.object_store.put_chunks((b"stable-inventory",))
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    policy = RetentionPolicy(limits=InventoryLimits(max_entries=10, max_bytes=100))

    repeated = tuple(
        service.inventory(policy=policy, now=NOW).model_dump(mode="json") for _ in range(100)
    )
    assert len({json.dumps(item, sort_keys=True) for item in repeated}) == 1

    with ThreadPoolExecutor(max_workers=10) as executor:
        concurrent = tuple(
            executor.map(
                lambda _: service.inventory(policy=policy, now=NOW).model_dump(mode="json"),
                range(20),
            )
        )
    assert len({json.dumps(item, sort_keys=True) for item in concurrent}) == 1
    assert concurrent[0] == repeated[0]


def test_active_hold_overrides_old_unreferenced_candidate(tmp_path: Path) -> None:
    """Explicit protection dominates age and unreferenced state."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"held",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = NOW - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    service.add_hold(stored.object_id, reason="operator_hold", now=NOW)
    policy = RetentionPolicy(limits=InventoryLimits(max_entries=10, max_bytes=100))
    assert service.plan(policy=policy, now=NOW).candidates == ()


def test_commit_requires_exact_ack_and_full_grace_boundary(tmp_path: Path) -> None:
    """Delete nothing at 23:59:59 and only the named object at exact minimum grace."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"expired",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = NOW - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))
    policy = RetentionPolicy(
        quarantine_grace_seconds=86_400,
        limits=InventoryLimits(max_entries=10, max_bytes=100),
    )
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)

    with pytest.raises(GraceActive):
        service.commit(
            batch.batch_id,
            acknowledgement=IRREVERSIBLE_ACKNOWLEDGEMENT,
            now=NOW + timedelta(hours=24) - timedelta(seconds=1),
        )
    assert workspace.maintenance_store.inventory(policy.limits).quarantined
    with pytest.raises(AcknowledgementRequired):
        service.commit(batch.batch_id, acknowledgement="yes", now=NOW + timedelta(days=1))

    committed = service.commit(
        batch.batch_id,
        acknowledgement=IRREVERSIBLE_ACKNOWLEDGEMENT,
        now=NOW + timedelta(days=1),
    )
    assert committed.state is QuarantineBatchState.COMMITTED
    inventory = workspace.maintenance_store.inventory(policy.limits)
    assert inventory.active == ()
    assert inventory.quarantined == ()


def test_new_hold_at_commit_restores_conflict_instead_of_removing(tmp_path: Path) -> None:
    """Final protection facts always win over an earlier reclamation plan."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"later-held",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = NOW - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))
    policy = RetentionPolicy(
        quarantine_grace_seconds=86_400,
        limits=InventoryLimits(max_entries=10, max_bytes=100),
    )
    service = MaintenanceService(workspace.maintenance_store, workspace.catalog)
    batch = service.quarantine(service.plan(policy=policy, now=NOW), now=NOW)
    service.add_hold(stored.object_id, reason="operator_hold", now=NOW + timedelta(hours=1))

    blocked = service.commit(
        batch.batch_id,
        acknowledgement=IRREVERSIBLE_ACKNOWLEDGEMENT,
        now=NOW + timedelta(days=1),
    )

    assert blocked.state is QuarantineBatchState.BLOCKED
    inventory = workspace.maintenance_store.inventory(policy.limits)
    assert inventory.quarantined == ()
    assert inventory.active[0].object_id == stored.object_id


def test_inventory_plan_and_hold_cli_are_body_and_path_free(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose exact maintenance handles without managed filesystem locations."""
    workspace = tmp_path / "private-workspace-name"
    assert main(["init", "--store", str(workspace)]) == 0
    captured = capsys.readouterr()
    assert "private-workspace-name" in captured.out
    opened = LocalWorkspace.open(workspace)
    stored = opened.object_store.put_chunks((b"PRIVATE-BODY",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = opened.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = datetime.now(UTC) - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))

    assert main(["storage-plan", "--store", str(workspace), "--json"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    encoded = json.dumps(payload)
    assert stored.object_id in encoded
    assert "PRIVATE-BODY" not in encoded
    assert "private-workspace-name" not in encoded

    assert (
        main(
            [
                "storage-hold",
                stored.object_id,
                "--store",
                str(workspace),
                "--json",
            ]
        )
        == 0
    )
    hold_payload = json.loads(capsys.readouterr().out)
    assert hold_payload["data"]["object_id"] == stored.object_id
