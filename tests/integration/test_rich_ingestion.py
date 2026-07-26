"""In-memory F006 evidence construction for one actual rich provider result."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.docling_native import build_docling_recipe
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.local_source import LocalSource
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.evidence import (
    OpaqueProviderPointerAnchor,
    ProviderPointer,
    validate_evidence_records,
)
from openardp.domain.ingestion import IngestionDisposition, RepresentationScope
from openardp.domain.rich_ingestion import (
    ComponentVersion,
    RichAttemptOutcome,
    RichEvidenceCandidate,
    RichEvidenceKind,
    RichMediaType,
    RichParseOutput,
    RichParserLimits,
    RichParserRecipe,
)
from openardp.domain.storage import ObjectInventory, StoredObject
from openardp.ports.catalog import RepresentationIntegrityError
from openardp.ports.object_store import ObjectCorrupt, ObjectPublicationError
from openardp.ports.parser import ParserProcessCrashed
from openardp.services.rich_ingestion import RichIngestionService, prepare_rich_attempt

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
SOURCE_ID = "sha256:" + "1" * 64
DOCUMENT_ID = UUID("018f1000-0000-7000-8000-000000000001")
ATTEMPT_ID = UUID("018f1000-0000-7000-8000-000000000002")


class _Clock:
    def __init__(self) -> None:
        self._tick = 0

    def __call__(self) -> datetime:
        value = NOW + timedelta(seconds=self._tick)
        self._tick += 1
        return value


class _Parser:
    def __init__(self, *, model_bundle_id: str | None = None) -> None:
        self._recipe = build_docling_recipe(
            limits=RichParserLimits(timeout_seconds=30.0),
            model_bundle_id=model_bundle_id,
        )
        self.text = "synthetic"
        self.calls = 0
        self.failure: Exception | None = None

    @property
    def recipe(self) -> RichParserRecipe:
        return self._recipe

    def supports(self, media_type: str) -> bool:
        return media_type == RichMediaType.DOCX.value

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> RichParseOutput:
        assert b"".join(chunks)
        assert media_type == RichMediaType.DOCX.value
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        pointer = ProviderPointer(
            provider_profile="openardp-docling-native",
            provider_profile_version="0.1.0",
            pointer_format="rfc6901-json-pointer",
            pointer="#/texts/0",
        )
        return RichParseOutput(
            media_type=RichMediaType.DOCX,
            native_document={
                "schema_name": "DoclingDocument",
                "texts": [{"self_ref": "#/texts/0", "text": self.text}],
            },
            candidates=(
                RichEvidenceCandidate(
                    ordinal=0,
                    kind=RichEvidenceKind.TEXT,
                    anchor=OpaqueProviderPointerAnchor(
                        anchor_type="provider_pointer",
                        target=pointer,
                    ),
                    retrieval_media_type="text/plain",
                    retrieval_text=self.text,
                    native_pointer=pointer,
                ),
            ),
            component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
        )

    def resolve(
        self,
        native_document: dict[str, object],
        *,
        pointer: str,
    ) -> object:
        del pointer
        return native_document


class _TamperingStore:
    def __init__(self, delegate: FilesystemObjectStore, target: str) -> None:
        self._delegate = delegate
        self._target = target

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        return self._delegate.put_chunks(chunks)

    def iter_chunks(
        self,
        object_id: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        return self._delegate.iter_chunks(object_id, chunk_size=chunk_size)

    def verify(
        self,
        object_id: str,
        *,
        expected_length: int | None = None,
    ) -> StoredObject:
        if object_id == self._target:
            raise ObjectCorrupt("synthetic object corruption")
        return self._delegate.verify(object_id, expected_length=expected_length)

    def inventory(self) -> ObjectInventory:
        return self._delegate.inventory()


class _FailingPutStore(_TamperingStore):
    def __init__(self, delegate: FilesystemObjectStore, *, fail_on_call: int) -> None:
        super().__init__(delegate, "sha256:" + "0" * 64)
        self._put_calls = 0
        self._fail_on_call = fail_on_call

    def put_chunks(self, chunks: Iterable[bytes]) -> StoredObject:
        self._put_calls += 1
        if self._put_calls == self._fail_on_call:
            raise ObjectPublicationError("object publication failed")
        return self._delegate.put_chunks(chunks)


def test_strict_output_becomes_complete_cas_backed_f006_evidence(
    tmp_path: Path,
) -> None:
    """Store complete native JSON and thin source-bound evidence with exact identities."""
    limits = RichParserLimits(timeout_seconds=30.0)
    recipe = build_docling_recipe(limits=limits)
    pointer = ProviderPointer(
        provider_profile="openardp-docling-native",
        provider_profile_version="0.1.0",
        pointer_format="rfc6901-json-pointer",
        pointer="#/texts/0",
    )
    output = RichParseOutput(
        media_type=RichMediaType.DOCX,
        native_document={
            "schema_name": "DoclingDocument",
            "texts": [{"self_ref": "#/texts/0", "text": "synthetic"}],
        },
        candidates=(
            RichEvidenceCandidate(
                ordinal=0,
                kind=RichEvidenceKind.TEXT,
                anchor=OpaqueProviderPointerAnchor(
                    anchor_type="provider_pointer",
                    target=pointer,
                ),
                retrieval_media_type="text/plain",
                retrieval_text="synthetic",
                native_pointer=pointer,
            ),
        ),
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
    )
    scope = RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=SOURCE_ID,
        representation_id=recipe.parser.representation_id_for(SOURCE_ID),
    )
    store = FilesystemObjectStore(tmp_path / "cas")

    commit = prepare_rich_attempt(
        scope=scope,
        recipe=recipe,
        output=output,
        object_store=store,
        attempt_id=ATTEMPT_ID,
        outcome=RichAttemptOutcome.CANONICAL,
        created_at=NOW,
    )

    bundle = commit.bundle
    validate_evidence_records(
        bundle.native_representation,
        bundle.references,
        bundle.projections,
        expected_source_version_id=SOURCE_ID,
    )
    assert commit.attempt.projection_count == len(bundle.records)
    assert store.verify(commit.attempt.provider_native_object.object_id)
    assert store.verify(commit.attempt.evidence_bundle_object.object_id)
    assert all(store.verify(record.retrieval_object.object_id) for record in bundle.records)
    assert all(
        projection.trust.instruction_execution_allowed is False for projection in bundle.projections
    )


def _service(
    tmp_path: Path,
    parser: _Parser,
    *,
    store: FilesystemObjectStore | _TamperingStore | None = None,
    catalog: SQLiteCatalog | None = None,
    clock: _Clock | None = None,
) -> tuple[RichIngestionService, FilesystemObjectStore, SQLiteCatalog]:
    selected_store = store or FilesystemObjectStore(tmp_path / "cas")
    physical_store = (
        selected_store._delegate if isinstance(selected_store, _TamperingStore) else selected_store
    )
    selected_catalog = catalog or SQLiteCatalog(tmp_path / "catalog.sqlite3")
    selected_catalog.initialize(now=NOW)
    service = RichIngestionService(
        selected_store,
        selected_catalog,
        parser,
        source_factory=LocalSource,
        clock=clock or _Clock(),
        owner_id_factory=lambda: "rich-service-worker",
        lease_token_factory=lambda: "rich-service-capability-000000000001",
        random_bits=lambda: 1,
    )
    return service, physical_store, selected_catalog


def test_rich_service_reuses_ten_times_then_records_convergence_and_divergence(
    tmp_path: Path,
) -> None:
    """Invoke the parser once for exact reuse and retain forced outcomes append-only."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    service, _store, catalog = _service(tmp_path, parser)

    committed = service.ingest(source)
    repeats = tuple(service.ingest(source) for _ in range(10))
    converged = service.ingest(source, force=True)
    accepted_before_divergence = catalog.load_rich_representation(committed.scope)
    parser.text = "different"
    divergent = service.ingest(source, force=True)

    assert committed.disposition is IngestionDisposition.COMMITTED
    assert all(result.disposition is IngestionDisposition.CACHE_HIT for result in repeats)
    assert parser.calls == 3
    assert converged.attempt_outcome is RichAttemptOutcome.CONVERGED
    assert converged.accepted_attempt_id == committed.accepted_attempt_id
    assert divergent.attempt_outcome is RichAttemptOutcome.DIVERGED
    assert divergent.head_advanced is False
    assert divergent.accepted_attempt_id == committed.accepted_attempt_id
    assert catalog.load_rich_representation(committed.scope) == accepted_before_divergence
    assert len(catalog.list_rich_attempts(committed.scope)) == 3


def test_changed_source_and_recipe_each_create_new_exact_representation(
    tmp_path: Path,
) -> None:
    """Invalidate cache identity for changed bytes and changed provider configuration."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    clock = _Clock()
    service, store, catalog = _service(tmp_path, parser, clock=clock)
    first = service.ingest(source)

    source.write_bytes(b"source-v2")
    changed_source = service.ingest(source)

    changed_parser = _Parser(model_bundle_id="sha256:" + "a" * 64)
    changed_service, _store, _catalog = _service(
        tmp_path,
        changed_parser,
        store=store,
        catalog=catalog,
        clock=clock,
    )
    changed_recipe = changed_service.ingest(source)

    assert parser.calls == 2
    assert changed_parser.calls == 1
    assert changed_source.scope.version_id != first.scope.version_id
    assert changed_recipe.scope.version_id == changed_source.scope.version_id
    assert changed_recipe.scope.representation_id != changed_source.scope.representation_id
    assert changed_source.disposition is IngestionDisposition.COMMITTED
    assert changed_recipe.disposition is IngestionDisposition.COMMITTED


def test_cache_verification_rejects_tamper_for_every_rich_object_class(
    tmp_path: Path,
) -> None:
    """Refuse cache reuse when any accepted base or rich CAS object fails verification."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    clock = _Clock()
    service, store, catalog = _service(tmp_path, parser, clock=clock)
    committed = service.ingest(source)
    artifacts = catalog.load_rich_representation(committed.scope)
    assert artifacts is not None
    representation = artifacts.aggregate.representation
    assert representation.manifest_object is not None
    assert representation.native_object is not None
    record = artifacts.bundle.records[0]
    object_ids = (
        representation.manifest_object.object_id,
        representation.native_object.object_id,
        artifacts.accepted_attempt.descriptor_object.object_id,
        artifacts.accepted_attempt.provider_native_object.object_id,
        artifacts.accepted_attempt.native_record_object.object_id,
        artifacts.accepted_attempt.evidence_bundle_object.object_id,
        record.reference_object.object_id,
        record.projection_object.object_id,
        record.retrieval_object.object_id,
    )

    for object_id in object_ids:
        tampered_service, _store, _catalog = _service(
            tmp_path,
            parser,
            store=_TamperingStore(store, object_id),
            catalog=catalog,
            clock=clock,
        )
        with pytest.raises(
            (RepresentationIntegrityError, ObjectCorrupt),
            match=r"integrity|corruption",
        ):
            tampered_service.ingest(source)
    assert parser.calls == 1


def test_cas_publication_failure_marks_retryable_without_incomplete_ready_state(
    tmp_path: Path,
) -> None:
    """Fail a claimed parse safely, then retry it through the same durable scope."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    clock = _Clock()
    physical = FilesystemObjectStore(tmp_path / "cas")
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    failing_service, _store, _catalog = _service(
        tmp_path,
        parser,
        store=_FailingPutStore(physical, fail_on_call=2),
        catalog=catalog,
        clock=clock,
    )

    with pytest.raises(ObjectPublicationError, match="publication failed"):
        failing_service.ingest(source)

    source_id = "sha256:" + hashlib.sha256(b"source-v1").hexdigest()
    document = catalog.get_document_by_source(LocalSource(source).source_key)
    assert document is not None
    scope = RepresentationScope(
        document_id=document.document_id,
        version_id=source_id,
        representation_id=parser.recipe.parser.representation_id_for(source_id),
    )
    failed = catalog.load_representation(scope)
    assert failed is not None
    assert failed.representation.state.value == "FAILED"
    assert catalog.load_rich_representation(scope) is None

    retry_service, _store, _catalog = _service(
        tmp_path,
        parser,
        store=physical,
        catalog=catalog,
        clock=clock,
    )
    result = retry_service.ingest(source)
    ready = catalog.load_representation(scope)
    assert result.disposition is IngestionDisposition.COMMITTED
    assert ready is not None
    assert ready.representation.attempt_count == 2


def test_catalog_commit_and_forced_parser_failures_preserve_atomic_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Roll back catalog publication and retain accepted data on later parser failure."""
    source = tmp_path / "source.docx"
    source.write_bytes(b"source-v1")
    parser = _Parser()
    clock = _Clock()
    service, store, catalog = _service(tmp_path, parser, clock=clock)

    def fail(point: str) -> None:
        if point == "before_rich_representation_commit":
            raise RuntimeError("synthetic catalog commit failure")

    monkeypatch.setattr(catalog, "_fault_point", fail)
    with pytest.raises(RuntimeError, match="catalog commit failure"):
        service.ingest(source)
    document = catalog.get_document_by_source(LocalSource(source).source_key)
    assert document is not None
    source_id = "sha256:" + hashlib.sha256(b"source-v1").hexdigest()
    scope = RepresentationScope(
        document_id=document.document_id,
        version_id=source_id,
        representation_id=parser.recipe.parser.representation_id_for(source_id),
    )
    assert catalog.load_rich_representation(scope) is None
    failed = catalog.load_representation(scope)
    assert failed is not None and failed.representation.state.value == "FAILED"

    monkeypatch.setattr(catalog, "_fault_point", lambda _point: None)
    retry, _store, _catalog = _service(
        tmp_path,
        parser,
        store=store,
        catalog=catalog,
        clock=clock,
    )
    committed = retry.ingest(source)
    accepted = catalog.load_rich_representation(committed.scope)
    head = catalog.get_document_head(document.document_id)
    parser.failure = ParserProcessCrashed("parser process crashed")
    with pytest.raises(ParserProcessCrashed, match="process crashed"):
        retry.ingest(source, force=True)
    assert catalog.load_rich_representation(committed.scope) == accepted
    assert catalog.get_document_head(document.document_id) == head
    assert len(catalog.list_rich_attempts(committed.scope)) == 1
