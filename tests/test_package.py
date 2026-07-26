"""Contracts for the minimal installable OpenARDP package."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import pkgutil
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
    "openardp.adapters.docling",
    "openardp.interfaces.mcp",
)
DOMAIN_MODULES = {
    "block",
    "common",
    "context",
    "derivation",
    "evidence",
    "identity",
    "manifest",
    "relation",
    "rich_ingestion",
    "storage",
    "ingestion",
    "search",
}
PORT_MODULES = {"catalog", "object_store", "parser"}
ADAPTER_MODULES = {
    "docling_native",
    "filesystem_cas",
    "isolated_docling",
    "isolated_parser",
    "local_source",
    "local_workspace",
    "sqlite_catalog",
    "sqlite_migrations",
    "text_parser",
}
SERVICE_MODULES = {
    "document_query",
    "ingestion",
    "persistence",
    "reachability",
    "rich_evidence",
    "rich_ingestion",
    "search",
}
INTERFACE_MODULES = {"cli"}


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
    """Prevent later work-package behavior from leaking into the current feature."""
    assert importlib.util.find_spec(module_name) is None


@pytest.mark.parametrize(
    ("package_name", "expected_modules"),
    (
        ("openardp.domain", DOMAIN_MODULES),
        ("openardp.ports", PORT_MODULES),
        ("openardp.adapters", ADAPTER_MODULES),
        ("openardp.services", SERVICE_MODULES),
        ("openardp.interfaces", INTERFACE_MODULES),
    ),
)
def test_module_surface_is_bounded_to_feature_007(
    package_name: str,
    expected_modules: set[str],
) -> None:
    """Expose exactly the reviewed F002-F007 modules."""
    package = importlib.import_module(package_name)
    discovered = {module.name for module in pkgutil.iter_modules(package.__path__)}
    assert discovered == expected_modules


def test_typing_marker_is_packaged() -> None:
    """Advertise inline typing for the installable package."""
    package_root = Path(openardp.__file__).resolve().parent
    assert (package_root / "py.typed").is_file()


def test_exact_openardp_console_script_is_installed(repository_root: Path) -> None:
    """Expose only the reviewed F004 command composition root."""
    project = _project_metadata(repository_root)
    assert project["scripts"] == {"openardp": "openardp.interfaces.cli:main"}
    openardp_entries = {
        (entry.name, entry.value)
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.value.startswith("openardp")
    }
    assert openardp_entries == {("openardp", "openardp.interfaces.cli:main")}
