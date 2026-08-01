"""Pure watcher identity, stability and bounded policy tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.domain.watcher import (
    AdmittedWatchRoot,
    WatchConfig,
    WatchFileFingerprint,
    WatchObservation,
    WatchObservationState,
    WatchScan,
    WatchScanEntry,
    WatchScanReason,
    watch_job_key,
    watch_locator_digest,
    watch_observation_fingerprint,
    watch_retry_delay_ms,
    watch_root_id,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
FINGERPRINT = WatchFileFingerprint(
    device_id="1", file_id="2", byte_length=3, modified_ns="4", mode=0o100600
)


def test_config_is_closed_bounded_and_identity_sensitive() -> None:
    """Include semantic policy in identity and reject contradictory recursion."""
    config = WatchConfig()
    assert config.config_hash.startswith("sha256:")
    assert config.model_copy(update={"poll_ms": 2_001}).config_hash != config.config_hash
    with pytest.raises(ValidationError, match="max_depth"):
        WatchConfig(recursive=False)
    assert WatchConfig(recursive=False, max_depth=0).max_depth == 0


def test_root_and_job_identity_exclude_execution_time() -> None:
    """Derive stable identities from exact authority and observation facts."""
    config = WatchConfig()
    path_digest = watch_locator_digest("/synthetic/watch-root")
    root_id = watch_root_id(
        root_path_digest=path_digest,
        device_id="1",
        file_id="2",
        config_hash=config.config_hash,
    )
    root = AdmittedWatchRoot(
        root_id=root_id,
        root_path="/synthetic/watch-root",
        root_path_digest=path_digest,
        device_id="1",
        file_id="2",
        config=config,
    )
    locator = watch_locator_digest("notes/a.txt")
    first = watch_job_key(
        root_id=root.root_id,
        locator_digest=locator,
        fingerprint=FINGERPRINT,
        parser_profile="default",
    )
    second = watch_job_key(
        root_id=root.root_id,
        locator_digest=locator,
        fingerprint=FINGERPRINT,
        parser_profile="default",
    )
    assert first == second
    assert first != watch_job_key(
        root_id=root.root_id,
        locator_digest=locator,
        fingerprint=FINGERPRINT.model_copy(update={"byte_length": 4}),
        parser_profile="default",
    )


def test_watcher_identity_golden_vectors_are_frozen() -> None:
    """Freeze every semantic watcher identity across implementations and processes."""
    expected = json.loads(
        (Path(__file__).parents[1] / "fixtures/watcher/canonicalization-vectors.json").read_text(
            encoding="utf-8"
        )
    )
    config = WatchConfig(
        recursive=True,
        max_depth=4,
        stability_ms=2_500,
        poll_ms=500,
        max_entries=100,
        max_active_jobs=10,
        max_jobs_per_cycle=2,
        max_attempts=4,
        retry_base_ms=250,
        retry_max_ms=4_000,
        text_profile="text-v1",
        rich_profile="rich-v1",
    )
    fingerprint = WatchFileFingerprint(
        device_id="17",
        file_id="42",
        byte_length=123,
        modified_ns="1722528000000000000",
        mode=33_188,
    )
    root_path_digest = watch_locator_digest("/opt/openardp/documents")
    root_id = watch_root_id(
        root_path_digest=root_path_digest,
        device_id="17",
        file_id="7",
        config_hash=config.config_hash,
    )
    locator_digest = watch_locator_digest("folder/report.txt")
    job_key = watch_job_key(
        root_id=root_id,
        locator_digest=locator_digest,
        fingerprint=fingerprint,
        parser_profile="text-v1",
    )
    provisional = WatchObservation.model_construct(
        root_id=root_id,
        relative_locator="folder/report.txt",
        locator_digest=locator_digest,
        state=WatchObservationState.STABLE,
        fingerprint=fingerprint,
        first_observed_at=datetime(2026, 8, 1, tzinfo=UTC),
        last_observed_at=datetime(2026, 8, 1, 0, 0, 3, tzinfo=UTC),
        stable_since=datetime(2026, 8, 1, 0, 0, 3, tzinfo=UTC),
        last_generation=2,
        last_scheduled_key=None,
        revision=2,
        row_fingerprint="sha256:" + "0" * 64,
    )
    assert {
        "config_hash": config.config_hash,
        "root_path_digest": root_path_digest,
        "root_id": root_id,
        "locator_digest": locator_digest,
        "job_key": job_key,
        "observation_fingerprint": watch_observation_fingerprint(provisional),
    } == expected


def test_scan_refuses_partial_or_unsorted_truth() -> None:
    """Make incomplete results structurally unable to imply absence."""
    entry = WatchScanEntry(
        relative_locator="a.txt",
        locator_digest=watch_locator_digest("a.txt"),
        fingerprint=FINGERPRINT,
        media_type="text/plain",
    )
    with pytest.raises(ValidationError, match="partial"):
        WatchScan(
            root_id="sha256:" + "a" * 64,
            started_at=NOW,
            completed_at=NOW,
            complete=False,
            reason=WatchScanReason.OVERFLOW,
            entries=(entry,),
        )
    with pytest.raises(ValidationError, match="sorted"):
        WatchScan(
            root_id="sha256:" + "a" * 64,
            started_at=NOW,
            completed_at=NOW,
            complete=True,
            entries=(
                entry.model_copy(
                    update={
                        "relative_locator": "b.txt",
                        "locator_digest": watch_locator_digest("b.txt"),
                    }
                ),
                entry,
            ),
        )


def test_relative_locator_rejects_escape_and_controls() -> None:
    """Keep reconstruction beneath the admitted root."""
    for value in ("../a.txt", "/a.txt", "a\\b.txt", "a\x00.txt"):
        with pytest.raises(ValidationError, match="locator"):
            WatchScanEntry(
                relative_locator=value,
                locator_digest=watch_locator_digest(value),
                fingerprint=FINGERPRINT,
                media_type="text/plain",
            )


def test_retry_delay_is_exact_and_capped() -> None:
    """Avoid jitter and integer overflow in persisted retry eligibility."""
    config = WatchConfig(max_attempts=10, retry_base_ms=1_000, retry_max_ms=5_000)
    assert [watch_retry_delay_ms(config, attempt_count=value) for value in range(1, 6)] == [
        1_000,
        2_000,
        4_000,
        5_000,
        5_000,
    ]
    with pytest.raises(ValueError, match="attempt_count"):
        watch_retry_delay_ms(config, attempt_count=0)


def test_scan_time_cannot_move_backwards() -> None:
    """Reject a clock projection that would shorten stability evidence."""
    with pytest.raises(ValidationError, match="precedes"):
        WatchScan(
            root_id="sha256:" + "a" * 64,
            started_at=NOW,
            completed_at=NOW - timedelta(microseconds=1),
            complete=True,
        )
