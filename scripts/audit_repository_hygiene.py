"""Detect local synchronization conflict copies without mutating a Git repository."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

_CONFLICT_COPY = re.compile(r"^(?P<base>.+?) (?P<number>[2-9][0-9]*)(?P<suffix>\..+)?$")
_HASH_CHUNK_BYTES = 1024 * 1024
_GIT = shutil.which("git")


class AuditError(ValueError):
    """Raised when repository facts cannot be inspected safely."""


class FindingKind(StrEnum):
    """Closed classification for one repository hygiene finding."""

    IDENTICAL = "identical"
    DIVERGENT = "divergent"
    MISSING_CANONICAL = "missing_canonical"
    UNSAFE = "unsafe"
    GIT_METADATA_COPY = "git_metadata_copy"


@dataclass(frozen=True, slots=True)
class HygieneFinding:
    """One deterministic body-free sync-artifact finding."""

    kind: FindingKind
    scope: str
    candidate: str
    canonical: str | None = None
    candidate_size: int | None = None
    canonical_size: int | None = None
    candidate_sha256: str | None = None
    canonical_sha256: str | None = None

    def render(self) -> str:
        """Render a stable diagnostic containing metadata but no file body."""
        facts = [f"{self.kind.value}: {self.scope}:{self.candidate}"]
        for name in (
            "canonical",
            "candidate_size",
            "canonical_size",
            "candidate_sha256",
            "canonical_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                facts.append(f"{name}={value}")
        return " ".join(facts)


@dataclass(frozen=True, slots=True)
class HygieneReport:
    """Deterministically ordered result of one read-only repository audit."""

    version: int
    checked_scopes: tuple[str, ...]
    findings: tuple[HygieneFinding, ...]

    @property
    def passed(self) -> bool:
        """Return whether no conflict-copy artifact was found."""
        return not self.findings


@dataclass(frozen=True, slots=True)
class _FileFacts:
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class _GitLayout:
    worktree: Path
    private_dir: Path
    common_dir: Path


def _run_git(root: Path, *arguments: str) -> bytes:
    if _GIT is None:
        raise AuditError("Git executable is unavailable")
    try:
        result = subprocess.run(  # noqa: S603 - fixed executable and argument vector, no shell
            (_GIT, "-C", os.fspath(root), *arguments),
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise AuditError("Git executable is unavailable") from error
    if result.returncode != 0:
        raise AuditError("root is not a Git worktree")
    return result.stdout


def _decode_line(value: bytes, *, fact: str) -> str:
    try:
        decoded = value.decode("utf-8").strip()
    except UnicodeError as error:
        raise AuditError(f"{fact} is not valid UTF-8") from error
    if not decoded or any(ord(character) < 32 for character in decoded):
        raise AuditError(f"{fact} is unsafe")
    return decoded


def _git_layout(root: Path) -> _GitLayout:
    worktree = root.resolve()
    if (
        _decode_line(
            _run_git(worktree, "rev-parse", "--is-inside-work-tree"),
            fact="Git worktree state",
        )
        != "true"
    ):
        raise AuditError("root is not a Git worktree")
    private_text = _decode_line(
        _run_git(worktree, "rev-parse", "--absolute-git-dir"),
        fact="Git directory",
    )
    common_text = _decode_line(
        _run_git(worktree, "rev-parse", "--git-common-dir"),
        fact="Git common directory",
    )
    private_dir = Path(private_text)
    common_dir = Path(common_text)
    if not private_dir.is_absolute():
        private_dir = worktree / private_dir
    if not common_dir.is_absolute():
        common_dir = worktree / common_dir
    private_dir = private_dir.resolve()
    common_dir = common_dir.resolve()
    if not private_dir.is_dir() or not common_dir.is_dir():
        raise AuditError("Git metadata directory is unavailable")
    return _GitLayout(worktree=worktree, private_dir=private_dir, common_dir=common_dir)


def _inventory(root: Path, *arguments: str) -> tuple[str, ...]:
    raw = _run_git(root, "ls-files", "-z", *arguments)
    values: list[str] = []
    for encoded in raw.split(b"\0"):
        if not encoded:
            continue
        try:
            value = encoded.decode("utf-8")
        except UnicodeError as error:
            raise AuditError("Git inventory path is not valid UTF-8") from error
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or any(ord(character) < 32 for character in value)
            or path.as_posix() != value
        ):
            raise AuditError("Git inventory contains unsafe path")
        values.append(value)
    return tuple(sorted(set(values)))


def _canonical_name(name: str) -> str | None:
    match = _CONFLICT_COPY.fullmatch(name)
    if match is None:
        return None
    return f"{match.group('base')}{match.group('suffix') or ''}"


def _canonical_relative(candidate: str) -> str | None:
    path = PurePosixPath(candidate)
    canonical_name = _canonical_name(path.name)
    if canonical_name is None:
        return None
    return path.with_name(canonical_name).as_posix()


def _file_facts(path: Path) -> _FileFacts | None:
    """Hash one stable regular file without following a link."""
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            return None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                before.st_dev,
                before.st_ino,
            ):
                return None
            digest = hashlib.sha256()
            while chunk := os.read(descriptor, _HASH_CHUNK_BYTES):
                digest.update(chunk)
        finally:
            os.close(descriptor)
        after = path.lstat()
    except OSError:
        return None
    if (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ):
        return None
    return _FileFacts(size=before.st_size, sha256=digest.hexdigest())


def _worktree_findings(layout: _GitLayout) -> Iterable[HygieneFinding]:
    tracked = set(_inventory(layout.worktree, "--cached"))
    untracked = _inventory(layout.worktree, "--others", "--exclude-standard")
    for candidate in untracked:
        canonical = _canonical_relative(candidate)
        if canonical is None:
            continue
        candidate_path = layout.worktree.joinpath(*PurePosixPath(candidate).parts)
        if canonical not in tracked:
            yield HygieneFinding(
                kind=FindingKind.MISSING_CANONICAL,
                scope="worktree",
                candidate=candidate,
                canonical=canonical,
                candidate_size=_safe_size(candidate_path),
            )
            continue
        canonical_path = layout.worktree.joinpath(*PurePosixPath(canonical).parts)
        candidate_facts = _file_facts(candidate_path)
        canonical_facts = _file_facts(canonical_path)
        if candidate_facts is None or canonical_facts is None:
            yield HygieneFinding(
                kind=FindingKind.UNSAFE,
                scope="worktree",
                candidate=candidate,
                canonical=canonical,
            )
            continue
        kind = (
            FindingKind.IDENTICAL if candidate_facts == canonical_facts else FindingKind.DIVERGENT
        )
        yield HygieneFinding(
            kind=kind,
            scope="worktree",
            candidate=candidate,
            canonical=canonical,
            candidate_size=candidate_facts.size,
            canonical_size=canonical_facts.size,
            candidate_sha256=candidate_facts.sha256,
            canonical_sha256=canonical_facts.sha256,
        )


def _safe_size(path: Path) -> int | None:
    try:
        metadata = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        return None
    return metadata.st_size


def _metadata_finding(root: Path, candidate: Path) -> HygieneFinding:
    relative = candidate.relative_to(root).as_posix()
    canonical_name = _canonical_name(candidate.name)
    canonical = candidate.with_name(canonical_name) if canonical_name is not None else None
    candidate_facts = _file_facts(candidate)
    canonical_facts = _file_facts(canonical) if canonical is not None else None
    return HygieneFinding(
        kind=FindingKind.GIT_METADATA_COPY,
        scope="git_metadata",
        candidate=relative,
        canonical=canonical.relative_to(root).as_posix() if canonical is not None else None,
        candidate_size=candidate_facts.size if candidate_facts else None,
        canonical_size=canonical_facts.size if canonical_facts else None,
        candidate_sha256=candidate_facts.sha256 if candidate_facts else None,
        canonical_sha256=canonical_facts.sha256 if canonical_facts else None,
    )


def _numbered_children(directory: Path, *, prefix: str | None = None) -> Iterable[Path]:
    try:
        children = tuple(directory.iterdir())
    except OSError as error:
        raise AuditError("Git metadata cannot be enumerated") from error
    for child in sorted(children, key=lambda path: path.name):
        if prefix is not None and not child.name.startswith(prefix):
            continue
        if _canonical_name(child.name) is not None:
            yield child


def _numbered_refs(refs: Path) -> Iterable[Path]:
    if not refs.exists():
        return
    for directory, names, filenames in os.walk(refs, followlinks=False):
        names[:] = sorted(name for name in names if not (Path(directory) / name).is_symlink())
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if _canonical_name(filename) is not None:
                yield path


def _git_metadata_findings(layout: _GitLayout) -> Iterable[HygieneFinding]:
    seen: set[Path] = set()
    for candidate in _numbered_children(layout.private_dir, prefix="index "):
        resolved = candidate.absolute()
        if resolved not in seen:
            seen.add(resolved)
            yield _metadata_finding(layout.private_dir, candidate)
    refs = layout.common_dir / "refs"
    for candidate in _numbered_refs(refs):
        resolved = candidate.absolute()
        if resolved not in seen:
            seen.add(resolved)
            yield _metadata_finding(layout.common_dir, candidate)


def audit_repository(root: Path) -> HygieneReport:
    """Inspect one Git worktree and return deterministic sync-artifact findings."""
    layout = _git_layout(Path(root))
    findings = tuple(
        sorted(
            (*_worktree_findings(layout), *_git_metadata_findings(layout)),
            key=lambda item: (item.scope, item.candidate, item.kind.value),
        )
    )
    return HygieneReport(
        version=1,
        checked_scopes=("worktree", "git_metadata"),
        findings=findings,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the read-only audit and return a shell-friendly status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    try:
        report = audit_repository(arguments.root)
    except AuditError as error:
        print(f"repository hygiene audit failed: {error}")
        return 2
    for finding in report.findings:
        print(finding.render())
    if report.passed:
        print("repository hygiene audit passed")
        return 0
    print(f"repository hygiene audit failed with {len(report.findings)} finding(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
