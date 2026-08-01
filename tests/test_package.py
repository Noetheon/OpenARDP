"""Contracts for the minimal installable OpenARDP package."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import pkgutil
import subprocess
import sys
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
    "context_compilation",
    "derivation",
    "derivation_lifecycle",
    "evidence",
    "identity",
    "manifest",
    "relation",
    "reconciliation",
    "rich_ingestion",
    "storage",
    "ingestion",
    "search",
    "visual",
    "watcher",
}
PORT_MODULES = {"catalog", "context", "object_store", "parser", "visual", "watcher"}
ADAPTER_MODULES = {
    "context_candidates",
    "context_estimators",
    "docling_native",
    "filesystem_cas",
    "isolated_docling",
    "isolated_parser",
    "isolated_visual",
    "local_source",
    "local_watch",
    "local_workspace",
    "sqlite_catalog",
    "sqlite_migrations",
    "text_parser",
    "visual_pdfium",
    "visual_policy",
}
SERVICE_MODULES = {
    "context_compiler",
    "document_query",
    "derivations",
    "ingestion",
    "persistence",
    "reachability",
    "reconciliation",
    "rich_evidence",
    "rich_ingestion",
    "search",
    "visual_evidence",
    "visual_interpretation",
    "watcher",
}
INTERFACE_MODULES = {"cli", "mcp_protocol", "mcp_server"}


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
def test_module_surface_is_bounded_to_feature_012(
    package_name: str,
    expected_modules: set[str],
) -> None:
    """Expose exactly the reviewed F002-F012 modules."""
    package = importlib.import_module(package_name)
    discovered = {module.name for module in pkgutil.iter_modules(package.__path__)}
    assert discovered == expected_modules


def test_no_mcp_or_network_dependency_is_introduced(repository_root: Path) -> None:
    """Keep the F009 transport stdlib-only inside the locked dependency set."""
    project = _project_metadata(repository_root)
    declared = list(project.get("dependencies", []))
    for extra_requirements in project.get("optional-dependencies", {}).values():
        declared.extend(extra_requirements)
    forbidden_fragments = (
        "mcp",
        "anyio",
        "asyncio",
        "trio",
        "httpx",
        "aiohttp",
        "starlette",
        "fastapi",
        "uvicorn",
        "websocket",
        "requests",
        "flask",
        "grpc",
    )
    names = [
        requirement.split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].lower()
        for requirement in declared
    ]
    for name in names:
        for fragment in forbidden_fragments:
            assert fragment not in name, f"forbidden F009 dependency: {name}"


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


def test_context_surfaces_import_without_loading_provider_runtime(
    repository_root: Path,
) -> None:
    """Keep Phase 2 compiler contracts usable in the core-only install."""
    code = """
import sys
import openardp.domain.context_compilation
import openardp.ports.context
import openardp.ports.catalog
import openardp.adapters.context_estimators
import openardp.adapters.context_candidates
import openardp.services.context_compiler
import openardp.adapters
import openardp.services
assert not any(name == "docling" or name.startswith("docling.") for name in sys.modules)
"""
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and literal test code
        [sys.executable, "-c", code],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
