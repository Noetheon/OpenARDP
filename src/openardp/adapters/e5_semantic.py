"""Persistent spawned offline E5 provider with disposable passage embeddings."""

from __future__ import annotations

import importlib.metadata
import multiprocessing
import os
import socket
import sys
import time
from contextlib import suppress
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any, NoReturn

from pydantic import ValidationError

from openardp.adapters.embedding_bundle import verify_embedding_bundle
from openardp.domain.semantic_retrieval import (
    PreparedSemanticCorpus,
    SemanticPassage,
    SemanticProviderRecipe,
    SemanticRetrievalLimits,
    SemanticScore,
    quantize_cosine,
)
from openardp.ports.context import CancellationCheck
from openardp.ports.semantic_retrieval import (
    SemanticProviderInvalid,
    SemanticProviderLimitExceeded,
    SemanticProviderTimedOut,
    SemanticProviderUnavailable,
)

_PROVIDER_NAME = "openardp-transformers-e5"
_PROVIDER_VERSION = "1.0.0"
_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "
_POLL_SECONDS = 0.05
_START_TIMEOUT_SECONDS = 180


# The following worker-only helpers execute in a spawned interpreter. Their real
# path is covered by the opt-in bundle integration test, outside in-process coverage.
def _peak_rss_bytes() -> int | None:  # pragma: no cover
    """Return this process's peak RSS in bytes on supported Unix platforms."""
    if sys.platform == "win32":
        return None
    import resource

    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


class _BlockedSocket(socket.socket):  # pragma: no cover
    """Socket-compatible class whose construction is denied after imports resolve."""

    def __new__(cls, *args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("network disabled")


def _deny_network() -> None:  # pragma: no cover
    """Deny socket construction before optional model libraries are imported."""

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network disabled")

    socket.socket = _BlockedSocket  # type: ignore[assignment,misc]
    socket.create_connection = blocked  # type: ignore[assignment]
    os.environ.update(
        {
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )


def _mean_pool(last_hidden: Any, attention_mask: Any) -> Any:  # pragma: no cover
    mask = attention_mask[..., None].bool()
    hidden = last_hidden.masked_fill(~mask, 0.0)
    return hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def _score_request(  # pragma: no cover
    request: dict[str, Any],
    *,
    torch: Any,
    functional: Any,
    tokenizer: Any,
    model: Any,
    recipe: SemanticProviderRecipe,
    cache: dict[str, tuple[str, Any]],
) -> dict[str, Any]:
    """Validate and score one worker request without owning process lifecycle."""
    query = request.get("query")
    raw_passages = request.get("passages")
    raw_limits = request.get("limits")
    if not isinstance(query, str) or not isinstance(raw_passages, list):
        raise ValueError
    limits = SemanticRetrievalLimits.model_validate(raw_limits)
    passages = tuple(SemanticPassage.model_validate(value) for value in raw_passages)
    if len(passages) > limits.max_passages:
        raise ValueError
    prior_hits = {passage.object_id: passage.object_id in cache for passage in passages}
    missing = [passage for passage in passages if passage.object_id not in cache]
    if len(cache) + len(missing) > limits.max_cache_entries:
        raise ValueError
    for passage in passages:
        existing = cache.get(passage.object_id)
        if existing is not None and existing[0] != passage.text:
            raise ValueError
    passage_started = time.perf_counter_ns()
    with torch.inference_mode():
        for offset in range(0, len(missing), limits.batch_size):
            batch = missing[offset : offset + limits.batch_size]
            encoded = tokenizer(
                [recipe.passage_prefix + passage.text for passage in batch],
                max_length=recipe.max_tokens,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            vectors = functional.normalize(
                _mean_pool(model(**encoded).last_hidden_state, encoded["attention_mask"]),
                p=2,
                dim=1,
            ).cpu()
            for passage, vector in zip(batch, vectors, strict=True):
                cache[passage.object_id] = (passage.text, vector)
        passage_encode_ns = time.perf_counter_ns() - passage_started
        query_started = time.perf_counter_ns()
        encoded_query = tokenizer(
            [recipe.query_prefix + query],
            max_length=recipe.max_tokens,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        query_vector = functional.normalize(
            _mean_pool(model(**encoded_query).last_hidden_state, encoded_query["attention_mask"]),
            p=2,
            dim=1,
        ).cpu()[0]
        query_encode_ns = time.perf_counter_ns() - query_started
        similarity_started = time.perf_counter_ns()
        scores = [
            {
                "cache_hit": prior_hits[passage.object_id],
                "evidence_id": passage.evidence_id,
                "object_id": passage.object_id,
                "provider_recipe_id": recipe.recipe_id,
                "score_millionths": quantize_cosine(
                    float(torch.dot(query_vector, cache[passage.object_id][1]).item())
                ),
            }
            for passage in passages
        ]
        similarity_ns = time.perf_counter_ns() - similarity_started
    return {
        "kind": "scores",
        "passage_encode_ns": passage_encode_ns,
        "peak_rss_bytes": _peak_rss_bytes(),
        "query_encode_ns": query_encode_ns,
        "similarity_ns": similarity_ns,
        "scores": scores,
    }


def _prepare_request(  # pragma: no cover
    request: dict[str, Any],
    *,
    torch: Any,
    functional: Any,
    tokenizer: Any,
    model: Any,
    recipe: SemanticProviderRecipe,
    cache: dict[str, tuple[str, Any]],
    corpora: dict[str, tuple[tuple[str, str], ...]],
) -> dict[str, Any]:
    raw_passages = request.get("passages")
    raw_limits = request.get("limits")
    if not isinstance(raw_passages, list):
        raise ValueError
    limits = SemanticRetrievalLimits.model_validate(raw_limits)
    passages = tuple(SemanticPassage.model_validate(value) for value in raw_passages)
    prepared = PreparedSemanticCorpus.from_passages(recipe.recipe_id, passages, limits)
    missing = [passage for passage in passages if passage.object_id not in cache]
    if len(cache) + len(missing) > limits.max_cache_entries:
        raise ValueError
    for passage in passages:
        existing = cache.get(passage.object_id)
        if existing is not None and existing[0] != passage.text:
            raise ValueError
    started = time.perf_counter_ns()
    with torch.inference_mode():
        for offset in range(0, len(missing), limits.batch_size):
            batch = missing[offset : offset + limits.batch_size]
            encoded = tokenizer(
                [recipe.passage_prefix + passage.text for passage in batch],
                max_length=recipe.max_tokens,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            vectors = functional.normalize(
                _mean_pool(model(**encoded).last_hidden_state, encoded["attention_mask"]),
                p=2,
                dim=1,
            ).cpu()
            for passage, vector in zip(batch, vectors, strict=True):
                cache[passage.object_id] = (passage.text, vector)
    corpora[prepared.corpus_id] = tuple(
        (passage.evidence_id, passage.object_id) for passage in passages
    )
    return {
        "kind": "prepared",
        "corpus": prepared.model_dump(mode="json"),
        "passage_encode_ns": time.perf_counter_ns() - started,
        "peak_rss_bytes": _peak_rss_bytes(),
    }


def _score_prepared_request(  # pragma: no cover
    request: dict[str, Any],
    *,
    torch: Any,
    functional: Any,
    tokenizer: Any,
    model: Any,
    recipe: SemanticProviderRecipe,
    cache: dict[str, tuple[str, Any]],
    corpora: dict[str, tuple[tuple[str, str], ...]],
) -> dict[str, Any]:
    query = request.get("query")
    corpus_id = request.get("corpus_id")
    limits = SemanticRetrievalLimits.model_validate(request.get("limits"))
    if not isinstance(query, str) or not isinstance(corpus_id, str):
        raise ValueError
    identities = corpora.get(corpus_id)
    if identities is None or len(identities) > limits.max_passages:
        raise ValueError
    if any(object_id not in cache for _evidence_id, object_id in identities):
        raise ValueError
    with torch.inference_mode():
        query_started = time.perf_counter_ns()
        encoded_query = tokenizer(
            [recipe.query_prefix + query],
            max_length=recipe.max_tokens,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        query_vector = functional.normalize(
            _mean_pool(model(**encoded_query).last_hidden_state, encoded_query["attention_mask"]),
            p=2,
            dim=1,
        ).cpu()[0]
        query_encode_ns = time.perf_counter_ns() - query_started
        similarity_started = time.perf_counter_ns()
        scores = [
            {
                "cache_hit": True,
                "evidence_id": evidence_id,
                "object_id": object_id,
                "provider_recipe_id": recipe.recipe_id,
                "score_millionths": quantize_cosine(
                    float(torch.dot(query_vector, cache[object_id][1]).item())
                ),
            }
            for evidence_id, object_id in identities
        ]
        similarity_ns = time.perf_counter_ns() - similarity_started
    return {
        "kind": "scores",
        "peak_rss_bytes": _peak_rss_bytes(),
        "query_encode_ns": query_encode_ns,
        "similarity_ns": similarity_ns,
        "scores": scores,
    }


def _worker(  # pragma: no cover
    input_connection: Connection,
    output_connection: Connection,
    model_root: str,
    recipe_value: dict[str, Any],
) -> None:
    """Own the optional runtime and model-specific vector cache in one child."""
    _deny_network()
    try:
        import torch
        import torch.nn.functional as functional
        from transformers import AutoModel, AutoTokenizer

        recipe = SemanticProviderRecipe.model_validate(recipe_value)
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        tokenizer = AutoTokenizer.from_pretrained(
            model_root,
            local_files_only=True,
            trust_remote_code=False,
        )
        model = AutoModel.from_pretrained(
            model_root,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
        )
        model.eval()
        hidden_size = int(getattr(model.config, "hidden_size", 0))
        if hidden_size != recipe.dimensions:
            raise ValueError
        cache: dict[str, tuple[str, Any]] = {}
        corpora: dict[str, tuple[tuple[str, str], ...]] = {}
        output_connection.send({"kind": "ready", "dimensions": hidden_size})
        while True:
            request = input_connection.recv()
            if not isinstance(request, dict):
                raise ValueError
            if request.get("kind") == "close":
                output_connection.send({"kind": "closed"})
                return
            kind = request.get("kind")
            if kind == "score":
                response = _score_request(
                    request,
                    torch=torch,
                    functional=functional,
                    tokenizer=tokenizer,
                    model=model,
                    recipe=recipe,
                    cache=cache,
                )
            elif kind == "prepare":
                response = _prepare_request(
                    request,
                    torch=torch,
                    functional=functional,
                    tokenizer=tokenizer,
                    model=model,
                    recipe=recipe,
                    cache=cache,
                    corpora=corpora,
                )
            elif kind == "score_prepared":
                response = _score_prepared_request(
                    request,
                    torch=torch,
                    functional=functional,
                    tokenizer=tokenizer,
                    model=model,
                    recipe=recipe,
                    cache=cache,
                    corpora=corpora,
                )
            else:
                raise ValueError
            output_connection.send(response)
    except BaseException:
        with suppress(BaseException):
            output_connection.send({"kind": "failed", "code": "provider_runtime_failed"})
    finally:
        input_connection.close()
        output_connection.close()


class IsolatedE5SemanticProvider:
    """Explicit local-only E5 adapter behind the provider-neutral score port."""

    def __init__(
        self,
        bundle: Path,
        *,
        expected_source_lock: Path,
    ) -> None:
        """Verify exact assets and freeze a complete runtime recipe without loading them."""
        self._process: BaseProcess | None = None
        self._input: Connection | None = None
        self._output: Connection | None = None
        self._requests = 0
        self._passages_scored = 0
        self._cache_hits = 0
        self._peak_worker_rss_bytes = 0
        self._preparations = 0
        self._prepared_requests = 0
        self._passage_encode_ns = 0
        self._query_encode_ns = 0
        self._similarity_ns = 0
        try:
            installed = verify_embedding_bundle(
                bundle,
                expected_source_lock=expected_source_lock,
            )
            transformers_version = importlib.metadata.version("transformers")
            torch_version = importlib.metadata.version("torch")
        except Exception:
            raise SemanticProviderUnavailable("semantic provider unavailable") from None
        self._bundle = bundle.absolute()
        self._recipe = SemanticProviderRecipe(
            provider=_PROVIDER_NAME,
            provider_version=_PROVIDER_VERSION,
            model_id=installed.model_id,
            model_revision=installed.model_revision,
            model_bundle_id=installed.bundle_id,
            dimensions=installed.dimensions,
            max_tokens=installed.max_tokens,
            query_prefix=_QUERY_PREFIX,
            passage_prefix=_PASSAGE_PREFIX,
            pooling="mean_attention_mask",
            normalization="l2",
            similarity="cosine",
            quantizer="half_away_from_zero_millionths_v1",
            transformers_version=transformers_version,
            torch_version=torch_version,
        )

    @property
    def recipe(self) -> SemanticProviderRecipe:
        """Return the exact verified runtime recipe."""
        return self._recipe

    @property
    def metrics(self) -> dict[str, int]:
        """Return aggregate body-free runtime observations for benchmark reporting."""
        return {
            "requests": self._requests,
            "passages_scored": self._passages_scored,
            "cache_hits": self._cache_hits,
            "peak_worker_rss_bytes": self._peak_worker_rss_bytes,
        }

    @property
    def phase_metrics(self) -> dict[str, int]:
        """Return body-free prepared-provider phase observations."""
        return {
            "preparations": self._preparations,
            "prepared_requests": self._prepared_requests,
            "passage_encode_ns": self._passage_encode_ns,
            "query_encode_ns": self._query_encode_ns,
            "similarity_ns": self._similarity_ns,
        }

    def prepare(
        self,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> PreparedSemanticCorpus:
        """Prepare exact passages once inside the bounded provider process."""
        self._validate_passages(passages, limits)
        if cancel():
            raise SemanticProviderTimedOut("semantic provider cancelled")
        expected = PreparedSemanticCorpus.from_passages(self.recipe.recipe_id, passages, limits)
        input_connection, output_connection = self._ensure_worker(cancel)
        try:
            input_connection.send(
                {
                    "kind": "prepare",
                    "limits": limits.model_dump(mode="json"),
                    "passages": [passage.model_dump(mode="json") for passage in passages],
                }
            )
            response = self._receive(output_connection, limits.timeout_seconds, cancel)
        except SemanticProviderTimedOut:
            self._terminate()
            raise
        except Exception:
            self._terminate()
            raise SemanticProviderUnavailable("semantic provider unavailable") from None
        if not isinstance(response, dict) or response.get("kind") != "prepared":
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid")
        try:
            observed = PreparedSemanticCorpus.model_validate(response.get("corpus"))
        except (ValidationError, ValueError, TypeError):
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid") from None
        if observed != expected:
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid")
        passage_ns = self._phase_value(response, "passage_encode_ns")
        self._update_peak_rss(response)
        self._preparations += 1
        self._passage_encode_ns += passage_ns
        return observed

    def score_prepared(
        self,
        query: str,
        corpus: PreparedSemanticCorpus,
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> tuple[SemanticScore, ...]:
        """Score a still-live prepared corpus using compact IPC."""
        if corpus.provider_recipe_id != self.recipe.recipe_id:
            raise SemanticProviderInvalid("semantic prepared corpus recipe mismatch")
        self._validate_query(query, limits)
        if corpus.passage_count > limits.max_passages:
            raise SemanticProviderLimitExceeded("semantic passage count exceeded")
        if cancel():
            raise SemanticProviderTimedOut("semantic provider cancelled")
        input_connection, output_connection = self._ensure_worker(cancel)
        try:
            input_connection.send(
                {
                    "corpus_id": corpus.corpus_id,
                    "kind": "score_prepared",
                    "limits": limits.model_dump(mode="json"),
                    "query": query,
                }
            )
            response = self._receive(output_connection, limits.timeout_seconds, cancel)
        except SemanticProviderTimedOut:
            self._terminate()
            raise
        except Exception:
            self._terminate()
            raise SemanticProviderUnavailable("semantic provider unavailable") from None
        scores = self._decode_scores(response, limits, expected_count=corpus.passage_count)
        self._prepared_requests += 1
        self._record_scores(scores, response)
        return scores

    def score(
        self,
        query: str,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
        cancel: CancellationCheck,
    ) -> tuple[SemanticScore, ...]:
        """Score one bounded request and terminate on timeout/cancellation/failure."""
        self._validate_request(query, passages, limits)
        if cancel():
            raise SemanticProviderTimedOut("semantic provider cancelled")
        input_connection, output_connection = self._ensure_worker(cancel)
        try:
            input_connection.send(
                {
                    "kind": "score",
                    "limits": limits.model_dump(mode="json"),
                    "passages": [passage.model_dump(mode="json") for passage in passages],
                    "query": query,
                }
            )
            response = self._receive(output_connection, limits.timeout_seconds, cancel)
        except SemanticProviderTimedOut:
            self._terminate()
            raise
        except Exception:
            self._terminate()
            raise SemanticProviderUnavailable("semantic provider unavailable") from None
        scores = self._decode_scores(response, limits, expected_count=len(passages))
        self._record_scores(scores, response)
        return scores

    def _decode_scores(
        self,
        response: object,
        limits: SemanticRetrievalLimits,
        *,
        expected_count: int,
    ) -> tuple[SemanticScore, ...]:
        if not isinstance(response, dict) or response.get("kind") != "scores":
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid")
        raw_scores = response.get("scores")
        if (
            not isinstance(raw_scores, list)
            or len(raw_scores) != expected_count
            or len(raw_scores) > limits.max_response_entries
        ):
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid")
        try:
            return tuple(SemanticScore.model_validate(value) for value in raw_scores)
        except (ValidationError, ValueError, TypeError):
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid") from None

    def _record_scores(self, scores: tuple[SemanticScore, ...], response: object) -> None:
        assert isinstance(response, dict)
        self._update_peak_rss(response)
        self._requests += 1
        self._passages_scored += len(scores)
        self._cache_hits += sum(score.cache_hit for score in scores)
        if "passage_encode_ns" in response:
            self._passage_encode_ns += self._phase_value(response, "passage_encode_ns")
        if "query_encode_ns" in response:
            self._query_encode_ns += self._phase_value(response, "query_encode_ns")
        if "similarity_ns" in response:
            self._similarity_ns += self._phase_value(response, "similarity_ns")

    def _update_peak_rss(self, response: dict[str, Any]) -> None:
        peak_rss = response.get("peak_rss_bytes")
        if peak_rss is not None and (
            not isinstance(peak_rss, int) or isinstance(peak_rss, bool) or peak_rss <= 0
        ):
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid")
        if isinstance(peak_rss, int):
            self._peak_worker_rss_bytes = max(self._peak_worker_rss_bytes, peak_rss)

    def _phase_value(self, response: dict[str, Any], field: str) -> int:
        value = response.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            self._terminate()
            raise SemanticProviderInvalid("semantic provider response invalid")
        return value

    def close(self) -> None:
        """Release the child and its model/vector memory idempotently."""
        input_connection = self._input
        output_connection = self._output
        process = self._process
        self._input = None
        self._output = None
        self._process = None
        if input_connection is not None and output_connection is not None:
            try:
                input_connection.send({"kind": "close"})
                if output_connection.poll(2):
                    output_connection.recv()
            except (EOFError, OSError, BrokenPipeError):
                pass
            finally:
                input_connection.close()
                output_connection.close()
        if process is not None:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)

    def _ensure_worker(self, cancel: CancellationCheck) -> tuple[Connection, Connection]:
        if self._process is not None and self._input is not None and self._output is not None:
            if self._process.is_alive():
                return self._input, self._output
            self._terminate()
        context = multiprocessing.get_context("spawn")
        child_input, parent_input = context.Pipe(duplex=False)
        parent_output, child_output = context.Pipe(duplex=False)
        process = context.Process(
            target=_worker,
            args=(
                child_input,
                child_output,
                str(self._bundle / "assets"),
                self._recipe.model_dump(mode="json"),
            ),
            name="openardp-e5-provider",
            daemon=True,
        )
        process.start()
        child_input.close()
        child_output.close()
        self._process = process
        self._input = parent_input
        self._output = parent_output
        try:
            response = self._receive(parent_output, _START_TIMEOUT_SECONDS, cancel)
        except SemanticProviderTimedOut:
            self._terminate()
            raise
        if (
            not isinstance(response, dict)
            or response.get("kind") != "ready"
            or response.get("dimensions") != self._recipe.dimensions
        ):
            self._terminate()
            raise SemanticProviderUnavailable("semantic provider unavailable")
        return parent_input, parent_output

    def _receive(
        self,
        connection: Connection,
        timeout_seconds: int,
        cancel: CancellationCheck,
    ) -> object:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if cancel():
                raise SemanticProviderTimedOut("semantic provider cancelled")
            if connection.poll(_POLL_SECONDS):
                try:
                    return connection.recv()
                except EOFError:
                    break
            if self._process is not None and not self._process.is_alive():
                break
        raise SemanticProviderTimedOut("semantic provider timed out")

    @staticmethod
    def _validate_request(
        query: str,
        passages: tuple[SemanticPassage, ...],
        limits: SemanticRetrievalLimits,
    ) -> None:
        IsolatedE5SemanticProvider._validate_query(query, limits)
        IsolatedE5SemanticProvider._validate_passages(passages, limits)
        if (
            len(query.encode("utf-8"))
            + sum(len(passage.text.encode("utf-8")) for passage in passages)
            > limits.max_total_text_bytes
        ):
            raise SemanticProviderLimitExceeded("semantic request bytes exceeded")

    @staticmethod
    def _validate_query(query: str, limits: SemanticRetrievalLimits) -> None:
        if not query or len(query.encode("utf-8")) > limits.max_passage_bytes:
            raise SemanticProviderLimitExceeded("semantic query limit exceeded")

    @staticmethod
    def _validate_passages(
        passages: tuple[SemanticPassage, ...], limits: SemanticRetrievalLimits
    ) -> None:
        if not passages:
            raise SemanticProviderLimitExceeded("semantic passage count exceeded")
        if len(passages) > limits.max_passages:
            raise SemanticProviderLimitExceeded("semantic passage count exceeded")
        identities = {(passage.evidence_id, passage.object_id) for passage in passages}
        if len(identities) != len(passages):
            raise SemanticProviderInvalid("semantic passage identities duplicated")
        sizes = tuple(len(passage.text.encode("utf-8")) for passage in passages)
        if any(size > limits.max_passage_bytes for size in sizes):
            raise SemanticProviderLimitExceeded("semantic passage limit exceeded")
        if sum(sizes) > limits.max_total_text_bytes:
            raise SemanticProviderLimitExceeded("semantic request bytes exceeded")

    def _terminate(self) -> None:
        input_connection = self._input
        output_connection = self._output
        process = self._process
        self._input = None
        self._output = None
        self._process = None
        if input_connection is not None:
            input_connection.close()
        if output_connection is not None:
            output_connection.close()
        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)

    def __enter__(self) -> IsolatedE5SemanticProvider:
        """Return the verified lazy provider."""
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        """Release the provider worker on context exit."""
        self.close()

    def __del__(self) -> None:
        """Best-effort cleanup when callers omit explicit lifecycle management."""
        self.close()


__all__ = ["IsolatedE5SemanticProvider"]
