"""Pure state and identity tests for the internal F010 derivation lifecycle."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

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
    DerivationEventReason,
    DerivationLifecycleEvent,
    DerivationLifecycleState,
    DerivationNode,
    DerivationPublication,
    DerivationPublicationDisposition,
    DerivationPublicationResult,
    DerivationSlotKey,
    derivation_node_fingerprint,
)
from openardp.domain.identity import (
    canonical_json_bytes,
    derivation_artifact_id,
    derivation_slot_id,
)
from openardp.domain.storage import StoredObject

INPUT = "sha256:" + "1" * 64
CONFIG = "sha256:" + "2" * 64
OUTPUT_BYTES = b"synthetic derived output"
OUTPUT = StoredObject(
    object_id="sha256:" + hashlib.sha256(OUTPUT_BYTES).hexdigest(),
    byte_length=len(OUTPUT_BYTES),
)
CREATED = datetime(2026, 7, 31, 13, 0, tzinfo=UTC)
COMPLETED = CREATED + timedelta(seconds=1)
PUBLISHED = COMPLETED + timedelta(seconds=1)


def _slot(*, purpose: str = "block-summary") -> DerivationSlotKey:
    namespace = "openardp.summary"
    return DerivationSlotKey(
        slot_id=derivation_slot_id(
            namespace=namespace,
            subject_digest=INPUT,
            purpose=purpose,
        ),
        namespace=namespace,
        subject_digest=INPUT,
        purpose=purpose,
    )


def _record(state: DerivationState = DerivationState.READY) -> DerivationRecord:
    artifact_id = derivation_artifact_id(
        input_hashes=(INPUT,),
        generator_name="synthetic-summary",
        generator_version="1.0.0",
        generator_profile="default",
        model_id=None,
        config_hash=CONFIG,
        prompt_hash=None,
    )
    return DerivationRecord(
        schema_version="0.1.0",
        artifact_id=artifact_id,
        state=state,
        generator=ComponentDescriptor(
            name="synthetic-summary",
            version="1.0.0",
            profile="default",
        ),
        input_hashes=(INPUT,),
        config_hash=CONFIG,
        created_at=CREATED,
        completed_at=COMPLETED,
        output_hash=OUTPUT.object_id if state is not DerivationState.FAILED else None,
        trust=DataTrustClassification(
            zone=TrustZone.MODEL_DERIVED,
            role=ContentRole.DATA,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.UNKNOWN,
        ),
    )


def _record_object(record: DerivationRecord) -> StoredObject:
    payload = canonical_json_bytes(record.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def _dependency(
    *,
    kind: DerivationDependencyKind = DerivationDependencyKind.EVIDENCE_BINDING,
    producer: str | None = None,
) -> DerivationDependency:
    return DerivationDependency(
        ordinal=0,
        kind=kind,
        input_digest=INPUT,
        producer_artifact_id=producer,
    )


def _publication(state: DerivationState = DerivationState.READY) -> DerivationPublication:
    record = _record(state)
    return DerivationPublication(
        record=record,
        record_object=_record_object(record),
        output_object=OUTPUT if state is DerivationState.READY else None,
        dependencies=(_dependency(),),
        slot=_slot(),
        failure_code="provider_failed" if state is DerivationState.FAILED else None,
        published_at=PUBLISHED,
    )


def _node(
    state: DerivationLifecycleState = DerivationLifecycleState.CURRENT,
) -> DerivationNode:
    publication = _publication(
        DerivationState.FAILED
        if state is DerivationLifecycleState.FAILED
        else DerivationState.READY
    )
    skeleton = DerivationNode.model_construct(
        artifact_id=publication.record.artifact_id,
        slot=publication.slot,
        state=state,
        record=publication.record,
        record_object=publication.record_object,
        output_object=publication.output_object,
        dependencies=publication.dependencies,
        revision=1,
        created_at=PUBLISHED,
        updated_at=PUBLISHED,
        failure_code=publication.failure_code,
        row_fingerprint="sha256:" + "0" * 64,
    )
    return DerivationNode(
        artifact_id=skeleton.artifact_id,
        slot=skeleton.slot,
        state=skeleton.state,
        record=skeleton.record,
        record_object=skeleton.record_object,
        output_object=skeleton.output_object,
        dependencies=skeleton.dependencies,
        revision=skeleton.revision,
        created_at=skeleton.created_at,
        updated_at=skeleton.updated_at,
        failure_code=skeleton.failure_code,
        row_fingerprint=derivation_node_fingerprint(skeleton),
    )


@pytest.mark.parametrize(
    "state",
    (
        DerivationLifecycleState.CURRENT,
        DerivationLifecycleState.STALE,
        DerivationLifecycleState.FAILED,
        DerivationLifecycleState.SUPERSEDED,
    ),
)
def test_all_internal_lifecycle_states_have_valid_closed_shapes(
    state: DerivationLifecycleState,
) -> None:
    """Keep workspace eligibility separate from the public generation-state enum."""
    node = _node(state)
    assert node.state is state
    assert node.record.state is (
        DerivationState.FAILED
        if state is DerivationLifecycleState.FAILED
        else DerivationState.READY
    )


def test_publication_binds_exact_ordered_dependencies_and_canonical_objects() -> None:
    """Reject any record, output or dependency projection that differs from the recipe."""
    publication = _publication()
    assert publication.output_object == OUTPUT
    payload = json.loads(publication.model_dump_json())
    payload["dependencies"] = [
        {
            "ordinal": 0,
            "kind": "OBJECT",
            "input_digest": "sha256:" + "9" * 64,
            "producer_artifact_id": None,
        }
    ]
    with pytest.raises(ValidationError, match="ordered recipe inputs"):
        DerivationPublication.model_validate_json(json.dumps(payload), strict=True)


def test_failed_publication_has_no_output_and_requires_bounded_failure_code() -> None:
    """Keep terminal generation failure separate from a successful artifact."""
    failed = _publication(DerivationState.FAILED)
    assert failed.output_object is None
    payload = json.loads(failed.model_dump_json())
    payload["failure_code"] = None
    with pytest.raises(ValidationError, match="failure code"):
        DerivationPublication.model_validate_json(json.dumps(payload), strict=True)


def test_producer_identity_is_required_only_for_derivation_output_edges() -> None:
    """Make producer ancestry explicit instead of guessing from equal hashes."""
    with pytest.raises(ValidationError, match="required only"):
        _dependency(kind=DerivationDependencyKind.OBJECT, producer=CONFIG)
    with pytest.raises(ValidationError, match="required only"):
        _dependency(kind=DerivationDependencyKind.DERIVATION_OUTPUT)
    edge = _dependency(
        kind=DerivationDependencyKind.DERIVATION_OUTPUT,
        producer=CONFIG,
    )
    assert edge.producer_artifact_id == CONFIG


def test_slot_and_node_fingerprints_reject_drift() -> None:
    """Recompute persisted slot and complete row identities at the domain boundary."""
    slot = _slot()
    with pytest.raises(ValidationError, match="slot_id"):
        DerivationSlotKey(
            slot_id="sha256:" + "f" * 64,
            namespace=slot.namespace,
            subject_digest=slot.subject_digest,
            purpose=slot.purpose,
        )
    node = _node()
    payload = json.loads(node.model_dump_json())
    payload["row_fingerprint"] = "sha256:" + "f" * 64
    with pytest.raises(ValidationError, match="row_fingerprint"):
        DerivationNode.model_validate_json(json.dumps(payload), strict=True)


def test_lifecycle_events_require_real_transitions_and_scoped_reasons() -> None:
    """Keep no-op retries out of the append-only event history."""
    node = _node()
    initial = DerivationLifecycleEvent(
        artifact_id=node.artifact_id,
        sequence=1,
        to_state=DerivationLifecycleState.CURRENT,
        reason=DerivationEventReason.PUBLISHED,
        occurred_at=PUBLISHED,
    )
    assert initial.from_state is None
    with pytest.raises(ValidationError, match="requires run_id"):
        DerivationLifecycleEvent(
            artifact_id=node.artifact_id,
            sequence=2,
            from_state=DerivationLifecycleState.CURRENT,
            to_state=DerivationLifecycleState.STALE,
            reason=DerivationEventReason.DEPENDENCY_INACTIVE,
            occurred_at=PUBLISHED,
        )
    with pytest.raises(ValidationError, match="must change"):
        DerivationLifecycleEvent(
            artifact_id=node.artifact_id,
            sequence=2,
            from_state=DerivationLifecycleState.CURRENT,
            to_state=DerivationLifecycleState.CURRENT,
            reason=DerivationEventReason.REACTIVATED,
            run_id=INPUT,
            occurred_at=PUBLISHED,
        )


def test_converged_result_cannot_repeat_supersession() -> None:
    """Classify an idempotent retry without replaying state transitions."""
    with pytest.raises(ValidationError, match="cannot repeat"):
        DerivationPublicationResult(
            disposition=DerivationPublicationDisposition.CONVERGED,
            node=_node(),
            superseded_artifact_ids=(CONFIG,),
        )
