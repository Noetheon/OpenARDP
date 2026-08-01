"""Eligibility, cancellation and recovery tests for revision-9 catalog jobs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.storage import JobEventType, JobSpec, JobState
from openardp.domain.watcher import WatchConfig, watch_retry_delay_ms
from openardp.ports.catalog import InvalidJobTransition, LeaseConflict

NOW = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
JOB_A = UUID("018f7e6a-4c00-4000-8000-000000000021")
JOB_B = UUID("018f7e6a-4c00-4000-8000-000000000022")


def _catalog(path: Path) -> SQLiteCatalog:
    catalog = SQLiteCatalog(path)
    catalog.initialize(now=NOW)
    return catalog


def _create(catalog: SQLiteCatalog, job_id: UUID, *, available_at: datetime = NOW) -> None:
    catalog.create_job(
        JobSpec(
            job_id=job_id,
            kind="watch_ingest",
            deduplication_key=f"job:{job_id}",
            max_attempts=3,
            available_at=available_at,
            created_at=NOW,
        )
    )


def test_claim_skips_delayed_jobs_and_orders_eligible_work(tmp_path: Path) -> None:
    """Persist eligibility and never lease delayed work early."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    _create(catalog, JOB_A, available_at=NOW + timedelta(minutes=1))
    _create(catalog, JOB_B)

    lease = catalog.claim_job(
        kind="watch_ingest",
        owner_id="worker",
        lease_token="eligible-token-0001",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(seconds=30),
    )
    assert lease is not None and lease.job.job_id == JOB_B
    catalog.complete_job(
        JOB_B,
        owner_id="worker",
        lease_token="eligible-token-0001",  # noqa: S106 - synthetic
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=1),
    )
    assert (
        catalog.claim_job(
            kind="watch_ingest",
            owner_id="worker",
            lease_token="eligible-token-0002",  # noqa: S106 - synthetic
            now=NOW + timedelta(seconds=59),
            lease_until=NOW + timedelta(seconds=90),
        )
        is None
    )


def test_retry_persists_next_eligibility(tmp_path: Path) -> None:
    """Make delayed retry durable across a fresh catalog instance."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _catalog(path)
    _create(catalog, JOB_A)
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="retry-token-00001",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(seconds=30),
    )
    assert lease is not None
    retry_at = NOW + timedelta(minutes=5)
    queued = catalog.fail_job(
        JOB_A,
        owner_id="worker",
        lease_token="retry-token-00001",  # noqa: S106 - synthetic
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=1),
        retryable=True,
        failure_code="source_changed",
        retry_at=retry_at,
    )
    assert queued.available_at == retry_at
    assert (
        SQLiteCatalog(path).claim_job(
            kind=None,
            owner_id="other",
            lease_token="retry-token-00002",  # noqa: S106 - synthetic
            now=retry_at - timedelta(microseconds=1),
            lease_until=retry_at + timedelta(seconds=30),
        )
        is None
    )


def test_queued_cancellation_is_terminal_and_idempotent(tmp_path: Path) -> None:
    """Cancel queued work exactly once and prevent every future claim."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    _create(catalog, JOB_A)
    cancelled = catalog.request_job_cancellation(JOB_A, now=NOW + timedelta(seconds=1))
    assert cancelled.state is JobState.CANCELLED
    assert catalog.request_job_cancellation(JOB_A, now=NOW + timedelta(seconds=2)) == cancelled
    assert (
        catalog.claim_job(
            kind=None,
            owner_id="worker",
            lease_token="cancel-token-0001",  # noqa: S106 - synthetic
            now=NOW + timedelta(seconds=3),
            lease_until=NOW + timedelta(minutes=1),
        )
        is None
    )
    assert tuple(event.event_type for event in catalog.list_job_events(JOB_A)) == (
        JobEventType.ENQUEUED,
        JobEventType.CANCELLED,
    )


def test_running_cancellation_fences_stale_revision_and_requires_ack(tmp_path: Path) -> None:
    """Let the active owner observe a durable request without accepting stale work."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    _create(catalog, JOB_A)
    token = "running-cancel-token"  # noqa: S105 - synthetic
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token=token,
        now=NOW,
        lease_until=NOW + timedelta(minutes=1),
    )
    assert lease is not None
    requested = catalog.request_job_cancellation(JOB_A, now=NOW + timedelta(seconds=1))
    assert requested.state is JobState.RUNNING
    assert requested.cancellation_requested_at == NOW + timedelta(seconds=1)
    assert requested.revision == lease.job.revision + 1
    with pytest.raises((LeaseConflict, InvalidJobTransition)):
        catalog.complete_job(
            JOB_A,
            owner_id="worker",
            lease_token=token,
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=2),
        )
    with pytest.raises((LeaseConflict, InvalidJobTransition)):
        catalog.renew_job(
            JOB_A,
            owner_id="worker",
            lease_token=token,
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=2),
            lease_until=NOW + timedelta(minutes=2),
        )
    with pytest.raises((LeaseConflict, InvalidJobTransition)):
        catalog.fail_job(
            JOB_A,
            owner_id="worker",
            lease_token=token,
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=2),
            retryable=True,
            failure_code="source_changed",
        )
    cancelled = catalog.acknowledge_job_cancellation(
        JOB_A,
        owner_id="worker",
        lease_token=token,
        expected_revision=requested.revision,
        now=NOW + timedelta(seconds=2),
    )
    assert cancelled.state is JobState.CANCELLED


def test_expired_requested_job_recovers_to_cancelled(tmp_path: Path) -> None:
    """Make operator cancellation dominate retry after a worker crash."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    _create(catalog, JOB_A)
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="expiry-cancel-token",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(seconds=10),
    )
    assert lease is not None
    catalog.request_job_cancellation(JOB_A, now=NOW + timedelta(seconds=1))
    recovered = catalog.recover_expired_jobs(now=NOW + timedelta(seconds=10))
    assert recovered.cancelled_job_ids == (JOB_A,)
    assert catalog.get_job(JOB_A).state is JobState.CANCELLED  # type: ignore[union-attr]


def test_concurrent_queued_cancellation_converges(tmp_path: Path) -> None:
    """Serialize racing operator requests into one cancellation event."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _catalog(path)
    _create(catalog, JOB_A)

    def cancel(_: int) -> JobState:
        return (
            SQLiteCatalog(path)
            .request_job_cancellation(JOB_A, now=NOW + timedelta(seconds=1))
            .state
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        states = tuple(executor.map(cancel, range(20)))
    assert set(states) == {JobState.CANCELLED}
    assert (
        tuple(event.event_type for event in catalog.list_job_events(JOB_A)).count(
            JobEventType.CANCELLED
        )
        == 1
    )


def test_retry_schedule_through_exhaustion_and_one_hundred_early_claims(
    tmp_path: Path,
) -> None:
    """Exercise every configured delay and repeatedly prove early work is ineligible."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _catalog(path)
    config = WatchConfig(
        max_attempts=5,
        retry_base_ms=1_000,
        retry_max_ms=5_000,
    )
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="watch_ingest",
            deduplication_key="retry-exhaustion",
            max_attempts=config.max_attempts,
            created_at=NOW,
        )
    )
    current = NOW
    eligibility: list[datetime] = []
    for attempt in range(1, config.max_attempts + 1):
        token = f"retry-exhaustion-token-{attempt:02d}"
        lease = SQLiteCatalog(path).claim_job(
            kind="watch_ingest",
            owner_id="worker",
            lease_token=token,
            now=current,
            lease_until=current + timedelta(seconds=30),
        )
        assert lease is not None and lease.job.attempt_count == attempt
        delay_ms = watch_retry_delay_ms(config, attempt_count=attempt)
        retry_at = current + timedelta(milliseconds=delay_ms)
        transitioned = SQLiteCatalog(path).fail_job(
            JOB_A,
            owner_id="worker",
            lease_token=token,
            expected_revision=lease.job.revision,
            now=current,
            retryable=True,
            failure_code="source_changed",
            retry_at=retry_at,
        )
        if attempt == config.max_attempts:
            assert transitioned.state is JobState.FAILED
            break
        eligibility.append(transitioned.available_at)
        if attempt == 1:
            for index in range(100):
                assert (
                    SQLiteCatalog(path).claim_job(
                        kind="watch_ingest",
                        owner_id=f"early-{index}",
                        lease_token=f"early-claim-token-{index:03d}",
                        now=retry_at - timedelta(microseconds=1),
                        lease_until=retry_at + timedelta(seconds=30),
                    )
                    is None
                )
        current = retry_at
    assert eligibility == [
        NOW + timedelta(seconds=1),
        NOW + timedelta(seconds=3),
        NOW + timedelta(seconds=7),
        NOW + timedelta(seconds=12),
    ]


def test_twenty_running_cancellation_requests_fence_every_stale_transition(
    tmp_path: Path,
) -> None:
    """Converge racing RUNNING requests before one owner acknowledgement."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _catalog(path)
    _create(catalog, JOB_A)
    token = "running-race-token"  # noqa: S105 - synthetic
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token=token,
        now=NOW,
        lease_until=NOW + timedelta(minutes=1),
    )
    assert lease is not None

    def request(_: int) -> int:
        return (
            SQLiteCatalog(path)
            .request_job_cancellation(
                JOB_A,
                now=NOW + timedelta(seconds=1),
            )
            .revision
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        revisions = tuple(executor.map(request, range(20)))
    assert set(revisions) == {lease.job.revision + 1}
    for transition in ("renew", "complete", "fail"):
        with pytest.raises((LeaseConflict, InvalidJobTransition)):
            if transition == "renew":
                catalog.renew_job(
                    JOB_A,
                    owner_id="worker",
                    lease_token=token,
                    expected_revision=lease.job.revision,
                    now=NOW + timedelta(seconds=2),
                    lease_until=NOW + timedelta(minutes=2),
                )
            elif transition == "complete":
                catalog.complete_job(
                    JOB_A,
                    owner_id="worker",
                    lease_token=token,
                    expected_revision=lease.job.revision,
                    now=NOW + timedelta(seconds=2),
                )
            else:
                catalog.fail_job(
                    JOB_A,
                    owner_id="worker",
                    lease_token=token,
                    expected_revision=lease.job.revision,
                    now=NOW + timedelta(seconds=2),
                    retryable=True,
                    failure_code="source_changed",
                )
    current = catalog.get_job(JOB_A)
    assert current is not None
    terminal = catalog.acknowledge_job_cancellation(
        JOB_A,
        owner_id="worker",
        lease_token=token,
        expected_revision=current.revision,
        now=NOW + timedelta(seconds=2),
    )
    assert terminal.state is JobState.CANCELLED
    types = tuple(event.event_type for event in catalog.list_job_events(JOB_A))
    assert types.count(JobEventType.CANCEL_REQUESTED) == 1
    assert types.count(JobEventType.CANCELLED) == 1


def test_cancel_retried_queued_job_preserves_attempt_count_in_event(tmp_path: Path) -> None:
    """Keep body-free cancellation evidence truthful after a retry transition."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    _create(catalog, JOB_A)
    token = "retry-cancel-token"  # noqa: S105 - synthetic
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token=token,
        now=NOW,
        lease_until=NOW + timedelta(seconds=30),
    )
    assert lease is not None
    catalog.fail_job(
        JOB_A,
        owner_id="worker",
        lease_token=token,
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=1),
        retryable=True,
        failure_code="source_changed",
        retry_at=NOW + timedelta(seconds=2),
    )
    catalog.request_job_cancellation(JOB_A, now=NOW + timedelta(seconds=2))
    cancelled = catalog.list_job_events(JOB_A)[-1]
    assert cancelled.event_type is JobEventType.CANCELLED
    assert cancelled.attempt_count == 1
