"""Golden independent identity vectors for F008 context identities."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from openardp.domain.context_compilation import task_digest
from openardp.domain.identity import (
    context_bundle_id,
    context_compilation_fingerprint,
    context_policy_id,
    selection_receipt_id,
)

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "context"


def _vectors() -> dict[str, object]:
    """Load reviewed independent F008 canonicalization and identity vectors."""
    vectors: dict[str, object] = json.loads(
        (FIXTURES / "canonicalization-vectors.json").read_text(encoding="utf-8")
    )
    return vectors


def _fixture(name: str) -> dict[str, object]:
    payload: dict[str, object] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return payload


def test_task_digest_matches_independent_vector() -> None:
    """Pin the exact UTF-8 task digest without retaining task text."""
    vector = _vectors()["task_digest"]
    assert isinstance(vector, dict)
    assert task_digest(str(vector["task"])) == vector["digest"]


def test_context_policy_identity_matches_independent_vector() -> None:
    """Pin the domain-separated complete-policy digest."""
    vector = _vectors()["context_policy"]
    assert isinstance(vector, dict)
    policy = vector["policy"]
    assert isinstance(policy, dict)
    assert context_policy_id(policy) == vector["digest"]  # type: ignore[arg-type]
    assert _fixture("selection-receipt.json")["policy_digest"] == vector["digest"]


def test_selection_receipt_identity_matches_golden_fixture() -> None:
    """Recompute the receipt identity from every semantic fixture field."""
    vector = _vectors()["selection_receipt"]
    assert isinstance(vector, dict)
    fixture = _fixture("selection-receipt.json")
    payload = {key: value for key, value in fixture.items() if key != "receipt_id"}
    assert selection_receipt_id(payload) == vector["receipt_id"]  # type: ignore[arg-type]
    assert fixture["receipt_id"] == vector["receipt_id"]


def test_context_bundle_identity_matches_golden_fixture() -> None:
    """Recompute the deterministic UUIDv5 from every semantic fixture field."""
    vector = _vectors()["context_bundle"]
    assert isinstance(vector, dict)
    fixture = _fixture("context-bundle-0.2.0.json")
    payload = {key: value for key, value in fixture.items() if key != "bundle_id"}
    assert str(context_bundle_id(payload)) == vector["bundle_id"]  # type: ignore[arg-type]
    assert fixture["bundle_id"] == vector["bundle_id"]


def test_compilation_row_fingerprint_matches_independent_vector() -> None:
    """Pin the immutable catalog row fingerprint projection."""
    vector = _vectors()["context_compilation_row"]
    assert isinstance(vector, dict)
    record = vector["record"]
    assert isinstance(record, dict)
    assert context_compilation_fingerprint(record) == vector["fingerprint"]  # type: ignore[arg-type]


def test_identity_payloads_reject_embedded_identifiers() -> None:
    """Keep identity inputs free of the field they derive."""
    fixture = _fixture("selection-receipt.json")
    with pytest.raises(ValueError, match="receipt_id"):
        selection_receipt_id(fixture)  # type: ignore[arg-type]
    bundle = _fixture("context-bundle-0.2.0.json")
    with pytest.raises(ValueError, match="bundle_id"):
        context_bundle_id(bundle)  # type: ignore[arg-type]


def test_context_identities_are_stable_across_fresh_processes() -> None:
    """Reproduce every F008 identity outside the current interpreter state."""
    code = """
import json
import sys
from pathlib import Path
from openardp.domain.context_compilation import task_digest
from openardp.domain.identity import (
    context_bundle_id,
    context_compilation_fingerprint,
    context_policy_id,
    selection_receipt_id,
)
root = Path(sys.argv[1])
fixtures = root / "tests" / "fixtures" / "context"
vectors = json.loads((fixtures / "canonicalization-vectors.json").read_text(encoding="utf-8"))
receipt = json.loads((fixtures / "selection-receipt.json").read_text(encoding="utf-8"))
bundle = json.loads((fixtures / "context-bundle-0.2.0.json").read_text(encoding="utf-8"))
receipt_payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
bundle_payload = {key: value for key, value in bundle.items() if key != "bundle_id"}
results = [
    task_digest(vectors["task_digest"]["task"]),
    context_policy_id(vectors["context_policy"]["policy"]),
    selection_receipt_id(receipt_payload),
    str(context_bundle_id(bundle_payload)),
    context_compilation_fingerprint(vectors["context_compilation_row"]["record"]),
]
print(json.dumps(results))
"""
    expected = [
        _vectors()["task_digest"]["digest"],  # type: ignore[index]
        _vectors()["context_policy"]["digest"],  # type: ignore[index]
        _vectors()["selection_receipt"]["receipt_id"],  # type: ignore[index]
        _vectors()["context_bundle"]["bundle_id"],  # type: ignore[index]
        _vectors()["context_compilation_row"]["fingerprint"],  # type: ignore[index]
    ]
    for seed in ("0", "1", "42"):
        environment = {**os.environ, "PYTHONHASHSEED": seed}
        completed = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned script
            [sys.executable, "-c", code, str(ROOT)],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )
        assert json.loads(completed.stdout) == expected
