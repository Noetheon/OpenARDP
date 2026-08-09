"""Verified deterministic lexical candidate discovery for context compilation."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from pydantic import JsonValue, ValidationError

from openardp.domain.block import ContentBlock
from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    validate_json,
)
from openardp.domain.context import EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    CandidateFreshness,
    ContextBlockProvenance,
    ContextCandidate,
    ContextCompileLimits,
    ContextProjectionProvenance,
    CorpusSnapshot,
)
from openardp.domain.context_relevance import RelevancePolicy, evaluate_candidate_relevance
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.rich_ingestion import RichEvidenceRecord, RichRepresentationArtifacts
from openardp.domain.search import (
    MAX_QUERY_ITEMS,
    MAX_SEARCH_LIMIT,
    MAX_TERM_CHARACTERS,
    SearchFilters,
    SearchMatchRow,
    block_text_for_index,
    indexed_text_hash,
)
from openardp.domain.storage import StoredObject
from openardp.domain.visual import VisualEvidenceDescriptor, VisualPageRaster
from openardp.ports.catalog import (
    Catalog,
    RichCatalog,
    RichEvidenceAuthorityCatalog,
    SearchIndexDrifted,
    SearchIndexIncomplete,
    VisualCatalog,
)
from openardp.ports.context import (
    CancellationCheck,
    ContextCompilationCancelled,
    ContextIntegrityFailure,
    ContextLimitExceeded,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError

TEXT_MATCH_REASON = "fts_lexical_match"
RICH_MATCH_REASON = "rich_lexical_scan"
_MAX_PREPARED_LEXICAL_TEXT_BYTES = 67_108_864


@dataclass(frozen=True, slots=True)
class _PreparedRichLexicalCorpus:
    cache_key: str
    authority_by_scope: dict[tuple[str, str, str], str | None]
    entries: tuple[tuple[ContextCandidate, str], ...]
    total_text_bytes: int


def lexical_query_items(task: str) -> tuple[str, ...]:
    """Normalize untrusted task text into bounded deterministic lexical items."""
    items = tuple(dict.fromkeys(task.split()))
    if len(items) > MAX_QUERY_ITEMS:
        raise ContextLimitExceeded("task_lexical_items_exceeded")
    if any(len(item) > MAX_TERM_CHARACTERS for item in items):
        raise ContextLimitExceeded("task_lexical_item_length_exceeded")
    return items


def lexical_match_expression(items: tuple[str, ...]) -> str:
    """Translate items into one deterministic FTS5 disjunction used as a bound parameter."""
    return " OR ".join(f'"{item.replace(chr(34), chr(34) * 2)}"' for item in items)


def lexical_score(text: str, items: tuple[str, ...]) -> tuple[int, int]:
    """Count exact casefolded item coverage and occurrences without floats."""
    folded = text.casefold()
    counts = [folded.count(item.casefold()) for item in items]
    coverage = sum(1 for count in counts if count > 0)
    return coverage, sum(counts)


def _scope_key(scope: VersionScope | RepresentationScope) -> tuple[str, str, str]:
    return (str(scope.document_id), scope.version_id, scope.representation_id)


def _read_verified(object_store: ObjectStore, stored: StoredObject) -> bytes:
    """Read one object only after digest, length and shape verification."""
    try:
        verified = object_store.verify(stored.object_id, expected_length=stored.byte_length)
        payload = b"".join(object_store.iter_chunks(verified.object_id))
    except ObjectStoreError as error:
        raise ContextIntegrityFailure("evidence_object_invalid") from error
    if len(payload) != verified.byte_length:
        raise ContextIntegrityFailure("evidence_object_length_changed")
    return payload


class TextLexicalCandidateSource:
    """Verified FTS-backed discovery over authoritative F002 text blocks."""

    def __init__(self, object_store: ObjectStore, catalog: Catalog) -> None:
        """Bind verified-read persistence boundaries without provider dependencies."""
        self._object_store = object_store
        self._catalog = catalog

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Return verified snapshot candidates and body-free stale index facts."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_text_discovery")
        items = lexical_query_items(task)
        if not items:
            return ()
        snapshot_keys = {_scope_key(scope) for scope in snapshot.scopes}
        match = lexical_match_expression(items)
        candidates: list[ContextCandidate] = []
        for document_id in _snapshot_document_ids(snapshot):
            for row in self._match_rows(document_id, match):
                if cancel():
                    raise ContextCompilationCancelled("cancelled_during_text_verification")
                if len(candidates) >= limits.max_discovered:
                    raise ContextLimitExceeded("max_discovered_exceeded")
                if _scope_key(row.scope) in snapshot_keys:
                    verified = self._verified_candidate(row, items, limits)
                    if verified is not None:
                        candidates.append(verified)
                else:
                    self._require_catalog_version(row)
                # Rows from versions outside the exact snapshot stay invisible:
                # replay must not float to newer heads, and superseded rows must
                # not enter fresh receipts as stale decisions because decision
                # scopes have to stay inside the corpus snapshot.
        return tuple(candidates)

    def _require_catalog_version(self, row: SearchMatchRow) -> None:
        """Fail closed when an accelerator row has no catalog version at all."""
        version = self._catalog.get_version(row.scope.document_id, row.scope.version_id)
        if version is None:
            raise ContextIntegrityFailure("accelerator_drifted")

    def _match_rows(
        self,
        document_id: UUID,
        match: str,
    ) -> Iterator[SearchMatchRow]:
        """Stream every FTS row through deterministic bounded offset pages."""
        offset = 0
        available: int | None = None
        identities: set[tuple[str, str, str]] = set()
        while available is None or offset < available:
            filters = SearchFilters(
                document_id=document_id,
                include_history=True,
                limit=MAX_SEARCH_LIMIT,
            )
            try:
                page = self._catalog.search_block_entries(
                    match=match,
                    filters=filters,
                    offset=offset,
                )
            except SearchIndexIncomplete as error:
                raise ContextIntegrityFailure("accelerator_incomplete") from error
            except SearchIndexDrifted as error:
                raise ContextIntegrityFailure("accelerator_drifted") from error
            if available is None:
                available = page.available
            elif page.available != available:
                raise ContextIntegrityFailure("accelerator_changed_during_paging")
            if not page.rows and offset < available:
                raise ContextIntegrityFailure("accelerator_page_incomplete")
            for row in page.rows:
                identity = (str(row.scope.document_id), row.scope.version_id, str(row.block_id))
                if identity in identities:
                    raise ContextIntegrityFailure("accelerator_page_drift")
                identities.add(identity)
                yield row
            offset += len(page.rows)
        if available != len(identities):
            raise ContextIntegrityFailure("accelerator_page_drift")

    def _verified_candidate(
        self,
        row: SearchMatchRow,
        items: tuple[str, ...],
        limits: ContextCompileLimits,
    ) -> ContextCandidate | None:
        """Reverify one indexed hit against catalog and CAS facts, then rescore."""
        if row.object_byte_length > limits.max_body_bytes:
            raise ContextLimitExceeded("max_body_bytes_exceeded")
        stored = StoredObject(object_id=row.object_id, byte_length=row.object_byte_length)
        payload = _read_verified(self._object_store, stored)
        try:
            block = validate_json(ContentBlock, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("indexed_block_invalid") from error
        if (
            block.block_id != row.block_id
            or block.kind != row.kind
            or str(block.document_id) != str(row.scope.document_id)
            or block.version_id != row.scope.version_id
            or block.representation_id != row.scope.representation_id
        ):
            raise ContextIntegrityFailure("indexed_block_mismatch")
        text = block_text_for_index(block.text)
        if indexed_text_hash(text) != row.text_hash:
            raise ContextIntegrityFailure("indexed_text_drift")
        coverage, occurrences = lexical_score(text, items)
        if coverage == 0:
            # The FTS tokenizer can match token sequences the exact casefolded
            # rescore rejects; exact rescoring is authoritative.
            return None
        provenance = ContextBlockProvenance(
            record_type="block",
            document_id=block.document_id,
            version_id=block.version_id,
            representation_id=block.representation_id,
            block_id=block.block_id,
            source=block.source,
        )
        return ContextCandidate(
            evidence_id=str(block.block_id),
            scope=VersionScope(
                document_id=block.document_id,
                version_id=block.version_id,
                representation_id=block.representation_id,
            ),
            provenance=provenance,
            representation=EvidenceRepresentation.EXACT,
            source_order=block.order,
            body_object=stored,
            body_media_type="application/json",
            trust=block.trust,
            freshness=CandidateFreshness.CURRENT,
            term_coverage=coverage,
            occurrences=occurrences,
            reason_code=TEXT_MATCH_REASON,
            high_value=False,
        )


class RichLexicalCandidateSource:
    """Bounded provider-free scan of accepted F006 evidence projections."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: RichCatalog,
        *,
        representation_verifier: Callable[[RichRepresentationArtifacts], None],
        prepared_snapshot: bool = False,
        relevance_policy: RelevancePolicy | None = None,
    ) -> None:
        """Bind provider-neutral persistence and integrity boundaries."""
        self._object_store = object_store
        self._catalog = catalog
        self._representation_verifier = representation_verifier
        self._prepared_snapshot = prepared_snapshot
        self._relevance_policy = relevance_policy
        self._prepared: _PreparedRichLexicalCorpus | None = None

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Return verified lexical candidates from accepted rich projections."""
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_rich_discovery")
        items = lexical_query_items(task)
        if not items:
            return ()
        cache_key = str(
            canonical_sha256(
                {
                    "domain": "openardp.prepared-rich-lexical-corpus",
                    "version": 1,
                    "snapshot": snapshot.model_dump(mode="json"),
                    "max_discovered": limits.max_discovered,
                    "max_body_bytes": limits.max_body_bytes,
                }
            )
        )
        cached = self._prepared if self._prepared_snapshot else None
        if cached is not None and cached.cache_key == cache_key:
            self._reconcile_prepared(snapshot, cached)
            return self._score_prepared(task, cached.entries, items, limits, cancel)
        candidates: list[ContextCandidate] = []
        prepared_entries: list[tuple[ContextCandidate, str]] = []
        authority_by_scope: dict[tuple[str, str, str], str | None] = {}
        total_text_bytes = 0
        for scope in snapshot.scopes:
            artifacts = self._catalog.load_rich_representation(_representation_scope(scope))
            authority_by_scope[_scope_key(scope)] = self._catalog_authority(scope, artifacts)
            if artifacts is None:
                continue
            try:
                self._representation_verifier(artifacts)
            except ContextCompilationCancelled:
                raise
            except Exception as error:
                raise ContextIntegrityFailure("rich_representation_integrity_failed") from error
            for record in artifacts.bundle.records:
                if cancel():
                    raise ContextCompilationCancelled("cancelled_during_rich_verification")
                projection = record.projection
                if projection.retrieval.media_type not in ("text/plain", "application/json"):
                    continue
                if record.retrieval_object.byte_length > limits.max_body_bytes:
                    raise ContextLimitExceeded("rich_body_limit_exceeded")
                if len(candidates) >= limits.max_discovered:
                    raise ContextLimitExceeded("max_discovered_exceeded")
                candidate, body = self._verified_entry(scope, record)
                total_text_bytes += len(body.encode("utf-8"))
                if total_text_bytes > _MAX_PREPARED_LEXICAL_TEXT_BYTES:
                    raise ContextLimitExceeded("prepared_lexical_text_limit_exceeded")
                prepared_entries.append((candidate, body))
                coverage, occurrences = lexical_score(body, items)
                if coverage:
                    candidates.append(self._annotate(candidate, task, body, coverage, occurrences))
        if self._prepared_snapshot:
            self._prepared = _PreparedRichLexicalCorpus(
                cache_key=cache_key,
                authority_by_scope=authority_by_scope,
                entries=tuple(prepared_entries),
                total_text_bytes=total_text_bytes,
            )
        return tuple(candidates)

    def _verified_entry(
        self,
        scope: VersionScope,
        record: RichEvidenceRecord,
    ) -> tuple[ContextCandidate, str]:
        """Verify one accepted projection and return its query-independent base."""
        projection = record.projection
        payload = _read_verified(self._object_store, record.retrieval_object)
        try:
            body = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContextIntegrityFailure("rich_body_not_utf8") from error
        if projection.retrieval.media_type == "application/json":
            try:
                value: JsonValue = json.loads(body)
                if canonical_json_bytes(value) != payload:
                    raise ValueError
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise ContextIntegrityFailure("rich_body_noncanonical_json") from error
        try:
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
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("rich_projection_scope_mismatch") from error
        trust = DataTrustClassification(
            zone=projection.trust.effective_zone,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=projection.trust.integrity,
            sensitivity=projection.trust.sensitivity,
        )
        return (
            ContextCandidate(
                evidence_id=projection.evidence_projection_id,
                scope=scope,
                provenance=provenance,
                representation=EvidenceRepresentation.EXACT
                if projection.retrieval.media_type == "text/plain"
                else EvidenceRepresentation.STRUCTURED,
                source_order=record.ordinal,
                body_object=record.retrieval_object,
                body_media_type=projection.retrieval.media_type,
                trust=trust,
                freshness=CandidateFreshness.CURRENT,
                term_coverage=0,
                occurrences=0,
                reason_code=RICH_MATCH_REASON,
                high_value=False,
            ),
            body,
        )

    def _score_prepared(
        self,
        task: str,
        entries: tuple[tuple[ContextCandidate, str], ...],
        items: tuple[str, ...],
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Rescore cached bodies and reverify every returned match against CAS."""
        candidates: list[ContextCandidate] = []
        for candidate, body in entries:
            if cancel():
                raise ContextCompilationCancelled("cancelled_during_rich_verification")
            coverage, occurrences = lexical_score(body, items)
            if not coverage:
                continue
            if len(candidates) >= limits.max_discovered:
                raise ContextLimitExceeded("max_discovered_exceeded")
            stored = candidate.body_object
            if stored is None or stored.byte_length > limits.max_body_bytes:
                raise ContextLimitExceeded("rich_body_limit_exceeded")
            payload = _read_verified(self._object_store, stored)
            if payload.decode("utf-8") != body:
                raise ContextIntegrityFailure("prepared_lexical_body_mismatch")
            candidates.append(self._annotate(candidate, task, body, coverage, occurrences))
        return tuple(candidates)

    def _annotate(
        self,
        candidate: ContextCandidate,
        task: str,
        body: str,
        coverage: int,
        occurrences: int,
    ) -> ContextCandidate:
        """Attach query-specific lexical and optional exact relevance observations."""
        update: dict[str, object] = {
            "term_coverage": coverage,
            "occurrences": occurrences,
        }
        if self._relevance_policy is not None:
            try:
                update["relevance"] = evaluate_candidate_relevance(
                    task, body, self._relevance_policy
                )
            except ValueError as error:
                raise ContextLimitExceeded("relevance_task_limit_exceeded") from error
        return candidate.model_copy(update=update)

    def _reconcile_prepared(
        self,
        snapshot: CorpusSnapshot,
        prepared: _PreparedRichLexicalCorpus,
    ) -> None:
        """Compare cached body-free evidence facts with current immutable catalog rows."""
        current: dict[tuple[str, str, str], str | None] = {}
        for scope in snapshot.scopes:
            artifacts = (
                None
                if isinstance(self._catalog, RichEvidenceAuthorityCatalog)
                else self._catalog.load_rich_representation(_representation_scope(scope))
            )
            current[_scope_key(scope)] = self._catalog_authority(scope, artifacts)
        if current != prepared.authority_by_scope:
            raise ContextIntegrityFailure("prepared_lexical_catalog_mismatch")

    def _catalog_authority(
        self,
        scope: VersionScope,
        artifacts: RichRepresentationArtifacts | None,
    ) -> str | None:
        """Prefer a lightweight catalog-native digest with a portable fallback."""
        if isinstance(self._catalog, RichEvidenceAuthorityCatalog):
            return self._catalog.rich_evidence_authority_fingerprint(_representation_scope(scope))
        return self._authority_fingerprint(artifacts) if artifacts is not None else None

    @staticmethod
    def _authority_fingerprint(artifacts: RichRepresentationArtifacts) -> str:
        """Identify only catalog-authoritative evidence and retrieval-object facts."""
        return str(
            canonical_sha256(
                [
                    {
                        "evidence_projection_id": record.projection.evidence_projection_id,
                        "ordinal": record.ordinal,
                        "retrieval_object": record.retrieval_object.model_dump(mode="json"),
                        "media_type": record.projection.retrieval.media_type,
                    }
                    for record in artifacts.bundle.records
                ]
            )
        )


class VisualContextCandidateSource:
    """Verified bounded discovery of pre-materialized canonical visual handles."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: RichCatalog | VisualCatalog,
    ) -> None:
        """Bind visual catalog and CAS verification without renderer authority."""
        self._object_store = object_store
        self._rich_catalog = cast("RichCatalog", catalog)
        self._visual_catalog = cast("VisualCatalog", catalog)

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Return handle-only candidates pinned to the exact supplied snapshot."""
        del task
        if cancel():
            raise ContextCompilationCancelled("cancelled_before_visual_discovery")
        candidates: list[ContextCandidate] = []
        for scope in snapshot.scopes:
            rich = self._rich_catalog.load_rich_representation(_representation_scope(scope))
            if rich is None:
                continue
            projection_by_id = {
                projection.evidence_projection_id: projection
                for projection in rich.bundle.projections
            }
            for record in self._visual_catalog.list_visual_evidence(_representation_scope(scope)):
                if cancel():
                    raise ContextCompilationCancelled("cancelled_during_visual_verification")
                if len(candidates) >= limits.max_discovered:
                    raise ContextLimitExceeded("max_discovered_exceeded")
                if not record.canonical_context_profile:
                    continue
                commit = self._visual_catalog.load_visual_evidence(record.visual_evidence_id)
                if commit is None:
                    raise ContextIntegrityFailure("visual_record_missing")
                descriptor = self._verified_descriptor(commit.descriptor_object)
                raster = self._verified_raster(commit.raster_record_object)
                if descriptor != commit.descriptor or raster != commit.page_raster:
                    raise ContextIntegrityFailure("visual_record_object_mismatch")
                self._verify_binary(commit.page_raster.raster_object)
                self._verify_binary(commit.crop_object)
                projection = projection_by_id.get(descriptor.evidence_projection_id)
                if (
                    projection is None
                    or projection.reference.evidence_reference_id
                    != descriptor.evidence_reference_id
                    or projection.reference.anchor != descriptor.target_anchor
                    or projection.trust != descriptor.trust
                ):
                    raise ContextIntegrityFailure("visual_parent_projection_mismatch")
                provenance = ContextProjectionProvenance(
                    record_type="evidence_projection",
                    document_id=scope.document_id,
                    version_id=scope.version_id,
                    representation_id=scope.representation_id,
                    source_version_id=projection.source_version_id,
                    native_representation_id=projection.native_representation_id,
                    evidence_reference_id=projection.reference.evidence_reference_id,
                    evidence_projection_id=projection.evidence_projection_id,
                )
                trust = DataTrustClassification(
                    zone=projection.trust.effective_zone,
                    role=ContentRole.DATA,
                    instruction_execution_allowed=False,
                    integrity=projection.trust.integrity,
                    sensitivity=projection.trust.sensitivity,
                )
                candidates.append(
                    ContextCandidate(
                        evidence_id=projection.evidence_projection_id,
                        scope=scope,
                        provenance=provenance,
                        representation=EvidenceRepresentation.VISUAL_HANDLE,
                        source_order=projection.ordinal,
                        artifact_handle=record.descriptor_object.object_id,
                        artifact_id=record.descriptor_object.object_id,
                        cost_object=record.descriptor_object,
                        trust=trust,
                        freshness=CandidateFreshness.CURRENT,
                        term_coverage=0,
                        occurrences=0,
                        reason_code="visual_evidence_materialized",
                        high_value=False,
                    )
                )
        return tuple(candidates)

    def _verified_descriptor(self, stored: StoredObject) -> VisualEvidenceDescriptor:
        payload = _read_verified(self._object_store, stored)
        try:
            descriptor = validate_json(VisualEvidenceDescriptor, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("visual_descriptor_invalid") from error
        if canonical_json_bytes(descriptor.model_dump(mode="json")) != payload:
            raise ContextIntegrityFailure("visual_descriptor_noncanonical")
        return descriptor

    def _verified_raster(self, stored: StoredObject) -> VisualPageRaster:
        payload = _read_verified(self._object_store, stored)
        try:
            raster = validate_json(VisualPageRaster, payload)
        except (ValidationError, ValueError) as error:
            raise ContextIntegrityFailure("visual_raster_record_invalid") from error
        if canonical_json_bytes(raster.model_dump(mode="json")) != payload:
            raise ContextIntegrityFailure("visual_raster_record_noncanonical")
        return raster

    def _verify_binary(self, stored: StoredObject) -> None:
        try:
            self._object_store.verify(stored.object_id, expected_length=stored.byte_length)
        except ObjectStoreError as error:
            raise ContextIntegrityFailure("visual_binary_invalid") from error


def _snapshot_document_ids(snapshot: CorpusSnapshot) -> tuple[UUID, ...]:
    """Return sorted unique document identifiers of one exact snapshot."""
    return tuple(sorted({scope.document_id for scope in snapshot.scopes}, key=str))


def _representation_scope(scope: VersionScope) -> RepresentationScope:
    return RepresentationScope(
        document_id=scope.document_id,
        version_id=scope.version_id,
        representation_id=scope.representation_id,
    )


__all__ = [
    "RICH_MATCH_REASON",
    "TEXT_MATCH_REASON",
    "RichLexicalCandidateSource",
    "TextLexicalCandidateSource",
    "VisualContextCandidateSource",
    "lexical_match_expression",
    "lexical_query_items",
    "lexical_score",
]
