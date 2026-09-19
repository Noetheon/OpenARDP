"""Offline regressions for the actual E5 worker's bounded selection lifecycle."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import openardp.adapters.e5_semantic as e5
from openardp.domain.semantic_retrieval import (
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
)
from openardp.ports.semantic_retrieval import SemanticProviderInvalid, SemanticProviderLimitExceeded


class _Vectors(list[float]):
    def cpu(self) -> _Vectors:
        return self


@dataclass
class _Runtime:
    recipe: SemanticProviderRecipe
    cache: dict[str, tuple[str, Any]] = field(default_factory=dict)
    corpora: dict[str, Any] = field(default_factory=dict)
    encoded: list[list[str]] = field(default_factory=list)

    def tokenize(self, texts: list[str], **_kwargs: Any) -> dict[str, Any]:
        self.encoded.append(texts)
        return {"texts": texts, "attention_mask": None}

    def model(self, *, texts: list[str], **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(last_hidden_state=_Vectors(0.5 for _ in texts))

    def dependencies(self) -> dict[str, Any]:
        return {
            "torch": SimpleNamespace(
                inference_mode=nullcontext,
                dot=lambda left, right: SimpleNamespace(item=lambda: left * right),
            ),
            "functional": SimpleNamespace(normalize=lambda vectors, **_kwargs: vectors),
            "tokenizer": self.tokenize,
            "model": self.model,
            "recipe": self.recipe,
            "cache": self.cache,
        }

    def call(
        self,
        kind: str,
        passages: tuple[SemanticPassage, ...] = (),
        *,
        limits: SemanticRetrievalLimits | None = None,
        query: str = "query",
        corpus_id: str = "",
    ) -> dict[str, Any]:
        request = {
            "kind": kind,
            "query": query,
            "corpus_id": corpus_id,
            "passages": [passage.model_dump(mode="json") for passage in passages],
            "limits": (limits or _limits()).model_dump(mode="json"),
        }
        kwargs = self.dependencies()
        if kind != "score":
            kwargs["corpora"] = self.corpora
        return getattr(e5, f"_{kind}_request")(request, **kwargs)  # type: ignore[no-any-return]

    @property
    def encoded_passages(self) -> list[str]:
        return [text for batch in self.encoded for text in batch if text.startswith("passage: ")]


def _limits(**updates: int) -> SemanticRetrievalLimits:
    return SemanticRetrievalLimits(
        **{
            "max_passages": 2,
            "max_cache_entries": 2,
            "max_response_entries": 2,
            "max_passage_bytes": 1024,
            "max_total_text_bytes": 1024,
            "batch_size": 1,
            **updates,
        }
    )


def _passage(
    number: int, *, evidence: str | None = None, text: str | None = None
) -> SemanticPassage:
    return SemanticPassage(
        evidence_id=evidence or f"evidence-{number}",
        object_id=f"sha256:{number:064x}",
        text=text or f"passage {number}",
    )


@pytest.fixture
def runtime(monkeypatch: pytest.MonkeyPatch) -> _Runtime:
    """Substitute numerical/model dependencies, retaining production request handling."""
    monkeypatch.setattr(e5, "_mean_pool", lambda hidden, _mask: hidden)
    monkeypatch.setattr(e5, "_peak_rss_bytes", lambda: None)
    return _Runtime(
        SemanticProviderRecipe(
            provider="fixture-e5",
            provider_version="1.0.0",
            model_id="fixture/e5",
            model_revision="a" * 40,
            model_bundle_id="sha256:" + "b" * 64,
            dimensions=1,
            max_tokens=16,
            query_prefix="query: ",
            passage_prefix="passage: ",
            pooling="mean_attention_mask",
            normalization="l2",
            similarity="cosine",
            quantizer="half_away_from_zero_millionths_v1",
            transformers_version="fixture",
            torch_version="fixture",
        )
    )


@pytest.mark.parametrize("kind", ["prepare", "score"])
def test_disjoint_full_selections_replace_obsolete_vectors(runtime: _Runtime, kind: str) -> None:
    """Individually valid selections never exhaust a cache through session history."""
    for numbers in ((1, 2), (3, 4), (1, 2)):
        passages = tuple(_passage(number) for number in numbers)
        runtime.call(kind, passages)
        assert set(runtime.cache) == {passage.object_id for passage in passages}
    assert len(runtime.encoded_passages) == 6


@pytest.mark.parametrize("kind", ["prepare", "score"])
def test_overlap_and_shared_objects_encode_once_in_request_order(
    runtime: _Runtime, kind: str
) -> None:
    """Retain overlap and return separate scores for distinct evidence of one object."""
    runtime.call(kind, (_passage(1), _passage(2)))
    response = runtime.call(kind, (_passage(2), _passage(2, evidence="other-evidence")))
    assert set(runtime.cache) == {_passage(2).object_id}
    assert runtime.encoded_passages == ["passage: passage 1", "passage: passage 2"]
    if kind == "prepare":
        response = runtime.call("score_prepared", corpus_id=response["corpus"]["corpus_id"])
    assert [score["evidence_id"] for score in response["scores"]] == [
        "evidence-2",
        "other-evidence",
    ]
    assert all(score["cache_hit"] for score in response["scores"])
    assert {score["score_millionths"] for score in response["scores"]} == {250_000}
    new_response = runtime.call(kind, (_passage(3), _passage(3, evidence="shared-new")))
    assert runtime.encoded_passages.count("passage: passage 3") == 1
    if kind == "score":
        assert not any(score["cache_hit"] for score in new_response["scores"])


@pytest.mark.parametrize("kind", ["prepare", "score"])
@pytest.mark.parametrize("cached", [False, True])
def test_conflicting_object_text_is_rejected_before_any_mutation(
    runtime: _Runtime, kind: str, cached: bool
) -> None:
    """Neither incoming duplicate objects nor overlap may change an object's body."""
    runtime.call("prepare", (_passage(1),))
    cache_before, corpora_before = dict(runtime.cache), dict(runtime.corpora)
    encoded_before = list(runtime.encoded)
    passages = (
        (_passage(2), _passage(1, text="conflict"))
        if cached
        else (_passage(2), _passage(2, evidence="different-evidence", text="conflict"))
    )
    with pytest.raises((ValueError, SemanticProviderInvalid)):
        runtime.call(kind, passages, limits=_limits(max_cache_entries=3))
    assert runtime.cache == cache_before and runtime.corpora == corpora_before
    assert runtime.encoded == encoded_before


@pytest.mark.parametrize("kind", ["prepare", "score"])
@pytest.mark.parametrize("invalid", ["empty", "count", "duplicate", "passage_bytes", "total_bytes"])
def test_invalid_selection_preserves_existing_preparation(
    runtime: _Runtime, kind: str, invalid: str
) -> None:
    """Apply all existing count and UTF-8 byte bounds before changing vectors or handles."""
    runtime.call("prepare", (_passage(1),))
    cache_before, corpora_before = dict(runtime.cache), dict(runtime.corpora)
    encoded_before = list(runtime.encoded)
    passages = {
        "empty": (),
        "count": (_passage(2), _passage(3), _passage(4)),
        "duplicate": (_passage(2), _passage(2)),
        "passage_bytes": (_passage(2, text="ä" * 300),),
        "total_bytes": (_passage(2, text="ä" * 300), _passage(3, text="ö" * 300)),
    }[invalid]
    limits = _limits(max_passage_bytes=512) if invalid == "passage_bytes" else _limits()
    with pytest.raises((ValueError, SemanticProviderInvalid, SemanticProviderLimitExceeded)):
        runtime.call(kind, passages, limits=limits)
    assert runtime.cache == cache_before and runtime.corpora == corpora_before
    assert runtime.encoded == encoded_before


def test_prepare_keeps_one_handle_and_requires_repreparation_after_eviction(
    runtime: _Runtime,
) -> None:
    """Evidence-only identity churn stays bounded and old IDs work only after preparation."""
    first = runtime.call("prepare", (_passage(1),))["corpus"]["corpus_id"]
    for index in range(20):
        current = runtime.call("prepare", (_passage(1, evidence=f"scope-{index}"),))
        assert set(runtime.corpora) == {current["corpus"]["corpus_id"]}
    with pytest.raises(ValueError):
        runtime.call("score_prepared", corpus_id=first)
    restored = runtime.call("prepare", (_passage(1),))["corpus"]["corpus_id"]
    assert restored == first
    assert runtime.call("score_prepared", corpus_id=restored)["scores"][0]["cache_hit"]
    assert runtime.encoded_passages == ["passage: passage 1"]


@pytest.mark.parametrize("kind", ["prepare", "score"])
@pytest.mark.parametrize(
    "invalid_limit",
    [
        {"max_passages": 0},
        {"max_cache_entries": 1},
        {"batch_size": True},
        {"max_total_text_bytes": 1023},
    ],
)
def test_invalid_limits_fail_before_cache_mutation(
    runtime: _Runtime, kind: str, invalid_limit: dict[str, Any]
) -> None:
    """Validate raw worker limit models rather than relying on the caller's model."""
    runtime.call("prepare", (_passage(1),))
    cache_before, corpora_before = dict(runtime.cache), dict(runtime.corpora)
    encoded_before = list(runtime.encoded)
    request = {
        "query": "query",
        "passages": [_passage(2).model_dump(mode="json")],
        "limits": {**_limits().model_dump(mode="json"), **invalid_limit},
    }
    kwargs = runtime.dependencies()
    if kind == "prepare":
        kwargs["corpora"] = runtime.corpora
    with pytest.raises(ValueError):
        getattr(e5, f"_{kind}_request")(request, **kwargs)
    assert runtime.cache == cache_before and runtime.corpora == corpora_before
    assert runtime.encoded == encoded_before


def test_prepared_scoring_rejects_missing_vectors_before_encoding(runtime: _Runtime) -> None:
    """Never deliver a partial prepared result if its disposable vector state is lost."""
    corpus_id = runtime.call("prepare", (_passage(1),))["corpus"]["corpus_id"]
    runtime.cache.clear()
    encoded_before = list(runtime.encoded)
    with pytest.raises(ValueError):
        runtime.call("score_prepared", corpus_id=corpus_id)
    assert runtime.encoded == encoded_before


@pytest.mark.parametrize("changed", ["batch_size", "timeout_seconds", "max_total_text_bytes"])
def test_prepared_scoring_rejects_any_changed_limit(runtime: _Runtime, changed: str) -> None:
    """Even non-count limits belong to the exact prepared corpus identity."""
    corpus_id = runtime.call("prepare", (_passage(1),))["corpus"]["corpus_id"]
    limits = _limits(**{changed: getattr(_limits(), changed) + 1})
    encoded_before = list(runtime.encoded)
    with pytest.raises(ValueError):
        runtime.call("score_prepared", corpus_id=corpus_id, limits=limits)
    assert runtime.encoded == encoded_before


@pytest.mark.parametrize("kind", ["score", "score_prepared"])
@pytest.mark.parametrize(
    "query", ["", "ä" * 513, "ü" * 13], ids=["empty", "query_bytes", "sum_bytes"]
)
def test_query_and_combined_bytes_fail_before_encoding(
    runtime: _Runtime, kind: str, query: str
) -> None:
    """Prepared IPC must enforce the same query-plus-passage byte budget as direct scoring."""
    passages = (_passage(1, text="ä" * 500),)
    corpus_id = runtime.call("prepare", passages)["corpus"]["corpus_id"]
    cache_before, corpora_before = dict(runtime.cache), dict(runtime.corpora)
    encoded_before = list(runtime.encoded)
    with pytest.raises((ValueError, SemanticProviderLimitExceeded)):
        runtime.call(kind, passages, query=query, corpus_id=corpus_id)
    assert runtime.cache == cache_before and runtime.corpora == corpora_before
    assert runtime.encoded == encoded_before


@pytest.mark.parametrize("kind", ["score", "score_prepared"])
def test_exact_combined_byte_boundary_is_accepted(runtime: _Runtime, kind: str) -> None:
    """Use UTF-8 bytes, allowing the inclusive limit without a gratuitous reserve."""
    passages = (_passage(1, text="ä" * 500),)
    corpus_id = runtime.call("prepare", passages)["corpus"]["corpus_id"]
    assert runtime.call(kind, passages, query="ü" * 12, corpus_id=corpus_id)["scores"]


def test_worker_direct_scoring_invalidates_previous_handle(
    runtime: _Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise real worker dispatch with fake imports, including its fail-closed response."""
    dependencies = runtime.dependencies()
    torch = ModuleType("torch")
    functional = ModuleType("torch.nn.functional")
    functional.normalize = dependencies["functional"].normalize  # type: ignore[attr-defined]
    torch.nn = SimpleNamespace(functional=functional)  # type: ignore[attr-defined]
    torch.inference_mode = nullcontext  # type: ignore[attr-defined]
    torch.dot = dependencies["torch"].dot  # type: ignore[attr-defined]
    for name in ("set_num_threads", "manual_seed", "use_deterministic_algorithms"):
        setattr(torch, name, lambda _value: None)
    transformers = ModuleType("transformers")

    class _Model:
        config = SimpleNamespace(hidden_size=1)

        def eval(self) -> None:
            pass

        def __call__(self, **kwargs: Any) -> SimpleNamespace:
            return runtime.model(**kwargs)

    transformers.AutoModel = SimpleNamespace(from_pretrained=lambda *_args, **_kwargs: _Model())  # type: ignore[attr-defined]
    transformers.AutoTokenizer = SimpleNamespace(  # type: ignore[attr-defined]
        from_pretrained=lambda *_args, **_kwargs: runtime.tokenize
    )
    for name, module in (
        ("torch", torch),
        ("torch.nn.functional", functional),
        ("transformers", transformers),
    ):
        monkeypatch.setitem(e5.sys.modules, name, module)
    monkeypatch.setattr(e5, "_deny_network", lambda: None)

    class _Connection:
        closed = False

        def __init__(self) -> None:
            self.responses: list[dict[str, Any]] = []
            self.index = 0

        def send(self, response: dict[str, Any]) -> None:
            self.responses.append(response)

        def recv(self) -> dict[str, Any]:
            kind = ("prepare", "score", "score_prepared", "close")[self.index]
            self.index += 1
            return {
                "kind": kind,
                "passages": [_passage(1).model_dump(mode="json")],
                "limits": _limits().model_dump(mode="json"),
                "query": "query",
                "corpus_id": self.responses[1]["corpus"]["corpus_id"] if self.index > 2 else "",
            }

        def close(self) -> None:
            self.closed = True

    connection = _Connection()
    e5._worker(connection, connection, "/unused", runtime.recipe.model_dump(mode="json"))  # type: ignore[arg-type]
    assert [response["kind"] for response in connection.responses] == [
        "ready",
        "prepared",
        "scores",
        "failed",
    ]
    assert connection.responses[-1] == {"kind": "failed", "code": "provider_runtime_failed"}
    assert connection.closed
