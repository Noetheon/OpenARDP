"""CAS-verified relevance observations over existing context candidates."""

from __future__ import annotations

import json
from typing import cast

from pydantic import JsonValue, ValidationError

from openardp.domain.block import ContentBlock
from openardp.domain.common import validate_json
from openardp.domain.context_compilation import (
    ContextBlockProvenance,
    ContextCandidate,
    ContextCompileLimits,
    CorpusSnapshot,
)
from openardp.domain.context_relevance import RelevancePolicy, evaluate_candidate_relevance
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.storage import StoredObject
from openardp.ports.context import (
    CancellationCheck,
    ContextCandidateSource,
    ContextCompilationCancelled,
    ContextIntegrityFailure,
    ContextLimitExceeded,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError


class RelevanceObservingCandidateSource:
    """Decorate verified candidate sources with one shared relevance policy."""

    def __init__(
        self,
        object_store: ObjectStore,
        sources: tuple[ContextCandidateSource, ...],
        policy: RelevancePolicy,
    ) -> None:
        """Bind exact-read authority, candidate sources and immutable policy."""
        if not sources:
            raise ValueError("relevance decorator requires at least one candidate source")
        self._object_store = object_store
        self._sources = sources
        self._policy = policy

    @property
    def policy(self) -> RelevancePolicy:
        """Return the exact immutable policy bound to this decorator."""
        return self._policy

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Discover, reverify and annotate candidates without filtering them."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_relevance_discovery")
        observed: list[ContextCandidate] = []
        for source in self._sources:
            if cancel():
                raise ContextCompilationCancelled("cancelled_during_relevance_discovery")
            candidates = source.discover(task, snapshot, limits, cancel)
            for candidate in candidates:
                if cancel():
                    raise ContextCompilationCancelled("cancelled_during_relevance_evaluation")
                if len(observed) >= limits.max_discovered:
                    raise ContextLimitExceeded("max_discovered_exceeded")
                text = self._verified_candidate_text(candidate, limits)
                try:
                    relevance = evaluate_candidate_relevance(task, text, self._policy)
                except ValueError as error:
                    raise ContextLimitExceeded("relevance_task_limit_exceeded") from error
                observed.append(candidate.model_copy(update={"relevance": relevance}))
        return tuple(observed)

    def _verified_candidate_text(
        self,
        candidate: ContextCandidate,
        limits: ContextCompileLimits,
    ) -> str:
        """Resolve one exact textual/structured candidate after CAS verification."""
        stored = candidate.body_object
        media_type = candidate.body_media_type
        if stored is None or media_type is None:
            raise ContextIntegrityFailure("relevance_candidate_body_missing")
        if stored.byte_length > limits.max_body_bytes:
            raise ContextLimitExceeded("relevance_body_limit_exceeded")
        payload = self._read_verified(stored)
        if isinstance(candidate.provenance, ContextBlockProvenance):
            return self._verified_block_text(candidate, payload)
        if media_type == "text/plain":
            try:
                return payload.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ContextIntegrityFailure("relevance_body_not_utf8") from error
        if media_type == "application/json":
            return self._verified_json_text(payload)
        raise ContextIntegrityFailure("relevance_body_media_unsupported")

    def _verified_block_text(self, candidate: ContextCandidate, payload: bytes) -> str:
        try:
            block = validate_json(ContentBlock, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("relevance_block_invalid") from error
        provenance = cast(ContextBlockProvenance, candidate.provenance)
        if (
            block.block_id != provenance.block_id
            or block.document_id != provenance.document_id
            or block.version_id != provenance.version_id
            or block.representation_id != provenance.representation_id
        ):
            raise ContextIntegrityFailure("relevance_block_mismatch")
        if block.text is not None:
            return block.text
        if block.structured is not None:
            return canonical_json_bytes(block.structured).decode("utf-8")
        raise ContextIntegrityFailure("relevance_block_text_missing")

    @staticmethod
    def _verified_json_text(payload: bytes) -> str:
        try:
            value: JsonValue = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContextIntegrityFailure("relevance_body_json_invalid") from error
        if canonical_json_bytes(value) != payload:
            raise ContextIntegrityFailure("relevance_body_json_noncanonical")
        if isinstance(value, str):
            return value
        return canonical_json_bytes(value).decode("utf-8")

    def _read_verified(self, stored: StoredObject) -> bytes:
        try:
            verified = self._object_store.verify(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        except ObjectStoreError as error:
            raise ContextIntegrityFailure("relevance_object_invalid") from error
        if len(payload) != verified.byte_length:
            raise ContextIntegrityFailure("relevance_object_length_changed")
        return payload


__all__ = ["RelevanceObservingCandidateSource"]
