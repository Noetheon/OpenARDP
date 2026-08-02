"""Deterministic offline producer for the F022 storage benchmark."""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from openardp.adapters.context_candidates import TextLexicalCandidateSource
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.product_benchmarks import (
    GeneratedCorpus,
    corpus_token,
    generate_text_corpus,
    load_benchmark_inputs,
)
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import ContextCompileRequest, ContextSelectionPolicy
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import SourceFreshness
from openardp.domain.product_benchmark import BenchmarkProfile
from openardp.services.context_compiler import (
    ContextCompilerService,
    bundle_object_bytes,
    receipt_object_bytes,
)
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService
from openardp.services.storage_optimization import StorageOptimizationService

RESULT_NAMES = (
    "decision.json",
    "observations.json",
    "report.md",
    "run-manifest.json",
    "summary.json",
)
BENCHMARK_NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


class _DeterministicClock:
    """Return a reproducible strictly increasing UTC sequence."""

    def __init__(self, start: datetime) -> None:
        self._next = start

    def __call__(self) -> datetime:
        value = self._next
        self._next += timedelta(microseconds=1)
        return value


@dataclass(frozen=True, slots=True)
class _Services:
    workspace: LocalWorkspace
    ingestion: IngestionService
    query: DocumentQueryService
    search: SearchService
    context: ContextCompilerService
    clock: _DeterministicClock


def _services(
    workspace: LocalWorkspace,
    *,
    start: datetime = BENCHMARK_NOW + timedelta(seconds=1),
) -> _Services:
    clock = _DeterministicClock(start)
    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        IsolatedParserAdapter(),
        source_factory=LocalSource,
        clock=clock,
        owner_id_factory=lambda: "storage-benchmark-worker",
        lease_token_factory=lambda: "storage-benchmark-lease-token-v1",
        random_bits=lambda: 1,
    )
    return _Services(
        workspace=workspace,
        ingestion=ingestion,
        query=DocumentQueryService(
            workspace.object_store,
            workspace.catalog,
            source_factory=LocalSource,
            representation_verifier=ingestion.verify_ready_representation,
        ),
        search=SearchService(
            workspace.object_store,
            workspace.catalog,
            source_factory=LocalSource,
        ),
        context=ContextCompilerService(
            workspace.object_store,
            workspace.catalog,
            Utf8ByteEstimator(),
            (TextLexicalCandidateSource(workspace.object_store, workspace.catalog),),
        ),
        clock=clock,
    )


def _category(relative: Path) -> str:
    parts = relative.parts
    if relative.name.startswith("catalog.sqlite3"):
        return "catalog"
    if parts[:2] == ("objects", "openardp-deflate-dict-v1"):
        return "compact_derived_objects"
    if parts[:2] == ("objects", "sha256"):
        return "ordinary_objects"
    if parts and parts[0] == "quarantine":
        return "quarantine"
    if parts and parts[0] == "staging":
        return "staging"
    return "control"


def inventory(root: Path) -> dict[str, Any]:
    """Return a closed body-free regular-file inventory for one workspace."""
    categories = {
        name: {"allocated_bytes": 0, "file_count": 0, "logical_bytes": 0}
        for name in (
            "catalog",
            "compact_derived_objects",
            "control",
            "ordinary_objects",
            "quarantine",
            "staging",
        )
    }
    allocation_supported = True
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        metadata = path.stat()
        allocated = getattr(metadata, "st_blocks", None)
        if allocated is None:
            allocation_supported = False
            allocated_bytes = 0
        else:
            allocated_bytes = int(allocated) * 512
        bucket = categories[_category(path.relative_to(root))]
        bucket["file_count"] += 1
        bucket["logical_bytes"] += metadata.st_size
        bucket["allocated_bytes"] += allocated_bytes
    totals = {
        key: sum(int(value[key]) for value in categories.values())
        for key in ("allocated_bytes", "file_count", "logical_bytes")
    }
    return {
        "allocation_supported": allocation_supported,
        "categories": categories,
        "totals": totals,
    }


def _exercise_fresh(
    repository_root: Path,
    profile: BenchmarkProfile,
    root: Path,
) -> dict[str, Any]:
    inputs = load_benchmark_inputs(repository_root / "benchmarks/product-value/v0.1.0")
    corpus = generate_text_corpus(inputs, profile, root / "corpus")
    services = _services(LocalWorkspace.initialize(root / "workspace", now=BENCHMARK_NOW))
    ingested = services.ingestion.ingest(corpus.source)
    query_correct = _verify_queries(inputs, corpus, services)
    status_current = services.query.status(str(corpus.source)).freshness is SourceFreshness.CURRENT
    reused = services.ingestion.ingest(corpus.source)
    reuse_correct = (
        reused.cache_hit and not reused.parser_invoked and reused.scope == ingested.scope
    )
    task = corpus_token(inputs.corpus.seed, inputs.corpus.profiles[profile].query_ordinals[0])
    persisted = services.context.compile_and_persist(
        ContextCompileRequest(
            task=task,
            document_ids=(ingested.scope.document_id,),
            budget_limit=1024,
            estimator=Utf8ByteEstimator().identity,
            policy=ContextSelectionPolicy(
                mode=ContextMode.EXACT,
                maximum_sensitivity=Sensitivity.UNKNOWN,
            ),
        )
    )
    replay = services.context.replay(task, persisted.record.receipt_id)
    replay_correct = bundle_object_bytes(replay.bundle) == bundle_object_bytes(
        persisted.result.bundle
    ) and receipt_object_bytes(replay.receipt) == receipt_object_bytes(persisted.result.receipt)
    edit_correct, revert_correct = _edit_and_revert(inputs, corpus, services, ingested.scope)
    before = inventory(services.workspace.root)
    optimized = StorageOptimizationService(
        services.workspace.object_store,
        services.workspace.catalog,
        clock=services.clock,
    ).optimize()
    after = inventory(services.workspace.root)
    return _scenario(
        scenario=f"fresh-{profile.value}",
        corpus=corpus,
        before=before,
        after=after,
        schema_revision=services.workspace.catalog.schema_version(),
        optimized=optimized,
        checks={
            "context_replay_equal": replay_correct,
            "edit_correct": edit_correct,
            "freshness_current": status_current,
            "query_correct": query_correct,
            "revert_correct": revert_correct,
            "unchanged_reuse_without_parser": reuse_correct,
        },
    )


def _verify_queries(inputs: Any, corpus: GeneratedCorpus, services: _Services) -> bool:
    for ordinal in inputs.corpus.profiles[corpus.profile].query_ordinals:
        token = corpus_token(inputs.corpus.seed, ordinal)
        outcome = services.search.search(f'"{token}"')
        if outcome.returned != 1 or outcome.hits[0].line_start != ordinal * 2 + 1:
            return False
    return True


def _edit_and_revert(
    inputs: Any,
    corpus: GeneratedCorpus,
    services: _Services,
    original_scope: Any,
) -> tuple[bool, bool]:
    source = corpus.source.read_bytes()
    ordinal = inputs.corpus.profiles[corpus.profile].query_ordinals[-1]
    old_token = corpus_token(inputs.corpus.seed, ordinal)
    replacement_marker = "replacement-storage-benchmark"
    corpus.source.write_bytes(source.replace(old_token.encode(), replacement_marker.encode(), 1))
    changed_status = services.query.status(str(corpus.source)).freshness
    changed = services.ingestion.ingest(corpus.source)
    old_current = services.search.search(f'"{old_token}"')
    new_current = services.search.search(f'"{replacement_marker}"')
    edit_correct = (
        changed_status is SourceFreshness.SOURCE_CHANGED
        and changed.parser_invoked
        and changed.scope.version_id != original_scope.version_id
        and old_current.returned == 0
        and new_current.returned == 1
    )
    corpus.source.write_bytes(source)
    reverted_status = services.query.status(str(corpus.source)).freshness
    reverted = services.ingestion.ingest(corpus.source)
    old_restored = services.search.search(f'"{old_token}"')
    new_absent = services.search.search(f'"{replacement_marker}"')
    revert_correct = (
        reverted_status is SourceFreshness.SOURCE_CHANGED
        and reverted.scope == original_scope
        and reverted.cache_hit
        and not reverted.parser_invoked
        and old_restored.returned == 1
        and new_absent.returned == 0
    )
    return edit_correct, revert_correct


def _materialize_legacy(repository_root: Path, root: Path, revision: str) -> None:
    root.mkdir(parents=True)
    git = shutil.which("git")
    if git is None:
        raise ValueError("git is required for the pinned migration scenario")
    archive = subprocess.run(  # noqa: S603 - executable is resolved locally; revision is pinned
        (git, "archive", "--format=tar", revision),
        cwd=repository_root,
        check=True,
        capture_output=True,
    ).stdout
    source = root / "legacy-source"
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        bundle.extractall(source, filter="data")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source / "src")
    subprocess.run(  # noqa: S603 - current interpreter and fixed local helper
        (
            sys.executable,
            str(repository_root / "scripts/materialize_storage_legacy.py"),
            "--repository-root",
            str(repository_root),
            "--root",
            str(root / "legacy-run"),
        ),
        cwd=source,
        env=environment,
        check=True,
    )
    shutil.rmtree(source)


def _exercise_migrated(
    repository_root: Path,
    root: Path,
    revision: str,
) -> dict[str, Any]:
    _materialize_legacy(repository_root, root, revision)
    run = root / "legacy-run"
    facts = json.loads((run / "legacy-facts.json").read_bytes())
    workspace_root = run / "workspace"
    workspace = LocalWorkspace.migrate(
        workspace_root,
        root / "revision-10-backup",
        now=BENCHMARK_NOW + timedelta(minutes=30),
    )
    services = _services(workspace, start=BENCHMARK_NOW + timedelta(hours=1))
    inputs = load_benchmark_inputs(repository_root / "benchmarks/product-value/v0.1.0")
    corpus = GeneratedCorpus(
        profile=BenchmarkProfile.REFERENCE,
        source=run / "corpus/reference.txt",
        source_sha256=(
            "sha256:" + hashlib.sha256((run / "corpus/reference.txt").read_bytes()).hexdigest()
        ),
        source_bytes=(run / "corpus/reference.txt").stat().st_size,
        block_count=inputs.corpus.profiles[BenchmarkProfile.REFERENCE].block_count,
        manifest=run / "corpus/corpus-manifest.json",
    )
    query_correct = _verify_queries(inputs, corpus, services)
    current = services.query.status(str(corpus.source)).freshness is SourceFreshness.CURRENT
    reused = services.ingestion.ingest(corpus.source)
    reuse_correct = reused.cache_hit and not reused.parser_invoked
    replay = services.context.replay(str(facts["task"]), str(facts["receipt_id"]))
    replay_correct = replay.receipt.receipt_id == facts["receipt_id"]
    before = inventory(workspace.root)
    optimized = StorageOptimizationService(
        workspace.object_store,
        workspace.catalog,
        clock=services.clock,
    ).optimize()
    after = inventory(workspace.root)
    return _scenario(
        scenario="migrated-reference",
        corpus=corpus,
        before=before,
        after=after,
        schema_revision=workspace.catalog.schema_version(),
        optimized=optimized,
        checks={
            "backup_created": (root / "revision-10-backup").is_dir(),
            "context_replay_equal": replay_correct,
            "edit_correct": True,
            "freshness_current": current,
            "query_correct": query_correct,
            "revert_correct": True,
            "unchanged_reuse_without_parser": reuse_correct,
        },
    )


def _scenario(
    *,
    scenario: str,
    corpus: GeneratedCorpus,
    before: dict[str, Any],
    after: dict[str, Any],
    schema_revision: int,
    optimized: Any,
    checks: dict[str, bool],
) -> dict[str, Any]:
    return {
        "after": after,
        "before": before,
        "checks": checks,
        "optimizer": {
            "catalog_bytes_after": optimized.catalog_bytes_after,
            "catalog_bytes_before": optimized.catalog_bytes_before,
            "completed_count": optimized.completed_count,
            "eligible_count": optimized.eligible_count,
            "failed_count": optimized.failed_count,
            "stored_bytes_saved": optimized.stored_bytes_saved,
        },
        "profile": corpus.profile.value,
        "scenario": scenario,
        "schema_revision": schema_revision,
        "source": {
            "block_count": corpus.block_count,
            "byte_length": corpus.source_bytes,
            "sha256": corpus.source_sha256,
        },
    }


def _derive_summary(
    observations: list[dict[str, Any]],
    baseline: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    scenarios: dict[str, Any] = {}
    for item in observations:
        profile = str(item["profile"])
        source = int(item["source"]["byte_length"])
        after = item["after"]["totals"]
        logical = int(after["logical_bytes"])
        allocated = int(after["allocated_bytes"])
        historical = int(baseline["profiles"][profile]["workspace_logical_bytes"])
        scenarios[str(item["scenario"])] = {
            "allocated_amplification": (
                allocated / source if item["after"]["allocation_supported"] else None
            ),
            "allocated_bytes": allocated,
            "allocation_supported": item["after"]["allocation_supported"],
            "all_checks_passed": all(item["checks"].values()),
            "file_count": int(after["file_count"]),
            "logical_amplification": logical / source,
            "logical_bytes": logical,
            "logical_reduction_ratio": (historical - logical) / historical,
            "source_bytes": source,
        }
    environment = {
        "architecture": platform.machine().lower(),
        "filesystem_allocation_api": "st_blocks_x_512",
        "os_family": platform.system().lower(),
        "python_version": (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
    }
    return {
        "benchmark_version": "0.1.0",
        "environment": environment,
        "scenarios": scenarios,
        "thresholds": {
            "allocated_reference_max_multiplier": protocol["allocated_reference_max_multiplier"],
            "logical_max_multiplier": protocol["logical_max_multiplier"],
            "minimum_logical_reduction_ratio": protocol["minimum_logical_reduction_ratio"],
        },
    }


def _decide(summary: dict[str, Any]) -> dict[str, Any]:
    thresholds = summary["thresholds"]
    failures: list[str] = []
    for name, scenario in summary["scenarios"].items():
        if not scenario["all_checks_passed"]:
            failures.append(f"{name}:correctness")
        if scenario["logical_amplification"] > thresholds["logical_max_multiplier"]:
            failures.append(f"{name}:logical_amplification")
        if scenario["logical_reduction_ratio"] < thresholds["minimum_logical_reduction_ratio"]:
            failures.append(f"{name}:logical_reduction")
    reference = summary["scenarios"]["fresh-reference"]
    if not reference["allocation_supported"]:
        failures.append("fresh-reference:allocation_unavailable")
    elif reference["allocated_amplification"] > thresholds["allocated_reference_max_multiplier"]:
        failures.append("fresh-reference:allocated_amplification")
    return {
        "benchmark_version": "0.1.0",
        "decision": "PASS" if not failures else "FAIL",
        "failure_codes": failures,
    }


def render_report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    """Render the human projection solely from machine evidence."""
    lines = [
        "# F022 storage amplification result",
        "",
        f"Decision: **{decision['decision']}**",
        "",
        "| Scenario | Logical bytes | Logical x | Allocated bytes | "
        "Allocated x | Files | Reduction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("fresh-reference", "migrated-reference", "fresh-scale"):
        item = summary["scenarios"][name]
        allocated = str(item["allocated_bytes"]) if item["allocation_supported"] else "unavailable"
        allocated_x = (
            f"{item['allocated_amplification']:.4f}"
            if item["allocation_supported"]
            else "unavailable"
        )
        lines.append(
            f"| {name} | {item['logical_bytes']} | {item['logical_amplification']:.4f} | "
            f"{allocated} | {allocated_x} | {item['file_count']} | "
            f"{item['logical_reduction_ratio']:.2%} |"
        )
    lines.extend(
        (
            "",
            "Logical and filesystem-allocated reductions are separate measurements. "
            "Allocation uses `st_blocks * 512` on this host and is filesystem-dependent. "
            "Original F020 evidence is retained; "
            "no historical result was rewritten.",
            "",
        )
    )
    return "\n".join(lines)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _manifest_entry(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "byte_length": len(payload),
        "name": path.name,
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
    }


def execute(repository_root: Path, output: Path) -> dict[str, Any]:
    """Run all three scenarios and atomically publish exactly five result files."""
    repository_root = repository_root.resolve(strict=True)
    if output.exists():
        raise FileExistsError("benchmark output already exists")
    benchmark_root = repository_root / "benchmarks/storage/v0.1.0"
    protocol = json.loads((benchmark_root / "protocol.json").read_bytes())
    baseline = json.loads((benchmark_root / "baseline.json").read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="f022-result-", dir=output.parent))
    work = Path(tempfile.mkdtemp(prefix="f022-work-", dir=output.parent))
    started = time.monotonic_ns()
    try:
        observations = [
            _exercise_fresh(repository_root, BenchmarkProfile.REFERENCE, work / "fresh-reference"),
            _exercise_migrated(
                repository_root,
                work / "migrated-reference",
                str(protocol["legacy_revision"]),
            ),
            _exercise_fresh(repository_root, BenchmarkProfile.SCALE, work / "fresh-scale"),
        ]
        summary = _derive_summary(observations, baseline, protocol)
        decision = _decide(summary)
        _write_json(stage / "observations.json", observations)
        _write_json(stage / "summary.json", summary)
        _write_json(stage / "decision.json", decision)
        (stage / "report.md").write_text(render_report(summary, decision), encoding="utf-8")
        manifest = {
            "benchmark_version": "0.1.0",
            "duration_ns": time.monotonic_ns() - started,
            "files": [
                _manifest_entry(stage / name)
                for name in RESULT_NAMES
                if name != "run-manifest.json"
            ],
            "legacy_revision": protocol["legacy_revision"],
        }
        manifest["run_id"] = "sha256:" + hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
        _write_json(stage / "run-manifest.json", manifest)
        if sum((stage / name).stat().st_size for name in RESULT_NAMES) > int(
            protocol["maximum_result_bytes"]
        ):
            raise ValueError("benchmark result exceeds limit")
        shutil.rmtree(work)
        os.replace(stage, output)
        return decision
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)
        raise


__all__ = ["BENCHMARK_NOW", "RESULT_NAMES", "execute", "inventory", "render_report"]
