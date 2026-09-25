"""Prepare many local files and folders in one process with per-file outcomes."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openardp.domain.agent_results import AddOutcome, AddReport, AddStatus
from openardp.domain.ingestion import (
    IngestionDisposition,
    RepresentationScope,
    SourceFreshness,
    SourceStatus,
)
from openardp.ports.parser import UnsupportedTextMedia

MAX_FILES_PER_RUN = 10_000


class PreparedResult(Protocol):
    """Shape shared by text and rich ingestion results."""

    @property
    def scope(self) -> RepresentationScope:
        """Return the prepared representation scope."""
        ...

    @property
    def disposition(self) -> IngestionDisposition:
        """Return how the source was prepared or reused."""
        ...


IngestOne = Callable[[Path], PreparedResult]
PriorStatus = Callable[[Path], SourceStatus]
DescribeError = Callable[[Exception], tuple[str, str | None]]
Progress = Callable[[int, int, AddOutcome], None]


@dataclass(frozen=True, slots=True)
class Discovery:
    """Supported files to prepare, explicit unsupported or missing paths and skipped counts."""

    files: tuple[Path, ...]
    rejected: tuple[Path, ...]
    skipped_unsupported: int
    missing: tuple[Path, ...] = ()


class SourcePathMissing(FileNotFoundError):
    """Raised for a requested file or folder that does not exist."""


class TooManyFiles(ValueError):
    """Raised when one run would prepare more files than the bounded maximum."""


def discover_files(
    paths: Sequence[Path],
    *,
    supported_suffixes: Sequence[str],
    exclude: Sequence[Path] = (),
    recursive: bool = True,
    max_files: int = MAX_FILES_PER_RUN,
) -> Discovery:
    """Expand files and folders into sorted supported files without following links."""
    suffixes = {suffix.casefold() for suffix in supported_suffixes}
    excluded = [path.absolute() for path in exclude]
    files: list[Path] = []
    rejected: list[Path] = []
    missing: list[Path] = []
    skipped = 0
    for raw in paths:
        path = raw.expanduser().absolute()
        if not path.exists() and not path.is_symlink():
            missing.append(path)
        elif path.is_dir() and not path.is_symlink():
            found, skipped_here = _walk(path, suffixes, excluded, recursive=recursive)
            files.extend(found)
            skipped += skipped_here
        elif path.suffix.casefold() in suffixes:
            files.append(path)
        else:
            rejected.append(path)
        if len(files) > max_files:
            raise TooManyFiles("too many files in one run")
    unique = tuple(dict.fromkeys(files))
    return Discovery(
        files=unique,
        rejected=tuple(rejected),
        skipped_unsupported=skipped,
        missing=tuple(missing),
    )


def _walk(
    root: Path,
    suffixes: set[str],
    excluded: Sequence[Path],
    *,
    recursive: bool,
) -> tuple[list[Path], int]:
    found: list[Path] = []
    skipped = 0
    for directory, subdirectories, names in os.walk(root, followlinks=False):
        current = Path(directory)
        subdirectories[:] = sorted(
            name
            for name in subdirectories
            if recursive
            and not name.startswith(".")
            and not any(_within(current / name, item) for item in excluded)
        )
        for name in sorted(names):
            candidate = current / name
            if name.startswith(".") or candidate.is_symlink():
                continue
            if candidate.suffix.casefold() in suffixes:
                found.append(candidate)
            else:
                skipped += 1
    return found, skipped


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


class BulkIngestService:
    """Prepare discovered files one by one, continuing past individual failures."""

    def __init__(
        self,
        ingest_one: IngestOne,
        prior_status: PriorStatus,
        describe_error: DescribeError,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Bind single-file preparation, the exact prior-state probe and error wording."""
        self._ingest_one = ingest_one
        self._prior_status = prior_status
        self._describe_error = describe_error
        self._clock = clock

    def add(self, discovery: Discovery, *, progress: Progress | None = None) -> AddReport:
        """Prepare every discovered file and report added, updated, unchanged or failed."""
        outcomes: list[AddOutcome] = []
        total = len(discovery.files) + len(discovery.rejected) + len(discovery.missing)
        unusable = [
            (path, SourcePathMissing("source path does not exist")) for path in discovery.missing
        ] + [(path, UnsupportedTextMedia("unsupported text media")) for path in discovery.rejected]
        for path, reason in unusable:
            code, hint = self._describe_error(reason)
            outcome = AddOutcome(
                path=str(path),
                status=AddStatus.FAILED,
                error_code=code,
                hint=hint,
                seconds=0.0,
            )
            outcomes.append(outcome)
            if progress is not None:
                progress(len(outcomes), total, outcome)
        for path in discovery.files:
            outcome = self._prepare(path)
            outcomes.append(outcome)
            if progress is not None:
                progress(len(outcomes), total, outcome)
        return AddReport(
            outcomes=tuple(outcomes),
            skipped_unsupported=discovery.skipped_unsupported,
        )

    def _prepare(self, path: Path) -> AddOutcome:
        started = self._clock()
        try:
            prior = self._prior_status(path)
            # Exact source bytes already match a READY head: nothing to prepare.
            if prior.freshness is SourceFreshness.CURRENT and prior.document_id is not None:
                return AddOutcome(
                    path=str(path),
                    status=AddStatus.UNCHANGED,
                    document_id=str(prior.document_id),
                    seconds=max(0.0, self._clock() - started),
                )
            existed = prior.freshness is not SourceFreshness.NOT_REGISTERED
            result = self._ingest_one(path)
        except Exception as error:
            code, hint = self._describe_error(error)
            return AddOutcome(
                path=str(path),
                status=AddStatus.FAILED,
                error_code=code,
                hint=hint,
                seconds=max(0.0, self._clock() - started),
            )
        if result.disposition is IngestionDisposition.CACHE_HIT:
            status = AddStatus.UNCHANGED
        else:
            status = AddStatus.UPDATED if existed else AddStatus.ADDED
        return AddOutcome(
            path=str(path),
            status=status,
            document_id=str(result.scope.document_id),
            seconds=max(0.0, self._clock() - started),
        )


__all__ = [
    "MAX_FILES_PER_RUN",
    "BulkIngestService",
    "Discovery",
    "PreparedResult",
    "SourcePathMissing",
    "TooManyFiles",
    "discover_files",
]
