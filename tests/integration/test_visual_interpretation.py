"""Explicit OCR/caption orchestration through the existing F010 DAG."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.evidence import ProviderRecipe
from openardp.domain.visual import (
    VisualInterpretationOperation,
    VisualInterpretationRequest,
    VisualInterpretationResult,
)
from openardp.ports.visual import VisualInterpretationUnavailable
from openardp.services.visual_evidence import VisualEvidenceService
from openardp.services.visual_interpretation import VisualInterpretationService
from tests.integration.test_rich_catalog import NOW
from tests.integration.visual_service_support import (
    CountingVisualRenderer,
    prepared_visual_service,
)


class _Interpreter:
    def __init__(self, *, oversized: bool = False, config: str = "1") -> None:
        self._provider = ProviderRecipe(
            name="synthetic-ocr",
            version="1.0.0",
            profile="offline-test",
            profile_version="1.0.0",
            config_hash="sha256:" + config * 64,
        )
        self.oversized = oversized
        self.calls = 0

    @property
    def provider(self) -> ProviderRecipe:
        return self._provider

    def interpret(
        self,
        request: VisualInterpretationRequest,
        crop_png: bytes,
    ) -> VisualInterpretationResult:
        self.calls += 1
        assert crop_png.startswith(b"\x89PNG")
        return VisualInterpretationResult(
            operation=request.operation,
            text="x" * (100 if self.oversized else 5),
            confidence_ppm=750_000,
            warning_codes=("synthetic",),
        )


def _prepared(tmp_path: Path):
    catalog, store, rich = prepared_visual_service(tmp_path)
    visual = VisualEvidenceService(
        store,
        catalog,
        CountingVisualRenderer(),
        LocalOnlyVisualPolicy(),
    )
    descriptor = visual.materialize(
        rich.bundle.scope,
        rich.bundle.projections[0].evidence_projection_id,
        created_at=NOW + timedelta(seconds=2),
    )
    record = catalog.list_visual_evidence(rich.bundle.scope)[0]
    return catalog, store, visual, descriptor, record


def _request(descriptor, record, provider, *, limit: int = 32_768):
    return VisualInterpretationRequest(
        visual_evidence_id=descriptor.visual_evidence_id,
        descriptor_object_id=record.descriptor_object.object_id,
        crop_object_id=descriptor.crop_object.object_id,
        operation=VisualInterpretationOperation.OCR,
        provider=provider,
        prompt_hash="sha256:" + "9" * 64,
        max_output_characters=limit,
    )


def test_explicit_interpretation_publishes_ready_crop_dependent_untrusted_output(
    tmp_path: Path,
) -> None:
    """Publish one exact model-derived output with an OBJECT edge to the crop."""
    catalog, store, visual, descriptor, record = _prepared(tmp_path)
    provider = _Interpreter()
    service = VisualInterpretationService(store, catalog, visual, provider)
    result = service.interpret(
        _request(descriptor, record, provider.provider),
        completed_at=NOW + timedelta(seconds=3),
    )
    node = result.node
    assert provider.calls == 1
    assert node.state.value == "CURRENT"
    assert node.record.trust.zone.value == "model_derived"
    assert node.record.trust.instruction_execution_allowed is False
    assert node.dependencies[0].kind.value == "OBJECT"
    assert node.dependencies[0].input_digest == descriptor.crop_object.object_id
    assert node.output_object is not None
    assert store.verify(node.output_object.object_id) == node.output_object

    repeated = service.interpret(
        _request(descriptor, record, provider.provider),
        completed_at=NOW + timedelta(seconds=3),
    )
    assert repeated.node == node


def test_no_provider_and_oversized_provider_result_are_explicit(tmp_path: Path) -> None:
    """Register no default provider and retain a bounded FAILED generation fact."""
    catalog, store, visual, descriptor, record = _prepared(tmp_path)
    request_provider = _Interpreter()
    with pytest.raises(VisualInterpretationUnavailable):
        VisualInterpretationService(store, catalog, visual).interpret(
            _request(descriptor, record, request_provider.provider),
            completed_at=NOW + timedelta(seconds=3),
        )

    oversized = _Interpreter(oversized=True)
    result = VisualInterpretationService(store, catalog, visual, oversized).interpret(
        _request(descriptor, record, oversized.provider, limit=10),
        completed_at=NOW + timedelta(seconds=3),
    )
    assert result.node.state.value == "FAILED"
    assert result.node.failure_code == "interpretation_failed"
    assert result.node.output_object is None


def test_recipe_change_supersedes_prior_slot_and_cancellation_invokes_nothing(
    tmp_path: Path,
) -> None:
    """Invalidate by exact provider config and stop before provider invocation."""
    catalog, store, visual, descriptor, record = _prepared(tmp_path)
    first_provider = _Interpreter(config="1")
    first = VisualInterpretationService(store, catalog, visual, first_provider).interpret(
        _request(descriptor, record, first_provider.provider),
        completed_at=NOW + timedelta(seconds=3),
    )
    second_provider = _Interpreter(config="2")
    second = VisualInterpretationService(store, catalog, visual, second_provider).interpret(
        _request(descriptor, record, second_provider.provider),
        completed_at=NOW + timedelta(seconds=4),
    )
    assert first.node.artifact_id != second.node.artifact_id
    assert second.superseded_artifact_ids == (first.node.artifact_id,)
    assert catalog.get_derivation(first.node.artifact_id).state.value == "SUPERSEDED"  # type: ignore[union-attr]

    cancelled = _Interpreter(config="3")
    with pytest.raises(VisualInterpretationUnavailable, match="cancelled"):
        VisualInterpretationService(store, catalog, visual, cancelled).interpret(
            _request(descriptor, record, cancelled.provider),
            completed_at=NOW + timedelta(seconds=5),
            cancellation_check=lambda: True,
        )
    assert cancelled.calls == 0
