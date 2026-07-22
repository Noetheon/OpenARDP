"""Security and race tests for the explicit local-source boundary."""

from __future__ import annotations

import hashlib
import os
import socket
import stat
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import (
    InvalidSourcePath,
    LocalSource,
    SourceChangedDuringSnapshot,
    SourceNotFound,
    SourceTooLarge,
)
from openardp.domain.storage import StoredObject

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


class _MutatingStore:
    def __init__(self, source: Path, replacement: bytes) -> None:
        self._source = source
        self._replacement = replacement

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        payload = b"".join(chunks)
        self._source.write_bytes(self._replacement)
        return StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )


def test_missing_directory_and_symlink_sources_are_rejected(tmp_path: Path) -> None:
    """Never follow links or accept non-regular leaf types."""
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    with pytest.raises(SourceNotFound, match="source not found"):
        LocalSource(tmp_path / "missing.txt").inspect(observed_at=NOW)
    directory = tmp_path / "directory.txt"
    directory.mkdir()
    with pytest.raises(InvalidSourcePath, match="invalid source path"):
        LocalSource(directory).inspect(observed_at=NOW)
    with pytest.raises(InvalidSourcePath, match="invalid source path"):
        LocalSource(link).inspect(observed_at=NOW)


def test_symlink_ancestor_and_control_path_are_rejected(tmp_path: Path) -> None:
    """Reject unsafe authority before opening the leaf."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "note.txt").write_text("safe", encoding="utf-8")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)

    with pytest.raises(InvalidSourcePath, match="invalid source path"):
        LocalSource(linked / "note.txt").inspect(observed_at=NOW)
    with pytest.raises(InvalidSourcePath, match="invalid source path"):
        LocalSource(tmp_path / "unsafe\nname.txt").inspect(observed_at=NOW)


@pytest.mark.skipif(os.name == "nt", reason="FIFO and Unix socket are POSIX-only")
@pytest.mark.enable_socket
def test_fifo_and_socket_sources_are_rejected_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject special files from metadata before a potentially blocking open."""
    fifo = tmp_path / "pipe.txt"
    os.mkfifo(fifo)
    monkeypatch.chdir(tmp_path)
    unix_socket = Path("socket.txt")
    listener = socket.socket(socket.AF_UNIX)
    listener.bind(str(unix_socket))
    try:
        for source in (fifo, unix_socket):
            with pytest.raises(InvalidSourcePath, match="invalid source path"):
                LocalSource(source).inspect(observed_at=NOW)
    finally:
        listener.close()
        unix_socket.unlink(missing_ok=True)


def test_byte_limit_is_checked_before_and_during_streaming(tmp_path: Path) -> None:
    """Bound oversized regular sources without parser involvement."""
    source = tmp_path / "large.txt"
    source.write_bytes(b"12345")
    with pytest.raises(SourceTooLarge, match="source byte limit exceeded"):
        LocalSource(source, max_source_bytes=4).snapshot_to(
            FilesystemObjectStore(tmp_path / "cas"),
            observed_at=NOW,
        )


def test_source_change_during_snapshot_is_rejected(tmp_path: Path) -> None:
    """Leave only an orphan candidate when path evidence changes after streaming."""
    source = tmp_path / "race.txt"
    source.write_bytes(b"before")
    with pytest.raises(SourceChangedDuringSnapshot, match="source changed during snapshot"):
        LocalSource(source).snapshot_to(
            _MutatingStore(source, b"after-content"),  # type: ignore[arg-type]
            observed_at=NOW,
        )


def test_source_bytes_size_mtime_and_mode_are_never_modified(tmp_path: Path) -> None:
    """Preserve claimed source metadata across snapshot and inspection reads."""
    source = tmp_path / "immutable.txt"
    source.write_bytes(b"immutable")
    source.chmod(0o640)
    before = source.stat()

    adapter = LocalSource(source)
    adapter.snapshot_to(FilesystemObjectStore(tmp_path / "cas"), observed_at=NOW)
    adapter.inspect(observed_at=NOW)

    after = source.stat()
    assert source.read_bytes() == b"immutable"
    assert after.st_size == before.st_size
    assert after.st_mtime_ns == before.st_mtime_ns
    assert stat.S_IMODE(after.st_mode) == stat.S_IMODE(before.st_mode)
