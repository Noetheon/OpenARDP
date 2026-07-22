"""Integration tests for exact local-source snapshotting and inspection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource, UnsupportedTextMedia

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("name", "media_type"),
    [("note.TXT", "text/plain"), ("readme.md", "text/markdown"), ("doc.MARKDOWN", "text/markdown")],
)
def test_snapshot_streams_exact_bytes_to_cas(
    tmp_path: Path,
    name: str,
    media_type: str,
) -> None:
    """Publish exact source bytes with a canonical local locator and UTC metadata."""
    source = tmp_path / name
    payload = b"\xef\xbb\xbfexact\r\nbytes"
    source.write_bytes(payload)
    store = FilesystemObjectStore(tmp_path / "cas")

    snapshot = LocalSource(source, chunk_size=2).snapshot_to(store, observed_at=NOW)

    assert snapshot.source_key.connector == "local"
    assert snapshot.source_key.locator == str(source.resolve())
    assert snapshot.media_type.value == media_type
    assert snapshot.object.byte_length == len(payload)
    assert b"".join(store.iter_chunks(snapshot.object.object_id, chunk_size=1)) == payload
    assert snapshot.observed_at == NOW


def test_inspection_hashes_without_publishing(tmp_path: Path) -> None:
    """Compute freshness evidence without creating a CAS object."""
    source = tmp_path / "note.txt"
    source.write_bytes(b"inspect-only")
    cas_root = tmp_path / "cas"

    inspection = LocalSource(source).inspect(observed_at=NOW)

    assert inspection.version_id == (
        "sha256:22e3a25ec8ce79698b07bcb6b0f8896e8b9e5902f7daf6f3e169293df97f5230"
    )
    assert inspection.byte_length == 12
    assert not cas_root.exists()


def test_media_classification_precedes_source_read(tmp_path: Path) -> None:
    """Reject unsupported suffixes without reflecting their contents."""
    source = tmp_path / "secret.pdf"
    source.write_bytes(b"secret-body")
    with pytest.raises(UnsupportedTextMedia, match="unsupported text media") as error:
        LocalSource(source).inspect(observed_at=NOW)
    assert "secret-body" not in str(error.value)
