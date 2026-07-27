"""Deterministic context compilation over real mixed text and rich corpora."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import UnicodeCharacterEstimator, Utf8ByteEstimator
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompilationCommit,
    ContextCompilationRecord,
    ContextCompileRequest,
    ContextSelectionPolicy,
    EstimatorIdentity,
)
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.storage import StoredObject
from openardp.ports.catalog import CatalogError
from openardp.ports.context import (
    ContextCompilationCancelled,
    ContextConfigurationMismatch,
    ContextIntegrityFailure,
    ContextLimitExceeded,
    ContextNotFound,
)
from openardp.ports.object_store import ObjectStoreError
from openardp.services.context_compiler import (
    ContextCompilerService,
    bundle_object_bytes,
    context_algorithm_identity,
    receipt_object_bytes,
)
from openardp.services.ingestion import IngestionService
from openardp.services.rich_ingestion import RichIngestionService
from tests.integration.test_rich_ingestion import _Clock, _Parser

TASK = "alpha evidence"
UNKNOWN_DOCUMENT_ID = UUID("01890f62-24e8-7c00-8000-00000000dead")


@dataclass(frozen=True, slots=True)
class MixedCorpus:
    """Verified mixed text/rich corpus handles for compiler integration tests."""

    compiler: ContextCompilerService
    document_ids: tuple[UUID, ...]
    store: FilesystemObjectStore
    catalog: SQLiteCatalog
    text_ingestion: IngestionService
    text_path: Path


def _mixed_corpus(tmp_path: Path) -> MixedCorpus:
    """Ingest one text and one rich document into one shared store and catalog."""
    store = FilesystemObjectStore(tmp_path / "cas")
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    clock = _Clock()
    catalog.initialize(now=clock())
    text_ingestion = IngestionService(
        store,
        catalog,
        TextParserAdapter(),
        source_factory=LocalSource,
        clock=clock,
    )
    parser = _Parser()
    parser.text = "alpha rich evidence alpha"
    rich_ingestion = RichIngestionService(
        store,
        catalog,
        parser,
        source_factory=LocalSource,
        clock=clock,
        owner_id_factory=lambda: "compiler-worker",
        lease_token_factory=lambda: "compiler-capability-000000000000001",
        random_bits=lambda: 1,
    )
    text_path = tmp_path / "doc.md"
    text_path.write_text("alpha text evidence alpha\n", encoding="utf-8")
    text_result = text_ingestion.ingest(text_path)
    rich_path = tmp_path / "source.docx"
    rich_path.write_bytes(b"source-v1")
    rich_result = rich_ingestion.ingest(rich_path)
    compiler = ContextCompilerService(
        store,
        catalog,
        Utf8ByteEstimator(),
        (
            TextLexicalCandidateSource(store, catalog),
            RichLexicalCandidateSource(
                store,
                catalog,
                representation_verifier=rich_ingestion.verify_ready_representation,
            ),
        ),
    )
    document_ids = tuple(
        sorted(
            (text_result.scope.document_id, rich_result.scope.document_id),
            key=str,
        )
    )
    return MixedCorpus(
        compiler=compiler,
        document_ids=document_ids,
        store=store,
        catalog=catalog,
        text_ingestion=text_ingestion,
        text_path=text_path,
    )


def _request(
    document_ids: tuple[UUID, ...],
    budget_limit: int,
    estimator: EstimatorIdentity | None = None,
    *,
    task: str = TASK,
) -> ContextCompileRequest:
    identity = estimator or Utf8ByteEstimator().identity
    return ContextCompileRequest(
        task=task,
        document_ids=document_ids,
        budget_limit=budget_limit,
        estimator=identity,
        policy=ContextSelectionPolicy(
            mode=ContextMode.EXACT,
            maximum_sensitivity=Sensitivity.UNKNOWN,
        ),
    )


def test_mixed_corpus_compiles_verified_bundle_and_body_free_receipt(
    tmp_path: Path,
) -> None:
    """Select reverified text and rich evidence under one deterministic budget."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids

    result = compiler.compile(_request(document_ids, 1_000_000))

    bundle = result.bundle
    receipt = result.receipt
    assert {item.provenance.record_type for item in bundle.items} == {
        "block",
        "evidence_projection",
    }
    assert receipt.corpus_snapshot == bundle.versions
    assert receipt.budget.bundle_used <= receipt.budget.bundle_ceiling
    assert receipt.budget.bundle_used == receipt.budget.bundle_ceiling - receipt.budget.remaining
    assert len(receipt.selected) == len(bundle.items)
    assert bundle.missing_evidence == ()
    assert all(item.trust.instruction_execution_allowed is False for item in bundle.items)
    repeated = compiler.compile(_request(document_ids, 1_000_000))
    assert repeated.bundle.bundle_id == bundle.bundle_id
    assert repeated.receipt.receipt_id == receipt.receipt_id


def test_snapshot_resolution_fails_closed_for_unknown_or_unready_documents(
    tmp_path: Path,
) -> None:
    """Never compile against unknown documents or documents without READY heads."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    store, catalog = corpus.store, corpus.catalog

    with pytest.raises(ContextNotFound, match="document"):
        compiler.compile(_request((UNKNOWN_DOCUMENT_ID,), 1_000_000))

    unready_path = tmp_path / "unready.docx"
    unready_path.write_bytes(b"source-unready")
    failing = _Parser()
    failing.failure = RuntimeError("synthetic parser crash")
    unready_ingestion = RichIngestionService(
        store,
        catalog,
        failing,
        source_factory=LocalSource,
        clock=_Clock(),
        owner_id_factory=lambda: "compiler-worker",
        lease_token_factory=lambda: "compiler-capability-000000000000002",
        random_bits=lambda: 1,
    )
    with pytest.raises(RuntimeError, match="synthetic parser crash"):
        unready_ingestion.ingest(unready_path)
    unready_id = next(
        document.document_id
        for document in catalog.list_documents()
        if document.document_id not in document_ids
    )

    with pytest.raises(ContextNotFound, match="ready_head"):
        compiler.compile(_request((unready_id,), 1_000_000))
    assert compiler.compile(_request(document_ids, 1_000_000)).bundle.versions


def test_estimator_identity_mismatch_is_rejected(tmp_path: Path) -> None:
    """Bind the request to the exact configured estimator identity."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids

    with pytest.raises(ContextConfigurationMismatch, match="estimator"):
        compiler.compile(_request(document_ids, 1_000_000, UnicodeCharacterEstimator().identity))


def test_exact_fit_then_one_unit_overflow_omits_the_last_item(tmp_path: Path) -> None:
    """Fit the full bundle exactly, then overflow the ceiling by one unit."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    full = compiler.compile(_request(document_ids, 1_000_000))
    used = full.receipt.budget.bundle_used
    # The limit value itself changes the canonical byte count via its digit
    # length, so the exact-fit limit is found by a bounded deterministic scan.
    exact = None
    exact_limit = 0
    for limit in range(used, used + used // 4 + 16):
        candidate = compiler.compile(_request(document_ids, limit))
        ledger = candidate.receipt.budget
        if (
            ledger.bundle_used == ledger.bundle_ceiling
            and len(candidate.receipt.selected) == len(full.receipt.selected)
            and candidate.receipt.omitted == ()
        ):
            exact = candidate
            exact_limit = limit
            break
    assert exact is not None, "no exact-fit limit found in the bounded scan"

    overflow = compiler.compile(_request(document_ids, exact_limit - 1))

    assert overflow.receipt.budget.bundle_used < exact.receipt.budget.bundle_ceiling
    assert len(overflow.receipt.selected) == len(exact.receipt.selected) - 1
    assert len(overflow.receipt.omitted) == 1
    assert overflow.receipt.omitted[0].evidence_id == exact.receipt.selected[-1].evidence_id


def test_base_bundle_over_budget_fails_closed(tmp_path: Path) -> None:
    """Refuse silent output when even the empty bundle exceeds the ceiling."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids

    with pytest.raises(ContextLimitExceeded, match="budget"):
        compiler.compile(_request(document_ids, 1024))


def test_twenty_repeats_produce_byte_identical_bundles_and_receipts(
    tmp_path: Path,
) -> None:
    """Repeat compilation twenty times without identity or byte drift."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    request = _request(document_ids, 1_000_000)

    outcomes = tuple(compiler.compile(request) for _ in range(20))

    first = outcomes[0]
    bundle_bytes = canonical_json_bytes(first.bundle.model_dump(mode="json"))
    receipt_bytes = canonical_json_bytes(first.receipt.model_dump(mode="json"))
    for result in outcomes[1:]:
        assert result.bundle.bundle_id == first.bundle.bundle_id
        assert result.receipt.receipt_id == first.receipt.receipt_id
        assert canonical_json_bytes(result.bundle.model_dump(mode="json")) == bundle_bytes
        assert canonical_json_bytes(result.receipt.model_dump(mode="json")) == receipt_bytes


def test_persisted_compilation_replays_byte_identically_five_times(tmp_path: Path) -> None:
    """Replay one persisted receipt five times with identical objects and identities."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    persisted = compiler.compile_and_persist(_request(document_ids, 1_000_000))

    replays = tuple(compiler.replay(TASK, persisted.record.receipt_id) for _ in range(5))

    stored_bundle = bundle_object_bytes(persisted.result.bundle)
    stored_receipt = receipt_object_bytes(persisted.result.receipt)
    for result in replays:
        assert result == persisted.result
        assert bundle_object_bytes(result.bundle) == stored_bundle
        assert receipt_object_bytes(result.receipt) == stored_receipt
    assert len(corpus.catalog.list_context_compilations()) == 1


def test_replay_stays_pinned_after_newer_head_is_committed(tmp_path: Path) -> None:
    """Use the recorded exact snapshot even after the head advanced."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    persisted = compiler.compile_and_persist(_request(document_ids, 1_000_000))
    corpus.text_path.write_text(
        "alpha text evidence alpha\n\nnewer beta paragraph\n",
        encoding="utf-8",
    )
    advanced = corpus.text_ingestion.ingest(corpus.text_path)
    head = corpus.catalog.get_document_head(advanced.scope.document_id)
    assert head is not None
    assert head.scope.version_id == advanced.scope.version_id
    recorded_versions = {scope.version_id for scope in persisted.result.receipt.corpus_snapshot}
    assert advanced.scope.version_id not in recorded_versions

    replayed = compiler.replay(TASK, persisted.record.receipt_id)

    assert replayed == persisted.result
    assert replayed.receipt.corpus_snapshot == persisted.result.receipt.corpus_snapshot
    fresh = compiler.compile(_request(document_ids, 1_000_000))
    assert fresh.receipt.receipt_id != persisted.result.receipt.receipt_id
    assert fresh.receipt.corpus_snapshot != persisted.result.receipt.corpus_snapshot


def test_replay_rejects_task_estimator_and_algorithm_mismatch(tmp_path: Path) -> None:
    """Fail replay with one stable mismatch category and no substitute result."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    persisted = compiler.compile_and_persist(_request(document_ids, 1_000_000))
    receipt_id = persisted.record.receipt_id

    with pytest.raises(ContextConfigurationMismatch, match="task"):
        compiler.replay("completely different task", receipt_id)

    mismatched_estimator = ContextCompilerService(
        corpus.store,
        corpus.catalog,
        UnicodeCharacterEstimator(),
        (),
    )
    with pytest.raises(ContextConfigurationMismatch, match="estimator"):
        mismatched_estimator.replay(TASK, receipt_id)

    foreign_algorithm = ContextCompilerService(
        corpus.store,
        corpus.catalog,
        Utf8ByteEstimator(),
        (),
        algorithm=context_algorithm_identity().model_copy(
            update={"version": "0.0.0"},
        ),
    )
    with pytest.raises(ContextConfigurationMismatch, match="algorithm"):
        foreign_algorithm.replay(TASK, receipt_id)

    assert compiler.replay(TASK, receipt_id) == persisted.result


class _FlipAfterPublishStore:
    """Delegate store that reports once the first object was published."""

    def __init__(self, inner: FilesystemObjectStore) -> None:
        self._inner = inner
        self.published = False

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        self.published = True
        return self._inner.put_chunks(chunks)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _FailingPublishStore:
    """Delegate store whose publication always fails with a store fault."""

    def __init__(self, inner: FilesystemObjectStore) -> None:
        self._inner = inner

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        raise ObjectStoreError("synthetic publish fault")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _FailOnceCommitCatalog:
    """Delegate catalog that fails the first compilation commit only."""

    def __init__(self, inner: SQLiteCatalog) -> None:
        self._inner = inner
        self.failures = 1

    def commit_context_compilation(
        self,
        commit: ContextCompilationCommit,
    ) -> ContextCompilationRecord:
        if self.failures:
            self.failures -= 1
            raise CatalogError("synthetic commit fault")
        return self._inner.commit_context_compilation(commit)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_cancellation_at_bounded_phases_leaves_no_partial_state(tmp_path: Path) -> None:
    """Cancel before retrieval, during verification and post-CAS pre-commit."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    request = _request(document_ids, 1_000_000)

    with pytest.raises(ContextCompilationCancelled, match="cancelled_before_snapshot"):
        compiler.compile(request, cancel=lambda: True)

    checks = iter((False, False, True))
    with pytest.raises(ContextCompilationCancelled, match="cancelled"):
        compiler.compile(request, cancel=lambda: next(checks, True))
    assert corpus.catalog.list_context_compilations() == ()

    flipping = _FlipAfterPublishStore(corpus.store)
    persisting = ContextCompilerService(
        flipping,
        corpus.catalog,
        Utf8ByteEstimator(),
        (
            TextLexicalCandidateSource(flipping, corpus.catalog),
            RichLexicalCandidateSource(
                flipping,
                corpus.catalog,
                representation_verifier=lambda artifacts: None,
            ),
        ),
    )
    with pytest.raises(ContextCompilationCancelled, match="cancelled_before_commit"):
        persisting.compile_and_persist(request, cancel=lambda: flipping.published)

    # No catalog-visible compilation; the pre-published immutable objects stay
    # behind only as unreachable recovery candidates.
    assert corpus.catalog.list_context_compilations() == ()
    expected = compiler.compile(request)
    recovered = corpus.store.verify(expected.receipt.receipt_id)
    assert recovered.object_id == expected.receipt.receipt_id

    # A retry after cancellation converges on the identical compilation.
    persisted = persisting.compile_and_persist(request)
    assert persisted.result == expected
    assert len(corpus.catalog.list_context_compilations()) == 1


def test_publish_and_commit_faults_retry_to_identical_identities(tmp_path: Path) -> None:
    """Expose no partial compilation across publish/commit faults and retries."""
    corpus = _mixed_corpus(tmp_path)
    document_ids = corpus.document_ids
    request = _request(document_ids, 1_000_000)
    expected = corpus.compiler.compile(request)

    failing_store = _FailingPublishStore(corpus.store)
    failing = ContextCompilerService(
        failing_store,
        corpus.catalog,
        Utf8ByteEstimator(),
        (),
    )
    with pytest.raises(ContextIntegrityFailure, match="publication"):
        failing.compile_and_persist(request)
    assert corpus.catalog.list_context_compilations() == ()

    persisted = corpus.compiler.compile_and_persist(request)
    assert persisted.result.receipt.receipt_id == expected.receipt.receipt_id
    assert persisted.result.bundle.bundle_id == expected.bundle.bundle_id

    # A commit fault after successful publication rolls back atomically; the
    # retry converges and the prior compilation stays byte-identical.
    other_request = _request(document_ids, 900_000)
    flaky_catalog = _FailOnceCommitCatalog(corpus.catalog)
    flaky = ContextCompilerService(
        corpus.store,
        flaky_catalog,
        Utf8ByteEstimator(),
        (
            TextLexicalCandidateSource(corpus.store, flaky_catalog),
            RichLexicalCandidateSource(
                corpus.store,
                flaky_catalog,
                representation_verifier=lambda artifacts: None,
            ),
        ),
    )
    with pytest.raises(ContextIntegrityFailure, match="commit"):
        flaky.compile_and_persist(other_request)
    assert [record.receipt_id for record in corpus.catalog.list_context_compilations()] == [
        persisted.record.receipt_id
    ]
    assert corpus.compiler.load_verified(persisted.record.receipt_id) == persisted.result

    retried = flaky.compile_and_persist(other_request)
    assert retried.result.receipt.receipt_id != persisted.record.receipt_id
    assert len(corpus.catalog.list_context_compilations()) == 2
    assert corpus.compiler.load_verified(persisted.record.receipt_id) == persisted.result

    # Concurrent duplicate commits converge on one immutable record.
    again = corpus.compiler.compile_and_persist(request)
    assert again.record == persisted.record
    assert len(corpus.catalog.list_context_compilations()) == 2
