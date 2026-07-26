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
F005A_FEATURE_SEQUENCE = (
    "005A-strategic-realignment",
    "006-evidence-contract-foundation",
    "007-docling-native-adapter",
    "008-context-compiler-receipts",
    "009-read-only-mcp",
    "010-reconciliation-derivation-dag",
    "011-visual-evidence-escalation",
    "012-local-watcher-and-jobs",
    "013-retention-recovery-migrations",
    "014-export-interchange-experiment",
    "015-benchmark-security-release-gate",
    "016-alternate-parser-conformance-spike",
    "017-microsoft-graph-design-spike",
)
HISTORICAL_FEATURE_PROMPTS = (
    "001-repository-baseline.md",
    "002-domain-models-schemas.md",
    "003-cas-sqlite-catalog.md",
    "004-text-ingestion-slice.md",
    "005-lexical-search.md",
)
F005A_ADRS = (
    "0007-implementation-first.md",
    "0008-preserve-provider-native-representations.md",
    "0009-indexes-are-non-authoritative.md",
    "0010-contracts-before-adapters.md",
)


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
    """Keep the core small and expose rich parsing only through the exact reviewed extra."""
    project = _project_configuration(repository_root)["project"]
    assert project["requires-python"] == ">=3.12,<3.13"
    assert project.get("dependencies", []) == [
        "pydantic>=2.12.5,<2.13",
        "rfc8785>=0.1.4,<0.2",
    ]
    assert project.get("optional-dependencies", {}) == {
        "docling": ["docling==2.114.0"],
    }
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


def test_f005a_constitution_is_ratified_and_canonical(repository_root: Path) -> None:
    """Keep one complete binding constitution after the strategic realignment."""
    constitution = (repository_root / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    source = (repository_root / "spec-kit/CONSTITUTION_SOURCE.md").read_text(encoding="utf-8")

    assert constitution == source
    assert "**Current version:** 2.0.0" in constitution
    assert "**Last amended:** 2026-07-26" in constitution
    required_boundaries = (
        "implementation-first",
        "complete provider-native",
        "second complete provider-neutral document representation",
        "Search indexes",
        "verified",
        "Linux, macOS and Windows",
        "external-use evidence",
    )
    for boundary in required_boundaries:
        assert boundary.casefold() in constitution.casefold()


def test_f005a_adoption_sources_point_to_canonical_governance(
    repository_root: Path,
) -> None:
    """Prevent versioned blueprint sources from becoming parallel authorities."""
    sources = {
        "CONSTITUTION_V3_SOURCE.md": "CONSTITUTION_SOURCE.md",
        "FEATURE_MAP_V3.md": "FEATURE_MAP.md",
        "OPERATING_PROCEDURE_V3.md": "OPERATING_PROCEDURE.md",
    }
    for source_name, canonical_name in sources.items():
        content = (repository_root / "spec-kit" / source_name).read_text(encoding="utf-8")
        assert "adoption source" in content.casefold()
        assert canonical_name in content
        assert "not authoritative" in content.casefold()


def test_f005a_feature_map_and_prompts_have_one_exact_sequence(
    repository_root: Path,
) -> None:
    """Require one dependency-ordered continuation map and prompt inventory."""
    feature_map = (repository_root / "spec-kit/FEATURE_MAP.md").read_text(encoding="utf-8")
    positions = [feature_map.index(feature) for feature in F005A_FEATURE_SEQUENCE]
    assert positions == sorted(positions)
    assert (
        feature_map.count("A feature begins only after its predecessor converges and merges") == 1
    )

    prompt_directory = repository_root / "spec-kit/feature-prompts"
    actual_prompts = {path.name for path in prompt_directory.glob("*.md")}
    expected_prompts = set(HISTORICAL_FEATURE_PROMPTS) | {
        f"{feature}.md" for feature in F005A_FEATURE_SEQUENCE
    }
    assert actual_prompts == expected_prompts

    for feature in F005A_FEATURE_SEQUENCE:
        prompt = (prompt_directory / f"{feature}.md").read_text(encoding="utf-8")
        assert feature.split("-", maxsplit=1)[0].casefold() in prompt.casefold()


def test_f005a_adrs_preserve_decision_history(repository_root: Path) -> None:
    """Require accepted strategic ADRs and explicit earlier-decision treatment."""
    adr_directory = repository_root / "docs/adr"
    for filename in F005A_ADRS:
        content = (adr_directory / filename).read_text(encoding="utf-8")
        assert "Status: Accepted" in content
        assert "2026-07-26" in content

    parser_adr = (adr_directory / "0001-use-docling-as-default-parser.md").read_text(
        encoding="utf-8"
    )
    package_adr = (adr_directory / "0005-portable-zip-runtime-cas.md").read_text(encoding="utf-8")
    assert "partly superseded" in parser_adr.casefold()
    assert "0008-preserve-provider-native-representations.md" in parser_adr
    assert "Status: Deferred" in package_adr
    assert "014-export-interchange-experiment" in package_adr


def test_f005a_contract_guidance_is_experimental_and_parseable(
    repository_root: Path,
) -> None:
    """Keep F005A examples informative without creating a stable public schema."""
    contracts = (repository_root / "contracts/README.md").read_text(encoding="utf-8")
    conformance = (repository_root / "conformance/README.md").read_text(encoding="utf-8")
    example_path = repository_root / "contracts/example-selection-receipt.json"
    example = json.loads(example_path.read_text(encoding="utf-8"))

    assert "experimental" in contracts.casefold()
    assert "design guidance" in contracts.casefold()
    assert "Feature 006" in contracts
    assert "Feature 016" in conformance
    assert "not a public schema" in contracts.casefold()
    assert isinstance(example, dict)
    assert example
    assert example_path not in set((repository_root / "schemas").glob("*.schema.json"))


def test_f005a_entry_points_use_claims_discipline(repository_root: Path) -> None:
    """Reject stale search status and unqualified standards positioning."""
    entry_paths = (
        repository_root / "README.md",
        repository_root / "START_HERE.md",
        repository_root / "docs/00_EXECUTIVE_BRIEF.md",
        repository_root / "docs/01_PRODUCT_REQUIREMENTS.md",
        repository_root / "docs/08_ROADMAP_AND_GOVERNANCE.md",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in entry_paths)
    lowered = combined.casefold()

    assert "implementation-first" in lowered
    assert "experimental interoperability" in lowered
    assert "lexical search" in lowered
    stale_search = re.compile(r"(?:no|without|does not (?:have|include|provide)) lexical search")
    standards_claim = re.compile(
        r"openardp is (?:an?|the) (?:open |universal |official )?"
        r"(?:document )?(?:standard|protocol)"
    )
    assert stale_search.search(lowered) is None
    assert standards_claim.search(lowered) is None


def test_f005a_overlay_is_curated_without_platform_metadata(
    repository_root: Path,
) -> None:
    """Exclude the external blueprint package and operating-system metadata."""
    assert not (repository_root / "openardp_codex_blueprint_v3_1").exists()
    excluded = {
        path.relative_to(repository_root).as_posix()
        for path in repository_root.rglob("*")
        if ".git" not in path.parts
        and (path.name == ".DS_Store" or "openardp_codex_blueprint_v3_1" in path.parts)
    }
    assert excluded == set()
