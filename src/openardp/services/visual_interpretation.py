"""Explicit optional visual interpretation published through the F010 DAG."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Protocol

from openardp.domain.common import (
    ComponentDescriptor,
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    Sensitivity,
    TrustZone,
)
from openardp.domain.derivation import DerivationRecord, DerivationState
from openardp.domain.derivation_lifecycle import (
    DerivationDependency,
    DerivationDependencyKind,
    DerivationPublicationResult,
    DerivationSlotKey,
)
from openardp.domain.identity import (
    canonical_json_bytes,
    canonical_sha256,
    derivation_artifact_id,
    derivation_slot_id,
)
from openardp.domain.visual import (
    VisualInterpretationRequest,
    VisualInterpretationResult,
)
from openardp.ports.catalog import ReconciliationDerivationCatalog, VisualCatalog
from openardp.ports.context import CancellationCheck
from openardp.ports.object_store import ObjectStore, ObjectStoreError
from openardp.ports.visual import (
    VisualIntegrityError,
    VisualInterpretationUnavailable,
    VisualInterpreter,
    VisualTargetUnavailable,
)
from openardp.services.derivations import DerivationService
from openardp.services.visual_evidence import VisualEvidenceService


def _never_cancel() -> bool:
    return False


class _VisualDerivationCatalog(VisualCatalog, ReconciliationDerivationCatalog, Protocol):
    """Structural intersection required by the interpretation orchestration."""


class VisualInterpretationService:
    """Invoke one explicit provider and retain its output as untrusted derivation data."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: _VisualDerivationCatalog,
        visual_service: VisualEvidenceService,
        interpreter: VisualInterpreter | None = None,
    ) -> None:
        """Bind existing visual/F010 services; register no provider by default."""
        self._object_store = object_store
        self._catalog = catalog
        self._visual_service = visual_service
        self._interpreter = interpreter
        self._derivations = DerivationService(object_store, catalog)

    def interpret(
        self,
        request: VisualInterpretationRequest,
        *,
        completed_at: datetime,
        cancellation_check: CancellationCheck = _never_cancel,
    ) -> DerivationPublicationResult:
        """Verify parent/crop, invoke explicitly, and publish READY or FAILED evidence."""
        interpreter = self._interpreter
        if interpreter is None:
            raise VisualInterpretationUnavailable("visual interpretation provider unavailable")
        request = VisualInterpretationRequest.model_validate(request)
        if interpreter.provider != request.provider:
            raise VisualInterpretationUnavailable("visual interpretation recipe mismatch")
        descriptor = self._visual_service.inspect(request.visual_evidence_id)
        if (
            request.descriptor_object_id != self._descriptor_object_id(request.visual_evidence_id)
            or request.crop_object_id != descriptor.crop_object.object_id
        ):
            raise VisualIntegrityError("visual interpretation request identity drifted")
        head = self._catalog.get_document_head(descriptor.document_id)
        if head is None or head.scope != descriptor.page_raster.scope:
            raise VisualTargetUnavailable("visual interpretation parent is not current")
        crop = self._read_crop(descriptor.crop_object.object_id, descriptor.crop_object.byte_length)
        if cancellation_check():
            raise VisualInterpretationUnavailable("visual interpretation cancelled")
        output: VisualInterpretationResult | None = None
        failure_code: str | None = None
        try:
            output = VisualInterpretationResult.model_validate(interpreter.interpret(request, crop))
            if output.operation is not request.operation:
                raise ValueError("operation mismatch")
            if len(output.text) > request.max_output_characters:
                raise ValueError("output length exceeded")
            if len(output.warning_codes) > request.max_warning_codes:
                raise ValueError("warning count exceeded")
        except Exception:
            failure_code = "interpretation_failed"
        config_hash = canonical_sha256(
            {
                "descriptor_object_id": request.descriptor_object_id,
                "crop_object_id": request.crop_object_id,
                "operation": request.operation.value,
                "provider": request.provider.model_dump(mode="json"),
                "max_output_characters": request.max_output_characters,
                "max_warning_codes": request.max_warning_codes,
            }
        )
        generator = ComponentDescriptor(
            name=request.provider.name,
            version=request.provider.version,
            profile=request.provider.profile,
        )
        input_hashes = (request.crop_object_id,)
        artifact_id = derivation_artifact_id(
            input_hashes=input_hashes,
            generator_name=generator.name,
            generator_version=generator.version,
            generator_profile=generator.profile,
            model_id=f"{request.provider.name}:{request.provider.profile}",
            config_hash=config_hash,
            prompt_hash=request.prompt_hash,
        )
        output_payload = (
            canonical_json_bytes(output.model_dump(mode="json"))
            if output is not None and failure_code is None
            else None
        )
        output_hash = (
            "sha256:" + hashlib.sha256(output_payload).hexdigest()
            if output_payload is not None
            else None
        )
        record = DerivationRecord(
            schema_version="0.1.0",
            artifact_id=artifact_id,
            state=(DerivationState.READY if output_payload is not None else DerivationState.FAILED),
            generator=generator,
            model_id=f"{request.provider.name}:{request.provider.profile}",
            input_hashes=input_hashes,
            config_hash=config_hash,
            prompt_hash=request.prompt_hash,
            created_at=completed_at,
            completed_at=completed_at,
            output_hash=output_hash,
            quality_signals=(
                {
                    "confidence_ppm": output.confidence_ppm,
                    "operation": output.operation.value,
                    "warning_codes": list(output.warning_codes),
                }
                if output is not None and failure_code is None
                else {"operation": request.operation.value}
            ),
            trust=DataTrustClassification(
                zone=TrustZone.MODEL_DERIVED,
                role=ContentRole.DATA,
                instruction_execution_allowed=False,
                integrity=(
                    IntegrityState.VERIFIED_SHA256
                    if output_payload is not None
                    else IntegrityState.UNVERIFIED
                ),
                sensitivity=Sensitivity.UNKNOWN,
            ),
        )
        dependency = DerivationDependency(
            ordinal=0,
            kind=DerivationDependencyKind.OBJECT,
            input_digest=request.crop_object_id,
        )
        slot = DerivationSlotKey(
            slot_id=derivation_slot_id(
                namespace="visual-interpretation",
                subject_digest=request.visual_evidence_id,
                purpose=request.operation.value,
            ),
            namespace="visual-interpretation",
            subject_digest=request.visual_evidence_id,
            purpose=request.operation.value,
        )
        return self._derivations.publish(
            record,
            (dependency,),
            slot,
            output_chunks=((output_payload,) if output_payload is not None else None),
            failure_code=failure_code,
            cancellation_check=cancellation_check,
        )

    def _descriptor_object_id(self, visual_evidence_id: str) -> str:
        commit = self._catalog.load_visual_evidence(visual_evidence_id)
        if commit is None:
            raise VisualTargetUnavailable("visual interpretation parent is unavailable")
        return commit.descriptor_object.object_id

    def _read_crop(self, object_id: str, byte_length: int) -> bytes:
        try:
            self._object_store.verify(object_id, expected_length=byte_length)
            payload = b"".join(self._object_store.iter_chunks(object_id))
        except ObjectStoreError as error:
            raise VisualIntegrityError("visual interpretation crop is invalid") from error
        if len(payload) != byte_length:
            raise VisualIntegrityError("visual interpretation crop length changed")
        return payload


__all__ = ["VisualInterpretationService"]
