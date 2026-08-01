"""Focused cross-platform filesystem maintenance invariants."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

import pytest

from openardp.adapters.filesystem_maintenance import (
    _file_open_flags,
    _hash_open_descriptor,
    _read_open_descriptor,
    _sync_tree,
    _unchanged_after_read,
)


def _metadata(
    *,
    inode: int = 7,
    size: int = 11,
    device: int = 3,
    links: int = 1,
    modified: int = 200,
    created: int = 300,
) -> os.stat_result:
    return os.stat_result(
        (
            stat.S_IFREG | 0o600,
            inode,
            device,
            links,
            501,
            20,
            size,
            100,
            modified,
            created,
        )
    )


def test_post_read_check_retains_same_handle_identity() -> None:
    """Keep strong descriptor identity in addition to Windows content replay."""
    opened = _metadata()
    metadata_drift = _metadata(
        inode=99,
        device=4,
        links=2,
        modified=201,
        created=301,
    )

    assert _unchanged_after_read(opened, opened)
    assert not _unchanged_after_read(opened, metadata_drift)


def test_file_open_flags_include_binary_mode_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never let Windows CRT text translation alter managed binary bytes."""
    binary = 0x8000
    monkeypatch.setattr(os, "O_BINARY", binary, raising=False)
    assert _file_open_flags(os.O_RDONLY) & binary == binary


def test_descriptor_replay_helpers_restart_and_bound_reads(tmp_path: Path) -> None:
    """Produce repeatable bytes and hashes from the same open descriptor."""
    payload = b"stable-payload"
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)
    descriptor = os.open(path, os.O_RDONLY)
    try:
        first = _read_open_descriptor(descriptor, maximum=len(payload))
        replay = _read_open_descriptor(descriptor, maximum=len(payload))
        byte_length, digest = _hash_open_descriptor(descriptor, maximum=len(payload))
    finally:
        os.close(descriptor)

    assert first == replay == payload
    assert byte_length == len(payload)
    assert digest == hashlib.sha256(payload).digest()


def test_sync_tree_opens_owned_files_read_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use a descriptor accepted by Windows `_commit` through `os.fsync`."""
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"durable")
    original_open = os.open
    observed: list[int] = []

    def recording_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
        if Path(path) == payload:
            observed.append(flags)
        return original_open(path, flags, mode)

    monkeypatch.setattr(os, "open", recording_open)
    _sync_tree(tmp_path)

    assert observed
    assert observed[0] & os.O_RDWR == os.O_RDWR
