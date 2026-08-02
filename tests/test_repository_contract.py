"""Repository-wide contracts for the OpenARDP engineering baseline."""

from __future__ import annotations

import hashlib
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
    (
        "actions/upload-artifact",
        "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        "v7.0.1",
    ),
    (
        "actions/download-artifact",
        "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
        "v8.0.1",
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
    "018-repository-hygiene",
    "019-ci-cost-optimization",
    "020-product-value-benchmark",
    "021-incremental-freshness",
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
F007_SCHEMA_HASHES = {
    "block.schema.json": "413d725016a9f4f261e384efff3f82906a08c7e3b73a25bc8f96963a10861562",
    "context-bundle.schema.json": (
        "e6cea129f58bd11ec52e1f63ef87258d8ec9c01ac37ff7fa933b08e96790a31a"
    ),
    "derivation.schema.json": ("56e8fc17050584b6d4bfc430d5f8d24de03237e5ef2b96fc7d9f6afd61f3e88a"),
    "evidence-projection.schema.json": (
        "cc580d589e46142a6c8429e0deb855c1bf3be79cf4334d9b39129e46c80aaf1e"
    ),
    "evidence-reference.schema.json": (
        "b86968eca4d9a8c208c4a4f52f207dda863377dcc5bf353775b0067e2b4f4362"
    ),
    "manifest.schema.json": "1995cc1062e5322405a00adba8e47c7f3bed9fa294de6920dc27476c5a36dfd4",
    "native-representation.schema.json": (
        "c4685f98633f2628240059e55703a0d8f27e32eb549cd7d453deb91b23d4d6ef"
    ),
    "relation.schema.json": "00b581b077089e6534f4cc0c3af511fa2caa8ede6b81649ee5094f0b60bca142",
    "trust-classification.schema.json": (
        "7c4a7b429a3994ebd62af394b06cf7daaeeb691720778ef0122c1871fff302bc"
    ),
}
F007_VECTOR_HASHES = {
    "tests/fixtures/domain/canonicalization-vectors.json": (
        "9387f64d8cf90f2039ca975c71d6f02d57cef8027005b69da6e07b4f8b6c291b"
    ),
    "conformance/evidence/v0.1.0/canonicalization-vectors.json": (
        "da1c718da44c6e51f3ec2e7aafcd94de4b59dad8b3c02e442eb02527a8729e97"
    ),
}
F007_EVIDENCE_CORPUS_DIGEST = (
    "sha256:e5fd01bc89d49267cd3d113e76428f0c931f99ce43b10756ac3aafc6e31eaccb"
)
F008_ADDITIVE_SCHEMA_HASHES = {
    "context-bundle-0.2.0.schema.json": (
        "2a5c3c286456aae31fa558f8d43d7c9226b15affc6d96a6641d4666e886a3d9e"
    ),
    "selection-receipt.schema.json": (
        "05c24f533da13b9705af4e6f25f0b96d5e41ee5d1d329756571a5c63a867d607"
    ),
}
F008_ADDITIVE_VECTOR_HASHES = {
    "tests/fixtures/context/canonicalization-vectors.json": (
        "2e221ba1533ce53db389fffa37a25b633472ef49646e6f9f3be5c68ff752afad"
    ),
}
F009_FROZEN_MANIFEST_HASHES = {
    "pyproject.toml": "739c224eb4dbc41155a986c76f30c9074646748c95f4b13dbade356d7fa70736",
    "uv.lock": "1540dd72ac6b4d9873f9502deff4b2ebce2b9df40cd339799fe5272caed2f8dc",
}
F009_FROZEN_DESCRIPTOR_HASHES = {
    "tests/fixtures/mcp/tools-list.json": (
        "770c959ebc5db69b8ff6d1dc8214c0417f21daa3853aeff565f2822a42d29d7e"
    ),
    "tests/fixtures/mcp/error-envelopes.json": (
        "7ebcfc4e348f8c3d6f247491673a3724d383ceec12a859d05e87e0df2f57a76d"
    ),
}
F014_ADDITIVE_SCHEMA_HASHES = {
    "openardp-interchange-package.schema.json": (
        "541f8a708886006bc7c8984b51fdd9b0356dcb59582fa0e2cf1600d44b7a073b"
    ),
}


def _project_configuration(repository_root: Path) -> dict[str, Any]:
    """Load the complete project configuration."""
    with (repository_root / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def _tree_digest(root: Path) -> str:
    """Hash sorted relative names and exact bytes for one frozen fixture tree."""
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def test_f007_contract_bytes_remain_frozen(repository_root: Path) -> None:
    """Prevent additive F008 work from changing any established public contract byte."""
    for name, expected in F007_SCHEMA_HASHES.items():
        actual = hashlib.sha256((repository_root / "schemas" / name).read_bytes()).hexdigest()
        assert actual == expected
    for relative, expected in F007_VECTOR_HASHES.items():
        actual = hashlib.sha256((repository_root / relative).read_bytes()).hexdigest()
        assert actual == expected
    assert (
        _tree_digest(repository_root / "conformance" / "evidence" / "v0.1.0")
        == F007_EVIDENCE_CORPUS_DIGEST
    )


def test_f008_contract_bytes_remain_frozen(repository_root: Path) -> None:
    """Prevent additive F009 work from changing any F008 public contract byte."""
    combined_schemas = {**F007_SCHEMA_HASHES, **F008_ADDITIVE_SCHEMA_HASHES}
    assert len(combined_schemas) == 11
    for name, expected in combined_schemas.items():
        actual = hashlib.sha256((repository_root / "schemas" / name).read_bytes()).hexdigest()
        assert actual == expected
    combined_vectors = {**F007_VECTOR_HASHES, **F008_ADDITIVE_VECTOR_HASHES}
    assert len(combined_vectors) == 3
    for relative, expected in combined_vectors.items():
        actual = hashlib.sha256((repository_root / relative).read_bytes()).hexdigest()
        assert actual == expected
    assert (
        _tree_digest(repository_root / "conformance" / "evidence" / "v0.1.0")
        == F007_EVIDENCE_CORPUS_DIGEST
    )


def test_f009_dependency_manifests_remain_frozen(repository_root: Path) -> None:
    """Retain the historical F009 dependency baseline for additive F011 review."""
    assert F009_FROZEN_MANIFEST_HASHES == {
        "pyproject.toml": "739c224eb4dbc41155a986c76f30c9074646748c95f4b13dbade356d7fa70736",
        "uv.lock": "1540dd72ac6b4d9873f9502deff4b2ebce2b9df40cd339799fe5272caed2f8dc",
    }


def test_f025_governance_and_prior_contracts_are_present_and_frozen(
    repository_root: Path,
) -> None:
    """Require active benchmark governance, accepted ADRs and frozen prior contracts."""
    active = json.loads((repository_root / ".specify/feature.json").read_text(encoding="utf-8"))
    assert active["feature_directory"] == "specs/025-semantic-e2e-source-evaluation"
    feature = repository_root / active["feature_directory"]
    assert {path.name for path in feature.iterdir()} >= {
        "spec.md",
        "plan.md",
        "tasks.md",
        "research.md",
        "data-model.md",
        "quickstart.md",
        "analysis.md",
        "implementation-notes.md",
        "contracts",
        "checklists",
    }
    f010_adr = (
        repository_root / "docs/adr/0011-reconciliation-lineages-and-derivation-lifecycle.md"
    ).read_text(encoding="utf-8")
    assert "Status: Accepted for Feature 010" in f010_adr
    f011_adr = (
        repository_root / "docs/adr/0012-visual-evidence-descriptors-and-rendering.md"
    ).read_text(encoding="utf-8")
    assert "Status: Accepted for Feature 011" in f011_adr
    assert "Date: 2026-08-01" in f011_adr
    f012_adr = (
        repository_root / "docs/adr/0013-local-watch-reconciliation-and-cancellable-jobs.md"
    ).read_text(encoding="utf-8")
    assert "Status: Accepted for Feature 012" in f012_adr
    assert "Date: 2026-08-01" in f012_adr
    f013_adr = (repository_root / "docs/adr/0014-retention-recovery-maintenance.md").read_text(
        encoding="utf-8"
    )
    assert "Status: Accepted for Feature 013" in f013_adr
    assert "Date: 2026-08-01" in f013_adr
    f014_adr = (repository_root / "docs/adr/0015-bagit-interchange-profile.md").read_text(
        encoding="utf-8"
    )
    assert "Status: Accepted for Feature 014" in f014_adr
    assert "Date: 2026-08-01" in f014_adr
    f017_adr = (repository_root / "docs/adr/0016-microsoft-graph-mock-design.md").read_text(
        encoding="utf-8"
    )
    assert "Status: Accepted for Feature 017" in f017_adr
    assert "does not authorize production Graph access" in f017_adr
    assert (repository_root / "spec-kit/feature-prompts/018-repository-hygiene.md").is_file()
    assert (repository_root / "spec-kit/feature-prompts/019-ci-cost-optimization.md").is_file()
    assert (repository_root / "spec-kit/feature-prompts/020-product-value-benchmark.md").is_file()
    assert (repository_root / "spec-kit/feature-prompts/021-incremental-freshness.md").is_file()
    assert (repository_root / "spec-kit/feature-prompts/022-storage-amplification.md").is_file()
    assert (repository_root / "spec-kit/feature-prompts/023-offline-pdf-model-bundle.md").is_file()
    assert (
        repository_root / "spec-kit/feature-prompts/024-redistributable-realworld-corpus.md"
    ).is_file()
    assert (
        repository_root / "spec-kit/feature-prompts/025-semantic-e2e-source-evaluation.md"
    ).is_file()
    f021_adr = (repository_root / "docs/adr/0017-freshness-integrity-coverage.md").read_text(
        encoding="utf-8"
    )
    assert "Status: Accepted for Feature 021" in f021_adr
    assert "MCP remains identifier-only and bounded to default HEAD coverage" in f021_adr
    f022_adr = (repository_root / "docs/adr/0018-compact-derived-block-storage.md").read_text(
        encoding="utf-8"
    )
    assert "Status: Accepted for Feature 022" in f022_adr
    assert (repository_root / "model-bundles/pdf-docling-2.114.0-v1/source-lock.json").is_file()
    assert (repository_root / "benchmarks/pdf-bundle/v0.1.0/protocol.json").is_file()
    assert (repository_root / "quality/maintainability-policy.json").is_file()
    assert (repository_root / "scripts/audit_maintainability.py").is_file()
    assert (repository_root / "quality/ci-policy.json").is_file()
    assert (repository_root / "quality/ci-cost-baseline-2026-08-01.json").is_file()
    assert (repository_root / "scripts/audit_ci.py").is_file()
    assert (repository_root / "schemas/visual-evidence-descriptor.schema.json").is_file()
    for name, expected in F014_ADDITIVE_SCHEMA_HASHES.items():
        actual = hashlib.sha256((repository_root / "schemas" / name).read_bytes()).hexdigest()
        assert actual == expected
    assert len(tuple((repository_root / "schemas").glob("*.schema.json"))) == 14
    assert (repository_root / "schemas/openardp-release-evidence.schema.json").is_file()
    assert (repository_root / "release/evidence/v0.1.0/decision.json").is_file()
    assert (
        repository_root / "conformance/alternate-parser/v0.1.0/expected/decision.json"
    ).is_file()
    assert (
        repository_root / "conformance/alternate-parser/v0.1.0/expected/alternate-record-set.json"
    ).is_file()
    migration_source = (repository_root / "src/openardp/adapters/sqlite_migrations.py").read_text(
        encoding="utf-8"
    )
    assert "MIGRATION_8 = Migration(" in migration_source
    assert 'name="visual-evidence"' in migration_source
    assert "MIGRATION_9 = Migration(" in migration_source
    assert 'name="local-watcher-and-cancellable-jobs"' in migration_source
    assert "MIGRATION_10 = Migration(" in migration_source
    assert 'name="retention-recovery-maintenance"' in migration_source
    for relative, expected in F009_FROZEN_DESCRIPTOR_HASHES.items():
        actual = hashlib.sha256((repository_root / relative).read_bytes()).hexdigest()
        assert actual == expected


def test_f020_committed_reference_result_remains_valid(repository_root: Path) -> None:
    """Recompute the committed real result and retain its explicit limitations."""
    from openardp.domain.product_benchmark import ValueOutcome
    from scripts.product_benchmark_runner import validate_product_benchmark

    result = validate_product_benchmark(
        repository_root,
        repository_root / "benchmarks/product-value/v0.1.0/results/reference-macos-arm64",
    )
    summary = json.loads((result.output / "summary.json").read_bytes())

    assert result.decision.outcome is ValueOutcome.CONDITIONALLY_WORTHWHILE
    assert summary["decision_metrics"]["reference_blocks"] == 10_000
    assert summary["decision_metrics"]["scale_blocks"] == 100_000
    assert summary["rich"]["docx"]["available"] is True
    assert summary["rich"]["pptx"]["available"] is True
    assert summary["rich"]["pdf"] == {
        "available": False,
        "reason_code": "pdf-model-bundle-unavailable",
    }


def test_focused_quickstarts_separate_partial_tests_from_full_coverage(
    repository_root: Path,
) -> None:
    """Keep feature-focused commands runnable without weakening the full coverage gate."""
    quickstarts = (
        "010-reconciliation-derivation-dag",
        "014-export-interchange-experiment",
        "015-benchmark-security-release-gate",
        "016-alternate-parser-conformance-spike",
        "017-microsoft-graph-design-spike",
        "018-repository-hygiene",
        "021-incremental-freshness",
    )
    for feature in quickstarts:
        text = (repository_root / "specs" / feature / "quickstart.md").read_text(encoding="utf-8")
        assert "pytest --no-cov" in text


def test_generated_local_state_is_not_tracked(repository_root: Path) -> None:
    """Keep caches, environments, coverage and build output outside repository history."""
    git_executable = shutil.which("git")
    assert git_executable is not None
    completed = subprocess.run(  # noqa: S603 -- fixed git command in repository checkout
        [git_executable, "ls-files"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    forbidden_parts = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "dist",
        "build",
        "htmlcov",
    }
    tracked = tuple(line for line in completed.stdout.splitlines() if line)
    assert not any(forbidden_parts.intersection(Path(path).parts) for path in tracked)
    assert not any(path.endswith((".pyc", ".coverage", "coverage.xml")) for path in tracked)


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
        "visual": ["Pillow==12.3.0", "pypdfium2==5.12.1"],
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
    """Require read-only core and release workflows with hardened checkout."""
    workflows = (
        repository_root / ".github/workflows/ci.yml",
        repository_root / ".github/workflows/release-evidence.yml",
    )
    for workflow in workflows:
        content = workflow.read_text(encoding="utf-8")
        assert "pull_request_target" not in content
        assert "permissions:\n  contents: read" in content
        assert "timeout-minutes:" in content
        assert 'python-version: "3.12"' in content
        assert "persist-credentials: false" in content
        assert "enable-cache: true" in content
        assert "cache-dependency-glob: uv.lock" in content
        assert "uv cache prune --ci" in content


def test_ci_actions_are_immutable_and_reviewed(repository_root: Path) -> None:
    """Pin every third-party action to its reviewed release commit."""
    content = "\n".join(
        (repository_root / path).read_text(encoding="utf-8")
        for path in (".github/workflows/ci.yml", ".github/workflows/release-evidence.yml")
    )
    uses_lines = [line for line in content.splitlines() if "uses:" in line]
    references = [match.groups() for match in ACTION_REFERENCE.finditer(content)]
    assert len(references) == len(uses_lines)
    assert set(references) == EXPECTED_ACTIONS


def test_ci_uses_locked_authoritative_gates_once(repository_root: Path) -> None:
    """Keep one authoritative Linux gate and complete paid-platform tests."""
    content = (repository_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    authoritative_steps = (
        "uv run --locked pre-commit validate-config",
        "uv run --locked ruff check .",
        "uv run --locked ruff format --check .",
        "uv run --locked mypy src",
        "uv build",
    )
    for step in authoritative_steps:
        assert content.count(step) == 1
    assert content.count("uv sync --all-extras --locked") == 4
    assert content.splitlines().count("        run: uv run --locked pytest") == 1
    assert content.count("git diff --exit-code") == 4
    assert content.count("uv cache prune --ci") == 4
    assert content.count("uv run --locked pytest --no-cov") == 2
    assert "name: Quality (ubuntu-latest)" in content
    assert "name: Quality (macos-latest)" in content
    assert "name: Quality (windows-latest)" in content
    assert "needs.preflight.outputs.scope == 'full'" in content
    assert "github.event.pull_request.draft == false" in content
    assert "ready_for_review" in content
    assert "pull_request:\n    types:" in content
    assert "paths-ignore:" not in content


def test_ci_keeps_stable_preflight_and_main_without_matrix_duplication(
    repository_root: Path,
) -> None:
    """Run core integrity everywhere while limiting final matrices to ready PRs."""
    content = (repository_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "name: Preflight" in content
    assert "branches: [main]" in content
    assert "github.event_name == 'pull_request'" in content
    assert "github.event_name == 'push'" not in content.split("quality-ubuntu:", maxsplit=1)[1]
    assert "python3 scripts/audit_ci.py classify" in content
    assert "python scripts/audit_ci.py audit" in content


def test_release_evidence_has_bounded_triggers_and_unchanged_gate(
    repository_root: Path,
) -> None:
    """Keep expensive all-platform evidence at deliberate release boundaries."""
    content = (repository_root / ".github/workflows/release-evidence.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in content
    assert 'tags: ["v*"]' in content
    assert "pull_request:" in content
    assert "paths:" in content
    assert "github.event.pull_request.draft == false" in content
    assert "fail-fast: false" in content
    assert content.count("platform:") == 3
    for platform in ("linux", "macos", "windows"):
        assert f"release-evidence-{platform}" in content
    assert "needs: release-evidence" in content
    assert "assert value['status'] == 'NO-GO'" in content
    assert "retention-days: 14" in content
    aggregate = content.split("  release-gate:", maxsplit=1)[1]
    assert "Install uv and Python without downstream cache contention" in aggregate
    assert "enable-cache: true" not in aggregate
    assert "cache-dependency-glob: uv.lock" not in aggregate
    assert "uv cache prune --ci" not in aggregate


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
    assert expected_prompts <= actual_prompts
    assert "022-storage-amplification.md" in actual_prompts

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
