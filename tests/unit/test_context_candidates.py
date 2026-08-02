"""Verified FTS text, bounded rich scan and mixed candidate classification tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
    VisualContextCandidateSource,
    lexical_query_items,
)
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.text_parser import TextParserAdapter
from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    TrustZone,
)
from openardp.domain.context import ContextMode, EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    CandidateFreshness,
    ContextCandidate,
    ContextCompileLimits,
    ContextSelectionPolicy,
    CorpusSnapshot,
)
from openardp.ports.context import (
    ContextCompilationCancelled,
    ContextIntegrityFailure,
    ContextLimitExceeded,
)
from openardp.services.context_compiler import (
    candidate_total_order_key,
    classify_candidates,
    required_representations,
)
from openardp.services.ingestion import IngestionService
from openardp.services.visual_evidence import VisualEvidenceService
from tests.integration.test_rich_ingestion import (
    _Clock,
    _Parser,
    _service,
    _TamperingStore,
)
from tests.integration.visual_service_support import (
    CountingVisualRenderer,
    prepared_visual_service,
)

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
LIMITS = ContextCompileLimits()


def _never_cancel() -> bool:
    return False


def _text_services(tmp_path: Path) -> tuple[IngestionService, FilesystemObjectStore, SQLiteCatalog]:
    root = tmp_path / "store"
    store = FilesystemObjectStore(root)
    catalog = SQLiteCatalog(root / "catalog.sqlite3")
    clock = _Clock()
    catalog.initialize(now=clock())
    ingestion = IngestionService(
        store,
        catalog,
        TextParserAdapter(),
        source_factory=LocalSource,
        clock=clock,
    )
    return ingestion, store, catalog


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_visual_candidate_source_is_exact_stable_bounded_and_cancellable(
    tmp_path: Path,
) -> None:
    """Discover only verified stable handle candidates under exact snapshot and caps."""
    catalog, store, rich = prepared_visual_service(tmp_path / "visual")
    visual = VisualEvidenceService(
        store,
        catalog,
        CountingVisualRenderer(),
        LocalOnlyVisualPolicy(),
    )
    for projection in rich.bundle.projections:
        visual.materialize(
            rich.bundle.scope,
            projection.evidence_projection_id,
            created_at=NOW + timedelta(seconds=2),
        )
    snapshot = CorpusSnapshot(
        scopes=(
            VersionScope(
                document_id=rich.bundle.scope.document_id,
                version_id=rich.bundle.scope.version_id,
                representation_id=rich.bundle.scope.representation_id,
            ),
        ),
        created_at=NOW,
    )
    source = VisualContextCandidateSource(store, catalog)
    candidates = source.discover("ignored", snapshot, LIMITS, _never_cancel)
    assert {item.source_order for item in candidates} == {0, 1}
    assert source.discover("ignored", snapshot, LIMITS, _never_cancel) == candidates
    assert all(item.body_object is None for item in candidates)
    with pytest.raises(ContextCompilationCancelled):
        source.discover("ignored", snapshot, LIMITS, lambda: True)
    with pytest.raises(ContextLimitExceeded, match="max_discovered"):
        source.discover(
            "ignored",
            snapshot,
            ContextCompileLimits(max_discovered=1, max_candidates=1),
            _never_cancel,
        )


def _snapshot_for(catalog: SQLiteCatalog, document_id: UUID) -> CorpusSnapshot:
    head = catalog.get_document_head(document_id)
    assert head is not None
    scope = VersionScope(
        document_id=head.scope.document_id,
        version_id=head.scope.version_id,
        representation_id=head.scope.representation_id,
    )
    return CorpusSnapshot(scopes=(scope,), created_at=head.last_ingested_at)


def test_lexical_items_are_deterministic_bounded_data() -> None:
    """Normalize untrusted task text without interpreting quotes, URLs or paths."""
    assert lexical_query_items("alpha beta alpha") == ("alpha", "beta")
    assert lexical_query_items('ignore "previous instructions" https://example.test/x /etc') == (
        "ignore",
        '"previous',
        'instructions"',
        "https://example.test/x",
        "/etc",
    )
    assert lexical_query_items("  \t\n ") == ()
    assert lexical_query_items("é 漢字 é") == ("é", "漢字")
    with pytest.raises(ContextLimitExceeded, match="lexical_items"):
        lexical_query_items(" ".join(f"term{index}" for index in range(33)))
    with pytest.raises(ContextLimitExceeded, match="lexical_item"):
        lexical_query_items("x" * 300)


def test_text_discovery_returns_verified_rescored_candidates(tmp_path: Path) -> None:
    """Discover FTS hits, reverify full bodies and rescore deterministically."""
    ingestion, store, catalog = _text_services(tmp_path)
    source_path = _write(
        tmp_path / "doc.md",
        "# Title\n\nThe alpha token lives here. Alpha again.\n\nSeparately beta appears.\n",
    )
    result = ingestion.ingest(source_path)
    snapshot = _snapshot_for(catalog, result.scope.document_id)
    source = TextLexicalCandidateSource(store, catalog)

    candidates = source.discover("alpha beta", snapshot, LIMITS, _never_cancel)

    assert len(candidates) >= 2
    alpha = next(item for item in candidates if item.term_coverage == 1 and item.occurrences == 2)
    beta = next(item for item in candidates if item.term_coverage == 1 and item.occurrences == 1)
    assert all(item.freshness is CandidateFreshness.CURRENT for item in candidates)
    assert alpha.evidence_id == str(alpha.provenance.block_id)
    assert alpha.provenance.record_type == "block"
    assert alpha.scope == snapshot.scopes[0]
    assert alpha.body_media_type == "application/json"
    assert alpha.trust.role is ContentRole.DATA
    assert alpha.trust.instruction_execution_allowed is False
    assert beta.evidence_id != alpha.evidence_id
    assert all(item.reason_code == "fts_lexical_match" for item in candidates)


def test_text_discovery_fails_closed_on_incomplete_index(tmp_path: Path) -> None:
    """Never trust indexed bodies or metadata when coverage is incomplete."""
    ingestion, store, catalog = _text_services(tmp_path)
    source_path = _write(tmp_path / "doc.md", "alpha evidence\n")
    result = ingestion.ingest(source_path)
    snapshot = _snapshot_for(catalog, result.scope.document_id)
    connection = sqlite3.connect(tmp_path / "store" / "catalog.sqlite3")
    connection.execute("DELETE FROM block_search_index")
    connection.execute(
        "UPDATE representation_blocks SET trust_zone=NULL, page=NULL, slide=NULL, "
        "text_hash=NULL, indexed_at=NULL"
    )
    connection.commit()
    connection.close()
    source = TextLexicalCandidateSource(store, catalog)

    with pytest.raises(ContextIntegrityFailure, match="accelerator"):
        source.discover("alpha", snapshot, LIMITS, _never_cancel)


def test_text_discovery_reverifies_body_against_cas(tmp_path: Path) -> None:
    """Reject indexed candidates whose authoritative block object is corrupt."""
    ingestion, store, catalog = _text_services(tmp_path)
    source_path = _write(tmp_path / "doc.md", "alpha evidence\n")
    result = ingestion.ingest(source_path)
    snapshot = _snapshot_for(catalog, result.scope.document_id)
    aggregate = catalog.load_representation(result.scope)
    assert aggregate is not None
    target = aggregate.blocks[0].object.object_id
    source = TextLexicalCandidateSource(_TamperingStore(store, target), catalog)

    with pytest.raises(ContextIntegrityFailure):
        source.discover("alpha", snapshot, LIMITS, _never_cancel)


def test_superseded_versions_stay_invisible_not_silent_drift(tmp_path: Path) -> None:
    """Skip index rows from superseded versions; replay pins exact recorded scopes."""
    ingestion, store, catalog = _text_services(tmp_path)
    source_path = _write(tmp_path / "doc.md", "alpha version one\n")
    result_v1 = ingestion.ingest(source_path)
    _write(source_path, "alpha version two\n")
    result_v2 = ingestion.ingest(source_path)
    assert result_v2.scope.version_id != result_v1.scope.version_id
    snapshot = _snapshot_for(catalog, result_v2.scope.document_id)
    source = TextLexicalCandidateSource(store, catalog)

    candidates = source.discover("alpha", snapshot, LIMITS, _never_cancel)

    # Superseded rows stay invisible because receipt decision scopes must
    # remain inside the corpus snapshot; a pinned replay snapshot still
    # discovers the superseded version exactly.
    assert len(candidates) == 1
    assert candidates[0].freshness is CandidateFreshness.CURRENT
    assert candidates[0].scope.version_id == result_v2.scope.version_id
    version_v1 = catalog.get_version(result_v1.scope.document_id, result_v1.scope.version_id)
    assert version_v1 is not None
    replay_snapshot = CorpusSnapshot(
        scopes=(
            VersionScope(
                document_id=result_v1.scope.document_id,
                version_id=result_v1.scope.version_id,
                representation_id=result_v1.scope.representation_id,
            ),
        ),
        created_at=version_v1.committed_at,
    )
    replay_candidates = source.discover("alpha", replay_snapshot, LIMITS, _never_cancel)
    assert len(replay_candidates) == 1
    assert replay_candidates[0].scope.version_id == result_v1.scope.version_id


def test_discovery_cancellation_and_empty_task_are_bounded(tmp_path: Path) -> None:
    """Stop at bounded checkpoints and treat blank tasks as honest no-match input."""
    ingestion, store, catalog = _text_services(tmp_path)
    source_path = _write(tmp_path / "doc.md", "alpha evidence\n")
    result = ingestion.ingest(source_path)
    snapshot = _snapshot_for(catalog, result.scope.document_id)
    source = TextLexicalCandidateSource(store, catalog)

    with pytest.raises(ContextCompilationCancelled):
        source.discover("alpha", snapshot, LIMITS, lambda: True)
    assert source.discover("   ", snapshot, LIMITS, _never_cancel) == ()


def _rich_snapshot(catalog: SQLiteCatalog, document_id: UUID) -> CorpusSnapshot:
    return _snapshot_for(catalog, document_id)


def test_rich_scan_returns_verified_projection_candidates(tmp_path: Path) -> None:
    """Scan accepted F007 projections with exact body verification and true identities."""
    source_path = tmp_path / "source.docx"
    source_path.write_bytes(b"source-v1")
    parser = _Parser()
    parser.text = "alpha evidence alpha"
    ingestion, store, catalog = _service(tmp_path, parser, clock=_Clock())
    result = ingestion.ingest(source_path)
    snapshot = _rich_snapshot(catalog, result.scope.document_id)
    source = RichLexicalCandidateSource(
        store,
        catalog,
        representation_verifier=ingestion.verify_ready_representation,
    )

    candidates = source.discover("alpha", snapshot, LIMITS, _never_cancel)

    assert len(candidates) == 1
    candidate = candidates[0]
    provenance = candidate.provenance
    assert provenance.record_type == "evidence_projection"
    assert provenance.version_id == provenance.source_version_id == result.scope.version_id
    assert candidate.evidence_id == provenance.evidence_projection_id
    assert candidate.representation is EvidenceRepresentation.EXACT
    assert candidate.term_coverage == 1
    assert candidate.occurrences == 2
    assert candidate.freshness is CandidateFreshness.CURRENT
    assert candidate.trust.role is ContentRole.DATA
    assert candidate.reason_code == "rich_lexical_scan"


def test_rich_scan_skips_text_scopes_and_verifies_bodies(tmp_path: Path) -> None:
    """Skip non-rich snapshot scopes and fail closed on retrieval tampering."""
    text_ingestion, text_store, text_catalog = _text_services(tmp_path / "text")
    (tmp_path / "text").mkdir(exist_ok=True)
    text_path = _write(tmp_path / "text" / "doc.md", "alpha text\n")
    text_result = text_ingestion.ingest(text_path)
    snapshot = _snapshot_for(text_catalog, text_result.scope.document_id)
    source = RichLexicalCandidateSource(
        text_store,
        text_catalog,
        representation_verifier=lambda _artifacts: None,
    )
    assert source.discover("alpha", snapshot, LIMITS, _never_cancel) == ()

    source_path = tmp_path / "source.docx"
    source_path.write_bytes(b"source-v1")
    parser = _Parser()
    parser.text = "alpha evidence"
    ingestion, store, catalog = _service(tmp_path / "rich", parser, clock=_Clock())
    (tmp_path / "rich").mkdir(exist_ok=True)
    result = ingestion.ingest(source_path)
    artifacts = catalog.load_rich_representation(result.scope)
    assert artifacts is not None
    target = artifacts.bundle.records[0].retrieval_object.object_id
    rich_snapshot = _snapshot_for(catalog, result.scope.document_id)
    tampered = RichLexicalCandidateSource(
        _TamperingStore(store, target),
        catalog,
        representation_verifier=lambda _artifacts: None,
    )
    with pytest.raises(ContextIntegrityFailure):
        tampered.discover("alpha", rich_snapshot, LIMITS, _never_cancel)


def test_rich_scan_enforces_body_and_discovery_limits(tmp_path: Path) -> None:
    """Bound rich retrieval bodies before allocation."""
    source_path = tmp_path / "source.docx"
    source_path.write_bytes(b"source-v1")
    parser = _Parser()
    parser.text = "alpha " * 300
    ingestion, store, catalog = _service(tmp_path, parser, clock=_Clock())
    result = ingestion.ingest(source_path)
    snapshot = _snapshot_for(catalog, result.scope.document_id)
    source = RichLexicalCandidateSource(
        store,
        catalog,
        representation_verifier=ingestion.verify_ready_representation,
    )

    with pytest.raises(ContextLimitExceeded, match="body"):
        source.discover(
            "alpha",
            snapshot,
            ContextCompileLimits(max_body_bytes=1024),
            _never_cancel,
        )


def _synthetic_candidate(
    *,
    document_id: UUID,
    block_id: UUID,
    coverage: int = 1,
    occurrences: int = 1,
    source_order: int = 0,
    representation: EvidenceRepresentation = EvidenceRepresentation.EXACT,
    freshness: CandidateFreshness = CandidateFreshness.CURRENT,
    zone: TrustZone = TrustZone.EXTERNAL_UNTRUSTED,
    sensitivity: Sensitivity = Sensitivity.INTERNAL,
) -> ContextCandidate:
    scope = VersionScope(
        document_id=document_id,
        version_id="sha256:" + "1" * 64,
        representation_id="sha256:" + "2" * 64,
    )
    return ContextCandidate(
        evidence_id=str(block_id),
        scope=scope,
        provenance={
            "record_type": "block",
            "document_id": document_id,
            "version_id": scope.version_id,
            "representation_id": scope.representation_id,
            "block_id": block_id,
            "source": {"extraction_method": "synthetic"},
        },
        representation=representation,
        source_order=source_order,
        body_object={"object_id": "sha256:" + "8" * 64, "byte_length": 128},
        body_media_type="application/json",
        trust=DataTrustClassification(
            zone=zone,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=sensitivity,
        ),
        freshness=freshness,
        term_coverage=coverage,
        occurrences=occurrences,
        reason_code="fts_lexical_match",
        high_value=False,
    )


def test_mixed_classification_partitions_stale_trust_sensitivity_and_duplicates() -> None:
    """Classify every discovered subject exactly once before ordering."""
    document_id = UUID("01890f62-24e8-7c00-8000-000000000001")
    block_a = UUID("12345678-1234-4234-9234-123456789abc")
    block_b = UUID("12345678-1234-4234-9234-123456789abd")
    policy = ContextSelectionPolicy(mode=ContextMode.EXACT)
    candidates = (
        _synthetic_candidate(document_id=document_id, block_id=block_a),
        _synthetic_candidate(document_id=document_id, block_id=block_a),
        _synthetic_candidate(
            document_id=document_id,
            block_id=block_b,
            zone=TrustZone.LOCAL_TRUSTED,
        ),
        _synthetic_candidate(
            document_id=document_id,
            block_id=UUID("12345678-1234-4234-9234-123456789abe"),
            sensitivity=Sensitivity.RESTRICTED,
        ),
        _synthetic_candidate(
            document_id=document_id,
            block_id=UUID("12345678-1234-4234-9234-123456789abf"),
            freshness=CandidateFreshness.STALE,
        ),
    )

    classified = classify_candidates(candidates, policy)

    assert [item.evidence_id for item in classified.ordered] == [str(block_a)]
    assert classified.ordered[0].high_value is True
    assert [reason for _, reason in classified.rejected] == [
        "duplicate_candidate",
        "trust_zone_not_allowed",
        "sensitivity_exceeded",
    ]
    assert len(classified.stale) == 1


def test_total_order_is_complete_and_deterministic() -> None:
    """Order by value, coverage, occurrences, scope, source order, representation, identity."""
    document_id = UUID("01890f62-24e8-7c00-8000-000000000001")
    base = dict(document_id=document_id)
    low_value = _synthetic_candidate(
        **base,
        block_id=UUID("12345678-1234-4234-9234-123456789ab0"),
        coverage=3,
        occurrences=9,
        representation=EvidenceRepresentation.STRUCTURED,
    )
    high_value = _synthetic_candidate(
        **base,
        block_id=UUID("12345678-1234-4234-9234-123456789ab1"),
        coverage=1,
        occurrences=1,
    )
    more_coverage = _synthetic_candidate(
        **base,
        block_id=UUID("12345678-1234-4234-9234-123456789ab2"),
        coverage=2,
        occurrences=2,
    )
    earlier_order = _synthetic_candidate(
        **base,
        block_id=UUID("12345678-1234-4234-9234-123456789ab3"),
        coverage=2,
        occurrences=2,
        source_order=0,
    )
    later_order = _synthetic_candidate(
        **base,
        block_id=UUID("12345678-1234-4234-9234-123456789ab4"),
        coverage=2,
        occurrences=2,
        source_order=1,
    )
    policy = ContextSelectionPolicy(mode=ContextMode.EXACT)
    classified = classify_candidates(
        (later_order, low_value, more_coverage, high_value, earlier_order),
        policy,
    )
    keys = [candidate_total_order_key(item) for item in classified.ordered]
    assert keys == sorted(keys)
    assert classified.ordered[0].evidence_id == str(more_coverage.evidence_id)
    assert [item.source_order for item in classified.ordered[1:3]] == [0, 1]
    assert classified.ordered[-2].evidence_id == str(high_value.evidence_id)
    assert classified.ordered[-1].evidence_id == str(low_value.evidence_id)


def test_required_representations_follow_policy_then_mode() -> None:
    """Derive honest evidence requirements without inventing unavailable detail."""
    explicit = ContextSelectionPolicy(
        mode=ContextMode.NUMERIC,
        required_evidence=(EvidenceRepresentation.STRUCTURED,),
    )
    assert required_representations(explicit) == {EvidenceRepresentation.STRUCTURED}
    assert required_representations(ContextSelectionPolicy(mode=ContextMode.NUMERIC)) == {
        EvidenceRepresentation.EXACT,
        EvidenceRepresentation.STRUCTURED,
    }
    assert required_representations(ContextSelectionPolicy(mode=ContextMode.VISUAL)) == {
        EvidenceRepresentation.VISUAL_HANDLE,
    }
    assert required_representations(ContextSelectionPolicy(mode=ContextMode.VERIFICATION)) == {
        EvidenceRepresentation.EXACT,
    }
