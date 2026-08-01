"""Bounded local evidence storage and canonical candidate source inventory."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Iterable, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, NoReturn

from pydantic import ValidationError

from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.release import (
    PlatformEvidence,
    SourceTreeEntry,
    SourceTreeInventory,
)
from openardp.ports.release import (
    ReleaseEvidenceConflict,
    ReleaseEvidenceIntegrityError,
)

_EVIDENCE_NAME = "evidence.json"
_MANIFEST_NAME = "manifest.json"
_MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
_MAX_MANIFEST_BYTES = 64 * 1024
_CHUNK_SIZE = 1024 * 1024
_IGNORED_DIRECTORY_NAMES = frozenset(
    {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "build", "dist"}
)
_IGNORED_FILE_NAMES = frozenset({".DS_Store"})
_IGNORED_FILE_SUFFIXES = (".pyc", ".pyo")


class LocalReleaseEvidenceStore:
    """Publish and verify manifest-committed immutable evidence directories."""

    def publish(self, destination: Path, evidence: PlatformEvidence) -> None:
        """Publish evidence with the manifest as the final authoritative marker."""
        evidence.verify_identity()
        target = _safe_target(destination)
        if _lexists(target):
            try:
                if self.load(target) == evidence:
                    return
            except ReleaseEvidenceIntegrityError:
                pass
            raise ReleaseEvidenceConflict("release evidence destination conflicts")
        evidence_bytes = canonical_json_bytes(evidence.model_dump(mode="json")) + b"\n"
        if len(evidence_bytes) > _MAX_EVIDENCE_BYTES:
            raise ReleaseEvidenceIntegrityError("release evidence exceeds configured limit")
        manifest = _manifest(evidence_bytes, evidence.evidence_id)
        manifest_bytes = canonical_json_bytes(manifest) + b"\n"

        staging = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.release-", dir=target.parent)
        ).resolve(strict=True)
        claimed_target = False
        try:
            _write_new_file(staging / _EVIDENCE_NAME, evidence_bytes)
            _write_new_file(staging / _MANIFEST_NAME, manifest_bytes)
            _sync_directory(staging)
            try:
                target.mkdir(mode=0o700)
                claimed_target = True
            except FileExistsError:
                try:
                    if self.load(target) == evidence:
                        return
                except ReleaseEvidenceIntegrityError:
                    pass
                raise ReleaseEvidenceConflict("release evidence destination conflicts") from None
            _copy_new_file(staging / _EVIDENCE_NAME, target / _EVIDENCE_NAME)
            _copy_new_file(staging / _MANIFEST_NAME, target / _MANIFEST_NAME)
            _sync_directory(target)
            _sync_directory(target.parent)
        except (ReleaseEvidenceConflict, ReleaseEvidenceIntegrityError):
            if claimed_target:
                with suppress(OSError):
                    shutil.rmtree(target)
            raise
        except OSError:
            if claimed_target:
                with suppress(OSError):
                    shutil.rmtree(target)
            raise ReleaseEvidenceIntegrityError("release evidence publication failed") from None
        finally:
            with suppress(OSError):
                shutil.rmtree(staging)

    def load(self, source: Path) -> PlatformEvidence:
        """Load one exact two-file bundle after complete structure and digest checks."""
        root = source.expanduser().absolute()
        try:
            metadata = root.lstat()
            if _is_link_or_junction(root, metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise ReleaseEvidenceIntegrityError("release evidence root is unsafe")
            names = tuple(sorted(item.name for item in root.iterdir()))
            if names != (_EVIDENCE_NAME, _MANIFEST_NAME):
                raise ReleaseEvidenceIntegrityError("release evidence inventory is incomplete")
            manifest_bytes = _read_safe_file(root / _MANIFEST_NAME, _MAX_MANIFEST_BYTES)
            manifest = _load_closed_json(manifest_bytes)
            evidence_bytes = _read_safe_file(root / _EVIDENCE_NAME, _MAX_EVIDENCE_BYTES)
        except ReleaseEvidenceIntegrityError:
            raise
        except OSError:
            raise ReleaseEvidenceIntegrityError("release evidence could not be read") from None
        expected = _manifest(evidence_bytes, _manifest_evidence_id(manifest))
        if manifest != expected:
            raise ReleaseEvidenceIntegrityError("release evidence manifest is invalid")
        try:
            parsed_evidence = _load_closed_json(evidence_bytes)
            evidence = PlatformEvidence.model_validate_json(canonical_json_bytes(parsed_evidence))
            evidence.verify_identity()
        except (ValidationError, ValueError):
            raise ReleaseEvidenceIntegrityError("release evidence record is invalid") from None
        if evidence.evidence_id != manifest["evidence_id"]:
            raise ReleaseEvidenceIntegrityError("release evidence identity is inconsistent")
        return evidence


def inventory_source_tree(root: Path, allowed_paths: Sequence[str]) -> SourceTreeInventory:
    """Hash one allowlisted source tree without recording its absolute location."""
    base = root.expanduser().absolute()
    try:
        metadata = base.lstat()
    except OSError:
        raise ReleaseEvidenceIntegrityError("source tree is unavailable") from None
    if _is_link_or_junction(base, metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ReleaseEvidenceIntegrityError("source tree root is unsafe")
    if not allowed_paths or len(set(allowed_paths)) != len(allowed_paths):
        raise ReleaseEvidenceIntegrityError("source tree allowlist is invalid")
    entries: dict[str, SourceTreeEntry] = {}
    for declared in sorted(allowed_paths):
        parts = _portable_parts(declared)
        candidate = base.joinpath(*parts)
        try:
            item_metadata = candidate.lstat()
        except OSError:
            raise ReleaseEvidenceIntegrityError("allowlisted source entry is unavailable") from None
        if _is_link_or_junction(candidate, item_metadata):
            raise ReleaseEvidenceIntegrityError("allowlisted source entry is unsafe")
        if stat.S_ISREG(item_metadata.st_mode):
            _add_source_entry(base, candidate, entries)
        elif stat.S_ISDIR(item_metadata.st_mode):
            for file_path in _walk_regular_files(candidate):
                _add_source_entry(base, file_path, entries)
        else:
            raise ReleaseEvidenceIntegrityError("allowlisted source entry is not regular")
    ordered = tuple(entries[path] for path in sorted(entries))
    source_tree_id = canonical_sha256([item.model_dump(mode="json") for item in ordered])
    return SourceTreeInventory(source_tree_id=source_tree_id, entries=ordered)


def _add_source_entry(base: Path, path: Path, entries: dict[str, SourceTreeEntry]) -> None:
    relative = path.relative_to(base).as_posix()
    _portable_parts(relative)
    if relative in entries:
        raise ReleaseEvidenceIntegrityError("source tree allowlist overlaps")
    digest, length = _hash_safe_file(path, _MAX_EVIDENCE_BYTES)
    entries[relative] = SourceTreeEntry(
        path=relative,
        byte_length=length,
        sha256="sha256:" + digest,
    )


def _walk_regular_files(root: Path) -> Iterable[Path]:
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories if name not in _IGNORED_DIRECTORY_NAMES
        )
        files.sort()
        for name in tuple(directories):
            child = current_path / name
            metadata = child.lstat()
            if _is_link_or_junction(child, metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise ReleaseEvidenceIntegrityError("source tree contains an unsafe directory")
        for name in files:
            if name in _IGNORED_FILE_NAMES or name.endswith(_IGNORED_FILE_SUFFIXES):
                continue
            child = current_path / name
            metadata = child.lstat()
            if _is_link_or_junction(child, metadata) or not stat.S_ISREG(metadata.st_mode):
                raise ReleaseEvidenceIntegrityError("source tree contains an unsafe file")
            yield child


def _portable_parts(value: str) -> tuple[str, ...]:
    if not value or "\\" in value or value.startswith("/") or "\x00" in value:
        raise ReleaseEvidenceIntegrityError("source tree path is not portable")
    parts = tuple(value.split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        raise ReleaseEvidenceIntegrityError("source tree path is not portable")
    return parts


def _manifest(data: bytes, evidence_id: str) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "evidence_id": evidence_id,
        "files": [
            {
                "path": _EVIDENCE_NAME,
                "byte_length": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        ],
    }


def _manifest_evidence_id(manifest: dict[str, Any]) -> str:
    value = manifest.get("evidence_id")
    if not isinstance(value, str):
        raise ReleaseEvidenceIntegrityError("release evidence manifest is invalid")
    return value


def _load_closed_json(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            data,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError):
        raise ReleaseEvidenceIntegrityError("release evidence JSON is invalid") from None
    if not isinstance(value, dict):
        raise ReleaseEvidenceIntegrityError("release evidence JSON root must be an object")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> NoReturn:
    raise ValueError("non-finite JSON number")


def _write_new_file(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _copy_new_file(source: Path, destination: Path) -> None:
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        while chunk := incoming.read(_CHUNK_SIZE):
            outgoing.write(chunk)
        outgoing.flush()
        os.fsync(outgoing.fileno())


def _read_safe_file(path: Path, limit: int) -> bytes:
    try:
        metadata = path.lstat()
        if _is_link_or_junction(path, metadata) or not stat.S_ISREG(metadata.st_mode):
            raise ReleaseEvidenceIntegrityError("release evidence entry is unsafe")
        if metadata.st_size > limit:
            raise ReleaseEvidenceIntegrityError("release evidence entry exceeds limit")
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            data = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
    except ReleaseEvidenceIntegrityError:
        raise
    except OSError:
        raise ReleaseEvidenceIntegrityError("release evidence entry could not be read") from None
    if len(data) > limit or _file_identity(before) != _file_identity(after):
        raise ReleaseEvidenceIntegrityError("release evidence entry changed during read")
    return data


def _hash_safe_file(path: Path, limit: int) -> tuple[str, int]:
    try:
        metadata = path.lstat()
        if _is_link_or_junction(path, metadata) or not stat.S_ISREG(metadata.st_mode):
            raise ReleaseEvidenceIntegrityError("source tree file is unsafe")
        if metadata.st_size > limit:
            raise ReleaseEvidenceIntegrityError("source tree file exceeds limit")
        digest = hashlib.sha256()
        length = 0
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            while chunk := handle.read(_CHUNK_SIZE):
                length += len(chunk)
                if length > limit:
                    raise ReleaseEvidenceIntegrityError("source tree file exceeds limit")
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except ReleaseEvidenceIntegrityError:
        raise
    except OSError:
        raise ReleaseEvidenceIntegrityError("source tree file could not be read") from None
    if _file_identity(before) != _file_identity(after):
        raise ReleaseEvidenceIntegrityError("source tree file changed during read")
    return digest.hexdigest(), length


def _safe_target(path: Path) -> Path:
    target = path.expanduser().absolute()
    try:
        metadata = target.parent.lstat()
    except OSError:
        raise ReleaseEvidenceConflict("release evidence parent is unavailable") from None
    if _is_link_or_junction(target.parent, metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ReleaseEvidenceConflict("release evidence parent is unsafe")
    return target


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_size


def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    if os.name != "nt":
        return False
    return bool(getattr(metadata, "st_reparse_tag", 0)) or path.is_symlink()


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = ["LocalReleaseEvidenceStore", "inventory_source_tree"]
