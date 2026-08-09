"""Validate OpenARDP repository documentation and governance without network access."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __package__:
    from scripts.audit_ci import (
        CIAuditError,
    )
    from scripts.audit_ci import (
        audit_repository as audit_ci,
    )
    from scripts.audit_ci import (
        load_policy as load_ci_policy,
    )
    from scripts.audit_maintainability import (
        PolicyError,
    )
    from scripts.audit_maintainability import (
        audit_repository as audit_maintainability,
    )
    from scripts.audit_maintainability import (
        load_policy as load_maintainability_policy,
    )
    from scripts.audit_repository_hygiene import (
        AuditError as RepositoryHygieneError,
    )
    from scripts.audit_repository_hygiene import (
        audit_repository as audit_repository_hygiene,
    )
else:
    from audit_ci import CIAuditError
    from audit_ci import audit_repository as audit_ci
    from audit_ci import load_policy as load_ci_policy
    from audit_maintainability import (
        PolicyError,
    )
    from audit_maintainability import (
        audit_repository as audit_maintainability,
    )
    from audit_maintainability import (
        load_policy as load_maintainability_policy,
    )
    from audit_repository_hygiene import AuditError as RepositoryHygieneError
    from audit_repository_hygiene import audit_repository as audit_repository_hygiene

_EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "htmlcov",
    "venv",
}
_EXTERNAL_SCHEMES = {"http", "https", "mailto"}
_FORBIDDEN_SCHEMES = {"file", "sandbox"}
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]*)\)")
_REFERENCE_DEFINITION = re.compile(r"^[ \t]{0,3}\[([^\]\n]+)\]:[ \t]*(.+)$", re.MULTILINE)
_REFERENCE_USE = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
_ATX_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)\s*$")
_SETEXT_HEADING = re.compile(r"^[ \t]*(?:=+|-+)[ \t]*$")
_REQUIRED_GOVERNANCE_FILES = (
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
_CANONICAL_COMMANDS = (
    "uv sync --all-extras --locked",
    "uv run ruff check .",
    "uv run ruff format --check .",
    "uv run mypy src",
    "uv run pytest",
)
_FEATURE_DIRECTORY = re.compile(r"^\d{3}[A-Z]?-[a-z0-9]+(?:-[a-z0-9]+)*$")
_DURABLE_FEATURE_FILES = ("spec.md", "implementation-notes.md")
_TRANSIENT_FEATURE_FILES = {
    "analysis.md",
    "data-model.md",
    "plan.md",
    "quickstart.md",
    "research.md",
    "tasks.md",
}
_F005A_OVERLAY_DESTINATIONS = (
    "codex/MASTER_SESSION_PROMPT.md",
    "conformance/README.md",
    "contracts/README.md",
    "contracts/example-selection-receipt.json",
    "docs/00_REVISED_EXECUTIVE_BRIEF.md",
    "docs/01_VISION_AND_POSITIONING.md",
    "docs/02_NORMATIVE_SCOPE_CANDIDATE.md",
    "docs/03_NON_GOALS.md",
    "docs/04_PRIOR_ART_AND_DD.md",
    "docs/05_TARGET_ARCHITECTURE.md",
    "docs/06_SECURITY_MODEL_V2.md",
    "docs/07_BENCHMARK_AND_EVIDENCE_PLAN.md",
    "docs/08_RELEASE_AND_ADOPTION_STRATEGY.md",
    "docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md",
    "docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md",
    "docs/adr/0007-implementation-first.md",
    "docs/adr/0008-preserve-provider-native-representations.md",
    "docs/adr/0009-indexes-are-non-authoritative.md",
    "docs/adr/0010-contracts-before-adapters.md",
    "spec-kit/CONSTITUTION_V3_SOURCE.md",
    "spec-kit/FEATURE_MAP_V3.md",
    "spec-kit/OPERATING_PROCEDURE_V3.md",
)
_F005A_ADOPTION_SOURCES = {
    "spec-kit/CONSTITUTION_V3_SOURCE.md": "CONSTITUTION_SOURCE.md",
    "spec-kit/FEATURE_MAP_V3.md": "FEATURE_MAP.md",
    "spec-kit/OPERATING_PROCEDURE_V3.md": "OPERATING_PROCEDURE.md",
}
_F015_REQUIRED_FILES = (
    "benchmarks/release/v0.1.0/claim-policy.json",
    "benchmarks/release/v0.1.0/corpus-manifest.json",
    "benchmarks/release/v0.1.0/dependency-review.json",
    "benchmarks/release/v0.1.0/gate-policy.json",
    "benchmarks/release/v0.1.0/judgments.json",
    "benchmarks/release/v0.1.0/protocol.json",
    "benchmarks/release/v0.1.0/security-controls.json",
    "benchmarks/release/v0.1.0/source-tree-policy.json",
    "release/evidence/v0.1.0/checksums.json",
    "release/evidence/v0.1.0/claim-map.json",
    "release/evidence/v0.1.0/decision.json",
    "release/evidence/v0.1.0/manifest.json",
    "release/evidence/v0.1.0/report.md",
    "release/evidence/v0.1.0/sbom.cdx.json",
    "schemas/openardp-release-evidence.schema.json",
    "scripts/generate_release_corpus.py",
    "scripts/generate_release_evidence.py",
    "scripts/generate_release_sbom.py",
    "scripts/validate_release_evidence.py",
)
_F016_REQUIRED_FILES = (
    "conformance/alternate-parser/v0.1.0/expected/alternate-record-set.json",
    "conformance/alternate-parser/v0.1.0/expected/decision.json",
    "conformance/alternate-parser/v0.1.0/manifest.json",
    "conformance/alternate-parser/v0.1.0/sources/sample.csv",
    "conformance/alternate-parser/v0.1.0/sources/sample.txt",
    "scripts/alternate_evidence_process.py",
    "scripts/validate_alternate_conformance.py",
)
_F017_REQUIRED_FILES = (
    "docs/16_MICROSOFT_GRAPH_DESIGN_SPIKE.md",
    "docs/adr/0016-microsoft-graph-mock-design.md",
    "specs/017-microsoft-graph-design-spike/contracts/connector-contract.md",
    "specs/017-microsoft-graph-design-spike/contracts/data-protection-assessment.md",
    "specs/017-microsoft-graph-design-spike/contracts/permission-matrix.md",
    "specs/017-microsoft-graph-design-spike/contracts/threat-model.md",
    "specs/017-microsoft-graph-design-spike/implementation-notes.md",
    "specs/017-microsoft-graph-design-spike/spec.md",
    "src/openardp/adapters/mock_graph.py",
    "src/openardp/domain/graph.py",
    "src/openardp/ports/graph.py",
    "src/openardp/services/graph_sync.py",
    "tests/contract/test_graph_ports.py",
    "tests/domain/test_graph.py",
    "tests/integration/test_graph_sync.py",
    "tests/security/test_graph_boundaries.py",
)
_F019_REQUIRED_FILES = (
    ".github/workflows/release-evidence.yml",
    "docs/18_CI_COST_AND_QUALITY.md",
    "quality/ci-cost-baseline-2026-08-01.json",
    "quality/ci-policy.json",
    "scripts/audit_ci.py",
    "specs/019-ci-cost-optimization/contracts/ci-execution-policy.md",
    "specs/019-ci-cost-optimization/implementation-notes.md",
    "specs/019-ci-cost-optimization/spec.md",
    "tests/unit/test_ci_audit.py",
)
_F020_REQUIRED_FILES = (
    "benchmarks/product-value/v0.1.0/corpus-spec.json",
    "benchmarks/product-value/v0.1.0/judgments.json",
    "benchmarks/product-value/v0.1.0/protocol.json",
    "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/decision.json",
    "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/observations.json",
    "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/report.md",
    "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/run-manifest.json",
    "benchmarks/product-value/v0.1.0/results/reference-macos-arm64/summary.json",
    "benchmarks/product-value/v0.1.0/value-policy.json",
    "docs/19_PRODUCT_VALUE_BENCHMARK.md",
    "scripts/generate_product_benchmark.py",
    "scripts/product_benchmark_evaluation.py",
    "scripts/product_benchmark_runner.py",
    "scripts/run_product_benchmark.py",
    "scripts/validate_product_benchmark.py",
    "specs/020-product-value-benchmark/contracts/maintainer-benchmark.md",
    "specs/020-product-value-benchmark/implementation-notes.md",
    "specs/020-product-value-benchmark/spec.md",
    "tests/integration/test_product_benchmark.py",
    "tests/unit/test_product_benchmark.py",
)
_F024_REQUIRED_FILES = (
    "benchmarks/realworld-corpus/v0.1.0/README.md",
    "benchmarks/realworld-corpus/v0.1.0/baseline.json",
    "benchmarks/realworld-corpus/v0.1.0/protocol.json",
    "benchmarks/realworld-corpus/v0.1.0/results/reference-macos-arm64/decision.json",
    "benchmarks/realworld-corpus/v0.1.0/results/reference-macos-arm64/observations.json",
    "benchmarks/realworld-corpus/v0.1.0/results/reference-macos-arm64/report.md",
    "benchmarks/realworld-corpus/v0.1.0/results/reference-macos-arm64/run-manifest.json",
    "benchmarks/realworld-corpus/v0.1.0/results/reference-macos-arm64/summary.json",
    "corpora/realworld/v0.1.0/README.md",
    "corpora/realworld/v0.1.0/THIRD_PARTY_NOTICES.md",
    "corpora/realworld/v0.1.0/corpus-lock.json",
    "corpora/realworld/v0.1.0/corpus-lock.schema.json",
    "corpora/realworld/v0.1.0/evidence/cisa-kev-revision.json",
    "corpora/realworld/v0.1.0/evidence/nasa-ntrs-20210012886.json",
    "corpora/realworld/v0.1.0/evidence/nasa-ntrs-20210014231.json",
    "corpora/realworld/v0.1.0/evidence/nasa-ntrs-20210025005.json",
    "corpora/realworld/v0.1.0/sources/cisa-kev-license.txt",
    "corpora/realworld/v0.1.0/sources/cisa-kev-readme.md",
    "corpora/realworld/v0.1.0/sources/cisa-known-exploited-vulnerabilities.csv",
    "corpora/realworld/v0.1.0/sources/nasa-ai-strategic-planning-workshop.docx",
    "corpora/realworld/v0.1.0/sources/nasa-ethical-ai-framework.pdf",
    "corpora/realworld/v0.1.0/sources/nasa-open-science-and-ai.pptx",
    "docs/23_REALWORLD_CORPUS.md",
    "scripts/fetch_realworld_corpus.py",
    "scripts/realworld_corpus.py",
    "scripts/realworld_corpus_benchmark.py",
    "scripts/realworld_corpus_benchmark_evaluation.py",
    "scripts/realworld_csv_probe.py",
    "scripts/run_realworld_corpus_benchmark.py",
    "scripts/validate_realworld_corpus.py",
    "scripts/validate_realworld_corpus_benchmark.py",
    "specs/024-redistributable-realworld-corpus/implementation-notes.md",
    "specs/024-redistributable-realworld-corpus/spec.md",
    "tests/integration/test_realworld_corpus.py",
    "tests/integration/test_realworld_corpus_benchmark.py",
    "tests/integration/test_realworld_corpus_reference.py",
    "tests/security/test_realworld_corpus_boundaries.py",
    "tests/test_realworld_corpus_drift.py",
    "tests/unit/test_realworld_corpus.py",
    "tests/unit/test_realworld_corpus_benchmark.py",
)
_F025_REQUIRED_FILES = (
    "benchmarks/semantic-e2e/v0.1.0/README.md",
    "benchmarks/semantic-e2e/v0.1.0/protocol.json",
    "benchmarks/semantic-e2e/v0.1.0/questions.json",
    "benchmarks/semantic-e2e/v0.1.0/questions.schema.json",
    "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/decision.json",
    "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/observations.json",
    "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/report.md",
    "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/run-manifest.json",
    "benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/summary.json",
    "docs/24_SEMANTIC_E2E_EVALUATION.md",
    "scripts/run_semantic_e2e_benchmark.py",
    "scripts/semantic_e2e_benchmark.py",
    "scripts/semantic_e2e_evaluation.py",
    "scripts/validate_semantic_e2e_benchmark.py",
    "specs/025-semantic-e2e-source-evaluation/implementation-notes.md",
    "specs/025-semantic-e2e-source-evaluation/spec.md",
    "tests/integration/test_semantic_e2e_benchmark.py",
    "tests/integration/test_semantic_e2e_reference.py",
    "tests/security/test_semantic_e2e_boundaries.py",
    "tests/test_semantic_e2e_drift.py",
    "tests/unit/test_semantic_e2e_benchmark.py",
)
_F026_REQUIRED_FILES = (
    "benchmarks/relevance/v0.1.0/results/reference-macos-arm64/report.md",
    "benchmarks/relevance/v0.1.0/results/reference-macos-arm64/result.json",
    "docs/25_RELEVANCE_AND_ABSTENTION.md",
    "scripts/run_relevance_benchmark.py",
    "scripts/validate_relevance_benchmark.py",
    "specs/026-relevance-abstention/contracts/context-relevance.md",
    "specs/026-relevance-abstention/implementation-notes.md",
    "specs/026-relevance-abstention/spec.md",
    "src/openardp/adapters/context_relevance.py",
    "src/openardp/domain/context_relevance.py",
    "src/openardp/interfaces/context_composition.py",
    "src/openardp/services/context_relevance.py",
    "tests/integration/test_context_relevance.py",
    "tests/integration/test_context_relevance_reference.py",
    "tests/security/test_context_relevance_boundaries.py",
    "tests/unit/test_context_relevance.py",
    "tests/unit/test_relevance_benchmark.py",
)

_F027_REQUIRED_FILES = (
    "benchmarks/ranking/v0.1.0/results/reference-macos-arm64/report.md",
    "benchmarks/ranking/v0.1.0/results/reference-macos-arm64/result.json",
    "docs/26_LEXICAL_RANKING_AND_DIVERSITY.md",
    "scripts/run_ranking_benchmark.py",
    "scripts/validate_ranking_benchmark.py",
    "specs/027-lexical-ranking-diversity/contracts/lexical-allocation.md",
    "specs/027-lexical-ranking-diversity/implementation-notes.md",
    "specs/027-lexical-ranking-diversity/spec.md",
    "src/openardp/domain/context_ranking.py",
    "src/openardp/services/context_ranking.py",
    "tests/domain/test_context_ranking.py",
    "tests/integration/test_context_ranking.py",
    "tests/security/test_context_ranking_boundaries.py",
    "tests/unit/test_context_ranking.py",
    "tests/unit/test_ranking_benchmark.py",
)

_F028_REQUIRED_FILES = (
    "benchmarks/csv-ingestion/v0.1.0/README.md",
    "benchmarks/csv-ingestion/v0.1.0/results/reference-macos-arm64/report.md",
    "benchmarks/csv-ingestion/v0.1.0/results/reference-macos-arm64/result.json",
    "docs/27_STABLE_CSV_INGESTION.md",
    "scripts/run_csv_ingestion_benchmark.py",
    "scripts/validate_csv_ingestion_benchmark.py",
    "specs/028-csv-ingestion/contracts/README.md",
    "specs/028-csv-ingestion/implementation-notes.md",
    "specs/028-csv-ingestion/spec.md",
    "src/openardp/adapters/csv_parser.py",
    "src/openardp/interfaces/ingestion_composition.py",
    "tests/integration/test_csv_ingestion.py",
    "tests/security/test_csv_boundaries.py",
    "tests/unit/test_csv_ingestion_benchmark.py",
    "tests/unit/test_csv_parser.py",
)

_F029_REQUIRED_FILES = (
    "benchmarks/provider-retrieval/v0.1.0/protocol.json",
    "benchmarks/provider-retrieval/v0.1.0/results/reference-macos-arm64/decision.json",
    "benchmarks/provider-retrieval/v0.2.0/protocol.json",
    "benchmarks/provider-retrieval/v0.2.0/results/reference-macos-arm64/decision.json",
    "benchmarks/provider-retrieval/v0.3.0/protocol.json",
    "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64/decision.json",
    "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64/observations.json",
    "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64/report.md",
    "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64/run-manifest.json",
    "benchmarks/provider-retrieval/v0.3.0/results/reference-macos-arm64/summary.json",
    "docs/28_PROVIDER_NEUTRAL_MULTILINGUAL_RETRIEVAL.md",
    "docs/adr/0019-optional-semantic-retrieval.md",
    "model-bundles/multilingual-e5-small-v1/README.md",
    "model-bundles/multilingual-e5-small-v1/THIRD_PARTY_NOTICES.md",
    "model-bundles/multilingual-e5-small-v1/licenses/MIT.txt",
    "model-bundles/multilingual-e5-small-v1/manifest.json",
    "model-bundles/multilingual-e5-small-v1/source-lock.json",
    "scripts/provider_retrieval_benchmark.py",
    "scripts/provision_embedding_bundle.py",
    "scripts/run_provider_retrieval_benchmark.py",
    "scripts/validate_provider_retrieval_benchmark.py",
    "scripts/verify_embedding_bundle.py",
    "specs/029-provider-neutral-multilingual-retrieval/contracts/README.md",
    "specs/029-provider-neutral-multilingual-retrieval/implementation-notes.md",
    "specs/029-provider-neutral-multilingual-retrieval/spec.md",
    "src/openardp/adapters/e5_semantic.py",
    "src/openardp/adapters/embedding_bundle.py",
    "src/openardp/adapters/embedding_bundle_provisioning.py",
    "src/openardp/adapters/semantic_candidates.py",
    "src/openardp/domain/semantic_retrieval.py",
    "src/openardp/ports/semantic_retrieval.py",
    "src/openardp/services/semantic_retrieval.py",
    "tests/integration/test_e5_semantic_provider.py",
    "tests/integration/test_provider_retrieval_reference.py",
    "tests/integration/test_semantic_candidates.py",
    "tests/security/test_semantic_retrieval_boundaries.py",
    "tests/unit/test_embedding_bundle.py",
    "tests/unit/test_provider_retrieval_benchmark.py",
    "tests/unit/test_semantic_retrieval.py",
)

_F031_REQUIRED_FILES = (
    "docs/17_CODEBASE_HYGIENE.md",
    "scripts/audit_repository_hygiene.py",
    "specs/031-repository-hygiene/contracts/repository-hygiene-audit.md",
    "specs/031-repository-hygiene/implementation-notes.md",
    "specs/031-repository-hygiene/spec.md",
    "src/openardp/interfaces/cli_arguments.py",
    "src/openardp/interfaces/cli_output.py",
    "tests/unit/test_repository_hygiene.py",
)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One deterministic repository validation finding."""

    path: Path
    line: int
    code: str
    target: str
    message: str

    def render(self, root: Path) -> str:
        """Render the finding relative to the repository root."""
        try:
            display_path = self.path.relative_to(root).as_posix()
        except ValueError:
            display_path = self.path.as_posix()
        return f"{display_path}:{self.line}: {self.code}: {self.target}: {self.message}"


def _line_number(text: str, offset: int) -> int:
    """Return the one-based line number for a character offset."""
    return text.count("\n", 0, offset) + 1


def _blank_preserving_newlines(text: str) -> str:
    """Replace content with spaces while preserving line structure."""
    return "".join("\n" if character == "\n" else " " for character in text)


def _mask_inline_code(line: str) -> str:
    """Mask paired inline-code spans without changing string offsets."""
    characters = list(line)
    index = 0
    while index < len(line):
        if line[index] != "`":
            index += 1
            continue
        end_of_run = index
        while end_of_run < len(line) and line[end_of_run] == "`":
            end_of_run += 1
        marker = line[index:end_of_run]
        closing = line.find(marker, end_of_run)
        if closing < 0:
            index = end_of_run
            continue
        for position in range(index, closing + len(marker)):
            if characters[position] != "\n":
                characters[position] = " "
        index = closing + len(marker)
    return "".join(characters)


def _mask_code(text: str) -> str:
    """Mask fenced and inline code while preserving lines and offsets."""
    result: list[str] = []
    fence_character = ""
    fence_length = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        fence = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_character:
            result.append(_blank_preserving_newlines(line))
            if (
                fence
                and fence.group(1)[0] == fence_character
                and len(fence.group(1)) >= fence_length
            ):
                fence_character = ""
                fence_length = 0
            continue
        if fence:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
            result.append(_blank_preserving_newlines(line))
            continue
        result.append(_mask_inline_code(line))
    return "".join(result)


def _extract_destination(raw_destination: str) -> str:
    """Extract a Markdown destination while ignoring an optional title."""
    stripped = raw_destination.strip()
    if not stripped:
        return ""
    if stripped.startswith("<"):
        closing = stripped.find(">", 1)
        return stripped[1:closing] if closing >= 0 else stripped[1:]
    return stripped.split(maxsplit=1)[0]


def _normalize_reference(reference: str) -> str:
    """Normalize a Markdown reference label."""
    return " ".join(reference.casefold().split())


def _case_status(root: Path, candidate: Path) -> str:
    """Return exact, mismatch or missing for a path independent of host case rules."""
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return "missing"
    current = root
    mismatch = False
    for part in relative.parts:
        try:
            entries = {entry.name: entry for entry in current.iterdir()}
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return "missing"
        if part in entries:
            current = entries[part]
            continue
        matches = [entry for name, entry in entries.items() if name.casefold() == part.casefold()]
        if not matches:
            return "missing"
        mismatch = True
        current = sorted(matches, key=lambda entry: entry.name)[0]
    return "mismatch" if mismatch else "exact"


def _heading_slug(heading: str) -> str:
    """Create a deterministic GitHub-style Markdown heading slug."""
    value = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", heading)
    value = re.sub(r"<[^>]+>", "", value)
    value = unicodedata.normalize("NFC", value).strip().casefold()
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    return re.sub(r"\s", "-", value)


def _markdown_anchors(path: Path) -> set[str]:
    """Return unique heading anchors, including duplicate suffixes."""
    masked = _mask_code(path.read_text(encoding="utf-8"))
    lines = masked.splitlines()
    headings: list[str] = []
    for index, line in enumerate(lines):
        atx = _ATX_HEADING.match(line)
        if atx:
            headings.append(re.sub(r"[ \t]+#+[ \t]*$", "", atx.group(1)).strip())
            continue
        if index + 1 < len(lines) and line.strip() and _SETEXT_HEADING.match(lines[index + 1]):
            headings.append(line.strip())
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for heading in headings:
        base = _heading_slug(heading)
        count = counts.get(base, 0)
        anchor = base if count == 0 else f"{base}-{count}"
        counts[base] = count + 1
        anchors.add(anchor)
    return anchors


def _diagnostic(
    source: Path,
    line: int,
    code: str,
    target: str,
    message: str,
) -> Diagnostic:
    """Create one diagnostic with normalized source metadata."""
    return Diagnostic(path=source, line=line, code=code, target=target, message=message)


def _validate_target(root: Path, source: Path, line: int, target: str) -> Diagnostic | None:
    """Validate one Markdown target without opening external resources."""
    if not target:
        return _diagnostic(source, line, "MD001", target, "link target is empty")
    if _WINDOWS_DRIVE.match(target) or "\\" in target:
        return _diagnostic(source, line, "MD005", target, "local target is not portable")

    parsed = urlsplit(target)
    scheme = parsed.scheme.casefold()
    if scheme in _EXTERNAL_SCHEMES:
        return None
    if scheme in _FORBIDDEN_SCHEMES or scheme:
        return _diagnostic(source, line, "MD003", target, "target scheme is not allowed")
    if parsed.netloc:
        return _diagnostic(source, line, "MD003", target, "scheme-relative target is not allowed")

    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path:
        return _diagnostic(source, line, "MD005", target, "local target is not portable")
    if decoded_path.startswith("/"):
        return _diagnostic(source, line, "MD004", target, "absolute local target is not allowed")
    if not decoded_path and not parsed.fragment:
        return _diagnostic(source, line, "MD001", target, "link target is empty")

    root_absolute = Path(os.path.abspath(root))
    candidate = source if not decoded_path else Path(os.path.abspath(source.parent / decoded_path))
    if not candidate.is_relative_to(root_absolute):
        return _diagnostic(source, line, "MD009", target, "local target escapes repository")

    case_status = _case_status(root_absolute, candidate)
    if case_status == "missing":
        return _diagnostic(source, line, "MD006", target, "local target does not exist")
    if case_status == "mismatch":
        return _diagnostic(source, line, "MD007", target, "local target path case does not match")
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return _diagnostic(source, line, "MD006", target, "local target does not exist")
    if not resolved.is_relative_to(root_absolute.resolve()):
        return _diagnostic(source, line, "MD009", target, "local target escapes repository")

    fragment = unquote(parsed.fragment)
    if (
        fragment
        and candidate.suffix.casefold() == ".md"
        and fragment not in _markdown_anchors(candidate)
    ):
        return _diagnostic(source, line, "MD008", target, "Markdown heading does not exist")
    return None


def _sort_diagnostics(root: Path, diagnostics: Iterable[Diagnostic]) -> list[Diagnostic]:
    """Sort findings by stable repository-relative metadata."""
    return sorted(
        diagnostics,
        key=lambda item: (
            item.path.relative_to(root).as_posix()
            if item.path.is_relative_to(root)
            else item.path.as_posix(),
            item.line,
            item.code,
            item.target,
            item.message,
        ),
    )


def _discover_markdown(root: Path) -> list[Path]:
    """Discover repository Markdown while excluding generated local outputs."""
    return sorted(
        path
        for path in root.rglob("*.md")
        if not (_EXCLUDED_DIRECTORIES & set(path.relative_to(root).parts))
        and not _is_vendored_corpus_source(path.relative_to(root))
    )


def _is_vendored_corpus_source(relative_path: Path) -> bool:
    """Identify exact external payloads whose internal links are not ours to rewrite."""
    parts = relative_path.parts
    return len(parts) >= 5 and parts[0:2] == ("corpora", "realworld") and parts[3] == "sources"


def validate_markdown(root: Path, paths: Iterable[Path] | None = None) -> list[Diagnostic]:
    """Validate local Markdown targets and headings without network access."""
    root = Path(os.path.abspath(root))
    markdown_paths = (
        _discover_markdown(root) if paths is None else sorted(Path(path) for path in paths)
    )
    diagnostics: list[Diagnostic] = []
    for source in markdown_paths:
        text = source.read_text(encoding="utf-8")
        masked = _mask_code(text)
        definitions: dict[str, str] = {}
        for definition in _REFERENCE_DEFINITION.finditer(masked):
            label = _normalize_reference(definition.group(1))
            definitions[label] = _extract_destination(definition.group(2))
        for link in _INLINE_LINK.finditer(masked):
            target = _extract_destination(link.group(1))
            finding = _validate_target(root, source, _line_number(masked, link.start()), target)
            if finding:
                diagnostics.append(finding)
        for reference in _REFERENCE_USE.finditer(masked):
            label = reference.group(2) or reference.group(1)
            normalized = _normalize_reference(label)
            line = _line_number(masked, reference.start())
            if normalized not in definitions:
                diagnostics.append(
                    _diagnostic(source, line, "MD002", label, "reference definition does not exist")
                )
                continue
            finding = _validate_target(root, source, line, definitions[normalized])
            if finding:
                diagnostics.append(finding)
    return _sort_diagnostics(root, diagnostics)


def _governance_finding(root: Path, code: str, target: str, message: str) -> Diagnostic:
    """Create a root-level governance diagnostic."""
    return _diagnostic(root / target, 1, code, target, message)


def _validate_f005a_governance(root: Path) -> list[Diagnostic]:
    """Validate the curated v3.1 migration without consulting its source package."""
    diagnostics: list[Diagnostic] = []
    for relative_path in _F005A_OVERLAY_DESTINATIONS:
        if not (root / relative_path).is_file():
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV007",
                    relative_path,
                    "reviewed F005A overlay destination is missing",
                )
            )

    constitution = root / ".specify/memory/constitution.md"
    constitution_source = root / "spec-kit/CONSTITUTION_SOURCE.md"
    if (
        constitution.is_file()
        and constitution_source.is_file()
        and constitution.read_bytes() != constitution_source.read_bytes()
    ):
        diagnostics.append(
            _governance_finding(
                root,
                "GOV008",
                "spec-kit/CONSTITUTION_SOURCE.md",
                "ratified constitution mirror differs from managed constitution",
            )
        )

    for relative_path, canonical_name in _F005A_ADOPTION_SOURCES.items():
        path = root / relative_path
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8").casefold()
        if "adoption source" not in content or "not authoritative" not in content:
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV008",
                    relative_path,
                    "versioned source lacks non-authoritative adoption label",
                )
            )
        if canonical_name.casefold() not in content:
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV008",
                    relative_path,
                    f"versioned source does not point to {canonical_name}",
                )
            )

    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if ".git" in relative_parts:
            continue
        if path.name == ".DS_Store" or "openardp_codex_blueprint_v3_1" in relative_parts:
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV009",
                    path.relative_to(root).as_posix(),
                    "external blueprint package or platform metadata must not be committed",
                )
            )
    return diagnostics


def _validate_feature_records(root: Path) -> list[Diagnostic]:
    """Require compact durable feature records and reject converged working artifacts."""
    diagnostics: list[Diagnostic] = []
    feature_root = root / "specs"
    feature_directories = (
        sorted(
            path
            for path in feature_root.iterdir()
            if path.is_dir() and _FEATURE_DIRECTORY.fullmatch(path.name)
        )
        if feature_root.is_dir()
        else []
    )
    for directory in feature_directories:
        for name in _DURABLE_FEATURE_FILES:
            path = directory / name
            if not path.is_file():
                relative = path.relative_to(root).as_posix()
                diagnostics.append(
                    _governance_finding(
                        root,
                        "GOV027",
                        relative,
                        "durable feature record is missing",
                    )
                )
        for path in sorted(directory.rglob("*.md")):
            if path.name in _TRANSIENT_FEATURE_FILES or "checklists" in path.parts:
                relative = path.relative_to(root).as_posix()
                diagnostics.append(
                    _governance_finding(
                        root,
                        "GOV028",
                        relative,
                        "converged working artifact must be compacted into the durable record",
                    )
                )

    prompt_root = root / "spec-kit" / "feature-prompts"
    if prompt_root.is_dir():
        for path in sorted(prompt_root.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV029",
                    relative,
                    "feature prompt is transient and must not remain after convergence",
                )
            )

    locator = root / ".specify" / "feature.json"
    try:
        active = json.loads(locator.read_bytes())
        active_relative = active["feature_directory"]
        if not isinstance(active_relative, str):
            raise TypeError
        active_parts = Path(active_relative).parts
        if (
            len(active_parts) != 2
            or active_parts[0] != "specs"
            or not _FEATURE_DIRECTORY.fullmatch(active_parts[1])
        ):
            raise TypeError
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        diagnostics.append(
            _governance_finding(
                root,
                "GOV030",
                ".specify/feature.json",
                "active-feature locator is missing or malformed",
            )
        )
    else:
        active_path = root / active_relative
        if active_path not in feature_directories:
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV030",
                    ".specify/feature.json",
                    "active-feature locator does not identify a feature directory",
                )
            )
    return diagnostics


def _validate_mcp_fixtures(root: Path) -> list[Diagnostic]:
    """Require canonical deterministic bytes for reviewed MCP golden fixtures."""
    diagnostics: list[Diagnostic] = []
    fixture_directory = root / "tests" / "fixtures" / "mcp"
    if not fixture_directory.is_dir():
        return diagnostics
    for path in sorted(fixture_directory.glob("*.json")):
        raw = path.read_bytes()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV010",
                    path.relative_to(root).as_posix(),
                    "MCP golden fixture is not valid UTF-8 JSON",
                )
            )
            continue
        canonical = json.dumps(
            parsed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if raw != canonical and raw != canonical + b"\n":
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV010",
                    path.relative_to(root).as_posix(),
                    "MCP golden fixture is not canonical deterministic JSON",
                )
            )
    return diagnostics


def _validate_f015_release_inputs(root: Path) -> list[Diagnostic]:
    """Require one complete versioned F015 input/evidence registry and candidate state."""
    diagnostics: list[Diagnostic] = []
    for relative in _F015_REQUIRED_FILES:
        if not (root / relative).is_file():
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV011",
                    relative,
                    "required F015 release input or evidence file is missing",
                )
            )
    policy_path = root / "benchmarks/release/v0.1.0/gate-policy.json"
    decision_path = root / "release/evidence/v0.1.0/decision.json"
    claim_map_path = root / "release/evidence/v0.1.0/claim-map.json"
    schema_path = root / "schemas/openardp-release-evidence.schema.json"
    try:
        policy = json.loads(policy_path.read_bytes())
        decision = json.loads(decision_path.read_bytes())
        claim_map = json.loads(claim_map_path.read_bytes())
        schema = json.loads(schema_path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        diagnostics.append(
            _governance_finding(
                root,
                "GOV012",
                "release/evidence/v0.1.0",
                "F015 release JSON is malformed",
            )
        )
        return diagnostics
    expected = {
        "policy_version": policy.get("policy_version"),
        "candidate_version": decision.get("candidate_version"),
        "schema_version": schema.get("x-openardp-release-evidence-version"),
    }
    if expected != {
        "policy_version": "0.1.0",
        "candidate_version": "0.1.0rc1",
        "schema_version": "0.1.0",
    }:
        diagnostics.append(
            _governance_finding(
                root,
                "GOV012",
                "release/evidence/v0.1.0",
                "F015 versions do not match the frozen candidate",
            )
        )
    policy_id = policy.get("policy_id")
    if not isinstance(policy_id, str) or policy_id == "sha256:" + "0" * 64:
        diagnostics.append(
            _governance_finding(
                root,
                "GOV012",
                "benchmarks/release/v0.1.0/gate-policy.json",
                "F015 policy identity is not frozen",
            )
        )
    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        claims = claim_map.get("allowed", []) + claim_map.get("prohibited", [])
        if not isinstance(claims, list) or any(
            not isinstance(claim, str) or f"claim:{claim}" not in readme for claim in claims
        ):
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV013",
                    "README.md",
                    "README claim IDs do not match the generated claim map",
                )
            )
    return diagnostics


def _validate_f016_conformance(root: Path) -> list[Diagnostic]:
    """Require and regenerate-check the bounded F016 conformance evidence."""
    diagnostics: list[Diagnostic] = []
    missing = [relative for relative in _F016_REQUIRED_FILES if not (root / relative).is_file()]
    for relative in missing:
        diagnostics.append(
            _governance_finding(
                root,
                "GOV014",
                relative,
                "required F016 conformance input or evidence file is missing",
            )
        )
    if missing:
        return diagnostics
    script = root / "scripts" / "validate_alternate_conformance.py"
    try:
        completed = subprocess.run(  # noqa: S603 - exact interpreter and repository script
            [sys.executable, str(script), "--check"],
            cwd=root,
            env={
                key: value
                for key, value in os.environ.items()
                if key in {"PATH", "SYSTEMROOT", "WINDIR"}
            },
            capture_output=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        completed = None
    if completed is None or completed.returncode != 0:
        diagnostics.append(
            _governance_finding(
                root,
                "GOV015",
                "conformance/alternate-parser/v0.1.0",
                "F016 generated conformance evidence is invalid or drifted",
            )
        )
    return diagnostics


def _validate_f017_design(root: Path) -> list[Diagnostic]:
    """Require the complete bounded F017 mock design and decision evidence."""
    diagnostics: list[Diagnostic] = []
    for relative in _F017_REQUIRED_FILES:
        if not (root / relative).is_file():
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV016",
                    relative,
                    "required F017 mock design artifact is missing",
                )
            )
    decision_path = root / "docs/16_MICROSOFT_GRAPH_DESIGN_SPIKE.md"
    if decision_path.is_file():
        decision = decision_path.read_text(encoding="utf-8")
        required = (
            "Mock contract architecture: GO",
            "Production Microsoft Graph connector: NO-GO",
            "no credential, SDK, network path or production configuration",
        )
        if any(statement not in decision for statement in required):
            diagnostics.append(
                _governance_finding(
                    root,
                    "GOV017",
                    "docs/16_MICROSOFT_GRAPH_DESIGN_SPIKE.md",
                    "F017 mock and production decisions are incomplete",
                )
            )
    return diagnostics


def _validate_f019_ci_governance(root: Path) -> list[Diagnostic]:
    """Require the complete F019 CI policy and evidence boundary."""
    return [
        _governance_finding(
            root,
            "GOV018",
            relative,
            "required F019 CI governance artifact is missing",
        )
        for relative in _F019_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f020_product_benchmark(root: Path) -> list[Diagnostic]:
    """Require the complete F020 product-value benchmark boundary."""
    return [
        _governance_finding(
            root,
            "GOV019",
            relative,
            "required F020 product benchmark artifact is missing",
        )
        for relative in _F020_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f024_realworld_corpus(root: Path) -> list[Diagnostic]:
    """Require the complete F024 corpus and structural-result boundary."""
    return [
        _governance_finding(
            root,
            "GOV020",
            relative,
            "required F024 real-world corpus artifact is missing",
        )
        for relative in _F024_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f025_semantic_evaluation(root: Path) -> list[Diagnostic]:
    """Require the complete F025 question, result and independent-validation boundary."""
    return [
        _governance_finding(
            root,
            "GOV021",
            relative,
            "required F025 semantic evaluation artifact is missing",
        )
        for relative in _F025_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f026_relevance(root: Path) -> list[Diagnostic]:
    """Require the complete F026 policy, benchmark and independent-validation boundary."""
    return [
        _governance_finding(
            root,
            "GOV022",
            relative,
            "required F026 relevance and abstention artifact is missing",
        )
        for relative in _F026_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f027_ranking(root: Path) -> list[Diagnostic]:
    """Require the complete F027 ranking, benchmark and validation boundary."""
    return [
        _governance_finding(
            root,
            "GOV023",
            relative,
            "required F027 lexical ranking artifact is missing",
        )
        for relative in _F027_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f028_csv(root: Path) -> list[Diagnostic]:
    """Require the complete F028 stable CSV and measured-validation boundary."""
    return [
        _governance_finding(
            root,
            "GOV024",
            relative,
            "required F028 stable CSV artifact is missing",
        )
        for relative in _F028_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f029_semantic_retrieval(root: Path) -> list[Diagnostic]:
    """Require the complete F029 provider, benchmark and validation boundary."""
    return [
        _governance_finding(
            root,
            "GOV025",
            relative,
            "required F029 provider-neutral retrieval artifact is missing",
        )
        for relative in _F029_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def _validate_f031_repository_hygiene(root: Path) -> list[Diagnostic]:
    """Require the complete F031 hygiene and bounded-refactoring evidence."""
    return [
        _governance_finding(
            root,
            "GOV026",
            relative,
            "required F031 repository-hygiene artifact is missing",
        )
        for relative in _F031_REQUIRED_FILES
        if not (root / relative).is_file()
    ]


def validate_governance(root: Path) -> list[Diagnostic]:
    """Validate required policy files and cross-document baseline consistency."""
    root = Path(os.path.abspath(root))
    diagnostics: list[Diagnostic] = []
    for name in _REQUIRED_GOVERNANCE_FILES:
        if not (root / name).is_file():
            diagnostics.append(
                _governance_finding(root, "GOV001", name, "required repository artifact is missing")
            )

    pyproject_path = root / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            with pyproject_path.open("rb") as stream:
                configuration = tomllib.load(stream)
            project = configuration["project"]
            uv_config = configuration["tool"]["uv"]
        except (KeyError, tomllib.TOMLDecodeError) as error:
            diagnostics.append(
                _governance_finding(root, "GOV002", "pyproject.toml", f"invalid metadata: {error}")
            )
        else:
            expected_metadata = {
                "license": (project.get("license"), "Apache-2.0"),
                "requires-python": (project.get("requires-python"), ">=3.12,<3.13"),
                "required-version": (uv_config.get("required-version"), "==0.11.31"),
                "preview-features": (
                    uv_config.get("preview-features"),
                    ["centralized-project-envs"],
                ),
            }
            for field, (actual, expected) in expected_metadata.items():
                if actual != expected:
                    diagnostics.append(
                        _governance_finding(
                            root,
                            "GOV003",
                            "pyproject.toml",
                            f"{field} must equal {expected!r}, found {actual!r}",
                        )
                    )

    license_path = root / "LICENSE"
    if license_path.is_file():
        license_text = license_path.read_text(encoding="utf-8")
        if "Apache License\nVersion 2.0, January 2004" not in license_text:
            diagnostics.append(
                _governance_finding(root, "GOV004", "LICENSE", "Apache-2.0 text is incomplete")
            )

    documents_requiring_commands = ("README.md", "START_HERE.md", "CONTRIBUTING.md")
    for name in documents_requiring_commands:
        path = root / name
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for command in _CANONICAL_COMMANDS:
            if command not in content:
                diagnostics.append(
                    _governance_finding(
                        root,
                        "GOV005",
                        name,
                        f"canonical command is missing: {command}",
                    )
                )

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        for name in ("CHANGELOG.md", "CONTRIBUTING.md", "LICENSE", "SECURITY.md", "VALIDATION.md"):
            if f"]({name})" not in readme:
                diagnostics.append(
                    _governance_finding(
                        root,
                        "GOV006",
                        "README.md",
                        f"governance link is missing: {name}",
                    )
                )
    diagnostics.extend(_validate_f005a_governance(root))
    diagnostics.extend(_validate_feature_records(root))
    diagnostics.extend(_validate_mcp_fixtures(root))
    diagnostics.extend(_validate_f015_release_inputs(root))
    diagnostics.extend(_validate_f016_conformance(root))
    diagnostics.extend(_validate_f017_design(root))
    diagnostics.extend(_validate_f019_ci_governance(root))
    diagnostics.extend(_validate_f020_product_benchmark(root))
    diagnostics.extend(_validate_f024_realworld_corpus(root))
    diagnostics.extend(_validate_f025_semantic_evaluation(root))
    diagnostics.extend(_validate_f026_relevance(root))
    diagnostics.extend(_validate_f027_ranking(root))
    diagnostics.extend(_validate_f028_csv(root))
    diagnostics.extend(_validate_f029_semantic_retrieval(root))
    diagnostics.extend(_validate_f031_repository_hygiene(root))
    return _sort_diagnostics(root, diagnostics)


def validate_repository(root: Path) -> list[Diagnostic]:
    """Return all offline Markdown and governance findings for a repository."""
    root = Path(os.path.abspath(root))
    return _sort_diagnostics(
        root,
        [
            *validate_markdown(root),
            *validate_governance(root),
            *_validate_maintainability(root),
            *_validate_repository_hygiene(root),
            *_validate_ci(root),
        ],
    )


def _validate_maintainability(root: Path) -> list[Diagnostic]:
    """Project deterministic structural findings into repository diagnostics."""
    policy_path = root / "quality/maintainability-policy.json"
    try:
        findings = audit_maintainability(root, load_maintainability_policy(policy_path))
    except PolicyError as error:
        return [
            Diagnostic(
                path=policy_path,
                line=1,
                code="HYG001",
                target="maintainability-policy",
                message=str(error),
            )
        ]
    return [
        Diagnostic(
            path=root / finding.key.partition(":")[0],
            line=1,
            code="HYG002",
            target=finding.code,
            message=(
                f"maintainability limit violated: actual={finding.actual!r}, "
                f"allowed={finding.allowed!r}"
            ),
        )
        for finding in findings
    ]


def _validate_repository_hygiene(root: Path) -> list[Diagnostic]:
    """Project read-only sync-artifact findings into repository diagnostics."""
    try:
        report = audit_repository_hygiene(root)
    except RepositoryHygieneError as error:
        return [
            Diagnostic(
                path=root,
                line=1,
                code="HYG003",
                target="repository-hygiene",
                message=str(error),
            )
        ]
    return [
        Diagnostic(
            path=root / finding.candidate,
            line=1,
            code="HYG004",
            target=f"{finding.scope}:{finding.kind.value}",
            message="repository sync-conflict artifact requires review",
        )
        for finding in report.findings
    ]


def _validate_ci(root: Path) -> list[Diagnostic]:
    """Project deterministic CI policy findings into repository diagnostics."""
    policy_path = root / "quality/ci-policy.json"
    try:
        findings = audit_ci(root, load_ci_policy(policy_path))
    except CIAuditError as error:
        return [
            Diagnostic(
                path=policy_path,
                line=1,
                code="CI001",
                target="ci-policy",
                message=str(error),
            )
        ]
    return [
        Diagnostic(
            path=root / finding.path,
            line=1,
            code="CI002",
            target=finding.code,
            message=f"CI invariant violated: marker={finding.marker}",
        )
        for finding in findings
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run repository validation and return a shell-friendly status code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    root = Path(os.path.abspath(arguments.root))
    diagnostics = validate_repository(root)
    for diagnostic in diagnostics:
        print(diagnostic.render(root))
    if diagnostics:
        print(f"Repository validation failed with {len(diagnostics)} finding(s).")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
