"""Deterministic bounded physical encoding for canonical derived blocks."""

from __future__ import annotations

import struct
import zlib
from typing import cast

PROFILE = "openardp-deflate-dict-v1"
MAX_LOGICAL_BYTES = 16 * 1024 * 1024

_MAGIC = b"OARDPDB\x01"
_HEADER = struct.Struct(">8sQ")

# DEFLATE dictionaries favor bytes near the end. This dictionary contains only stable
# F002 schema/profile vocabulary, never user document content.
_DICTIONARY = (
    b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:,{}[]nulltruefalse"
    b"sha256:0000000000000000000000000000000000000000000000000000000000000000"
    b'{"asset_id":null,"block_id":"00000000-0000-0000-0000-000000000000",'
    b'"canonical_hash":"sha256:0000000000000000000000000000000000000000000000000000000000000000",'
    b'"document_id":"00000000-0000-0000-0000-000000000000","extensions":{},'
    b'"kind":"paragraph","order":0,"parent_id":null,"representation_id":"sha256:'
    b'0000000000000000000000000000000000000000000000000000000000000000",'
    b'"schema_version":"0.1.0","source":{"bbox":null,"extensions":{"openardp.text":'
    b'{"line_end":1,"line_start":1}},"extraction_method":"openardp-text-v1",'
    b'"native_id":null,"page":null,"slide":null},"structured":null,"text":"",'
    b'"trust":{"instruction_execution_allowed":false,"integrity":"verified_sha256",'
    b'"role":"data","sensitivity":"unknown","zone":"external_untrusted"},'
    b'"version_id":"sha256:0000000000000000000000000000000000000000000000000000000000000000"}'
)


class CompactObjectError(ValueError):
    """Raised when a compact physical form is malformed or exceeds its bounds."""


def encode_compact(payload: bytes) -> bytes | None:
    """Return a smaller v1 envelope, or ``None`` when ordinary bytes are safer."""
    if not isinstance(payload, bytes):
        raise TypeError("compact payload must be bytes")
    if len(payload) > MAX_LOGICAL_BYTES:
        return None
    compressor = zlib.compressobj(level=9, wbits=-15, zdict=_DICTIONARY)
    compressed = compressor.compress(payload) + compressor.flush(zlib.Z_FINISH)
    envelope = _HEADER.pack(_MAGIC, len(payload)) + compressed
    return envelope if len(envelope) < len(payload) else None


def decode_compact(envelope: bytes) -> bytes:
    """Decode one complete v1 envelope under strict length and stream bounds."""
    if not isinstance(envelope, bytes):
        raise TypeError("compact envelope must be bytes")
    if len(envelope) < _HEADER.size:
        raise CompactObjectError("compact object header is incomplete")
    magic, declared_length = _HEADER.unpack_from(envelope)
    if magic != _MAGIC:
        raise CompactObjectError("compact object profile is unsupported")
    if declared_length > MAX_LOGICAL_BYTES:
        raise CompactObjectError("compact object logical length exceeds the limit")
    compressed = envelope[_HEADER.size :]
    try:
        decoder = zlib.decompressobj(wbits=-15, zdict=_DICTIONARY)
        payload = decoder.decompress(compressed, declared_length + 1)
        if len(payload) > declared_length or decoder.unconsumed_tail:
            raise CompactObjectError("compact object expands beyond its declared length")
        payload += decoder.flush()
    except CompactObjectError:
        raise
    except zlib.error:
        raise CompactObjectError("compact object stream is malformed") from None
    if not decoder.eof:
        raise CompactObjectError("compact object stream is incomplete")
    if decoder.unused_data:
        raise CompactObjectError("compact object has trailing data")
    if len(payload) != declared_length:
        raise CompactObjectError("compact object logical length is inconsistent")
    return payload


def compact_logical_length(envelope: bytes) -> int:
    """Return the validated declared length without decoding the payload."""
    if len(envelope) < _HEADER.size:
        raise CompactObjectError("compact object header is incomplete")
    magic, declared_length = _HEADER.unpack_from(envelope)
    if magic != _MAGIC or declared_length > MAX_LOGICAL_BYTES:
        raise CompactObjectError("compact object header is invalid")
    return cast(int, declared_length)


__all__ = [
    "MAX_LOGICAL_BYTES",
    "PROFILE",
    "CompactObjectError",
    "compact_logical_length",
    "decode_compact",
    "encode_compact",
]
