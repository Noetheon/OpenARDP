"""Validate committed F015 release evidence structure, identity and projections."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn

from openardp.domain.identity import canonical_json_bytes
from openardp.domain.release import ReleaseDecision, ReleaseEvidenceBundle
from openardp.services.release_gate import build_claim_map, render_release_report

_EXPECTED = {
    "artifacts.json",
    "checksums.json",
    "claim-map.json",
    "decision.json",
    "manifest.json",
    "platform-evidence.json",
    "release-evidence.json",
    "report.md",
    "sbom.cdx.json",
}
_MAX_FILE_BYTES = 64 * 1024 * 1024
_FORBIDDEN = (b"/Users/", b"C:\\Users\\", b"PRIVATE-RELEASE-CANARY")


class ReleaseValidationError(ValueError):
    """Raised when committed release evidence is inconsistent or unsafe."""


def validate(directory: Path) -> None:
    """Validate exact inventory, hashes, canonical roots and derived projections."""
    root = directory.resolve(strict=True)
    if directory.is_symlink() or not root.is_dir():
        raise ReleaseValidationError("release evidence root is unsafe")
    names = {item.name for item in root.iterdir()}
    if names != _EXPECTED:
        raise ReleaseValidationError("release evidence inventory is incomplete")
    files = {name: _read(root / name) for name in names}
    manifest = _object(files["manifest.json"])
    checksums = _object(files["checksums.json"])
    _verify_inventory(manifest, files, excluded={"manifest.json"})
    _verify_inventory(checksums, files, excluded={"checksums.json", "manifest.json"})
    bundle = ReleaseEvidenceBundle.model_validate_json(files["release-evidence.json"])
    decision = ReleaseDecision.model_validate_json(files["decision.json"])
    if bundle.decision != decision or manifest.get("decision_id") != decision.decision_id:
        raise ReleaseValidationError("release decision identity is inconsistent")
    if files["platform-evidence.json"] != (
        canonical_json_bytes(bundle.platform_evidence[0].model_dump(mode="json")) + b"\n"
    ):
        raise ReleaseValidationError("platform evidence projection drift")
    if files["claim-map.json"] != canonical_json_bytes(build_claim_map(decision)) + b"\n":
        raise ReleaseValidationError("claim map projection drift")
    if files["report.md"] != render_release_report(decision):
        raise ReleaseValidationError("release report projection drift")
    sbom = _object(files["sbom.cdx.json"])
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.5":
        raise ReleaseValidationError("release SBOM is invalid")
    if any(canary in data for data in files.values() for canary in _FORBIDDEN):
        raise ReleaseValidationError("release evidence contains a forbidden privacy value")


def _verify_inventory(
    inventory: dict[str, Any], files: dict[str, bytes], *, excluded: set[str]
) -> None:
    rows = inventory.get("files")
    if not isinstance(rows, list):
        raise ReleaseValidationError("release file inventory is malformed")
    observed: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict) or set(raw) != {"byte_length", "path", "sha256"}:
            raise ReleaseValidationError("release file inventory row is malformed")
        path = raw["path"]
        if not isinstance(path, str) or path in observed or path not in files or "/" in path:
            raise ReleaseValidationError("release file inventory path is invalid")
        observed.add(path)
        data = files[path]
        if raw["byte_length"] != len(data) or raw["sha256"] != _digest(data):
            raise ReleaseValidationError("release file inventory digest mismatch")
    if observed != set(files) - excluded:
        raise ReleaseValidationError("release file inventory set is incomplete")


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_FILE_BYTES:
        raise ReleaseValidationError("release evidence file is unsafe")
    data = path.read_bytes()
    if len(data) != path.stat().st_size:
        raise ReleaseValidationError("release evidence changed during read")
    return data


def _object(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            data,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ReleaseValidationError("release evidence JSON is malformed") from error
    if not isinstance(value, dict):
        raise ReleaseValidationError("release evidence JSON root must be an object")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReleaseValidationError("duplicate JSON key")
        value[key] = item
    return value


def _reject_constant(_value: str) -> NoReturn:
    raise ReleaseValidationError("non-finite JSON number")


def _digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def main() -> int:
    """Validate one release evidence directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    arguments = parser.parse_args()
    try:
        validate(arguments.directory)
    except (OSError, ReleaseValidationError, ValueError):
        print("release evidence validation failed")
        return 1
    print("release evidence validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
