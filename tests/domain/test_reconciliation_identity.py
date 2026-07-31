"""Golden tests for the additive F010 persisted identity domains."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openardp.domain.identity import (
    block_lineage_id,
    derivation_slot_id,
    evidence_binding_id,
    reconciliation_run_id,
)

ROOT = Path(__file__).parents[2]
VECTORS = ROOT / "tests" / "fixtures" / "reconciliation" / "identity" / "identity-vectors.json"


def _vectors() -> dict[str, object]:
    return json.loads(VECTORS.read_text(encoding="utf-8"))


def test_f010_identity_domains_match_reviewed_vectors() -> None:
    """Pin all four ADR-0011 domains to independent reviewed fixture values."""
    vectors = _vectors()
    origin = vectors["origin"]
    previous = vectors["previous_scope"]
    current = vectors["current_scope"]
    slot = vectors["slot"]
    assert isinstance(origin, dict)
    assert isinstance(previous, dict)
    assert isinstance(current, dict)
    assert isinstance(slot, dict)
    assert block_lineage_id(origin=origin) == vectors["lineage_id"]  # type: ignore[arg-type]
    assert (
        evidence_binding_id(
            lineage_id=str(vectors["lineage_id"]),
            canonical_hash=str(vectors["canonical_hash"]),
        )
        == vectors["binding_id"]
    )
    assert (
        reconciliation_run_id(
            previous_scope=previous,  # type: ignore[arg-type]
            current_scope=current,  # type: ignore[arg-type]
            algorithm_version=str(vectors["algorithm_version"]),
            config_hash=str(vectors["config_hash"]),
        )
        == vectors["run_id"]
    )
    assert (
        derivation_slot_id(
            namespace=str(slot["namespace"]),
            subject_digest=str(slot["subject_digest"]),
            purpose=str(slot["purpose"]),
        )
        == slot["slot_id"]
    )


@pytest.mark.parametrize(
    ("call", "message"),
    (
        (
            lambda: block_lineage_id(
                origin={"record_type": "artifact", "artifact_id": "sha256:" + "1" * 64}
            ),
            "block reference",
        ),
        (
            lambda: evidence_binding_id(lineage_id="invalid", canonical_hash="sha256:" + "2" * 64),
            "lineage_id",
        ),
        (
            lambda: reconciliation_run_id(
                previous_scope={"document_id": "doc", "version_id": "sha256:" + "1" * 64},
                current_scope={
                    "document_id": "doc",
                    "version_id": "sha256:" + "2" * 64,
                    "representation_id": "sha256:" + "3" * 64,
                },
                algorithm_version="v1",
                config_hash="sha256:" + "4" * 64,
            ),
            "exactly",
        ),
        (
            lambda: derivation_slot_id(namespace="safe", subject_digest="bad", purpose="summary"),
            "subject_digest",
        ),
    ),
)
def test_f010_identity_helpers_reject_malformed_projections(call: object, message: str) -> None:
    """Reject incomplete or non-hash identity inputs instead of normalizing them."""
    assert callable(call)
    with pytest.raises(ValueError, match=message):
        call()


def test_f010_identities_are_stable_across_fresh_processes() -> None:
    """Reproduce the fixture twenty times under varied randomized hash seeds."""
    code = """
import json
import sys
from pathlib import Path
from openardp.domain.identity import (
    block_lineage_id,
    derivation_slot_id,
    evidence_binding_id,
    reconciliation_run_id,
)
vectors = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
slot = vectors['slot']
result = [
    block_lineage_id(origin=vectors['origin']),
    evidence_binding_id(
        lineage_id=vectors['lineage_id'],
        canonical_hash=vectors['canonical_hash'],
    ),
    reconciliation_run_id(
        previous_scope=vectors['previous_scope'],
        current_scope=vectors['current_scope'],
        algorithm_version=vectors['algorithm_version'],
        config_hash=vectors['config_hash'],
    ),
    derivation_slot_id(
        namespace=slot['namespace'],
        subject_digest=slot['subject_digest'],
        purpose=slot['purpose'],
    ),
]
print(json.dumps(result))
"""
    vectors = _vectors()
    slot = vectors["slot"]
    assert isinstance(slot, dict)
    expected = [
        vectors["lineage_id"],
        vectors["binding_id"],
        vectors["run_id"],
        slot["slot_id"],
    ]
    for seed in range(20):
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned code
            [sys.executable, "-c", code, str(VECTORS)],
            check=True,
            capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
        )
        assert json.loads(completed.stdout) == expected
