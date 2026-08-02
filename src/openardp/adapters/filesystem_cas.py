"""Safe local SHA-256 filesystem content-addressed object store."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import BinaryIO

from openardp.adapters.compact_objects import (
    MAX_LOGICAL_BYTES,
    PROFILE,
    CompactObjectError,
    decode_compact,
    encode_compact,
)
from openardp.domain.maintenance import (
    StorageOptimizationItem,
    StorageOptimizationOutcome,
)
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

    def __init__(self, root: Path, *, create: bool = True) -> None:
        """Create or validate managed directories without hidden open-time repair."""
        configured = root.expanduser()
        if create:
            configured.mkdir(parents=True, exist_ok=True, mode=0o700)
        elif not self._lexists(configured):
            raise UnsafeStoreEntry("managed storage root is missing")
        self._root = configured.resolve(strict=True)
        self._objects = self._root / "objects"
        self._algorithm_root = self._objects / "sha256"
        self._compact_profile_root = self._objects / PROFILE
        self._compact_algorithm_root = self._compact_profile_root / "sha256"
        self._staging = self._root / "staging"
        directories = [self._objects, self._algorithm_root, self._staging]
        if create:
            directories.extend((self._compact_profile_root, self._compact_algorithm_root))
        for directory in directories:
            if create:
                self._ensure_directory(directory)
            else:
                self._assert_directory(directory)

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
                if os.name == "nt":
                    os.rename(temporary, destination)
                else:
                    os.link(temporary, destination, follow_symlinks=False)
                    try:
                        temporary.unlink()
                    except OSError:
                        with suppress(OSError):
                            destination.unlink()
                        raise ObjectPublicationError(
                            f"object publication failed for {object_id}"
                        ) from None
                published = True
            except FileExistsError:
                return self._reuse_existing(
                    temporary,
                    object_id=object_id,
                    byte_length=byte_length,
                )
            except ObjectStoreError:
                raise
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

    def put_canonical_block(self, payload: bytes) -> StoredObject:
        """Publish one canonical derived block using the compact v1 form if smaller."""
        if not isinstance(payload, bytes):
            raise TypeError("canonical block payload must be bytes")
        object_id = "sha256:" + hashlib.sha256(payload).hexdigest()
        ordinary = self._path_for_id(object_id)
        if self._lexists(ordinary):
            return self.verify(object_id, expected_length=len(payload))
        envelope = encode_compact(payload)
        if envelope is None:
            return self.put_chunks((payload,))
        destination = self._compact_path_for_id(object_id)
        self._publish_physical_bytes(destination, envelope, object_id=object_id)
        return self.verify(object_id, expected_length=len(payload))

    def retain_ordinary_authority(
        self,
        object_id: str,
        *,
        expected_length: int,
    ) -> StoredObject:
        """Converge a committed source/native collision to its ordinary authority."""
        if type(expected_length) is not int or expected_length < 0:
            raise ValueError("expected_length must be a non-negative integer")
        ordinary = self._path_for_id(object_id)
        compact = self._compact_path_for_id(object_id)
        verified = self._verify_ordinary(ordinary, object_id=object_id)
        if verified.byte_length != expected_length:
            raise ObjectCorrupt(f"object length mismatch: {object_id}")
        if not self._lexists(compact):
            return verified
        compact_payload = self._read_verified_compact(compact, object_id=object_id)
        if len(compact_payload) != expected_length:
            raise ObjectCorrupt(f"physical object forms disagree: {object_id}")
        try:
            compact.unlink()
            self._sync_directory(compact.parent)
        except OSError:
            raise ObjectDurabilityError(
                f"ordinary authority convergence is uncertain for {object_id}"
            ) from None
        return self._verify_ordinary(ordinary, object_id=object_id)

    def optimize_derived_block(
        self,
        object_id: str,
        *,
        expected_length: int,
    ) -> StorageOptimizationItem:
        """Explicitly converge one catalog-approved block to its smaller physical form."""
        if type(expected_length) is not int or expected_length < 0:
            raise ValueError("expected_length must be a non-negative integer")
        ordinary = self._path_for_id(object_id)
        compact = self._compact_path_for_id(object_id)
        ordinary_present = self._lexists(ordinary)
        compact_present = self._lexists(compact)
        if not ordinary_present and not compact_present:
            raise ObjectNotFound(object_id)
        before = 0
        if ordinary_present:
            ordinary_verified = self._verify_ordinary(ordinary, object_id=object_id)
            if ordinary_verified.byte_length != expected_length:
                raise ObjectCorrupt(f"object length mismatch: {object_id}")
            before += ordinary.lstat().st_size
        if compact_present:
            compact_payload = self._read_verified_compact(compact, object_id=object_id)
            if len(compact_payload) != expected_length:
                raise ObjectCorrupt(f"object length mismatch: {object_id}")
            before += compact.lstat().st_size
        if compact_present and not ordinary_present:
            return StorageOptimizationItem(
                object_id=object_id,
                outcome=StorageOptimizationOutcome.ALREADY_COMPACT,
                logical_bytes=expected_length,
                stored_bytes_before=before,
                stored_bytes_after=before,
            )
        if compact_present:
            ordinary.unlink()
            self._sync_directory(ordinary.parent)
            self._fault_point("after_ordinary_removal")
            return StorageOptimizationItem(
                object_id=object_id,
                outcome=StorageOptimizationOutcome.DUPLICATE_CONVERGED,
                logical_bytes=expected_length,
                stored_bytes_before=before,
                stored_bytes_after=compact.lstat().st_size,
            )
        with self._open_regular(ordinary, object_id=object_id) as stream:
            payload = stream.read(MAX_LOGICAL_BYTES + 1)
        envelope = encode_compact(payload) if len(payload) == expected_length else None
        if envelope is None:
            return StorageOptimizationItem(
                object_id=object_id,
                outcome=StorageOptimizationOutcome.ORDINARY_SMALLER,
                logical_bytes=expected_length,
                stored_bytes_before=before,
                stored_bytes_after=before,
            )
        self._publish_physical_bytes(compact, envelope, object_id=object_id)
        self._fault_point("after_compact_publication")
        self.verify(object_id, expected_length=expected_length)
        ordinary.unlink()
        self._sync_directory(ordinary.parent)
        self._fault_point("after_ordinary_removal")
        return StorageOptimizationItem(
            object_id=object_id,
            outcome=StorageOptimizationOutcome.COMPACTED,
            logical_bytes=expected_length,
            stored_bytes_before=before,
            stored_bytes_after=compact.lstat().st_size,
        )

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> Iterator[bytes]:
        """Yield bounded exact object chunks from a safe regular-file handle."""
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        ordinary = self._path_for_id(object_id)
        compact = self._compact_path_for_id(object_id)
        ordinary_present = self._lexists(ordinary)
        compact_present = self._lexists(compact)
        if not ordinary_present and not compact_present:
            raise ObjectNotFound(object_id)
        if compact_present:
            compact_payload = self._read_verified_compact(compact, object_id=object_id)
            if ordinary_present:
                ordinary_object = self._verify_ordinary(ordinary, object_id=object_id)
                if ordinary_object.byte_length != len(compact_payload):
                    raise ObjectCorrupt(f"physical object forms disagree: {object_id}")
            for offset in range(0, len(compact_payload), chunk_size):
                yield compact_payload[offset : offset + chunk_size]
            return
        with self._open_regular(ordinary, object_id=object_id) as stream:
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
        ordinary = self._path_for_id(object_id)
        compact = self._compact_path_for_id(object_id)
        ordinary_present = self._lexists(ordinary)
        compact_present = self._lexists(compact)
        if not ordinary_present and not compact_present:
            raise ObjectNotFound(object_id)
        verified: StoredObject | None = None
        if ordinary_present:
            verified = self._verify_ordinary(ordinary, object_id=object_id)
        if compact_present:
            compact_payload = self._read_verified_compact(compact, object_id=object_id)
            compact_verified = StoredObject(object_id=object_id, byte_length=len(compact_payload))
            if verified is not None and verified != compact_verified:
                raise ObjectCorrupt(f"physical object forms disagree: {object_id}")
            verified = compact_verified
        assert verified is not None
        if expected_length is not None and verified.byte_length != expected_length:
            raise ObjectCorrupt(f"object length mismatch: {object_id}")
        return verified

    def _verify_ordinary(self, path: Path, *, object_id: str) -> StoredObject:
        """Verify one present ordinary physical form without consulting peers."""
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
        return StoredObject(object_id=object_id, byte_length=byte_length)

    def _read_verified_compact(self, path: Path, *, object_id: str) -> bytes:
        """Read, bound, decode and verify one present compact physical form."""
        with self._open_compact_regular(path, object_id=object_id) as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_LOGICAL_BYTES:
                raise ObjectCorrupt(f"compact object is oversized: {object_id}")
            envelope = stream.read(MAX_LOGICAL_BYTES + 1)
            after = os.fstat(stream.fileno())
        if (
            self._file_identity(before) != self._file_identity(after)
            or before.st_size != after.st_size
            or len(envelope) != before.st_size
        ):
            raise ObjectCorrupt(f"object changed during verification: {object_id}")
        try:
            payload = decode_compact(envelope)
        except CompactObjectError:
            raise ObjectCorrupt(f"compact object is malformed: {object_id}") from None
        actual_id = "sha256:" + hashlib.sha256(payload).hexdigest()
        if actual_id != object_id:
            raise ObjectCorrupt(f"object digest or length mismatch: {object_id}")
        return payload

    def inventory(self) -> ObjectInventory:
        """Scan the exact fan-out tree without following or deleting entries."""
        objects_by_id: dict[str, StoredObject] = {}
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
            return self._inventory_result(list(objects_by_id.values()), anomalies)
        if not self._inventory_directory_is_safe(self._algorithm_root, anomalies):
            return self._inventory_result(list(objects_by_id.values()), anomalies)
        self._scan_algorithm_tree(
            self._algorithm_root,
            objects_by_id=objects_by_id,
            anomalies=anomalies,
            compact=False,
        )
        if self._lexists(self._compact_profile_root):
            if not self._inventory_directory_is_safe(self._compact_profile_root, anomalies):
                return self._inventory_result(list(objects_by_id.values()), anomalies)
            if not self._inventory_directory_is_safe(self._compact_algorithm_root, anomalies):
                return self._inventory_result(list(objects_by_id.values()), anomalies)
            self._scan_algorithm_tree(
                self._compact_algorithm_root,
                objects_by_id=objects_by_id,
                anomalies=anomalies,
                compact=True,
            )
        return self._inventory_result(list(objects_by_id.values()), anomalies)

    def _scan_algorithm_tree(
        self,
        algorithm_root: Path,
        *,
        objects_by_id: dict[str, StoredObject],
        anomalies: list[StoreAnomaly],
        compact: bool,
    ) -> None:
        """Scan one closed physical namespace into a deduplicated logical inventory."""
        for first in self._scandir_sorted(algorithm_root):
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
                        if compact:
                            payload = self._read_verified_compact(leaf_path, object_id=object_id)
                            stored = StoredObject(object_id=object_id, byte_length=len(payload))
                        else:
                            stored = self._verify_ordinary(leaf_path, object_id=object_id)
                        peer = objects_by_id.get(object_id)
                        if peer is not None and peer != stored:
                            raise ObjectCorrupt(f"physical object forms disagree: {object_id}")
                        objects_by_id[object_id] = stored
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

    def _publish_physical_bytes(
        self,
        destination: Path,
        payload: bytes,
        *,
        object_id: str,
    ) -> None:
        """Atomically publish one already-encoded physical form without replacement."""
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="compact-",
            suffix=".part",
            dir=self._staging,
        )
        temporary = Path(temporary_name)
        published = False
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                self._sync_staged_file(stream.fileno())
            self._ensure_directory(destination.parent.parent.parent)
            self._ensure_directory(destination.parent.parent)
            self._ensure_directory(destination.parent)
            if self._lexists(destination):
                self._read_verified_compact(destination, object_id=object_id)
                return
            try:
                if os.name == "nt":
                    os.rename(temporary, destination)
                else:
                    os.link(temporary, destination, follow_symlinks=False)
                    temporary.unlink()
                published = True
            except FileExistsError:
                self._read_verified_compact(destination, object_id=object_id)
                return
            except OSError:
                raise ObjectPublicationError(
                    f"compact object publication failed for {object_id}"
                ) from None
            self._read_verified_compact(destination, object_id=object_id)
            self._sync_directory(destination.parent)
        except ObjectStoreError:
            raise
        except Exception:
            raise ObjectPublicationError("compact object publication failed") from None
        finally:
            if not published:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)

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
        deadline = time.monotonic() + 1.0
        while True:
            try:
                verified = self.verify(object_id, expected_length=byte_length)
                break
            except UnsafeStoreEntry:
                destination = self._path_for_id(object_id)
                if not self._publication_link_is_settling(destination):
                    raise
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.001)
        temporary.unlink(missing_ok=True)
        return verified

    def _publication_link_is_settling(self, destination: Path) -> bool:
        """Recognize only the transient internal hard link used for POSIX publication."""
        try:
            for directory in (
                self._root,
                self._objects,
                self._algorithm_root,
                destination.parent.parent,
                destination.parent,
            ):
                self._assert_directory(directory)
            metadata = destination.lstat()
        except (FileNotFoundError, UnsafeStoreEntry):
            return False
        for _ in range(3):
            if not self._safe_regular_metadata(destination, metadata):
                return False
            if metadata.st_nlink <= 1:
                return True
            if self._staging_twin_exists(metadata):
                return True
            # The twin may vanish between the metadata read and the staging scan;
            # re-read the destination before judging the link count unsafe.
            time.sleep(0.001)
            try:
                metadata = destination.lstat()
            except FileNotFoundError:
                return False
        return False

    def _safe_regular_metadata(self, path: Path, metadata: os.stat_result) -> bool:
        """Check the non-link regular-file invariant without the link-count rule."""
        return not self._is_link_or_junction(path, metadata) and stat.S_ISREG(metadata.st_mode)

    def _staging_twin_exists(self, metadata: os.stat_result) -> bool:
        """Find a staged temporary file holding the same inode as the destination."""
        try:
            with os.scandir(self._staging) as entries:
                for entry in entries:
                    try:
                        # DirEntry.stat caches Windows directory data without a file
                        # index, so request the complete identity from the OS.
                        entry_metadata = os.stat(entry.path, follow_symlinks=False)
                    except OSError:
                        continue
                    if stat.S_ISREG(entry_metadata.st_mode) and self._file_identity(
                        entry_metadata
                    ) == self._file_identity(metadata):
                        return True
        except OSError:
            return False
        return False

    def _path_for_id(self, object_id: str) -> Path:
        digest = self._digest_for_id(object_id)
        return self._algorithm_root / digest[:2] / digest[2:4] / digest[4:]

    def _compact_path_for_id(self, object_id: str) -> Path:
        digest = self._digest_for_id(object_id)
        return self._compact_algorithm_root / digest[:2] / digest[2:4] / digest[4:]

    @staticmethod
    def _digest_for_id(object_id: str) -> str:
        match = _OBJECT_ID.fullmatch(object_id)
        if match is None:
            raise MalformedObjectIdentity("invalid SHA-256 object identity")
        return match.group(1)

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

    @contextmanager
    def _open_compact_regular(self, path: Path, *, object_id: str) -> Iterator[BinaryIO]:
        """Open a compact leaf while validating its distinct managed ancestors."""
        for directory in (
            self._root,
            self._objects,
            self._compact_profile_root,
            self._compact_algorithm_root,
        ):
            self._assert_directory(directory)
        for directory in (path.parent.parent, path.parent):
            if not self._lexists(directory):
                raise ObjectNotFound(object_id)
            self._assert_directory(directory)
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

    @staticmethod
    def _fault_point(_point: str) -> None:
        """Provide deterministic interruption boundaries for recovery tests."""
