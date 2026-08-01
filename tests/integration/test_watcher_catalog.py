"""Atomic durable watch reconciliation, stability and backpressure tests."""

from __future__ import annotations

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openardp.adapters.local_watch import LocalWatchScanner
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.storage import JobEventType, JobState
from openardp.domain.watcher import (
    WatchConfig,
    WatchEventType,
    WatchObservationState,
    WatchReconciliation,
    WatchScan,
    WatchScanReason,
)
from openardp.ports.catalog import JobConflict

NOW = datetime(2026, 8, 1, 15, 0, tzinfo=UTC)


class _FaultCatalog(SQLiteCatalog):
    """Inject one exact catalog fault without changing production transactions."""

    fail_at: str | None = None

    def _fault_point(self, point: str) -> None:
        if point == self.fail_at:
            raise RuntimeError(f"synthetic fault at {point}")


def _setup(
    tmp_path: Path,
    *,
    config: WatchConfig,
) -> tuple[Path, Path, LocalWatchScanner, SQLiteCatalog, str]:
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=config)
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    registered = catalog.register_watch_root(admitted, now=NOW)
    return workspace, root, scanner, catalog, registered.authority.root_id


def _scan(
    scanner: LocalWatchScanner,
    catalog: SQLiteCatalog,
    root_id: str,
    at: datetime,
) -> WatchReconciliation:
    root = catalog.get_watch_root(root_id)
    assert root is not None
    scan = scanner.scan(root.authority, started_at=at, completed_at=at)
    return catalog.reconcile_watch_scan(root_id, scan, now=at)


def test_candidate_becomes_one_stable_exact_job_at_boundary(tmp_path: Path) -> None:
    """Schedule no early work and exactly one job at the configured boundary."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=2_000),
    )
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    first = _scan(scanner, catalog, root_id, NOW)
    assert first.candidate_count == 1
    assert first.scheduled_job_ids == ()
    early = _scan(scanner, catalog, root_id, NOW + timedelta(milliseconds=1_999))
    assert early.scheduled_job_ids == ()
    stable = _scan(scanner, catalog, root_id, NOW + timedelta(milliseconds=2_000))
    assert len(stable.scheduled_job_ids) == 1
    repeated = _scan(scanner, catalog, root_id, NOW + timedelta(milliseconds=3_000))
    assert repeated.scheduled_job_ids == ()
    job_id = stable.scheduled_job_ids[0]
    target = catalog.get_watch_target(job_id)
    assert target is not None and target.relative_locator == "a.txt"
    assert catalog.get_job(job_id).state is JobState.QUEUED  # type: ignore[union-attr]


def test_root_registration_is_idempotent_and_rejects_identity_conflict(tmp_path: Path) -> None:
    """Reuse exact authority and fail closed if the same root id carries different facts."""
    _workspace, _root, _scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(),
    )
    registered = catalog.get_watch_root(root_id)
    assert registered is not None
    assert catalog.register_watch_root(registered.authority, now=NOW) == registered
    conflicting = registered.authority.model_copy(update={"device_id": "conflicting-device"})
    with pytest.raises(JobConflict):
        catalog.register_watch_root(conflicting, now=NOW)


def test_observation_row_fingerprint_detects_catalog_tampering(tmp_path: Path) -> None:
    """Recompute the complete mutable observation row before returning it."""
    workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0),
    )
    (root / "a.txt").write_text("a", encoding="utf-8")
    _scan(scanner, catalog, root_id, NOW)
    with sqlite3.connect(workspace / "catalog.sqlite3") as connection:
        connection.execute(
            "UPDATE watch_observations SET row_fingerprint = ? WHERE root_id = ?",
            ("sha256:" + "f" * 64, root_id),
        )
        connection.commit()
    with pytest.raises(ValueError, match="fingerprint"):
        catalog.list_watch_observations(root_id)


def test_concurrent_identical_reconciliation_converges_to_one_target(tmp_path: Path) -> None:
    """Use catalog serialization and canonical identity as the race backstop."""
    workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0),
    )
    (root / "same.txt").write_text("same", encoding="utf-8")
    registered = catalog.get_watch_root(root_id)
    assert registered is not None
    scan = scanner.scan(registered.authority, started_at=NOW, completed_at=NOW)

    def reconcile(_: int) -> tuple[str, ...]:
        result = SQLiteCatalog(workspace / "catalog.sqlite3").reconcile_watch_scan(
            root_id,
            scan,
            now=NOW,
        )
        return tuple(str(value) for value in result.scheduled_job_ids)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(reconcile, range(20)))
    scheduled = {value for result in results for value in result}
    assert len(scheduled) == 1
    observations = catalog.list_watch_observations(root_id)
    assert len(observations) == 1
    assert observations[0].last_scheduled_key is not None
    for offset in range(100):
        repeated = _scan(scanner, catalog, root_id, NOW + timedelta(seconds=offset + 1))
        assert repeated.scheduled_job_ids == ()
    with sqlite3.connect(workspace / "catalog.sqlite3") as connection:
        assert connection.execute(
            "SELECT count(*) FROM jobs WHERE kind = 'watch_ingest'"
        ).fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM watch_job_targets").fetchone() == (1,)


def test_incomplete_scan_changes_only_rescan_state(tmp_path: Path) -> None:
    """Never interpret partial observations as additions or deletions."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0),
    )
    (root / "a.txt").write_text("a", encoding="utf-8")
    complete = _scan(scanner, catalog, root_id, NOW)
    before = catalog.list_watch_observations(root_id)
    incomplete = WatchScan(
        root_id=root_id,
        started_at=NOW + timedelta(seconds=1),
        completed_at=NOW + timedelta(seconds=1),
        complete=False,
        reason=WatchScanReason.OVERFLOW,
    )
    result = catalog.reconcile_watch_scan(
        root_id,
        incomplete,
        now=NOW + timedelta(seconds=1),
    )
    assert not result.complete and result.root.rescan_required
    assert result.root.generation == complete.root.generation
    assert catalog.list_watch_observations(root_id) == before


def test_delete_tombstones_without_removing_job_or_target(tmp_path: Path) -> None:
    """Preserve immutable scheduled history when a source locator disappears."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0),
    )
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    scheduled = _scan(scanner, catalog, root_id, NOW)
    job_id = scheduled.scheduled_job_ids[0]
    source.unlink()
    deleted = _scan(scanner, catalog, root_id, NOW + timedelta(seconds=1))
    assert deleted.tombstone_count == 1
    observation = catalog.list_watch_observations(root_id)[0]
    assert observation.state is WatchObservationState.TOMBSTONED
    assert observation.fingerprint is None
    assert catalog.get_job(job_id) is not None
    assert catalog.get_watch_target(job_id) is not None
    assert WatchEventType.TOMBSTONED in {
        event.event_type for event in catalog.list_watch_events(root_id)
    }


def test_unique_rename_is_hint_only_and_new_locator_has_fresh_lifecycle(tmp_path: Path) -> None:
    """Tombstone the old path and debounce the new path despite an unambiguous inode move."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=1_000),
    )
    source = root / "old.txt"
    source.write_text("same bytes", encoding="utf-8")
    _scan(scanner, catalog, root_id, NOW)
    _scan(scanner, catalog, root_id, NOW + timedelta(seconds=1))
    source.rename(root / "new.txt")
    renamed = _scan(scanner, catalog, root_id, NOW + timedelta(seconds=2))
    assert renamed.candidate_count == 1
    observations = {
        item.relative_locator: item for item in catalog.list_watch_observations(root_id)
    }
    assert observations["old.txt"].state is WatchObservationState.TOMBSTONED
    assert observations["new.txt"].state is WatchObservationState.CANDIDATE
    events = catalog.list_watch_events(root_id)
    assert sum(event.event_type is WatchEventType.RENAME_HINT for event in events) == 1


def test_hard_link_ambiguity_emits_no_rename_hint_and_reappearance_reschedules(
    tmp_path: Path,
) -> None:
    """Degrade ambiguous identities to path facts and treat reappearance as new work."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0),
    )
    first = root / "a.txt"
    second = root / "b.txt"
    first.write_text("shared", encoding="utf-8")
    try:
        os.link(first, second)
    except OSError:
        pytest.skip("hard links are unavailable on this filesystem")
    initial = _scan(scanner, catalog, root_id, NOW)
    assert len(initial.scheduled_job_ids) == 2
    first.rename(root / "c.txt")
    _scan(scanner, catalog, root_id, NOW + timedelta(seconds=1))
    assert not any(
        event.event_type is WatchEventType.RENAME_HINT
        for event in catalog.list_watch_events(root_id)
    )
    (root / "c.txt").unlink()
    _scan(scanner, catalog, root_id, NOW + timedelta(seconds=2))
    (root / "c.txt").write_text("fresh", encoding="utf-8")
    reappeared = _scan(scanner, catalog, root_id, NOW + timedelta(seconds=3))
    assert len(reappeared.scheduled_job_ids) == 1
    observation = next(
        item
        for item in catalog.list_watch_observations(root_id)
        if item.relative_locator == "c.txt"
    )
    assert observation.state is WatchObservationState.STABLE
    assert any(
        event.event_type is WatchEventType.REAPPEARED
        for event in catalog.list_watch_events(root_id)
    )


def test_candidate_tombstone_and_reappearance_converge_across_restarts(
    tmp_path: Path,
) -> None:
    """Persist debounce and path lifecycle without relying on hard-link support."""
    workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=1_000),
    )
    source = root / "portable.txt"
    source.write_text("first", encoding="utf-8")
    first = _scan(scanner, catalog, root_id, NOW)
    assert first.candidate_count == 1 and first.scheduled_job_ids == ()

    restarted = SQLiteCatalog(workspace / "catalog.sqlite3")
    stable = _scan(scanner, restarted, root_id, NOW + timedelta(seconds=1))
    assert len(stable.scheduled_job_ids) == 1
    first_job = stable.scheduled_job_ids[0]
    source.unlink()

    restarted = SQLiteCatalog(workspace / "catalog.sqlite3")
    deleted = _scan(scanner, restarted, root_id, NOW + timedelta(seconds=2))
    assert deleted.tombstone_count == 1
    assert restarted.list_watch_observations(root_id)[0].state is WatchObservationState.TOMBSTONED

    source.write_text("second version", encoding="utf-8")
    restarted = SQLiteCatalog(workspace / "catalog.sqlite3")
    reappeared = _scan(scanner, restarted, root_id, NOW + timedelta(seconds=3))
    assert reappeared.candidate_count == 1 and reappeared.scheduled_job_ids == ()
    restarted = SQLiteCatalog(workspace / "catalog.sqlite3")
    restabilized = _scan(scanner, restarted, root_id, NOW + timedelta(seconds=4))
    assert len(restabilized.scheduled_job_ids) == 1
    assert restabilized.scheduled_job_ids[0] != first_job


def test_delayed_queue_and_backpressure_resume_after_catalog_restart(tmp_path: Path) -> None:
    """Retain delayed eligibility and rescan demand until capacity becomes available."""
    workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0, max_active_jobs=1),
    )
    (root / "a.txt").write_text("a", encoding="utf-8")
    (root / "b.txt").write_text("b", encoding="utf-8")
    first = _scan(scanner, catalog, root_id, NOW)
    assert len(first.scheduled_job_ids) == 1 and first.root.rescan_required
    token = "restart-backpressure-token"  # noqa: S105 - synthetic
    lease = catalog.claim_watch_job(
        root_id,
        owner_id="worker",
        lease_token=token,
        now=NOW,
        lease_until=NOW + timedelta(seconds=30),
    )
    assert lease is not None
    retry_at = NOW + timedelta(minutes=1)
    catalog.fail_job(
        lease.job.job_id,
        owner_id="worker",
        lease_token=token,
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=1),
        retryable=True,
        failure_code="source_changed",
        retry_at=retry_at,
    )

    restarted = SQLiteCatalog(workspace / "catalog.sqlite3")
    durable = restarted.get_job(lease.job.job_id)
    root_state = restarted.get_watch_root(root_id)
    assert durable is not None and durable.available_at == retry_at
    assert root_state is not None and root_state.rescan_required
    restarted.request_job_cancellation(lease.job.job_id, now=retry_at)
    converged = _scan(scanner, restarted, root_id, retry_at)
    assert len(converged.scheduled_job_ids) == 1
    assert not converged.root.rescan_required


def test_backpressure_marks_rescan_and_later_schedules_omitted_work(tmp_path: Path) -> None:
    """Retain unscheduled stable work until active capacity returns."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0, max_active_jobs=1),
    )
    (root / "a.txt").write_text("a", encoding="utf-8")
    (root / "b.txt").write_text("b", encoding="utf-8")
    first = _scan(scanner, catalog, root_id, NOW)
    assert len(first.scheduled_job_ids) == 1
    assert first.root.rescan_required
    catalog.request_job_cancellation(first.scheduled_job_ids[0], now=NOW)
    second = _scan(scanner, catalog, root_id, NOW + timedelta(seconds=1))
    assert len(second.scheduled_job_ids) == 1
    assert not second.root.rescan_required


def test_exact_entry_overflow_has_no_partial_truth_and_reduced_root_converges(
    tmp_path: Path,
) -> None:
    """Prove the SC-003 1,001-to-1,000 all-or-nothing recovery boundary."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0, max_entries=1_000, max_active_jobs=1_000),
    )
    for index in range(1_001):
        (root / f"{index:04d}.txt").touch()
    registered = catalog.get_watch_root(root_id)
    assert registered is not None
    overflow = scanner.scan(registered.authority, started_at=NOW, completed_at=NOW)
    assert not overflow.complete
    assert overflow.entries == ()
    first = catalog.reconcile_watch_scan(root_id, overflow, now=NOW)
    assert first.root.rescan_required and first.root.generation == 0
    assert catalog.list_watch_observations(root_id) == ()
    assert catalog.list_jobs(kind="watch_ingest") == ()

    (root / "1000.txt").unlink()
    converged = _scan(scanner, catalog, root_id, NOW + timedelta(seconds=1))
    assert converged.complete and converged.entry_count == 1_000
    assert len(converged.scheduled_job_ids) == 1_000
    assert not converged.root.rescan_required


def test_unsupported_entries_still_consume_the_scan_entry_bound(tmp_path: Path) -> None:
    """Keep unsupported names from bypassing the bounded-enumeration contract."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0, max_entries=1),
    )
    (root / "ignored-a.bin").touch()
    (root / "ignored-b.bin").touch()
    registered = catalog.get_watch_root(root_id)
    assert registered is not None
    scan = scanner.scan(registered.authority, started_at=NOW, completed_at=NOW)
    assert not scan.complete
    assert scan.reason is WatchScanReason.OVERFLOW
    assert scan.entries == ()


def test_schedule_event_failure_rolls_back_observation_job_target_and_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the complete reconciliation transaction atomic at the final event boundary."""
    _workspace, root, scanner, catalog, root_id = _setup(
        tmp_path,
        config=WatchConfig(stability_ms=0),
    )
    (root / "atomic.txt").write_text("atomic", encoding="utf-8")
    registered = catalog.get_watch_root(root_id)
    assert registered is not None
    scan = scanner.scan(registered.authority, started_at=NOW, completed_at=NOW)
    original = SQLiteCatalog._append_watch_event

    def fail_target_event(self: SQLiteCatalog, *args: object, **kwargs: object) -> None:
        if kwargs.get("event_type") is WatchEventType.TARGET_SCHEDULED:
            raise RuntimeError("synthetic watcher transaction fault")
        original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(SQLiteCatalog, "_append_watch_event", fail_target_event)
    with pytest.raises(RuntimeError, match="synthetic"):
        catalog.reconcile_watch_scan(root_id, scan, now=NOW)
    assert catalog.list_watch_observations(root_id) == ()
    assert catalog.list_jobs(kind="watch_ingest") == ()
    assert [event.event_type for event in catalog.list_watch_events(root_id)] == [
        WatchEventType.ROOT_REGISTERED
    ]


@pytest.mark.parametrize("point", ("after_watch_root", "after_watch_event"))
def test_root_registration_faults_leave_no_partial_authority(
    tmp_path: Path,
    point: str,
) -> None:
    """Rollback both the root row and its first event at either write boundary."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())
    catalog = _FaultCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    catalog.fail_at = point
    with pytest.raises(RuntimeError, match="synthetic"):
        catalog.register_watch_root(admitted, now=NOW)
    catalog.fail_at = None
    assert catalog.get_watch_root(admitted.root_id) is None


@pytest.mark.parametrize(
    "point",
    (
        "after_watch_observation",
        "after_watch_job",
        "after_watch_target",
        "before_watch_reconciliation_commit",
    ),
)
def test_reconciliation_fault_points_leave_no_partial_schedule(
    tmp_path: Path,
    point: str,
) -> None:
    """Rollback observation, job, target and terminal reconciliation boundaries."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig(stability_ms=0))
    catalog = _FaultCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    catalog.register_watch_root(admitted, now=NOW)
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    catalog.fail_at = point
    with pytest.raises(RuntimeError, match="synthetic"):
        catalog.reconcile_watch_scan(admitted.root_id, scan, now=NOW)
    catalog.fail_at = None
    assert catalog.list_watch_observations(admitted.root_id) == ()
    assert catalog.list_jobs(kind="watch_ingest") == ()
    assert [event.event_type for event in catalog.list_watch_events(admitted.root_id)] == [
        WatchEventType.ROOT_REGISTERED
    ]


def test_tombstone_fault_rolls_back_absence_and_generation(tmp_path: Path) -> None:
    """Retain the prior live observation if tombstone publication is interrupted."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig(stability_ms=0))
    catalog = _FaultCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    catalog.register_watch_root(admitted, now=NOW)
    initial = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    catalog.reconcile_watch_scan(admitted.root_id, initial, now=NOW)
    source.unlink()
    missing = scanner.scan(
        admitted,
        started_at=NOW + timedelta(seconds=1),
        completed_at=NOW + timedelta(seconds=1),
    )
    catalog.fail_at = "after_watch_tombstone"
    with pytest.raises(RuntimeError, match="synthetic"):
        catalog.reconcile_watch_scan(
            admitted.root_id,
            missing,
            now=NOW + timedelta(seconds=1),
        )
    catalog.fail_at = None
    observation = catalog.list_watch_observations(admitted.root_id)[0]
    assert observation.state is WatchObservationState.STABLE
    root_state = catalog.get_watch_root(admitted.root_id)
    assert root_state is not None and root_state.generation == 1


@pytest.mark.parametrize(
    "outcome",
    ("success", "retry", "failure", "queued_cancel", "running_cancel", "recovery"),
)
def test_watcher_job_outcome_event_faults_rollback_the_complete_transition(
    tmp_path: Path,
    outcome: str,
) -> None:
    """Keep job projection, job event and watcher event in one atomic transaction."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig(stability_ms=0))
    catalog = _FaultCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    catalog.register_watch_root(admitted, now=NOW)
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    scheduled = catalog.reconcile_watch_scan(admitted.root_id, scan, now=NOW)
    job_id = scheduled.scheduled_job_ids[0]
    before_watch_types = tuple(
        event.event_type for event in catalog.list_watch_events(admitted.root_id)
    )

    if outcome == "queued_cancel":
        catalog.fail_at = "after_watch_event"
        with pytest.raises(RuntimeError, match="synthetic"):
            catalog.request_job_cancellation(job_id, now=NOW + timedelta(seconds=1))
        expected_state = JobState.QUEUED
        expected_job_types = (JobEventType.ENQUEUED,)
    else:
        token = f"atomic-{outcome}-token"
        lease = catalog.claim_watch_job(
            admitted.root_id,
            owner_id="worker",
            lease_token=token,
            now=NOW,
            lease_until=NOW + timedelta(seconds=1),
        )
        assert lease is not None
        expected_state = JobState.RUNNING
        expected_job_types = (JobEventType.ENQUEUED, JobEventType.CLAIMED)
        if outcome == "running_cancel":
            requested = catalog.request_job_cancellation(
                job_id,
                now=NOW + timedelta(milliseconds=500),
            )
            expected_job_types += (JobEventType.CANCEL_REQUESTED,)
        catalog.fail_at = "after_watch_event"
        with pytest.raises(RuntimeError, match="synthetic"):
            if outcome == "success":
                catalog.complete_job(
                    job_id,
                    owner_id="worker",
                    lease_token=token,
                    expected_revision=lease.job.revision,
                    now=NOW + timedelta(milliseconds=500),
                )
            elif outcome in {"retry", "failure"}:
                catalog.fail_job(
                    job_id,
                    owner_id="worker",
                    lease_token=token,
                    expected_revision=lease.job.revision,
                    now=NOW + timedelta(milliseconds=500),
                    retryable=outcome == "retry",
                    failure_code="source_changed",
                    retry_at=(NOW + timedelta(seconds=2) if outcome == "retry" else None),
                )
            elif outcome == "running_cancel":
                catalog.acknowledge_job_cancellation(
                    job_id,
                    owner_id="worker",
                    lease_token=token,
                    expected_revision=requested.revision,
                    now=NOW + timedelta(milliseconds=750),
                )
            else:
                catalog.recover_expired_jobs(now=NOW + timedelta(seconds=1))

    catalog.fail_at = None
    job = catalog.get_job(job_id)
    assert job is not None and job.state is expected_state
    assert (
        tuple(event.event_type for event in catalog.list_job_events(job_id)) == expected_job_types
    )
    assert (
        tuple(event.event_type for event in catalog.list_watch_events(admitted.root_id))
        == before_watch_types
    )
