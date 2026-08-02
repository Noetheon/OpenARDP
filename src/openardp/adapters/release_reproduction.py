"""Bounded artifact inspection and sanitized install/recovery reproduction evidence."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tarfile
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import cast

from pydantic import JsonValue

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import CURRENT_SCHEMA_VERSION, MIGRATIONS
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.release import EvidenceCheck, EvidenceStatus, PlatformEvidence

_MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
_MAX_EXPANDED_BYTES = 512 * 1024 * 1024
_MAX_MEMBERS = 20_000
_FORBIDDEN_MEMBER_PARTS = (".git", ".openardp", "__pycache__", ".pytest_cache")


class ReproductionEvidenceMalformed(ValueError):
    """Raised when an artifact or reproduction record is incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class ArtifactInventory:
    """Body-free facts for one inspected wheel or source distribution."""

    filename: str
    artifact_type: str
    byte_length: int
    sha256: str
    member_count: int
    member_inventory_id: str
    status: str


@dataclass(frozen=True, slots=True)
class ReproductionResult:
    """Sanitized outcome for one explicit installation or recovery step."""

    step_id: str
    status: str
    duration_ms: int
    reason: str | None = None
    evidence_ids: tuple[str, ...] = ()


def inspect_artifact(path: Path, *, forbidden_canaries: Sequence[bytes] = ()) -> ArtifactInventory:
    """Inspect wheel/sdist structure without extracting or retaining member bodies."""
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size > _MAX_ARTIFACT_BYTES
    ):
        raise ReproductionEvidenceMalformed("artifact is unsafe or exceeds size limit")
    if path.suffix == ".whl":
        artifact_type = "wheel"
        members = _zip_members(path, forbidden_canaries)
    elif path.name.endswith(".tar.gz"):
        artifact_type = "sdist"
        members = _tar_members(path, forbidden_canaries)
    else:
        raise ReproductionEvidenceMalformed("artifact type is unsupported")
    data_digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            data_digest.update(chunk)
    return ArtifactInventory(
        filename=path.name,
        artifact_type=artifact_type,
        byte_length=metadata.st_size,
        sha256=f"sha256:{data_digest.hexdigest()}",
        member_count=len(members),
        member_inventory_id=canonical_sha256(cast(JsonValue, members)),
        status="passed",
    )


def reproduction_checks(
    artifacts: Sequence[ArtifactInventory],
    results: Sequence[ReproductionResult],
    *,
    required_steps: Sequence[str],
) -> tuple[EvidenceCheck, ...]:
    """Require both distribution types and every declared install/recovery step."""
    artifact_types = {item.artifact_type for item in artifacts if item.status == "passed"}
    checks = [
        EvidenceCheck(
            check_id="candidate-artifacts-inspected",
            status=(
                EvidenceStatus.PASSED
                if artifact_types == {"wheel", "sdist"}
                else EvidenceStatus.FAILED
            ),
            reason=None
            if artifact_types == {"wheel", "sdist"}
            else "artifact-inventory-incomplete",
            observed=len(artifact_types),
            expected=2,
            evidence_ids=tuple(sorted(item.sha256 for item in artifacts)),
        )
    ]
    by_step: dict[str, ReproductionResult] = {}
    for result in results:
        if result.step_id in by_step or result.duration_ms < 0:
            raise ReproductionEvidenceMalformed("reproduction result is duplicate or malformed")
        if result.status not in {"passed", "failed", "unavailable"}:
            raise ReproductionEvidenceMalformed("reproduction status is unsupported")
        by_step[result.step_id] = result
    if set(by_step) - set(required_steps):
        raise ReproductionEvidenceMalformed("reproduction result is not allowlisted")
    checks.extend(
        EvidenceCheck(
            check_id=step,
            status=(
                EvidenceStatus.PASSED
                if step in by_step and by_step[step].status == "passed"
                else EvidenceStatus.FAILED
            ),
            reason=(
                None
                if step in by_step and by_step[step].status == "passed"
                else "reproduction-step-incomplete"
            ),
            evidence_ids=(
                (
                    canonical_sha256(
                        {
                            "duration_ms": by_step[step].duration_ms,
                            "reason": by_step[step].reason,
                            "status": by_step[step].status,
                            "step_id": by_step[step].step_id,
                        }
                    ),
                    *by_step[step].evidence_ids,
                )
                if step in by_step
                else ()
            ),
        )
        for step in required_steps
    )
    return tuple(checks)


def platform_semantics_agree(evidence: Sequence[PlatformEvidence]) -> bool:
    """Compare identity and terminal suite semantics while excluding timings/environment."""
    if not evidence:
        return False
    projections = [
        {
            "source_tree_id": item.source_tree_id,
            "protocol_id": item.protocol_id,
            "corpus_id": item.corpus_id,
            "configuration_id": item.configuration_id,
            "lockfile_id": item.lockfile_id,
            "baselines": [baseline.value for baseline in item.baselines],
            "suites": [
                {
                    "name": suite.name.value,
                    "status": suite.status.value,
                    "checks": [
                        {
                            "check_id": check.check_id,
                            "status": check.status.value,
                            "reason": check.reason,
                        }
                        for check in suite.checks
                    ],
                }
                for suite in item.suites
            ],
        }
        for item in evidence
    ]
    return all(item == projections[0] for item in projections[1:])


def reproduce_workspace_recovery(
    fixture_root: Path,
    scratch: Path,
    *,
    now: datetime,
) -> tuple[ReproductionResult, ...]:
    """Exercise supported prior-open, previous-revision migration and exact rollback."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    previous_plan = _fixture_plan(fixture_root / "previous-v0.0.1" / "workspace-plan.json")
    revision_nine_plan = _fixture_plan(fixture_root / "revision-9" / "workspace-plan.json")
    if (
        previous_plan.get("application_version") != "0.0.1"
        or previous_plan.get("catalog_revision") != CURRENT_SCHEMA_VERSION
        or revision_nine_plan.get("catalog_revision") != CURRENT_SCHEMA_VERSION - 1
    ):
        raise ReproductionEvidenceMalformed("previous workspace fixture contract is invalid")

    scratch.mkdir(parents=True, exist_ok=False)
    previous = scratch / "previous"
    LocalWorkspace.initialize(previous, now=now)
    opened = LocalWorkspace.open(previous)
    previous_passed = opened.catalog.schema_version() == CURRENT_SCHEMA_VERSION

    revision_nine = scratch / "revision-ten"
    _initialize_historical_workspace(revision_nine, now=now)
    backup = scratch / "pre-upgrade-backup"
    migrated = LocalWorkspace.migrate(revision_nine, backup, now=now)
    migration_passed = migrated.catalog.schema_version() == CURRENT_SCHEMA_VERSION
    restored = scratch / "restored-revision-ten"
    report = LocalWorkspace.restore(backup, restored, now=now)
    rollback_passed = (
        report.catalog_schema_version == CURRENT_SCHEMA_VERSION - 1
        and SQLiteCatalog(restored / "catalog.sqlite3", migrations=MIGRATIONS[:-1]).schema_version()
        == CURRENT_SCHEMA_VERSION - 1
    )
    return (
        ReproductionResult(
            "previous-workspace-open",
            "passed" if previous_passed else "failed",
            0,
            None if previous_passed else "previous-workspace-open-failed",
            (canonical_sha256(cast(JsonValue, previous_plan)),),
        ),
        ReproductionResult(
            # Stable release-evidence check ID retained for schema compatibility.
            "revision-nine-migration",
            "passed" if migration_passed else "failed",
            0,
            None if migration_passed else "revision-nine-migration-failed",
            (canonical_sha256(cast(JsonValue, revision_nine_plan)),),
        ),
        ReproductionResult(
            "backup-upgrade-restore",
            "passed" if rollback_passed else "failed",
            0,
            None if rollback_passed else "backup-restore-mismatch",
            (report.manifest_id,),
        ),
    )


def _fixture_plan(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReproductionEvidenceMalformed("previous workspace fixture is malformed") from error
    if not isinstance(value, dict) or value.get("synthetic") is not True:
        raise ReproductionEvidenceMalformed("previous workspace fixture is malformed")
    return cast(dict[str, object], value)


def _initialize_historical_workspace(root: Path, *, now: datetime) -> None:
    root.mkdir(parents=True, exist_ok=False)
    FilesystemObjectStore(root)
    (root / "staging").mkdir(exist_ok=True)
    SQLiteCatalog(root / "catalog.sqlite3", migrations=MIGRATIONS[:-1]).initialize(now=now)
    marker = {
        "catalog": "catalog.sqlite3",
        "format": "openardp-local-workspace",
        "objects": "objects",
        "staging": "staging",
        "version": 1,
    }
    _write_atomic(
        root / ".openardp-workspace.json",
        canonical_json_bytes(cast(JsonValue, marker)),
    )


def _write_atomic(path: Path, data: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _zip_members(path: Path, canaries: Sequence[bytes]) -> list[dict[str, object]]:
    members: list[dict[str, object]] = []
    expanded = 0
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > _MAX_MEMBERS:
                raise ReproductionEvidenceMalformed("artifact member count is invalid")
            for info in infos:
                _safe_member(info.filename)
                expanded += info.file_size
                if expanded > _MAX_EXPANDED_BYTES:
                    raise ReproductionEvidenceMalformed("artifact expanded size exceeds limit")
                body = archive.read(info)
                _reject_canaries(body, canaries)
                members.append(_member(info.filename, info.file_size, body))
    except (OSError, zipfile.BadZipFile) as error:
        raise ReproductionEvidenceMalformed("wheel is malformed") from error
    return sorted(members, key=lambda item: str(item["path"]))


def _tar_members(path: Path, canaries: Sequence[bytes]) -> list[dict[str, object]]:
    members: list[dict[str, object]] = []
    expanded = 0
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            infos = archive.getmembers()
            if not infos or len(infos) > _MAX_MEMBERS:
                raise ReproductionEvidenceMalformed("artifact member count is invalid")
            for info in infos:
                _safe_member(info.name)
                if info.issym() or info.islnk() or info.isdev():
                    raise ReproductionEvidenceMalformed("source distribution member is unsafe")
                if not info.isfile():
                    continue
                expanded += info.size
                if expanded > _MAX_EXPANDED_BYTES:
                    raise ReproductionEvidenceMalformed("artifact expanded size exceeds limit")
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise ReproductionEvidenceMalformed("artifact member is unreadable")
                body = extracted.read()
                _reject_canaries(body, canaries)
                members.append(_member(info.name, info.size, body))
    except (OSError, tarfile.TarError) as error:
        raise ReproductionEvidenceMalformed("source distribution is malformed") from error
    return sorted(members, key=lambda item: str(item["path"]))


def _member(path: str, byte_length: int, body: bytes) -> dict[str, object]:
    return {
        "path": path,
        "byte_length": byte_length,
        "sha256": f"sha256:{hashlib.sha256(body).hexdigest()}",
    }


def _safe_member(value: str) -> None:
    candidate = PurePosixPath(value)
    if (
        not value
        or candidate.is_absolute()
        or ".." in candidate.parts
        or "\\" in value
        or any(part in _FORBIDDEN_MEMBER_PARTS for part in candidate.parts)
    ):
        raise ReproductionEvidenceMalformed("artifact member path is unsafe")


def _reject_canaries(body: bytes, canaries: Sequence[bytes]) -> None:
    if any(canary and canary in body for canary in canaries):
        raise ReproductionEvidenceMalformed("artifact contains a forbidden privacy canary")


__all__ = [
    "ArtifactInventory",
    "ReproductionEvidenceMalformed",
    "ReproductionResult",
    "inspect_artifact",
    "platform_semantics_agree",
    "reproduce_workspace_recovery",
    "reproduction_checks",
]
