"""Idempotence and interruption tests for explicit object optimization."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.domain.maintenance import StorageOptimizationOutcome


def _payload() -> bytes:
    return (
        b'{"asset_id":null,"block_id":"00000000-0000-4000-8000-000000000001",'
        b'"canonical_hash":"sha256:' + b"a" * 64 + b'","document_id":"00000000-0000-'
        b'4000-8000-000000000002","extensions":{},"kind":"paragraph","order":0,'
        b'"parent_id":null,"representation_id":"sha256:' + b"b" * 64 + b'",'
        b'"schema_version":"0.1.0","text":"synthetic evidence"}'
    )


def _paths(root: Path, object_id: str) -> tuple[Path, Path]:
    digest = object_id.removeprefix("sha256:")
    relative = Path(digest[:2]) / digest[2:4] / digest[4:]
    return (
        root / "objects" / "sha256" / relative,
        root / "objects" / "openardp-deflate-dict-v1" / "sha256" / relative,
    )


def test_optimizer_compacts_once_then_reports_already_compact(tmp_path: Path) -> None:
    """Remove ordinary bytes only after the compact peer verifies exactly."""
    store = FilesystemObjectStore(tmp_path)
    payload = _payload()
    stored = store.put_chunks((payload,))

    first = store.optimize_derived_block(stored.object_id, expected_length=len(payload))
    second = store.optimize_derived_block(stored.object_id, expected_length=len(payload))

    assert first.outcome is StorageOptimizationOutcome.COMPACTED
    assert second.outcome is StorageOptimizationOutcome.ALREADY_COMPACT
    assert b"".join(store.iter_chunks(stored.object_id)) == payload
    ordinary, compact = _paths(tmp_path, stored.object_id)
    assert not ordinary.exists()
    assert compact.is_file()


def test_interrupted_publication_retries_by_converging_valid_duplicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Treat raw-plus-compact as a valid retry state without hiding corruption."""
    store = FilesystemObjectStore(tmp_path)
    payload = _payload()
    stored = store.put_chunks((payload,))

    def interrupt(point: str) -> None:
        if point == "after_compact_publication":
            raise RuntimeError("synthetic interruption")

    monkeypatch.setattr(store, "_fault_point", interrupt)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        store.optimize_derived_block(stored.object_id, expected_length=len(payload))
    assert (
        store.verify(stored.object_id).object_id == "sha256:" + hashlib.sha256(payload).hexdigest()
    )

    monkeypatch.setattr(store, "_fault_point", lambda _point: None)
    retried = store.optimize_derived_block(stored.object_id, expected_length=len(payload))
    assert retried.outcome is StorageOptimizationOutcome.DUPLICATE_CONVERGED
