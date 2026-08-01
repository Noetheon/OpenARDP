"""Hostile authority and redaction boundaries for local watcher facts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.watcher import WatchEvent, WatchEventType

NOW = datetime(2026, 8, 1, 14, 0, tzinfo=UTC)


def test_structured_event_has_no_path_body_token_or_message_field() -> None:
    """Keep watcher audit events on a closed opaque allowlist."""
    event = WatchEvent(
        root_id="sha256:" + "a" * 64,
        sequence=1,
        event_type=WatchEventType.SCAN_COMPLETED,
        generation=1,
        occurred_at=NOW,
        entry_count=3,
    )
    assert set(event.model_dump()) == {
        "root_id",
        "sequence",
        "event_type",
        "locator_digest",
        "job_id",
        "generation",
        "occurred_at",
        "entry_count",
        "scheduled_count",
        "tombstone_count",
    }


@pytest.mark.parametrize(
    ("event_type", "locator", "job_id", "scheduled", "tombstoned"),
    (
        (WatchEventType.ROOT_REGISTERED, "sha256:" + "b" * 64, None, 0, 0),
        (WatchEventType.TARGET_SCHEDULED, None, UUID(int=1), 1, 0),
        (WatchEventType.TOMBSTONED, "sha256:" + "b" * 64, None, 0, 0),
        (WatchEventType.JOB_FAILED, "sha256:" + "b" * 64, None, 0, 0),
    ),
)
def test_structured_event_rejects_cross_classification_fields(
    event_type: WatchEventType,
    locator: str | None,
    job_id: UUID | None,
    scheduled: int,
    tombstoned: int,
) -> None:
    """Prevent identifiers and counts from drifting across the closed event allowlist."""
    with pytest.raises(ValidationError, match="event"):
        WatchEvent(
            root_id="sha256:" + "a" * 64,
            sequence=1,
            event_type=event_type,
            locator_digest=locator,
            job_id=job_id,
            generation=1,
            occurred_at=NOW,
            scheduled_count=scheduled,
            tombstone_count=tombstoned,
        )
