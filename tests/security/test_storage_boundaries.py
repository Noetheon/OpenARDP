"""Security boundary tests for digest-only filesystem and sanitized metadata."""

from __future__ import annotations

import hashlib
import os
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.storage import JobSpec, SourceKey, uuid7_from_parts
from openardp.ports.catalog import DocumentConflict, LeaseConflict
from openardp.ports.object_store import (
    MalformedObjectIdentity,
    ObjectPublicationError,
    UnsafeStoreEntry,
)

NOW = datetime(2026, 7, 22, 12, 30, tzinfo=UTC)


def _identity(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _object_path(root: Path, object_id: str) -> Path:
    digest = object_id.removeprefix("sha256:")
    return root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]


@pytest.mark.parametrize(
    "object_id",
    (
        "",
        "../outside",
        "sha256:../" + "a" * 61,
        "sha256:" + "A" * 64,
        "sha256:" + "a" * 63,
        "sha512:" + "a" * 64,
        "sha256:C:\\outside" + "a" * 53,
        "sha256:\\server\\share" + "a" * 50,
        "sha256:" + "a" * 32 + ":stream" + "a" * 25,
        "sha256:" + "a" * 64 + "\x00",
        " sha256:" + "a" * 64,
    ),
)
def test_malformed_identity_never_touches_outside_sentinel(tmp_path: Path, object_id: str) -> None:
    """Reject traversal-like input before deriving or opening a managed path."""
    root = tmp_path / "store"
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"sentinel")
    store = FilesystemObjectStore(root)

    with pytest.raises(MalformedObjectIdentity):
        store.verify(object_id)

    assert outside.read_bytes() == b"sentinel"


def test_symlink_leaf_is_never_followed(tmp_path: Path) -> None:
    """Reject a canonical leaf redirected to outside bytes."""
    root = tmp_path / "store"
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"sentinel")
    object_id = _identity(outside.read_bytes())
    leaf = _object_path(root, object_id)
    leaf.parent.mkdir(parents=True)
    try:
        leaf.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    store = FilesystemObjectStore(root)

    with pytest.raises(UnsafeStoreEntry):
        store.verify(object_id)

    assert outside.read_bytes() == b"sentinel"


def test_symlink_fanout_directory_is_never_followed(tmp_path: Path) -> None:
    """Reject a managed ancestor redirected outside the configured root."""
    root = tmp_path / "store"
    outside = tmp_path / "outside"
    outside.mkdir()
    store = FilesystemObjectStore(root)
    object_id = _identity(b"payload")
    digest = object_id.removeprefix("sha256:")
    fanout = root / "objects" / "sha256" / digest[:2]
    try:
        fanout.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(UnsafeStoreEntry):
        store.put_chunks((b"payload",))

    assert list(outside.iterdir()) == []


def test_verify_never_reads_through_a_symlinked_fanout(tmp_path: Path) -> None:
    """Validate every managed ancestor before opening an otherwise valid leaf."""
    root = tmp_path / "store"
    store = FilesystemObjectStore(root)
    payload = b"outside-payload"
    object_id = _identity(payload)
    digest = object_id.removeprefix("sha256:")
    outside = tmp_path / "outside"
    outside_leaf = outside / digest[2:4] / digest[4:]
    outside_leaf.parent.mkdir(parents=True)
    outside_leaf.write_bytes(payload)
    fanout = root / "objects" / "sha256" / digest[:2]
    try:
        fanout.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(UnsafeStoreEntry):
        store.verify(object_id)

    assert outside_leaf.read_bytes() == payload


def test_directory_at_object_leaf_is_rejected(tmp_path: Path) -> None:
    """Accept only regular files as canonical object leaves."""
    store = FilesystemObjectStore(tmp_path)
    object_id = _identity(b"payload")
    _object_path(tmp_path, object_id).mkdir(parents=True)

    with pytest.raises(UnsafeStoreEntry):
        store.verify(object_id)


def test_hard_link_at_object_leaf_is_rejected_when_link_count_is_available(tmp_path: Path) -> None:
    """Detect an object inode writable through another local name."""
    store = FilesystemObjectStore(tmp_path / "store")
    result = store.put_chunks((b"payload",))
    leaf = _object_path(tmp_path / "store", result.object_id)
    outside_link = tmp_path / "outside-link"
    try:
        os.link(leaf, outside_link)
    except OSError as error:
        pytest.skip(f"hard links unavailable: {error}")
    if leaf.stat().st_nlink <= 1:
        pytest.skip("platform does not expose reliable link counts")

    with pytest.raises(UnsafeStoreEntry):
        store.verify(result.object_id)


@pytest.mark.skipif(os.name == "nt", reason="POSIX FIFO boundary")
def test_fifo_at_object_leaf_is_rejected_without_opening_it(tmp_path: Path) -> None:
    """Reject a blocking special file by metadata before any read."""
    store = FilesystemObjectStore(tmp_path)
    object_id = _identity(b"payload")
    leaf = _object_path(tmp_path, object_id)
    leaf.parent.mkdir(parents=True)
    os.mkfifo(leaf)

    with pytest.raises(UnsafeStoreEntry):
        store.verify(object_id)


def test_sql_values_are_bound_and_sensitive_locator_is_not_disclosed(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep hostile opaque metadata out of SQL structure, errors and ordinary logs."""
    marker = "SECRET_LOCATOR_x'); DROP TABLE documents; --\x00é"
    path = tmp_path / "catalog.sqlite3"
    catalog = SQLiteCatalog(path)
    catalog.initialize(now=NOW)
    first_id = uuid7_from_parts(timestamp_ms=1_720_000_000_000, random_bits=1)
    catalog.register_document(
        SourceKey(connector="local", locator="safe"),
        document_id=first_id,
        now=NOW,
    )

    with pytest.raises(DocumentConflict) as captured:
        catalog.register_document(
            SourceKey(connector="local", locator=marker),
            document_id=first_id,
            now=NOW,
        )

    assert marker not in str(captured.value)
    assert marker not in caplog.text
    assert catalog.diagnostics()["quick_check"] == "ok"


def test_lease_tokens_are_hashed_and_never_disclosed(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Persist only token hashes and keep raw capabilities out of failures and logs."""
    path = tmp_path / "catalog.sqlite3"
    catalog = SQLiteCatalog(path)
    catalog.initialize(now=NOW)
    job_id = UUID("018f7e6a-4c00-4000-8000-000000000011")
    catalog.create_job(
        JobSpec(
            job_id=job_id,
            kind="ingest",
            deduplication_key="security-test",
            max_attempts=1,
            created_at=NOW,
        )
    )
    raw_token = "SECRET_LEASE_TOKEN_0001"  # noqa: S105 - synthetic capability
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token=raw_token,
        now=NOW,
        lease_until=NOW + timedelta(minutes=1),
    )
    assert lease is not None

    with pytest.raises(LeaseConflict) as captured:
        catalog.complete_job(
            job_id,
            owner_id="worker",
            lease_token="WRONG_SECRET_TOKEN_01",  # noqa: S106 - synthetic capability
            expected_revision=lease.job.revision,
            now=NOW + timedelta(seconds=1),
        )

    database_bytes = path.read_bytes()
    assert raw_token.encode() not in database_bytes
    assert raw_token not in str(captured.value)
    assert raw_token not in caplog.text


def test_source_iterator_exception_is_suppressed_from_public_traceback(tmp_path: Path) -> None:
    """Do not expose document-originated iterator details through a wrapped CAS failure."""
    marker = "SECRET_DOCUMENT_EXCEPTION_MARKER"
    store = FilesystemObjectStore(tmp_path / "store")

    def broken_chunks():  # type: ignore[no-untyped-def]
        yield b"prefix"
        raise RuntimeError(marker)

    with pytest.raises(ObjectPublicationError) as captured:
        store.put_chunks(broken_chunks())

    rendered = "".join(
        traceback.format_exception(
            type(captured.value),
            captured.value,
            captured.value.__traceback__,
        )
    )
    assert marker not in str(captured.value)
    assert marker not in rendered
