"""Pure domain tests for conservative F010 block reconciliation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.block import BlockKind
from openardp.domain.identity import block_content_hash
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.reconciliation import (
    MAX_RECONCILIATION_DEPTH,
    MatchMethod,
    ReconciliationBlock,
    ReconciliationError,
    ReconciliationLimitExceeded,
    ReconciliationMatch,
    reconcile_blocks,
)
from openardp.domain.relation import BlockReference

DOCUMENT_ID = UUID("01890f62-24e8-7c00-8000-000000000001")
PREVIOUS_SCOPE = RepresentationScope(
    document_id=DOCUMENT_ID,
    version_id="sha256:" + "1" * 64,
    representation_id="sha256:" + "2" * 64,
)
CURRENT_SCOPE = RepresentationScope(
    document_id=DOCUMENT_ID,
    version_id="sha256:" + "3" * 64,
    representation_id="sha256:" + "4" * 64,
)
READY_AT = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 7, 31, 12, 1, tzinfo=UTC)


def _block(
    scope: RepresentationScope,
    block_id: str,
    text: str,
    *,
    order: int = 0,
    ordinal: int = 0,
    parent_id: UUID | None = None,
    kind: BlockKind = BlockKind.PARAGRAPH,
    native_id: str | None = None,
    asset_id: str | None = None,
    structured_hash: str | None = None,
) -> ReconciliationBlock:
    return ReconciliationBlock(
        reference=BlockReference(
            record_type="block",
            document_id=scope.document_id,
            version_id=scope.version_id,
            representation_id=scope.representation_id,
            block_id=UUID(block_id),
        ),
        parent_id=parent_id,
        kind=kind,
        order=order,
        ordinal=ordinal,
        canonical_hash=block_content_hash(
            kind=kind.value,
            text=text,
            structured=None,
            asset_id=asset_id,
        ),
        text=text,
        asset_id=asset_id,
        structured_hash=structured_hash,
        native_stable_id=native_id,
    )


def _plan(
    previous: tuple[ReconciliationBlock, ...],
    current: tuple[ReconciliationBlock, ...],
):
    return reconcile_blocks(
        previous,
        current,
        previous_scope=PREVIOUS_SCOPE,
        current_scope=CURRENT_SCOPE,
        current_ready_at=READY_AT,
        created_at=CREATED_AT,
    )


def test_exact_content_survives_location_change_and_is_reusable() -> None:
    """Inherit one lineage only after exact unique content survives the edit."""
    previous = (_block(PREVIOUS_SCOPE, "12345678-1234-4234-9234-123456789abc", "Exact"),)
    current = (
        _block(
            CURRENT_SCOPE,
            "12345678-1234-4234-9234-123456789abd",
            "Exact",
            order=7,
        ),
    )
    plan = _plan(previous, current)
    assert (plan.matched_count, plan.reusable_count, plan.new_count) == (1, 1, 0)
    match = plan.matches[0]
    assert match.method is MatchMethod.EXACT_CONTENT
    assert match.reusable is True
    assert match.relation.provenance.created_at == READY_AT
    assert plan.memberships[0].lineage_id == plan.seed_memberships[0].lineage_id
    assert not plan.inactive_binding_digests


def test_native_id_keeps_logical_continuity_but_changed_content_is_not_reused() -> None:
    """Separate a strong logical handle from the exact derivative input rule."""
    previous = (
        _block(
            PREVIOUS_SCOPE,
            "12345678-1234-4234-9234-123456789abc",
            "Before",
            native_id="word:paragraph:42",
        ),
    )
    current = (
        _block(
            CURRENT_SCOPE,
            "12345678-1234-4234-9234-123456789abd",
            "After",
            native_id="word:paragraph:42",
        ),
    )
    plan = _plan(previous, current)
    assert plan.matches[0].method is MatchMethod.NATIVE_ID
    assert plan.matches[0].reusable is False
    assert plan.inactive_binding_digests == (plan.seed_memberships[0].binding_digest,)


def test_unique_high_similarity_retains_lineage_without_reuse() -> None:
    """Use similarity only as conservative continuity evidence."""
    previous = (
        _block(
            PREVIOUS_SCOPE,
            "12345678-1234-4234-9234-123456789abc",
            "The quarterly revenue was exactly 1,000,000 euros in the reviewed period.",
        ),
    )
    current = (
        _block(
            CURRENT_SCOPE,
            "12345678-1234-4234-9234-123456789abd",
            "The quarterly revenue was exactly 1,000,001 euros in the reviewed period.",
        ),
    )
    plan = _plan(previous, current)
    assert plan.matches[0].method is MatchMethod.SIMILARITY
    assert plan.matches[0].confidence_ppm >= 970_000
    assert plan.matches[0].reusable is False


@pytest.mark.parametrize(
    ("kind", "asset_id", "structured_hash"),
    (
        (BlockKind.PICTURE, "sha256:" + "a" * 64, None),
        (BlockKind.TABLE, None, "sha256:" + "b" * 64),
    ),
)
def test_exact_asset_and_table_identity_establish_continuity_without_false_reuse(
    kind: BlockKind,
    asset_id: str | None,
    structured_hash: str | None,
) -> None:
    """Use exact non-text identity while retaining the exact-content reuse gate."""
    previous = (
        _block(
            PREVIOUS_SCOPE,
            "12345678-1234-4234-9234-123456789abc",
            "Before",
            kind=kind,
            asset_id=asset_id,
            structured_hash=structured_hash,
        ),
    )
    current = (
        _block(
            CURRENT_SCOPE,
            "12345678-1234-4234-9234-123456789abd",
            "After",
            kind=kind,
            asset_id=asset_id,
            structured_hash=structured_hash,
        ),
    )

    match = _plan(previous, current).matches[0]
    assert match.method is MatchMethod.ASSET_OR_TABLE
    assert match.reusable is False


def test_bounded_sequence_phase_disambiguates_equal_content_by_mapped_parent() -> None:
    """Align non-text sibling gaps only after unique parents establish structure."""
    previous_parent_a = _block(
        PREVIOUS_SCOPE,
        "12345678-1234-4234-9234-123456789a01",
        "Parent A",
        kind=BlockKind.HEADING,
    )
    previous_parent_b = _block(
        PREVIOUS_SCOPE,
        "12345678-1234-4234-9234-123456789a02",
        "Parent B",
        kind=BlockKind.HEADING,
        order=1,
        ordinal=1,
    )
    current_parent_a = _block(
        CURRENT_SCOPE,
        "12345678-1234-4234-9234-123456789b01",
        "Parent A",
        kind=BlockKind.HEADING,
    )
    current_parent_b = _block(
        CURRENT_SCOPE,
        "12345678-1234-4234-9234-123456789b02",
        "Parent B",
        kind=BlockKind.HEADING,
        order=1,
        ordinal=1,
    )
    previous_children = tuple(
        _block(
            PREVIOUS_SCOPE,
            f"12345678-1234-4234-9234-123456789a{index + 10:02d}",
            "Repeated structural payload",
            ordinal=index + 2,
            parent_id=parent.reference.block_id,
        ).model_copy(update={"text": None})
        for index, parent in enumerate((previous_parent_a, previous_parent_b))
    )
    current_children = tuple(
        _block(
            CURRENT_SCOPE,
            f"12345678-1234-4234-9234-123456789b{index + 10:02d}",
            "Repeated structural payload",
            ordinal=index + 2,
            parent_id=parent.reference.block_id,
        ).model_copy(update={"text": None})
        for index, parent in enumerate((current_parent_a, current_parent_b))
    )

    plan = _plan(
        (previous_parent_a, previous_parent_b, *previous_children),
        (current_parent_a, current_parent_b, *current_children),
    )
    assert [match.method for match in plan.matches] == [
        MatchMethod.EXACT_CONTENT,
        MatchMethod.EXACT_CONTENT,
        MatchMethod.SEQUENCE,
        MatchMethod.SEQUENCE,
    ]
    assert all(match.reusable for match in plan.matches)


def test_duplicate_exact_candidates_remain_new_and_ambiguous() -> None:
    """Never guess between duplicate boilerplate candidates."""
    previous = (
        _block(PREVIOUS_SCOPE, "12345678-1234-4234-9234-123456789ab1", "Boilerplate"),
        _block(
            PREVIOUS_SCOPE,
            "12345678-1234-4234-9234-123456789ab2",
            "Boilerplate",
            order=1,
            ordinal=1,
        ),
    )
    current = (
        _block(CURRENT_SCOPE, "12345678-1234-4234-9234-123456789ab3", "Boilerplate"),
        _block(
            CURRENT_SCOPE,
            "12345678-1234-4234-9234-123456789ab4",
            "Boilerplate",
            order=1,
            ordinal=1,
        ),
    )
    plan = _plan(previous, current)
    assert (plan.matched_count, plan.reusable_count, plan.new_count) == (0, 0, 2)
    assert plan.ambiguous_count == 2
    assert len({item.lineage_id for item in plan.memberships}) == 2


def test_empty_aggregate_changes_are_valid_and_complete() -> None:
    """Represent all-inserted and all-deleted edits without fabricating a block."""
    inserted = _plan(
        (),
        (_block(CURRENT_SCOPE, "12345678-1234-4234-9234-123456789abc", "New"),),
    )
    deleted = _plan(
        (_block(PREVIOUS_SCOPE, "12345678-1234-4234-9234-123456789abc", "Old"),),
        (),
    )
    assert (inserted.new_count, inserted.matched_count) == (1, 0)
    assert deleted.memberships == ()
    assert deleted.inactive_binding_digests == (deleted.seed_memberships[0].binding_digest,)


def test_reconciliation_rejects_same_or_cross_document_scopes() -> None:
    """Fail before matching scopes that cannot share logical lineage."""
    with pytest.raises(ReconciliationError, match="distinct"):
        reconcile_blocks(
            (),
            (),
            previous_scope=PREVIOUS_SCOPE,
            current_scope=PREVIOUS_SCOPE,
            current_ready_at=READY_AT,
            created_at=CREATED_AT,
        )
    other = CURRENT_SCOPE.model_copy(
        update={"document_id": UUID("01890f62-24e8-7c00-8000-000000000002")}
    )
    with pytest.raises(ReconciliationError, match="cross documents"):
        reconcile_blocks(
            (),
            (),
            previous_scope=PREVIOUS_SCOPE,
            current_scope=other,
            current_ready_at=READY_AT,
            created_at=CREATED_AT,
        )


def test_match_model_rejects_a_false_reuse_flag() -> None:
    """Make the zero-false-reuse rule a model invariant, not caller convention."""
    previous = (_block(PREVIOUS_SCOPE, "12345678-1234-4234-9234-123456789abc", "Before"),)
    current = (
        _block(
            CURRENT_SCOPE,
            "12345678-1234-4234-9234-123456789abd",
            "After",
            native_id="same",
        ),
    )
    previous = (previous[0].model_copy(update={"native_stable_id": "same"}),)
    match = _plan(previous, current).matches[0]
    payload = json.loads(match.model_dump_json())
    payload["reusable"] = True
    with pytest.raises(ValidationError, match="reuse requires exact"):
        ReconciliationMatch.model_validate_json(json.dumps(payload), strict=True)


def test_hierarchy_and_similarity_work_are_hard_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed before adversarial depth or candidate work can grow unbounded."""
    deep: list[ReconciliationBlock] = []
    parent: UUID | None = None
    for index in range(MAX_RECONCILIATION_DEPTH + 2):
        block_id = UUID(f"12345678-1234-4234-9234-{index + 100:012d}")
        deep.append(
            _block(
                PREVIOUS_SCOPE,
                str(block_id),
                f"depth {index}",
                ordinal=index,
                parent_id=parent,
            )
        )
        parent = block_id
    with pytest.raises(ReconciliationLimitExceeded, match="depth"):
        _plan(tuple(deep), ())

    import openardp.domain.reconciliation as reconciliation_module

    monkeypatch.setattr(reconciliation_module, "MAX_SIMILARITY_COMPARISONS", 2)
    previous = tuple(
        _block(
            PREVIOUS_SCOPE,
            f"12345678-1234-4234-9234-{index + 200:012d}",
            f"old dissimilar {index}",
            ordinal=index,
        )
        for index in range(2)
    )
    current = tuple(
        _block(
            CURRENT_SCOPE,
            f"12345678-1234-4234-9234-{index + 300:012d}",
            f"new unrelated {index}",
            ordinal=index,
        )
        for index in range(2)
    )
    with pytest.raises(ReconciliationLimitExceeded, match="comparison budget"):
        _plan(previous, current)
