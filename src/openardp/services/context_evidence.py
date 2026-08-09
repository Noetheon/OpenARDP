"""Small verified-evidence helpers for deterministic context compilation."""

from __future__ import annotations

from collections.abc import Sequence

from openardp.domain.context import EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    ContextBlockProvenance,
    ContextCandidate,
    ContextEvidenceItem,
    ContextMissingEvidence,
    ContextSelectionPolicy,
    ReceiptNotice,
)
from openardp.domain.storage import StoredObject
from openardp.ports.context import ContextIntegrityFailure
from openardp.ports.object_store import ObjectStore, ObjectStoreError
from openardp.services.context_ranking import required_representations


def item_evidence_id(item: ContextEvidenceItem) -> str:
    """Return the stable evidence identity carried by one selected item."""
    provenance = item.provenance
    if isinstance(provenance, ContextBlockProvenance):
        return str(provenance.block_id)
    return provenance.evidence_projection_id


def candidate_object_cost(candidate: ContextCandidate) -> int:
    """Return the verified body or descriptor object length used for receipt costing."""
    value = candidate.body_object or candidate.cost_object
    if value is None:
        raise ContextIntegrityFailure("candidate_cost_object_missing")
    return value.byte_length


def missing_evidence(
    policy: ContextSelectionPolicy,
    selected: Sequence[tuple[object, ContextEvidenceItem, int]],
) -> tuple[list[ContextMissingEvidence], list[ReceiptNotice]]:
    """Report unsatisfied requirements and visual escalation honestly."""
    required = required_representations(policy)
    satisfied = {entry[1].representation for entry in selected}
    missing: list[ContextMissingEvidence] = []
    notices: list[ReceiptNotice] = []
    if not (required & satisfied):
        for representation in sorted(required, key=lambda item: item.value):
            missing.append(
                ContextMissingEvidence(
                    evidence_type=representation,
                    reason_code="required_evidence_unavailable",
                )
            )
    if EvidenceRepresentation.VISUAL_HANDLE in required and (
        EvidenceRepresentation.VISUAL_HANDLE not in satisfied
    ):
        if not any(item.evidence_type is EvidenceRepresentation.VISUAL_HANDLE for item in missing):
            missing.append(
                ContextMissingEvidence(
                    evidence_type=EvidenceRepresentation.VISUAL_HANDLE,
                    reason_code="visual_evidence_required",
                )
            )
        notices.append(ReceiptNotice(code="visual_evidence_required"))
    return missing, notices


def read_verified(object_store: ObjectStore, stored: StoredObject) -> bytes:
    """Read one object only after digest, length and shape verification."""
    try:
        verified = object_store.verify(stored.object_id, expected_length=stored.byte_length)
        payload = b"".join(object_store.iter_chunks(verified.object_id))
    except ObjectStoreError as error:
        raise ContextIntegrityFailure("selected_object_invalid") from error
    if len(payload) != verified.byte_length:
        raise ContextIntegrityFailure("selected_object_length_changed")
    return payload


def item_scope(item: ContextEvidenceItem) -> VersionScope:
    """Return the exact corpus scope of one persisted evidence item."""
    provenance = item.provenance
    return VersionScope(
        document_id=provenance.document_id,
        version_id=provenance.version_id,
        representation_id=provenance.representation_id,
    )


__all__ = [
    "candidate_object_cost",
    "item_evidence_id",
    "item_scope",
    "missing_evidence",
    "read_verified",
]
