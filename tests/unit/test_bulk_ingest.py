"""Bulk preparation discovery rules and per-file outcomes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from openardp.domain.agent_results import AddStatus
from openardp.domain.ingestion import (
    IngestionDisposition,
    IntegrityCoverage,
    RepresentationScope,
    SourceFreshness,
    SourceStatus,
)
from openardp.services.bulk_ingest import (
    BulkIngestService,
    Discovery,
    TooManyFiles,
    discover_files,
)

SUFFIXES = (".md", ".txt", ".pdf")


def test_discovery_recurses_sorts_and_skips_hidden_excluded_and_unsupported(
    tmp_path: Path,
) -> None:
    """Expand folders deterministically and never descend into the store."""
    root = tmp_path / "docs"
    (root / "b").mkdir(parents=True)
    (root / ".hidden").mkdir()
    (root / "store").mkdir()
    for name in (
        "b/z.md",
        "a.txt",
        "b/x.PDF",
        "c.xlsx",
        ".secret.md",
        ".hidden/h.md",
        "store/s.md",
    ):
        (root / name).write_text("x", encoding="utf-8")
    explicit = tmp_path / "extra.docx"
    explicit.write_text("x", encoding="utf-8")
    discovery = discover_files(
        [root, root / "a.txt", explicit],
        supported_suffixes=SUFFIXES,
        exclude=[root / "store"],
    )
    assert [path.relative_to(root).as_posix() for path in discovery.files] == [
        "a.txt",
        "b/x.PDF",
        "b/z.md",
    ]
    assert discovery.rejected == (explicit.absolute(),)
    assert discovery.skipped_unsupported == 1
    typo = discover_files([tmp_path / "docz", root / "a.txt"], supported_suffixes=SUFFIXES)
    assert typo.missing == ((tmp_path / "docz").absolute(),) and len(typo.files) == 1
    shallow = discover_files([root], supported_suffixes=SUFFIXES, recursive=False)
    assert [path.name for path in shallow.files] == ["a.txt"]


@pytest.mark.skipif(os.name == "nt", reason="symbolic links need privileges on Windows")
def test_discovery_does_not_follow_symbolic_links(tmp_path: Path) -> None:
    """Skip linked files and folders so a walk cannot leave the chosen roots."""
    root = tmp_path / "docs"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "o.md").write_text("x", encoding="utf-8")
    (root / "link.md").symlink_to(outside / "o.md")
    (root / "folder").symlink_to(outside, target_is_directory=True)
    assert discover_files([root], supported_suffixes=SUFFIXES).files == ()


def test_discovery_bounds_one_run(tmp_path: Path) -> None:
    """Refuse unbounded runs before any file is prepared."""
    for index in range(3):
        (tmp_path / f"{index}.md").write_text("x", encoding="utf-8")
    with pytest.raises(TooManyFiles):
        discover_files([tmp_path], supported_suffixes=SUFFIXES, max_files=2)


@dataclass(frozen=True)
class _Result:
    scope: RepresentationScope
    disposition: IngestionDisposition


def _scope() -> RepresentationScope:
    return RepresentationScope(
        document_id=UUID("01a0d55f-0000-7000-8000-000000000001"),
        version_id="sha256:" + "1" * 64,
        representation_id="sha256:" + "2" * 64,
    )


def _status(freshness: SourceFreshness) -> SourceStatus:
    registered = freshness is not SourceFreshness.NOT_REGISTERED
    return SourceStatus(
        freshness=freshness,
        integrity_coverage=IntegrityCoverage.HEAD if registered else IntegrityCoverage.NONE,
        document_id=_scope().document_id if registered else None,
        head=_scope() if registered else None,
        checked_at=datetime(2026, 9, 24, tzinfo=UTC),
    )


def test_outcomes_distinguish_added_updated_unchanged_and_failed(tmp_path: Path) -> None:
    """Continue after failures, skip exact-current files and classify each file once."""
    names = ("new.md", "changed.md", "same.md", "current.md", "bad.md")
    files = tuple(tmp_path / name for name in names)
    prior = {
        "changed.md": SourceFreshness.SOURCE_CHANGED,
        "same.md": SourceFreshness.NO_READY_REPRESENTATION,
        "current.md": SourceFreshness.CURRENT,
    }
    ingested: list[str] = []

    def ingest(path: Path) -> _Result:
        ingested.append(path.name)
        if path.name == "bad.md":
            raise ValueError("private detail")
        disposition = (
            IngestionDisposition.CACHE_HIT
            if path.name == "same.md"
            else IngestionDisposition.COMMITTED
        )
        return _Result(scope=_scope(), disposition=disposition)

    ticks = iter(float(value) for value in range(100))
    progress: list[tuple[int, int, str]] = []
    report = BulkIngestService(
        ingest,
        lambda path: _status(prior.get(path.name, SourceFreshness.NOT_REGISTERED)),
        lambda error: ("rejected_input", "fixed hint"),
        clock=lambda: next(ticks),
    ).add(
        Discovery(
            files=files,
            rejected=(tmp_path / "x.xlsx",),
            skipped_unsupported=4,
            missing=(tmp_path / "gone",),
        ),
        progress=lambda position, total, outcome: progress.append(
            (position, total, outcome.status.value)
        ),
    )
    assert [outcome.status for outcome in report.outcomes] == [
        AddStatus.FAILED,
        AddStatus.FAILED,
        AddStatus.ADDED,
        AddStatus.UPDATED,
        AddStatus.UNCHANGED,
        AddStatus.UNCHANGED,
        AddStatus.FAILED,
    ]
    assert "current.md" not in ingested
    assert report.outcomes[0].path == str(tmp_path / "gone")
    assert report.outcomes[5].document_id == str(_scope().document_id)
    assert report.outcomes[-1].hint == "fixed hint"
    assert "private detail" not in report.model_dump_json()
    assert report.count(AddStatus.FAILED) == 3 and report.skipped_unsupported == 4
    assert [entry[:2] for entry in progress] == [(index, 7) for index in range(1, 8)]
