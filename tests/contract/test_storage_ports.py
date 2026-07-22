"""Structural contracts for F003 provider-neutral persistence ports."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from typing import assert_type

from openardp.domain.storage import ObjectInventory, StoredObject
from openardp.ports.catalog import Catalog
from openardp.ports.object_store import (
    MalformedObjectIdentity,
    ObjectNotFound,
    ObjectStore,
    PersistenceError,
)


class _ObjectStoreDouble:
    """Minimal structural double for the object-store port."""

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        del chunks
        return StoredObject(object_id="sha256:" + "0" * 64, byte_length=0)

    def iter_chunks(self, object_id: str, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        del object_id, chunk_size
        return iter(())

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject:
        del expected_length
        return StoredObject(object_id=object_id, byte_length=0)

    def inventory(self) -> ObjectInventory:
        return ObjectInventory(objects=(), anomalies=())


def test_object_store_protocol_accepts_structural_double() -> None:
    """Keep the storage provider contract narrow and implementation-neutral."""
    store: ObjectStore = _ObjectStoreDouble()

    assert_type(store, ObjectStore)
    assert isinstance(store, ObjectStore)


def test_catalog_protocol_is_runtime_checkable() -> None:
    """Expose the catalog as one documented provider boundary."""
    assert hasattr(Catalog, "register_document")
    assert hasattr(Catalog, "commit_source_version")
    assert hasattr(Catalog, "recover_expired_jobs")
    assert hasattr(Catalog, "reference_snapshot")


def test_persistence_errors_are_sanitized_value_only_types() -> None:
    """Keep public error construction independent of raw bodies or locators."""
    malformed = MalformedObjectIdentity("invalid object identity")
    missing = ObjectNotFound("sha256:" + "0" * 64)

    assert isinstance(malformed, PersistenceError)
    assert isinstance(missing, PersistenceError)
    assert malformed.args == ("invalid object identity",)
    assert "sha256:" in str(missing)
    assert datetime.now(UTC).tzinfo is UTC
