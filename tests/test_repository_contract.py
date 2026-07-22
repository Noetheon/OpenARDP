"""Repository-wide contracts for the OpenARDP engineering baseline."""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pytest_socket import SocketBlockedError

REQUIRED_FILES = (
    "AGENTS.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "START_HERE.md",
    "VALIDATION.md",
    "pyproject.toml",
    "uv.lock",
)
ALLOWED_AGENT_PATH = re.compile(r"^\.agents/skills/[^/]+/SKILL\.md$")
ACTION_REFERENCE = re.compile(
    r"^\s*-?\s*uses:\s*([^@\s]+)@([0-9a-f]{40})\s+#\s+(v\d+\.\d+\.\d+)\s*$",
    re.MULTILINE,
)
EXPECTED_ACTIONS = {
    (
        "actions/checkout",
        "3d3c42e5aac5ba805825da76410c181273ba90b1",
        "v7.0.1",
    ),
    (
        "astral-sh/setup-uv",
        "c771a70e6277c0a99b617c7a806ffedaca235ff9",
        "v9.0.0",
    ),
}


def _project_configuration(repository_root: Path) -> dict[str, Any]:
    """Load the complete project configuration."""
    with (repository_root / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def test_required_repository_files_exist(repository_root: Path) -> None:
    """Require every baseline governance and reproducibility artifact."""
    missing = [name for name in REQUIRED_FILES if not (repository_root / name).is_file()]
    assert missing == []


def test_public_json_schemas_are_draft_2020_12(repository_root: Path) -> None:
    """Keep checked-in public schemas syntactically valid without implementing them."""
    schema_paths = sorted((repository_root / "schemas").glob("*.schema.json"))
    assert schema_paths
    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(schema)


def test_only_reviewed_agent_skills_are_tracked(repository_root: Path) -> None:
    """Prevent local agent state from entering the reviewed integration directory."""
    git_executable = shutil.which("git")
    assert git_executable is not None
    result = subprocess.run(  # noqa: S603 -- executable resolved from PATH for this test
        [git_executable, "ls-files", ".agents"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line for line in result.stdout.splitlines() if line]
    assert tracked
    assert all(ALLOWED_AGENT_PATH.fullmatch(path) for path in tracked)


def test_project_metadata_has_only_reviewed_runtime_dependencies(repository_root: Path) -> None:
    """Keep F004 on the standard library plus reviewed F002 dependencies."""
    project = _project_configuration(repository_root)["project"]
    assert project["requires-python"] == ">=3.12,<3.13"
    assert project.get("dependencies", []) == [
        "pydantic>=2.12.5,<2.13",
        "rfc8785>=0.1.4,<0.2",
    ]
    assert project.get("optional-dependencies", {}) == {}
    assert project["scripts"] == {"openardp": "openardp.interfaces.cli:main"}
    assert project["license"] == "Apache-2.0"


def test_uv_version_is_repository_constrained(repository_root: Path) -> None:
    """Make the lockfile tool semantics explicit and reviewable."""
    uv_config = _project_configuration(repository_root)["tool"]["uv"]
    assert uv_config["required-version"] == "==0.11.31"
    assert uv_config["preview-features"] == ["centralized-project-envs"]


def test_ignore_rules_cover_local_state(repository_root: Path) -> None:
    """Exclude common local, secret, coverage and operating-system artifacts."""
    patterns = (repository_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    required = {
        ".venv/",
        ".venv",
        ".venv [0-9]*",
        "venv/",
        ".coverage",
        ".coverage.*",
        ".coverage [0-9]*",
        "coverage.xml",
        ".env",
        ".env.*",
        ".DS_Store",
        "Thumbs.db",
        "Desktop.ini",
    }
    assert required <= set(patterns)


def test_text_contracts_use_cross_platform_lf_checkouts(repository_root: Path) -> None:
    """Keep byte-reviewed schemas and UTF-8 sources stable on Windows checkouts."""
    attributes = (repository_root / ".gitattributes").read_text(encoding="utf-8").splitlines()
    required = {
        "*.json text eol=lf",
        "*.lock text eol=lf",
        "*.md text eol=lf",
        "*.py text eol=lf",
        "*.toml text eol=lf",
        "*.txt text eol=lf",
        "*.yaml text eol=lf",
        "*.yml text eol=lf",
    }
    assert required <= set(attributes)


def test_pytest_enforces_coverage_and_no_network(repository_root: Path) -> None:
    """Keep coverage and network policy inside the authoritative pytest command."""
    config = _project_configuration(repository_root)
    pytest_config = config["tool"]["pytest"]["ini_options"]
    assert pytest_config["pythonpath"] == ["."]
    options = set(pytest_config["addopts"])
    assert {
        "--strict-markers",
        "--strict-config",
        "--disable-socket",
        "--cov=openardp",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=85",
    } <= options
    assert {"pytest-cov>=6.2", "pytest-socket>=0.7"} <= set(pytest_config["required_plugins"])
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 85


def test_socket_access_is_blocked() -> None:
    """Prove that a unit test cannot create a network socket."""
    with pytest.warns(UserWarning, match="tried to use socket"), pytest.raises(SocketBlockedError):
        socket.socket()


def test_lint_and_type_policies_are_strict(repository_root: Path) -> None:
    """Require docstrings and strict typing for source contracts."""
    config = _project_configuration(repository_root)["tool"]
    assert "D" in config["ruff"]["lint"]["select"]
    assert config["mypy"]["strict"] is True
    assert config["mypy"]["packages"] == ["openardp"]


def test_pre_commit_runs_the_authoritative_gates(repository_root: Path) -> None:
    """Keep commit-time checks aligned with the locked local commands."""
    content = (repository_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    entries = (
        "uv run --locked ruff check .",
        "uv run --locked ruff format --check .",
        "uv run --locked mypy src",
        "uv run --locked pytest",
    )
    for entry in entries:
        assert content.count(f"entry: {entry}") == 1
    assert content.count("language: unsupported") == len(entries)
    assert content.count("pass_filenames: false") == len(entries)
    assert content.count("always_run: true") == len(entries)


def test_ci_is_cross_platform_and_least_privilege(repository_root: Path) -> None:
    """Require a read-only three-platform workflow without persistent credentials."""
    content = (repository_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pull_request_target" not in content
    assert "pull_request:" in content
    assert "permissions:\n  contents: read" in content
    assert "fail-fast: false" in content
    assert "timeout-minutes:" in content
    assert "os: [ubuntu-latest, macos-latest, windows-latest]" in content
    assert 'python-version: "3.12"' in content
    assert "persist-credentials: false" in content


def test_ci_actions_are_immutable_and_reviewed(repository_root: Path) -> None:
    """Pin every third-party action to its reviewed release commit."""
    content = (repository_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    uses_lines = [line for line in content.splitlines() if "uses:" in line]
    references = {match.groups() for match in ACTION_REFERENCE.finditer(content)}
    assert len(references) == len(uses_lines)
    assert references == EXPECTED_ACTIONS


def test_ci_uses_locked_uncached_authoritative_gates(repository_root: Path) -> None:
    """Prevent CI from mutating dependency state or drifting from local checks."""
    content = (repository_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    required_steps = (
        "enable-cache: false",
        "uv sync --all-extras --locked",
        "uv run --locked pre-commit validate-config",
        "uv run --locked ruff check .",
        "uv run --locked ruff format --check .",
        "uv run --locked mypy src",
        "uv run --locked pytest",
        "uv build",
        "git diff --exit-code",
    )
    for step in required_steps:
        assert step in content
