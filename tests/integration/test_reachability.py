"""Read-only reachability integration tests for mixed catalog/CAS state."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from uuid import UUID

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.storage import (
    JobSpec,
    ObjectReference,
    ReachabilityIssueCode,
    SourceKey,
    SourceVersionCommit,
    StoredObject,
)
from openardp.services.persistence import PersistenceService
from openardp.services.reachability import ReachabilityService

NOW = datetime(2026, 7, 22, 12, 30, tzinfo=UTC)
JOB_ID = UUID("018f7e6a-4c00-4000-8000-000000000011")


def _components(
    tmp_path: Path,
) -> tuple[FilesystemObjectStore, SQLiteCatalog, PersistenceService, ReachabilityService]:
    store = FilesystemObjectStore(tmp_path / "store")
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    entropy = count(1)
    persistence = PersistenceService(store, catalog, random_bits=lambda: next(entropy))
    return store, catalog, persistence, ReachabilityService(store, catalog)


def _leaf(store: FilesystemObjectStore, object_id: str) -> Path:
    digest = object_id.removeprefix("sha256:")
    return store.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]


def _tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | str], ...]:
    entries: list[tuple[str, str, bytes | str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((relative, "link", os.readlink(path)))
        elif path.is_file():
            entries.append((relative, "file", path.read_bytes()))
        else:
            entries.append((relative, "directory", b""))
    return tuple(entries)


def test_historical_versions_terminal_job_and_orphan_are_classified(
    tmp_path: Path,
) -> None:
    """Keep all committed history/job roots live and report only complete orphans."""
    store, catalog, persistence, reachability = _components(tmp_path)
    document = persistence.register_document(
        SourceKey(connector="local", locator="document"),
        now=NOW,
    )
    first = persistence.persist_source_version(
        document_id=document.document_id,
        source_chunks=(b"version-one",),
        media_type="text/plain",
        now=NOW,
    )
    second = persistence.persist_source_version(
        document_id=document.document_id,
        source_chunks=(b"version-two",),
        media_type="text/plain",
        now=NOW + timedelta(seconds=1),
    )
    job_object = store.put_chunks((b"terminal-job-input",))
    job_reference = ObjectReference(
        role="input",
        ordinal=0,
        object_id=job_object.object_id,
        byte_length=job_object.byte_length,
    )
    catalog.create_job(
        JobSpec(
            job_id=JOB_ID,
            kind="ingest",
            deduplication_key="document",
            max_attempts=1,
            references=(job_reference,),
            created_at=NOW,
        )
    )
    lease = catalog.claim_job(
        kind=None,
        owner_id="worker",
        lease_token="reachability-token-01",  # noqa: S106 - synthetic
        now=NOW,
        lease_until=NOW + timedelta(minutes=1),
    )
    assert lease is not None
    catalog.complete_job(
        JOB_ID,
        owner_id="worker",
        lease_token="reachability-token-01",  # noqa: S106 - synthetic
        expected_revision=lease.job.revision,
        now=NOW + timedelta(seconds=2),
    )
    orphan = store.put_chunks((b"complete-orphan",))

    report = reachability.analyze(observed_at=NOW + timedelta(minutes=2))
    repeated = reachability.analyze(observed_at=NOW + timedelta(minutes=2))

    assert report == repeated
    assert tuple(item.object_id for item in report.reachable) == tuple(
        sorted((first.version_id, second.version_id, job_object.object_id))
    )
    assert report.candidates == (orphan,)
    assert report.inconsistencies == ()


def test_missing_and_corrupt_references_are_not_candidates(tmp_path: Path) -> None:
    """Separate unavailable live evidence from ordinary unreferenced objects."""
    store, catalog, persistence, reachability = _components(tmp_path)
    missing_document = persistence.register_document(
        SourceKey(connector="local", locator="missing"),
        now=NOW,
    )
    corrupt_document = persistence.register_document(
        SourceKey(connector="local", locator="corrupt"),
        now=NOW,
    )
    missing_id = "sha256:" + "f" * 64
    catalog.commit_source_version(
        SourceVersionCommit(
            document_id=missing_document.document_id,
            version_id=missing_id,
            source=StoredObject(object_id=missing_id, byte_length=7),
            media_type="application/octet-stream",
            committed_at=NOW,
        )
    )
    corrupt = store.put_chunks((b"original",))
    catalog.commit_source_version(
        SourceVersionCommit(
            document_id=corrupt_document.document_id,
            version_id=corrupt.object_id,
            source=corrupt,
            media_type="application/octet-stream",
            committed_at=NOW,
        )
    )
    _leaf(store, corrupt.object_id).write_bytes(b"corrupt")

    report = reachability.analyze(observed_at=NOW)

    assert report.reachable == ()
    assert report.candidates == ()
    assert {(issue.code, issue.object_id) for issue in report.inconsistencies} == {
        (ReachabilityIssueCode.MISSING_REFERENCE, missing_id),
        (ReachabilityIssueCode.CORRUPT_REFERENCE, corrupt.object_id),
    }


def test_malformed_unsafe_and_staging_entries_are_reported_without_following(
    tmp_path: Path,
) -> None:
    """Classify managed-tree anomalies without reading a symlink target."""
    store, _, _, reachability = _components(tmp_path)
    algorithm_root = store.root / "objects" / "sha256"
    (algorithm_root / "not-hex").mkdir()
    staging = store.root / "staging" / "crash.part"
    staging.write_bytes(b"incomplete")
    corrupt_orphan = store.put_chunks((b"unreferenced-corrupt",))
    _leaf(store, corrupt_orphan.object_id).write_bytes(b"wrong")
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_bytes(b"outside-sentinel")
    unsafe_link = algorithm_root / "ee"
    try:
        unsafe_link.symlink_to(outside, target_is_directory=True)
    except OSError:
        unsafe_link = None

    report = reachability.analyze(observed_at=NOW)

    codes = {issue.code for issue in report.inconsistencies}
    assert ReachabilityIssueCode.MALFORMED_STORE_ENTRY in codes
    assert ReachabilityIssueCode.STAGING_RESIDUE in codes
    assert ReachabilityIssueCode.CORRUPT_STORE_OBJECT in codes
    if unsafe_link is not None:
        assert ReachabilityIssueCode.UNSAFE_STORE_ENTRY in codes
    assert sentinel.read_bytes() == b"outside-sentinel"


def test_analysis_is_byte_for_byte_read_only(tmp_path: Path) -> None:
    """Leave both the catalog file and complete managed tree exactly unchanged."""
    store, catalog, persistence, reachability = _components(tmp_path)
    document = persistence.register_document(
        SourceKey(connector="local", locator="document"),
        now=NOW,
    )
    persistence.persist_source_version(
        document_id=document.document_id,
        source_chunks=(b"source",),
        media_type="text/plain",
        now=NOW,
    )
    store.put_chunks((b"orphan",))
    before_tree = _tree_snapshot(store.root)
    before_catalog = catalog.path.read_bytes()

    reachability.analyze(observed_at=NOW)

    assert _tree_snapshot(store.root) == before_tree
    assert catalog.path.read_bytes() == before_catalog


def test_object_published_after_catalog_snapshot_is_advisory_candidate(tmp_path: Path) -> None:
    """Document the conservative snapshot-then-inventory race classification."""
    store, catalog, _, _ = _components(tmp_path)

    class PublishingCatalog:
        def __init__(self) -> None:
            self.published: StoredObject | None = None

        def reference_snapshot(self, *, observed_at: datetime):  # type: ignore[no-untyped-def]
            snapshot = catalog.reference_snapshot(observed_at=observed_at)
            self.published = store.put_chunks((b"published-after-snapshot",))
            return snapshot

    racing_catalog = PublishingCatalog()
    service = ReachabilityService(store, racing_catalog)  # type: ignore[arg-type]

    report = service.analyze(observed_at=NOW)

    assert racing_catalog.published is not None
    assert report.candidates == (racing_catalog.published,)
    assert store.verify(racing_catalog.published.object_id) == racing_catalog.published
