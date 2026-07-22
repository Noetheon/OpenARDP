"""Tests for pure F003 persistence records and value invariants."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.storage import (
    DocumentVersion,
    Job,
    JobEvent,
    JobEventType,
    JobLease,
    JobSpec,
    JobState,
    LogicalDocument,
    ObjectInventory,
    ObjectReference,
    ReachabilityIssue,
    ReachabilityIssueCode,
    ReachabilityReport,
    RecoveryResult,
    SourceKey,
    SourceVersionCommit,
    StoreAnomaly,
    StoreAnomalyCode,
    StoredObject,
    decode_storage_datetime,
    encode_storage_datetime,
    uuid7_from_parts,
)

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
DOC_ID = UUID("018f7e6a-4c00-7000-8000-000000000001")
JOB_ID = UUID("018f7e6a-4c00-4000-8000-000000000002")
NOW = datetime(2026, 7, 22, 12, 30, 0, 123, tzinfo=UTC)


def test_uuid7_from_parts_has_expected_version_variant_and_bits() -> None:
    """Build a deterministic RFC 9562 UUIDv7 without weakening F002 validation."""
    value = uuid7_from_parts(timestamp_ms=0x0123456789AB, random_bits=0)

    assert str(value) == "01234567-89ab-7000-8000-000000000000"
    assert value.version == 7
    assert value.variant == "specified in RFC 4122"


@pytest.mark.parametrize(
    ("timestamp_ms", "random_bits"),
    ((-1, 0), (1 << 48, 0), (0, -1), (0, 1 << 74)),
)
def test_uuid7_from_parts_rejects_out_of_range_values(
    timestamp_ms: int,
    random_bits: int,
) -> None:
    """Keep injected UUIDv7 entropy and time inside their exact bit fields."""
    with pytest.raises(ValueError):
        uuid7_from_parts(timestamp_ms=timestamp_ms, random_bits=random_bits)


def test_storage_datetime_is_fixed_width_utc_and_round_trips() -> None:
    """Make SQL lexical lease comparisons deterministic."""
    encoded = encode_storage_datetime(NOW)

    assert encoded == "2026-07-22T12:30:00.000123Z"
    assert decode_storage_datetime(encoded) == NOW
    assert len(encoded) == 27


@pytest.mark.parametrize(
    "value",
    (
        datetime(2026, 7, 22, 12, 30),
        datetime(2026, 7, 22, 14, 30, tzinfo=timezone(timedelta(hours=2))),
    ),
)
def test_storage_datetime_rejects_non_utc_or_naive_values(value: datetime) -> None:
    """Reject ambiguous durable lease times."""
    with pytest.raises(ValueError, match="UTC"):
        encode_storage_datetime(value)


@pytest.mark.parametrize(
    "value",
    (
        "2026-07-22T12:30:00Z",
        "2026-07-22T12:30:00.123Z",
        "2026-07-22T12:30:00.000123+00:00",
        "2026-07-22 12:30:00.000123Z",
    ),
)
def test_storage_datetime_decoder_rejects_noncanonical_text(value: str) -> None:
    """Accept only one fixed persisted timestamp form."""
    with pytest.raises(ValueError, match="fixed-width"):
        decode_storage_datetime(value)


def test_source_key_preserves_exact_locator_text() -> None:
    """Keep connector locators opaque and free of silent normalization."""
    left = SourceKey(connector="local", locator=" Folder/é ")
    right = SourceKey(connector="local", locator=" Folder/e\u0301 ")

    assert left != right
    assert left.locator == " Folder/é "


def test_storage_records_are_strict_and_attribute_frozen() -> None:
    """Reject coercion and mutation at the pure persistence boundary."""
    stored = StoredObject(object_id=SHA_A, byte_length=0)

    with pytest.raises(ValidationError):
        StoredObject(object_id=SHA_A, byte_length="0")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        stored.byte_length = 1


def test_source_version_requires_matching_source_and_unique_reference_slots() -> None:
    """Pin source identity and prevent ambiguous role/ordinal ownership."""
    duplicate = ObjectReference(role="asset", ordinal=0, object_id=SHA_B, byte_length=1)

    with pytest.raises(ValidationError, match="source object identity"):
        SourceVersionCommit(
            document_id=DOC_ID,
            version_id=SHA_A,
            source=StoredObject(object_id=SHA_B, byte_length=1),
            media_type="text/plain",
            references=(),
            committed_at=NOW,
        )
    with pytest.raises(ValidationError, match="reference slots"):
        SourceVersionCommit(
            document_id=DOC_ID,
            version_id=SHA_A,
            source=StoredObject(object_id=SHA_A, byte_length=1),
            media_type="text/plain",
            references=(duplicate, duplicate),
            committed_at=NOW,
        )


def test_logical_document_and_version_accept_uuid7_and_exact_source() -> None:
    """Represent one committed source-version fact without claiming READY parsing."""
    source_key = SourceKey(connector="local", locator="opaque://document")
    document = LogicalDocument(document_id=DOC_ID, source_key=source_key, created_at=NOW)
    version = DocumentVersion(
        document_id=document.document_id,
        version_id=SHA_A,
        source=StoredObject(object_id=SHA_A, byte_length=3),
        media_type="text/plain",
        references=(),
        committed_at=NOW,
    )

    assert version.document_id == document.document_id
    assert not hasattr(version, "state")


def test_job_spec_rejects_duplicate_reference_slots() -> None:
    """Keep job reachability roots deterministic."""
    reference = ObjectReference(role="input", ordinal=0, object_id=SHA_A, byte_length=1)

    with pytest.raises(ValidationError, match="reference slots"):
        JobSpec(
            job_id=JOB_ID,
            kind="ingest",
            deduplication_key="source:1",
            max_attempts=3,
            references=(reference, reference),
            created_at=NOW,
        )


def test_job_state_invariants_require_exact_lease_and_terminal_fields() -> None:
    """Reject states that cannot be recovered unambiguously."""
    with pytest.raises(ValidationError, match="RUNNING"):
        Job(
            job_id=JOB_ID,
            kind="ingest",
            deduplication_key="source:1",
            state=JobState.RUNNING,
            attempt_count=1,
            max_attempts=3,
            revision=1,
            active_owner_id=None,
            lease_expires_at=None,
            created_at=NOW,
            updated_at=NOW,
        )
    with pytest.raises(ValidationError, match="terminal_at"):
        Job(
            job_id=JOB_ID,
            kind="ingest",
            deduplication_key="source:1",
            state=JobState.SUCCEEDED,
            attempt_count=1,
            max_attempts=3,
            revision=2,
            created_at=NOW,
            updated_at=NOW,
        )


def test_job_lease_masks_raw_token_representation() -> None:
    """Prevent bearer tokens from leaking through ordinary model representation."""
    job = Job(
        job_id=JOB_ID,
        kind="ingest",
        deduplication_key="source:1",
        state=JobState.RUNNING,
        attempt_count=1,
        max_attempts=3,
        revision=1,
        active_owner_id="worker-1",
        lease_expires_at=NOW + timedelta(minutes=1),
        created_at=NOW,
        updated_at=NOW,
    )
    lease = JobLease(job=job, lease_token="very-secret-token")  # noqa: S106 - synthetic

    assert lease.lease_token.get_secret_value() == "very-secret-token"
    assert "very-secret-token" not in repr(lease)


def test_reachability_records_require_evidence_and_deterministic_partitions() -> None:
    """Reject ambiguous, overlapping or non-deterministic reclamation evidence."""
    with pytest.raises(ValidationError, match="requires object_id"):
        ReachabilityIssue(code=ReachabilityIssueCode.MISSING_REFERENCE)
    issue = ReachabilityIssue(
        code=ReachabilityIssueCode.STAGING_RESIDUE,
        relative_location="staging/crash.part",
    )
    first = StoredObject(object_id=SHA_A, byte_length=1)
    second = StoredObject(object_id=SHA_B, byte_length=1)

    with pytest.raises(ValidationError, match="sorted"):
        ReachabilityReport(
            observed_at=NOW,
            catalog_schema_version=2,
            reachable=(second, first),
            candidates=(),
            inconsistencies=(issue,),
        )
    with pytest.raises(ValidationError, match="disjoint"):
        ReachabilityReport(
            observed_at=NOW,
            catalog_schema_version=2,
            reachable=(first,),
            candidates=(first,),
            inconsistencies=(issue,),
        )


def test_inventory_and_recovery_results_require_canonical_unique_order() -> None:
    """Make provider outputs deterministic even when records are constructed directly."""
    first = StoredObject(object_id=SHA_A, byte_length=1)
    second = StoredObject(object_id=SHA_B, byte_length=1)
    anomaly = StoreAnomaly(
        code=StoreAnomalyCode.STAGING_RESIDUE,
        relative_location="staging/crash.part",
    )
    with pytest.raises(ValidationError, match="inventory objects must be sorted"):
        ObjectInventory(objects=(second, first), anomalies=(anomaly,))
    with pytest.raises(ValidationError, match="inventory anomalies must be sorted"):
        ObjectInventory(objects=(), anomalies=(anomaly, anomaly))
    other_job = UUID("018f7e6a-4c00-4000-8000-000000000001")
    with pytest.raises(ValidationError, match="sorted and disjoint"):
        RecoveryResult(
            requeued_job_ids=(JOB_ID, other_job),
            failed_job_ids=(),
            recovered_at=NOW,
        )
    with pytest.raises(ValidationError, match="sorted and disjoint"):
        RecoveryResult(
            requeued_job_ids=(JOB_ID,),
            failed_job_ids=(JOB_ID,),
            recovered_at=NOW,
        )


def test_job_event_requires_a_coherent_transition_shape() -> None:
    """Reject append-only evidence that contradicts its event classification."""
    with pytest.raises(ValidationError, match="transition"):
        JobEvent(
            job_id=JOB_ID,
            sequence=1,
            event_type=JobEventType.CLAIMED,
            from_state=JobState.RUNNING,
            to_state=JobState.SUCCEEDED,
            occurred_at=NOW,
            attempt_count=1,
            owner_id="worker",
        )
    with pytest.raises(ValidationError, match="failure code"):
        JobEvent(
            job_id=JOB_ID,
            sequence=2,
            event_type=JobEventType.FAILED,
            from_state=JobState.RUNNING,
            to_state=JobState.FAILED,
            occurred_at=NOW,
            attempt_count=1,
            owner_id="worker",
        )
