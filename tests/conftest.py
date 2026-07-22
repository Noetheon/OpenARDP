"""Shared fixtures for repository-baseline contract tests."""

from pathlib import Path

import pytest


@pytest.fixture
def repository_root() -> Path:
    """Return the checked-out repository root."""
    return Path(__file__).resolve().parents[1]
