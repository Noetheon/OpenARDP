"""Generate and drift-check the normalized, license-enriched F015 CycloneDX SBOM."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from openardp.adapters.release_supply_chain import normalize_cyclonedx

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "benchmarks" / "release" / "v0.1.0" / "dependency-review.json"
DESTINATION = ROOT / "release" / "evidence" / "v0.1.0" / "sbom.cdx.json"


def build_sbom() -> dict[str, Any]:
    """Export the exact lock and normalize non-deterministic uv metadata."""
    executable = shutil.which("uv")
    if executable is None:
        raise RuntimeError("uv executable is unavailable")
    with tempfile.TemporaryDirectory(prefix="openardp-sbom-") as directory:
        raw_path = Path(directory) / "raw.cdx.json"
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
                str(raw_path),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        raw = json.loads(raw_path.read_bytes())
    review = json.loads(REVIEW.read_bytes())
    if not isinstance(raw, dict) or not isinstance(review, dict):
        raise RuntimeError("SBOM inputs must be JSON objects")
    return normalize_cyclonedx(raw, review)


def _bytes() -> bytes:
    return (json.dumps(build_sbom(), indent=2, sort_keys=True) + "\n").encode()


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
    """Write or check the normalized committed SBOM."""
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
        print("release SBOM drift")
        return 1
    print(f"all {len(build_sbom()['components'])} SBOM components are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
