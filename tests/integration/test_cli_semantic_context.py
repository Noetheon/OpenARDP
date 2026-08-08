"""Opt-in CLI semantic context and exact replay integration tests."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

import openardp.interfaces.cli as cli
from openardp.domain.semantic_retrieval import (
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticScore,
)
from openardp.ports.context import CancellationCheck
from tests.integration.test_cli_context import _invoke_json, _WorkspaceCorpus


class _FakeProvider:
    """Deterministic model-free provider with observable lifecycle."""

    def __init__(self, *, revision: str = "1" * 40) -> None:
        self.closed = False
        self.recipe = SemanticProviderRecipe(
            provider="fake-semantic",
            provider_version="1.0.0",
            model_id="example/model",
            model_revision=revision,
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
        """Return one eligible fixed score for every exact passage."""
        del query, limits
        assert not cancel()
        return tuple(
            SemanticScore(
                evidence_id=passage.evidence_id,
                object_id=passage.object_id,
                provider_recipe_id=self.recipe.recipe_id,
                score_millionths=900_000,
                cache_hit=False,
            )
            for passage in passages
        )

    def close(self) -> None:
        """Record exact ownership release."""
        self.closed = True


def _semantic_arguments(corpus: _WorkspaceCorpus) -> list[str]:
    return [
        *corpus.context_arguments(),
        "--retrieval-profile",
        "semantic",
        "--semantic-bundle",
        "/not/read/fake-bundle",
        "--semantic-source-lock",
        "/not/read/fake-lock.json",
    ]


def test_cli_semantic_compile_is_explicit_body_free_and_closes_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compile through the exact F029 profile and release provider state."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    providers: list[_FakeProvider] = []

    def open_provider(_configuration: tuple[Path, Path]) -> _FakeProvider:
        provider = _FakeProvider()
        providers.append(provider)
        return provider

    monkeypatch.setattr(cli, "_open_semantic_provider", open_provider)
    code, payload, stderr = _invoke_json(capsys, _semantic_arguments(corpus))
    assert code == 0 and stderr == ""
    assert payload["ok"] is True
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["counts"]["selected"] >= 1  # type: ignore[index]
    assert providers and all(provider.closed for provider in providers)
    assert "fake-bundle" not in str(payload)
    assert "alpha text evidence" not in str(payload)


def test_cli_lexical_default_and_explicit_profile_are_identical(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Keep omission exactly equivalent to explicit lexical selection."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    default_code, default, _ = _invoke_json(capsys, corpus.context_arguments())
    explicit_code, explicit, _ = _invoke_json(
        capsys,
        [*corpus.context_arguments(), "--retrieval-profile", "lexical"],
    )
    assert default_code == explicit_code == 0
    assert default["data"] == explicit["data"]


@pytest.mark.parametrize(
    "extra",
    (
        ("--retrieval-profile", "semantic"),
        ("--semantic-bundle", "/bundle"),
        ("--semantic-source-lock", "/lock"),
        (
            "--retrieval-profile",
            "lexical",
            "--semantic-bundle",
            "/bundle",
            "--semantic-source-lock",
            "/lock",
        ),
    ),
)
def test_cli_rejects_incomplete_or_lexical_semantic_configuration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    extra: tuple[str, ...],
) -> None:
    """Reject every configuration that could make profile selection ambiguous."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    code, payload, stderr = _invoke_json(capsys, [*corpus.context_arguments(), *extra])
    assert code == 2 and stderr == ""
    assert payload["error"] == {
        "code": "invalid_usage",
        "message": "command usage is invalid",
    }
    assert "/bundle" not in str(payload)


def test_cli_semantic_replay_requires_exact_provider_recipe(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replay with the exact recipe and reject drift before returning evidence."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    revision = ["1" * 40]

    def open_provider(_configuration: tuple[Path, Path]) -> _FakeProvider:
        return _FakeProvider(revision=revision[0])

    monkeypatch.setattr(cli, "_open_semantic_provider", open_provider)
    code, payload, _ = _invoke_json(capsys, _semantic_arguments(corpus))
    assert code == 0
    data = payload["data"]
    assert isinstance(data, dict)
    receipt_id = str(data["receipt_id"])
    replay = [
        "context",
        "alpha evidence",
        "--replay",
        receipt_id,
        "--semantic-bundle",
        "/bundle",
        "--semantic-source-lock",
        "/lock",
        "--store",
        str(corpus.store),
    ]
    replay_code, replayed, _ = _invoke_json(capsys, replay)
    assert replay_code == 0
    assert replayed["data"]["replayed"] is True  # type: ignore[index]
    revision[0] = "9" * 40
    drift_code, drifted, _ = _invoke_json(capsys, replay)
    assert drift_code == 5
    assert drifted["error"] == {
        "code": "conflict",
        "message": "operation conflicts with current state",
    }


def test_cli_semantic_replay_rejects_missing_or_explicit_lexical_profile(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require capability configuration and reject explicit profile disagreement."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    monkeypatch.setattr(cli, "_open_semantic_provider", lambda _config: _FakeProvider())
    code, payload, _ = _invoke_json(capsys, _semantic_arguments(corpus))
    assert code == 0
    receipt_id = str(payload["data"]["receipt_id"])  # type: ignore[index]
    base = [
        "context",
        "alpha evidence",
        "--replay",
        receipt_id,
        "--store",
        str(corpus.store),
    ]
    missing_code, missing, _ = _invoke_json(capsys, base)
    assert missing_code == 2 and missing["error"]["code"] == "invalid_usage"  # type: ignore[index]
    mismatch_code, mismatch, _ = _invoke_json(
        capsys,
        [
            *base,
            "--retrieval-profile",
            "lexical",
            "--semantic-bundle",
            "/bundle",
            "--semantic-source-lock",
            "/lock",
        ],
    )
    assert mismatch_code == 5 and mismatch["error"]["code"] == "conflict"  # type: ignore[index]


def test_mcp_process_configuration_owns_and_closes_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Close the process-authorized provider even when the MCP input ends immediately."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    provider = _FakeProvider()
    monkeypatch.setattr(cli, "_open_semantic_provider", lambda _config: provider)
    arguments = cli._parser().parse_args(
        [
            "mcp",
            "--store",
            str(corpus.store),
            "--semantic-bundle",
            "/bundle",
            "--semantic-source-lock",
            "/lock",
        ]
    )
    assert cli._serve_mcp(arguments, source=io.BytesIO(), sink=io.BytesIO()) == 0
    assert provider.closed is True


def test_mcp_process_configuration_rejects_partial_pair(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject partial trusted startup configuration before opening a provider."""
    corpus = _WorkspaceCorpus(tmp_path, capsys)
    arguments = cli._parser().parse_args(
        ["mcp", "--store", str(corpus.store), "--semantic-bundle", "/bundle"]
    )
    with pytest.raises(cli._UsageError):
        cli._serve_mcp(arguments, source=io.BytesIO(), sink=io.BytesIO())
