"""Candidate artifact, installation and platform reproduction tests."""

from __future__ import annotations

import io
import json
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.release_reproduction import (
    ArtifactInventory,
    ReproductionEvidenceMalformed,
    ReproductionResult,
    inspect_artifact,
    reproduce_workspace_recovery,
    reproduction_checks,
)
from openardp.domain.release import EvidenceStatus

ROOT = Path(__file__).resolve().parents[2]


def _wheel(path: Path, name: str = "openardp/module.py", body: bytes = b"value = 1\n") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, body)
        archive.writestr("openardp-0.1.0rc1.dist-info/METADATA", b"Name: openardp\n")
    return path


def _sdist(path: Path) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        body = b"[project]\nname='openardp'\n"
        info = tarfile.TarInfo("openardp-0.1.0rc1/pyproject.toml")
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))
    return path


def test_artifact_inventory_covers_wheel_sdist_members_and_hashes(tmp_path: Path) -> None:
    """Inspect both candidate distribution types without extraction."""
    wheel = inspect_artifact(_wheel(tmp_path / "openardp-0.1.0rc1-py3-none-any.whl"))
    sdist = inspect_artifact(_sdist(tmp_path / "openardp-0.1.0rc1.tar.gz"))
    assert {wheel.artifact_type, sdist.artifact_type} == {"wheel", "sdist"}
    assert wheel.member_count == 2
    assert wheel.sha256.startswith("sha256:")
    assert sdist.member_inventory_id.startswith("sha256:")


def test_artifact_inspection_rejects_traversal_and_privacy_canary(tmp_path: Path) -> None:
    """Reject unsafe member paths and cleartext privacy canaries before release."""
    with pytest.raises(ReproductionEvidenceMalformed, match="path is unsafe"):
        inspect_artifact(_wheel(tmp_path / "unsafe.whl", "../escape.py"))
    canary = b"PRIVATE-CANDIDATE-CANARY"
    with pytest.raises(ReproductionEvidenceMalformed, match="privacy canary"):
        inspect_artifact(
            _wheel(tmp_path / "canary.whl", body=canary),
            forbidden_canaries=(canary,),
        )


def test_reproduction_requires_both_artifacts_and_every_allowlisted_step() -> None:
    """Map missing upgrade/recovery/install steps to explicit failed checks."""
    artifacts = (
        ArtifactInventory(
            "a.whl", "wheel", 1, "sha256:" + "1" * 64, 1, "sha256:" + "2" * 64, "passed"
        ),
        ArtifactInventory(
            "a.tar.gz", "sdist", 1, "sha256:" + "3" * 64, 1, "sha256:" + "4" * 64, "passed"
        ),
    )
    steps = ("fresh-install", "previous-upgrade", "revision-9-backup-restore")
    results = (
        ReproductionResult("fresh-install", "passed", 1),
        ReproductionResult("previous-upgrade", "passed", 2),
    )
    checks = reproduction_checks(artifacts, results, required_steps=steps)
    assert checks[0].status is EvidenceStatus.PASSED
    assert checks[-1].status is EvidenceStatus.FAILED
    with pytest.raises(ReproductionEvidenceMalformed, match="not allowlisted"):
        reproduction_checks(
            artifacts,
            (*results, ReproductionResult("unknown", "passed", 1)),
            required_steps=steps,
        )


def test_previous_application_and_revision_ten_fixture_provenance_is_explicit() -> None:
    """Bind upgrade/recovery plans to independent version and revision facts."""
    previous = json.loads(
        (
            ROOT / "tests" / "fixtures" / "release" / "previous-v0.0.1" / "workspace-plan.json"
        ).read_bytes()
    )
    revision_nine = json.loads(
        (
            ROOT / "tests" / "fixtures" / "release" / "revision-9" / "workspace-plan.json"
        ).read_bytes()
    )
    assert previous["application_version"] == "0.0.1"
    assert previous["catalog_revision"] == 11
    assert len(previous["source_merge_commit"]) == 40
    assert revision_nine["catalog_revision"] == 10
    assert revision_nine["synthetic"] is True


def test_previous_open_revision_ten_migration_and_disjoint_rollback(tmp_path: Path) -> None:
    """Execute the complete supported workspace reproduction instead of asserting a plan."""
    results = reproduce_workspace_recovery(
        ROOT / "tests" / "fixtures" / "release",
        tmp_path / "reproduction",
        now=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert tuple(item.step_id for item in results) == (
        "previous-workspace-open",
        "revision-nine-migration",
        "backup-upgrade-restore",
    )
    assert all(item.status == "passed" for item in results)
    assert (tmp_path / "reproduction" / "revision-ten").is_dir()
    assert (tmp_path / "reproduction" / "pre-upgrade-backup").is_dir()
    assert (tmp_path / "reproduction" / "restored-revision-ten").is_dir()
