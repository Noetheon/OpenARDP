"""Pure revision-9 eligibility and cancellation job invariants."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.storage import Job, JobEvent, JobEventType, JobSpec, JobState

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
JOB_ID = UUID("018f7e6a-4c00-4000-8000-000000000012")


def _job(**updates: object) -> Job:
    values: dict[str, object] = {
        "job_id": JOB_ID,
        "kind": "watch_ingest",
        "deduplication_key": "sha256:" + "a" * 64,
        "state": JobState.QUEUED,
        "attempt_count": 0,
        "max_attempts": 3,
        "revision": 0,
        "available_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(updates)
    return Job(**values)  # type: ignore[arg-type]


def test_job_spec_eligibility_cannot_precede_creation() -> None:
    """Reject eligibility facts that move before immutable request creation."""
    with pytest.raises(ValidationError, match="available_at"):
        JobSpec(
            job_id=JOB_ID,
            kind="watch_ingest",
            deduplication_key="sha256:" + "a" * 64,
            max_attempts=3,
            available_at=NOW - timedelta(microseconds=1),
            created_at=NOW,
        )


def test_cancelled_job_is_terminal_and_lease_free() -> None:
    """Model cancellation as a truthful terminal state, never a disguised failure."""
    cancelled = _job(
        state=JobState.CANCELLED,
        revision=1,
        updated_at=NOW + timedelta(seconds=1),
        terminal_at=NOW + timedelta(seconds=1),
    )
    assert cancelled.last_failure_code is None
    with pytest.raises(ValidationError, match="non-RUNNING"):
        _job(
            state=JobState.CANCELLED,
            active_owner_id="worker",
            lease_expires_at=NOW + timedelta(minutes=1),
            terminal_at=NOW + timedelta(seconds=1),
        )


def test_cancellation_request_exists_only_on_running_job() -> None:
    """Keep request, lease and running ownership as one consistent projection."""
    running = _job(
        state=JobState.RUNNING,
        attempt_count=1,
        revision=2,
        active_owner_id="worker",
        lease_expires_at=NOW + timedelta(minutes=1),
        cancellation_requested_at=NOW + timedelta(seconds=1),
        updated_at=NOW + timedelta(seconds=1),
    )
    assert running.cancellation_requested_at == NOW + timedelta(seconds=1)
    with pytest.raises(ValidationError, match="cancellation"):
        _job(cancellation_requested_at=NOW)


@pytest.mark.parametrize(
    ("event_type", "from_state", "to_state", "attempt", "owner"),
    (
        (JobEventType.CANCELLED, JobState.QUEUED, JobState.CANCELLED, 0, None),
        (JobEventType.CANCELLED, JobState.QUEUED, JobState.CANCELLED, 2, None),
        (JobEventType.CANCEL_REQUESTED, JobState.RUNNING, JobState.RUNNING, 1, "worker"),
        (JobEventType.CANCELLED, JobState.RUNNING, JobState.CANCELLED, 1, "worker"),
    ),
)
def test_cancellation_event_shapes_are_exact(
    event_type: JobEventType,
    from_state: JobState,
    to_state: JobState,
    attempt: int,
    owner: str | None,
) -> None:
    """Admit only the three reviewed cancellation transition shapes."""
    event = JobEvent(
        job_id=JOB_ID,
        sequence=2,
        event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        occurred_at=NOW,
        attempt_count=attempt,
        owner_id=owner,
    )
    assert event.failure_code is None


def test_cancellation_event_rejects_failure_payload() -> None:
    """Do not leak arbitrary failure text or conflate cancellation with failure."""
    with pytest.raises(ValidationError, match="failure code"):
        JobEvent(
            job_id=JOB_ID,
            sequence=1,
            event_type=JobEventType.CANCELLED,
            from_state=JobState.QUEUED,
            to_state=JobState.CANCELLED,
            occurred_at=NOW,
            attempt_count=0,
            failure_code="cancelled",
        )
