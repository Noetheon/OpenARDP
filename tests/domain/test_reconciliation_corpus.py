"""Labelled offline safety corpus for conservative F010 reuse decisions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from openardp.domain.block import BlockKind
from openardp.domain.identity import block_content_hash
from openardp.domain.ingestion import RepresentationScope
from openardp.domain.reconciliation import MatchMethod, ReconciliationBlock, reconcile_blocks
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
NOW = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)


def _block(
    scope: RepresentationScope,
    block_id: UUID,
    text: str,
    *,
    order: int = 0,
    ordinal: int = 0,
    native_id: str | None = None,
) -> ReconciliationBlock:
    return ReconciliationBlock(
        reference=BlockReference(
            record_type="block",
            document_id=scope.document_id,
            version_id=scope.version_id,
            representation_id=scope.representation_id,
            block_id=block_id,
        ),
        kind=BlockKind.PARAGRAPH,
        order=order,
        ordinal=ordinal,
        canonical_hash=block_content_hash(
            kind=BlockKind.PARAGRAPH.value,
            text=text,
            structured=None,
            asset_id=None,
        ),
        text=text,
        native_stable_id=native_id,
    )


def _id(index: int, side: int) -> UUID:
    return UUID(f"12345678-1234-4234-9234-{index * 10 + side:012d}")


def test_labelled_corpus_has_zero_false_reuse_and_reports_exact_metrics(
    repository_root: Path,
) -> None:
    """Audit at least 100 labelled decisions with an unconditional precision gate."""
    manifest = json.loads(
        (repository_root / "tests/fixtures/reconciliation/corpus-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    decisions = 0
    true_reusable = 0
    predicted_reusable = 0
    true_positive = 0
    false_reuse = 0
    methods: Counter[MatchMethod] = Counter()
    cursor = 0
    for cohort in manifest["cohorts"]:
        for _ in range(int(cohort["count"])):
            cursor += 1
            name = str(cohort["name"])
            if name == "unique_exact_reuse":
                text = f"Reviewed exact evidence {cursor}"
                previous = (_block(PREVIOUS_SCOPE, _id(cursor, 1), text),)
                current = (_block(CURRENT_SCOPE, _id(cursor, 2), text),)
                labels = (True,)
            elif name == "native_continuity_changed_content":
                native = f"synthetic:paragraph:{cursor}"
                previous = (
                    _block(PREVIOUS_SCOPE, _id(cursor, 1), f"Before {cursor}", native_id=native),
                )
                current = (
                    _block(CURRENT_SCOPE, _id(cursor, 2), f"After {cursor}", native_id=native),
                )
                labels = (False,)
            elif name == "new_insertions":
                previous = ()
                current = (_block(CURRENT_SCOPE, _id(cursor, 2), f"Inserted {cursor}"),)
                labels = (False,)
            else:
                text = f"Duplicate boilerplate {cursor}"
                previous = (
                    _block(PREVIOUS_SCOPE, _id(cursor, 1), text),
                    _block(PREVIOUS_SCOPE, _id(cursor, 2), text, order=1, ordinal=1),
                )
                current = (
                    _block(CURRENT_SCOPE, _id(cursor, 3), text),
                    _block(CURRENT_SCOPE, _id(cursor, 4), text, order=1, ordinal=1),
                )
                labels = (False, False)
            plan = reconcile_blocks(
                previous,
                current,
                previous_scope=PREVIOUS_SCOPE,
                current_scope=CURRENT_SCOPE,
                current_ready_at=NOW,
                created_at=NOW,
            )
            predicted = {match.current.block_id: match.reusable for match in plan.matches}
            for block, expected in zip(current, labels, strict=True):
                actual = predicted.get(block.reference.block_id, False)
                decisions += 1
                true_reusable += expected
                predicted_reusable += actual
                true_positive += expected and actual
                false_reuse += actual and not expected
            methods.update(match.method for match in plan.matches)

    precision = true_positive / predicted_reusable
    recall = true_positive / true_reusable
    assert decisions == 130
    assert false_reuse == 0
    assert precision == 1.0
    assert recall == 1.0
    assert methods == Counter({MatchMethod.EXACT_CONTENT: 60, MatchMethod.NATIVE_ID: 30})


def test_complete_plan_and_relation_bytes_are_fresh_process_deterministic() -> None:
    """Reproduce the complete decision fingerprint under varied hash randomization."""
    code = """
import json
from tests.domain.test_reconciliation import (
    CURRENT_SCOPE, PREVIOUS_SCOPE, _block, _plan,
)
previous = (
    _block(PREVIOUS_SCOPE, '12345678-1234-4234-9234-123456789a01', 'Exact', ordinal=0),
    _block(
        PREVIOUS_SCOPE, '12345678-1234-4234-9234-123456789a02', 'Before',
        ordinal=1, order=1, native_id='native:2',
    ),
)
current = (
    _block(CURRENT_SCOPE, '12345678-1234-4234-9234-123456789b01', 'Exact', ordinal=0),
    _block(
        CURRENT_SCOPE, '12345678-1234-4234-9234-123456789b02', 'After',
        ordinal=1, order=1, native_id='native:2',
    ),
)
plan = _plan(previous, current)
print(json.dumps([
    plan.result_fingerprint,
    [item.relation_object.object_id for item in plan.matches],
]))
"""
    outputs = []
    for seed in range(10):
        completed = subprocess.run(  # noqa: S603 -- fixed interpreter and test code
            [sys.executable, "-c", code],
            check=True,
            capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    assert outputs == [outputs[0]] * 10
