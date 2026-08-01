"""Reachability and missing-object reporting for F011 visual artifacts."""

from __future__ import annotations

from pathlib import Path

from openardp.domain.storage import ReachabilityIssueCode
from openardp.services.reachability import ReachabilityService
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_support import prepared_visual


def _leaf(root: Path, object_id: str) -> Path:
    digest = object_id.removeprefix("sha256:")
    return root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]


def test_all_visual_objects_are_roots_and_missing_crop_is_integrity_failure(
    tmp_path: Path,
) -> None:
    """Classify raster record, raster, descriptor and crop as live evidence."""
    catalog, store, commit = prepared_visual(tmp_path)
    catalog.commit_visual_evidence(commit)
    expected = {
        commit.page_raster.raster_object.object_id,
        commit.raster_record_object.object_id,
        commit.crop_object.object_id,
        commit.descriptor_object.object_id,
    }
    report = ReachabilityService(store, catalog).analyze(observed_at=NOW)
    assert expected <= {item.object_id for item in report.reachable}

    _leaf(store.root, commit.crop_object.object_id).unlink()
    missing = ReachabilityService(store, catalog).analyze(observed_at=NOW)
    assert (ReachabilityIssueCode.MISSING_REFERENCE, commit.crop_object.object_id) in {
        (issue.code, issue.object_id) for issue in missing.inconsistencies
    }
