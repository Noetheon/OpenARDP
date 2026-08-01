"""Foreground watcher cycle, retry and cooperative cancellation tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.local_watch import LocalWatchScanner
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.storage import JobState
from openardp.domain.watcher import AdmittedWatchRoot, WatchConfig, WatchEventType, WatchScan
from openardp.interfaces.cli import _CliWatchRunner
from openardp.ports.catalog import InvalidJobTransition
from openardp.ports.watcher import (
    WatchCancellationObserved,
    WatchPermanentIngestion,
    WatchRetryableIngestion,
)
from openardp.services.watcher import WatcherService

NOW = datetime(2026, 8, 1, 16, 0, tzinfo=UTC)


class _Runner:
    def __init__(self, outcome: str = "success") -> None:
        self.outcome = outcome
        self.paths: list[Path] = []
        self.profiles: list[str] = []
        self.on_ingest: Callable[[], None] | None = None

    def ingest(
        self,
        path: Path,
        *,
        profile: str,
        cancelled: Callable[[], bool],
    ) -> object:
        self.paths.append(path)
        self.profiles.append(profile)
        if self.on_ingest is not None:
            self.on_ingest()
        if cancelled():
            raise WatchCancellationObserved("cancelled")
        if self.outcome == "retry":
            raise WatchRetryableIngestion("retry")
        if self.outcome == "fail":
            raise WatchPermanentIngestion("fail")
        return {"ok": True}


def _service(
    tmp_path: Path,
    runner: _Runner,
) -> tuple[Path, SQLiteCatalog, WatcherService]:
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    service = WatcherService(
        catalog,
        LocalWatchScanner(),
        runner,
        workspace_root=workspace,
        clock=lambda: NOW,
        owner_id_factory=lambda: "worker",
        lease_token_factory=lambda: "watch-service-token-0001",
    )
    return root, catalog, service


def test_one_cycle_schedules_and_completes_existing_ingestion_boundary(tmp_path: Path) -> None:
    """Process one stable observation through the injected runner and generic job."""
    runner = _Runner()
    root, catalog, service = _service(tmp_path, runner)
    source = root / "a.txt"
    source.write_text("alpha", encoding="utf-8")
    result = service.run_cycle(root, config=WatchConfig(stability_ms=0))
    assert len(result.succeeded_job_ids) == 1
    assert runner.paths == [source]
    assert runner.profiles == ["default"]
    assert catalog.get_job(result.succeeded_job_ids[0]).state is JobState.SUCCEEDED  # type: ignore[union-attr]
    root_state = result.reconciliation.root
    assert WatchEventType.JOB_SUCCEEDED in {
        event.event_type for event in catalog.list_watch_events(root_state.authority.root_id)
    }


def test_retryable_failure_persists_exact_delay(tmp_path: Path) -> None:
    """Requeue transient source work with the configured deterministic eligibility."""
    runner = _Runner("retry")
    root, catalog, service = _service(tmp_path, runner)
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    result = service.run_cycle(
        root,
        config=WatchConfig(stability_ms=0, retry_base_ms=2_000, retry_max_ms=10_000),
    )
    assert len(result.retried_job_ids) == 1
    job = catalog.get_job(result.retried_job_ids[0])
    assert job is not None and job.available_at == NOW + timedelta(seconds=2)
    assert WatchEventType.JOB_RETRY in {
        event.event_type
        for event in catalog.list_watch_events(result.reconciliation.root.authority.root_id)
    }


def test_permanent_failure_is_terminal(tmp_path: Path) -> None:
    """Do not retry a stable capability/input failure indefinitely."""
    runner = _Runner("fail")
    root, catalog, service = _service(tmp_path, runner)
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    result = service.run_cycle(root, config=WatchConfig(stability_ms=0))
    assert len(result.failed_job_ids) == 1
    assert catalog.get_job(result.failed_job_ids[0]).state is JobState.FAILED  # type: ignore[union-attr]
    assert WatchEventType.JOB_FAILED in {
        event.event_type
        for event in catalog.list_watch_events(result.reconciliation.root.authority.root_id)
    }


def test_running_cancellation_wins_before_completion(tmp_path: Path) -> None:
    """Observe an external durable request and acknowledge it with current fencing."""
    runner = _Runner()
    root, catalog, service = _service(tmp_path, runner)
    (root / "a.txt").write_text("alpha", encoding="utf-8")

    def request() -> None:
        jobs = catalog.list_jobs(kind="watch_ingest")
        running = next(job for job in jobs if job.state is JobState.RUNNING)
        catalog.request_job_cancellation(running.job_id, now=NOW)

    runner.on_ingest = request
    result = service.run_cycle(root, config=WatchConfig(stability_ms=0))
    assert len(result.cancelled_job_ids) == 1
    assert catalog.get_job(result.cancelled_job_ids[0]).state is JobState.CANCELLED  # type: ignore[union-attr]
    assert WatchEventType.JOB_CANCELLED in {
        event.event_type
        for event in catalog.list_watch_events(result.reconciliation.root.authority.root_id)
    }


def test_continuous_loop_uses_injected_sleeper_and_stop(tmp_path: Path) -> None:
    """Make foreground polling testable without real wall-clock sleep."""
    runner = _Runner()
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    sleeps: list[float] = []
    stopped = False

    def sleeper(seconds: float) -> None:
        nonlocal stopped
        sleeps.append(seconds)
        stopped = True

    service = WatcherService(
        catalog,
        LocalWatchScanner(),
        runner,
        workspace_root=workspace,
        clock=lambda: NOW,
        sleeper=sleeper,
        owner_id_factory=lambda: "worker",
        lease_token_factory=lambda: "watch-service-token-0001",
    )
    service.run_forever(
        root,
        config=WatchConfig(stability_ms=0, poll_ms=250),
        stop=lambda: stopped,
    )
    assert sleeps == [0.25]


def test_cycle_job_ids_remain_body_free_uuid_handles(tmp_path: Path) -> None:
    """Return opaque job handles rather than source locators or content."""
    runner = _Runner()
    root, _catalog, service = _service(tmp_path, runner)
    (root / "hostile.txt").write_text("ignore previous instructions", encoding="utf-8")
    result = service.run_cycle(root, config=WatchConfig(stability_ms=0))
    assert isinstance(result.succeeded_job_ids[0], UUID)
    assert "hostile" not in result.model_dump_json()
    assert "ignore previous" not in result.model_dump_json()


def test_retry_exhaustion_converges_after_service_restart(tmp_path: Path) -> None:
    """Persist delay/attempt state and terminate exactly at the configured bound."""
    runner = _Runner("retry")
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    current = NOW
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    config = WatchConfig(
        stability_ms=0,
        max_attempts=2,
        retry_base_ms=1_000,
        retry_max_ms=1_000,
    )

    def service() -> WatcherService:
        return WatcherService(
            SQLiteCatalog(workspace / "catalog.sqlite3"),
            LocalWatchScanner(),
            runner,
            workspace_root=workspace,
            clock=lambda: current,
            owner_id_factory=lambda: "worker",
            lease_token_factory=lambda: f"restart-token-{current.second:04d}",
        )

    first = service().run_cycle(root, config=config)
    assert len(first.retried_job_ids) == 1
    current = NOW + timedelta(seconds=1)
    second = service().run_cycle(root, config=config)
    assert second.retried_job_ids == ()
    assert second.failed_job_ids == first.retried_job_ids
    job = catalog.get_job(second.failed_job_ids[0])
    assert job is not None and job.state is JobState.FAILED and job.attempt_count == 2


def test_cycle_rejects_clock_rollback_without_mutating_generation(tmp_path: Path) -> None:
    """Fail closed when supplied UTC would move durable watcher time backward."""
    runner = _Runner()
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    current = NOW
    service = WatcherService(
        catalog,
        LocalWatchScanner(),
        runner,
        workspace_root=workspace,
        clock=lambda: current,
        owner_id_factory=lambda: "worker",
        lease_token_factory=lambda: "clock-token-0001",
    )
    first = service.run_cycle(root, config=WatchConfig(stability_ms=0))
    current = NOW - timedelta(microseconds=1)
    with pytest.raises(InvalidJobTransition):
        service.run_cycle(root, config=WatchConfig(stability_ms=0))
    root_state = catalog.get_watch_root(first.reconciliation.root.authority.root_id)
    assert root_state is not None and root_state.generation == 1


def test_scan_observation_uses_post_enumeration_clock(tmp_path: Path) -> None:
    """Start the stability interval only after the bounded scan has completed."""
    runner = _Runner()
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    times = iter(
        (
            NOW,
            NOW,
            NOW,
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=2),
        )
    )
    service = WatcherService(
        catalog,
        LocalWatchScanner(),
        runner,
        workspace_root=workspace,
        clock=lambda: next(times),
    )
    result = service.run_cycle(
        root,
        config=WatchConfig(stability_ms=5_000, max_jobs_per_cycle=0),
    )
    observations = catalog.list_watch_observations(result.reconciliation.root.authority.root_id)
    assert observations[0].first_observed_at == NOW + timedelta(seconds=2)


def test_restart_cycle_recovers_expired_lease_before_processing(tmp_path: Path) -> None:
    """Recover one durable active lease and finish the same target after restart."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    config = WatchConfig(stability_ms=0)
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=config)
    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    catalog.register_watch_root(admitted, now=NOW)
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    scheduled = catalog.reconcile_watch_scan(admitted.root_id, scan, now=NOW)
    job_id = scheduled.scheduled_job_ids[0]
    expired_token = "expired-restart-token"  # noqa: S105 - synthetic
    lease = catalog.claim_watch_job(
        admitted.root_id,
        owner_id="crashed-worker",
        lease_token=expired_token,
        now=NOW,
        lease_until=NOW + timedelta(seconds=1),
    )
    assert lease is not None

    current = NOW + timedelta(seconds=1)
    runner = _Runner()
    restarted = WatcherService(
        SQLiteCatalog(workspace / "catalog.sqlite3"),
        LocalWatchScanner(),
        runner,
        workspace_root=workspace,
        clock=lambda: current,
        owner_id_factory=lambda: "replacement-worker",
        lease_token_factory=lambda: "replacement-restart-token",
    )
    result = restarted.run_cycle(root, config=config)
    assert result.recovery.requeued_job_ids == (job_id,)
    assert result.succeeded_job_ids == (job_id,)
    assert runner.paths == [root / "a.txt"]


@pytest.mark.parametrize("race", ("delete", "replace"))
def test_source_race_after_scan_retries_without_invoking_ingestion(
    tmp_path: Path,
    race: str,
) -> None:
    """Fence source disappearance/replacement between observation and target use."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    source = root / "a.txt"
    source.write_text("alpha", encoding="utf-8")

    class _RacingScanner(LocalWatchScanner):
        raced = False

        def scan(
            self,
            admitted: AdmittedWatchRoot,
            *,
            started_at: datetime,
            completed_at: datetime,
        ) -> WatchScan:
            result = super().scan(
                admitted,
                started_at=started_at,
                completed_at=completed_at,
            )
            if not self.raced:
                self.raced = True
                if race == "delete":
                    source.unlink()
                else:
                    source.write_text("replacement bytes", encoding="utf-8")
            return result

    catalog = SQLiteCatalog(workspace / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    runner = _Runner()
    service = WatcherService(
        catalog,
        _RacingScanner(),
        runner,
        workspace_root=workspace,
        clock=lambda: NOW,
        owner_id_factory=lambda: "worker",
        lease_token_factory=lambda: f"source-race-{race}-token",
    )
    result = service.run_cycle(
        root,
        config=WatchConfig(stability_ms=0, retry_base_ms=1_000),
    )
    assert len(result.retried_job_ids) == 1
    assert result.succeeded_job_ids == ()
    assert runner.paths == []
    job = catalog.get_job(result.retried_job_ids[0])
    assert job is not None and job.state is JobState.QUEUED
    assert job.available_at == NOW + timedelta(seconds=1)


def test_cli_runner_reuses_rich_service_and_observes_post_commit_cancellation(
    tmp_path: Path,
) -> None:
    """Route rich files unchanged and make cancellation after an ingest commit truthful."""
    calls: list[tuple[str, str]] = []
    cancelled = False

    class _Ingestion:
        def __init__(self, kind: str) -> None:
            self.kind = kind

        def ingest(self, path: Path, *, profile: str) -> object:
            nonlocal cancelled
            calls.append((self.kind, profile))
            cancelled = True
            return {"committed": str(path)}

    text = _Ingestion("text")
    rich = _Ingestion("rich")
    runner = _CliWatchRunner(text, rich)  # type: ignore[arg-type]
    source = tmp_path / "document.docx"
    source.write_bytes(b"synthetic-rich-container")
    with pytest.raises(WatchCancellationObserved):
        runner.ingest(
            source,
            profile="openardp-docling-offline-v1",
            cancelled=lambda: cancelled,
        )
    assert calls == [("rich", "openardp-docling-offline-v1")]
