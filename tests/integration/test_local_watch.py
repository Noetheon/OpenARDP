"""Safe complete and bounded local polling scanner tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from openardp.adapters import local_watch
from openardp.adapters.local_watch import LocalWatchScanner
from openardp.domain.watcher import WatchConfig, WatchJobTarget, WatchScanReason, watch_job_key
from openardp.ports.watcher import (
    WatchRootInvalid,
    WatchRootOverlap,
    WatchRootUnsupported,
    WatchTargetChanged,
)

NOW = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)


def _locations(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    root.mkdir()
    return workspace, root


def test_scan_is_supported_sorted_and_nonrecursive_when_selected(tmp_path: Path) -> None:
    """Return only supported regular files in deterministic relative order."""
    workspace, root = _locations(tmp_path)
    (root / "z.txt").write_text("z", encoding="utf-8")
    (root / "table.csv").write_text("key,value\na,b\n", encoding="utf-8")
    (root / "a.md").write_text("a", encoding="utf-8")
    (root / "ignored.bin").write_bytes(b"x")
    if os.name != "nt":
        (root / "hostile\\name.txt").write_text("hostile", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "inside.txt").write_text("inside", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(
        root,
        workspace=workspace,
        config=WatchConfig(recursive=False, max_depth=0),
    )
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW + timedelta(seconds=1))
    assert scan.complete
    assert tuple(entry.relative_locator for entry in scan.entries) == (
        "a.md",
        "table.csv",
        "z.txt",
    )


def test_scan_refreshes_identity_instead_of_using_direntry_cached_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use portable stat identities because Windows DirEntry identities are zeroed."""
    workspace, root = _locations(tmp_path)
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    real_scandir = os.scandir

    class _CachedEntry:
        name = source.name
        path = str(source)

        def stat(self, *, follow_symlinks: bool) -> os.stat_result:
            del follow_symlinks
            raise AssertionError("cached DirEntry.stat() identity was used")

    def cached_scandir(path: os.PathLike[str] | str) -> Any:
        if Path(path) == root:
            return [_CachedEntry()]
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", cached_scandir)
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert tuple(entry.relative_locator for entry in scan.entries) == ("a.txt",)


def test_recursive_scan_and_entry_overflow_are_all_or_nothing(tmp_path: Path) -> None:
    """Return zero partial observations after crossing the exact bound."""
    workspace, root = _locations(tmp_path)
    nested = root / "nested"
    nested.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    (nested / "b.txt").write_text("b", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig(max_entries=1))
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert not scan.complete
    assert scan.reason is WatchScanReason.OVERFLOW
    assert scan.entries == ()


def test_recursive_depth_bound_is_exact(tmp_path: Path) -> None:
    """Include files at the selected directory depth and never descend beyond it."""
    workspace = tmp_path / "workspace"
    root = tmp_path / "documents"
    workspace.mkdir()
    (root / "level-one" / "level-two").mkdir(parents=True)
    (root / "level-one" / "included.txt").write_text("included", encoding="utf-8")
    (root / "level-one" / "level-two" / "excluded.txt").write_text("excluded", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig(max_depth=1))
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert tuple(entry.relative_locator for entry in scan.entries) == ("level-one/included.txt",)


def test_root_and_workspace_must_be_disjoint(tmp_path: Path) -> None:
    """Reject feedback loops in either containment direction."""
    workspace, root = _locations(tmp_path)
    scanner = LocalWatchScanner()
    with pytest.raises(WatchRootOverlap):
        scanner.admit(tmp_path, workspace=workspace, config=WatchConfig())
    (root / "nested").mkdir()
    with pytest.raises(WatchRootOverlap):
        scanner.admit(root, workspace=root / "nested", config=WatchConfig())


def test_root_must_be_supplied_as_an_absolute_lexically_canonical_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject authority aliases instead of silently expanding or normalizing them."""
    workspace, root = _locations(tmp_path)
    scanner = LocalWatchScanner()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(WatchRootInvalid):
        scanner.admit(Path("documents"), workspace=workspace, config=WatchConfig())
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(WatchRootInvalid):
        scanner.admit(Path("~/documents"), workspace=workspace, config=WatchConfig())
    aliased = root / ".." / root.name
    assert aliased.is_absolute()
    with pytest.raises(WatchRootInvalid):
        scanner.admit(aliased, workspace=workspace, config=WatchConfig())


def test_link_component_and_recognizable_share_are_rejected(tmp_path: Path) -> None:
    """Fail before traversal for linked or recognizable remote authority."""
    workspace, root = _locations(tmp_path)
    link = tmp_path / "linked"
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    scanner = LocalWatchScanner()
    with pytest.raises(WatchRootInvalid):
        scanner.admit(link, workspace=workspace, config=WatchConfig())
    with pytest.raises(WatchRootUnsupported):
        scanner.admit(Path(r"\\server\share"), workspace=workspace, config=WatchConfig())


def test_file_links_are_not_followed(tmp_path: Path) -> None:
    """Ignore a linked document even when its suffix is supported."""
    workspace, root = _locations(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("file symlinks unavailable")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert scan.complete and scan.entries == ()


def test_root_replacement_returns_empty_incomplete_scan(tmp_path: Path) -> None:
    """Never apply absence after admitted root authority changes."""
    workspace, root = _locations(tmp_path)
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())
    root.rename(tmp_path / "retained-old-root")
    root.mkdir()
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert scan.reason is WatchScanReason.ROOT_CHANGED
    assert scan.entries == ()


def test_disappearing_entry_and_cross_device_file_never_produce_partial_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail a disappearing enumeration closed and skip a foreign-device regular file."""
    workspace, root = _locations(tmp_path)
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())

    real_stat = local_watch._fresh_stat

    def disappearing_stat(path: Path) -> os.stat_result:
        if path == source:
            raise FileNotFoundError
        return real_stat(path)

    monkeypatch.setattr(local_watch, "_fresh_stat", disappearing_stat)
    incomplete = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert not incomplete.complete
    assert incomplete.reason is WatchScanReason.INCOMPLETE
    assert incomplete.entries == ()

    metadata = real_stat(source)

    def foreign_stat(path: Path) -> Any:
        if path == source:
            return type(
                "ForeignMetadata",
                (),
                {"st_mode": metadata.st_mode, "st_dev": metadata.st_dev + 1},
            )()
        return real_stat(path)

    monkeypatch.setattr(local_watch, "_fresh_stat", foreign_stat)
    foreign = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert foreign.complete
    assert foreign.entries == ()


def test_directory_change_during_enumeration_invalidates_entire_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not call an internally raced directory enumeration authoritative."""
    workspace, root = _locations(tmp_path)
    (root / "before.txt").write_text("before", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())
    real_scandir = os.scandir
    initial_metadata = root.stat()
    changed = False

    def racing_scandir(path: os.PathLike[str] | str) -> list[os.DirEntry[str]]:
        nonlocal changed
        entries = list(real_scandir(path))
        if not changed:
            changed = True
            (root / "during.txt").write_text("during", encoding="utf-8")
            os.utime(
                root,
                ns=(initial_metadata.st_atime_ns, initial_metadata.st_mtime_ns + 1_000_000_000),
            )
        return entries

    monkeypatch.setattr(os, "scandir", racing_scandir)
    scan = scanner.scan(admitted, started_at=NOW, completed_at=NOW)
    assert not scan.complete
    assert scan.reason is WatchScanReason.INCOMPLETE
    assert scan.entries == ()


def test_revalidation_rejects_replaced_root_before_target_use(tmp_path: Path) -> None:
    """Bind target reconstruction to the admitted directory identity, not only its path."""
    workspace, root = _locations(tmp_path)
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig(stability_ms=0))
    entry = scanner.scan(admitted, started_at=NOW, completed_at=NOW).entries[0]
    key = watch_job_key(
        root_id=admitted.root_id,
        locator_digest=entry.locator_digest,
        fingerprint=entry.fingerprint,
        parser_profile="default",
    )
    target = WatchJobTarget(
        job_id=UUID("018f7e6a-4c00-4000-8000-000000000099"),
        root_id=admitted.root_id,
        relative_locator=entry.relative_locator,
        locator_digest=entry.locator_digest,
        fingerprint=entry.fingerprint,
        parser_profile="default",
        deduplication_key=key,
        created_at=NOW,
    )
    root.rename(tmp_path / "old-documents")
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    with pytest.raises(WatchTargetChanged):
        scanner.revalidate_target(admitted, target)


def test_scanner_does_not_open_document_bodies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Collect only metadata and leave exact bytes to the source snapshot boundary."""
    workspace, root = _locations(tmp_path)
    (root / "a.txt").write_text("body", encoding="utf-8")
    scanner = LocalWatchScanner()
    admitted = scanner.admit(root, workspace=workspace, config=WatchConfig())

    def forbidden_open(*args: object, **kwargs: object) -> int:
        del args, kwargs
        raise AssertionError("scanner opened document bytes")

    monkeypatch.setattr(os, "open", forbidden_open)
    assert scanner.scan(admitted, started_at=NOW, completed_at=NOW).complete
