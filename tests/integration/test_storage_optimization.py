"""Workspace-level storage optimization integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.maintenance import (
    MaintenanceOperationKind,
    StorageOptimizationOutcome,
)
from openardp.ports.catalog import MaintenanceRecoveryRequired
from openardp.services.ingestion import IngestionService
from openardp.services.storage_optimization import StorageOptimizationService

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def _ingestion(workspace: LocalWorkspace) -> IngestionService:
    return IngestionService(
        workspace.object_store,
        workspace.catalog,
        TextParserAdapter(),
        source_factory=LocalSource,
        clock=lambda: NOW,
    )


def test_workspace_optimizer_converges_duplicate_and_reclaims_catalog(tmp_path: Path) -> None:
    """Optimize only catalog-approved block objects and preserve exact replay."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    source = tmp_path / "source.txt"
    source.write_text("first synthetic evidence\n\nsecond synthetic evidence\n", encoding="utf-8")
    ingestion = _ingestion(workspace)
    result = ingestion.ingest(source)
    aggregate = workspace.catalog.load_representation(result.scope)
    assert aggregate is not None
    first_block = aggregate.blocks[0].object
    payload = b"".join(workspace.object_store.iter_chunks(first_block.object_id))
    workspace.object_store.put_chunks((payload,))

    report = StorageOptimizationService(
        workspace.object_store,
        workspace.catalog,
    ).optimize()

    outcomes = {item.object_id: item.outcome for item in report.items}
    assert outcomes[first_block.object_id] is StorageOptimizationOutcome.DUPLICATE_CONVERGED
    assert report.failed_count == 0
    assert report.catalog_bytes_after <= report.catalog_bytes_before
    assert b"".join(workspace.object_store.iter_chunks(first_block.object_id)) == payload

    backup = tmp_path / "backup"
    workspace.backup(backup, now=NOW, reserve_bytes=0)
    assert any(
        "openardp-deflate-dict-v1" in path.as_posix()
        for path in (backup / "workspace" / "objects").rglob("*")
        if path.is_file()
    )
    LocalWorkspace.restore(backup, tmp_path / "restored", now=NOW, reserve_bytes=0)
    restored = LocalWorkspace.open(tmp_path / "restored")
    assert b"".join(restored.object_store.iter_chunks(first_block.object_id)) == payload


def test_optimizer_crash_keeps_fence_and_retry_converges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume persisted optimizer intent after a physical convergence crash."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    source = tmp_path / "source.txt"
    source.write_text("compressible synthetic evidence\n" * 100, encoding="utf-8")
    result = _ingestion(workspace).ingest(source)
    aggregate = workspace.catalog.load_representation(result.scope)
    assert aggregate is not None
    block = aggregate.blocks[0].object
    payload = b"".join(workspace.object_store.iter_chunks(block.object_id))
    workspace.object_store.put_chunks((payload,))

    def crash(point: str) -> None:
        if point == "after_ordinary_removal":
            raise RuntimeError("synthetic optimizer crash")

    monkeypatch.setattr(workspace.object_store, "_fault_point", crash)
    with pytest.raises(RuntimeError, match="synthetic optimizer crash"):
        StorageOptimizationService(
            workspace.object_store,
            workspace.catalog,
            clock=lambda: NOW,
        ).optimize()

    active = workspace.catalog.active_maintenance_operation()
    assert active is not None
    assert active.kind is MaintenanceOperationKind.STORAGE_OPTIMIZE
    with pytest.raises(MaintenanceRecoveryRequired):
        workspace.catalog.register_document(
            LocalSource(source).source_key,
            document_id=result.scope.document_id,
            now=NOW,
        )

    monkeypatch.setattr(workspace.object_store, "_fault_point", lambda _point: None)
    report = StorageOptimizationService(
        workspace.object_store,
        workspace.catalog,
        clock=lambda: NOW,
    ).optimize()

    assert workspace.catalog.active_maintenance_operation() is None
    assert report.failed_count == 0
    assert {item.object_id: item.outcome for item in report.items}[
        block.object_id
    ] is StorageOptimizationOutcome.ALREADY_COMPACT
    assert (
        workspace.object_store.verify(
            block.object_id,
            expected_length=block.byte_length,
        )
        == block
    )


def test_optimizer_fence_blocks_concurrent_ingestion_until_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent new catalog authority while compact objects are being published."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    existing = tmp_path / "existing.txt"
    existing.write_text("compressible existing evidence\n" * 100, encoding="utf-8")
    ingestion = _ingestion(workspace)
    result = ingestion.ingest(existing)
    aggregate = workspace.catalog.load_representation(result.scope)
    assert aggregate is not None
    block = aggregate.blocks[0].object
    payload = b"".join(workspace.object_store.iter_chunks(block.object_id))
    workspace.object_store.put_chunks((payload,))
    incoming = tmp_path / "incoming.txt"
    incoming.write_bytes(payload)
    blocked = False

    def attempt_concurrent_ingestion(point: str) -> None:
        nonlocal blocked
        if point != "after_ordinary_removal":
            return
        with pytest.raises(MaintenanceRecoveryRequired):
            ingestion.ingest(incoming)
        blocked = True

    monkeypatch.setattr(
        workspace.object_store,
        "_fault_point",
        attempt_concurrent_ingestion,
    )
    StorageOptimizationService(
        workspace.object_store,
        workspace.catalog,
        clock=lambda: NOW,
    ).optimize()

    assert blocked
    assert workspace.catalog.active_maintenance_operation() is None
    retry = ingestion.ingest(incoming)
    version = workspace.catalog.get_version(retry.scope.document_id, retry.scope.version_id)
    assert version is not None
    assert version.source.byte_length == len(incoming.read_bytes())
    assert version.source.object_id == block.object_id
    assert workspace.object_store._path_for_id(block.object_id).is_file()
    assert not workspace.object_store._compact_path_for_id(block.object_id).exists()
