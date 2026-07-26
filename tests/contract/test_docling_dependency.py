"""Contract tests for the optional exactly locked Docling provider."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]
PYPROJECT = ROOT / "pyproject.toml"
EXPECTED_DOCLING_VERSION = "2.114.0"


def test_docling_extra_is_exact_and_not_a_core_dependency() -> None:
    """Keep the provider selectable, exact and absent from the core dependency set."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]

    assert f"docling=={EXPECTED_DOCLING_VERSION}" not in project["dependencies"]
    assert project["optional-dependencies"]["docling"] == [f"docling=={EXPECTED_DOCLING_VERSION}"]


def test_locked_environment_installs_the_reviewed_docling_release() -> None:
    """Exercise the exact provider selected by the all-extras locked environment."""
    assert importlib.metadata.version("docling") == EXPECTED_DOCLING_VERSION


def test_core_package_import_does_not_import_docling() -> None:
    """Keep domain/contract use provider-lazy even when the extra is installed."""
    code = (
        "import sys; import openardp; "
        "assert not any(name == 'docling' or name.startswith('docling.') for name in sys.modules)"
    )
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
