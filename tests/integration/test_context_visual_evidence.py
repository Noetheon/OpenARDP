"""Handle-only visual context compilation without implicit rendering."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from openardp.adapters.context_candidates import VisualContextCandidateSource
from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.common import Sensitivity
from openardp.domain.context import ContextMode, EvidenceRepresentation
from openardp.domain.context_compilation import ContextCompileRequest, ContextSelectionPolicy
from openardp.ports.context import ContextIntegrityFailure
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.visual_evidence import VisualEvidenceService
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_service_support import (
    CountingVisualRenderer,
    advance_visual_document_head,
    prepared_visual_service,
)


def _request(document_id, estimator) -> ContextCompileRequest:
    return ContextCompileRequest(
        task="inspect exact visual evidence",
        document_ids=(document_id,),
        budget_limit=1_000_000,
        estimator=estimator.identity,
        policy=ContextSelectionPolicy(
            mode=ContextMode.VISUAL,
            maximum_sensitivity=Sensitivity.UNKNOWN,
        ),
    )


def test_visual_context_preserves_missing_then_selects_verified_descriptor_handle(
    tmp_path: Path,
) -> None:
    """Compile honestly before/after explicit materialization without reading image bytes."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    estimator = Utf8ByteEstimator()
    source = VisualContextCandidateSource(store, catalog)
    compiler = ContextCompilerService(store, catalog, estimator, (source,))
    request = _request(rich.bundle.scope.document_id, estimator)

    before = compiler.compile(request)
    assert before.bundle.items == ()
    assert tuple(item.evidence_type for item in before.bundle.missing_evidence) == (
        EvidenceRepresentation.VISUAL_HANDLE,
    )
    assert before.receipt.notices[0].code == "visual_evidence_required"

    renderer = CountingVisualRenderer()
    visual = VisualEvidenceService(store, catalog, renderer, LocalOnlyVisualPolicy())
    descriptor = visual.materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    after = compiler.compile(request)
    assert len(after.bundle.items) == 1
    item = after.bundle.items[0]
    record = catalog.list_visual_evidence(rich.bundle.scope)[0]
    assert item.representation is EvidenceRepresentation.VISUAL_HANDLE
    assert item.content is None
    assert item.artifact_handle == record.descriptor_object.object_id
    assert item.artifact_id == record.descriptor_object.object_id
    assert item.provenance.evidence_projection_id == descriptor.evidence_projection_id  # type: ignore[union-attr]
    assert after.bundle.missing_evidence == ()
    assert renderer.render_count == 1


def test_visual_context_persisted_replay_is_byte_identical_and_provider_free(
    tmp_path: Path,
) -> None:
    """Replay the pinned descriptor handle without invoking renderer or interpreter."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    renderer = CountingVisualRenderer()
    VisualEvidenceService(store, catalog, renderer, LocalOnlyVisualPolicy()).materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    estimator = Utf8ByteEstimator()
    compiler = ContextCompilerService(
        store,
        catalog,
        estimator,
        (VisualContextCandidateSource(store, catalog),),
    )
    request = _request(rich.bundle.scope.document_id, estimator)
    persisted = compiler.compile_and_persist(request)
    replayed = compiler.replay(request.task, persisted.record.receipt_id)
    assert replayed == persisted.result
    assert renderer.render_count == 1
    assert renderer.crop_count == 1


def test_visual_context_rejects_descriptor_cas_drift_without_reading_crop_body(
    tmp_path: Path,
) -> None:
    """Fail closed when the selected descriptor handle no longer verifies exactly."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    VisualEvidenceService(
        store,
        catalog,
        CountingVisualRenderer(),
        LocalOnlyVisualPolicy(),
    ).materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    record = catalog.list_visual_evidence(rich.bundle.scope)[0]
    digest = record.descriptor_object.object_id.removeprefix("sha256:")
    path = store.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    path.write_bytes(b"corrupt descriptor")
    estimator = Utf8ByteEstimator()
    compiler = ContextCompilerService(
        store,
        catalog,
        estimator,
        (VisualContextCandidateSource(store, catalog),),
    )
    with pytest.raises(ContextIntegrityFailure, match="evidence_object_invalid"):
        compiler.compile(_request(rich.bundle.scope.document_id, estimator))


def test_new_head_excludes_old_visual_while_persisted_replay_stays_pinned(
    tmp_path: Path,
) -> None:
    """Never float a visual handle from its exact source/representation snapshot."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    VisualEvidenceService(
        store,
        catalog,
        CountingVisualRenderer(),
        LocalOnlyVisualPolicy(),
    ).materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    estimator = Utf8ByteEstimator()
    compiler = ContextCompilerService(
        store,
        catalog,
        estimator,
        (VisualContextCandidateSource(store, catalog),),
    )
    request = _request(rich.bundle.scope.document_id, estimator)
    persisted = compiler.compile_and_persist(request)
    assert len(persisted.result.bundle.items) == 1

    advance_visual_document_head(catalog, store, rich)
    fresh = compiler.compile(request)
    assert fresh.bundle.items == ()
    assert fresh.receipt.notices[0].code == "visual_evidence_required"
    assert compiler.replay(request.task, persisted.record.receipt_id) == persisted.result
