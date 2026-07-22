"""Provider-neutral object-store protocol and sanitized persistence errors."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol, runtime_checkable

from openardp.domain.storage import ObjectInventory, StoredObject


class PersistenceError(RuntimeError):
    """Base class for sanitized persistence-boundary failures."""


class ObjectStoreError(PersistenceError):
    """Base class for content-addressed object-store failures."""


class MalformedObjectIdentity(ObjectStoreError, ValueError):
    """Raised before filesystem access for a malformed content identity."""


class ObjectNotFound(ObjectStoreError, FileNotFoundError):
    """Raised when a canonical object leaf does not exist."""


class ObjectCorrupt(ObjectStoreError):
    """Raised when stored bytes or length disagree with immutable metadata."""


class UnsafeStoreEntry(ObjectStoreError):
    """Raised for links, junctions, non-regular leaves or malformed layout."""


class ObjectPublicationError(ObjectStoreError):
    """Raised when staging or atomic publication does not complete."""


class ObjectDurabilityError(ObjectStoreError):
    """Raised when a complete visible object could not be fully synchronized."""


@runtime_checkable
class ObjectStore(Protocol):
    """Streaming immutable content-addressed object provider."""

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        """Store exact chunks atomically and return verified immutable metadata."""
        ...

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        """Yield bounded exact object chunks without following unsafe entries."""
        ...

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject:
        """Verify a complete object's digest, length and stable regular-file shape."""
        ...

    def inventory(self) -> ObjectInventory:
        """Return deterministic verified objects and managed-tree anomalies."""
        ...
