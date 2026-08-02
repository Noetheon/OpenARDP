"""Synthetic miniature PDF model-bundle fixtures for F023 tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openardp.domain.identity import canonical_json_bytes

MODEL_PAYLOADS = {
    "docling-project--docling-layout-heron/config.json": b'{"model":"layout"}\n',
    "docling-project--docling-models/model_artifacts/tableformer/accurate/tm_config.json": (
        b'{"model":"table"}\n'
    ),
}
LICENSE_PAYLOADS = {
    "licenses/Apache-2.0.txt": b"Apache License 2.0 synthetic fixture\n",
    "licenses/CDLA-Permissive-2.0.txt": b"CDLA Permissive 2.0 synthetic fixture\n",
}
NOTICE = b"Synthetic test-only third-party notices.\n"


def digest(payload: bytes) -> str:
    """Return an OpenARDP SHA-256 identifier for fixture bytes."""
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def source_lock_dict() -> dict[str, object]:
    """Build one valid closed source lock using tiny redistributable bytes."""
    sources = [
        {
            "repository_id": "docling-project/docling-layout-heron",
            "revision": "a" * 40,
            "license_id": "Apache-2.0",
            "license_evidence_url": "https://example.invalid/layout-license",
        },
        {
            "repository_id": "docling-project/docling-models",
            "revision": "b" * 40,
            "license_id": "CDLA-Permissive-2.0",
            "license_evidence_url": "https://example.invalid/table-license",
        },
    ]
    files: list[dict[str, object]] = []
    for destination, payload in MODEL_PAYLOADS.items():
        layout = "layout-heron" in destination
        files.append(
            {
                "repository_id": sources[0 if layout else 1]["repository_id"],
                "revision": sources[0 if layout else 1]["revision"],
                "source_path": (
                    "config.json"
                    if layout
                    else "model_artifacts/tableformer/accurate/tm_config.json"
                ),
                "destination_path": destination,
                "sha256": digest(payload),
                "byte_length": len(payload),
                "license_id": sources[0 if layout else 1]["license_id"],
            }
        )
    reviews = [
        {
            "path": path,
            "sha256": digest(payload),
            "byte_length": len(payload),
        }
        for path, payload in LICENSE_PAYLOADS.items()
    ]
    reviews.append(
        {
            "path": "THIRD_PARTY_NOTICES.md",
            "sha256": digest(NOTICE),
            "byte_length": len(NOTICE),
        }
    )
    reviews.sort(key=lambda item: str(item["path"]))
    return {
        "schema_version": "0.1.0",
        "bundle_name": "synthetic-docling-pdf",
        "bundle_version": "test-v1",
        "docling_version": "2.114.0",
        "provider_profile": "openardp-docling-native",
        "provider_profile_version": "0.1.0",
        "max_file_bytes": 1_024,
        "max_total_asset_bytes": 2_048,
        "sources": sources,
        "files": files,
        "review_files": reviews,
    }


def write_source_material(root: Path) -> Path:
    """Write a canonical source lock plus exact local review files."""
    root.mkdir(parents=True)
    lock = root / "source-lock.json"
    lock.write_bytes(canonical_json_bytes(source_lock_dict()) + b"\n")
    for path, payload in LICENSE_PAYLOADS.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (root / "THIRD_PARTY_NOTICES.md").write_bytes(NOTICE)
    return lock


def write_installation(root: Path) -> tuple[Path, Path]:
    """Materialize a valid synthetic installation and return root plus source lock."""
    from openardp.adapters.docling_bundle import materialize_control_files

    source_root = root.parent / f"{root.name}-source"
    lock_path = write_source_material(source_root)
    root.mkdir()
    for path, payload in MODEL_PAYLOADS.items():
        target = root / "assets" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    materialize_control_files(root, lock_path=lock_path)
    return root, lock_path


def load_json(path: Path) -> dict[str, object]:
    """Load one fixture JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value
