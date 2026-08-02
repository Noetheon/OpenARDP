"""Bounded exact-object filesystem maintenance for one validated local workspace."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from openardp.adapters.compact_objects import PROFILE, CompactObjectError, decode_compact
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.maintenance import (
    BackupFile,
    BackupManifest,
    BackupReport,
    CapacityReport,
    InventoryLimits,
    MaintenanceAnomaly,
    MaintenanceAnomalyCode,
    MaintenanceInventory,
    MaintenanceObject,
    ObjectLocation,
    RestoreReport,
    StorageCategory,
    StorageDiagnostic,
    StorageHealth,
)
from openardp.ports.maintenance import (
    InsufficientSpace,
    InventoryOverflow,
    MaintenanceError,
    StoreInconsistent,
)

if TYPE_CHECKING:
    from openardp.adapters.sqlite_catalog import SQLiteCatalog

_FANOUT = re.compile(r"^[0-9a-f]{2}$")
_LEAF = re.compile(r"^[0-9a-f]{60}$")
_OBJECT_ID = re.compile(r"^sha256:([0-9a-f]{64})$")
_CHUNK_SIZE = 1024 * 1024
_BACKUP_LIMITS = InventoryLimits(
    max_entries=1_000_000,
    max_bytes=9_007_199_254_740_991,
)
PhysicalProfile = Literal["ordinary", "openardp-deflate-dict-v1"]
_ORDINARY_PROFILE: PhysicalProfile = "ordinary"
_COMPACT_PROFILE: PhysicalProfile = "openardp-deflate-dict-v1"


class FilesystemMaintenanceStore:
    """Only adapter allowed to inspect and mutate managed maintenance locations."""

    def __init__(
        self,
        root: Path,
        *,
        create: bool = False,
        allow_missing_quarantine: bool = False,
    ) -> None:
        """Bind one canonical workspace and optionally create revision-10 layout."""
        raw = root.expanduser().absolute()
        metadata = raw.lstat()
        if self._is_link_or_junction(raw, metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise MaintenanceError("workspace storage is unsafe")
        self._root = raw.resolve(strict=True)
        self._active = self._root / "objects" / "sha256"
        self._active_compact = self._root / "objects" / PROFILE / "sha256"
        self._staging = self._root / "staging"
        self._quarantine = self._root / "quarantine" / "sha256"
        self._quarantine_compact = self._root / "quarantine" / PROFILE / "sha256"
        if create:
            self._ensure_directory(self._root / "quarantine")
            self._ensure_directory(self._quarantine)
            self._ensure_directory(self._root / "quarantine" / PROFILE)
            self._ensure_directory(self._quarantine_compact)
        for path in (self._active, self._staging):
            self._assert_directory(path)
        if self._lexists(self._active_compact):
            self._assert_directory(self._root / "objects" / PROFILE)
            self._assert_directory(self._active_compact)
        self._quarantine_available = self._lexists(self._quarantine)
        if self._quarantine_available:
            self._assert_directory(self._quarantine)
            if self._lexists(self._quarantine_compact):
                self._assert_directory(self._root / "quarantine" / PROFILE)
                self._assert_directory(self._quarantine_compact)
        elif not allow_missing_quarantine:
            raise MaintenanceError("managed maintenance directory is missing")

    def inventory(self, limits: InventoryLimits) -> MaintenanceInventory:
        """Return one complete bounded verified active/quarantine inventory."""
        active, active_anomalies, entries, byte_count = self._scan_tree(
            self._active,
            location=ObjectLocation.ACTIVE,
            limits=limits,
            entries=0,
            byte_count=0,
            physical_profile=_ORDINARY_PROFILE,
        )
        if self._lexists(self._active_compact):
            compact, compact_anomalies, entries, byte_count = self._scan_tree(
                self._active_compact,
                location=ObjectLocation.ACTIVE,
                limits=limits,
                entries=entries,
                byte_count=byte_count,
                physical_profile=_COMPACT_PROFILE,
            )
            active, duplicate_anomalies, entries = self._merge_physical_forms(
                active,
                compact,
                limits=limits,
                entries=entries,
            )
            active_anomalies.extend((*compact_anomalies, *duplicate_anomalies))
        if self._quarantine_available:
            quarantined, quarantine_anomalies, entries, byte_count = self._scan_tree(
                self._quarantine,
                location=ObjectLocation.QUARANTINE,
                limits=limits,
                entries=entries,
                byte_count=byte_count,
                physical_profile=_ORDINARY_PROFILE,
            )
            if self._lexists(self._quarantine_compact):
                compact, compact_anomalies, entries, byte_count = self._scan_tree(
                    self._quarantine_compact,
                    location=ObjectLocation.QUARANTINE,
                    limits=limits,
                    entries=entries,
                    byte_count=byte_count,
                    physical_profile=_COMPACT_PROFILE,
                )
                quarantined, duplicate_anomalies, entries = self._merge_physical_forms(
                    quarantined,
                    compact,
                    limits=limits,
                    entries=entries,
                )
                quarantine_anomalies.extend((*compact_anomalies, *duplicate_anomalies))
        else:
            quarantined, quarantine_anomalies = [], []
        anomalies = [*active_anomalies, *quarantine_anomalies]
        active_ids = {item.object_id for item in active}
        for item in quarantined:
            if item.object_id in active_ids:
                anomalies.append(
                    self._anomaly(
                        MaintenanceAnomalyCode.DUPLICATE_LOCATION,
                        f"duplicate/{item.object_id}",
                        object_id=item.object_id,
                    )
                )
                entries = self._admit_entry(entries, limits)
        for entry in self._scandir(self._staging):
            entries = self._admit_entry(entries, limits)
            anomalies.append(
                self._anomaly(MaintenanceAnomalyCode.STAGING_RESIDUE, f"staging/{entry.name}")
            )
        return MaintenanceInventory(
            active=tuple(sorted(active, key=lambda item: item.object_id)),
            quarantined=tuple(sorted(quarantined, key=lambda item: item.object_id)),
            anomalies=tuple(
                sorted(
                    set(anomalies),
                    key=lambda item: (
                        item.location_digest,
                        item.code.value,
                        item.object_id or "",
                    ),
                )
            ),
            scanned_entries=entries,
            scanned_bytes=byte_count,
        )

    def _merge_physical_forms(
        self,
        ordinary: list[MaintenanceObject],
        compact: list[MaintenanceObject],
        *,
        limits: InventoryLimits,
        entries: int,
    ) -> tuple[list[MaintenanceObject], list[MaintenanceAnomaly], int]:
        """Deduplicate logical identities while exposing recoverable physical residue."""
        merged = {item.object_id: item for item in ordinary}
        anomalies: list[MaintenanceAnomaly] = []
        for item in compact:
            peer = merged.get(item.object_id)
            if peer is not None:
                if peer.byte_length != item.byte_length:
                    raise StoreInconsistent("physical object forms disagree")
                entries = self._admit_entry(entries, limits)
                anomalies.append(
                    self._anomaly(
                        MaintenanceAnomalyCode.DUPLICATE_PHYSICAL_FORM,
                        f"physical-duplicate/{item.object_id}",
                        object_id=item.object_id,
                    )
                )
            merged[item.object_id] = item
        return list(merged.values()), anomalies, entries

    def transition(self, object_id: str, *, to_quarantine: bool, byte_length: int) -> None:
        """Move exact bytes between managed trees without overwrite, idempotently."""
        if type(byte_length) is not int or byte_length < 0:
            raise ValueError("byte_length must be a non-negative integer")
        source_roots = (
            (self._active, self._active_compact)
            if to_quarantine
            else (self._quarantine, self._quarantine_compact)
        )
        destination_roots = (
            (self._quarantine, self._quarantine_compact)
            if to_quarantine
            else (self._active, self._active_compact)
        )
        source_forms = self._present_forms(object_id, source_roots)
        destination_forms = self._present_forms(object_id, destination_roots)
        if len(source_forms) > 1 or len(destination_forms) > 1:
            raise MaintenanceError("transition physical forms conflict")
        expected_location = ObjectLocation.QUARANTINE if to_quarantine else ObjectLocation.ACTIVE
        if not source_forms:
            if not destination_forms:
                raise MaintenanceError("transition object is missing")
            destination, physical_profile = destination_forms[0]
            verified = self._verify_path(
                destination,
                object_id,
                expected_location,
                physical_profile=physical_profile,
            )
            if verified.byte_length != byte_length:
                raise MaintenanceError("transition destination length conflicts")
            return
        source, physical_profile = source_forms[0]
        destination_root = destination_roots[1 if physical_profile == PROFILE else 0]
        destination = self._path_for(object_id, destination_root)
        other_destination = self._path_for(
            object_id,
            destination_roots[0 if physical_profile == PROFILE else 1],
        )
        if self._lexists(other_destination):
            raise MaintenanceError("transition destination physical form conflicts")
        self._ensure_directory(destination.parent.parent)
        self._ensure_directory(destination.parent)
        source_location = ObjectLocation.ACTIVE if to_quarantine else ObjectLocation.QUARANTINE
        if self._lexists(destination):
            self._converge_transition(
                source,
                destination,
                object_id=object_id,
                byte_length=byte_length,
                expected_location=expected_location,
                physical_profile=physical_profile,
            )
            return
        if not self._lexists(source):
            raise MaintenanceError("transition object is missing")
        try:
            verified = self._verify_path(
                source,
                object_id,
                source_location,
                physical_profile=physical_profile,
            )
            if verified.byte_length != byte_length:
                raise MaintenanceError("transition source length conflicts")
            if source.stat(follow_symlinks=False).st_dev != destination.parent.stat().st_dev:
                raise MaintenanceError("transition would cross a filesystem device")
            if os.name == "nt":
                os.rename(source, destination)
            else:
                os.link(source, destination, follow_symlinks=False)
                self._sync_directory(destination.parent)
                with suppress(FileNotFoundError):
                    source.unlink()
                self._sync_directory(source.parent)
        except (MaintenanceError, OSError) as error:
            try:
                self._converge_transition(
                    source,
                    destination,
                    object_id=object_id,
                    byte_length=byte_length,
                    expected_location=expected_location,
                    physical_profile=physical_profile,
                )
            except MaintenanceError:
                if isinstance(error, MaintenanceError):
                    raise error from None
                raise MaintenanceError("managed transition failed") from None
            return
        self._converge_transition(
            source,
            destination,
            object_id=object_id,
            byte_length=byte_length,
            expected_location=expected_location,
            physical_profile=physical_profile,
        )

    def _converge_transition(
        self,
        source: Path,
        destination: Path,
        *,
        object_id: str,
        byte_length: int,
        expected_location: ObjectLocation,
        physical_profile: PhysicalProfile = _ORDINARY_PROFILE,
    ) -> None:
        """Finish or verify the single admissible exact transition end state."""
        try:
            destination_metadata = destination.lstat()
        except FileNotFoundError:
            raise MaintenanceError("transition destination is missing") from None
        try:
            source_metadata = source.lstat()
        except FileNotFoundError:
            source_metadata = None
        if source_metadata is not None:
            if (
                os.name == "nt"
                or self._identity(source_metadata) != self._identity(destination_metadata)
                or source_metadata.st_nlink != 2
                or destination_metadata.st_nlink != 2
            ):
                raise MaintenanceError("transition locations conflict")
            with suppress(FileNotFoundError):
                source.unlink()
            self._sync_directory(source.parent)
        verified = self._verify_path(
            destination,
            object_id,
            expected_location,
            physical_profile=physical_profile,
        )
        if verified.byte_length != byte_length:
            raise MaintenanceError("transition destination length conflicts")

    def remove(self, object_id: str, *, byte_length: int) -> None:
        """Remove only exact verified quarantine bytes, idempotently after intent."""
        if type(byte_length) is not int or byte_length < 0:
            raise ValueError("byte_length must be a non-negative integer")
        if self._present_forms(object_id, (self._active, self._active_compact)):
            raise MaintenanceError("removal conflicts with active object state")
        present = self._present_forms(object_id, (self._quarantine, self._quarantine_compact))
        if not present:
            return
        if len(present) != 1:
            raise MaintenanceError("removal physical forms conflict")
        quarantine, physical_profile = present[0]
        verified = self._verify_path(
            quarantine,
            object_id,
            ObjectLocation.QUARANTINE,
            physical_profile=physical_profile,
        )
        if verified.byte_length != byte_length:
            raise MaintenanceError("removal source length conflicts")
        try:
            quarantine.unlink()
            self._sync_directory(quarantine.parent)
        except OSError:
            raise MaintenanceError("managed removal failed") from None
        if self._lexists(quarantine):
            raise MaintenanceError("managed removal did not complete")

    def _present_forms(
        self,
        object_id: str,
        roots: tuple[Path, Path],
    ) -> tuple[tuple[Path, PhysicalProfile], ...]:
        """Return ordinary/compact leaves present in one logical location."""
        candidates = (
            (self._path_for(object_id, roots[0]), _ORDINARY_PROFILE),
            (self._path_for(object_id, roots[1]), _COMPACT_PROFILE),
        )
        return tuple(item for item in candidates if self._lexists(item[0]))

    def _required_unique_form(
        self,
        object_id: str,
        roots: tuple[Path, Path],
    ) -> tuple[Path, PhysicalProfile]:
        """Require one and only one physical form before maintenance mutation."""
        present = self._present_forms(object_id, roots)
        if not present:
            raise MaintenanceError("transition object is missing")
        if len(present) != 1:
            raise MaintenanceError("transition physical forms conflict")
        return present[0]

    def capacity(self, required_bytes: int, reserve_bytes: int) -> CapacityReport:
        """Return exact point-in-time admission facts for the local filesystem."""
        if min(required_bytes, reserve_bytes) < 0:
            raise ValueError("capacity byte counts must be non-negative")
        usage = shutil.disk_usage(self._root)
        return CapacityReport(
            required_bytes=required_bytes,
            reserve_bytes=reserve_bytes,
            free_bytes=usage.free,
            admitted=usage.free >= required_bytes + reserve_bytes,
        )

    def diagnostics(
        self,
        *,
        reserve_bytes: int,
        observed_at: datetime,
        index_count: int,
        index_bytes: int,
    ) -> StorageDiagnostic:
        """Measure closed logical categories without exposing managed paths."""
        if min(reserve_bytes, index_count, index_bytes) < 0:
            raise ValueError("diagnostic values must be non-negative")
        inventory = self.inventory(_BACKUP_LIMITS)
        staging_count, staging_bytes, staging_unsafe = self._tree_usage(self._staging)
        catalog_files = tuple(
            path
            for path in (
                self._root / "catalog.sqlite3",
                self._root / "catalog.sqlite3-wal",
                self._root / "catalog.sqlite3-shm",
                self._root / "catalog.sqlite3-journal",
            )
            if self._lexists(path)
        )
        catalog_bytes = 0
        for path in catalog_files:
            metadata = path.lstat()
            if _is_link_or_junction(path, metadata) or not stat.S_ISREG(metadata.st_mode):
                raise StoreInconsistent("catalog storage is inconsistent")
            catalog_bytes += metadata.st_size
        try:
            usage = shutil.disk_usage(self._root)
            health = (
                StorageHealth.INCONSISTENT
                if inventory.anomalies or staging_unsafe
                else (
                    StorageHealth.LOW_SPACE if usage.free < reserve_bytes else StorageHealth.HEALTHY
                )
            )
            total, free = usage.total, usage.free
        except OSError:
            health = StorageHealth.UNAVAILABLE
            total = free = 0
        return StorageDiagnostic(
            observed_at=observed_at,
            categories=tuple(
                sorted(
                    (
                        StorageCategory(
                            name="active",
                            count=len(inventory.active),
                            byte_count=sum(item.byte_length for item in inventory.active),
                        ),
                        StorageCategory(
                            name="catalog",
                            count=len(catalog_files),
                            byte_count=catalog_bytes,
                        ),
                        StorageCategory(
                            name="disposable_index",
                            count=index_count,
                            byte_count=index_bytes,
                        ),
                        StorageCategory(
                            name="quarantine",
                            count=len(inventory.quarantined),
                            byte_count=sum(item.byte_length for item in inventory.quarantined),
                        ),
                        StorageCategory(
                            name="staging",
                            count=staging_count,
                            byte_count=staging_bytes,
                        ),
                    ),
                    key=lambda item: item.name,
                )
            ),
            disk_total_bytes=total,
            disk_free_bytes=free,
            reserve_bytes=reserve_bytes,
            health=health,
        )

    def _tree_usage(self, root: Path) -> tuple[int, int, bool]:
        count = 0
        byte_count = 0
        unsafe = False
        for current, directories, files in os.walk(root, followlinks=False):
            base = Path(current)
            for name in tuple(directories):
                metadata = (base / name).lstat()
                if _is_link_or_junction(base / name, metadata):
                    unsafe = True
            for name in files:
                count += 1
                if count > _BACKUP_LIMITS.max_entries:
                    raise InventoryOverflow("managed inventory limit exceeded")
                path = base / name
                metadata = path.lstat()
                if (
                    _is_link_or_junction(path, metadata)
                    or not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_nlink != 1
                ):
                    unsafe = True
                else:
                    byte_count += metadata.st_size
                if byte_count > _BACKUP_LIMITS.max_bytes:
                    raise InventoryOverflow("managed inventory byte limit exceeded")
        return count, byte_count, unsafe

    def _scan_tree(
        self,
        algorithm_root: Path,
        *,
        location: ObjectLocation,
        limits: InventoryLimits,
        entries: int,
        byte_count: int,
        physical_profile: PhysicalProfile,
    ) -> tuple[list[MaintenanceObject], list[MaintenanceAnomaly], int, int]:
        objects: list[MaintenanceObject] = []
        anomalies: list[MaintenanceAnomaly] = []
        for first in self._scandir(algorithm_root):
            first_path = Path(first.path)
            if not _FANOUT.fullmatch(first.name) or not self._safe_directory(first_path):
                entries = self._admit_entry(entries, limits)
                anomalies.append(self._layout_anomaly(first_path, algorithm_root))
                continue
            for second in self._scandir(first_path):
                second_path = Path(second.path)
                if not _FANOUT.fullmatch(second.name) or not self._safe_directory(second_path):
                    entries = self._admit_entry(entries, limits)
                    anomalies.append(self._layout_anomaly(second_path, algorithm_root))
                    continue
                for leaf in self._scandir(second_path):
                    entries = self._admit_entry(entries, limits)
                    leaf_path = Path(leaf.path)
                    if not _LEAF.fullmatch(leaf.name):
                        anomalies.append(self._layout_anomaly(leaf_path, algorithm_root))
                        continue
                    object_id = f"sha256:{first.name}{second.name}{leaf.name}"
                    try:
                        item = self._verify_path(
                            leaf_path,
                            object_id,
                            location,
                            physical_profile=physical_profile,
                        )
                    except MaintenanceError:
                        anomalies.append(
                            self._anomaly(
                                MaintenanceAnomalyCode.UNSAFE_ENTRY,
                                self._relative_token(leaf_path),
                                object_id=object_id,
                            )
                        )
                        continue
                    byte_count += item.byte_length
                    if byte_count > limits.max_bytes:
                        raise InventoryOverflow("maintenance inventory byte limit exceeded")
                    objects.append(item)
        return objects, anomalies, entries, byte_count

    def _verify_path(
        self,
        path: Path,
        object_id: str,
        location: ObjectLocation,
        *,
        physical_profile: PhysicalProfile = "ordinary",
    ) -> MaintenanceObject:
        before = path.lstat()
        if (
            self._is_link_or_junction(path, before)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            raise MaintenanceError("managed object is unsafe")
        descriptor = os.open(path, _file_open_flags(os.O_RDONLY))
        digest = hashlib.sha256()
        observed = 0
        encoded = bytearray()
        try:
            opened = os.fstat(descriptor)
            if self._identity(opened) != self._identity(before) or opened.st_nlink != 1:
                raise MaintenanceError("managed object changed while opening")
            while chunk := os.read(descriptor, _CHUNK_SIZE):
                observed += len(chunk)
                if physical_profile == PROFILE:
                    encoded.extend(chunk)
                else:
                    digest.update(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        logical_length = observed
        if physical_profile == PROFILE:
            try:
                logical = decode_compact(bytes(encoded))
            except CompactObjectError:
                raise MaintenanceError("managed compact object is corrupt") from None
            digest.update(logical)
            logical_length = len(logical)
        actual_id = "sha256:" + digest.hexdigest()
        if (
            not _unchanged_after_read(opened, after)
            or before.st_size != after.st_size
            or observed != after.st_size
            or actual_id != object_id
        ):
            raise MaintenanceError("managed object is corrupt")
        return MaintenanceObject(
            object_id=object_id,
            byte_length=logical_length,
            modified_at=datetime.fromtimestamp(after.st_mtime_ns / 1_000_000_000, tz=UTC),
            location=location,
            physical_profile=physical_profile,
        )

    def _layout_anomaly(self, path: Path, root: Path) -> MaintenanceAnomaly:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = "outside"
        return self._anomaly(MaintenanceAnomalyCode.MALFORMED_ENTRY, relative)

    @staticmethod
    def _path_for(object_id: str, algorithm_root: Path) -> Path:
        match = _OBJECT_ID.fullmatch(object_id)
        if match is None:
            raise ValueError("object_id must be a SHA-256 identity")
        digest = match.group(1)
        return algorithm_root / digest[:2] / digest[2:4] / digest[4:]

    @staticmethod
    def _admit_entry(current: int, limits: InventoryLimits) -> int:
        updated = current + 1
        if updated > limits.max_entries:
            raise InventoryOverflow("maintenance inventory entry limit exceeded")
        return updated

    def _anomaly(
        self,
        code: MaintenanceAnomalyCode,
        relative: str,
        *,
        object_id: str | None = None,
    ) -> MaintenanceAnomaly:
        return MaintenanceAnomaly(
            code=code,
            location_digest=canonical_sha256(
                {"domain": "openardp:maintenance-location", "relative": relative}
            ),
            object_id=object_id,
        )

    def _relative_token(self, path: Path) -> str:
        try:
            return path.relative_to(self._root).as_posix()
        except ValueError:
            return "outside"

    def _ensure_directory(self, path: Path) -> None:
        if self._lexists(path):
            self._assert_directory(path)
            return
        path.mkdir(mode=0o700)
        self._assert_directory(path)

    @staticmethod
    def _lexists(path: Path) -> bool:
        try:
            path.lstat()
        except FileNotFoundError:
            return False
        return True

    def _assert_directory(self, path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            raise MaintenanceError("managed maintenance directory is missing") from None
        if self._is_link_or_junction(path, metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise MaintenanceError("managed maintenance directory is unsafe")

    def _safe_directory(self, path: Path) -> bool:
        try:
            self._assert_directory(path)
        except MaintenanceError:
            return False
        return True

    @staticmethod
    def _scandir(path: Path) -> tuple[os.DirEntry[str], ...]:
        with os.scandir(path) as entries:
            return tuple(sorted(entries, key=lambda item: item.name))

    @staticmethod
    def _identity(metadata: os.stat_result) -> tuple[int, int]:
        return metadata.st_dev, metadata.st_ino

    @staticmethod
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

    @staticmethod
    def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
        is_junction = getattr(os.path, "isjunction", lambda _: False)
        return stat.S_ISLNK(metadata.st_mode) or bool(is_junction(path))


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
                FilesystemMaintenanceStore(source_root, create=True)
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


__all__ = [
    "FilesystemMaintenanceStore",
    "backup_workspace",
    "restore_workspace",
]
