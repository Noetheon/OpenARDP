"""Verified explicit materialization/cache/inspection service tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest

from openardp.adapters.isolated_visual import IsolatedVisualRenderer
from openardp.adapters.visual_pdfium import canonical_visual_recipe
from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.visual import VisualRenderLimits
from openardp.ports.object_store import ObjectPublicationError
from openardp.ports.visual import VisualCancelled, VisualIntegrityError
from openardp.services.visual_evidence import VisualEvidenceService
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_service_support import (
    CountingVisualRenderer,
    prepared_pdf_visual_service,
    prepared_visual_service,
)


def test_first_render_exact_hit_and_same_page_new_crop_have_truthful_counts(
    tmp_path: Path,
) -> None:
    """Render a page once, reuse exact descriptor, then crop a second target only."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    renderer = CountingVisualRenderer()
    service = VisualEvidenceService(store, catalog, renderer, LocalOnlyVisualPolicy())
    first_projection, second_projection = rich.bundle.projections
    first = service.materialize(
        rich.bundle.scope,
        first_projection.evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    exact = service.materialize(
        rich.bundle.scope,
        first_projection.evidence_projection_id,
        created_at=NOW + timedelta(seconds=99),
    )
    second = service.materialize(
        rich.bundle.scope,
        second_projection.evidence_projection_id,
        created_at=NOW + timedelta(seconds=3),
    )
    assert exact == first
    assert second.page_raster == first.page_raster
    assert second.visual_evidence_id != first.visual_evidence_id
    assert second.transform != first.transform
    assert (renderer.render_count, renderer.crop_count) == (1, 2)
    assert service.inspect(first.visual_evidence_id) == first
    assert first.usage_policy.export_allowed is False


def test_twenty_concurrent_identical_requests_converge_to_one_descriptor(tmp_path: Path) -> None:
    """Use independent SQLite transactions and CAS publication to converge safely."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    renderer = CountingVisualRenderer()
    service = VisualEvidenceService(store, catalog, renderer, LocalOnlyVisualPolicy())
    projection_id = rich.bundle.projections[0].evidence_projection_id

    def materialize(_: int) -> str:
        return service.materialize(
            rich.bundle.scope,
            projection_id,
            created_at=NOW + timedelta(seconds=2),
        ).visual_evidence_id

    with ThreadPoolExecutor(max_workers=10) as executor:
        identities = tuple(executor.map(materialize, range(20)))
    assert len(set(identities)) == 1
    assert len(catalog.list_visual_evidence(rich.bundle.scope)) == 1


def test_real_pdf_materializes_end_to_end_through_spawned_renderer(tmp_path: Path) -> None:
    """Bind accepted PDF evidence to deterministic page and crop objects end to end."""
    catalog, store, rich = prepared_pdf_visual_service(tmp_path)
    service = VisualEvidenceService(
        store,
        catalog,
        IsolatedVisualRenderer(),
        LocalOnlyVisualPolicy(),
    )
    descriptor = service.materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    assert descriptor.page_raster.pixel_width == 1_224
    assert descriptor.page_raster.pixel_height == 1_584
    assert descriptor.crop_width == 246
    assert descriptor.crop_height == 318
    assert service.inspect(descriptor.visual_evidence_id) == descriptor


def test_recipe_change_creates_a_distinct_page_and_visual_identity(tmp_path: Path) -> None:
    """Bind every admission/output-affecting recipe field into both cache identities."""
    catalog, store, rich = prepared_visual_service(tmp_path)
    first_renderer = CountingVisualRenderer()
    first = VisualEvidenceService(
        store, catalog, first_renderer, LocalOnlyVisualPolicy()
    ).materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    changed_renderer = CountingVisualRenderer(
        canonical_visual_recipe(VisualRenderLimits(timeout_seconds=121.0))
    )
    changed = VisualEvidenceService(
        store, catalog, changed_renderer, LocalOnlyVisualPolicy()
    ).materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=3),
    )
    assert changed.page_raster.raster_id != first.page_raster.raster_id
    assert changed.visual_evidence_id != first.visual_evidence_id
    assert (first_renderer.render_count, changed_renderer.render_count) == (1, 1)


@pytest.mark.parametrize("failed_put", range(1, 5))
def test_each_visual_cas_publication_failure_is_unreachable_and_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_put: int,
) -> None:
    """Map every raster/crop/record CAS write failure before catalog visibility."""
    catalog, store, rich = prepared_visual_service(tmp_path / str(failed_put))
    service = VisualEvidenceService(
        store, catalog, CountingVisualRenderer(), LocalOnlyVisualPolicy()
    )
    original = store.put_chunks
    calls = 0

    def fail_once(chunks):
        nonlocal calls
        calls += 1
        if calls == failed_put:
            raise ObjectPublicationError("injected publication fault")
        return original(chunks)

    monkeypatch.setattr(store, "put_chunks", fail_once)
    with pytest.raises(VisualIntegrityError, match="publication"):
        service.materialize(
            rich.bundle.scope,
            rich.bundle.projections[0].evidence_projection_id,
            created_at=NOW + timedelta(seconds=2),
        )
    assert catalog.list_visual_evidence(rich.bundle.scope) == ()

    monkeypatch.setattr(store, "put_chunks", original)
    recovered = service.materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    assert service.inspect(recovered.visual_evidence_id) == recovered


@pytest.mark.parametrize(
    "object_role",
    ("raster_record", "raster", "descriptor", "crop"),
)
def test_inspection_rejects_every_visual_object_tamper(
    tmp_path: Path,
    object_role: str,
) -> None:
    """Reverify both canonical records and binary artifacts on every inspection."""
    catalog, store, rich = prepared_visual_service(tmp_path / object_role)
    service = VisualEvidenceService(
        store, catalog, CountingVisualRenderer(), LocalOnlyVisualPolicy()
    )
    descriptor = service.materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    commit = catalog.load_visual_evidence(descriptor.visual_evidence_id)
    assert commit is not None
    objects = {
        "raster_record": commit.raster_record_object,
        "raster": commit.page_raster.raster_object,
        "descriptor": commit.descriptor_object,
        "crop": commit.crop_object,
    }
    digest = objects[object_role].object_id.removeprefix("sha256:")
    path = store.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest[4:]
    path.write_bytes(b"tampered visual object")
    with pytest.raises(VisualIntegrityError):
        service.inspect(descriptor.visual_evidence_id)


@pytest.mark.parametrize("cancel_on_call", range(1, 11))
def test_cancellation_at_each_materialization_boundary_leaves_no_reachable_record(
    tmp_path: Path,
    cancel_on_call: int,
) -> None:
    """Fail closed across source, render, CAS, crop and pre-commit boundaries."""
    catalog, store, rich = prepared_visual_service(tmp_path / str(cancel_on_call))
    service = VisualEvidenceService(
        store,
        catalog,
        CountingVisualRenderer(),
        LocalOnlyVisualPolicy(),
    )
    calls = 0

    def cancellation_check() -> bool:
        nonlocal calls
        calls += 1
        return calls == cancel_on_call

    with pytest.raises(VisualCancelled):
        service.materialize(
            rich.bundle.scope,
            rich.bundle.projections[0].evidence_projection_id,
            created_at=NOW + timedelta(seconds=2),
            cancellation_check=cancellation_check,
        )
    assert catalog.list_visual_evidence(rich.bundle.scope) == ()
