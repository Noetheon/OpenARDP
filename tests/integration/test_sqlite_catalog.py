"""Integration tests for migrations, source facts and fenced catalog jobs."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATION_1, MIGRATIONS, Migration
from openardp.domain.storage import (
    JobEventType,
    JobSpec,
    JobState,
    ObjectReference,
    SourceKey,
    SourceVersionCommit,
    StoredObject,
    uuid7_from_parts,
)
from openardp.ports.catalog import (
    CatalogIncompatible,
    CatalogTooNew,
    InvalidJobTransition,
    InvalidObjectReference,
    JobConflict,
    LeaseConflict,
    MigrationFailed,
    VersionConflict,
)

NOW = datetime(2026, 7, 22, 12, 30, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
DOC_A = uuid7_from_parts(timestamp_ms=1_720_000_000_000, random_bits=1)
DOC_B = uuid7_from_parts(timestamp_ms=1_720_000_000_001, random_bits=2)
JOB_A = UUID("018f7e6a-4c00-4000-8000-000000000011")


def _source_commit(
    document_id: UUID,
    *,
    version_id: str = SHA_A,
    references: tuple[ObjectReference, ...] = (),
) -> SourceVersionCommit:
    return SourceVersionCommit(
        document_id=document_id,
        version_id=version_id,
        source=StoredObject(object_id=version_id, byte_length=3),
        media_type="text/plain",
        references=references,
        committed_at=NOW,
    )


def _initialized_catalog(path: Path) -> SQLiteCatalog:
    catalog = SQLiteCatalog(path)
    assert catalog.initialize(now=NOW) == 2
    return catalog


def _schema_dump(path: Path) -> tuple[str, ...]:
    with sqlite3.connect(path) as connection:
        return tuple(connection.iterdump())


def test_revision_one_schema_and_safe_connection_profile(tmp_path: Path) -> None:
    """Install the real first revision with foreign keys and rollback journaling."""
    path = tmp_path / "catalog.sqlite3"
    catalog = SQLiteCatalog(path, migrations=(MIGRATION_1,))

    assert catalog.initialize(now=NOW) == 1
    assert catalog.initialize(now=NOW + timedelta(seconds=1)) == 1
    diagnostics = catalog.diagnostics()
    assert diagnostics["schema_version"] == 1
    assert diagnostics["journal_mode"] == "delete"
    assert diagnostics["synchronous"] == 3
    assert diagnostics["foreign_keys"] == 1
    assert diagnostics["trusted_schema"] == 0
    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert tables == {
        "schema_migrations",
        "objects",
        "documents",
        "document_versions",
        "version_object_references",
    }


def test_concurrent_exact_source_registration_returns_one_uuid7(tmp_path: Path) -> None:
    """Use the exact source-key constraint as the document registration race backstop."""
    path = tmp_path / "catalog.sqlite3"
    _initialized_catalog(path)
    source = SourceKey(connector="local", locator="opaque://same")

    def register(index: int) -> UUID:
        catalog = SQLiteCatalog(path)
        proposed = uuid7_from_parts(
            timestamp_ms=1_720_000_000_100 + index,
            random_bits=index,
        )
        return catalog.register_document(source, document_id=proposed, now=NOW).document_id

    with ThreadPoolExecutor(max_workers=8) as executor:
        identifiers = tuple(executor.map(register, range(16)))

    assert len(set(identifiers)) == 1
    assert identifiers[0].version == 7


def test_source_keys_are_exact_and_hostile_text_is_bound_data(tmp_path: Path) -> None:
    """Preserve locator text without executing SQL syntax or normalizing Unicode."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    hostile = "x'); DROP TABLE documents; --\x00é"
    first = catalog.register_document(
        SourceKey(connector="local", locator=hostile),
        document_id=DOC_A,
        now=NOW,
    )
    second = catalog.register_document(
        SourceKey(connector="local", locator=hostile.replace("é", "e\u0301")),
        document_id=DOC_B,
        now=NOW,
    )

    assert first.document_id != second.document_id
    assert catalog.diagnostics()["quick_check"] == "ok"


def test_equivalent_source_version_retry_and_cross_document_reuse(tmp_path: Path) -> None:
    """Keep global bytes reusable without collapsing logical document identity."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.register_document(
        SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW
    )
    catalog.register_document(
        SourceKey(connector="local", locator="two"), document_id=DOC_B, now=NOW
    )
    extra = ObjectReference(
        role="asset", ordinal=0, object_id=SHA_B, byte_length=5, media_type="image/png"
    )
    commit_a = _source_commit(DOC_A, references=(extra,))
    commit_b = _source_commit(DOC_B)

    first = catalog.commit_source_version(commit_a)
    assert catalog.commit_source_version(commit_a) == first
    assert catalog.commit_source_version(commit_b).version_id == first.version_id
    assert catalog.get_version(DOC_A, SHA_A) == first
    assert catalog.list_versions(DOC_A) == (first,)


def test_version_retry_canonicalizes_references_and_retains_first_commit_time(
    tmp_path: Path,
) -> None:
    """Treat role/ordinal order canonically while preserving the first successful outcome."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.register_document(
        SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW
    )
    asset = ObjectReference(role="asset", ordinal=0, object_id=SHA_B, byte_length=5)
    preview = ObjectReference(role="preview", ordinal=0, object_id=SHA_C, byte_length=7)
    original = SourceVersionCommit(
        document_id=DOC_A,
        version_id=SHA_A,
        source=StoredObject(object_id=SHA_A, byte_length=3),
        media_type="text/plain",
        references=(preview, asset),
        committed_at=NOW,
    )
    first = catalog.commit_source_version(original)
    retry = original.model_copy(
        update={
            "references": (asset, preview),
            "committed_at": NOW + timedelta(minutes=1),
        }
    )

    assert catalog.commit_source_version(retry) == first
    assert first.references == (asset, preview)
    assert first.committed_at == NOW


def test_conflicting_source_version_retry_preserves_original(tmp_path: Path) -> None:
    """Reject immutable metadata drift under an existing composite identity."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.register_document(
        SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW
    )
    original = _source_commit(DOC_A)
    catalog.commit_source_version(original)
    conflicting = original.model_copy(update={"media_type": "application/octet-stream"})

    with pytest.raises(VersionConflict):
        catalog.commit_source_version(conflicting)

    stored = catalog.get_version(DOC_A, SHA_A)
    assert stored is not None
    assert stored.model_dump() == original.model_dump()

    modified_time_conflict = original.model_copy(
        update={"source_modified_at": NOW - timedelta(days=1)}
    )
    with pytest.raises(VersionConflict):
        catalog.commit_source_version(modified_time_conflict)


def test_version_reference_length_conflict_rolls_back_entire_commit(tmp_path: Path) -> None:
    """Reject a reused object identity with conflicting immutable length."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.register_document(
        SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW
    )
    catalog.register_document(
        SourceKey(connector="local", locator="two"), document_id=DOC_B, now=NOW
    )
    catalog.commit_source_version(_source_commit(DOC_A))
    conflict = SourceVersionCommit(
        document_id=DOC_B,
        version_id=SHA_A,
        source=StoredObject(object_id=SHA_A, byte_length=999),
        media_type="text/plain",
        committed_at=NOW,
    )

    with pytest.raises(InvalidObjectReference):
        catalog.commit_source_version(conflict)

    assert catalog.get_version(DOC_B, SHA_A) is None


@pytest.mark.parametrize(
    "failure_point",
    ("after_version_header", "after_version_reference", "before_commit"),
)
def test_independent_reader_never_observes_partial_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    """Prove source-version rows and references share one visibility boundary."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _initialized_catalog(path)
    catalog.register_document(
        SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW
    )
    extra = ObjectReference(role="asset", ordinal=0, object_id=SHA_B, byte_length=5)
    observed_counts: list[tuple[int, int]] = []

    def fail_before_commit(point: str) -> None:
        with sqlite3.connect(path) as reader:
            version_count = reader.execute("SELECT count(*) FROM document_versions").fetchone()[0]
            reference_count = reader.execute(
                "SELECT count(*) FROM version_object_references"
            ).fetchone()[0]
            observed_counts.append((version_count, reference_count))
        if point == failure_point:
            raise RuntimeError("synthetic commit interruption")

    monkeypatch.setattr(catalog, "_fault_point", fail_before_commit)

    with pytest.raises(RuntimeError, match="synthetic commit interruption"):
        catalog.commit_source_version(_source_commit(DOC_A, references=(extra,)))

    assert observed_counts
    assert all(counts == (0, 0) for counts in observed_counts)
    assert SQLiteCatalog(path).get_version(DOC_A, SHA_A) is None


def test_real_revision_one_catalog_upgrades_transactionally_to_two(tmp_path: Path) -> None:
    """Exercise a genuine installed older-to-current migration path."""
    path = tmp_path / "catalog.sqlite3"
    old = SQLiteCatalog(path, migrations=(MIGRATION_1,))
    old.initialize(now=NOW)
    old.register_document(SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW)

    current = SQLiteCatalog(path)

    assert current.initialize(now=NOW + timedelta(seconds=1)) == 2
    assert (
        current.register_document(
            SourceKey(connector="local", locator="one"), document_id=DOC_B, now=NOW
        ).document_id
        == DOC_A
    )
    with sqlite3.connect(path) as connection:
        versions = tuple(
            row[0] for row in connection.execute("SELECT version FROM schema_migrations")
        )
    assert versions == (1, 2)


def test_failed_pending_migration_leaves_revision_one_unchanged(tmp_path: Path) -> None:
    """Roll back both DDL and the migration record on an injected failure."""
    path = tmp_path / "catalog.sqlite3"
    SQLiteCatalog(path, migrations=(MIGRATION_1,)).initialize(now=NOW)
    before = _schema_dump(path)
    broken = Migration(
        version=2,
        name="broken",
        statements=("CREATE TABLE should_rollback (id INTEGER) STRICT", "INVALID SQL"),
    )

    with pytest.raises(MigrationFailed):
        SQLiteCatalog(path, migrations=(MIGRATION_1, broken)).initialize(now=NOW)

    assert _schema_dump(path) == before
    assert SQLiteCatalog(path, migrations=(MIGRATION_1,)).schema_version() == 1


def test_failed_pending_chain_from_empty_rolls_back_every_revision(tmp_path: Path) -> None:
    """Keep an empty catalog empty when a later migration in the same chain fails."""
    path = tmp_path / "catalog.sqlite3"
    broken = Migration(
        version=2,
        name="broken",
        statements=("CREATE TABLE should_rollback (id INTEGER) STRICT", "INVALID SQL"),
    )

    with pytest.raises(MigrationFailed):
        SQLiteCatalog(path, migrations=(MIGRATION_1, broken)).initialize(now=NOW)

    with sqlite3.connect(path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table'"
        ).fetchall()
    assert tables == []


def test_too_new_catalog_is_rejected_without_mutation(tmp_path: Path) -> None:
    """Inspect compatibility before changing persistent catalog configuration."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _initialized_catalog(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO schema_migrations("
            "version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
            (3, "future", "sha256:" + "f" * 64, "2026-07-22T12:30:00.000000Z"),
        )
        connection.commit()
    before = _schema_dump(path)

    with pytest.raises(CatalogTooNew):
        catalog.initialize(now=NOW)

    assert _schema_dump(path) == before


def test_foreign_schema_and_checksum_drift_are_rejected(tmp_path: Path) -> None:
    """Refuse unknown ownership and altered released migration history."""
    foreign_path = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(foreign_path) as connection:
        connection.execute("CREATE TABLE foreign_table (value TEXT)")
    with pytest.raises(CatalogIncompatible):
        SQLiteCatalog(foreign_path).initialize(now=NOW)

    path = tmp_path / "catalog.sqlite3"
    _initialized_catalog(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE schema_migrations SET checksum = ? WHERE version = 1",
            ("sha256:" + "0" * 64,),
        )
        connection.commit()
    with pytest.raises(CatalogIncompatible):
        SQLiteCatalog(path).initialize(now=NOW)


def test_migration_gap_and_structural_drift_are_rejected(tmp_path: Path) -> None:
    """Require contiguous history and the exact released table inventory."""
    gap_path = tmp_path / "gap.sqlite3"
    _initialized_catalog(gap_path)
    with sqlite3.connect(gap_path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version = 1")
        connection.commit()
    with pytest.raises(CatalogIncompatible, match="gap"):
        SQLiteCatalog(gap_path).initialize(now=NOW)

    drift_path = tmp_path / "drift.sqlite3"
    _initialized_catalog(drift_path)
    with sqlite3.connect(drift_path) as connection:
        connection.execute("DROP TABLE job_events")
        connection.commit()
    with pytest.raises(CatalogIncompatible, match="tables"):
        SQLiteCatalog(drift_path).initialize(now=NOW)


def test_foreign_key_corruption_is_detected_before_initialize_commits(tmp_path: Path) -> None:
    """Refuse a checksum-valid catalog whose durable references are inconsistent."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _initialized_catalog(path)
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=1,
            created_at=NOW,
        )
    )
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO job_object_references("
            "job_id, role, ordinal, object_id, media_type) VALUES (?, ?, ?, ?, NULL)",
            (str(JOB_A), "asset", 0, SHA_A),
        )
        connection.commit()

    with pytest.raises(MigrationFailed, match="foreign-key"):
        SQLiteCatalog(path).initialize(now=NOW)


def test_job_creation_claim_renew_and_complete_are_fenced_and_audited(tmp_path: Path) -> None:
    """Persist a complete successful job lifecycle with lost-response retries."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    spec = JobSpec(
        job_id=JOB_A,
        kind="ingest",
        deduplication_key="document:one",
        max_attempts=3,
        created_at=NOW,
    )
    queued = catalog.create_job(spec)

    assert queued.state is JobState.QUEUED
    assert catalog.create_job(spec) == queued
    lease = catalog.claim_job(
        kind="ingest",
        owner_id="worker-1",
        lease_token="claim-token-0001",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(minutes=1),
    )
    assert lease is not None
    assert lease.job.state is JobState.RUNNING
    assert (
        catalog.claim_job(
            kind="ingest",
            owner_id="worker-1",
            lease_token="claim-token-0001",  # noqa: S106 - synthetic
            now=NOW,
            lease_until=NOW + timedelta(minutes=1),
        )
        == lease
    )
    renewed = catalog.renew_job(
        JOB_A,
        owner_id="worker-1",
        lease_token="claim-token-0001",  # noqa: S106 - synthetic
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=10),
        lease_until=NOW + timedelta(minutes=2),
    )
    assert (
        catalog.renew_job(
            JOB_A,
            owner_id="worker-1",
            lease_token="claim-token-0001",  # noqa: S106 - synthetic
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=11),
            lease_until=NOW + timedelta(minutes=2),
        )
        == renewed
    )
    completed = catalog.complete_job(
        JOB_A,
        owner_id="worker-1",
        lease_token="claim-token-0001",  # noqa: S106 - synthetic
        expected_revision=renewed.job.revision,
        now=NOW + timedelta(seconds=20),
    )

    assert completed.state is JobState.SUCCEEDED
    assert (
        catalog.complete_job(
            JOB_A,
            owner_id="worker-1",
            lease_token="claim-token-0001",  # noqa: S106 - synthetic
            expected_revision=renewed.job.revision,
            now=NOW + timedelta(seconds=21),
        )
        == completed
    )
    assert tuple(event.event_type for event in catalog.list_job_events(JOB_A)) == (
        JobEventType.ENQUEUED,
        JobEventType.CLAIMED,
        JobEventType.RENEWED,
        JobEventType.COMPLETED,
    )


def test_job_deduplication_conflict_is_immutable(tmp_path: Path) -> None:
    """Reject an idempotency key reused for different durable work."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    original = JobSpec(
        job_id=JOB_A,
        kind="ingest",
        deduplication_key="document:one",
        max_attempts=2,
        created_at=NOW,
    )
    catalog.create_job(original)

    with pytest.raises(JobConflict):
        catalog.create_job(
            JobSpec(
                job_id=UUID("018f7e6a-4c00-4000-8000-000000000012"),
                kind="ingest",
                deduplication_key="document:one",
                max_attempts=3,
                created_at=NOW,
            )
        )


def test_equivalent_job_retry_canonicalizes_reference_tuple_order(tmp_path: Path) -> None:
    """Use persisted role/ordinal semantics instead of caller tuple order for idempotency."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    asset = ObjectReference(role="asset", ordinal=0, object_id=SHA_A, byte_length=3)
    preview = ObjectReference(role="preview", ordinal=0, object_id=SHA_B, byte_length=5)
    original = JobSpec(
        job_id=JOB_A,
        kind="ingest",
        deduplication_key="document:one",
        max_attempts=2,
        references=(preview, asset),
        created_at=NOW,
    )
    first = catalog.create_job(original)
    retry = original.model_copy(update={"references": (asset, preview)})

    assert catalog.create_job(retry) == first
    assert first.references == (asset, preview)

    with pytest.raises(JobConflict):
        catalog.create_job(
            JobSpec(
                job_id=JOB_A,
                kind="ingest",
                deduplication_key="document:one",
                max_attempts=2,
                references=(
                    ObjectReference(
                        role="asset",
                        ordinal=0,
                        object_id=SHA_A,
                        byte_length=3,
                    ),
                ),
                created_at=NOW,
            )
        )


def test_retryable_failure_requeues_then_attempt_limit_fails(tmp_path: Path) -> None:
    """Keep retries bounded and terminal outcomes immutable."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=2,
            created_at=NOW,
        )
    )
    first = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="failure-token-001",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(seconds=10),
    )
    assert first is not None
    queued = catalog.fail_job(
        JOB_A,
        owner_id="worker",
        lease_token="failure-token-001",  # noqa: S106 - synthetic
        expected_revision=first.job.revision,
        now=NOW + timedelta(seconds=1),
        retryable=True,
        failure_code="parser_timeout",
    )
    assert queued.state is JobState.QUEUED
    second = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="failure-token-002",  # noqa: S106 - synthetic
        now=NOW + timedelta(seconds=2),
        lease_until=NOW + timedelta(seconds=12),
    )
    assert second is not None
    failed = catalog.fail_job(
        JOB_A,
        owner_id="worker",
        lease_token="failure-token-002",  # noqa: S106 - synthetic
        expected_revision=second.job.revision,
        now=NOW + timedelta(seconds=3),
        retryable=True,
        failure_code="parser_timeout",
    )

    assert failed.state is JobState.FAILED
    assert failed.attempt_count == 2
    assert catalog.recover_expired_jobs(now=NOW + timedelta(days=1)).failed_job_ids == ()
    assert tuple(event.event_type for event in catalog.list_job_events(JOB_A)) == (
        JobEventType.ENQUEUED,
        JobEventType.CLAIMED,
        JobEventType.RETRY_QUEUED,
        JobEventType.CLAIMED,
        JobEventType.FAILED,
    )


def test_stale_token_revision_and_exact_expiry_are_rejected(tmp_path: Path) -> None:
    """Treat lease expiry equality as expired and reject every stale proof."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=2,
            created_at=NOW,
        )
    )
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="expiry-token-0001",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(seconds=10),
    )
    assert lease is not None

    with pytest.raises(LeaseConflict):
        catalog.complete_job(
            JOB_A,
            owner_id="stale-worker",
            lease_token="expiry-token-0001",  # noqa: S106 - synthetic
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=1),
        )
    with pytest.raises(LeaseConflict):
        catalog.complete_job(
            JOB_A,
            owner_id="worker",
            lease_token="wrong-token-00001",  # noqa: S106 - synthetic
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=1),
        )
    with pytest.raises(LeaseConflict):
        catalog.complete_job(
            JOB_A,
            owner_id="worker",
            lease_token="expiry-token-0001",  # noqa: S106 - synthetic
            expected_revision=lease.job.revision + 1,
            now=NOW + timedelta(seconds=1),
        )
    with pytest.raises(LeaseConflict):
        catalog.complete_job(
            JOB_A,
            owner_id="worker",
            lease_token="expiry-token-0001",  # noqa: S106 - synthetic
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=10),
        )

    recovered = catalog.recover_expired_jobs(now=NOW + timedelta(seconds=10))
    assert recovered.requeued_job_ids == (JOB_A,)
    assert catalog.recover_expired_jobs(now=NOW + timedelta(seconds=10)).requeued_job_ids == ()


def test_job_mutations_reject_time_earlier_than_current_projection(tmp_path: Path) -> None:
    """Prevent revision and event timestamps from moving backwards across retries."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=2,
            created_at=NOW,
        )
    )
    first = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="monotonic-token-01",  # noqa: S106 - synthetic
        now=NOW + timedelta(seconds=10),
        lease_until=NOW + timedelta(minutes=1),
    )
    assert first is not None
    queued = catalog.fail_job(
        JOB_A,
        owner_id="worker",
        lease_token="monotonic-token-01",  # noqa: S106 - synthetic
        expected_revision=first.job.revision,
        now=NOW + timedelta(seconds=20),
        retryable=True,
        failure_code="transient",
    )
    assert queued.state is JobState.QUEUED

    with pytest.raises(InvalidJobTransition, match="precedes"):
        catalog.claim_job(
            kind=None,
            owner_id="worker",
            lease_token="monotonic-token-02",  # noqa: S106 - synthetic
            now=NOW + timedelta(seconds=15),
            lease_until=NOW + timedelta(minutes=2),
        )


def test_last_transition_token_hash_requires_canonical_sha256(tmp_path: Path) -> None:
    """Reject malformed durable fencing proofs at the SQLite constraint boundary."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _initialized_catalog(path)
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=1,
            created_at=NOW,
        )
    )

    with sqlite3.connect(path) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "UPDATE jobs SET last_transition_token_hash = ? WHERE job_id = ?",
            ("x" * 71, str(JOB_A)),
        )


def test_restart_preserves_terminal_job_and_uncommitted_process_work_rolls_back(
    tmp_path: Path,
) -> None:
    """Rely on SQLite recovery rather than process-local job or transaction state."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _initialized_catalog(path)
    catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=1,
            created_at=NOW,
        )
    )
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="terminal-token-01",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(seconds=10),
    )
    assert lease is not None
    terminal = catalog.complete_job(
        JOB_A,
        owner_id="worker",
        lease_token="terminal-token-01",  # noqa: S106 - synthetic
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=1),
    )
    assert SQLiteCatalog(path).get_job(JOB_A) == terminal

    script = """
import os, sqlite3, sys
connection = sqlite3.connect(sys.argv[1], autocommit=True)
connection.execute('BEGIN IMMEDIATE')
connection.execute(
    'INSERT INTO objects(object_id, byte_length, registered_at) VALUES (?, ?, ?)',
    ('sha256:' + 'c' * 64, 1, '2026-07-22T12:30:00.000000Z'),
)
os._exit(0)
"""
    subprocess.run([sys.executable, "-c", script, str(path)], check=True)  # noqa: S603

    with sqlite3.connect(path) as connection:
        count = connection.execute(
            "SELECT count(*) FROM objects WHERE object_id = ?", ("sha256:" + "c" * 64,)
        ).fetchone()[0]
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    assert count == 0
    assert quick_check == "ok"


def test_reference_snapshot_includes_versions_and_terminal_jobs(tmp_path: Path) -> None:
    """Keep every historical version and job reference as a conservative live root."""
    catalog = _initialized_catalog(tmp_path / "catalog.sqlite3")
    catalog.register_document(
        SourceKey(connector="local", locator="one"), document_id=DOC_A, now=NOW
    )
    asset = ObjectReference(role="asset", ordinal=0, object_id=SHA_B, byte_length=5)
    catalog.commit_source_version(_source_commit(DOC_A, references=(asset,)))
    job = catalog.create_job(
        JobSpec(
            job_id=JOB_A,
            kind="ingest",
            deduplication_key="document:one",
            max_attempts=1,
            references=(asset,),
            created_at=NOW,
        )
    )
    assert job.references == (asset,)

    snapshot = catalog.reference_snapshot(observed_at=NOW)

    assert snapshot.object_ids == tuple(sorted((SHA_A, SHA_B)))
    assert snapshot.catalog_schema_version == 2


def test_current_migration_definitions_are_contiguous_and_checksummed() -> None:
    """Freeze released migration ordering and content identity."""
    assert tuple(migration.version for migration in MIGRATIONS) == (1, 2)
    assert all(migration.checksum.startswith("sha256:") for migration in MIGRATIONS)
    assert len({migration.checksum for migration in MIGRATIONS}) == 2
