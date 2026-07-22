"""Explicit versioned composition root for one local OpenARDP workspace."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from pydantic import JsonValue

from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import CURRENT_SCHEMA_VERSION
from openardp.domain.identity import canonical_json_bytes
from openardp.ports.catalog import CatalogIncompatible, CatalogTooNew, MigrationFailed

_MARKER_NAME = ".openardp-workspace.json"
_CATALOG_NAME = "catalog.sqlite3"
_MARKER: dict[str, JsonValue] = {
    "catalog": _CATALOG_NAME,
    "format": "openardp-local-workspace",
    "objects": "objects",
    "staging": "staging",
    "version": 1,
}
_BOOTSTRAP_ENTRIES = {
    _CATALOG_NAME,
    f"{_CATALOG_NAME}-journal",
    f"{_CATALOG_NAME}-shm",
    f"{_CATALOG_NAME}-wal",
    "objects",
    "staging",
}


class WorkspaceError(RuntimeError):
    """Base class for sanitized local-workspace failures."""


class WorkspaceMissing(WorkspaceError, FileNotFoundError):
    """Raised when a non-init operation targets an unmarked workspace."""


class WorkspaceIncompatible(WorkspaceError):
    """Raised for unsafe, malformed, foreign or unsupported workspace state."""


class LocalWorkspace:
    """Validated local composition of immutable CAS and SQLite catalog."""

    def __init__(
        self,
        root: Path,
        object_store: FilesystemObjectStore,
        catalog: SQLiteCatalog,
    ) -> None:
        """Construct only from the validated class factories."""
        self._root = root
        self._object_store = object_store
        self._catalog = catalog

    @property
    def root(self) -> Path:
        """Return the canonical operator-selected workspace root."""
        return self._root

    @property
    def object_store(self) -> FilesystemObjectStore:
        """Return the validated local immutable object store."""
        return self._object_store

    @property
    def catalog(self) -> SQLiteCatalog:
        """Return the validated local catalog."""
        return self._catalog

    @classmethod
    def initialize(cls, root: Path, *, now: datetime) -> LocalWorkspace:
        """Create or explicitly upgrade one compatible workspace idempotently."""
        canonical = _prepare_root(root)
        marker = canonical / _MARKER_NAME
        if _lexists(marker):
            _validate_marker(marker)
        else:
            foreign = {entry.name for entry in canonical.iterdir()} - _BOOTSTRAP_ENTRIES
            if foreign:
                raise WorkspaceIncompatible("workspace is incompatible")

        try:
            object_store = FilesystemObjectStore(canonical)
            catalog = SQLiteCatalog(canonical / _CATALOG_NAME)
            revision = catalog.initialize(now=now)
        except (CatalogIncompatible, CatalogTooNew, MigrationFailed) as error:
            raise WorkspaceIncompatible("workspace is incompatible") from error
        if revision != CURRENT_SCHEMA_VERSION:
            raise WorkspaceIncompatible("workspace is incompatible")
        if not _lexists(marker):
            _publish_marker(marker)
        _validate_marker(marker)
        return cls(canonical, object_store, catalog)

    @classmethod
    def open(cls, root: Path) -> LocalWorkspace:
        """Open an existing current workspace without initialization or repair."""
        raw = root.expanduser().absolute()
        if not _lexists(raw):
            raise WorkspaceMissing("workspace is not initialized")
        canonical = _validate_root(raw)
        marker = canonical / _MARKER_NAME
        if not _lexists(marker):
            raise WorkspaceMissing("workspace is not initialized")
        _validate_marker(marker)
        _validate_existing_layout(canonical)
        object_store = FilesystemObjectStore(canonical)
        catalog = SQLiteCatalog(canonical / _CATALOG_NAME)
        try:
            if catalog.schema_version() != CURRENT_SCHEMA_VERSION:
                raise WorkspaceIncompatible("workspace is incompatible")
        except (CatalogIncompatible, CatalogTooNew, MigrationFailed) as error:
            raise WorkspaceIncompatible("workspace is incompatible") from error
        return cls(canonical, object_store, catalog)


def _prepare_root(root: Path) -> Path:
    raw = root.expanduser().absolute()
    if _lexists(raw):
        return _validate_root(raw)
    try:
        raw.mkdir(parents=True, mode=0o700)
    except OSError:
        raise WorkspaceIncompatible("workspace is incompatible") from None
    return _validate_root(raw)


def _validate_root(root: Path) -> Path:
    try:
        metadata = root.lstat()
    except FileNotFoundError:
        raise WorkspaceMissing("workspace is not initialized") from None
    if _is_link_or_junction(root, metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise WorkspaceIncompatible("workspace is incompatible")
    return root.resolve(strict=True)


def _validate_marker(marker: Path) -> None:
    try:
        metadata = marker.lstat()
        if _is_link_or_junction(marker, metadata) or not stat.S_ISREG(metadata.st_mode):
            raise WorkspaceIncompatible("workspace is incompatible")
        payload = marker.read_bytes()
    except (FileNotFoundError, OSError):
        raise WorkspaceIncompatible("workspace is incompatible") from None
    expected = canonical_json_bytes(_MARKER)
    if payload != expected:
        try:
            parsed = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        if parsed != _MARKER:
            raise WorkspaceIncompatible("workspace is incompatible")
        raise WorkspaceIncompatible("workspace is incompatible")


def _validate_existing_layout(root: Path) -> None:
    for name, expected_directory in (
        (_CATALOG_NAME, False),
        ("objects", True),
        ("staging", True),
    ):
        path = root / name
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            raise WorkspaceIncompatible("workspace is incompatible") from None
        if _is_link_or_junction(path, metadata):
            raise WorkspaceIncompatible("workspace is incompatible")
        type_matches = (
            stat.S_ISDIR(metadata.st_mode) if expected_directory else stat.S_ISREG(metadata.st_mode)
        )
        if not type_matches:
            raise WorkspaceIncompatible("workspace is incompatible")


def _publish_marker(marker: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".openardp-workspace-",
        suffix=".part",
        dir=marker.parent,
    )
    temporary = Path(temporary_name)
    published = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json_bytes(_MARKER))
            stream.flush()
            os.fsync(stream.fileno())
        with suppress(OSError):
            temporary.chmod(0o600)
        os.replace(temporary, marker)
        published = True
        _sync_directory(marker.parent)
    except OSError:
        raise WorkspaceIncompatible("workspace marker publication failed") from None
    finally:
        if not published:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


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
    "LocalWorkspace",
    "WorkspaceError",
    "WorkspaceIncompatible",
    "WorkspaceMissing",
]
