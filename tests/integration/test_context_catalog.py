"""Atomic compilation persistence, exact idempotency and tamper matrices."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from openardp.adapters.context_estimators import Utf8ByteEstimator
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.common import validate_json
from openardp.domain.context_compilation import (
    ContextCompilationCommit,
    ContextCompilationRecord,
    ContextCompilationResult,
    ContextCompilationScope,
)
from openardp.domain.identity import canonical_json_bytes, context_compilation_fingerprint
from openardp.ports.catalog import (
    CatalogError,
    ContextCompilationConflict,
    RepresentationNotFound,
)
from openardp.ports.context import ContextIntegrityFailure, ContextNotFound
from openardp.services.context_compiler import (
    ContextCompilerService,
    bundle_object_bytes,
    receipt_object_bytes,
)
from openardp.services.reachability import ReachabilityService
from tests.integration.test_context_compiler import _mixed_corpus, _request
from tests.integration.test_rich_ingestion import _Clock, _TamperingStore

TASK = "alpha evidence"


def _commit_for(
    result: ContextCompilationResult,
    store: FilesystemObjectStore,
    catalog: SQLiteCatalog,
) -> ContextCompilationCommit:
    """Build the exact immutable row and scope set for one compile result."""
    receipt_object = store.put_chunks((receipt_object_bytes(result.receipt),))
    bundle_object = store.put_chunks((bundle_object_bytes(result.bundle),))
    assert receipt_object.object_id == result.receipt.receipt_id
    receipt = result.receipt
    payload: dict[str, object] = {
        "receipt_id": receipt.receipt_id,
        "receipt_object": receipt_object,
        "bundle_object": bundle_object,
        "bundle_id": result.bundle.bundle_id,
        "task_digest": receipt.task_digest,
        "algorithm": receipt.algorithm,
        "estimator": receipt.estimator,
        "policy_digest": receipt.policy_digest,
        "budget_limit": receipt.budget.limit,
        "budget_unit": receipt.budget.unit,
        "created_at": receipt.created_at,
        "selected_count": len(receipt.selected),
        "omitted_count": len(receipt.omitted),
        "rejected_count": len(receipt.rejected),
        "stale_count": len(receipt.stale),
    }
    draft = ContextCompilationRecord.model_construct(
        row_fingerprint="sha256:" + "0" * 64,
        **payload,
    )
    identity_payload = draft.model_dump(mode="json", exclude={"row_fingerprint"})
    payload["row_fingerprint"] = context_compilation_fingerprint(identity_payload)
    record = ContextCompilationRecord.model_validate(payload)
    scopes = tuple(
        ContextCompilationScope(receipt_id=receipt.receipt_id, ordinal=index, scope=scope)
        for index, scope in enumerate(receipt.corpus_snapshot)
    )
    return ContextCompilationCommit(record=record, scopes=scopes)


def _compiled(
    tmp_path: Path,
    *,
    task: str = TASK,
) -> tuple[
    ContextCompilationResult, ContextCompilationCommit, SQLiteCatalog, FilesystemObjectStore
]:
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    store, catalog = corpus.store, corpus.catalog
    result = compiler.compile(_request(document_ids, 1_000_000, task=task))
    commit = _commit_for(result, store, catalog)
    return result, commit, catalog, store


def test_commit_load_and_list_are_atomic_exact_and_ordered(tmp_path: Path) -> None:
    """Persist one compilation in one transaction and reload the exact aggregate."""
    result, commit, catalog, _store = _compiled(tmp_path)

    record = catalog.commit_context_compilation(commit)

    assert record == commit.record
    loaded = catalog.load_context_compilation(result.receipt.receipt_id)
    assert loaded == commit
    assert catalog.list_context_compilations() == (record,)
    assert catalog.load_context_compilation("sha256:" + "f" * 64) is None

    other_result, other_commit, _, _ = _compiled(tmp_path, task="beta unrelated evidence")
    other_record = catalog.commit_context_compilation(other_commit)
    assert [item.receipt_id for item in catalog.list_context_compilations()] == sorted(
        [record.receipt_id, other_record.receipt_id]
    )
    assert other_result.receipt.receipt_id == other_record.receipt_id


def test_commit_is_exactly_idempotent_and_conflicts_fail_closed(tmp_path: Path) -> None:
    """Reuse byte-identical retries and reject any differing same-identity row."""
    result, commit, catalog, _store = _compiled(tmp_path)
    first = catalog.commit_context_compilation(commit)

    second = catalog.commit_context_compilation(commit)

    assert second == first
    assert len(catalog.list_context_compilations()) == 1

    draft = commit.record.model_copy(update={"selected_count": commit.record.selected_count + 1})
    identity_payload = draft.model_dump(mode="json", exclude={"row_fingerprint"})
    tampered = validate_json(
        ContextCompilationRecord,
        canonical_json_bytes(
            {
                **identity_payload,
                "row_fingerprint": context_compilation_fingerprint(identity_payload),
            }
        ),
    )
    conflict = ContextCompilationCommit(record=tampered, scopes=commit.scopes)
    with pytest.raises(ContextCompilationConflict, match="conflict"):
        catalog.commit_context_compilation(conflict)
    assert catalog.load_context_compilation(result.receipt.receipt_id) == commit


def test_scope_rows_require_persisted_representation_roots(tmp_path: Path) -> None:
    """Reject scope rows that do not reference a persisted representation."""
    result, commit, catalog, _store = _compiled(tmp_path)
    unknown = ContextCompilationScope(
        receipt_id=commit.record.receipt_id,
        ordinal=0,
        scope=commit.scopes[0].scope.model_copy(update={"representation_id": "sha256:" + "e" * 64}),
    )
    broken = ContextCompilationCommit(record=commit.record, scopes=(unknown,))

    with pytest.raises(RepresentationNotFound, match="scope"):
        catalog.commit_context_compilation(broken)
    assert catalog.load_context_compilation(result.receipt.receipt_id) is None


def test_receipt_and_bundle_objects_are_reachability_roots(tmp_path: Path) -> None:
    """Keep both immutable compilation objects reachable like F006/F007 roots."""
    _result, commit, catalog, store = _compiled(tmp_path)
    catalog.commit_context_compilation(commit)

    snapshot = catalog.reference_snapshot(observed_at=_Clock()())
    roots = set(snapshot.object_ids)

    assert commit.record.receipt_object.object_id in roots
    assert commit.record.bundle_object.object_id in roots
    report = ReachabilityService(store, catalog).analyze(observed_at=_Clock()())
    reachable_ids = {item.object_id for item in report.reachable}
    assert commit.record.receipt_object.object_id in reachable_ids
    assert commit.record.bundle_object.object_id in reachable_ids


def test_row_fact_tampering_is_detected_on_load(tmp_path: Path) -> None:
    """Fail closed when any immutable row fact drifts from its fingerprint."""
    result, commit, catalog, _store = _compiled(tmp_path)
    catalog.commit_context_compilation(commit)
    with sqlite3.connect(catalog.path) as connection:
        connection.execute(
            "UPDATE context_compilations SET selected_count = selected_count + 1 "
            "WHERE receipt_id = ?",
            (result.receipt.receipt_id,),
        )
        connection.commit()

    with pytest.raises(CatalogError, match="integrity"):
        catalog.load_context_compilation(result.receipt.receipt_id)


def test_object_identity_tampering_is_detected_on_load(tmp_path: Path) -> None:
    """Fail closed when the row points at a different immutable object identity."""
    result, commit, catalog, _store = _compiled(tmp_path)
    catalog.commit_context_compilation(commit)
    with sqlite3.connect(catalog.path) as connection:
        connection.execute(
            "UPDATE context_compilations SET bundle_object_id = ? WHERE receipt_id = ?",
            ("sha256:" + "a" * 64, result.receipt.receipt_id),
        )
        connection.commit()

    with pytest.raises(CatalogError, match="integrity"):
        catalog.load_context_compilation(result.receipt.receipt_id)


def test_scope_ordinal_tampering_is_detected_on_load(tmp_path: Path) -> None:
    """Fail closed when scope rows lose their exact contiguous sorted order."""
    result, commit, catalog, _store = _compiled(tmp_path)
    catalog.commit_context_compilation(commit)
    assert len(commit.scopes) == 2
    with sqlite3.connect(catalog.path) as connection:
        connection.execute(
            "UPDATE context_compilation_scopes SET ordinal = 7 "
            "WHERE receipt_id = ? AND ordinal = 1",
            (result.receipt.receipt_id,),
        )
        connection.commit()

    with pytest.raises(CatalogError, match="integrity"):
        catalog.load_context_compilation(result.receipt.receipt_id)


def test_service_load_verifies_cas_bytes_and_aggregate_identities(tmp_path: Path) -> None:
    """Verify receipt/bundle objects, rows, scopes and decisions before return."""
    corpus = _mixed_corpus(tmp_path)
    compiler, document_ids = corpus.compiler, corpus.document_ids
    store, catalog = corpus.store, corpus.catalog
    persisted = compiler.compile_and_persist(_request(document_ids, 1_000_000))

    verified = compiler.load_verified(persisted.record.receipt_id)

    assert verified == persisted.result
    assert persisted.record.receipt_object.object_id == persisted.result.receipt.receipt_id
    with pytest.raises(ContextNotFound, match="compilation"):
        compiler.load_verified("sha256:" + "b" * 64)

    tampered = ContextCompilerService(
        _TamperingStore(store, persisted.record.bundle_object.object_id),
        catalog,
        Utf8ByteEstimator(),
        (),
    )
    with pytest.raises(ContextIntegrityFailure):
        tampered.load_verified(persisted.record.receipt_id)

    with sqlite3.connect(catalog.path) as connection:
        connection.execute(
            "DELETE FROM context_compilation_scopes WHERE receipt_id = ? AND ordinal = 1",
            (persisted.record.receipt_id,),
        )
        connection.commit()
    with pytest.raises(ContextIntegrityFailure, match="scope"):
        compiler.load_verified(persisted.record.receipt_id)
