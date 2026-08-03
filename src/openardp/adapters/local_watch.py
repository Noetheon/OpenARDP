"""Safe deterministic polling scanner for one explicit local root."""

from __future__ import annotations

import os
import stat
from datetime import datetime
from pathlib import Path

from openardp.domain.watcher import (
    AdmittedWatchRoot,
    WatchConfig,
    WatchFileFingerprint,
    WatchJobTarget,
    WatchScan,
    WatchScanEntry,
    WatchScanReason,
    watch_locator_digest,
    watch_root_id,
)
from openardp.ports.watcher import (
    WatchRootInvalid,
    WatchRootOverlap,
    WatchRootUnsupported,
    WatchTargetChanged,
)

_MEDIA_BY_SUFFIX = {
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".markdown": "text/markdown",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
}


class LocalWatchScanner:
    """Use bounded stdlib metadata scans without following filesystem links."""

    def admit(
        self,
        root: Path,
        *,
        workspace: Path,
        config: WatchConfig,
    ) -> AdmittedWatchRoot:
        """Validate exact disjoint root authority and capture directory identity."""
        raw = str(root)
        if _invalid_raw_path(raw):
            raise WatchRootInvalid("watch root is invalid")
        if _recognizable_network_or_device_path(raw):
            raise WatchRootUnsupported("watch root is unsupported")
        if not root.is_absolute() or os.path.normpath(raw) != raw:
            raise WatchRootInvalid("watch root is invalid")
        canonical = Path(raw)
        workspace_path = Path(os.path.abspath(str(workspace.expanduser())))
        self._assert_safe_directory(canonical)
        self._assert_safe_directory(workspace_path)
        if _overlaps(canonical, workspace_path):
            raise WatchRootOverlap("watch root overlaps workspace")
        metadata = _fresh_stat(canonical)
        device_id = str(metadata.st_dev)
        file_id = str(metadata.st_ino)
        path_digest = watch_locator_digest(str(canonical))
        return AdmittedWatchRoot(
            root_id=watch_root_id(
                root_path_digest=path_digest,
                device_id=device_id,
                file_id=file_id,
                config_hash=config.config_hash,
            ),
            root_path=str(canonical),
            root_path_digest=path_digest,
            device_id=device_id,
            file_id=file_id,
            config=config,
        )

    def scan(
        self,
        root: AdmittedWatchRoot,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> WatchScan:
        """Return all supported regular entries or no authoritative partial entries."""
        base = Path(root.root_path)
        try:
            before = _fresh_stat(base)
            if _is_link_or_junction(base, before) or not stat.S_ISDIR(before.st_mode):
                return _incomplete(root, started_at, completed_at, WatchScanReason.ROOT_CHANGED)
            if (str(before.st_dev), str(before.st_ino)) != (root.device_id, root.file_id):
                return _incomplete(root, started_at, completed_at, WatchScanReason.ROOT_CHANGED)
            entries: list[WatchScanEntry] = []
            enumerated_count = 0
            stack: list[tuple[Path, int]] = [(base, 0)]
            while stack:
                directory, depth = stack.pop()
                directory_before = _fresh_stat(directory)
                if (
                    _is_link_or_junction(directory, directory_before)
                    or not stat.S_ISDIR(directory_before.st_mode)
                    or str(directory_before.st_dev) != root.device_id
                ):
                    return _incomplete(
                        root,
                        started_at,
                        completed_at,
                        WatchScanReason.INCOMPLETE,
                    )
                iterator = os.scandir(directory)
                children: list[os.DirEntry[str]] = []
                try:
                    for child in iterator:
                        enumerated_count += 1
                        if enumerated_count > root.config.max_entries:
                            return _incomplete(
                                root,
                                started_at,
                                completed_at,
                                WatchScanReason.OVERFLOW,
                            )
                        children.append(child)
                finally:
                    close = getattr(iterator, "close", None)
                    if close is not None:
                        close()
                children.sort(key=lambda entry: entry.name)
                directories: list[Path] = []
                for child in children:
                    child_path = Path(child.path)
                    metadata = _fresh_stat(child_path)
                    if _is_link_or_junction(child_path, metadata):
                        continue
                    if stat.S_ISDIR(metadata.st_mode):
                        if (
                            root.config.recursive
                            and depth < root.config.max_depth
                            and str(metadata.st_dev) == root.device_id
                        ):
                            directories.append(child_path)
                        continue
                    if not stat.S_ISREG(metadata.st_mode):
                        continue
                    if str(metadata.st_dev) != root.device_id:
                        continue
                    media_type = _MEDIA_BY_SUFFIX.get(child_path.suffix.casefold())
                    if media_type is None:
                        continue
                    relative = child_path.relative_to(base).as_posix()
                    if _invalid_relative_path(relative):
                        continue
                    entries.append(
                        WatchScanEntry(
                            relative_locator=relative,
                            locator_digest=watch_locator_digest(relative),
                            fingerprint=WatchFileFingerprint(
                                device_id=str(metadata.st_dev),
                                file_id=str(metadata.st_ino),
                                byte_length=metadata.st_size,
                                modified_ns=str(metadata.st_mtime_ns),
                                mode=metadata.st_mode,
                            ),
                            media_type=media_type,
                        )
                    )
                for child_directory in reversed(directories):
                    stack.append((child_directory, depth + 1))
                directory_after = _fresh_stat(directory)
                if (
                    directory_before.st_dev,
                    directory_before.st_ino,
                    directory_before.st_mtime_ns,
                ) != (
                    directory_after.st_dev,
                    directory_after.st_ino,
                    directory_after.st_mtime_ns,
                ):
                    return _incomplete(
                        root,
                        started_at,
                        completed_at,
                        WatchScanReason.INCOMPLETE,
                    )
            after = _fresh_stat(base)
            if (str(after.st_dev), str(after.st_ino)) != (root.device_id, root.file_id):
                return _incomplete(root, started_at, completed_at, WatchScanReason.ROOT_CHANGED)
        except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
            return _incomplete(root, started_at, completed_at, WatchScanReason.INCOMPLETE)
        return WatchScan(
            root_id=root.root_id,
            started_at=started_at,
            completed_at=completed_at,
            complete=True,
            entries=tuple(sorted(entries, key=lambda entry: entry.relative_locator)),
        )

    def revalidate_target(
        self,
        root: AdmittedWatchRoot,
        target: WatchJobTarget,
    ) -> Path:
        """Reconstruct one path without links and require its scheduled metadata."""
        if target.root_id != root.root_id:
            raise WatchTargetChanged("watch target is no longer current")
        base = Path(root.root_path)
        selected = base.joinpath(*target.relative_locator.split("/"))
        try:
            selected.relative_to(base)
            root_metadata = _fresh_stat(base)
            if (
                _is_link_or_junction(base, root_metadata)
                or not stat.S_ISDIR(root_metadata.st_mode)
                or (str(root_metadata.st_dev), str(root_metadata.st_ino))
                != (root.device_id, root.file_id)
            ):
                raise WatchTargetChanged("watch target is no longer current")
            current = base
            for part in target.relative_locator.split("/"):
                current /= part
                metadata = _fresh_stat(current)
                if (
                    _is_link_or_junction(current, metadata)
                    or str(metadata.st_dev) != root.device_id
                ):
                    raise WatchTargetChanged("watch target is no longer current")
            if not stat.S_ISREG(metadata.st_mode):
                raise WatchTargetChanged("watch target is no longer current")
            observed = WatchFileFingerprint(
                device_id=str(metadata.st_dev),
                file_id=str(metadata.st_ino),
                byte_length=metadata.st_size,
                modified_ns=str(metadata.st_mtime_ns),
                mode=metadata.st_mode,
            )
        except (FileNotFoundError, NotADirectoryError, OSError, ValueError):
            raise WatchTargetChanged("watch target is no longer current") from None
        if observed != target.fingerprint:
            raise WatchTargetChanged("watch target is no longer current")
        return selected

    @staticmethod
    def _assert_safe_directory(path: Path) -> None:
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current /= part
            try:
                metadata = _fresh_stat(current)
            except (FileNotFoundError, OSError):
                raise WatchRootInvalid("watch directory is invalid") from None
            if _is_link_or_junction(current, metadata):
                raise WatchRootInvalid("watch directory is invalid")
            if current != path and not stat.S_ISDIR(metadata.st_mode):
                raise WatchRootInvalid("watch directory is invalid")
        try:
            metadata = _fresh_stat(path)
        except (FileNotFoundError, OSError):
            raise WatchRootInvalid("watch directory is invalid") from None
        if not stat.S_ISDIR(metadata.st_mode):
            raise WatchRootInvalid("watch directory is invalid")


def _incomplete(
    root: AdmittedWatchRoot,
    started_at: datetime,
    completed_at: datetime,
    reason: WatchScanReason,
) -> WatchScan:
    return WatchScan(
        root_id=root.root_id,
        started_at=started_at,
        completed_at=completed_at,
        complete=False,
        reason=reason,
    )


def _invalid_raw_path(value: str) -> bool:
    return not value or any(ord(character) < 32 or ord(character) == 127 for character in value)


def _recognizable_network_or_device_path(value: str) -> bool:
    normalized = value.replace("/", "\\")
    return normalized.startswith(("\\\\", "\\?\\", "\\.\\"))


def _invalid_relative_path(value: str) -> bool:
    return (
        value.startswith(("/", "\\"))
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or any(segment in {"", ".", ".."} for segment in value.split("/"))
    )


def _overlaps(first: Path, second: Path) -> bool:
    try:
        common = Path(os.path.commonpath((first, second)))
    except ValueError:
        return False
    return common in (first, second)


def _is_link_or_junction(path: Path, metadata: os.stat_result) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda _: False)
    return stat.S_ISLNK(metadata.st_mode) or bool(is_junction(path))


def _fresh_stat(path: Path) -> os.stat_result:
    """Return uncached no-follow metadata with usable Windows file identities."""
    return os.stat(path, follow_symlinks=False)


__all__ = ["LocalWatchScanner"]
