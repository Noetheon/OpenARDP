"""Foreground recovery, scan reconciliation and bounded ingestion-job orchestration."""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep
from uuid import UUID

from openardp.domain.storage import Job, JobState
from openardp.domain.watcher import WatchConfig, WatchCycleResult, WatchScan, watch_retry_delay_ms
from openardp.ports.catalog import InvalidJobTransition, LeaseConflict
from openardp.ports.watcher import (
    WatchCancellationObserved,
    WatchIngestionRunner,
    WatchPermanentIngestion,
    WatchRetryableIngestion,
    WatchRuntimeCatalog,
    WatchScanner,
    WatchTargetChanged,
)

_JOB_LEASE = timedelta(minutes=5)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _owner_id() -> str:
    return f"openardp-watch-{os.getpid()}"


def _lease_token() -> str:
    return secrets.token_hex(32)


class WatcherService:
    """Run explicit local watcher cycles through provider-neutral boundaries."""

    def __init__(
        self,
        catalog: WatchRuntimeCatalog,
        scanner: WatchScanner,
        runner: WatchIngestionRunner,
        *,
        workspace_root: Path,
        clock: Callable[[], datetime] = _utc_now,
        sleeper: Callable[[float], None] = sleep,
        owner_id_factory: Callable[[], str] = _owner_id,
        lease_token_factory: Callable[[], str] = _lease_token,
    ) -> None:
        """Bind local authority and injectable time/process nondeterminism."""
        self._catalog = catalog
        self._scanner = scanner
        self._runner = runner
        self._workspace_root = workspace_root
        self._clock = clock
        self._sleeper = sleeper
        self._owner_id_factory = owner_id_factory
        self._lease_token_factory = lease_token_factory

    def run_cycle(self, root_path: Path, *, config: WatchConfig) -> WatchCycleResult:
        """Recover, reconcile and process bounded jobs for one explicit root."""
        admitted = self._scanner.admit(
            root_path,
            workspace=self._workspace_root,
            config=config,
        )
        registered_at = self._clock()
        registered = self._catalog.register_watch_root(admitted, now=registered_at)
        recovery = self._catalog.recover_expired_jobs(now=self._clock())
        started_at = self._clock()
        scan = self._scanner.scan(
            registered.authority,
            started_at=started_at,
            completed_at=started_at,
        )
        completed_at = self._clock()
        if completed_at < started_at:
            raise InvalidJobTransition("watch scan clock moved backward")
        scan = WatchScan(
            root_id=scan.root_id,
            started_at=scan.started_at,
            completed_at=completed_at,
            complete=scan.complete,
            reason=scan.reason,
            entries=scan.entries,
        )
        reconciliation = self._catalog.reconcile_watch_scan(
            registered.authority.root_id,
            scan,
            now=self._clock(),
        )
        succeeded: list[UUID] = []
        retried: list[UUID] = []
        failed: list[UUID] = []
        cancelled: list[UUID] = []
        for _index in range(config.max_jobs_per_cycle):
            outcome = self._run_one(registered.authority.root_id, config=config)
            if outcome is None:
                break
            job_id, state = outcome
            if state is JobState.SUCCEEDED:
                succeeded.append(job_id)
            elif state is JobState.QUEUED:
                retried.append(job_id)
            elif state is JobState.CANCELLED:
                cancelled.append(job_id)
            else:
                failed.append(job_id)
        return WatchCycleResult(
            reconciliation=reconciliation,
            recovery=recovery,
            succeeded_job_ids=tuple(sorted(succeeded, key=str)),
            retried_job_ids=tuple(sorted(retried, key=str)),
            failed_job_ids=tuple(sorted(failed, key=str)),
            cancelled_job_ids=tuple(sorted(cancelled, key=str)),
        )

    def run_forever(
        self,
        root_path: Path,
        *,
        config: WatchConfig,
        stop: Callable[[], bool],
    ) -> None:
        """Repeat foreground cycles until an explicit local stop signal."""
        while not stop():
            self.run_cycle(root_path, config=config)
            if not stop():
                self._sleeper(config.poll_ms / 1_000)

    def _run_one(
        self,
        root_id: str,
        *,
        config: WatchConfig,
    ) -> tuple[UUID, JobState] | None:
        owner_id = self._owner_id_factory()
        token = self._lease_token_factory()
        now = self._clock()
        lease = self._catalog.claim_watch_job(
            root_id,
            owner_id=owner_id,
            lease_token=token,
            now=now,
            lease_until=now + _JOB_LEASE,
        )
        if lease is None:
            return None
        job_id = lease.job.job_id
        try:
            target = self._catalog.get_watch_target(job_id)
            root = self._catalog.get_watch_root(root_id)
            if target is None or root is None or target.root_id != root_id:
                raise WatchPermanentIngestion("watch target is unavailable")
            path = self._scanner.revalidate_target(root.authority, target)
            self._raise_if_cancelled(job_id, owner_id=owner_id, token=token)
            self._runner.ingest(
                path,
                profile=target.parser_profile,
                cancelled=lambda: self._cancellation_requested(job_id),
            )
            current = self._required_job(job_id)
            if current.cancellation_requested_at is not None:
                terminal = self._catalog.acknowledge_job_cancellation(
                    job_id,
                    owner_id=owner_id,
                    lease_token=token,
                    expected_revision=current.revision,
                    now=self._clock(),
                )
            else:
                terminal = self._catalog.complete_job(
                    job_id,
                    owner_id=owner_id,
                    lease_token=token,
                    expected_revision=current.revision,
                    now=self._clock(),
                )
        except WatchCancellationObserved:
            current = self._required_job(job_id)
            terminal = self._catalog.acknowledge_job_cancellation(
                job_id,
                owner_id=owner_id,
                lease_token=token,
                expected_revision=current.revision,
                now=self._clock(),
            )
        except (WatchTargetChanged, WatchRetryableIngestion):
            terminal = self._fail_job(
                job_id,
                owner_id=owner_id,
                token=token,
                config=config,
                retryable=True,
                failure_code="source_changed",
            )
        except WatchPermanentIngestion:
            terminal = self._fail_job(
                job_id,
                owner_id=owner_id,
                token=token,
                config=config,
                retryable=False,
                failure_code="ingestion_failed",
            )
        except (InvalidJobTransition, LeaseConflict):
            current = self._required_job(job_id)
            if current.state is JobState.CANCELLED:
                terminal = current
            elif current.cancellation_requested_at is not None:
                terminal = self._catalog.acknowledge_job_cancellation(
                    job_id,
                    owner_id=owner_id,
                    lease_token=token,
                    expected_revision=current.revision,
                    now=self._clock(),
                )
            else:
                raise
        except Exception:
            terminal = self._fail_job(
                job_id,
                owner_id=owner_id,
                token=token,
                config=config,
                retryable=False,
                failure_code="ingestion_failed",
            )
        return job_id, terminal.state

    def _fail_job(
        self,
        job_id: UUID,
        *,
        owner_id: str,
        token: str,
        config: WatchConfig,
        retryable: bool,
        failure_code: str,
    ) -> Job:
        current = self._required_job(job_id)
        if current.cancellation_requested_at is not None:
            return self._catalog.acknowledge_job_cancellation(
                job_id,
                owner_id=owner_id,
                lease_token=token,
                expected_revision=current.revision,
                now=self._clock(),
            )
        now = self._clock()
        retry_at = (
            now
            + timedelta(
                milliseconds=watch_retry_delay_ms(
                    config,
                    attempt_count=current.attempt_count,
                )
            )
            if retryable
            else None
        )
        return self._catalog.fail_job(
            job_id,
            owner_id=owner_id,
            lease_token=token,
            expected_revision=current.revision,
            now=now,
            retryable=retryable,
            failure_code=failure_code,
            retry_at=retry_at,
        )

    def _cancellation_requested(self, job_id: UUID) -> bool:
        job = self._catalog.get_job(job_id)
        return (
            job is None
            or job.state is JobState.CANCELLED
            or job.cancellation_requested_at is not None
        )

    def _raise_if_cancelled(self, job_id: UUID, *, owner_id: str, token: str) -> None:
        current = self._required_job(job_id)
        if current.cancellation_requested_at is None:
            return
        self._catalog.acknowledge_job_cancellation(
            job_id,
            owner_id=owner_id,
            lease_token=token,
            expected_revision=current.revision,
            now=self._clock(),
        )
        raise WatchCancellationObserved("watch job cancellation observed")

    def _required_job(self, job_id: UUID) -> Job:
        job = self._catalog.get_job(job_id)
        if job is None:
            raise WatchPermanentIngestion("watch job is unavailable")
        return job


__all__ = ["WatcherService"]
