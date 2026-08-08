"""Process-authorized semantic MCP context integration tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.semantic_retrieval import (
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticScore,
)
from openardp.interfaces.context_composition import local_semantic_context_compiler
from openardp.ports.context import (
    CancellationCheck,
    ContextCompilationCancelled,
    ContextEstimator,
)
from openardp.services.context_compiler import ContextCompilerService
from tests.integration.test_mcp_server import (
    _call_tool,
    _compile_arguments,
    _Corpus,
    _error,
    _result,
    _server,
)


class _CachingProvider:
    """Deterministic provider that exposes same-process cache reuse."""

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.requests = 0
        self.recipe = SemanticProviderRecipe(
            provider="fake-mcp-semantic",
            provider_version="1.0.0",
            model_id="example/model",
            model_revision="1" * 40,
            model_bundle_id="sha256:" + "2" * 64,
            dimensions=3,
            max_tokens=32,
            query_prefix="query: ",
            passage_prefix="passage: ",
            pooling="mean_attention_mask",
            normalization="l2",
            similarity="cosine",
            quantizer="half_away_from_zero_millionths_v1",
            transformers_version="4.55.0",
            torch_version="2.8.0",
        )

    def score(
        self,
        query: str,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> tuple[SemanticScore, ...]:
        """Return eligible scores and mark repeated object identities as hits."""
        del query, limits
        assert not cancel()
        self.requests += 1
        scores = tuple(
            SemanticScore(
                evidence_id=passage.evidence_id,
                object_id=passage.object_id,
                provider_recipe_id=self.recipe.recipe_id,
                score_millionths=900_000,
                cache_hit=passage.object_id in self.seen,
            )
            for passage in passages
        )
        self.seen.update(passage.object_id for passage in passages)
        return scores

    def close(self) -> None:
        """Satisfy the provider lifecycle contract for composition tests."""


def _semantic_factory(
    corpus: _Corpus,
    provider: _CachingProvider,
) -> Callable[[ContextEstimator], ContextCompilerService]:
    workspace = cast(
        LocalWorkspace,
        SimpleNamespace(object_store=corpus.object_store, catalog=corpus.catalog),
    )

    def factory(estimator: ContextEstimator) -> ContextCompilerService:
        return local_semantic_context_compiler(
            workspace,
            estimator,
            corpus.text_ingestion.verify_ready_representation,
            corpus._rich_verifier,
            provider,
        )

    return factory


def test_unconfigured_server_rejects_semantic_without_lexical_fallback(tmp_path: Path) -> None:
    """Reject unavailable capability and remain usable for lexical requests."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    unavailable = _call_tool(
        server,
        "compile_context",
        _compile_arguments(corpus, retrieval_profile="semantic"),
    )
    assert _error(unavailable)["data"]["category"] == "invalid_params"
    lexical = _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))
    assert lexical["counts"]["selected"] >= 1


def test_configured_server_selects_semantic_and_reuses_one_provider(tmp_path: Path) -> None:
    """Serve lexical and repeated semantic requests through one provider lifecycle."""
    corpus = _Corpus(tmp_path)
    provider = _CachingProvider()
    server = _server(corpus, semantic_compiler_factory=_semantic_factory(corpus, provider))
    lexical = _result(
        _call_tool(
            server,
            "compile_context",
            _compile_arguments(corpus, retrieval_profile="lexical"),
        )
    )
    first = _result(
        _call_tool(
            server,
            "compile_context",
            _compile_arguments(corpus, retrieval_profile="semantic"),
        )
    )
    second = _result(
        _call_tool(
            server,
            "compile_context",
            _compile_arguments(corpus, retrieval_profile="semantic"),
        )
    )
    assert lexical["counts"]["selected"] >= 1
    assert first == second
    assert provider.requests == 2
    assert provider.seen


def test_mcp_contract_rejects_profile_paths_and_unknown_values(tmp_path: Path) -> None:
    """Keep all model/path authority outside client-controlled tool input."""
    corpus = _Corpus(tmp_path)
    server = _server(corpus)
    for overrides in (
        {"retrieval_profile": "unknown"},
        {"semantic_bundle": "/host/path"},
        {"provider": "fake"},
    ):
        envelope = _call_tool(server, "compile_context", _compile_arguments(corpus, **overrides))
        assert _error(envelope)["data"]["category"] == "invalid_params"


def test_semantic_cancellation_is_distinct_and_lexical_session_remains_usable(
    tmp_path: Path,
) -> None:
    """Preserve cooperative cancellation semantics after selecting the optional profile."""
    corpus = _Corpus(tmp_path)

    class CancelledCompiler:
        def compile_and_persist(self, _request: object, *, cancel: object) -> None:
            del cancel
            raise ContextCompilationCancelled("provider stopped")

    server = _server(
        corpus,
        semantic_compiler_factory=lambda _estimator: cast(
            ContextCompilerService,
            CancelledCompiler(),
        ),
    )
    cancelled = _call_tool(
        server,
        "compile_context",
        _compile_arguments(corpus, retrieval_profile="semantic"),
    )
    assert _error(cancelled)["data"]["category"] == "cancelled"
    assert (
        _result(_call_tool(server, "compile_context", _compile_arguments(corpus)))["counts"][
            "selected"
        ]
        >= 1
    )
