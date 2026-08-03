"""Ranked context compiler integration and replay tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.context_compilation import AlgorithmIdentity
from openardp.domain.context_ranking import LexicalAllocationPolicy
from openardp.domain.context_relevance import RelevancePolicy
from openardp.interfaces.context_composition import local_context_compiler_for_algorithm
from openardp.ports.context import ContextConfigurationMismatch
from openardp.services.context_compiler import ContextCompilerService, context_algorithm_identity
from tests.integration.test_context_compiler import _mixed_corpus, _request


def _compiler(tmp_path: Path) -> tuple[ContextCompilerService, object]:
    corpus = _mixed_corpus(tmp_path)
    relevance = RelevancePolicy()
    lexical = (
        TextLexicalCandidateSource(corpus.store, corpus.catalog),
        RichLexicalCandidateSource(
            corpus.store,
            corpus.catalog,
            representation_verifier=lambda _artifacts: None,
        ),
    )
    compiler = ContextCompilerService(
        corpus.store,
        corpus.catalog,
        Utf8ByteEstimator(),
        (RelevanceObservingCandidateSource(corpus.store, lexical, relevance),),
        relevance_policy=relevance,
        allocation_policy=LexicalAllocationPolicy(),
    )
    return compiler, corpus


def test_ranked_compilation_is_deterministic_and_binds_combined_identity(tmp_path: Path) -> None:
    """Repeated execution preserves selected ordering and exact algorithm facts."""
    compiler, corpus = _compiler(tmp_path)
    request = _request(corpus.document_ids, 1_000_000, task="alpha evidence")

    first = compiler.compile(request)
    second = compiler.compile(request)

    assert first == second
    assert first.receipt.algorithm == context_algorithm_identity(
        RelevancePolicy(), LexicalAllocationPolicy()
    )
    assert len({decision.scope.document_id for decision in first.receipt.selected}) == 2


def test_ranked_receipt_replays_and_relevance_only_profile_fails_closed(tmp_path: Path) -> None:
    """Persisted ranked allocation cannot replay through a different policy profile."""
    compiler, corpus = _compiler(tmp_path)
    task = "alpha evidence"
    persisted = compiler.compile_and_persist(_request(corpus.document_ids, 1_000_000, task=task))

    replayed = compiler.replay(task, persisted.record.receipt_id)
    assert replayed == persisted.result

    relevance_only = ContextCompilerService(
        corpus.store,
        corpus.catalog,
        Utf8ByteEstimator(),
        (),
        relevance_policy=RelevancePolicy(),
    )
    with pytest.raises(ContextConfigurationMismatch, match="algorithm"):
        relevance_only.replay(task, persisted.record.receipt_id)


@pytest.mark.parametrize(
    "algorithm",
    (
        context_algorithm_identity(),
        context_algorithm_identity(RelevancePolicy()),
        context_algorithm_identity(RelevancePolicy(), LexicalAllocationPolicy()),
    ),
)
def test_local_replay_composition_selects_each_recorded_builtin_profile(
    tmp_path: Path,
    algorithm: AlgorithmIdentity,
) -> None:
    """Legacy, F026 and F027 receipts each resolve to their exact built-in compiler."""
    workspace = LocalWorkspace.initialize(
        tmp_path / algorithm.name,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )

    compiler = local_context_compiler_for_algorithm(
        workspace,
        Utf8ByteEstimator(),
        lambda _artifacts: None,
        algorithm,
    )

    assert compiler._algorithm == algorithm


def test_local_replay_composition_rejects_unknown_algorithm(tmp_path: Path) -> None:
    """An unrecognized persisted identity cannot silently select the current profile."""
    workspace = LocalWorkspace.initialize(
        tmp_path / "unknown",
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    unknown = AlgorithmIdentity(
        name="unknown.context",
        version="1.0.0",
        config_hash="sha256:" + "f" * 64,
    )

    with pytest.raises(ContextConfigurationMismatch, match="algorithm"):
        local_context_compiler_for_algorithm(
            workspace,
            Utf8ByteEstimator(),
            lambda _artifacts: None,
            unknown,
        )
