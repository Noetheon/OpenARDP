"""Small deterministic primitives used by the scaffold."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO

_CHUNK_SIZE = 1024 * 1024


def stream_sha256(stream: BinaryIO) -> tuple[str, int]:
    """Hash a stream without loading it into memory and return digest plus byte length."""
    digest = hashlib.sha256()
    length = 0
    while chunk := stream.read(_CHUNK_SIZE):
        digest.update(chunk)
        length += len(chunk)
    return digest.hexdigest(), length


def file_sha256(path: Path) -> tuple[str, int]:
    with path.open("rb") as stream:
        return stream_sha256(stream)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data deterministically for identity calculations."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def safe_chunks(text: str, max_chars: int = 4000) -> Iterator[str]:
    """Simple deterministic paragraph chunking for the initial text-only slice."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n")]
    for paragraph in paragraphs:
        if not paragraph:
            continue
        for start in range(0, len(paragraph), max_chars):
            yield paragraph[start : start + max_chars]
