"""Hostile-data and authority tests for F013 maintenance boundaries."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.maintenance import BackupFile
from openardp.interfaces.cli import main
from openardp.ports.maintenance import MaintenanceError

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def test_ordinary_object_store_has_no_destructive_authority(tmp_path: Path) -> None:
    """Keep exact removal outside the ordinary immutable CAS interface."""
    workspace = LocalWorkspace.initialize(tmp_path / "workspace", now=NOW)
    stored = workspace.object_store.put_chunks((b"DO-NOT-REMOVE",))

    assert not hasattr(workspace.object_store, "remove")
    assert workspace.object_store.verify(stored.object_id) == stored


@pytest.mark.parametrize(
    "relative_path",
    ("../escape", "/absolute", "workspace/../../escape", "workspace\\escape"),
)
def test_backup_manifest_paths_reject_traversal_and_platform_separators(
    relative_path: str,
) -> None:
    """Validate every untrusted manifest path before any restore read."""
    with pytest.raises(ValidationError):
        BackupFile(
            relative_path=relative_path,
            byte_length=0,
            sha256="sha256:" + "0" * 64,
        )


def test_backup_symlink_and_diagnostic_output_fail_closed_without_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject linked backup authority and keep hostile names/bodies out of JSON."""
    hostile_name = "PRIVATE-WORKSPACE-NAME"
    hostile_body = "PRIVATE-DOCUMENT-BODY"
    workspace = LocalWorkspace.initialize(tmp_path / hostile_name, now=NOW)
    workspace.object_store.put_chunks((hostile_body.encode(),))
    real_backup = tmp_path / "backup"
    workspace.backup(real_backup, now=NOW, reserve_bytes=0)
    linked_backup = tmp_path / "linked-backup"
    try:
        linked_backup.symlink_to(real_backup, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")

    destination = tmp_path / "restore-target"
    with pytest.raises(MaintenanceError):
        LocalWorkspace.restore(linked_backup, destination, now=NOW, reserve_bytes=0)
    assert not destination.exists()

    assert (
        main(
            [
                "storage-diagnostics",
                "--store",
                str(workspace.root),
                "--reserve-bytes",
                "0",
                "--json",
            ]
        )
        == 0
    )
    encoded = json.dumps(json.loads(capsys.readouterr().out))
    assert hostile_name not in encoded
    assert hostile_body not in encoded
