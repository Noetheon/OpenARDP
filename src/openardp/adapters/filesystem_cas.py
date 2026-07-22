"""Safe local SHA-256 filesystem content-addressed object store."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import BinaryIO

from openardp.domain.storage import (
    ObjectInventory,
    StoreAnomaly,
    StoreAnomalyCode,
    StoredObject,
)
from openardp.ports.object_store import (
    MalformedObjectIdentity,
    ObjectCorrupt,
    ObjectDurabilityError,
    ObjectNotFound,
    ObjectPublicationError,
    ObjectStoreError,
    UnsafeStoreEntry,
)

_OBJECT_ID = re.compile(r"^sha256:([0-9a-f]{64})$")
_FANOUT = re.compile(r"^[0-9a-f]{2}$")
_LEAF = re.compile(r"^[0-9a-f]{60}$")
_DEFAULT_CHUNK_SIZE = 1024 * 1024


class FilesystemObjectStore:
    """Immutable exact-byte CAS below one local app-owned storage root."""

    def __init__(self, root: Path) -> None:
        """Create or validate the managed store directories."""
        configured = root.expanduser()
        configured.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._root = configured.resolve(strict=True)
        self._objects = self._root / "objects"
        self._algorithm_root = self._objects / "sha256"
        self._staging = self._root / "staging"
        for directory in (self._objects, self._algorithm_root, self._staging):
            self._ensure_directory(directory)

    @property
    def root(self) -> Path:
        """Return the canonical operator-configured storage root."""
        return self._root

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        """Stream, synchronize and atomically publish exact immutable bytes."""
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="object-",
            suffix=".part",
            dir=self._staging,
        )
        temporary = Path(temporary_name)
        published = False
        digest = hashlib.sha256()
        byte_length = 0
        try:
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    for chunk in chunks:
                        if not isinstance(chunk, bytes):
                            raise TypeError("object chunks must be bytes")
                        stream.write(chunk)
                        digest.update(chunk)
                        byte_length += len(chunk)
                    stream.flush()
                    self._sync_staged_file(stream.fileno())
            except Exception:
                raise ObjectPublicationError("object staging failed") from None

            object_id = "sha256:" + digest.hexdigest()
            destination = self._path_for_id(object_id)
            self._ensure_directory(destination.parent.parent)
            self._ensure_directory(destination.parent)

            if self._lexists(destination):
                return self._reuse_existing(
                    temporary,
                    object_id=object_id,
                    byte_length=byte_length,
                )

            try:
                os.replace(temporary, destination)
                published = True
            except OSError:
                if self._lexists(destination):
                    try:
                        return self._reuse_existing(
                            temporary,
                            object_id=object_id,
                            byte_length=byte_length,
                        )
                    except ObjectStoreError:
                        pass
                raise ObjectPublicationError(f"object publication failed for {object_id}") from None

            verified = self.verify(object_id, expected_length=byte_length)
            try:
                self._sync_directory(destination.parent)
            except OSError:
                raise ObjectDurabilityError(
                    f"published object durability is uncertain for {object_id}"
                ) from None
            return verified
        except ObjectStoreError:
            raise
        except Exception:
            raise ObjectPublicationError("object publication failed") from None
        finally:
            if not published:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> Iterator[bytes]:
        """Yield bounded exact object chunks from a safe regular-file handle."""
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        path = self._path_for_id(object_id)
        with self._open_regular(path, object_id=object_id) as stream:
            while chunk := stream.read(chunk_size):
                yield chunk

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject:
        """Hash a stable regular object and compare identity plus optional length."""
        if expected_length is not None and (
            type(expected_length) is not int or expected_length < 0
        ):
            raise ValueError("expected_length must be a non-negative integer")
        path = self._path_for_id(object_id)
        digest = hashlib.sha256()
        byte_length = 0
        with self._open_regular(path, object_id=object_id) as stream:
            before = os.fstat(stream.fileno())
            while chunk := stream.read(_DEFAULT_CHUNK_SIZE):
                digest.update(chunk)
                byte_length += len(chunk)
            after = os.fstat(stream.fileno())
        if (
            self._file_identity(before) != self._file_identity(after)
            or before.st_size != after.st_size
        ):
            raise ObjectCorrupt(f"object changed during verification: {object_id}")
        actual_id = "sha256:" + digest.hexdigest()
        if actual_id != object_id or byte_length != after.st_size:
            raise ObjectCorrupt(f"object digest or length mismatch: {object_id}")
        if expected_length is not None and byte_length != expected_length:
            raise ObjectCorrupt(f"object length mismatch: {object_id}")
        return StoredObject(object_id=object_id, byte_length=byte_length)

    def inventory(self) -> ObjectInventory:
        """Scan the exact fan-out tree without following or deleting entries."""
        objects: list[StoredObject] = []
        anomalies: list[StoreAnomaly] = []
        if not self._inventory_directory_is_safe(self._root, anomalies):
            return ObjectInventory(objects=(), anomalies=tuple(anomalies))
        if self._inventory_directory_is_safe(self._staging, anomalies):
            for entry in self._scandir_sorted(self._staging):
                anomalies.append(
                    StoreAnomaly(
                        code=StoreAnomalyCode.STAGING_RESIDUE,
                        relative_location=self._relative(Path(entry.path)),
                    )
                )
        if not self._inventory_directory_is_safe(self._objects, anomalies):
            return self._inventory_result(objects, anomalies)
        if not self._inventory_directory_is_safe(self._algorithm_root, anomalies):
            return self._inventory_result(objects, anomalies)
        for first in self._scandir_sorted(self._algorithm_root):
            first_path = Path(first.path)
            if not _FANOUT.fullmatch(first.name):
                anomalies.append(self._layout_anomaly(first_path, malformed=True))
                continue
            if not self._safe_directory_entry(first):
                anomalies.append(self._layout_anomaly(first_path, malformed=False))
                continue
            for second in self._scandir_sorted(first_path):
                second_path = Path(second.path)
                if not _FANOUT.fullmatch(second.name):
                    anomalies.append(self._layout_anomaly(second_path, malformed=True))
                    continue
                if not self._safe_directory_entry(second):
                    anomalies.append(self._layout_anomaly(second_path, malformed=False))
                    continue
                for leaf in self._scandir_sorted(second_path):
                    leaf_path = Path(leaf.path)
                    if not _LEAF.fullmatch(leaf.name):
                        anomalies.append(self._layout_anomaly(leaf_path, malformed=True))
                        continue
                    object_id = f"sha256:{first.name}{second.name}{leaf.name}"
                    try:
                        objects.append(self.verify(object_id))
                    except ObjectCorrupt:
                        anomalies.append(
                            StoreAnomaly(
                                code=StoreAnomalyCode.CORRUPT_OBJECT,
                                relative_location=self._relative(leaf_path),
                                object_id=object_id,
                            )
                        )
                    except (ObjectNotFound, UnsafeStoreEntry):
                        anomalies.append(
                            StoreAnomaly(
                                code=StoreAnomalyCode.UNSAFE_ENTRY,
                                relative_location=self._relative(leaf_path),
                                object_id=object_id,
                            )
                        )
        return self._inventory_result(objects, anomalies)

    @staticmethod
    def _inventory_result(
        objects: list[StoredObject],
        anomalies: list[StoreAnomaly],
    ) -> ObjectInventory:
        return ObjectInventory(
            objects=tuple(sorted(objects, key=lambda item: item.object_id)),
            anomalies=tuple(
                sorted(
                    anomalies,
                    key=lambda item: (
                        item.relative_location,
                        item.code.value,
                        item.object_id or "",
                    ),
                )
            ),
        )

    def _inventory_directory_is_safe(
        self,
        path: Path,
        anomalies: list[StoreAnomaly],
    ) -> bool:
        try:
            self._assert_directory(path)
        except UnsafeStoreEntry:
            anomalies.append(
                StoreAnomaly(
                    code=StoreAnomalyCode.UNSAFE_ENTRY,
                    relative_location=self._relative(path),
                )
            )
            return False
        return True

    def _reuse_existing(
        self,
        temporary: Path,
        *,
        object_id: str,
        byte_length: int,
    ) -> StoredObject:
        verified = self.verify(object_id, expected_length=byte_length)
        temporary.unlink(missing_ok=True)
        return verified

    def _path_for_id(self, object_id: str) -> Path:
        match = _OBJECT_ID.fullmatch(object_id)
        if match is None:
            raise MalformedObjectIdentity("invalid SHA-256 object identity")
        digest = match.group(1)
        return self._algorithm_root / digest[:2] / digest[2:4] / digest[4:]

    def _ensure_directory(self, path: Path) -> None:
        if self._lexists(path):
            self._assert_directory(path)
            return
        parent = path.parent
        if parent != path and parent != self._root.parent:
            if not self._lexists(parent):
                self._ensure_directory(parent)
            else:
                self._assert_directory(parent)
        try:
            path.mkdir(mode=0o700)
            self._sync_directory(parent)
        except FileExistsError:
            pass
        self._assert_directory(path)

    def _assert_directory(self, path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            raise UnsafeStoreEntry("managed directory disappeared") from None
        if self._is_link_or_junction(path, metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise UnsafeStoreEntry(f"unsafe managed directory: {self._relative(path)}")

    @contextmanager
    def _open_regular(self, path: Path, *, object_id: str) -> Iterator[BinaryIO]:
        self._assert_object_ancestors(path, object_id=object_id)
        try:
            before = path.lstat()
        except FileNotFoundError:
            raise ObjectNotFound(object_id) from None
        self._assert_regular_metadata(path, before)
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            raise ObjectNotFound(object_id) from None
        except OSError:
            raise UnsafeStoreEntry(f"unsafe object entry: {object_id}") from None
        try:
            opened = os.fstat(descriptor)
            self._assert_regular_metadata(path, opened)
            if self._file_identity(before) != self._file_identity(opened):
                raise UnsafeStoreEntry(f"object entry changed while opening: {object_id}")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                yield stream
        finally:
            os.close(descriptor)

    def _assert_object_ancestors(self, path: Path, *, object_id: str) -> None:
        for directory in (self._root, self._objects, self._algorithm_root):
            self._assert_directory(directory)
        for directory in (path.parent.parent, path.parent):
            if not self._lexists(directory):
                raise ObjectNotFound(object_id)
            self._assert_directory(directory)

    def _assert_regular_metadata(self, path: Path, metadata: os.stat_result) -> None:
        if self._is_link_or_junction(path, metadata) or not stat.S_ISREG(metadata.st_mode):
            raise UnsafeStoreEntry(f"unsafe object entry: {self._relative(path)}")
        if metadata.st_nlink > 1:
            raise UnsafeStoreEntry(f"hard-linked object entry: {self._relative(path)}")

    @staticmethod
    def _file_identity(metadata: os.stat_result) -> tuple[int, int]:
        return metadata.st_dev, metadata.st_ino

    @staticmethod
    def _lexists(path: Path) -> bool:
        try:
            path.lstat()
        except FileNotFoundError:
            return False
        return True

    @staticmethod
    def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
        is_junction = getattr(os.path, "isjunction", lambda _: False)
        return stat.S_ISLNK(metadata.st_mode) or bool(is_junction(path))

    def _safe_directory_entry(self, entry: os.DirEntry[str]) -> bool:
        path = Path(entry.path)
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError:
            return False
        return not self._is_link_or_junction(path, metadata) and stat.S_ISDIR(metadata.st_mode)

    def _layout_anomaly(self, path: Path, *, malformed: bool) -> StoreAnomaly:
        return StoreAnomaly(
            code=(StoreAnomalyCode.MALFORMED_ENTRY if malformed else StoreAnomalyCode.UNSAFE_ENTRY),
            relative_location=self._relative(path),
        )

    @staticmethod
    def _sync_staged_file(descriptor: int) -> None:
        os.fsync(descriptor)

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
    def _scandir_sorted(path: Path) -> tuple[os.DirEntry[str], ...]:
        with os.scandir(path) as entries:
            return tuple(sorted(entries, key=lambda entry: entry.name))

    def _relative(self, path: Path) -> str:
        try:
            raw = path.relative_to(self._root).as_posix()
        except ValueError:
            return "outside-managed-root"
        return "".join(character if ord(character) >= 32 else "?" for character in raw)
