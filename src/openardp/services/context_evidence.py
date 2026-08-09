"""Small verified-evidence helpers for deterministic context compilation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import JsonValue

from openardp.domain.context import EvidenceRepresentation, VersionScope
from openardp.domain.context_compilation import (
    ContextBlockProvenance,
    ContextBundleV020,
    ContextCandidate,
    ContextCompilationRecord,
    ContextCompilationResult,
    ContextEvidenceItem,
    ContextMissingEvidence,
    ContextSelectionPolicy,
    ReceiptDecision,
    ReceiptNotice,
    SelectionOutcome,
    SelectionReceipt,
)
from openardp.domain.identity import (
    CANONICALIZATION_ALGORITHM,
    IDENTITY_VERSION,
    SELECTION_RECEIPT_DOMAIN,
    canonical_json_bytes,
)
from openardp.domain.storage import StoredObject
from openardp.ports.context import ContextIntegrityFailure
from openardp.ports.object_store import ObjectStore, ObjectStoreError
from openardp.services.context_ranking import required_representations
from openardp.services.context_relevance import relevance_extensions


@dataclass(frozen=True, slots=True)
class PersistedCompilation:
    """Verified compile result together with its immutable catalog record."""

    result: ContextCompilationResult
    record: ContextCompilationRecord


def receipt_object_bytes(receipt: SelectionReceipt) -> bytes:
    """Serialize the canonical identity envelope whose SHA-256 is the receipt ID."""
    envelope: dict[str, JsonValue] = {
        "canonicalization": CANONICALIZATION_ALGORITHM,
        "domain": SELECTION_RECEIPT_DOMAIN,
        "identity_version": IDENTITY_VERSION,
        "payload": receipt.model_dump(mode="json", exclude={"receipt_id"}),
    }
    return canonical_json_bytes(envelope)


def bundle_object_bytes(bundle: ContextBundleV020) -> bytes:
    """Serialize the complete canonical ContextBundle 0.2.0 handoff bytes."""
    return canonical_json_bytes(bundle.model_dump(mode="json"))


def receipt_decision(
    candidate: ContextCandidate,
    outcome: SelectionOutcome,
    cost: int | None,
    *,
    reason_code: str | None = None,
    final_order: int | None = None,
) -> ReceiptDecision:
    """Project one classified candidate into its body-free receipt decision."""
    return ReceiptDecision(
        outcome=outcome,
        evidence_id=candidate.evidence_id,
        scope=candidate.scope,
        representation=candidate.representation,
        reason_code=reason_code if reason_code is not None else candidate.reason_code,
        high_value=candidate.high_value,
        term_coverage=candidate.term_coverage,
        occurrences=candidate.occurrences,
        source_order=candidate.source_order,
        estimated_cost=(cost if cost is not None else candidate_object_cost(candidate)),
        final_order=final_order,
        extensions=relevance_extensions(candidate),
    )


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
    "PersistedCompilation",
    "bundle_object_bytes",
    "candidate_object_cost",
    "item_evidence_id",
    "item_scope",
    "missing_evidence",
    "read_verified",
    "receipt_decision",
    "receipt_object_bytes",
]
