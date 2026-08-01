"""Atomic visual page-raster and descriptor catalog tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.ports.catalog import VisualCatalogConflict, VisualCatalogIntegrityError
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_support import prepared_visual


def test_visual_commit_is_atomic_idempotent_listed_and_fully_reachable(tmp_path: Path) -> None:
    """Publish and exactly reuse one complete visual aggregate."""
    catalog, _, commit = prepared_visual(tmp_path)
    first = catalog.commit_visual_evidence(commit)
    second = catalog.commit_visual_evidence(commit)
    assert second == first
    assert catalog.load_visual_raster(commit.page_raster.raster_id) == commit.page_raster
    assert catalog.load_visual_evidence(commit.descriptor.visual_evidence_id) == commit
    assert catalog.list_visual_evidence(commit.page_raster.scope) == (first,)
    roots = set(catalog.reference_snapshot(observed_at=NOW).object_ids)
    assert {
        commit.page_raster.raster_object.object_id,
        commit.raster_record_object.object_id,
        commit.crop_object.object_id,
        commit.descriptor_object.object_id,
    } <= roots


def test_visual_semantic_conflict_and_catalog_tamper_fail_closed(tmp_path: Path) -> None:
    """Reject a same-identity conflict and every persisted fingerprint drift."""
    catalog, _, commit = prepared_visual(tmp_path)
    catalog.commit_visual_evidence(commit)
    with sqlite3.connect(catalog.path) as connection:
        connection.execute(
            "UPDATE visual_evidence SET row_fingerprint = ? WHERE visual_evidence_id = ?",
            ("sha256:" + "f" * 64, commit.descriptor.visual_evidence_id),
        )
        connection.commit()
    with pytest.raises(VisualCatalogIntegrityError):
        catalog.load_visual_evidence(commit.descriptor.visual_evidence_id)

    catalog2, _, commit2 = prepared_visual(tmp_path / "conflict")
    catalog2.commit_visual_evidence(commit2)
    changed = commit2.model_copy(
        update={"crop_object": commit2.crop_object.model_copy(update={"byte_length": 999})}
    )
    with pytest.raises((VisualCatalogConflict, ValueError)):
        catalog2.commit_visual_evidence(changed)


@pytest.mark.parametrize(
    ("failure_point", "occurrence"),
    (
        ("after_visual_object", 1),
        ("after_visual_object", 2),
        ("after_visual_object", 3),
        ("after_visual_object", 4),
        ("after_visual_raster", 1),
        ("after_visual_descriptor", 1),
        ("before_visual_commit", 1),
    ),
)
def test_visual_fault_rolls_back_every_logical_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
    occurrence: int,
) -> None:
    """Leave no raster, descriptor or object row after every transactional boundary."""
    catalog, _, commit = prepared_visual(tmp_path)
    seen = 0

    def fail(point: str) -> None:
        nonlocal seen
        if point == failure_point:
            seen += 1
        if point == failure_point and seen == occurrence:
            raise RuntimeError("injected visual fault")

    monkeypatch.setattr(catalog, "_fault_point", fail)
    with pytest.raises(RuntimeError, match="injected visual fault"):
        catalog.commit_visual_evidence(commit)
    clean = SQLiteCatalog(catalog.path)
    assert clean.load_visual_evidence(commit.descriptor.visual_evidence_id) is None
    assert clean.load_visual_raster(commit.page_raster.raster_id) is None
    with sqlite3.connect(clean.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM objects WHERE object_id IN (?, ?, ?, ?)",
            (
                commit.page_raster.raster_object.object_id,
                commit.raster_record_object.object_id,
                commit.crop_object.object_id,
                commit.descriptor_object.object_id,
            ),
        ).fetchone() == (0,)
