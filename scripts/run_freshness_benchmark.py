"""Execute and atomically publish the offline F021 freshness benchmark."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
import time
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue

from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.product_benchmarks import generate_text_corpus, load_benchmark_inputs
from openardp.domain.identity import canonical_sha256
from openardp.domain.ingestion import (
    ParsedTextDocument,
    ParserRecipe,
    RepresentationAggregate,
    StatusMode,
)
from openardp.domain.product_benchmark import BenchmarkProfile
from openardp.domain.storage import ObjectInventory, StoredObject
from openardp.ports.catalog import Catalog
from openardp.ports.object_store import ObjectStore
from openardp.ports.parser import ParserAdapter
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.release_benchmarks import environment_profile

try:
    from scripts.freshness_benchmark import (
        FreshnessCounters,
        FreshnessObservation,
        canonical_file,
        decide_freshness,
        load_freshness_protocol,
        make_observation,
        render_report,
        summarize_observations,
    )
except ModuleNotFoundError:
    from freshness_benchmark import (  # type: ignore[no-redef]
        FreshnessCounters,
        FreshnessObservation,
        canonical_file,
        decide_freshness,
        load_freshness_protocol,
        make_observation,
        render_report,
        summarize_observations,
    )

_RESULT_FILES = ("decision.json", "observations.json", "report.md", "summary.json")


class _CountingParser:
    def __init__(self) -> None:
        self.delegate = IsolatedParserAdapter()
        self.calls = 0

    @property
    def recipe(self) -> ParserRecipe:
        return self.delegate.recipe

    def supports(self, media_type: str) -> bool:
        return self.delegate.supports(media_type)

    def parse(self, chunks: Iterable[bytes], *, media_type: str) -> ParsedTextDocument:
        self.calls += 1
        return self.delegate.parse(chunks, media_type=media_type)


class _CountingCatalog:
    def __init__(self, delegate: Catalog) -> None:
        self.delegate = delegate
        self.aggregate_loads = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)

    def load_representation(self, scope: object) -> RepresentationAggregate | None:
        self.aggregate_loads += 1
        return self.delegate.load_representation(scope)  # type: ignore[arg-type]


class _CountingStore:
    def __init__(self, delegate: ObjectStore, block_ids: frozenset[str]) -> None:
        self.delegate = delegate
        self.block_ids = block_ids
        self.block_verifications = 0

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        return self.delegate.put_chunks(chunks)

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        return self.delegate.iter_chunks(object_id, chunk_size=chunk_size)

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject:
        if object_id in self.block_ids:
            self.block_verifications += 1
        return self.delegate.verify(object_id, expected_length=expected_length)

    def inventory(self) -> ObjectInventory:
        return self.delegate.inventory()


class _CountingSourceFactory:
    def __init__(self) -> None:
        self.inspections = 0

    def __call__(self, path: Path) -> _CountingSource:
        return _CountingSource(LocalSource(path), self)


class _CountingSource:
    def __init__(self, delegate: LocalSource, owner: _CountingSourceFactory) -> None:
        self.delegate = delegate
        self.owner = owner

    @property
    def source_key(self) -> object:
        return self.delegate.source_key

    def inspect(self, *, observed_at: datetime) -> object:
        self.owner.inspections += 1
        return self.delegate.inspect(observed_at=observed_at)


class _VerifierCounter:
    def __init__(self, delegate: IngestionService) -> None:
        self.delegate = delegate
        self.calls = 0

    def __call__(self, aggregate: RepresentationAggregate) -> None:
        self.calls += 1
        self.delegate.verify_ready_representation(aggregate)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f"{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _inventory_id(inventory: ObjectInventory) -> str:
    return canonical_sha256(inventory.model_dump(mode="json"))


def _measure_profile(
    repository_root: Path,
    profile: BenchmarkProfile,
    work: Path,
    environment_id: str,
) -> tuple[list[FreshnessObservation], dict[str, JsonValue]]:
    inputs = load_benchmark_inputs(repository_root / "benchmarks/product-value/v0.1.0")
    corpus = generate_text_corpus(inputs, profile, work / "corpus")
    workspace = LocalWorkspace.initialize(work / "workspace", now=datetime.now(UTC))
    parser = _CountingParser()
    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        cast(ParserAdapter, parser),
        source_factory=LocalSource,
    )
    result = ingestion.ingest(corpus.source)
    if result.block_count != corpus.block_count:
        raise ValueError("prepared block count differs from frozen corpus")
    aggregate = workspace.catalog.load_representation(result.scope)
    if aggregate is None:
        raise ValueError("prepared representation is unavailable")
    block_ids = frozenset(item.object.object_id for item in aggregate.blocks)
    catalog = _CountingCatalog(workspace.catalog)
    store = _CountingStore(workspace.object_store, block_ids)
    verifier_service = IngestionService(
        cast(ObjectStore, store),
        workspace.catalog,
        cast(ParserAdapter, parser),
        source_factory=LocalSource,
    )
    verifier = _VerifierCounter(verifier_service)
    source_factory = _CountingSourceFactory()
    query = DocumentQueryService(
        workspace.object_store,
        cast(Catalog, catalog),
        source_factory=cast(Any, source_factory),
        representation_verifier=verifier,
    )
    source_hash_before = _sha256(corpus.source)
    inventory_before = _inventory_id(workspace.object_store.inventory())
    observations: list[FreshnessObservation] = []
    for mode in (StatusMode.HEAD, StatusMode.FULL):
        query.status(str(corpus.source), mode=mode)
        for repetition in range(7):
            catalog.aggregate_loads = 0
            store.block_verifications = 0
            parser.calls = 0
            source_factory.inspections = 0
            verifier.calls = 0
            started = time.monotonic_ns()
            status = query.status(str(corpus.source), mode=mode)
            elapsed = time.monotonic_ns() - started
            observations.append(
                make_observation(
                    environment_id=environment_id,
                    profile=profile.value,
                    mode=mode.value,
                    repetition=repetition,
                    block_count=corpus.block_count,
                    source_bytes=corpus.source_bytes,
                    elapsed_ns=elapsed,
                    freshness=status.freshness.value,
                    integrity_coverage=status.integrity_coverage.value,
                    counters=FreshnessCounters(
                        aggregate_loads=catalog.aggregate_loads,
                        block_object_verifications=store.block_verifications,
                        parser_invocations=parser.calls,
                        source_inspections=source_factory.inspections,
                        verifier_invocations=verifier.calls,
                    ).model_dump(mode="json"),
                )
            )
    facts: dict[str, JsonValue] = {
        "block_count": corpus.block_count,
        "source_bytes": corpus.source_bytes,
        "source_sha256_before": source_hash_before,
        "source_sha256_after": _sha256(corpus.source),
        "object_inventory_before": inventory_before,
        "object_inventory_after": _inventory_id(workspace.object_store.inventory()),
    }
    if facts["source_sha256_before"] != facts["source_sha256_after"]:
        raise ValueError("status workload modified the source")
    if facts["object_inventory_before"] != facts["object_inventory_after"]:
        raise ValueError("status workload modified persisted objects")
    return observations, facts


def execute_freshness_benchmark(repository_root: Path, output: Path) -> Path:
    """Run both frozen scales and atomically publish complete evidence."""
    root = repository_root.resolve(strict=True)
    protocol, protocol_id = load_freshness_protocol(root)
    if output.exists():
        raise FileExistsError("benchmark output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f"{output.name}-stage-", dir=output.parent))
    work = Path(tempfile.mkdtemp(prefix="f021-work-", dir=output.parent))
    started = time.monotonic_ns()
    try:
        environment = environment_profile(reference_timing=True).model_dump(mode="json")
        environment_id = canonical_sha256(environment)
        observations: list[FreshnessObservation] = []
        facts: dict[str, JsonValue] = {}
        for profile in (BenchmarkProfile.REFERENCE, BenchmarkProfile.SCALE):
            observed, profile_facts = _measure_profile(
                root,
                profile,
                work / profile.value,
                environment_id,
            )
            observations.extend(observed)
            facts[profile.value] = profile_facts
        summaries = summarize_observations(protocol, observations)
        decision = decide_freshness(protocol, observations, summaries)
        run_id = canonical_sha256(
            {
                "environment_id": environment_id,
                "observation_ids": [item.observation_id for item in observations],
                "protocol_id": protocol_id,
            }
        )
        observation_payload: dict[str, JsonValue] = {
            "benchmark_version": "0.1.0",
            "environment": environment,
            "environment_id": environment_id,
            "facts": facts,
            "observations": [item.model_dump(mode="json") for item in observations],
            "protocol_id": protocol_id,
            "run_id": run_id,
        }
        summary_payload: dict[str, JsonValue] = {
            "benchmark_version": "0.1.0",
            "protocol_id": protocol_id,
            "run_id": run_id,
            "summaries": [item.model_dump(mode="json") for item in summaries],
        }
        _atomic_write(stage / "observations.json", canonical_file(observation_payload))
        _atomic_write(stage / "summary.json", canonical_file(summary_payload))
        _atomic_write(stage / "decision.json", canonical_file(decision))
        _atomic_write(stage / "report.md", render_report(protocol, summaries, decision))
        duration_ns = time.monotonic_ns() - started
        files: dict[str, JsonValue] = {}
        for name in _RESULT_FILES:
            payload = (stage / name).read_bytes()
            files[name] = {
                "byte_length": len(payload),
                "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            }
        manifest: dict[str, JsonValue] = {
            "benchmark_version": "0.1.0",
            "duration_ns": duration_ns,
            "environment_id": environment_id,
            "files": files,
            "protocol_id": protocol_id,
            "run_id": run_id,
        }
        manifest["manifest_id"] = canonical_sha256(manifest)
        _atomic_write(stage / "run-manifest.json", canonical_file(manifest))
        os.replace(stage, output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return output


def main() -> int:
    """Parse bounded maintainer arguments and execute a fresh run."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = execute_freshness_benchmark(arguments.repository_root, arguments.output)
    except (OSError, ValueError):
        print("freshness_benchmark_failed")
        return 6
    print(f"freshness_benchmark_published:{result.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
