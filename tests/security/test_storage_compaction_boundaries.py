"""Hostile physical-form boundaries for F022 compact derived objects."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from openardp.adapters.compact_objects import CompactObjectError, decode_compact, encode_compact
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.ports.object_store import ObjectCorrupt


def _payload() -> bytes:
    return b'{"kind":"paragraph","text":"' + (b"bounded synthetic evidence " * 100) + b'"}'


@pytest.mark.parametrize(
    "mutator",
    (
        lambda envelope: envelope[:7] + b"\x02" + envelope[8:],
        lambda envelope: envelope[:8] + struct.pack(">Q", 1) + envelope[16:],
        lambda envelope: envelope[:-2],
        lambda envelope: envelope + b"untrusted-trailing-data",
    ),
)
def test_unknown_profile_length_truncation_and_trailing_data_fail_closed(mutator) -> None:
    """Return no partial logical body from any malformed compact envelope."""
    envelope = encode_compact(_payload())
    assert envelope is not None

    with pytest.raises(CompactObjectError):
        decode_compact(mutator(envelope))


def test_corrupt_compact_peer_blocks_logical_read(tmp_path: Path) -> None:
    """A present corrupt physical form can never be hidden by logical lookup."""
    store = FilesystemObjectStore(tmp_path / "store")
    stored = store.put_canonical_block(_payload())
    leaf = store._compact_path_for_id(stored.object_id)
    leaf.write_bytes(leaf.read_bytes()[:-1])

    with pytest.raises(ObjectCorrupt):
        tuple(store.iter_chunks(stored.object_id))
