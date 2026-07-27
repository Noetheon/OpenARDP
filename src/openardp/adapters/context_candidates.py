"""Verified deterministic lexical candidate discovery for context compilation."""

from __future__ import annotations

import json
from collections.abc import Callable
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
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.rich_ingestion import RichEvidenceRecord, RichRepresentationArtifacts
from openardp.domain.search import (
    MAX_QUERY_ITEMS,
    MAX_TERM_CHARACTERS,
    SearchFilters,
    SearchMatchPage,
    SearchMatchRow,
    block_text_for_index,
    indexed_text_hash,
)
from openardp.domain.storage import StoredObject
from openardp.ports.catalog import (
    Catalog,
    RichCatalog,
    SearchIndexDrifted,
    SearchIndexIncomplete,
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
            page = self._match_page(document_id, match)
            if page.available > len(page.rows):
                raise ContextLimitExceeded("discovery_page_exhausted")
            for row in page.rows:
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

    def _match_page(self, document_id: UUID, match: str) -> SearchMatchPage:
        """Execute one coverage-checked FTS query with closed failure mapping."""
        filters = SearchFilters(
            document_id=document_id,
            include_history=True,
        )
        try:
            return self._catalog.search_block_entries(match=match, filters=filters)
        except SearchIndexIncomplete as error:
            raise ContextIntegrityFailure("accelerator_incomplete") from error
        except SearchIndexDrifted as error:
            raise ContextIntegrityFailure("accelerator_drifted") from error

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
    ) -> None:
        """Bind provider-neutral persistence and integrity boundaries."""
        self._object_store = object_store
        self._catalog = catalog
        self._representation_verifier = representation_verifier

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
        candidates: list[ContextCandidate] = []
        for scope in snapshot.scopes:
            artifacts = self._catalog.load_rich_representation(_representation_scope(scope))
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
                candidate = self._verified_candidate(scope, record, items)
                if candidate is not None:
                    candidates.append(candidate)
        return tuple(candidates)

    def _verified_candidate(
        self,
        scope: VersionScope,
        record: RichEvidenceRecord,
        items: tuple[str, ...],
    ) -> ContextCandidate | None:
        """Verify one accepted projection body exactly and rescore it deterministically."""
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
        coverage, occurrences = lexical_score(body, items)
        if coverage == 0:
            return None
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
        return ContextCandidate(
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
            term_coverage=coverage,
            occurrences=occurrences,
            reason_code=RICH_MATCH_REASON,
            high_value=False,
        )


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
    "lexical_match_expression",
    "lexical_query_items",
    "lexical_score",
]
