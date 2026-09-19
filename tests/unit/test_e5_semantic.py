"""In-process lifecycle and failure tests for the isolated E5 parent adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import openardp.adapters.e5_semantic as e5_module
from openardp.adapters.e5_semantic import IsolatedE5SemanticProvider
from openardp.domain.semantic_retrieval import (
    PreparedSemanticCorpus,
    SemanticPassage,
    SemanticRetrievalLimits,
)
from openardp.ports.semantic_retrieval import (
    SemanticProviderInvalid,
    SemanticProviderLimitExceeded,
    SemanticProviderTimedOut,
    SemanticProviderUnavailable,
)


class _Connection:
    def __init__(self, responses: list[object] | None = None, *, send_error: bool = False) -> None:
        self.responses = responses or []
        self.send_error = send_error
        self.sent: list[object] = []
        self.closed = False

    def send(self, value: object) -> None:
        if self.send_error:
            raise BrokenPipeError
        self.sent.append(value)

    def poll(self, _timeout: float) -> bool:
        return bool(self.responses)

    def recv(self) -> object:
        if not self.responses:
            raise EOFError
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


class _Process:
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive
        self.started = False
        self.terminated = False
        self.joins: list[int] = []

    def start(self) -> None:
        self.started = True

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.terminated = True
        self.alive = False

    def join(self, timeout: int) -> None:
        self.joins.append(timeout)


def _passage(identity: str = "1", *, text: str = "bounded passage") -> SemanticPassage:
    return SemanticPassage(
        evidence_id=f"evidence-{identity}",
        object_id="sha256:" + identity * 64,
        text=text,
    )


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> IsolatedE5SemanticProvider:
    """Build a provider whose exact bundle and package metadata are deterministic fakes."""
    installed = SimpleNamespace(
        model_id="fixture/e5",
        model_revision="a" * 40,
        bundle_id="sha256:" + "b" * 64,
        dimensions=3,
        max_tokens=16,
    )
    monkeypatch.setattr(e5_module, "verify_embedding_bundle", lambda *_args, **_kwargs: installed)
    monkeypatch.setattr(e5_module.importlib.metadata, "version", lambda name: f"{name}-test")
    return IsolatedE5SemanticProvider(tmp_path / "bundle", expected_source_lock=tmp_path / "lock")


def test_init_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Map bundle and runtime metadata failures to the provider-neutral unavailable error."""
    monkeypatch.setattr(
        e5_module,
        "verify_embedding_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("secret")),
    )
    with pytest.raises(SemanticProviderUnavailable, match="provider unavailable"):
        IsolatedE5SemanticProvider(tmp_path, expected_source_lock=tmp_path / "lock")


def test_score_accepts_body_free_response_and_tracks_metrics(
    provider: IsolatedE5SemanticProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate parent-side score parsing, cache metrics and peak-RSS aggregation."""
    passage = _passage()
    input_connection = _Connection()
    output_connection = _Connection()
    response = {
        "kind": "scores",
        "peak_rss_bytes": 123,
        "scores": [
            {
                "cache_hit": True,
                "evidence_id": passage.evidence_id,
                "object_id": passage.object_id,
                "provider_recipe_id": provider.recipe.recipe_id,
                "score_millionths": 812_345,
            }
        ],
    }
    monkeypatch.setattr(
        provider,
        "_ensure_worker",
        lambda _cancel: (input_connection, output_connection),
    )
    monkeypatch.setattr(provider, "_receive", lambda *_args: response)
    result = provider.score(
        "valid query",
        (passage,),
        SemanticRetrievalLimits(max_passages=1, max_cache_entries=1),
        lambda: False,
    )
    assert result[0].score_millionths == 812_345
    assert provider.metrics == {
        "requests": 1,
        "passages_scored": 1,
        "cache_hits": 1,
        "peak_worker_rss_bytes": 123,
    }
    assert input_connection.sent[0]["kind"] == "score"  # type: ignore[index]


def test_prepare_then_score_prepared_uses_body_once_and_tracks_phase_metrics(
    provider: IsolatedE5SemanticProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Send full text only during preparation and a compact corpus handle thereafter."""
    passage = _passage()
    limits = SemanticRetrievalLimits(max_passages=1, max_cache_entries=1)
    prepared = PreparedSemanticCorpus.from_passages(provider.recipe.recipe_id, (passage,), limits)
    input_connection = _Connection()
    output_connection = _Connection()
    responses = [
        {
            "kind": "prepared",
            "corpus": prepared.model_dump(mode="json"),
            "peak_rss_bytes": 120,
            "passage_encode_ns": 11,
        },
        {
            "kind": "scores",
            "peak_rss_bytes": 123,
            "query_encode_ns": 7,
            "similarity_ns": 5,
            "scores": [
                {
                    "cache_hit": True,
                    "evidence_id": passage.evidence_id,
                    "object_id": passage.object_id,
                    "provider_recipe_id": provider.recipe.recipe_id,
                    "score_millionths": 812_345,
                }
            ],
        },
    ]
    monkeypatch.setattr(
        provider, "_ensure_worker", lambda _cancel: (input_connection, output_connection)
    )
    monkeypatch.setattr(provider, "_receive", lambda *_args: responses.pop(0))

    assert provider.prepare((passage,), limits, lambda: False) == prepared
    scores = provider.score_prepared("valid query", prepared, limits, lambda: False)

    assert scores[0].score_millionths == 812_345
    assert input_connection.sent[0]["kind"] == "prepare"  # type: ignore[index]
    assert input_connection.sent[0]["passages"][0]["text"] == passage.text  # type: ignore[index]
    assert input_connection.sent[1] == {  # type: ignore[index]
        "corpus_id": prepared.corpus_id,
        "kind": "score_prepared",
        "limits": limits.model_dump(mode="json"),
        "query": "valid query",
    }
    assert provider.phase_metrics == {
        "preparations": 1,
        "prepared_requests": 1,
        "passage_encode_ns": 11,
        "query_encode_ns": 7,
        "similarity_ns": 5,
    }


def test_prepared_calls_reject_recipe_mismatch_and_malformed_worker_response(
    provider: IsolatedE5SemanticProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed before or after IPC when a process-local handle cannot be trusted."""
    passage = _passage()
    limits = SemanticRetrievalLimits(max_passages=1, max_cache_entries=1)
    wrong = PreparedSemanticCorpus.from_passages("sha256:" + "f" * 64, (passage,), limits)
    with pytest.raises(SemanticProviderInvalid, match="recipe"):
        provider.score_prepared("query", wrong, limits, lambda: False)
    monkeypatch.setattr(provider, "_ensure_worker", lambda _cancel: (_Connection(), _Connection()))
    monkeypatch.setattr(provider, "_receive", lambda *_args: {"kind": "unknown"})
    with pytest.raises(SemanticProviderInvalid, match="response invalid"):
        provider.prepare((passage,), limits, lambda: False)


@pytest.mark.parametrize(
    "response",
    [
        None,
        {"kind": "wrong", "scores": []},
        {"kind": "scores", "scores": "invalid"},
        {"kind": "scores", "scores": [], "peak_rss_bytes": True},
        {"kind": "scores", "scores": [{"invalid": "score"}]},
    ],
)
def test_score_rejects_malformed_worker_responses(
    provider: IsolatedE5SemanticProvider,
    monkeypatch: pytest.MonkeyPatch,
    response: object,
) -> None:
    """Terminate and fail closed for every malformed IPC response family."""
    monkeypatch.setattr(provider, "_ensure_worker", lambda _cancel: (_Connection(), _Connection()))
    monkeypatch.setattr(provider, "_receive", lambda *_args: response)
    terminated: list[bool] = []
    monkeypatch.setattr(provider, "_terminate", lambda: terminated.append(True))
    with pytest.raises(SemanticProviderInvalid, match="response invalid"):
        provider.score(
            "query",
            (_passage(),),
            SemanticRetrievalLimits(max_passages=1, max_cache_entries=1),
            lambda: False,
        )
    assert terminated == [True]


def test_score_maps_ipc_failure_and_preserves_timeout(
    provider: IsolatedE5SemanticProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep cancellation/timeout distinct while sanitizing arbitrary IPC failures."""
    monkeypatch.setattr(provider, "_ensure_worker", lambda _cancel: (_Connection(), _Connection()))
    terminated: list[bool] = []
    monkeypatch.setattr(provider, "_terminate", lambda: terminated.append(True))
    limits = SemanticRetrievalLimits(max_passages=1, max_cache_entries=1)
    monkeypatch.setattr(
        provider,
        "_receive",
        lambda *_args: (_ for _ in ()).throw(SemanticProviderTimedOut("timed out")),
    )
    with pytest.raises(SemanticProviderTimedOut):
        provider.score("query", (_passage(),), limits, lambda: False)
    monkeypatch.setattr(
        provider,
        "_receive",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("secret")),
    )
    with pytest.raises(SemanticProviderUnavailable, match="provider unavailable"):
        provider.score("query", (_passage(),), limits, lambda: False)
    assert terminated == [True, True]


def test_request_limits_and_cancellation_fail_before_worker(
    provider: IsolatedE5SemanticProvider,
) -> None:
    """Reject invalid identity and byte/count bounds before creating a child."""
    limits = SemanticRetrievalLimits(
        max_passages=1,
        max_passage_bytes=1000,
        max_total_text_bytes=1024,
        max_cache_entries=1,
    )
    with pytest.raises(SemanticProviderLimitExceeded, match="query"):
        provider.score("", (), limits, lambda: False)
    with pytest.raises(SemanticProviderLimitExceeded, match="count"):
        provider.score("query", (_passage("1"), _passage("2")), limits, lambda: False)
    with pytest.raises(SemanticProviderInvalid, match="duplicated"):
        provider.score(
            "query",
            (_passage(), _passage()),
            limits.model_copy(update={"max_passages": 2}),
            lambda: False,
        )
    with pytest.raises(SemanticProviderLimitExceeded, match="passage limit"):
        provider.score("query", (_passage(text="x" * 1001),), limits, lambda: False)
    with pytest.raises(SemanticProviderLimitExceeded, match="request bytes"):
        provider.score("x" * 100, (_passage(text="x" * 925),), limits, lambda: False)
    with pytest.raises(SemanticProviderTimedOut, match="cancelled"):
        provider.score("query", (_passage(),), limits, lambda: True)


def test_receive_close_and_terminate_are_bounded(
    provider: IsolatedE5SemanticProvider,
) -> None:
    """Exercise successful receive, graceful close and forced termination idempotently."""
    connection = _Connection([{"kind": "ready"}])
    assert provider._receive(connection, 1, lambda: False) == {"kind": "ready"}
    with pytest.raises(SemanticProviderTimedOut, match="cancelled"):
        provider._receive(_Connection(), 1, lambda: True)
    input_connection = _Connection()
    output_connection = _Connection([{"kind": "closed"}])
    process = _Process()
    provider._input = input_connection  # type: ignore[assignment]
    provider._output = output_connection  # type: ignore[assignment]
    provider._process = process  # type: ignore[assignment]
    provider.close()
    assert input_connection.sent == [{"kind": "close"}]
    assert input_connection.closed and output_connection.closed
    assert process.terminated and process.joins == [2, 2]
    provider.close()


def test_prepared_query_combined_byte_limit_fails_before_worker(
    provider: IsolatedE5SemanticProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject an oversized query plus prepared corpus before IPC or child termination."""
    limits = SemanticRetrievalLimits(max_passage_bytes=1024, max_total_text_bytes=1024)
    prepared = PreparedSemanticCorpus.from_passages(
        provider.recipe.recipe_id, (_passage(text="ä" * 500),), limits
    )
    monkeypatch.setattr(
        provider,
        "_ensure_worker",
        lambda _cancel: (_ for _ in ()).throw(AssertionError("worker must not be used")),
    )
    with pytest.raises(SemanticProviderLimitExceeded, match="request bytes"):
        provider.score_prepared("ü" * 13, prepared, limits, lambda: False)


def test_ensure_worker_reuses_live_child_and_rejects_bad_startup(
    provider: IsolatedE5SemanticProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reuse only a live complete child and sanitize an invalid startup handshake."""
    existing_input, existing_output, existing_process = _Connection(), _Connection(), _Process()
    provider._input = existing_input  # type: ignore[assignment]
    provider._output = existing_output  # type: ignore[assignment]
    provider._process = existing_process  # type: ignore[assignment]
    assert provider._ensure_worker(lambda: False) == (existing_input, existing_output)
    existing_process.alive = False
    terminated: list[bool] = []
    monkeypatch.setattr(provider, "_terminate", lambda: terminated.append(True))
    monkeypatch.setattr(provider, "_receive", lambda *_args: {"kind": "invalid"})

    child_input, parent_input = _Connection(), _Connection()
    parent_output, child_output = _Connection(), _Connection()
    spawned = _Process()

    class _Context:
        def __init__(self) -> None:
            self.pipes = [(child_input, parent_input), (parent_output, child_output)]

        def Pipe(self, *, duplex: bool) -> tuple[_Connection, _Connection]:
            assert duplex is False
            return self.pipes.pop(0)

        def Process(self, **_kwargs: object) -> _Process:
            return spawned

    monkeypatch.setattr(e5_module.multiprocessing, "get_context", lambda method: _Context())
    with pytest.raises(SemanticProviderUnavailable, match="provider unavailable"):
        provider._ensure_worker(lambda: False)
    assert terminated == [True, True]
    assert spawned.started and child_input.closed and child_output.closed
