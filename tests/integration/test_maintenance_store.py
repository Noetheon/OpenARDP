"""Safe bounded active/quarantine filesystem maintenance tests."""

from __future__ import annotations

import os
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Lock

import pytest

from openardp.adapters.filesystem_maintenance import FilesystemMaintenanceStore
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.maintenance import InventoryLimits, ObjectLocation, StorageHealth
from openardp.ports.maintenance import InventoryOverflow

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def test_validate_only_store_inventory_reports_exact_old_object(tmp_path: Path) -> None:
    """Hash and timestamp complete CAS bytes without exposing their path."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"candidate",))
    digest = stored.object_id.removeprefix("sha256:")
    leaf = workspace.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    old = NOW - timedelta(days=2)
    os.utime(leaf, (old.timestamp(), old.timestamp()))

    inventory = workspace.maintenance_store.inventory(
        InventoryLimits(max_entries=10, max_bytes=100)
    )
    assert len(inventory.active) == 1
    assert inventory.active[0].object_id == stored.object_id
    assert inventory.active[0].location is ObjectLocation.ACTIVE
    assert inventory.active[0].modified_at == old
    assert inventory.anomalies == ()


def test_inventory_limit_plus_one_returns_no_partial_value(tmp_path: Path) -> None:
    """Overflow raises before any authoritative inventory can escape."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    workspace.object_store.put_chunks((b"one",))
    workspace.object_store.put_chunks((b"two",))
    with pytest.raises(InventoryOverflow):
        workspace.maintenance_store.inventory(InventoryLimits(max_entries=1, max_bytes=100))


def test_exact_transition_is_no_overwrite_and_idempotent(tmp_path: Path) -> None:
    """Move one verified object through quarantine and back without byte drift."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"transition",))
    limits = InventoryLimits(max_entries=10, max_bytes=100)

    workspace.maintenance_store.transition(
        stored.object_id,
        to_quarantine=True,
        byte_length=stored.byte_length,
    )
    workspace.maintenance_store.transition(
        stored.object_id,
        to_quarantine=True,
        byte_length=stored.byte_length,
    )
    quarantined = workspace.maintenance_store.inventory(limits)
    assert quarantined.active == ()
    assert quarantined.quarantined[0].object_id == stored.object_id

    workspace.maintenance_store.transition(
        stored.object_id,
        to_quarantine=False,
        byte_length=stored.byte_length,
    )
    restored = workspace.maintenance_store.inventory(limits)
    assert restored.quarantined == ()
    assert restored.active[0].object_id == stored.object_id


@pytest.mark.skipif(os.name == "nt", reason="POSIX hard-link race regression")
def test_concurrent_posix_links_converge_to_one_exact_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accept only the exact winner when callers race at hard-link publication."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"contended-transition",))
    workspace.maintenance_store.transition(
        stored.object_id,
        to_quarantine=True,
        byte_length=stored.byte_length,
    )
    workspace.maintenance_store.transition(
        stored.object_id,
        to_quarantine=False,
        byte_length=stored.byte_length,
    )
    real_link = os.link
    barrier = Barrier(10)

    def contested_link(
        source: os.PathLike[str],
        destination: os.PathLike[str],
        *,
        follow_symlinks: bool = True,
    ) -> None:
        barrier.wait()
        real_link(source, destination, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "link", contested_link)

    def quarantine(_: int) -> None:
        workspace.maintenance_store.transition(
            stored.object_id,
            to_quarantine=True,
            byte_length=stored.byte_length,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        tuple(executor.map(quarantine, range(10)))

    inventory = workspace.maintenance_store.inventory(
        InventoryLimits(max_entries=10, max_bytes=100)
    )
    assert inventory.active == ()
    assert inventory.quarantined[0].object_id == stored.object_id


def test_windows_transition_waits_for_delayed_destination_visibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bound a Windows rename race until the single destination becomes visible."""
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    destination.write_bytes(b"exact")
    real_lstat = Path.lstat
    destination_reads = 0

    def delayed_lstat(path: Path) -> os.stat_result:
        nonlocal destination_reads
        if path == destination:
            destination_reads += 1
            if destination_reads < 3:
                raise FileNotFoundError
        return real_lstat(path)

    monkeypatch.setattr("openardp.adapters.filesystem_maintenance.os.name", "nt")
    monkeypatch.setattr(Path, "lstat", delayed_lstat)

    destination_metadata, source_metadata = FilesystemMaintenanceStore._await_transition_metadata(
        source, destination
    )

    assert destination_metadata.st_size == 5
    assert source_metadata is None
    assert destination_reads == 3


def test_concurrent_exact_removals_converge_after_verified_unlink_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Converge transient Windows unlink conflicts to one exact winner."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"contended-removal",))
    workspace.maintenance_store.transition(
        stored.object_id,
        to_quarantine=True,
        byte_length=stored.byte_length,
    )
    digest = stored.object_id.removeprefix("sha256:")
    quarantine = workspace.root / "quarantine" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    real_unlink = Path.unlink
    barrier = Barrier(10)
    lock = Lock()
    calls = 0

    def contested_unlink(path: Path, missing_ok: bool = False) -> None:
        nonlocal calls
        if path == quarantine:
            barrier.wait()
            with lock:
                calls += 1
                if calls < barrier.parties:
                    raise PermissionError("synthetic sharing violation")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", contested_unlink)

    def remove(_: int) -> None:
        workspace.maintenance_store.remove(
            stored.object_id,
            byte_length=stored.byte_length,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        tuple(executor.map(remove, range(10)))

    inventory = workspace.maintenance_store.inventory(
        InventoryLimits(max_entries=10, max_bytes=100)
    )
    assert inventory.active == ()
    assert inventory.quarantined == ()


def test_storage_diagnostics_and_capacity_are_exact_at_reserve_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report logical categories and admit reserve-exact but reject reserve-minus-one."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    workspace.object_store.put_chunks((b"12345",))
    (workspace.root / "staging" / "owned.part").write_bytes(b"123")
    DiskUsage = namedtuple("DiskUsage", "total used free")
    free = 105
    monkeypatch.setattr(
        "openardp.adapters.filesystem_maintenance.shutil.disk_usage",
        lambda _path: DiskUsage(1_000, 895, free),
    )

    assert workspace.maintenance_store.capacity(5, 100).admitted is True
    assert workspace.maintenance_store.capacity(6, 100).admitted is False
    diagnostic = workspace.maintenance_store.diagnostics(
        reserve_bytes=100,
        observed_at=NOW,
        index_count=2,
        index_bytes=17,
    )
    categories = {item.name: item for item in diagnostic.categories}
    assert categories["active"].byte_count == 5
    assert categories["active"].count == 1
    assert categories["staging"].byte_count == 3
    assert categories["disposable_index"].byte_count == 17
    assert diagnostic.disk_free_bytes == free
    assert diagnostic.health is StorageHealth.INCONSISTENT
