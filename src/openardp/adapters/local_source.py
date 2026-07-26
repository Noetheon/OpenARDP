"""Read-only stable snapshot boundary for explicit local TXT/Markdown sources."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from openardp.domain.ingestion import (
    MAX_SOURCE_BYTES,
    RichMediaType,
    SourceInspection,
    SourceMediaType,
    SourceSnapshot,
    TextMediaType,
)
from openardp.domain.storage import SourceKey
from openardp.ports.object_store import ObjectPublicationError, ObjectStore
from openardp.ports.parser import UnsupportedTextMedia

_DEFAULT_CHUNK_SIZE = 1024 * 1024
_MEDIA_BY_SUFFIX: dict[str, SourceMediaType] = {
    ".md": TextMediaType.MARKDOWN,
    ".markdown": TextMediaType.MARKDOWN,
    ".txt": TextMediaType.PLAIN,
    ".pdf": RichMediaType.PDF,
    ".docx": RichMediaType.DOCX,
    ".pptx": RichMediaType.PPTX,
}


class LocalSourceError(RuntimeError):
    """Base class for sanitized local-source failures."""


class SourceNotFound(LocalSourceError, FileNotFoundError):
    """Raised when an explicit source does not exist."""


class InvalidSourcePath(LocalSourceError, ValueError):
    """Raised for controls, links, junctions or non-regular source authority."""


class SourceTooLarge(LocalSourceError):
    """Raised before or while a source exceeds its exact byte bound."""


class SourceChangedDuringSnapshot(LocalSourceError):
    """Raised when path or descriptor evidence changes during a read."""


class LocalSource:
    """One explicit local path with no write, traversal or parser capability."""

    def __init__(
        self,
        path: Path,
        *,
        max_source_bytes: int = MAX_SOURCE_BYTES,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> None:
        """Validate scalar configuration without touching the source path."""
        raw = str(path.expanduser())
        if not raw or any(ord(character) < 32 or ord(character) == 127 for character in raw):
            raise InvalidSourcePath("invalid source path")
        if type(max_source_bytes) is not int or max_source_bytes < 0:
            raise ValueError("max_source_bytes must be a non-negative integer")
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        self._path = Path(os.path.abspath(raw))
        self._max_source_bytes = max_source_bytes
        self._chunk_size = chunk_size

    @property
    def path(self) -> Path:
        """Return the canonical absolute source locator without resolving links."""
        return self._path

    @property
    def source_key(self) -> SourceKey:
        """Return the exact provider-neutral local source identity."""
        return SourceKey(connector="local", locator=str(self._path))

    @property
    def media_type(self) -> SourceMediaType:
        """Classify a case-insensitive suffix under the reviewed local allowlist."""
        try:
            return _MEDIA_BY_SUFFIX[self._path.suffix.casefold()]
        except KeyError as error:
            raise UnsupportedTextMedia("unsupported text media") from error

    def snapshot_to(
        self,
        object_store: ObjectStore,
        *,
        observed_at: datetime,
    ) -> SourceSnapshot:
        """Stream one stable regular descriptor into CAS and return exact metadata."""
        media_type = self.media_type
        descriptor, before = self._open_regular()
        try:
            try:
                stored = object_store.put_chunks(self._iter_descriptor(descriptor))
            except ObjectPublicationError:
                self._raise_if_changed_or_oversized(descriptor, before)
                raise
            self._assert_stable(descriptor, before)
            if stored.byte_length != before.st_size:
                raise SourceChangedDuringSnapshot("source changed during snapshot")
            verified = object_store.verify(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            return SourceSnapshot(
                source_key=self.source_key,
                media_type=media_type,
                object=verified,
                modified_at=_modified_at(before),
                observed_at=observed_at,
            )
        finally:
            os.close(descriptor)

    def inspect(self, *, observed_at: datetime) -> SourceInspection:
        """Hash one stable source without publishing or invoking a parser."""
        media_type = self.media_type
        descriptor, before = self._open_regular()
        digest = hashlib.sha256()
        byte_length = 0
        try:
            for chunk in self._iter_descriptor(descriptor):
                digest.update(chunk)
                byte_length += len(chunk)
            self._assert_stable(descriptor, before)
        finally:
            os.close(descriptor)
        if byte_length != before.st_size:
            raise SourceChangedDuringSnapshot("source changed during snapshot")
        return SourceInspection(
            source_key=self.source_key,
            media_type=media_type,
            version_id="sha256:" + digest.hexdigest(),
            byte_length=byte_length,
            modified_at=_modified_at(before),
            observed_at=observed_at,
        )

    def _open_regular(self) -> tuple[int, os.stat_result]:
        self._assert_safe_components()
        try:
            before = self._path.lstat()
        except FileNotFoundError:
            raise SourceNotFound("source not found") from None
        self._assert_regular(before)
        if before.st_size > self._max_source_bytes:
            raise SourceTooLarge("source byte limit exceeded")
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        try:
            descriptor = os.open(self._path, flags)
        except FileNotFoundError:
            raise SourceNotFound("source not found") from None
        except OSError:
            raise InvalidSourcePath("invalid source path") from None
        try:
            opened = os.fstat(descriptor)
            self._assert_regular(opened)
            if _file_identity(before) != _file_identity(opened):
                raise SourceChangedDuringSnapshot("source changed during snapshot")
            return descriptor, before
        except Exception:
            os.close(descriptor)
            raise

    def _iter_descriptor(self, descriptor: int) -> Iterator[bytes]:
        byte_length = 0
        while chunk := os.read(descriptor, self._chunk_size):
            byte_length += len(chunk)
            if byte_length > self._max_source_bytes:
                raise SourceTooLarge("source byte limit exceeded")
            yield chunk

    def _assert_safe_components(self) -> None:
        current = Path(self._path.anchor)
        for part in self._path.parts[1:]:
            current /= part
            try:
                metadata = current.lstat()
            except FileNotFoundError:
                raise SourceNotFound("source not found") from None
            if _is_link_or_junction(current, metadata):
                raise InvalidSourcePath("invalid source path")
            if current != self._path and not stat.S_ISDIR(metadata.st_mode):
                raise InvalidSourcePath("invalid source path")

    def _assert_regular(self, metadata: os.stat_result) -> None:
        if _is_link_or_junction(self._path, metadata) or not stat.S_ISREG(metadata.st_mode):
            raise InvalidSourcePath("invalid source path")

    def _assert_stable(self, descriptor: int, before: os.stat_result) -> None:
        try:
            after = os.fstat(descriptor)
            current = self._path.lstat()
        except (FileNotFoundError, OSError):
            raise SourceChangedDuringSnapshot("source changed during snapshot") from None
        self._assert_regular(after)
        if _stat_fingerprint(after) != _stat_fingerprint(before):
            raise SourceChangedDuringSnapshot("source changed during snapshot")
        if _file_identity(current) != _file_identity(before):
            raise SourceChangedDuringSnapshot("source changed during snapshot")

    def _raise_if_changed_or_oversized(
        self,
        descriptor: int,
        before: os.stat_result,
    ) -> None:
        try:
            current = os.fstat(descriptor)
        except OSError:
            raise SourceChangedDuringSnapshot("source changed during snapshot") from None
        if current.st_size > self._max_source_bytes:
            raise SourceTooLarge("source byte limit exceeded")
        self._assert_stable(descriptor, before)


def _file_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _stat_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_mode,
    )


def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda _: False)
    return stat.S_ISLNK(metadata.st_mode) or bool(is_junction(path))


def _modified_at(metadata: os.stat_result) -> datetime:
    return datetime.fromtimestamp(metadata.st_mtime_ns / 1_000_000_000, tz=UTC)


__all__ = [
    "InvalidSourcePath",
    "LocalSource",
    "LocalSourceError",
    "SourceChangedDuringSnapshot",
    "SourceNotFound",
    "SourceTooLarge",
    "UnsupportedTextMedia",
]
