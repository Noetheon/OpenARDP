"""Verified relevance-observation adapter tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.context_relevance import RelevanceObservingCandidateSource
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    SourceLocator,
    TrustZone,
)
from openardp.domain.context import ContextMode, EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    CandidateFreshness,
    ContextBlockProvenance,
    ContextCandidate,
    ContextCompileLimits,
    ContextSelectionPolicy,
    CorpusSnapshot,
)
from openardp.domain.context_relevance import RelevancePolicy, evaluate_candidate_relevance
from openardp.domain.identity import block_content_hash, canonical_json_bytes
from openardp.ports.context import CancellationCheck, ContextCompilationCancelled
from openardp.services.context_compiler import classify_candidates

NOW = datetime(2026, 8, 3, 0, 0, tzinfo=UTC)
DOCUMENT_ID = UUID("01890f62-24e8-7c00-8000-000000000026")
BLOCK_ID = UUID("12345678-1234-4234-9234-123456789026")
SCOPE = VersionScope(
    document_id=DOCUMENT_ID,
    version_id="sha256:" + "1" * 64,
    representation_id="sha256:" + "2" * 64,
)


@dataclass
class _StaticSource:
    candidates: tuple[ContextCandidate, ...]
    calls: int = 0

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        del task, snapshot, limits
        self.calls += 1
        if cancel():
            raise ContextCompilationCancelled("cancelled_static_source")
        return self.candidates


def _candidate(tmp_path: Path, text: str) -> tuple[FilesystemObjectStore, ContextCandidate]:
    store = FilesystemObjectStore(tmp_path / "cas")
    block = ContentBlock(
        schema_version="0.1.0",
        block_id=BLOCK_ID,
        document_id=DOCUMENT_ID,
        version_id=SCOPE.version_id,
        representation_id=SCOPE.representation_id,
        kind=BlockKind.PARAGRAPH,
        order=0,
        text=text,
        canonical_hash=block_content_hash(
            kind=BlockKind.PARAGRAPH.value,
            text=text,
            structured=None,
            asset_id=None,
        ),
        source=SourceLocator(extraction_method="synthetic"),
        trust=DataTrustClassification(
            zone=TrustZone.EXTERNAL_UNTRUSTED,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.PUBLIC,
        ),
    )
    stored = store.put_chunks((canonical_json_bytes(block.model_dump(mode="json")),))
    candidate = ContextCandidate(
        evidence_id=str(BLOCK_ID),
        scope=SCOPE,
        provenance=ContextBlockProvenance(
            record_type="block",
            document_id=DOCUMENT_ID,
            version_id=SCOPE.version_id,
            representation_id=SCOPE.representation_id,
            block_id=BLOCK_ID,
            source=block.source,
        ),
        representation=EvidenceRepresentation.EXACT,
        source_order=0,
        body_object=stored,
        body_media_type="application/json",
        trust=block.trust,
        freshness=CandidateFreshness.CURRENT,
        term_coverage=2,
        occurrences=2,
        reason_code="fts_lexical_match",
        high_value=False,
    )
    return store, candidate


def _snapshot() -> CorpusSnapshot:
    return CorpusSnapshot(scopes=(SCOPE,), created_at=NOW)


def test_decorator_reverifies_block_and_attaches_body_free_observation(tmp_path: Path) -> None:
    """The adapter scores exact CAS content without altering evidence identity."""
    store, candidate = _candidate(tmp_path, "alpha beta")
    source = _StaticSource((candidate,))
    decorator = RelevanceObservingCandidateSource(store, (source,), RelevancePolicy())

    observed = decorator.discover(
        "alpha beta gamma delta",
        _snapshot(),
        ContextCompileLimits(),
        lambda: False,
    )

    assert source.calls == 1
    assert len(observed) == 1
    assert observed[0].evidence_id == candidate.evidence_id
    assert observed[0].body_object == candidate.body_object
    assert observed[0].relevance is not None
    assert observed[0].relevance.score_millionths == 500_000
    assert observed[0].relevance.meets_minimum is True


def test_decorator_records_below_floor_without_dropping_candidate(tmp_path: Path) -> None:
    """Compiler classification, not discovery, owns the exhaustive rejection partition."""
    store, candidate = _candidate(tmp_path, "alpha")
    decorator = RelevanceObservingCandidateSource(
        store,
        (_StaticSource((candidate,)),),
        RelevancePolicy(minimum_score_millionths=500_000),
    )

    observed = decorator.discover(
        "alpha beta gamma delta",
        _snapshot(),
        ContextCompileLimits(),
        lambda: False,
    )

    assert observed[0].relevance is not None
    assert observed[0].relevance.score_millionths == 250_000
    assert observed[0].relevance.meets_minimum is False


def test_decorator_checks_cancellation_between_sources(tmp_path: Path) -> None:
    """Cancellation remains a typed failure rather than evidence abstention."""
    store, candidate = _candidate(tmp_path, "alpha")
    calls = 0

    def cancel() -> bool:
        nonlocal calls
        calls += 1
        return calls > 1

    decorator = RelevanceObservingCandidateSource(
        store,
        (_StaticSource((candidate,)), _StaticSource((candidate,))),
        RelevancePolicy(),
    )

    with pytest.raises(ContextCompilationCancelled):
        decorator.discover("alpha", _snapshot(), ContextCompileLimits(), cancel)


def test_mixed_relevance_is_partitioned_without_discovery_filtering(tmp_path: Path) -> None:
    """Classification retains a strong candidate and audits a weak candidate once."""
    store, candidate = _candidate(tmp_path, "alpha")
    policy = RelevancePolicy(minimum_score_millionths=500_000)
    weak = evaluate_candidate_relevance("alpha beta gamma delta", "alpha", policy)
    strong = evaluate_candidate_relevance("alpha beta gamma delta", "alpha beta", policy)
    classified = classify_candidates(
        (
            candidate.model_copy(update={"relevance": weak}),
            candidate.model_copy(
                update={"evidence_id": "second-evidence", "source_order": 1, "relevance": strong}
            ),
        ),
        ContextSelectionPolicy(mode=ContextMode.EXACT),
        relevance_policy=policy,
    )

    assert [item.evidence_id for item in classified.ordered] == ["second-evidence"]
    assert [(item.evidence_id, reason) for item, reason in classified.rejected] == [
        (candidate.evidence_id, "insufficient_relevance")
    ]
    assert candidate.body_object is not None
    assert store.verify(candidate.body_object.object_id) == candidate.body_object


@pytest.mark.parametrize(
    ("task", "body"),
    [
        ("NASA deployment 2027", "NASA deployment is scheduled for 2027."),
        ("CVE-2021-44228 guidance", "CVE-2021-44228 guidance is retained."),
    ],
)
def test_high_information_acronym_identifier_and_year_survive(
    tmp_path: Path,
    task: str,
    body: str,
) -> None:
    """Short exact high-information evidence remains eligible under the default floor."""
    store, candidate = _candidate(tmp_path, body)
    observed = RelevanceObservingCandidateSource(
        store,
        (_StaticSource((candidate,)),),
        RelevancePolicy(),
    ).discover(task, _snapshot(), ContextCompileLimits(), lambda: False)

    assert observed[0].relevance is not None
    assert observed[0].relevance.meets_minimum is True
