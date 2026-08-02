"""Materialize the F022 reference workload with a pinned legacy runtime."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openardp.adapters.context_candidates import TextLexicalCandidateSource
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.adapters.product_benchmarks import (
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
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.search import SearchService

BENCHMARK_NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


class _DeterministicClock:
    """Return a reproducible strictly increasing UTC sequence."""

    def __init__(self, start: datetime) -> None:
        self._next = start

    def __call__(self) -> datetime:
        value = self._next
        self._next += timedelta(microseconds=1)
        return value


def main() -> int:
    """Create a populated revision-10 workspace and body-free handoff facts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    arguments = parser.parse_args()
    root = arguments.root
    inputs = load_benchmark_inputs(arguments.repository_root / "benchmarks/product-value/v0.1.0")
    corpus = generate_text_corpus(inputs, BenchmarkProfile.REFERENCE, root / "corpus")
    workspace = LocalWorkspace.initialize(root / "workspace", now=BENCHMARK_NOW)
    clock = _DeterministicClock(BENCHMARK_NOW + timedelta(seconds=1))
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
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
    )
    search = SearchService(workspace.object_store, workspace.catalog, source_factory=LocalSource)
    context = ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        Utf8ByteEstimator(),
        (TextLexicalCandidateSource(workspace.object_store, workspace.catalog),),
    )
    ingested = ingestion.ingest(corpus.source)
    for ordinal in inputs.corpus.profiles[BenchmarkProfile.REFERENCE].query_ordinals:
        token = corpus_token(inputs.corpus.seed, ordinal)
        hit = search.search(f'"{token}"')
        if hit.returned != 1 or hit.hits[0].line_start != ordinal * 2 + 1:
            raise ValueError("legacy search correctness failed")
    task = corpus_token(
        inputs.corpus.seed,
        inputs.corpus.profiles[BenchmarkProfile.REFERENCE].query_ordinals[0],
    )
    persisted = context.compile_and_persist(
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
    original = corpus.source.read_bytes()
    edit_ordinal = inputs.corpus.profiles[BenchmarkProfile.REFERENCE].query_ordinals[-1]
    old_token = corpus_token(inputs.corpus.seed, edit_ordinal)
    replacement_marker = "replacement-legacy-storage"
    corpus.source.write_bytes(original.replace(old_token.encode(), replacement_marker.encode(), 1))
    if query.status(str(corpus.source)).freshness is not SourceFreshness.SOURCE_CHANGED:
        raise ValueError("legacy edit freshness failed")
    changed = ingestion.ingest(corpus.source)
    corpus.source.write_bytes(original)
    if query.status(str(corpus.source)).freshness is not SourceFreshness.SOURCE_CHANGED:
        raise ValueError("legacy revert freshness failed")
    reverted = ingestion.ingest(corpus.source)
    if reverted.scope != ingested.scope or not reverted.cache_hit or reverted.parser_invoked:
        raise ValueError("legacy revert reuse failed")
    facts = {
        "changed_version_id": changed.scope.version_id,
        "document_id": str(ingested.scope.document_id),
        "receipt_id": persisted.record.receipt_id,
        "task": task,
        "version_id": ingested.scope.version_id,
    }
    (root / "legacy-facts.json").write_bytes(canonical_json_bytes(facts) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
