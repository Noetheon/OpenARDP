"""Offline prepared semantic reuse through real MCP request dispatch."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

import openardp.interfaces.mcp_server as mcp_module
import openardp.services.context_compiler as compiler_module
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.context_compilation import EstimatorIdentity
from openardp.domain.evidence import EvidenceProjection
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.semantic_retrieval import (
    PreparedSemanticCorpus,
    SemanticPassage,
    SemanticRetrievalLimits,
    SemanticScore,
)
from openardp.interfaces.context_composition import (
    RetrievalProfile,
    local_context_compiler_for_profile,
)
from openardp.interfaces.mcp_protocol import RequestDeadline, SessionLimits
from openardp.ports.context import CancellationCheck, ContextCompilationCancelled, ContextEstimator
from openardp.ports.semantic_retrieval import (
    SemanticProviderInvalid,
    SemanticProviderTimedOut,
    SemanticProviderUnavailable,
)
from openardp.services.context_compiler import ContextCompilerService
from tests.integration.test_mcp_semantic_context import _CachingProvider
from tests.integration.test_mcp_server import (
    RICH_BODY,
    _call_tool,
    _compile_arguments,
    _Corpus,
    _error,
    _result,
    _server,
)


class _PreparedProvider(_CachingProvider):
    """Expose preparation counts and a single disposable model-free handle."""

    def __init__(self) -> None:
        super().__init__()
        self.preparations = 0
        self.passages: tuple[SemanticPassage, ...] = ()
        self.failure: Exception | None = None

    def prepare(
        self,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> PreparedSemanticCorpus:
        """Replace the active corpus and report exact preparation counts."""
        assert not cancel()
        self.preparations += 1
        self.passages = passages
        return PreparedSemanticCorpus.from_passages(self.recipe.recipe_id, passages, limits)

    def score_prepared(
        self,
        query: str,
        corpus: PreparedSemanticCorpus,
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> tuple[SemanticScore, ...]:
        """Score the active corpus or expose one requested worker failure."""
        if self.failure is not None:
            failure, self.failure = self.failure, None
            self.passages = ()
            raise failure
        assert corpus == PreparedSemanticCorpus.from_passages(
            self.recipe.recipe_id, self.passages, limits
        )
        return self.score(query, self.passages, limits, cancel)


class _PreparedFactory:
    """Compose the real current product profile and count compiler lifetimes."""

    def __init__(self, corpus: _Corpus) -> None:
        self.corpus = corpus
        self.provider = _PreparedProvider()
        self.identities: list[EstimatorIdentity] = []

    def __call__(self, estimator: ContextEstimator) -> ContextCompilerService:
        """Build the ordinary product compiler with the offline prepared provider."""
        self.identities.append(estimator.identity)
        workspace = cast(
            LocalWorkspace,
            SimpleNamespace(
                object_store=self.corpus.object_store,
                catalog=self.corpus.catalog,
            ),
        )
        return local_context_compiler_for_profile(
            workspace,
            estimator,
            self.corpus.text_ingestion.verify_ready_representation,
            self.corpus._rich_verifier,
            RetrievalProfile.SEMANTIC,
            provider=self.provider,
        )


def _semantic_arguments(corpus: _Corpus, **overrides: object) -> dict[str, object]:
    return _compile_arguments(
        corpus, retrieval_profile="semantic", include_bundle=True, **overrides
    )


def _assert_private_failure(envelope: dict[str, object], corpus: _Corpus) -> str:
    result = envelope.get("result")
    assert result is None or (isinstance(result, dict) and result.get("isError") is True)
    encoded = json.dumps(envelope)
    for forbidden in (RICH_BODY, "alpha text evidence", str(corpus.store), "PRIVATE-DETAIL"):
        assert forbidden not in encoded
    return str(_error(envelope)["data"]["category"])


def test_prepared_mcp_reuses_compiler_across_lexical_and_matches_fresh_results(
    tmp_path: Path,
) -> None:
    """Reuse one exact snapshot while lexical interleaving preserves cold-result parity."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    server = _server(corpus, semantic_compiler_factory=factory)
    first = _result(_call_tool(server, "compile_context", _semantic_arguments(corpus)))
    lexical = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    assert lexical["counts"]["selected"] > 0
    repeated = _result(_call_tool(server, "compile_context", _semantic_arguments(corpus)))
    changed_task = _semantic_arguments(corpus, task="rich evidence")
    second = _result(_call_tool(server, "compile_context", changed_task))
    assert first == repeated
    assert factory.provider.preparations == 1
    assert factory.provider.requests == 3
    assert len(factory.identities) == 1
    # Keep provider diagnostics comparable: only the compiler is fresh, as before F037.
    fresh_factory = _PreparedFactory(corpus)
    fresh_factory.provider = factory.provider
    fresh = _server(corpus, semantic_compiler_factory=fresh_factory)
    expected = _result(_call_tool(fresh, "compile_context", changed_task))
    assert second == expected


@pytest.mark.parametrize("unit", ["characters", "tokens"])
def test_prepared_mcp_estimator_switch_replaces_the_single_slot(tmp_path: Path, unit: str) -> None:
    """A to B to A must prepare three times and retain only the current compiler."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    server = _server(corpus, semantic_compiler_factory=factory)
    for selected in ("bytes", unit, "bytes", "bytes"):
        _result(_call_tool(server, "compile_context", _semantic_arguments(corpus, unit=selected)))
    assert [identity.unit.value for identity in factory.identities] == ["bytes", unit, "bytes"]
    assert factory.provider.preparations == 3


@pytest.mark.parametrize(
    "changed",
    [{"name": "fixture.bytes"}, {"version": "1.0.1"}, {"config_hash": "sha256:" + "a" * 64}],
)
def test_prepared_mcp_slot_compares_the_complete_estimator_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: dict[str, str]
) -> None:
    """Even same-unit estimators with different names, versions or configs cannot share."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    first = Utf8ByteEstimator()

    class DifferentIdentity(Utf8ByteEstimator):
        @property
        def identity(self) -> EstimatorIdentity:
            return first.identity.model_copy(update=changed)

    second = DifferentIdentity()
    selected = [first]
    # Install the identical byte measurement under a synthetic identity only in this test.
    monkeypatch.setattr(compiler_module, "BUILT_IN_ESTIMATORS", (first, second))
    monkeypatch.setattr(mcp_module, "_estimator_for_unit", lambda _unit: selected[0])
    server = _server(corpus, semantic_compiler_factory=factory)
    for estimator in (first, second, first, first):
        selected[0] = estimator
        _result(_call_tool(server, "compile_context", _semantic_arguments(corpus)))
    assert factory.identities == [first.identity, second.identity, first.identity]
    assert factory.provider.preparations == 3


def test_prepared_mcp_scope_switch_reprepares_without_new_compiler(tmp_path: Path) -> None:
    """A to B to A document selections invalidate preparation within the same compiler."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    server = _server(corpus, semantic_compiler_factory=factory)
    for document_id in (
        corpus.text_document_id,
        corpus.rich_document_id,
        corpus.text_document_id,
        corpus.text_document_id,
    ):
        _result(
            _call_tool(
                server,
                "compile_context",
                _semantic_arguments(corpus, document_ids=[str(document_id)]),
            )
        )
    assert factory.provider.preparations == 3
    assert len(factory.identities) == 1


def test_unrelated_failed_requests_preserve_prepared_semantic_state(tmp_path: Path) -> None:
    """Unknown tools and failed lexical calls cannot evict semantic preparation."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    server = _server(corpus, semantic_compiler_factory=factory)
    arguments = _semantic_arguments(corpus)
    first = _result(_call_tool(server, "compile_context", arguments))
    assert _error(_call_tool(server, "unknown"))["data"]["category"] == "unknown_tool"
    assert (
        _error(_call_tool(server, "compile_context", _compile_arguments(corpus, document_ids=[])))[
            "data"
        ]["category"]
        == "invalid_params"
    )
    assert _result(_call_tool(server, "compile_context", arguments)) == first
    assert factory.provider.preparations == 1
    assert len(factory.identities) == 1


@pytest.mark.parametrize(
    ("failure_type", "category"),
    [
        (ContextCompilationCancelled, "cancelled"),
        (SemanticProviderInvalid, "integrity_or_workspace"),
        (SemanticProviderTimedOut, "internal"),
        (SemanticProviderUnavailable, "internal"),
    ],
)
def test_prepared_mcp_failure_evicts_warm_state_and_recovers(
    tmp_path: Path, failure_type: type[Exception], category: str
) -> None:
    """A worker failure cannot leave a live compiler referring to lost preparation."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    server = _server(corpus, semantic_compiler_factory=factory)
    arguments = _semantic_arguments(corpus)
    first = _result(_call_tool(server, "compile_context", arguments))
    factory.provider.failure = failure_type("PRIVATE-DETAIL /private/provider")
    failed = _call_tool(server, "compile_context", arguments)
    assert _assert_private_failure(failed, corpus) == category
    assert _result(_call_tool(server, "compile_context", arguments)) == first
    assert _result(_call_tool(server, "compile_context", arguments)) == first
    assert len(factory.identities) == 2
    assert factory.provider.preparations == 2


@pytest.mark.parametrize("failure", ["deadline", "cancellation", "response_cap"])
def test_rejected_semantic_delivery_evicts_after_successful_compilation(
    tmp_path: Path, failure: str
) -> None:
    """Late protocol rejection also drops the compiler before a subsequent request."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    now = [1_000.0]
    server = _server(corpus, semantic_compiler_factory=factory, clock=lambda: now[0])
    arguments = _semantic_arguments(corpus)
    first = _result(_call_tool(server, "compile_context", arguments))
    original = server._dispatch["compile_context"]

    def reject_delivery(
        arguments: dict[str, object], deadline: RequestDeadline, cancel: CancellationCheck
    ) -> dict[str, object]:
        result = original(arguments, deadline, cancel)  # type: ignore[arg-type]
        if failure == "deadline":
            now[0] += 31
        elif failure == "cancellation":
            server._registry.cancel(10)
        else:
            # A tiny test-only cap deterministically exercises final response encoding.
            server._limits = SessionLimits.model_construct(response_cap_bytes=1)
        return result

    server._dispatch["compile_context"] = reject_delivery  # type: ignore[assignment]
    failed = _call_tool(server, "compile_context", arguments)
    expected = {"deadline": "deadline_exceeded", "cancellation": "cancelled"}
    assert _assert_private_failure(failed, corpus) == expected.get(failure, "invalid_params")
    server._dispatch["compile_context"] = original
    server._limits = SessionLimits()
    assert _result(_call_tool(server, "compile_context", arguments)) == first
    assert len(factory.identities) == 2
    assert factory.provider.preparations == 2


@pytest.mark.parametrize("tamper", ["body", "reference", "trust_projection"])
def test_warm_semantic_mcp_rejects_cas_and_catalog_authority_tampering(
    tmp_path: Path, tamper: str
) -> None:
    """Warm preparations cannot deliver stale bytes or cached trust/reference mappings."""
    corpus = _Corpus(tmp_path)
    factory = _PreparedFactory(corpus)
    server = _server(corpus, semantic_compiler_factory=factory)
    arguments = _semantic_arguments(corpus, document_ids=[str(corpus.rich_document_id)])
    first = _result(_call_tool(server, "compile_context", arguments))
    assert _result(_call_tool(server, "compile_context", arguments)) == first
    assert factory.provider.preparations == 1
    with sqlite3.connect(corpus.catalog.path) as connection:
        row = connection.execute(
            "SELECT reference_object_id, projection_object_id, retrieval_object_id "
            "FROM rich_attempt_evidence WHERE ordinal = ?",
            (0,),
        ).fetchone()
        assert row is not None
        reference, projection, retrieval = row
        if tamper == "reference":
            connection.execute(
                "UPDATE rich_attempt_evidence SET reference_object_id = ? WHERE ordinal = ?",
                (retrieval, 0),
            )
        elif tamper == "trust_projection":
            payload = json.loads(corpus.object_store._path_for_id(projection).read_bytes())
            payload["trust"]["sensitivity"] = (
                "public" if payload["trust"]["sensitivity"] != "public" else "restricted"
            )
            # Keep the projection and evidence identity structurally valid, changing only trust.
            projection_bytes = canonical_json_bytes(payload)
            EvidenceProjection.model_validate_json(projection_bytes)
            forged = corpus.object_store.put_chunks((projection_bytes,))
            connection.execute(
                "INSERT INTO objects(object_id, byte_length, registered_at) "
                "SELECT ?, ?, registered_at FROM objects WHERE object_id = ?",
                (forged.object_id, forged.byte_length, projection),
            )
            connection.execute(
                "UPDATE rich_attempt_evidence SET projection_object_id = ? WHERE ordinal = ?",
                (forged.object_id, 0),
            )
    body_path = corpus.object_store._path_for_id(retrieval)
    original_body = body_path.read_bytes()
    if tamper == "body":
        body_path.write_bytes(b"PRIVATE-DETAIL tampered source")

    failed = _call_tool(server, "compile_context", arguments)
    assert _assert_private_failure(failed, corpus) == "integrity_or_workspace"
    body_path.write_bytes(original_body)
    with sqlite3.connect(corpus.catalog.path) as connection:
        connection.execute(
            "UPDATE rich_attempt_evidence SET reference_object_id = ?, projection_object_id = ? "
            "WHERE ordinal = ?",
            (reference, projection, 0),
        )
    assert _result(_call_tool(server, "compile_context", arguments)) == first
    assert len(factory.identities) == 2
    assert factory.provider.preparations == 2
