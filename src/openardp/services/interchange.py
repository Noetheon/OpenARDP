"""Trusted-operator orchestration for experimental package exchange."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from contextlib import suppress
from pathlib import Path

from openardp.adapters.bagit_interchange import (
    BagItPackageAdapter,
    owned_temporary_file,
    sync_directory,
)
from openardp.domain.identity import canonical_sha256
from openardp.domain.interchange import (
    ImportPlan,
    InterchangeLimits,
    InterchangeOperation,
    InterchangeOutcome,
    InterchangePackage,
    InterchangeResult,
    VerifiedPackage,
    import_plan_identity,
)
from openardp.ports.interchange import (
    AssetByteSource,
    InterchangeDestinationConflict,
    InterchangePublicationFailed,
)


class InterchangeService:
    """Export, verify and import through one strict BagIt profile adapter."""

    def __init__(self, adapter: BagItPackageAdapter | None = None) -> None:
        """Use the stdlib BagIt adapter unless explicitly replaced for tests."""
        self._adapter = adapter or BagItPackageAdapter()

    def export(
        self,
        package: InterchangePackage,
        source: AssetByteSource,
        destination: Path,
        *,
        limits: InterchangeLimits | None = None,
    ) -> InterchangeResult:
        """Create, self-verify and atomically publish a deterministic package."""
        effective = limits or InterchangeLimits()
        target = _fresh_target(destination)
        with owned_temporary_file(target) as staging:
            self._adapter.write_staged(package, source, staging, limits=effective)
            verified = self._adapter.verify(staging, limits=effective)
            if verified.package != package:
                raise InterchangePublicationFailed("self-verification changed package facts")
            outcome = self._publish_file(staging, target, verified, limits=effective)
        return _result(InterchangeOperation.EXPORT, outcome, verified)

    def verify(
        self,
        package: Path,
        *,
        limits: InterchangeLimits | None = None,
    ) -> InterchangeResult:
        """Return one complete body-free verification result without publication."""
        verified = self._adapter.verify(package, limits=limits or InterchangeLimits())
        return _result(InterchangeOperation.VERIFY, InterchangeOutcome.COMPLETE, verified)

    def import_snapshot(
        self,
        package: Path,
        destination: Path,
        *,
        limits: InterchangeLimits | None = None,
    ) -> InterchangeResult:
        """Publish one fresh fully verified immutable package snapshot."""
        effective = limits or InterchangeLimits()
        target = _fresh_target(destination)
        verified = self._adapter.verify(package, limits=effective)
        plan = _import_plan(verified, target, effective)
        if _lexists(target):
            if self._adapter.verify_snapshot(target, verified):
                return _result(InterchangeOperation.IMPORT, InterchangeOutcome.CONVERGED, verified)
            raise InterchangeDestinationConflict("destination already contains other data")
        staging = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.import-", dir=target.parent)
        ).resolve(strict=True)
        published = False
        try:
            self._adapter.copy_verified_snapshot(
                package,
                verified,
                staging,
                limits=effective,
            )
            if not self._adapter.verify_snapshot(staging, verified):
                raise InterchangePublicationFailed("staged snapshot verification failed")
            if _import_plan(verified, target, effective) != plan:
                raise InterchangeDestinationConflict("destination authority changed")
            _freeze_snapshot(staging)
            sync_directory(staging)
            try:
                os.rename(staging, target)
                published = True
                sync_directory(target.parent)
                outcome = InterchangeOutcome.COMPLETE
            except OSError:
                if _lexists(target) and self._adapter.verify_snapshot(target, verified):
                    outcome = InterchangeOutcome.CONVERGED
                elif _lexists(target):
                    raise InterchangeDestinationConflict(
                        "destination publication conflicts with existing data"
                    ) from None
                else:
                    raise InterchangePublicationFailed("snapshot publication failed") from None
        finally:
            if not published:
                with suppress(OSError):
                    _thaw_snapshot(staging)
                    shutil.rmtree(staging)
        return _result(InterchangeOperation.IMPORT, outcome, verified)

    def _publish_file(
        self,
        staging: Path,
        target: Path,
        verified: VerifiedPackage,
        *,
        limits: InterchangeLimits,
    ) -> InterchangeOutcome:
        try:
            with staging.open("r+b") as stream:
                stream.flush()
                os.fsync(stream.fileno())
            if os.name == "nt":
                os.rename(staging, target)
            else:
                os.link(staging, target, follow_symlinks=False)
                staging.unlink()
            sync_directory(target.parent)
            return InterchangeOutcome.COMPLETE
        except FileExistsError:
            pass
        except OSError:
            if not _lexists(target):
                raise InterchangePublicationFailed("package publication failed") from None
        try:
            existing = self._adapter.verify(target, limits=limits)
        except Exception:
            raise InterchangeDestinationConflict(
                "destination already contains other data"
            ) from None
        if existing != verified:
            raise InterchangeDestinationConflict("destination already contains other data")
        return InterchangeOutcome.CONVERGED


def _fresh_target(path: Path) -> Path:
    raw = path.expanduser().absolute()
    parent = raw.parent
    try:
        metadata = parent.lstat()
    except OSError:
        raise InterchangeDestinationConflict("destination parent is unavailable") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise InterchangeDestinationConflict("destination parent is unsafe")
    return raw


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _import_plan(
    verified: VerifiedPackage,
    target: Path,
    limits: InterchangeLimits,
) -> ImportPlan:
    """Bind verified bytes and limits to the still-current destination authority."""
    try:
        parent = target.parent.lstat()
    except OSError:
        raise InterchangeDestinationConflict("destination parent is unavailable") from None
    if stat.S_ISLNK(parent.st_mode) or not stat.S_ISDIR(parent.st_mode):
        raise InterchangeDestinationConflict("destination parent is unsafe")
    target_id = canonical_sha256(
        {
            "algorithm": "interchange-target-v1",
            "destination": os.fsencode(str(target)).hex(),
            "parent_device": str(parent.st_dev),
            "parent_inode": str(parent.st_ino),
        }
    )
    values: dict[str, object] = {
        "plan_id": "sha256:" + ("0" * 64),
        "package_id": verified.package.package_id,
        "archive_sha256": verified.archive_sha256,
        "target_id": target_id,
        "limits": limits,
        "inventory": verified.inventory,
    }
    values["plan_id"] = import_plan_identity(values)
    return ImportPlan.model_validate(values)


def _freeze_snapshot(root: Path) -> None:
    """Make the published experiment snapshot read-only by default."""
    directories: list[Path] = []
    for current, names, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories.append(current_path)
        for name in files:
            (current_path / name).chmod(0o444)
        for name in names:
            child = current_path / name
            if child.is_symlink():
                raise InterchangePublicationFailed("staged snapshot contains a link")
    for directory in reversed(directories):
        sync_directory(directory)
        directory.chmod(0o555)


def _thaw_snapshot(root: Path) -> None:
    """Restore owner permissions only on operation-owned staging for cleanup."""
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        with suppress(OSError):
            current_path.chmod(0o700)
        for name in directories:
            with suppress(OSError):
                (current_path / name).chmod(0o700)
        for name in files:
            with suppress(OSError):
                (current_path / name).chmod(0o600)


def _result(
    operation: InterchangeOperation,
    outcome: InterchangeOutcome,
    verified: VerifiedPackage,
) -> InterchangeResult:
    record = verified.package
    return InterchangeResult(
        operation=operation,
        outcome=outcome,
        package_id=record.package_id,
        profile_version=record.profile_version,
        schema_version=record.schema_version,
        archive_sha256=verified.archive_sha256,
        archive_bytes=verified.archive_bytes,
        entry_count=len(verified.inventory),
        payload_bytes=verified.payload_bytes,
        record_count=len(record.records),
        asset_count=len(record.assets),
        relationship_count=len(record.relationships),
    )


__all__ = ["InterchangeService"]
