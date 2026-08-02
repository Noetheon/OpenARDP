"""Deterministic and hostile-boundary tests for compact derived objects."""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Callable

import pytest

from openardp.adapters.compact_objects import (
    MAX_LOGICAL_BYTES,
    CompactObjectError,
    decode_compact,
    encode_compact,
)


def _canonical_block_payload() -> bytes:
    return (
        b'{"block_id":"00000000-0000-4000-8000-000000000001",'
        b'"document_id":"00000000-0000-4000-8000-000000000002",'
        b'"kind":"paragraph","record_type":"block","schema_version":"0.1.0",'
        b'"text":"A deterministic sentence used only as a synthetic fixture.",'
        b'"version_id":"sha256:' + b"a" * 64 + b'"}'
    )


def test_compact_round_trip_is_deterministic_and_smaller() -> None:
    """Round-trip one synthetic block into a stable smaller physical envelope."""
    payload = _canonical_block_payload()

    first = encode_compact(payload)
    second = encode_compact(payload)

    assert first is not None
    assert first == second
    assert len(first) < len(payload)
    assert decode_compact(first) == payload


@pytest.mark.parametrize(
    "payload",
    [b"", b"x", b"".join(hashlib.sha256(bytes((value,))).digest() for value in range(8))],
)
def test_non_saving_payload_stays_ordinary(payload: bytes) -> None:
    """Reject compact forms that do not reduce complete stored bytes."""
    assert encode_compact(payload) is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value[:4],
        lambda value: b"BADMAGIC" + value[8:],
        lambda value: value[:-1],
        lambda value: value + b"trailing",
        lambda value: value[:8] + struct.pack(">Q", MAX_LOGICAL_BYTES + 1) + value[16:],
    ],
)
def test_malformed_compact_envelopes_fail_closed(
    mutator: Callable[[bytes], bytes],
) -> None:
    """Reject framing, stream, trailing-byte and expansion-bound violations."""
    envelope = encode_compact(_canonical_block_payload())
    assert envelope is not None

    with pytest.raises(CompactObjectError):
        decode_compact(mutator(envelope))


def test_payload_over_logical_limit_is_not_compacted() -> None:
    """Keep over-limit logical content outside the bounded compact profile."""
    assert encode_compact(b"x" * (MAX_LOGICAL_BYTES + 1)) is None
