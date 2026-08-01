"""Closed security-control evidence and digest-only privacy canary scanning."""

from __future__ import annotations

import hashlib
import json
import tarfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar

from openardp.domain.identity import canonical_sha256
from openardp.domain.release import EvidenceCheck, EvidenceStatus

_MAX_MANIFEST_BYTES = 1024 * 1024
_MAX_SCAN_BYTES = 64 * 1024 * 1024
_MAX_ARCHIVE_MEMBERS = 5_000


class SecurityEvidenceMalformed(ValueError):
    """Raised when control or privacy evidence is incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class SecurityControl:
    """One stable threat-to-test mapping."""

    control_id: str
    threat: str
    invariant: str
    test_nodes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TestNodeResult:
    """Sanitized result for one exact pytest node identity."""

    __test__: ClassVar[bool] = False

    node_id: str
    status: str
    duration_ms: int


@dataclass(frozen=True, slots=True)
class PrivacyScanResult:
    """Digest-only canary occurrence result."""

    canary_id: str
    canary_sha256: str
    allowed_occurrences: int
    observed_occurrences: int
    status: str


def load_security_controls(path: Path) -> tuple[SecurityControl, ...]:
    """Load the frozen closed control manifest without executing its content."""
    payload = _load_json(path)
    if set(payload) != {"controls", "manifest_version"} or payload["manifest_version"] != "0.1.0":
        raise SecurityEvidenceMalformed("security control manifest fields are invalid")
    raw_controls = payload["controls"]
    if not isinstance(raw_controls, list) or not raw_controls:
        raise SecurityEvidenceMalformed("security control manifest is empty")
    controls: list[SecurityControl] = []
    for raw in raw_controls:
        if not isinstance(raw, dict) or set(raw) != {
            "control_id",
            "invariant",
            "test_nodes",
            "threat",
        }:
            raise SecurityEvidenceMalformed("security control fields are invalid")
        nodes = _strings(raw["test_nodes"])
        controls.append(
            SecurityControl(
                control_id=_identifier(raw["control_id"]),
                threat=_identifier(raw["threat"]),
                invariant=_identifier(raw["invariant"]),
                test_nodes=nodes,
            )
        )
    ids = tuple(item.control_id for item in controls)
    nodes = tuple(node for item in controls for node in item.test_nodes)
    if len(ids) != len(set(ids)) or len(nodes) != len(set(nodes)):
        raise SecurityEvidenceMalformed("security controls or test nodes are duplicate")
    return tuple(sorted(controls, key=lambda item: item.control_id))


def evaluate_security_controls(
    controls: Sequence[SecurityControl], results: Sequence[TestNodeResult]
) -> tuple[EvidenceCheck, ...]:
    """Require one passing, non-skipped result for every declared test node."""
    by_node: dict[str, TestNodeResult] = {}
    for result in results:
        if result.node_id in by_node or result.duration_ms < 0:
            raise SecurityEvidenceMalformed("test result is duplicate or malformed")
        if result.status not in {"passed", "failed", "skipped", "unavailable"}:
            raise SecurityEvidenceMalformed("test result status is unsupported")
        by_node[result.node_id] = result
    expected_nodes = {node for control in controls for node in control.test_nodes}
    if set(by_node) - expected_nodes:
        raise SecurityEvidenceMalformed("test result is not allowlisted")
    checks: list[EvidenceCheck] = []
    for control in controls:
        matches = tuple(by_node.get(node) for node in control.test_nodes)
        passed = all(item is not None and item.status == "passed" for item in matches)
        checks.append(
            EvidenceCheck(
                check_id=control.control_id,
                status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
                reason=None if passed else "security-control-incomplete",
                observed=sum(item is not None and item.status == "passed" for item in matches),
                expected=len(control.test_nodes),
                evidence_ids=tuple(
                    canonical_sha256(
                        {
                            "duration_ms": item.duration_ms,
                            "node_id": item.node_id,
                            "status": item.status,
                        }
                    )
                    for item in matches
                    if item is not None
                ),
            )
        )
    return tuple(checks)


def scan_privacy_canaries(
    paths: Sequence[Path],
    canaries: Mapping[str, bytes],
    *,
    allowed_occurrences: Mapping[str, int] | None = None,
) -> tuple[PrivacyScanResult, ...]:
    """Scan bounded files and archives while serializing only canary digests/counts."""
    if not canaries or any(not value for value in canaries.values()):
        raise SecurityEvidenceMalformed("privacy canaries must be non-empty")
    allowed = dict(allowed_occurrences or {})
    counts = {canary_id: 0 for canary_id in canaries}
    consumed = 0
    for path in paths:
        chunks, size = _scan_chunks(path, remaining=_MAX_SCAN_BYTES - consumed)
        consumed += size
        for chunk in chunks:
            for canary_id, canary in canaries.items():
                counts[canary_id] += chunk.count(canary)
    results = []
    for canary_id in sorted(canaries):
        limit = allowed.get(canary_id, 0)
        if limit < 0:
            raise SecurityEvidenceMalformed("allowed canary occurrences cannot be negative")
        observed = counts[canary_id]
        results.append(
            PrivacyScanResult(
                canary_id=_identifier(canary_id),
                canary_sha256=f"sha256:{hashlib.sha256(canaries[canary_id]).hexdigest()}",
                allowed_occurrences=limit,
                observed_occurrences=observed,
                status="passed" if observed <= limit else "failed",
            )
        )
    return tuple(results)


def privacy_checks(results: Sequence[PrivacyScanResult]) -> tuple[EvidenceCheck, ...]:
    """Convert privacy scan results to release-suite checks."""
    return tuple(
        EvidenceCheck(
            check_id=f"privacy-{result.canary_id}",
            status=(EvidenceStatus.PASSED if result.status == "passed" else EvidenceStatus.FAILED),
            reason=None if result.status == "passed" else "privacy-disclosure-detected",
            observed=result.observed_occurrences,
            expected=result.allowed_occurrences,
            evidence_ids=(
                canonical_sha256(
                    {
                        "allowed_occurrences": result.allowed_occurrences,
                        "canary_id": result.canary_id,
                        "canary_sha256": result.canary_sha256,
                        "observed_occurrences": result.observed_occurrences,
                        "status": result.status,
                    }
                ),
            ),
        )
        for result in results
    )


def _scan_chunks(path: Path, *, remaining: int) -> tuple[tuple[bytes, ...], int]:
    if remaining < 0 or path.is_symlink() or not path.is_file():
        raise SecurityEvidenceMalformed("privacy scan path is unsafe or exceeds limit")
    size = path.stat().st_size
    if size > remaining:
        raise SecurityEvidenceMalformed("privacy scan byte limit exceeded")
    suffixes = tuple(item.casefold() for item in path.suffixes)
    if suffixes and suffixes[-1] == ".zip":
        return _zip_chunks(path, remaining)
    if suffixes and suffixes[-1] in {".tar", ".tgz", ".gz"}:
        return _tar_chunks(path, remaining)
    data = path.read_bytes()
    if len(data) != size:
        raise SecurityEvidenceMalformed("privacy scan file changed during read")
    return (data,), len(data)


def _zip_chunks(path: Path, remaining: int) -> tuple[tuple[bytes, ...], int]:
    chunks: list[bytes] = []
    total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise SecurityEvidenceMalformed("privacy archive member limit exceeded")
            for member in members:
                _safe_member(member.filename)
                if member.is_dir():
                    continue
                total += member.file_size
                if total > remaining:
                    raise SecurityEvidenceMalformed("privacy archive byte limit exceeded")
                chunks.append(archive.read(member))
    except (OSError, zipfile.BadZipFile) as error:
        raise SecurityEvidenceMalformed("privacy archive is malformed") from error
    return tuple(chunks), total


def _tar_chunks(path: Path, remaining: int) -> tuple[tuple[bytes, ...], int]:
    chunks: list[bytes] = []
    total = 0
    try:
        with tarfile.open(path, mode="r:*") as archive:
            members = archive.getmembers()
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise SecurityEvidenceMalformed("privacy archive member limit exceeded")
            for member in members:
                _safe_member(member.name)
                if not member.isfile():
                    if member.issym() or member.islnk():
                        raise SecurityEvidenceMalformed("privacy archive link is unsafe")
                    continue
                total += member.size
                if total > remaining:
                    raise SecurityEvidenceMalformed("privacy archive byte limit exceeded")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise SecurityEvidenceMalformed("privacy archive member is unreadable")
                chunks.append(extracted.read())
    except (OSError, tarfile.TarError) as error:
        raise SecurityEvidenceMalformed("privacy archive is malformed") from error
    return tuple(chunks), total


def _safe_member(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise SecurityEvidenceMalformed("privacy archive path is unsafe")


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise SecurityEvidenceMalformed("security control manifest is unsafe")
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SecurityEvidenceMalformed("security control manifest is not strict JSON") from error
    if not isinstance(value, dict):
        raise SecurityEvidenceMalformed("security control manifest must be an object")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SecurityEvidenceMalformed("duplicate JSON key")
        value[key] = item
    return value


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
        raise SecurityEvidenceMalformed("expected a non-empty string list")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise SecurityEvidenceMalformed("string list contains duplicates")
    return result


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise SecurityEvidenceMalformed("identifier is invalid")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in value):
        raise SecurityEvidenceMalformed("identifier is invalid")
    return value


__all__ = [
    "PrivacyScanResult",
    "SecurityControl",
    "SecurityEvidenceMalformed",
    "TestNodeResult",
    "evaluate_security_controls",
    "load_security_controls",
    "privacy_checks",
    "scan_privacy_canaries",
]
