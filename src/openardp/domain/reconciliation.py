"""Pure deterministic block reconciliation and lineage contracts."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, JsonValue, StringConstraints, model_validator

from openardp.domain.block import BlockKind
from openardp.domain.common import (
    ComponentDescriptor,
    DomainModel,
    GenerationProvenance,
    Sha256Id,
    UtcDatetime,
)
from openardp.domain.identity import (
    block_lineage_id,
    canonical_json_bytes,
    canonical_sha256,
    evidence_binding_id,
    reconciliation_run_id,
    relation_identity,
)
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.relation import BlockReference, Relation, RelationKind
from openardp.domain.storage import StoredObject

RECONCILIATION_ALGORITHM_VERSION = "openardp-block-reconcile-v1"
MAX_RECONCILIATION_BLOCKS = 100_000
MAX_RECONCILIATION_DEPTH = 32
MAX_SIMILARITY_TEXT = 4_096
MAX_SIMILARITY_ORDER_DISTANCE = 8
MAX_SIMILARITY_COMPARISONS = 1_000_000
MAX_SEQUENCE_GAP = 256
MIN_SIMILARITY_PPM = 970_000
MIN_WINNER_MARGIN_PPM = 50_000

_SPACE = re.compile(r"\s+")
NativeStableId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=2048)]


def _config_payload() -> dict[str, JsonValue]:
    return {
        "algorithm_version": RECONCILIATION_ALGORITHM_VERSION,
        "max_blocks": MAX_RECONCILIATION_BLOCKS,
        "max_depth": MAX_RECONCILIATION_DEPTH,
        "max_similarity_text": MAX_SIMILARITY_TEXT,
        "max_similarity_order_distance": MAX_SIMILARITY_ORDER_DISTANCE,
        "max_similarity_comparisons": MAX_SIMILARITY_COMPARISONS,
        "max_sequence_gap": MAX_SEQUENCE_GAP,
        "min_similarity_ppm": MIN_SIMILARITY_PPM,
        "min_winner_margin_ppm": MIN_WINNER_MARGIN_PPM,
    }


RECONCILIATION_CONFIG_HASH = canonical_sha256(_config_payload())


class ReconciliationError(ValueError):
    """Base error for invalid or unsafe pure reconciliation input."""


class ReconciliationLimitExceeded(ReconciliationError):
    """Raised before a configured matching resource bound is exceeded."""


class MatchMethod(StrEnum):
    """Deterministic phase that established logical continuity."""

    NATIVE_ID = "native_id"
    EXACT_CONTENT = "exact_content"
    ASSET_OR_TABLE = "asset_or_table"
    SIMILARITY = "similarity"
    SEQUENCE = "sequence"


class ReconciliationBlock(DomainModel):
    """Verified block facts required by the pure bounded matcher."""

    reference: BlockReference
    parent_id: UUID | None = None
    kind: BlockKind
    order: int = Field(strict=True, ge=0)
    ordinal: int = Field(strict=True, ge=0, lt=MAX_RECONCILIATION_BLOCKS)
    canonical_hash: Sha256Id
    text: str | None = None
    structured_hash: Sha256Id | None = None
    asset_id: Sha256Id | None = None
    native_stable_id: NativeStableId | None = None
    lineage_id: Sha256Id | None = None
    lineage_introduced_by_run_id: Sha256Id | None = None

    @model_validator(mode="after")
    def _scope_and_payload_are_consistent(self) -> Self:
        if (self.lineage_id is None) != (self.lineage_introduced_by_run_id is None):
            raise ValueError("lineage identity and introducing run must be provided together")
        if self.parent_id == self.reference.block_id:
            raise ValueError("reconciliation block cannot parent itself")
        if self.text is not None and len(self.text) > MAX_SIMILARITY_TEXT * 16:
            raise ReconciliationLimitExceeded("reconciliation text exceeds hard input limit")
        if self.kind is BlockKind.TABLE and self.structured_hash is None:
            # Text-only markdown tables remain valid and fall through exact/text phases.
            return self
        return self


class BlockLineageMembership(DomainModel):
    """One exact block membership in a version-independent logical lineage."""

    lineage_id: Sha256Id
    block: BlockReference
    canonical_hash: Sha256Id
    binding_digest: Sha256Id
    introduced_by_run_id: Sha256Id

    @model_validator(mode="after")
    def _binding_matches(self) -> Self:
        expected = evidence_binding_id(
            lineage_id=self.lineage_id,
            canonical_hash=self.canonical_hash,
        )
        if self.binding_digest != expected:
            raise ValueError("binding_digest does not match lineage and content")
        return self


class ReconciliationMatch(DomainModel):
    """One accepted cross-version logical relation and its reuse classification."""

    previous: BlockReference
    current: BlockReference
    lineage_id: Sha256Id
    previous_canonical_hash: Sha256Id
    current_canonical_hash: Sha256Id
    method: MatchMethod
    confidence_ppm: int = Field(strict=True, ge=0, le=1_000_000)
    reusable: bool
    relation: Relation
    relation_object: StoredObject

    @model_validator(mode="after")
    def _relation_and_reuse_are_exact(self) -> Self:
        if self.previous.document_id != self.current.document_id:
            raise ValueError("reconciliation match cannot cross documents")
        if self.previous.version_id == self.current.version_id and (
            self.previous.representation_id == self.current.representation_id
        ):
            raise ValueError("reconciliation match requires distinct scopes")
        if self.reusable != (self.previous_canonical_hash == self.current_canonical_hash):
            raise ValueError("reuse requires exact canonical content equality")
        if (
            self.relation.kind is not RelationKind.SAME_LOGICAL_BLOCK_AS
            or self.relation.source != self.current
            or self.relation.target != self.previous
            or self.relation.algorithm_version != RECONCILIATION_ALGORITHM_VERSION
            or self.relation.confidence != self.confidence_ppm / 1_000_000
        ):
            raise ValueError("relation does not match reconciliation decision")
        payload = canonical_json_bytes(self.relation.model_dump(mode="json"))
        expected = StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )
        if self.relation_object != expected:
            raise ValueError("relation object does not match canonical relation")
        return self


class ReconciliationPlan(DomainModel):
    """Complete deterministic result for one ordered pair of representation scopes."""

    run_id: Sha256Id
    previous_scope: RepresentationScope
    current_scope: RepresentationScope
    algorithm_version: str
    config_hash: Sha256Id
    seed_memberships: tuple[BlockLineageMembership, ...]
    memberships: tuple[BlockLineageMembership, ...]
    matches: tuple[ReconciliationMatch, ...]
    inactive_binding_digests: tuple[Sha256Id, ...]
    matched_count: int = Field(strict=True, ge=0)
    reusable_count: int = Field(strict=True, ge=0)
    new_count: int = Field(strict=True, ge=0)
    ambiguous_count: int = Field(strict=True, ge=0)
    comparison_count: int = Field(strict=True, ge=0, le=MAX_SIMILARITY_COMPARISONS)
    result_fingerprint: Sha256Id
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _complete_plan_is_consistent(self) -> Self:
        expected_run = reconciliation_run_id(
            previous_scope=self.previous_scope.model_dump(mode="json"),
            current_scope=self.current_scope.model_dump(mode="json"),
            algorithm_version=self.algorithm_version,
            config_hash=self.config_hash,
        )
        if self.run_id != expected_run:
            raise ValueError("run_id does not match reconciliation scopes and config")
        if self.algorithm_version != RECONCILIATION_ALGORITHM_VERSION:
            raise ValueError("unsupported reconciliation algorithm version")
        if self.config_hash != RECONCILIATION_CONFIG_HASH:
            raise ValueError("unsupported reconciliation configuration")
        if self.matched_count != len(self.matches):
            raise ValueError("matched_count does not match decisions")
        if self.reusable_count != sum(item.reusable for item in self.matches):
            raise ValueError("reusable_count does not match decisions")
        if self.new_count != len(self.memberships) - len(self.matches):
            raise ValueError("new_count does not match current memberships")
        if self.inactive_binding_digests != tuple(sorted(set(self.inactive_binding_digests))):
            raise ValueError("inactive bindings must be sorted and unique")
        expected = reconciliation_result_fingerprint(self)
        if self.result_fingerprint != expected:
            raise ValueError("result_fingerprint does not match plan facts")
        return self


class ReconciliationDisposition(StrEnum):
    """Observable result of an idempotent reconciliation publication."""

    COMMITTED = "COMMITTED"
    CONVERGED = "CONVERGED"


class ReconciliationResult(DomainModel):
    """Complete plan plus its catalog publication classification."""

    disposition: ReconciliationDisposition
    plan: ReconciliationPlan
    stale_artifact_ids: tuple[Sha256Id, ...] = ()
    reactivated_artifact_ids: tuple[Sha256Id, ...] = ()

    @model_validator(mode="after")
    def _transition_ids_are_canonical(self) -> Self:
        for values in (self.stale_artifact_ids, self.reactivated_artifact_ids):
            if values != tuple(sorted(set(values))):
                raise ValueError("lifecycle artifact identifiers must be sorted and unique")
        if set(self.stale_artifact_ids).intersection(self.reactivated_artifact_ids):
            raise ValueError("one reconciliation cannot stale and reactivate the same artifact")
        return self


def reconciliation_result_fingerprint(plan: ReconciliationPlan) -> str:
    """Hash every immutable result fact while excluding time and the fingerprint."""
    payload = plan.model_dump(mode="json", exclude={"created_at", "result_fingerprint"})
    return canonical_sha256(payload)


def reconcile_blocks(
    previous: tuple[ReconciliationBlock, ...],
    current: tuple[ReconciliationBlock, ...],
    *,
    previous_scope: RepresentationScope,
    current_scope: RepresentationScope,
    current_ready_at: UtcDatetime,
    created_at: UtcDatetime,
) -> ReconciliationPlan:
    """Build one complete conservative plan without I/O or mutable process state."""
    _validate_aggregates(previous, current, previous_scope, current_scope)
    run_id = reconciliation_run_id(
        previous_scope=previous_scope.model_dump(mode="json"),
        current_scope=current_scope.model_dump(mode="json"),
        algorithm_version=RECONCILIATION_ALGORITHM_VERSION,
        config_hash=RECONCILIATION_CONFIG_HASH,
    )
    previous_lineages = {
        item.reference.block_id: item.lineage_id
        or block_lineage_id(origin=item.reference.model_dump(mode="json"))
        for item in previous
    }
    previous_memberships = tuple(
        _membership(item, previous_lineages[item.reference.block_id], run_id) for item in previous
    )

    assignments: dict[int, tuple[int, MatchMethod, int]] = {}
    used_previous: set[int] = set()
    current_to_previous_parent: dict[UUID, UUID] = {}
    comparison_count = 0
    candidate_seen: set[int] = set()

    def assign(current_index: int, previous_index: int, method: MatchMethod, ppm: int) -> None:
        assignments[current_index] = (previous_index, method, ppm)
        used_previous.add(previous_index)
        current_to_previous_parent[current[current_index].reference.block_id] = previous[
            previous_index
        ].reference.block_id

    _assign_unique_phase(
        previous,
        current,
        assignments,
        used_previous,
        current_to_previous_parent,
        candidate_seen,
        method=MatchMethod.NATIVE_ID,
        key=lambda item: (
            (item.native_stable_id, item.kind.value) if item.native_stable_id is not None else None
        ),
        confidence_ppm=1_000_000,
        require_parent=False,
        assign=assign,
    )
    _assign_unique_phase(
        previous,
        current,
        assignments,
        used_previous,
        current_to_previous_parent,
        candidate_seen,
        method=MatchMethod.EXACT_CONTENT,
        key=lambda item: (item.kind.value, item.canonical_hash),
        confidence_ppm=1_000_000,
        require_parent=True,
        assign=assign,
    )
    _assign_unique_phase(
        previous,
        current,
        assignments,
        used_previous,
        current_to_previous_parent,
        candidate_seen,
        method=MatchMethod.ASSET_OR_TABLE,
        key=_asset_or_table_key,
        confidence_ppm=1_000_000,
        require_parent=True,
        assign=assign,
    )

    similarity_candidates: dict[int, list[tuple[int, int]]] = defaultdict(list)
    reverse_candidates: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for current_index, current_item in enumerate(current):
        if current_index in assignments or current_item.text is None:
            continue
        normalized_current = _normalized_text(current_item.text)
        for previous_index, previous_item in enumerate(previous):
            if previous_index in used_previous or previous_item.text is None:
                continue
            if current_item.kind is not previous_item.kind or not _parent_compatible(
                previous_item,
                current_item,
                current_to_previous_parent,
            ):
                continue
            if abs(current_item.order - previous_item.order) > MAX_SIMILARITY_ORDER_DISTANCE:
                continue
            candidate_seen.add(current_index)
            comparison_count += 1
            if comparison_count > MAX_SIMILARITY_COMPARISONS:
                raise ReconciliationLimitExceeded("similarity comparison budget exceeded")
            ppm = _similarity_ppm(_normalized_text(previous_item.text), normalized_current)
            if ppm >= MIN_SIMILARITY_PPM:
                similarity_candidates[current_index].append((ppm, previous_index))
                reverse_candidates[previous_index].append((ppm, current_index))

    for current_index in sorted(similarity_candidates):
        ranked = sorted(similarity_candidates[current_index], key=lambda item: (-item[0], item[1]))
        score, previous_index = ranked[0]
        if current_index in assignments or previous_index in used_previous:
            continue
        if len(ranked) > 1 and score - ranked[1][0] < MIN_WINNER_MARGIN_PPM:
            continue
        reverse = sorted(reverse_candidates[previous_index], key=lambda item: (-item[0], item[1]))
        if reverse[0][1] != current_index:
            continue
        if len(reverse) > 1 and score - reverse[1][0] < MIN_WINNER_MARGIN_PPM:
            continue
        assign(current_index, previous_index, MatchMethod.SIMILARITY, score)

    _assign_sequence_gaps(
        previous,
        current,
        assignments,
        used_previous,
        current_to_previous_parent,
        candidate_seen,
        assign,
    )

    matches: list[ReconciliationMatch] = []
    memberships: list[BlockLineageMembership] = []
    for current_index, current_item in enumerate(current):
        assigned = assignments.get(current_index)
        if assigned is None:
            lineage = current_item.lineage_id or block_lineage_id(
                origin=current_item.reference.model_dump(mode="json")
            )
        else:
            previous_index, method, confidence = assigned
            previous_item = previous[previous_index]
            lineage = previous_lineages[previous_item.reference.block_id]
            if current_item.lineage_id is not None and current_item.lineage_id != lineage:
                raise ReconciliationError("existing target lineage conflicts with accepted match")
            relation = _relation(
                previous_item,
                current_item,
                confidence_ppm=confidence,
                created_at=current_ready_at,
            )
            relation_payload = canonical_json_bytes(relation.model_dump(mode="json"))
            matches.append(
                ReconciliationMatch(
                    previous=previous_item.reference,
                    current=current_item.reference,
                    lineage_id=lineage,
                    previous_canonical_hash=previous_item.canonical_hash,
                    current_canonical_hash=current_item.canonical_hash,
                    method=method,
                    confidence_ppm=confidence,
                    reusable=previous_item.canonical_hash == current_item.canonical_hash,
                    relation=relation,
                    relation_object=StoredObject(
                        object_id="sha256:" + hashlib.sha256(relation_payload).hexdigest(),
                        byte_length=len(relation_payload),
                    ),
                )
            )
        memberships.append(_membership(current_item, lineage, run_id))

    current_bindings = {item.binding_digest for item in memberships}
    inactive = tuple(
        sorted(
            item.binding_digest
            for item in previous_memberships
            if item.binding_digest not in current_bindings
        )
    )
    skeleton = ReconciliationPlan.model_construct(
        run_id=run_id,
        previous_scope=previous_scope,
        current_scope=current_scope,
        algorithm_version=RECONCILIATION_ALGORITHM_VERSION,
        config_hash=RECONCILIATION_CONFIG_HASH,
        seed_memberships=previous_memberships,
        memberships=tuple(memberships),
        matches=tuple(matches),
        inactive_binding_digests=inactive,
        matched_count=len(matches),
        reusable_count=sum(item.reusable for item in matches),
        new_count=len(current) - len(matches),
        ambiguous_count=sum(
            index in candidate_seen for index in range(len(current)) if index not in assignments
        ),
        comparison_count=comparison_count,
        result_fingerprint="sha256:" + "0" * 64,
        created_at=created_at,
    )
    return ReconciliationPlan(
        run_id=run_id,
        previous_scope=previous_scope,
        current_scope=current_scope,
        algorithm_version=RECONCILIATION_ALGORITHM_VERSION,
        config_hash=RECONCILIATION_CONFIG_HASH,
        seed_memberships=previous_memberships,
        memberships=tuple(memberships),
        matches=tuple(matches),
        inactive_binding_digests=inactive,
        matched_count=len(matches),
        reusable_count=sum(item.reusable for item in matches),
        new_count=len(current) - len(matches),
        ambiguous_count=sum(
            index in candidate_seen for index in range(len(current)) if index not in assignments
        ),
        comparison_count=comparison_count,
        result_fingerprint=reconciliation_result_fingerprint(skeleton),
        created_at=created_at,
    )


def _validate_aggregates(
    previous: tuple[ReconciliationBlock, ...],
    current: tuple[ReconciliationBlock, ...],
    previous_scope: RepresentationScope,
    current_scope: RepresentationScope,
) -> None:
    if len(previous) > MAX_RECONCILIATION_BLOCKS or len(current) > MAX_RECONCILIATION_BLOCKS:
        raise ReconciliationLimitExceeded("reconciliation block count exceeds limit")
    if previous_scope.document_id != current_scope.document_id:
        raise ReconciliationError("reconciliation cannot cross documents")
    if previous_scope == current_scope:
        raise ReconciliationError("reconciliation requires distinct scopes")
    _validate_block_set(previous, previous_scope)
    _validate_block_set(current, current_scope)


def _validate_block_set(
    blocks: tuple[ReconciliationBlock, ...],
    scope: RepresentationScope,
) -> None:
    if tuple(item.ordinal for item in blocks) != tuple(range(len(blocks))):
        raise ReconciliationError("reconciliation ordinals must be contiguous")
    by_id = {item.reference.block_id: item for item in blocks}
    if len(by_id) != len(blocks):
        raise ReconciliationError("reconciliation block identifiers must be unique")
    for item in blocks:
        if _scope(item) != scope:
            raise ReconciliationError("reconciliation block scope is inconsistent")
        depth = 0
        parent = item.parent_id
        seen: set[UUID] = set()
        while parent is not None:
            if parent in seen or parent not in by_id:
                raise ReconciliationError("reconciliation hierarchy is invalid")
            seen.add(parent)
            depth += 1
            if depth > MAX_RECONCILIATION_DEPTH:
                raise ReconciliationLimitExceeded("reconciliation hierarchy exceeds depth limit")
            parent = by_id[parent].parent_id


def _scope(item: ReconciliationBlock) -> RepresentationScope:
    return RepresentationScope(
        document_id=item.reference.document_id,
        version_id=item.reference.version_id,
        representation_id=item.reference.representation_id,
    )


def _membership(
    item: ReconciliationBlock,
    lineage_id: str,
    run_id: str,
) -> BlockLineageMembership:
    return BlockLineageMembership(
        lineage_id=lineage_id,
        block=item.reference,
        canonical_hash=item.canonical_hash,
        binding_digest=evidence_binding_id(
            lineage_id=lineage_id,
            canonical_hash=item.canonical_hash,
        ),
        introduced_by_run_id=item.lineage_introduced_by_run_id or run_id,
    )


def _assign_unique_phase(
    previous: tuple[ReconciliationBlock, ...],
    current: tuple[ReconciliationBlock, ...],
    assignments: dict[int, tuple[int, MatchMethod, int]],
    used_previous: set[int],
    parent_mapping: dict[UUID, UUID],
    candidate_seen: set[int],
    *,
    method: MatchMethod,
    key: object,
    confidence_ppm: int,
    require_parent: bool,
    assign: object,
) -> None:
    if not callable(key) or not callable(assign):
        raise TypeError("matcher callbacks must be callable")
    made_progress = True
    while made_progress:
        made_progress = False
        previous_groups: dict[object, list[int]] = defaultdict(list)
        current_groups: dict[object, list[int]] = defaultdict(list)
        for index, item in enumerate(previous):
            if index not in used_previous:
                value = key(item)
                if value is not None:
                    previous_groups[value].append(index)
        for index, item in enumerate(current):
            if index not in assignments:
                value = key(item)
                if value is not None:
                    current_groups[value].append(index)
        for value in sorted(set(previous_groups).intersection(current_groups), key=repr):
            previous_indices = previous_groups[value]
            current_indices = current_groups[value]
            candidate_seen.update(current_indices)
            if len(previous_indices) != 1 or len(current_indices) != 1:
                continue
            previous_index = previous_indices[0]
            current_index = current_indices[0]
            if require_parent and not _parent_compatible(
                previous[previous_index],
                current[current_index],
                parent_mapping,
            ):
                continue
            assign(current_index, previous_index, method, confidence_ppm)
            made_progress = True


def _asset_or_table_key(item: ReconciliationBlock) -> tuple[str, str] | None:
    if item.asset_id is not None:
        return (item.kind.value, item.asset_id)
    if item.kind is BlockKind.TABLE and item.structured_hash is not None:
        return (item.kind.value, item.structured_hash)
    return None


def _parent_compatible(
    previous: ReconciliationBlock,
    current: ReconciliationBlock,
    parent_mapping: dict[UUID, UUID],
) -> bool:
    if previous.parent_id is None or current.parent_id is None:
        return previous.parent_id is None and current.parent_id is None
    return parent_mapping.get(current.parent_id) == previous.parent_id


def _normalized_text(value: str) -> str:
    return _SPACE.sub(" ", value.casefold()).strip()[:MAX_SIMILARITY_TEXT]


def _similarity_ppm(previous: str, current: str) -> int:
    return round(SequenceMatcher(None, previous, current, autojunk=False).ratio() * 1_000_000)


def _assign_sequence_gaps(
    previous: tuple[ReconciliationBlock, ...],
    current: tuple[ReconciliationBlock, ...],
    assignments: dict[int, tuple[int, MatchMethod, int]],
    used_previous: set[int],
    parent_mapping: dict[UUID, UUID],
    candidate_seen: set[int],
    assign: object,
) -> None:
    if not callable(assign):
        raise TypeError("matcher callback must be callable")
    # Conservative alignment only accepts equal-position exact signatures inside a
    # bounded parent gap. Repeated signatures remain ambiguous and are never paired.
    groups_previous: dict[tuple[UUID | None, str, str], list[int]] = defaultdict(list)
    groups_current: dict[tuple[UUID | None, str, str], list[int]] = defaultdict(list)
    for index, item in enumerate(previous):
        if index not in used_previous:
            groups_previous[(item.parent_id, item.kind.value, item.canonical_hash)].append(index)
    for index, item in enumerate(current):
        if index not in assignments:
            mapped_parent = (
                parent_mapping.get(item.parent_id) if item.parent_id is not None else None
            )
            groups_current[(mapped_parent, item.kind.value, item.canonical_hash)].append(index)
    for key in sorted(set(groups_previous).intersection(groups_current), key=repr):
        previous_indices = groups_previous[key]
        current_indices = groups_current[key]
        candidate_seen.update(current_indices)
        if len(previous_indices) != 1 or len(current_indices) != 1:
            continue
        previous_index = previous_indices[0]
        current_index = current_indices[0]
        if abs(previous[previous_index].order - current[current_index].order) > MAX_SEQUENCE_GAP:
            continue
        if not _parent_compatible(previous[previous_index], current[current_index], parent_mapping):
            continue
        assign(current_index, previous_index, MatchMethod.SEQUENCE, 1_000_000)


def _relation(
    previous: ReconciliationBlock,
    current: ReconciliationBlock,
    *,
    confidence_ppm: int,
    created_at: UtcDatetime,
) -> Relation:
    source = current.reference.model_dump(mode="json")
    target = previous.reference.model_dump(mode="json")
    return Relation(
        schema_version="0.1.0",
        relation_id=relation_identity(
            kind=RelationKind.SAME_LOGICAL_BLOCK_AS.value,
            source=source,
            target=target,
        ),
        kind=RelationKind.SAME_LOGICAL_BLOCK_AS,
        source=current.reference,
        target=previous.reference,
        confidence=confidence_ppm / 1_000_000,
        algorithm_version=RECONCILIATION_ALGORITHM_VERSION,
        provenance=GenerationProvenance(
            component=ComponentDescriptor(
                name="openardp-reconciliation",
                version=RECONCILIATION_ALGORITHM_VERSION,
                profile="conservative",
            ),
            created_at=created_at,
        ),
    )


__all__ = [
    "MAX_RECONCILIATION_BLOCKS",
    "MAX_RECONCILIATION_DEPTH",
    "MAX_SEQUENCE_GAP",
    "MAX_SIMILARITY_COMPARISONS",
    "MAX_SIMILARITY_ORDER_DISTANCE",
    "MAX_SIMILARITY_TEXT",
    "MIN_SIMILARITY_PPM",
    "MIN_WINNER_MARGIN_PPM",
    "RECONCILIATION_ALGORITHM_VERSION",
    "RECONCILIATION_CONFIG_HASH",
    "BlockLineageMembership",
    "MatchMethod",
    "ReconciliationBlock",
    "ReconciliationDisposition",
    "ReconciliationError",
    "ReconciliationLimitExceeded",
    "ReconciliationMatch",
    "ReconciliationPlan",
    "ReconciliationResult",
    "reconcile_blocks",
    "reconciliation_result_fingerprint",
]
