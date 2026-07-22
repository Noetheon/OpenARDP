"""Contracts for the minimal installable OpenARDP package."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import openardp

BOUNDARY_MODULES = (
    "openardp.domain",
    "openardp.ports",
    "openardp.adapters",
    "openardp.services",
    "openardp.interfaces",
)
FORBIDDEN_MODULES = (
    "openardp.core",
    "openardp.domain.models",
    "openardp.interfaces.cli",
)


def _project_metadata(repository_root: Path) -> dict[str, Any]:
    """Load project metadata from the repository configuration."""
    with (repository_root / "pyproject.toml").open("rb") as stream:
        data: dict[str, Any] = tomllib.load(stream)
    return data["project"]


def test_source_and_distribution_versions_match(repository_root: Path) -> None:
    """Keep the public source version aligned with build metadata."""
    project = _project_metadata(repository_root)
    assert openardp.__version__ == project["version"]
    assert importlib.metadata.version("openardp") == project["version"]


@pytest.mark.parametrize("module_name", BOUNDARY_MODULES)
def test_architecture_boundary_is_importable_and_documented(module_name: str) -> None:
    """Expose each required architectural boundary as a documented namespace."""
    module: ModuleType = importlib.import_module(module_name)
    assert module.__doc__ is not None
    assert module.__doc__.strip()


@pytest.mark.parametrize("module_name", FORBIDDEN_MODULES)
def test_later_feature_module_is_absent(module_name: str) -> None:
    """Prevent later work-package behavior from leaking into feature 001."""
    assert importlib.util.find_spec(module_name) is None


def test_typing_marker_is_packaged() -> None:
    """Advertise inline typing for the installable package."""
    package_root = Path(openardp.__file__).resolve().parent
    assert (package_root / "py.typed").is_file()


def test_no_openardp_console_script_is_installed(repository_root: Path) -> None:
    """Keep product commands outside the repository-baseline feature."""
    project = _project_metadata(repository_root)
    assert "scripts" not in project
    openardp_entries = {
        entry.name
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.value.startswith("openardp")
    }
    assert openardp_entries == set()
