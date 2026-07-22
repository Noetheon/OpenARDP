"""Cross-resource persistence-service tests for F003 source-version facts."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.storage import ObjectReference, SourceKey
from openardp.ports.object_store import ObjectCorrupt, ObjectNotFound
from openardp.services.persistence import PersistenceService

NOW = datetime(2026, 7, 22, 12, 30, tzinfo=UTC)


def _service(tmp_path: Path) -> tuple[PersistenceService, FilesystemObjectStore, SQLiteCatalog]:
    store = FilesystemObjectStore(tmp_path / "store")
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    entropy = count(7)
    service = PersistenceService(store, catalog, random_bits=lambda: next(entropy))
    return service, store, catalog


def test_document_registration_and_source_version_retry_are_idempotent(tmp_path: Path) -> None:
    """Return stable identities after a caller loses either successful response."""
    service, _, catalog = _service(tmp_path)
    key = SourceKey(connector="local", locator="opaque://one")
    document = service.register_document(key, now=NOW)

    assert service.register_document(key, now=NOW).document_id == document.document_id
    version = service.persist_source_version(
        document_id=document.document_id,
        source_chunks=(b"abc",),
        media_type="text/plain",
        now=NOW,
    )
    retry = service.persist_source_version(
        document_id=document.document_id,
        source_chunks=(b"abc",),
        media_type="text/plain",
        now=NOW,
    )

    assert retry == version
    assert catalog.list_versions(document.document_id) == (version,)


def test_same_source_bytes_can_belong_to_two_logical_documents(tmp_path: Path) -> None:
    """Deduplicate physical content without collapsing source-key identity."""
    service, store, _ = _service(tmp_path)
    first = service.register_document(SourceKey(connector="local", locator="one"), now=NOW)
    second = service.register_document(SourceKey(connector="local", locator="two"), now=NOW)

    first_version = service.persist_source_version(
        document_id=first.document_id,
        source_chunks=(b"same",),
        media_type="text/plain",
        now=NOW,
    )
    second_version = service.persist_source_version(
        document_id=second.document_id,
        source_chunks=(b"same",),
        media_type="text/plain",
        now=NOW,
    )

    assert first_version.version_id == second_version.version_id
    assert len(store.inventory().objects) == 1


def test_document_registration_retries_a_genuine_uuid_collision(tmp_path: Path) -> None:
    """Generate a new UUIDv7 only when a candidate belongs to another source key."""
    store = FilesystemObjectStore(tmp_path / "store")
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    catalog.initialize(now=NOW)
    entropy = iter((7, 7, 8))
    service = PersistenceService(store, catalog, random_bits=lambda: next(entropy))

    first = service.register_document(SourceKey(connector="local", locator="one"), now=NOW)
    second = service.register_document(SourceKey(connector="local", locator="two"), now=NOW)

    assert first.document_id != second.document_id
    assert first.document_id.version == 7
    assert second.document_id.version == 7


def test_missing_or_corrupt_extra_reference_prevents_catalog_commit(tmp_path: Path) -> None:
    """Verify every physical dependency before the source-version transaction."""
    service, store, catalog = _service(tmp_path)
    document = service.register_document(SourceKey(connector="local", locator="one"), now=NOW)
    missing_id = "sha256:" + "f" * 64
    missing = ObjectReference(role="asset", ordinal=0, object_id=missing_id, byte_length=1)

    with pytest.raises(ObjectNotFound):
        service.persist_source_version(
            document_id=document.document_id,
            source_chunks=(b"source",),
            media_type="text/plain",
            references=(missing,),
            now=NOW,
        )
    assert catalog.list_versions(document.document_id) == ()

    asset = store.put_chunks((b"asset",))
    corrupt = ObjectReference(
        role="asset", ordinal=0, object_id=asset.object_id, byte_length=asset.byte_length
    )
    digest = asset.object_id.removeprefix("sha256:")
    leaf = store.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    leaf.write_bytes(b"wrong")
    with pytest.raises(ObjectCorrupt):
        service.persist_source_version(
            document_id=document.document_id,
            source_chunks=(b"source",),
            media_type="text/plain",
            references=(corrupt,),
            now=NOW,
        )
    assert catalog.list_versions(document.document_id) == ()


def test_catalog_failure_after_cas_publish_leaves_complete_orphan_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep cross-resource failure honest and recoverable through reachability."""
    service, store, catalog = _service(tmp_path)
    document = service.register_document(SourceKey(connector="local", locator="one"), now=NOW)

    def fail_before_commit(point: str) -> None:
        if point == "before_commit":
            raise RuntimeError("synthetic catalog failure")

    monkeypatch.setattr(catalog, "_fault_point", fail_before_commit)

    with pytest.raises(RuntimeError, match="synthetic catalog failure"):
        service.persist_source_version(
            document_id=document.document_id,
            source_chunks=(b"source",),
            media_type="text/plain",
            now=NOW,
        )

    inventory = store.inventory()
    assert len(inventory.objects) == 1
    assert store.verify(inventory.objects[0].object_id) == inventory.objects[0]
    assert SQLiteCatalog(catalog.path).list_versions(document.document_id) == ()
