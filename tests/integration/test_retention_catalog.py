"""Explainable root and operator-hold catalog tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.identity import canonical_sha256
from openardp.domain.maintenance import RetentionHold, RootReason
from openardp.domain.storage import SourceKey, SourceVersionCommit, generate_uuid7

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def test_retention_snapshot_explains_source_root_and_active_hold(tmp_path: Path) -> None:
    """Return closed root families and opaque reference evidence in one snapshot."""
    workspace = LocalWorkspace.initialize(tmp_path / "store", now=NOW)
    stored = workspace.object_store.put_chunks((b"source",))
    document_id = generate_uuid7(now=NOW, random_bits=1)
    workspace.catalog.register_document(
        SourceKey(connector="local", locator="opaque"), document_id=document_id, now=NOW
    )
    workspace.catalog.commit_source_version(
        SourceVersionCommit(
            document_id=document_id,
            version_id=stored.object_id,
            source=stored,
            media_type="text/plain",
            committed_at=NOW,
        )
    )
    hold = RetentionHold(
        hold_id=canonical_sha256({"hold": 1}),
        object_id=stored.object_id,
        reason="operator_hold",
        created_at=NOW,
        expires_at=NOW + timedelta(days=1),
    )
    workspace.catalog.add_retention_hold(hold)

    snapshot = workspace.catalog.retention_snapshot(observed_at=NOW)
    assert any(
        root.object_id == stored.object_id and root.reason is RootReason.SOURCE_VERSION
        for root in snapshot.roots
    )
    assert snapshot.holds == (hold,)
    released = workspace.catalog.release_retention_hold(hold.hold_id, now=NOW)
    assert released.released_at == NOW
    assert workspace.catalog.retention_snapshot(observed_at=NOW).holds == ()
