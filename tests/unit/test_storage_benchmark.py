"""Independent F022 storage benchmark validation tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from openardp.domain.identity import canonical_json_bytes
from scripts.storage_benchmark import inventory
from scripts.validate_storage_benchmark import validate

REPOSITORY = Path(__file__).parents[2]
COMMITTED = REPOSITORY / "benchmarks/storage/v0.1.0/results/reference-macos-arm64"


def _copy_result(tmp_path: Path) -> Path:
    destination = tmp_path / "result"
    shutil.copytree(COMMITTED, destination)
    return destination


def test_inventory_reconciles_closed_categories(tmp_path: Path) -> None:
    """Every regular file contributes once to category and complete totals."""
    root = tmp_path / "workspace"
    (root / "objects/sha256/aa").mkdir(parents=True)
    (root / "objects/openardp-deflate-dict-v1/sha256/bb").mkdir(parents=True)
    (root / "catalog.sqlite3").write_bytes(b"catalog")
    (root / "objects/sha256/aa/raw").write_bytes(b"raw")
    (root / "objects/openardp-deflate-dict-v1/sha256/bb/compact").write_bytes(b"compact")

    result = inventory(root)

    assert result["totals"]["file_count"] == 3
    assert result["totals"]["logical_bytes"] == len(b"catalograwcompact")
    assert (
        sum(item["logical_bytes"] for item in result["categories"].values())
        == result["totals"]["logical_bytes"]
    )


def test_validator_rejects_category_arithmetic_drift(tmp_path: Path) -> None:
    """A producer cannot hide bytes by changing only an aggregate total."""
    result = _copy_result(tmp_path)
    observations = json.loads((result / "observations.json").read_bytes())
    observations[0]["after"]["totals"]["logical_bytes"] += 1
    (result / "observations.json").write_bytes(canonical_json_bytes(observations) + b"\n")

    with pytest.raises(ValueError, match="category arithmetic"):
        validate(REPOSITORY, result)


def test_validator_rejects_privacy_marker(tmp_path: Path) -> None:
    """Body-free evidence rejects an absolute user path before trusting projections."""
    result = _copy_result(tmp_path)
    decision = json.loads((result / "decision.json").read_bytes())
    decision["leak"] = "/Users/example/private.txt"
    (result / "decision.json").write_bytes(canonical_json_bytes(decision) + b"\n")

    with pytest.raises(ValueError, match="privacy marker"):
        validate(REPOSITORY, result)


def test_validator_rejects_extra_result_file(tmp_path: Path) -> None:
    """The published evidence inventory is exactly five files."""
    result = _copy_result(tmp_path)
    (result / "extra.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="inventory mismatch"):
        validate(REPOSITORY, result)
