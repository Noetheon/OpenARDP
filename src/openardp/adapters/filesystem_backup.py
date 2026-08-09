"""Verified backup and restore operations for local OpenARDP workspaces."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from openardp.adapters.compact_objects import PROFILE, CompactObjectError, decode_compact
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.maintenance import (
    BackupFile,
    BackupManifest,
    BackupReport,
    InventoryLimits,
    MaintenanceAnomalyCode,
    MaintenanceObject,
    RestoreReport,
)
from openardp.ports.maintenance import InsufficientSpace, MaintenanceError, StoreInconsistent

if TYPE_CHECKING:
    from openardp.adapters.filesystem_maintenance import FilesystemMaintenanceStore
    from openardp.adapters.sqlite_catalog import SQLiteCatalog

_CHUNK_SIZE = 1024 * 1024
_BACKUP_LIMITS = InventoryLimits(max_entries=1_000_000, max_bytes=9_007_199_254_740_991)
_OBJECT_ID = re.compile(r"^sha256:([0-9a-f]{64})$")


def backup_workspace(
    root: Path,
    catalog: SQLiteCatalog,
    store: FilesystemMaintenanceStore,
    destination: Path,
    *,
    now: datetime,
    migrate_at_exit: bool = False,
    reserve_bytes: int = 64 * 1024 * 1024,
    expected_revision: int | None = None,
    fault: Callable[[str], None] | None = None,
) -> BackupReport:
    """Create, verify and publish one complete internal workspace backup."""
    source_root = root.resolve(strict=True)
    target = _fresh_disjoint_target(source_root, destination)
    try:
        target.mkdir(mode=0o700)
    except FileExistsError:
        raise MaintenanceError("destination must be absent") from None
    staging = target / f".openardp-backup-{uuid4().hex}.part"
    staging.mkdir(mode=0o700)
    workspace = staging / "workspace"
    workspace.mkdir(mode=0o700)
    (workspace / "objects" / "sha256").mkdir(parents=True, mode=0o700)
    (workspace / "quarantine" / "sha256").mkdir(parents=True, mode=0o700)
    (workspace / "staging").mkdir(mode=0o700)
    staged_catalog = workspace / "catalog.sqlite3"
    manifest_holder: dict[str, str] = {}
    inject = fault or (lambda _point: None)
    published = False
    manifest: BackupManifest | None = None
    try:
        with catalog.consistent_backup(
            staged_catalog,
            now=now,
            migrate_at_exit=migrate_at_exit,
            manifest_id_supplier=lambda: manifest_holder["manifest_id"],
            expected_revision=expected_revision,
        ) as source_revision:
            inject("after_catalog_snapshot")
            inventory = store.inventory(_BACKUP_LIMITS)
            unsafe = tuple(
                item
                for item in inventory.anomalies
                if item.code is not MaintenanceAnomalyCode.STAGING_RESIDUE
            )
            if unsafe:
                raise StoreInconsistent("managed storage is inconsistent")
            available_ids = {item.object_id for item in (*inventory.active, *inventory.quarantined)}
            if not set(catalog.backup_root_object_ids()).issubset(available_ids):
                raise StoreInconsistent("catalog references unavailable managed bytes")
            required_bytes = (
                sum(item.byte_length for item in inventory.active)
                + sum(item.byte_length for item in inventory.quarantined)
                + (source_root / "catalog.sqlite3").stat().st_size
                + (source_root / ".openardp-workspace.json").stat().st_size
            )
            if not store.capacity(required_bytes, reserve_bytes).admitted:
                raise InsufficientSpace("insufficient capacity for backup")
            files: list[BackupFile] = []
            files.append(
                _copy_backup_file(
                    source_root / ".openardp-workspace.json",
                    workspace / ".openardp-workspace.json",
                    relative_path="workspace/.openardp-workspace.json",
                )
            )
            for item in inventory.active:
                relative = _physical_object_relative(item, location="objects")
                files.append(
                    _copy_backup_file(
                        source_root / relative,
                        workspace / relative,
                        relative_path=f"workspace/{relative.as_posix()}",
                    )
                )
                inject("after_object_copy")
            for item in inventory.quarantined:
                relative = _physical_object_relative(item, location="quarantine")
                files.append(
                    _copy_backup_file(
                        source_root / relative,
                        workspace / relative,
                        relative_path=f"workspace/{relative.as_posix()}",
                    )
                )
            catalog_revision, migration_checksums = catalog.normalize_backup_copy(staged_catalog)
            if catalog_revision != source_revision:
                raise MaintenanceError("backup catalog revision drifted")
            files.append(
                _inspect_backup_file(
                    staged_catalog,
                    relative_path="workspace/catalog.sqlite3",
                )
            )
            manifest = BackupManifest.create(
                created_at=now,
                catalog_schema_version=catalog_revision,
                migration_checksums=migration_checksums,
                files=tuple(files),
                active_object_ids=tuple(item.object_id for item in inventory.active),
                quarantined_object_ids=tuple(item.object_id for item in inventory.quarantined),
                excluded_staging_count=sum(
                    item.code is MaintenanceAnomalyCode.STAGING_RESIDUE
                    for item in inventory.anomalies
                ),
            )
            _write_new_file(
                staging / "manifest.json",
                canonical_json_bytes(manifest.model_dump(mode="json")),
            )
            _verify_backup_tree(staging, manifest)
            _write_new_file(staging / "COMPLETE", (manifest.manifest_id + "\n").encode())
            _sync_directory(staging)
            manifest_holder["manifest_id"] = manifest.manifest_id
            inject("before_backup_publication")
            os.rename(staging / "workspace", target / "workspace")
            os.rename(staging / "manifest.json", target / "manifest.json")
            os.rename(staging / "COMPLETE", target / "COMPLETE")
            staging.rmdir()
            _sync_directory(target)
            _sync_directory(target.parent)
            published = True
            inject("after_backup_publication")
            if migrate_at_exit:
                type(store)(source_root, create=True)
        assert manifest is not None
        return BackupReport(
            manifest_id=manifest.manifest_id,
            catalog_schema_version=manifest.catalog_schema_version,
            file_count=len(manifest.files),
            byte_count=sum(item.byte_length for item in manifest.files),
            active_object_count=len(manifest.active_object_ids),
            quarantined_object_count=len(manifest.quarantined_object_ids),
            completed_at=now,
        )
    finally:
        if not published:
            shutil.rmtree(target, ignore_errors=True)


def restore_workspace(
    backup: Path,
    destination: Path,
    *,
    now: datetime,
    reserve_bytes: int = 64 * 1024 * 1024,
) -> RestoreReport:
    """Verify one internal backup and publish it only to a fresh workspace."""
    backup_root = backup.expanduser().absolute()
    backup_metadata = backup_root.lstat()
    if _is_link_or_junction(backup_root, backup_metadata) or not stat.S_ISDIR(
        backup_metadata.st_mode
    ):
        raise MaintenanceError("backup root is unsafe")
    backup_root = backup_root.resolve(strict=True)
    target = _fresh_disjoint_target(backup_root, destination)
    manifest_bytes = _read_regular(backup_root / "manifest.json", maximum=16_777_216)
    try:
        manifest = BackupManifest.model_validate_json(manifest_bytes)
    except ValueError:
        raise MaintenanceError("backup manifest is invalid") from None
    if canonical_json_bytes(manifest.model_dump(mode="json")) != manifest_bytes:
        raise MaintenanceError("backup manifest is not canonical")
    complete = _read_regular(backup_root / "COMPLETE", maximum=256)
    if complete != (manifest.manifest_id + "\n").encode():
        raise MaintenanceError("backup completion marker is invalid")
    _verify_backup_tree(backup_root, manifest)
    expected = {item.relative_path for item in manifest.files} | {
        "manifest.json",
        "COMPLETE",
    }
    if _regular_file_inventory(backup_root) != expected:
        raise MaintenanceError("backup contains unexpected or missing files")
    usage = shutil.disk_usage(target.parent)
    required_bytes = sum(item.byte_length for item in manifest.files)
    if usage.free < required_bytes + reserve_bytes:
        raise InsufficientSpace("insufficient capacity for restore")
    try:
        target.mkdir(mode=0o700)
    except FileExistsError:
        raise MaintenanceError("destination must be absent") from None
    staging = target / f".openardp-restore-{uuid4().hex}.part"
    staging.mkdir(mode=0o700)
    (staging / "objects" / "sha256").mkdir(parents=True, mode=0o700)
    (staging / "quarantine" / "sha256").mkdir(parents=True, mode=0o700)
    (staging / "staging").mkdir(mode=0o700)
    published = False
    try:
        for entry in manifest.files:
            if not entry.relative_path.startswith("workspace/"):
                raise MaintenanceError("backup file path is outside workspace")
            relative = Path(entry.relative_path.removeprefix("workspace/"))
            copied = _copy_backup_file(
                backup_root / entry.relative_path,
                staging / relative,
                relative_path=entry.relative_path,
            )
            if copied.byte_length != entry.byte_length or copied.sha256 != entry.sha256:
                raise MaintenanceError("restored file disagrees with manifest")
        from openardp.adapters.sqlite_catalog import SQLiteCatalog
        from openardp.adapters.sqlite_migrations import MIGRATIONS

        restored_catalog = SQLiteCatalog(
            staging / "catalog.sqlite3",
            migrations=MIGRATIONS[: manifest.catalog_schema_version],
        )
        if restored_catalog.schema_version() != manifest.catalog_schema_version:
            raise MaintenanceError("restored catalog revision disagrees with manifest")
        _validate_restored_object_sets(staging, manifest)
        manifest_ids = set(manifest.active_object_ids) | set(manifest.quarantined_object_ids)
        if not set(restored_catalog.backup_root_object_ids()).issubset(manifest_ids):
            raise MaintenanceError("restored catalog references unavailable objects")
        _sync_tree(staging)
        marker = staging / ".openardp-workspace.json"
        for path in sorted(staging.iterdir(), key=lambda item: item.name):
            if path == marker:
                continue
            os.rename(path, target / path.name)
        os.rename(marker, target / marker.name)
        staging.rmdir()
        _sync_directory(target)
        _sync_directory(target.parent)
        published = True
        return RestoreReport(
            manifest_id=manifest.manifest_id,
            catalog_schema_version=manifest.catalog_schema_version,
            file_count=len(manifest.files),
            byte_count=sum(item.byte_length for item in manifest.files),
            completed_at=now,
        )
    finally:
        if not published:
            shutil.rmtree(target, ignore_errors=True)


def _fresh_disjoint_target(source: Path, destination: Path) -> Path:
    raw = destination.expanduser().absolute()
    if _lexists(raw):
        raise MaintenanceError("destination must be absent")
    parent = raw.parent.resolve(strict=True)
    metadata = parent.lstat()
    if _is_link_or_junction(parent, metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise MaintenanceError("destination parent is unsafe")
    target = parent / raw.name
    try:
        source.relative_to(target)
        overlap = True
    except ValueError:
        try:
            target.relative_to(source)
            overlap = True
        except ValueError:
            overlap = False
    if overlap:
        raise MaintenanceError("source and destination overlap")
    return target


def _copy_backup_file(source: Path, destination: Path, *, relative_path: str) -> BackupFile:
    before = source.lstat()
    if (
        _is_link_or_junction(source, before)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        raise MaintenanceError("backup source file is unsafe")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    source_descriptor = os.open(source, _file_open_flags(os.O_RDONLY))
    destination_descriptor: int | None = None
    digest = hashlib.sha256()
    observed = 0
    try:
        opened = os.fstat(source_descriptor)
        if _identity(opened) != _identity(before):
            raise MaintenanceError("backup source changed while opening")
        destination_descriptor = os.open(
            destination,
            _file_open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            0o600,
        )
        while chunk := os.read(source_descriptor, _CHUNK_SIZE):
            view = memoryview(chunk)
            while view:
                written = os.write(destination_descriptor, view)
                if written == 0:
                    raise MaintenanceError("backup destination write made no progress")
                view = view[written:]
            digest.update(chunk)
            observed += len(chunk)
        os.fsync(destination_descriptor)
        if os.name == "nt":
            replayed, replay_digest = _hash_open_descriptor(
                source_descriptor,
                maximum=before.st_size,
            )
            if replayed != observed or replay_digest != digest.digest():
                raise MaintenanceError("backup source changed while copying")
        after = os.fstat(source_descriptor)
        if (
            not _unchanged_after_read(opened, after)
            or before.st_size != after.st_size
            or observed != after.st_size
        ):
            raise MaintenanceError("backup source changed while copying")
    finally:
        if destination_descriptor is not None:
            os.close(destination_descriptor)
        os.close(source_descriptor)
    _sync_directory(destination.parent)
    return BackupFile(
        relative_path=relative_path,
        byte_length=observed,
        sha256="sha256:" + digest.hexdigest(),
    )


def _inspect_backup_file(path: Path, *, relative_path: str) -> BackupFile:
    byte_length, digest = _hash_regular(path, maximum=9_007_199_254_740_991)
    return BackupFile(
        relative_path=relative_path,
        byte_length=byte_length,
        sha256=digest,
    )


def _verify_backup_tree(root: Path, manifest: BackupManifest) -> None:
    for entry in manifest.files:
        byte_length, digest = _hash_regular(
            root / entry.relative_path,
            maximum=entry.byte_length,
        )
        if byte_length != entry.byte_length:
            raise MaintenanceError("backup file length disagrees with manifest")
        if digest != entry.sha256:
            raise MaintenanceError("backup file identity disagrees with manifest")


def _validate_restored_object_sets(root: Path, manifest: BackupManifest) -> None:
    for object_id, location in (
        *((item, "objects") for item in manifest.active_object_ids),
        *((item, "quarantine") for item in manifest.quarantined_object_ids),
    ):
        relative = _object_relative(object_id)
        ordinary = root / location / "sha256" / relative
        compact = root / location / PROFILE / "sha256" / relative
        present = tuple(path for path in (ordinary, compact) if path.exists())
        if len(present) != 1:
            raise MaintenanceError("restored object physical form is inconsistent")
        path = present[0]
        if path == compact:
            envelope = _read_regular(path, maximum=16 * 1024 * 1024)
            try:
                logical = decode_compact(envelope)
            except CompactObjectError:
                raise MaintenanceError("restored compact object is invalid") from None
            digest = "sha256:" + hashlib.sha256(logical).hexdigest()
        else:
            _byte_length, digest = _hash_regular(
                path,
                maximum=9_007_199_254_740_991,
            )
        if digest != object_id:
            raise MaintenanceError("restored object identity is invalid")


def _regular_file_inventory(root: Path) -> set[str]:
    result: set[str] = set()
    for current, directories, files in os.walk(root, followlinks=False):
        base = Path(current)
        for name in tuple(directories):
            path = base / name
            metadata = path.lstat()
            if _is_link_or_junction(path, metadata):
                raise MaintenanceError("backup contains unsafe directory")
        for name in files:
            path = base / name
            metadata = path.lstat()
            if (
                _is_link_or_junction(path, metadata)
                or not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
            ):
                raise MaintenanceError("backup contains unsafe file")
            result.add(path.relative_to(root).as_posix())
    return result


def _read_regular(path: Path, *, maximum: int) -> bytes:
    metadata = path.lstat()
    if (
        _is_link_or_junction(path, metadata)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size > maximum
    ):
        raise MaintenanceError("regular file validation failed")
    descriptor = os.open(path, _file_open_flags(os.O_RDONLY))
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(metadata):
            raise MaintenanceError("regular file changed while opening")
        payload = _read_open_descriptor(descriptor, maximum=maximum)
        if os.name == "nt" and payload != _read_open_descriptor(descriptor, maximum=maximum):
            raise MaintenanceError("regular file changed while reading")
        after = os.fstat(descriptor)
        if not _unchanged_after_read(opened, after) or metadata.st_size != len(payload):
            raise MaintenanceError("regular file changed while reading")
    finally:
        os.close(descriptor)
    return payload


def _hash_regular(path: Path, *, maximum: int) -> tuple[int, str]:
    metadata = path.lstat()
    if (
        _is_link_or_junction(path, metadata)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size > maximum
    ):
        raise MaintenanceError("regular file validation failed")
    descriptor = os.open(path, _file_open_flags(os.O_RDONLY))
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(metadata):
            raise MaintenanceError("regular file changed while opening")
        observed, digest = _hash_open_descriptor(descriptor, maximum=maximum)
        if os.name == "nt":
            replayed, replay_digest = _hash_open_descriptor(descriptor, maximum=maximum)
            if replayed != observed or replay_digest != digest:
                raise MaintenanceError("regular file changed while reading")
        after = os.fstat(descriptor)
        if not _unchanged_after_read(opened, after) or metadata.st_size != observed:
            raise MaintenanceError("regular file changed while reading")
    finally:
        os.close(descriptor)
    return observed, "sha256:" + digest.hex()


def _read_open_descriptor(descriptor: int, *, maximum: int) -> bytes:
    """Read one bounded descriptor from the beginning for stability replay."""
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    observed = 0
    while chunk := os.read(descriptor, _CHUNK_SIZE):
        observed += len(chunk)
        if observed > maximum:
            raise MaintenanceError("regular file exceeds limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _hash_open_descriptor(descriptor: int, *, maximum: int) -> tuple[int, bytes]:
    """Hash one bounded descriptor from the beginning for stability replay."""
    os.lseek(descriptor, 0, os.SEEK_SET)
    observed = 0
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, _CHUNK_SIZE):
        observed += len(chunk)
        if observed > maximum:
            raise MaintenanceError("regular file exceeds limit")
        digest.update(chunk)
    return observed, digest.digest()


def _write_new_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        _file_open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written == 0:
                raise MaintenanceError("file publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _sync_directory(path.parent)


def _object_relative(object_id: str) -> Path:
    match = _OBJECT_ID.fullmatch(object_id)
    if match is None:
        raise MaintenanceError("backup object identity is invalid")
    digest = match.group(1)
    return Path(digest[:2]) / digest[2:4] / digest[4:]


def _physical_object_relative(item: MaintenanceObject, *, location: str) -> Path:
    """Return the closed workspace-relative leaf for one observed physical form."""
    prefix = (
        Path(location) / "sha256"
        if item.physical_profile == "ordinary"
        else Path(location) / PROFILE / "sha256"
    )
    return prefix / _object_relative(item.object_id)


def _sync_tree(root: Path) -> None:
    for current, _directories, files in os.walk(root, topdown=False):
        base = Path(current)
        for name in files:
            descriptor = os.open(base / name, _file_open_flags(os.O_RDWR))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        _sync_directory(base)


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _unchanged_after_read(opened: os.stat_result, after: os.stat_result) -> bool:
    """Require the same open filesystem identity after I/O."""
    return _identity(opened) == _identity(after)


def _file_open_flags(base: int) -> int:
    """Add portable safety flags and mandatory Windows binary mode."""
    return (
        base
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda _: False)
    return stat.S_ISLNK(metadata.st_mode) or bool(is_junction(path))
