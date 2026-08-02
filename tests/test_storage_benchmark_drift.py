"""Committed F022 benchmark evidence drift gate."""

from pathlib import Path

from scripts.validate_storage_benchmark import validate


def test_committed_storage_benchmark_is_independently_valid() -> None:
    """Recompute the checked-in PASS from raw machine evidence."""
    repository = Path(__file__).parents[1]
    result = repository / "benchmarks/storage/v0.1.0/results/reference-macos-arm64"

    assert validate(repository, result)["decision"] == "PASS"
