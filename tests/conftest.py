"""Shared fixtures for repository-baseline contract tests."""

from pathlib import Path

import pytest


@pytest.fixture
def repository_root() -> Path:
    """Return the checked-out repository root."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def without_subprocess_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep heavyweight provider children out of parent-process coverage tracing."""
    for name in (
        "COV_CORE_BRANCH",
        "COV_CORE_CONFIG",
        "COV_CORE_CONTEXT",
        "COV_CORE_DATAFILE",
        "COV_CORE_SOURCE",
    ):
        monkeypatch.delenv(name, raising=False)
