"""CAS-verified semantic candidates over exact text, CSV and rich snapshots."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Callable
from typing import Any, cast

from pydantic import JsonValue, ValidationError

from openardp.domain.block import ContentBlock
from openardp.domain.common import ContentRole, DataTrustClassification, validate_json
from openardp.domain.context import EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    CandidateFreshness,
    ContextBlockProvenance,
    ContextCandidate,
    ContextCompileLimits,
    ContextProjectionProvenance,
    CorpusSnapshot,
)
from openardp.domain.context_relevance import (
    RelevancePolicy,
    RelevanceSignalClass,
    extract_relevance_signals,
)
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import RepresentationAggregate, RepresentationScope
from openardp.domain.rich_ingestion import RichRepresentationArtifacts
from openardp.domain.semantic_retrieval import (
    PreparedSemanticCorpus,
    SemanticCandidateObservation,
    SemanticPassage,
    SemanticRetrievalLimits,
    SemanticRetrievalPolicy,
    SemanticScore,
)
from openardp.domain.storage import StoredObject
from openardp.ports.catalog import Catalog, RichCatalog, RichEvidenceAuthorityCatalog
from openardp.ports.context import (
    CancellationCheck,
    ContextCandidateSource,
    ContextCompilationCancelled,
    ContextIntegrityFailure,
    ContextLimitExceeded,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError
from openardp.ports.semantic_retrieval import (
    PreparedSemanticRetrievalProvider,
    SemanticProviderInvalid,
    SemanticProviderLimitExceeded,
    SemanticRetrievalProvider,
)

SEMANTIC_MATCH_REASON = "semantic_embedding_match"
_TOKEN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)


class SemanticContextCandidateSource:
    """Enumerate exact evidence, score it through one provider and admit by policy."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: Catalog | RichCatalog,
        provider: SemanticRetrievalProvider,
        policy: SemanticRetrievalPolicy,
        provider_limits: SemanticRetrievalLimits,
        *,
        text_verifier: Callable[[RepresentationAggregate], None],
        rich_verifier: Callable[[RichRepresentationArtifacts], None],
        source_balanced: bool = False,
        max_per_document: int = 32,
        ranked_prefix: int = 4,
        rich_first: bool = True,
        prepared_corpus: bool = False,
    ) -> None:
        """Bind exact evidence authorities and an explicitly configured provider."""
        self._object_store = object_store
        self._catalog = catalog
        self._rich_catalog = cast(RichCatalog, catalog)
        self._provider = provider
        self._policy = policy
        self._provider_limits = provider_limits
        self._text_verifier = text_verifier
        self._rich_verifier = rich_verifier
        if max_per_document < 1 or ranked_prefix < 0:
            raise ValueError("semantic allocation bounds must be non-negative")
        self._source_balanced = source_balanced
        self._max_per_document = max_per_document
        self._ranked_prefix = ranked_prefix
        self._rich_first = rich_first
        if prepared_corpus and not isinstance(provider, PreparedSemanticRetrievalProvider):
            raise ValueError("semantic provider does not support prepared corpora")
        self._prepared_corpus = prepared_corpus
        self._prepared_cache: (
            tuple[
                str,
                list[tuple[ContextCandidate, SemanticPassage]],
                PreparedSemanticCorpus,
                dict[RepresentationScope, str],
            ]
            | None
        ) = None
        self._calls = 0
        self._snapshot_cache_hits = 0
        self._passages_prepared = 0
        self._enumeration_ns = 0
        self._provider_ns = 0
        self._admission_ns = 0
        self._reconciliation_ns = 0

    @property
    def provider(self) -> SemanticRetrievalProvider:
        """Return the exact provider for lifecycle management and metrics."""
        return self._provider

    @property
    def phase_metrics(self) -> dict[str, int]:
        """Return cumulative body-free discovery phase observations."""
        return {
            "calls": self._calls,
            "snapshot_cache_hits": self._snapshot_cache_hits,
            "passages_prepared": self._passages_prepared,
            "enumeration_ns": self._enumeration_ns,
            "provider_ns": self._provider_ns,
            "admission_ns": self._admission_ns,
            "reconciliation_ns": self._reconciliation_ns,
        }

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Return policy-admitted semantic candidates with exact score ordering."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_semantic_discovery")
        self._calls += 1
        cache_key = self._cache_key(snapshot, limits)
        cached = self._prepared_cache
        if self._prepared_corpus and cached is not None and cached[0] == cache_key:
            self._snapshot_cache_hits += 1
            corpus = cached[1]
            prepared = cached[2]
            rich_authorities = cached[3]
        else:
            enumeration_started = time.perf_counter_ns()
            corpus = self._enumerate(snapshot, limits, cancel)
            self._enumeration_ns += time.perf_counter_ns() - enumeration_started
            prepared = None
            rich_authorities = self._rich_authorities(snapshot)
        passages = tuple(entry[1] for entry in corpus)
        encoded_bytes = sum(len(passage.text.encode("utf-8")) for passage in passages)
        if encoded_bytes > self._provider_limits.max_total_text_bytes:
            raise ContextLimitExceeded("semantic_total_text_bytes_exceeded")
        identities = {(passage.evidence_id, passage.object_id) for passage in passages}
        if len(identities) != len(passages):
            raise ContextIntegrityFailure("semantic_passage_identity_duplicate")
        provider_started = time.perf_counter_ns()
        try:
            if self._prepared_corpus:
                prepared_provider = cast(PreparedSemanticRetrievalProvider, self._provider)
                if prepared is None:
                    prepared = prepared_provider.prepare(passages, self._provider_limits, cancel)
                    self._prepared_cache = (
                        cache_key,
                        corpus,
                        prepared,
                        rich_authorities,
                    )
                    self._passages_prepared += len(passages)
                scores = prepared_provider.score_prepared(
                    task, prepared, self._provider_limits, cancel
                )
            else:
                scores = self._provider.score(task, passages, self._provider_limits, cancel)
        except SemanticProviderLimitExceeded as error:
            raise ContextLimitExceeded("semantic_provider_limit_exceeded") from error
        except SemanticProviderInvalid as error:
            raise ContextIntegrityFailure("semantic_provider_response_invalid") from error
        finally:
            self._provider_ns += time.perf_counter_ns() - provider_started
        admitted = self._admit(task, corpus, scores)
        if self._prepared_corpus and cached is not None and cached[0] == cache_key:
            reconciliation_started = time.perf_counter_ns()
            self._reconcile_catalog(admitted, rich_authorities)
            self._reconciliation_ns += time.perf_counter_ns() - reconciliation_started
        return tuple(admitted)

    def _admit(
        self,
        task: str,
        corpus: list[tuple[ContextCandidate, SemanticPassage]],
        scores: tuple[SemanticScore, ...],
    ) -> list[ContextCandidate]:
        """Validate provider coverage and apply the exact semantic admission policy."""
        passages = tuple(entry[1] for entry in corpus)
        expected = {(passage.evidence_id, passage.object_id) for passage in passages}
        observed = {(score.evidence_id, score.object_id) for score in scores}
        if len(scores) != len(observed) or observed != expected:
            raise ContextIntegrityFailure("semantic_provider_response_coverage")
        recipe_id = self._provider.recipe.recipe_id
        by_identity = {(score.evidence_id, score.object_id): score for score in scores}
        admission_started = time.perf_counter_ns()
        candidates: list[ContextCandidate] = []
        for candidate, passage in corpus:
            score = by_identity[(passage.evidence_id, passage.object_id)]
            if score.provider_recipe_id != recipe_id:
                raise ContextIntegrityFailure("semantic_provider_recipe_mismatch")
            volatile_matched = _volatile_time_matched(task, passage.text)
            meets = score.score_millionths >= self._policy.minimum_score_millionths and (
                volatile_matched or not self._policy.require_volatile_time_match
            )
            if not meets:
                continue
            semantic = SemanticCandidateObservation(
                provider_recipe_id=recipe_id,
                policy_id=self._policy.policy_id,
                score_millionths=score.score_millionths,
                volatile_time_matched=volatile_matched,
                meets_minimum=True,
                cache_hit=score.cache_hit,
            )
            candidates.append(
                candidate.model_copy(
                    update={
                        "semantic": semantic,
                        "term_coverage": max(0, score.score_millionths),
                        "retrieval_tier": 1,
                    }
                )
            )
        candidates.sort(
            key=lambda candidate: (
                -cast(SemanticCandidateObservation, candidate.semantic).score_millionths,
                str(candidate.scope.document_id),
                candidate.scope.version_id,
                candidate.scope.representation_id,
                candidate.source_order,
                candidate.evidence_id,
            )
        )
        admitted = (
            self._balanced(candidates)[: self._policy.top_k]
            if self._source_balanced
            else candidates[: self._policy.top_k]
        )
        self._admission_ns += time.perf_counter_ns() - admission_started
        return admitted

    def _cache_key(self, snapshot: CorpusSnapshot, limits: ContextCompileLimits) -> str:
        """Bind one compiler-lifetime cache entry to exact authority and limits."""
        return str(
            canonical_sha256(
                {
                    "domain": "openardp.semantic-candidate-cache",
                    "version": 1,
                    "snapshot": snapshot.model_dump(mode="json"),
                    "compile_limits": limits.model_dump(mode="json"),
                    "provider_limits": self._provider_limits.model_dump(mode="json"),
                    "provider_recipe_id": self._provider.recipe.recipe_id,
                    "rich_first": self._rich_first,
                }
            )
        )

    def _rich_authorities(self, snapshot: CorpusSnapshot) -> dict[RepresentationScope, str]:
        """Capture lightweight accepted-rich-row fingerprints when supported."""
        if not isinstance(self._catalog, RichEvidenceAuthorityCatalog):
            return {}
        result: dict[RepresentationScope, str] = {}
        for scope in snapshot.scopes:
            representation_scope = _representation_scope(scope)
            fingerprint = self._catalog.rich_evidence_authority_fingerprint(representation_scope)
            if fingerprint is not None:
                result[representation_scope] = fingerprint
        return result

    def _reconcile_catalog(
        self,
        candidates: list[ContextCandidate],
        rich_authorities: dict[RepresentationScope, str],
    ) -> None:
        """Recheck cached admitted metadata against current authoritative catalog rows."""
        by_scope: dict[
            RepresentationScope,
            tuple[RepresentationAggregate | None, RichRepresentationArtifacts | None],
        ] = {}
        verified_rich_scopes: set[RepresentationScope] = set()
        for candidate in candidates:
            representation_scope = _representation_scope(candidate.scope)
            if representation_scope in verified_rich_scopes:
                continue
            facts = by_scope.get(representation_scope)
            if facts is None:
                expected_rich = rich_authorities.get(representation_scope)
                if expected_rich is not None and isinstance(
                    self._catalog, RichEvidenceAuthorityCatalog
                ):
                    current = self._catalog.rich_evidence_authority_fingerprint(
                        representation_scope
                    )
                    if current != expected_rich:
                        raise ContextIntegrityFailure("semantic_cached_catalog_mismatch")
                    verified_rich_scopes.add(representation_scope)
                    continue
                facts = (
                    self._catalog.load_representation(representation_scope),
                    self._rich_catalog.load_rich_representation(representation_scope),
                )
                by_scope[representation_scope] = facts
            aggregate, rich = facts
            if isinstance(candidate.provenance, ContextBlockProvenance):
                if aggregate is None or not any(
                    str(row.block_id) == candidate.evidence_id
                    and row.object == candidate.body_object
                    and row.ordinal == candidate.source_order
                    for row in aggregate.blocks
                ):
                    raise ContextIntegrityFailure("semantic_cached_catalog_mismatch")
                continue
            if rich is None or not any(
                record.projection.evidence_projection_id == candidate.evidence_id
                and record.retrieval_object == candidate.body_object
                and record.ordinal == candidate.source_order
                for record in rich.bundle.records
            ):
                raise ContextIntegrityFailure("semantic_cached_catalog_mismatch")

    def _balanced(self, candidates: list[ContextCandidate]) -> list[ContextCandidate]:
        """Apply a ranked prefix then fair document round-robin before global top-k."""
        queues: dict[tuple[str, str], list[ContextCandidate]] = {}
        for candidate in candidates:
            key = (str(candidate.scope.document_id), candidate.scope.version_id)
            queue = queues.setdefault(key, [])
            if len(queue) < self._max_per_document:
                queue.append(candidate)
        prefix = candidates[: self._ranked_prefix]
        prefix_ids = {candidate.evidence_id for candidate in prefix}
        for key, queue in queues.items():
            queues[key] = [
                candidate for candidate in queue if candidate.evidence_id not in prefix_ids
            ]
        ordered = list(prefix)
        round_index = 0
        source_order = sorted(
            (key for key, queue in queues.items() if queue),
            key=lambda key: (
                -cast(SemanticCandidateObservation, queues[key][0].semantic).score_millionths,
                key,
            ),
        )
        while True:
            emitted = False
            for key in source_order:
                queue = queues[key]
                if round_index < len(queue):
                    ordered.append(queue[round_index])
                    emitted = True
            if not emitted:
                return ordered
            round_index += 1

    def _enumerate(
        self,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> list[tuple[ContextCandidate, SemanticPassage]]:
        entries: list[tuple[ContextCandidate, SemanticPassage]] = []
        for scope in snapshot.scopes:
            if cancel():
                raise ContextCompilationCancelled("cancelled_during_semantic_enumeration")
            representation_scope = _representation_scope(scope)
            rich = self._rich_catalog.load_rich_representation(representation_scope)
            aggregate = self._catalog.load_representation(representation_scope)
            if self._rich_first and rich is not None:
                self._rich_verifier(rich)
                for record in rich.bundle.records:
                    if record.projection.retrieval.media_type not in (
                        "text/plain",
                        "application/json",
                    ):
                        continue
                    self._guard_count(entries, limits)
                    entries.append(self._rich_entry(scope, record))
                continue
            if aggregate is not None:
                self._text_verifier(aggregate)
                for row in aggregate.blocks:
                    self._guard_count(entries, limits)
                    entries.append(self._text_entry(scope, row.object, row.ordinal))
                continue
            if rich is not None:
                self._rich_verifier(rich)
                for record in rich.bundle.records:
                    if record.projection.retrieval.media_type not in (
                        "text/plain",
                        "application/json",
                    ):
                        continue
                    self._guard_count(entries, limits)
                    entries.append(self._rich_entry(scope, record))
                continue
            raise ContextIntegrityFailure("semantic_snapshot_representation_missing")
        return entries

    def _guard_count(
        self,
        entries: list[tuple[ContextCandidate, SemanticPassage]],
        limits: ContextCompileLimits,
    ) -> None:
        if len(entries) >= min(limits.max_discovered, self._provider_limits.max_passages):
            raise ContextLimitExceeded("semantic_max_passages_exceeded")

    def _text_entry(
        self,
        scope: VersionScope,
        stored: StoredObject,
        ordinal: int,
    ) -> tuple[ContextCandidate, SemanticPassage]:
        payload = self._read(stored)
        try:
            block = validate_json(ContentBlock, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("semantic_block_invalid") from error
        if (
            block.document_id != scope.document_id
            or block.version_id != scope.version_id
            or block.representation_id != scope.representation_id
        ):
            raise ContextIntegrityFailure("semantic_block_scope_mismatch")
        text = (
            block.text
            if block.text is not None
            else canonical_json_bytes(block.structured).decode("utf-8")
        )
        provenance = ContextBlockProvenance(
            record_type="block",
            document_id=block.document_id,
            version_id=block.version_id,
            representation_id=block.representation_id,
            block_id=block.block_id,
            source=block.source,
        )
        candidate = ContextCandidate(
            evidence_id=str(block.block_id),
            scope=scope,
            provenance=provenance,
            representation=EvidenceRepresentation.EXACT,
            source_order=ordinal,
            body_object=stored,
            body_media_type="application/json",
            trust=block.trust,
            freshness=CandidateFreshness.CURRENT,
            term_coverage=0,
            occurrences=0,
            reason_code=SEMANTIC_MATCH_REASON,
            high_value=False,
        )
        return candidate, SemanticPassage(
            evidence_id=candidate.evidence_id,
            object_id=stored.object_id,
            text=text,
        )

    def _rich_entry(
        self,
        scope: VersionScope,
        record: Any,
    ) -> tuple[ContextCandidate, SemanticPassage]:
        projection = record.projection
        stored = record.retrieval_object
        payload = self._read(stored)
        try:
            body = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContextIntegrityFailure("semantic_rich_body_not_utf8") from error
        if projection.retrieval.media_type == "application/json":
            try:
                value: JsonValue = json.loads(body)
                if canonical_json_bytes(value) != payload:
                    raise ValueError
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise ContextIntegrityFailure("semantic_rich_body_noncanonical") from error
        provenance = ContextProjectionProvenance(
            record_type="evidence_projection",
            document_id=scope.document_id,
            version_id=scope.version_id,
            representation_id=scope.representation_id,
            source_version_id=projection.source_version_id,
            native_representation_id=projection.native_representation_id,
            evidence_reference_id=record.reference.evidence_reference_id,
            evidence_projection_id=projection.evidence_projection_id,
        )
        trust = DataTrustClassification(
            zone=projection.trust.effective_zone,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=projection.trust.integrity,
            sensitivity=projection.trust.sensitivity,
        )
        candidate = ContextCandidate(
            evidence_id=projection.evidence_projection_id,
            scope=scope,
            provenance=provenance,
            representation=(
                EvidenceRepresentation.EXACT
                if projection.retrieval.media_type == "text/plain"
                else EvidenceRepresentation.STRUCTURED
            ),
            source_order=record.ordinal,
            body_object=stored,
            body_media_type=projection.retrieval.media_type,
            trust=trust,
            freshness=CandidateFreshness.CURRENT,
            term_coverage=0,
            occurrences=0,
            reason_code=SEMANTIC_MATCH_REASON,
            high_value=False,
        )
        return candidate, SemanticPassage(
            evidence_id=candidate.evidence_id,
            object_id=stored.object_id,
            text=body,
        )

    def _read(self, stored: StoredObject) -> bytes:
        if stored.byte_length > self._provider_limits.max_passage_bytes:
            raise ContextLimitExceeded("semantic_passage_bytes_exceeded")
        try:
            verified = self._object_store.verify(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        except ObjectStoreError as error:
            raise ContextIntegrityFailure("semantic_evidence_object_invalid") from error
        if len(payload) != stored.byte_length:
            raise ContextIntegrityFailure("semantic_evidence_object_length_changed")
        return payload


class HybridRetrievalCandidateSource:
    """Preserve eligible lexical evidence before adding source-balanced semantics."""

    def __init__(
        self,
        lexical: ContextCandidateSource,
        semantic: ContextCandidateSource,
    ) -> None:
        """Bind already verified lexical and semantic candidate sources."""
        self._lexical = lexical
        self._semantic = semantic

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Return minimum-relevant lexical candidates first, then semantic additions."""
        lexical = self._lexical.discover(task, snapshot, limits, cancel)
        relevant = tuple(
            candidate
            for candidate in lexical
            if candidate.relevance is not None and candidate.relevance.meets_minimum
        )
        semantic = self._semantic.discover(task, snapshot, limits, cancel)
        lexical_ids = {
            (
                str(candidate.scope.document_id),
                candidate.scope.version_id,
                candidate.scope.representation_id,
                candidate.evidence_id,
                candidate.representation.value,
            )
            for candidate in relevant
        }
        additions = tuple(
            candidate
            for candidate in semantic
            if (
                str(candidate.scope.document_id),
                candidate.scope.version_id,
                candidate.scope.representation_id,
                candidate.evidence_id,
                candidate.representation.value,
            )
            not in lexical_ids
        )
        return (*relevant, *additions)


def _volatile_time_matched(task: str, text: str) -> bool:
    policy = RelevancePolicy(minimum_score_millionths=0)
    signals = tuple(
        signal
        for signal in extract_relevance_signals(task, policy)
        if signal.signal_class is RelevanceSignalClass.VOLATILE_TIME
    )
    if not signals:
        return True
    tokens = {
        unicodedata.normalize("NFC", match.group(0)).casefold() for match in _TOKEN.finditer(text)
    }
    return all(signal.value in tokens for signal in signals)


def _representation_scope(scope: VersionScope) -> RepresentationScope:
    return RepresentationScope(
        document_id=scope.document_id,
        version_id=scope.version_id,
        representation_id=scope.representation_id,
    )


__all__ = [
    "SEMANTIC_MATCH_REASON",
    "HybridRetrievalCandidateSource",
    "SemanticContextCandidateSource",
]
