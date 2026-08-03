"""Additive compatibility and dependency review gates for F011."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any

from tests.test_repository_contract import (
    F007_EVIDENCE_CORPUS_DIGEST,
    F007_SCHEMA_HASHES,
    F007_VECTOR_HASHES,
    F008_ADDITIVE_SCHEMA_HASHES,
    F008_ADDITIVE_VECTOR_HASHES,
    F009_FROZEN_DESCRIPTOR_HASHES,
    _tree_digest,
)


def _toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def test_all_eleven_prior_schemas_vectors_and_mcp_descriptors_remain_frozen(
    repository_root: Path,
) -> None:
    """Prove the visual root is additive across every prior public surface."""
    schemas = {**F007_SCHEMA_HASHES, **F008_ADDITIVE_SCHEMA_HASHES}
    assert len(schemas) == 11
    for relative, digest in schemas.items():
        actual = hashlib.sha256((repository_root / "schemas" / relative).read_bytes()).hexdigest()
        assert actual == digest
    vectors = {**F007_VECTOR_HASHES, **F008_ADDITIVE_VECTOR_HASHES}
    for relative, digest in vectors.items():
        assert hashlib.sha256((repository_root / relative).read_bytes()).hexdigest() == digest
    for relative, digest in F009_FROZEN_DESCRIPTOR_HASHES.items():
        assert hashlib.sha256((repository_root / relative).read_bytes()).hexdigest() == digest
    assert (
        _tree_digest(repository_root / "conformance/evidence/v0.1.0") == F007_EVIDENCE_CORPUS_DIGEST
    )


def test_only_reviewed_optional_dependency_surfaces_are_present(
    repository_root: Path,
) -> None:
    """Allow only exact reviewed optional provider dependency sets beside the core."""
    project = _toml(repository_root / "pyproject.toml")["project"]
    assert project["dependencies"] == [
        "pydantic>=2.12.5,<2.13",
        "rfc8785>=0.1.4,<0.2",
    ]
    assert project["optional-dependencies"] == {
        "docling": ["docling==2.114.0"],
        "semantic": [
            "huggingface-hub==1.24.0",
            "safetensors==0.8.0",
            "torch==2.13.0",
            "transformers==5.8.1",
        ],
        "visual": ["Pillow==12.3.0", "pypdfium2==5.12.1"],
    }
    lock = _toml(repository_root / "uv.lock")
    packages = {
        (entry["name"], entry["version"]) for entry in lock["package"] if "version" in entry
    }
    assert ("pillow", "12.3.0") in packages
    assert ("pypdfium2", "5.12.1") in packages
    assert ("torch", "2.13.0") in packages
    assert ("transformers", "5.8.1") in packages
