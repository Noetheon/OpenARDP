"""Generate and drift-check the complete F015 locked-component review inventory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "benchmarks" / "release" / "v0.1.0" / "dependency-review.json"
DIRECT = frozenset({"docling", "openardp", "pillow", "pydantic", "pypdfium2", "rfc8785"})
REVIEWED_LICENSES = {
    "docling": "MIT",
    "openardp": "Apache-2.0",
    "pillow": "MIT-CMU",
    "pydantic": "MIT",
}


def build_review() -> dict[str, Any]:
    """Return deterministic review rows for every component in the locked uv SBOM."""
    raw = _uv_sbom()
    metadata = raw.get("metadata")
    components = raw.get("components")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("component"), dict):
        raise RuntimeError("uv SBOM root component is missing")
    if not isinstance(components, list):
        raise RuntimeError("uv SBOM component inventory is missing")
    rows = []
    for component in [metadata["component"], *components]:
        if not isinstance(component, dict):
            raise RuntimeError("uv SBOM component is malformed")
        name = component.get("name")
        version = component.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise RuntimeError("uv SBOM component identity is malformed")
        normalized = name.casefold()
        row: dict[str, Any] = {
            "component": f"{name}=={version}",
            "direct": normalized in DIRECT,
            "disposition": "approved" if normalized in REVIEWED_LICENSES else "deferred",
        }
        if normalized in REVIEWED_LICENSES:
            row["license_expression"] = REVIEWED_LICENSES[normalized]
        else:
            row["license_state"] = "unreviewed-metadata-unavailable"
        rows.append(row)
    rows.sort(key=lambda item: item["component"].casefold())
    return {
        "review_version": "0.1.0",
        "generator": "scripts/generate_dependency_review.py",
        "components": rows,
        "maintenance_review": {
            "direct_dependencies_complete": True,
            "transitive_maintenance_review": "deferred",
            "workflow_actions": [
                {
                    "action": "actions/checkout",
                    "commit": "3d3c42e5aac5ba805825da76410c181273ba90b1",
                    "disposition": "pinned",
                },
                {
                    "action": "astral-sh/setup-uv",
                    "commit": "c771a70e6277c0a99b617c7a806ffedaca235ff9",
                    "disposition": "pinned",
                },
                {
                    "action": "actions/upload-artifact",
                    "commit": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
                    "disposition": "pinned",
                },
                {
                    "action": "actions/download-artifact",
                    "commit": "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
                    "disposition": "pinned",
                },
            ],
        },
        "vulnerability_snapshot": {
            "schema": "OSV-1.7.4",
            "observed_at": "1970-01-01T00:00:00Z",
            "findings": [],
            "status": "unavailable",
            "reason": "current-snapshot-not-committed",
        },
    }


def _uv_sbom() -> dict[str, Any]:
    executable = shutil.which("uv")
    if executable is None:
        raise RuntimeError("uv executable is unavailable")
    with tempfile.TemporaryDirectory(prefix="openardp-sbom-") as directory:
        path = Path(directory) / "raw.cdx.json"
        subprocess.run(  # noqa: S603 - fixed uv executable and closed argument vector
            [
                executable,
                "export",
                "--locked",
                "--format",
                "cyclonedx1.5",
                "--all-extras",
                "--no-dev",
                "--preview-features",
                "sbom-export",
                "--output-file",
                str(path),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise RuntimeError("uv SBOM must be a JSON object")
    return value


def _bytes() -> bytes:
    return (json.dumps(build_review(), indent=2, sort_keys=True) + "\n").encode()


def _write_atomic(data: bytes) -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{DESTINATION.name}.", dir=DESTINATION.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, DESTINATION)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    """Write or check the committed dependency review."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    expected = _bytes()
    if arguments.write:
        _write_atomic(expected)
        print(f"wrote {DESTINATION.relative_to(ROOT)}")
        return 0
    if not DESTINATION.is_file() or DESTINATION.read_bytes() != expected:
        print("dependency review drift")
        return 1
    print(f"all {len(build_review()['components'])} component reviews are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
