"""Provider-neutral optional F022 storage capability contracts."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.domain.storage import ObjectInventory, StoredObject
from openardp.ports.object_store import (
    CompactBlockStore,
    ExistingObjectOptimizer,
    ObjectStore,
    OrdinaryAuthorityStore,
)


class _OrdinaryOnlyStore:
    """Minimal shape proving compact publication remains optional."""

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        raise NotImplementedError

    def iter_chunks(self, object_id: str, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        raise NotImplementedError

    def verify(self, object_id: str, *, expected_length: int | None = None) -> StoredObject:
        raise NotImplementedError

    def inventory(self) -> ObjectInventory:
        raise NotImplementedError


def test_compact_and_optimizer_capabilities_are_optional_and_runtime_checkable(
    tmp_path: Path,
) -> None:
    """Ordinary providers remain valid while the filesystem provider opts in."""
    ordinary = _OrdinaryOnlyStore()
    filesystem = FilesystemObjectStore(tmp_path / "store")

    assert isinstance(ordinary, ObjectStore)
    assert not isinstance(ordinary, CompactBlockStore)
    assert not isinstance(ordinary, ExistingObjectOptimizer)
    assert not isinstance(ordinary, OrdinaryAuthorityStore)
    assert isinstance(filesystem, ObjectStore)
    assert isinstance(filesystem, CompactBlockStore)
    assert isinstance(filesystem, ExistingObjectOptimizer)
    assert isinstance(filesystem, OrdinaryAuthorityStore)
