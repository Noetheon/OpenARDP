"""Integration tests for the local filesystem content-addressed store."""

from __future__ import annotations

import hashlib
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.domain.storage import StoreAnomalyCode
from openardp.ports.object_store import ObjectCorrupt, ObjectPublicationError


def _identity(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _object_path(root: Path, object_id: str) -> Path:
    digest = object_id.removeprefix("sha256:")
    return root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]


def _put_in_spawned_process(arguments: tuple[str, bytes]) -> tuple[str, int]:
    root, payload = arguments
    result = FilesystemObjectStore(Path(root)).put_chunks((payload,))
    return result.object_id, result.byte_length


def test_put_verify_and_bounded_read_preserve_exact_chunks(tmp_path: Path) -> None:
    """Store exact chunk concatenation without requiring a whole-body API."""
    store = FilesystemObjectStore(tmp_path)
    payload = "Grüße\n".encode()

    result = store.put_chunks((payload[:2], b"", payload[2:5], payload[5:]))

    assert result.object_id == _identity(payload)
    assert result.byte_length == len(payload)
    assert store.verify(result.object_id, expected_length=len(payload)) == result
    chunks = tuple(store.iter_chunks(result.object_id, chunk_size=2))
    assert b"".join(chunks) == payload
    assert all(0 < len(chunk) <= 2 for chunk in chunks)


def test_empty_payload_is_a_valid_immutable_object(tmp_path: Path) -> None:
    """Address the empty byte sequence deterministically."""
    store = FilesystemObjectStore(tmp_path)

    result = store.put_chunks(())

    assert result.object_id == _identity(b"")
    assert result.byte_length == 0
    assert tuple(store.iter_chunks(result.object_id)) == ()


def test_verify_rejects_length_mismatch(tmp_path: Path) -> None:
    """Distinguish expected metadata drift from successful verification."""
    store = FilesystemObjectStore(tmp_path)
    result = store.put_chunks((b"abc",))

    with pytest.raises(ObjectCorrupt, match=result.object_id):
        store.verify(result.object_id, expected_length=4)


def test_thirty_two_concurrent_duplicate_writes_converge(tmp_path: Path) -> None:
    """Make duplicate publication idempotent under same-process concurrency."""
    store = FilesystemObjectStore(tmp_path)
    payload = b"concurrent exact bytes" * 128

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = tuple(executor.map(lambda _: store.put_chunks((payload,)), range(32)))

    assert {result.object_id for result in results} == {_identity(payload)}
    assert {result.byte_length for result in results} == {len(payload)}
    leaves = [path for path in (tmp_path / "objects").rglob("*") if path.is_file()]
    assert leaves == [_object_path(tmp_path, _identity(payload))]


def test_spawned_process_duplicate_writes_converge(tmp_path: Path) -> None:
    """Exercise publication with Windows-compatible spawn semantics."""
    payload = b"cross-process exact bytes" * 32
    context = multiprocessing.get_context("spawn")

    with context.Pool(processes=4) as pool:
        results = pool.map(_put_in_spawned_process, [(str(tmp_path), payload)] * 8)

    assert set(results) == {(_identity(payload), len(payload))}
    assert _object_path(tmp_path, _identity(payload)).read_bytes() == payload


def test_concurrent_different_payloads_remain_distinct(tmp_path: Path) -> None:
    """Keep content identity separate while writers share directories."""
    store = FilesystemObjectStore(tmp_path)
    payloads = tuple(f"payload-{index}".encode() for index in range(16))

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(lambda body: store.put_chunks((body,)), payloads))

    assert {result.object_id for result in results} == {_identity(body) for body in payloads}


def test_source_iterator_failure_publishes_nothing_and_cleans_own_temp(tmp_path: Path) -> None:
    """Remove catchable staging residue without exposing a canonical prefix."""
    store = FilesystemObjectStore(tmp_path)

    def broken_chunks() -> object:
        yield b"prefix"
        raise RuntimeError("synthetic source failure")

    with pytest.raises(ObjectPublicationError, match="staging failed"):
        store.put_chunks(broken_chunks())  # type: ignore[arg-type]

    assert list((tmp_path / "staging").iterdir()) == []
    assert list((tmp_path / "objects" / "sha256").rglob("*")) == []


def test_prepublication_sync_failure_publishes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse publication when staged bytes cannot be synchronized."""
    store = FilesystemObjectStore(tmp_path)

    def fail_sync(_: int) -> None:
        raise OSError("synthetic sync failure")

    monkeypatch.setattr(store, "_sync_staged_file", fail_sync)

    with pytest.raises(ObjectPublicationError, match="staging failed"):
        store.put_chunks((b"abc",))

    assert list((tmp_path / "staging").iterdir()) == []
    assert not _object_path(tmp_path, _identity(b"abc")).exists()


def test_publication_failure_cleans_temp_and_keeps_destination_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep an atomic replacement error from becoming visible state."""
    store = FilesystemObjectStore(tmp_path)

    def fail_replace(_: object, __: object) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(ObjectPublicationError, match="publication failed"):
        store.put_chunks((b"abc",))

    assert list((tmp_path / "staging").iterdir()) == []
    assert not _object_path(tmp_path, _identity(b"abc")).exists()


def test_existing_corrupt_destination_is_not_repaired_by_put(tmp_path: Path) -> None:
    """Preserve corruption evidence instead of silently overwriting it."""
    store = FilesystemObjectStore(tmp_path)
    expected_id = _identity(b"correct")
    destination = _object_path(tmp_path, expected_id)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"wrong")

    with pytest.raises(ObjectCorrupt, match=expected_id):
        store.put_chunks((b"correct",))

    assert destination.read_bytes() == b"wrong"


def test_inventory_is_sorted_and_reports_malformed_and_staging_entries(tmp_path: Path) -> None:
    """Inventory complete objects separately from non-canonical residue."""
    store = FilesystemObjectStore(tmp_path)
    first = store.put_chunks((b"first",))
    second = store.put_chunks((b"second",))
    (tmp_path / "staging" / "crash.part").write_bytes(b"prefix")
    (tmp_path / "objects" / "sha256" / "not-a-prefix").write_text("bad", encoding="utf-8")

    inventory = store.inventory()

    assert tuple(item.object_id for item in inventory.objects) == tuple(
        sorted((first.object_id, second.object_id))
    )
    assert {item.code for item in inventory.anomalies} == {
        StoreAnomalyCode.MALFORMED_ENTRY,
        StoreAnomalyCode.STAGING_RESIDUE,
    }
    assert (tmp_path / "staging" / "crash.part").exists()


def test_inventory_reports_corruption_without_deleting_bytes(tmp_path: Path) -> None:
    """Keep corrupt canonical leaves available for explicit operator review."""
    store = FilesystemObjectStore(tmp_path)
    result = store.put_chunks((b"original",))
    leaf = _object_path(tmp_path, result.object_id)
    leaf.write_bytes(b"changed!")

    inventory = store.inventory()

    assert inventory.objects == ()
    assert len(inventory.anomalies) == 1
    assert inventory.anomalies[0].code is StoreAnomalyCode.CORRUPT_OBJECT
    assert inventory.anomalies[0].object_id == result.object_id
    assert leaf.read_bytes() == b"changed!"
