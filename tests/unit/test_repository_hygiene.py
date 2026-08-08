"""Deterministic, mutation-free repository sync-artifact audit tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.audit_repository_hygiene import (
    AuditError,
    FindingKind,
    audit_repository,
)

_GIT = shutil.which("git")


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    assert _GIT is not None
    return subprocess.run(  # noqa: S603 - fixed test executable and argument vector
        (_GIT, "-C", os.fspath(root), *arguments),
        check=True,
        capture_output=True,
    )


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "--quiet")
    return root


def _track(root: Path, relative: str, content: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    _git(root, "add", "--", relative)
    return path


def test_clean_repository_and_tracked_numbered_name_pass(tmp_path: Path) -> None:
    """Ignore intended tracked numbered names and unrelated untracked files."""
    root = _repository(tmp_path)
    _track(root, "chapter 2.md", b"intentional\n")
    (root / "notes.tmp").write_bytes(b"unrelated\n")

    report = audit_repository(root)

    assert report.passed
    assert report.findings == ()
    assert report.checked_scopes == ("worktree", "git_metadata")


def test_identical_divergent_and_missing_canonical_are_classified(tmp_path: Path) -> None:
    """Compare only safe untracked candidates with tracked canonical files."""
    root = _repository(tmp_path)
    _track(root, "docs/same.md", b"same\n")
    _track(root, "docs/changed.md", b"new canonical\n")
    (root / "docs/same 2.md").write_bytes(b"same\n")
    (root / "docs/changed 3.md").write_bytes(b"older copy\n")
    (root / "docs/orphan 2.md").write_bytes(b"unique\n")

    report = audit_repository(root)

    assert not report.passed
    assert [(item.candidate, item.kind) for item in report.findings] == [
        ("docs/changed 3.md", FindingKind.DIVERGENT),
        ("docs/orphan 2.md", FindingKind.MISSING_CANONICAL),
        ("docs/same 2.md", FindingKind.IDENTICAL),
    ]
    same = report.findings[-1]
    assert same.canonical == "docs/same.md"
    assert same.candidate_sha256 == same.canonical_sha256
    assert same.candidate_size == same.canonical_size == 5


def test_symlink_candidate_is_unsafe_and_not_followed(tmp_path: Path) -> None:
    """Never hash through a conflict-copy symlink."""
    root = _repository(tmp_path)
    _track(root, "safe.md", b"canonical\n")
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"private body\n")
    candidate = root / "safe 2.md"
    try:
        candidate.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    report = audit_repository(root)

    assert [(item.candidate, item.kind) for item in report.findings] == [
        ("safe 2.md", FindingKind.UNSAFE)
    ]
    assert report.findings[0].candidate_sha256 is None


def test_audit_is_deterministic_body_free_and_mutation_free(tmp_path: Path) -> None:
    """Repeated audits preserve candidate and canonical metadata and bytes."""
    root = _repository(tmp_path)
    canonical = _track(root, "sample.py", b"VALUE = 1\n")
    candidate = root / "sample 2.py"
    candidate.write_bytes(b"VALUE = 1\n")
    before = {
        path: (path.read_bytes(), path.lstat().st_mtime_ns) for path in (canonical, candidate)
    }

    first = audit_repository(root)
    second = audit_repository(root)

    assert first == second
    assert all("VALUE" not in finding.render() for finding in first.findings)
    assert {
        path: (path.read_bytes(), path.lstat().st_mtime_ns) for path in (canonical, candidate)
    } == before


def test_git_metadata_conflict_copies_are_reported_without_active_index(tmp_path: Path) -> None:
    """Inspect only explicit inactive index and loose-ref conflict copies."""
    root = _repository(tmp_path)
    _track(root, "file.txt", b"tracked\n")
    git_dir = Path(_git(root, "rev-parse", "--absolute-git-dir").stdout.decode().strip())
    active_index = git_dir / "index"
    active_before = active_index.read_bytes()
    (git_dir / "index 2").write_bytes(active_before)
    canonical_ref = git_dir / "refs/heads/topic"
    canonical_ref.parent.mkdir(parents=True, exist_ok=True)
    canonical_ref.write_text("a" * 40 + "\n", encoding="ascii")
    (git_dir / "refs/heads/topic 2").write_text("b" * 40 + "\n", encoding="ascii")

    report = audit_repository(root)

    assert [(item.scope, item.candidate, item.kind) for item in report.findings] == [
        ("git_metadata", "index 2", FindingKind.GIT_METADATA_COPY),
        ("git_metadata", "refs/heads/topic 2", FindingKind.GIT_METADATA_COPY),
    ]
    assert active_index.read_bytes() == active_before


def test_linked_worktree_git_directory_is_audited(tmp_path: Path) -> None:
    """Resolve a linked worktree's private index directory through Git."""
    root = _repository(tmp_path)
    _track(root, "file.txt", b"tracked\n")
    _git(
        root,
        "-c",
        "user.name=OpenARDP Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "fixture",
        "--quiet",
    )
    linked = tmp_path / "linked"
    _git(root, "worktree", "add", "--quiet", "--detach", os.fspath(linked), "HEAD")
    git_dir = Path(_git(linked, "rev-parse", "--absolute-git-dir").stdout.decode().strip())
    (git_dir / "index 2").write_bytes((git_dir / "index").read_bytes())

    report = audit_repository(linked)

    assert [(item.candidate, item.kind) for item in report.findings] == [
        ("index 2", FindingKind.GIT_METADATA_COPY)
    ]


def test_non_repository_fails_with_stable_classification(tmp_path: Path) -> None:
    """Do not expose arbitrary Git stderr when the root is invalid."""
    with pytest.raises(AuditError, match="root is not a Git worktree"):
        audit_repository(tmp_path)
