"""Migration-5 and atomic rich representation catalog integration tests."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.docling_native import build_docling_recipe
from openardp.adapters.filesystem_cas import FilesystemObjectStore
from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.domain.common import ParserDescriptor
from openardp.domain.evidence import OpaqueProviderPointerAnchor, ProviderPointer
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.ingestion import (
    IngestionDisposition,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationScope,
)
from openardp.domain.manifest import (
    DocumentManifest,
    ManifestState,
    SchemaVersions,
    SourceDescriptor,
)
from openardp.domain.rich_ingestion import (
    ComponentVersion,
    ReadyRichRepresentationCommit,
    RichAttemptOutcome,
    RichEvidenceCandidate,
    RichEvidenceKind,
    RichMediaType,
    RichParseOutput,
    RichParserLimits,
)
from openardp.domain.storage import SourceKey, SourceVersionCommit, StoredObject
from openardp.ports.catalog import RepresentationConflict, RepresentationIntegrityError
from openardp.services.rich_ingestion import prepare_rich_attempt

NOW = datetime(2026, 7, 26, 14, 0, tzinfo=UTC)
DOCUMENT_ID = UUID("018f1000-0000-7000-8000-000000000011")
ATTEMPT_A = UUID("018f1000-0000-7000-8000-000000000012")
ATTEMPT_B = UUID("018f1000-0000-7000-8000-000000000013")
ATTEMPT_C = UUID("018f1000-0000-7000-8000-000000000014")
FENCING_CAPABILITY = "catalog-rich-capability-000000000001"


def _stored_model(model: DocumentManifest) -> StoredObject:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def _output(text: str = "synthetic") -> RichParseOutput:
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
            "texts": [{"self_ref": "#/texts/0", "text": text}],
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
                retrieval_text=text,
                native_pointer=pointer,
            ),
        ),
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
    )


def _setup(
    tmp_path: Path,
) -> tuple[
    SQLiteCatalog,
    FilesystemObjectStore,
    ReadyRepresentationCommit,
    RepresentationScope,
]:
    store = FilesystemObjectStore(tmp_path / "cas")
    source = store.put_chunks((b"synthetic rich source",))
    recipe = build_docling_recipe(limits=RichParserLimits(timeout_seconds=30.0))
    scope = RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=source.object_id,
        representation_id=recipe.parser.representation_id_for(source.object_id),
    )
    catalog = SQLiteCatalog(tmp_path / "catalog.sqlite3")
    assert catalog.initialize(now=NOW) == 5
    catalog.register_document(
        SourceKey(connector="local", locator="/synthetic/source.docx"),
        document_id=DOCUMENT_ID,
        now=NOW,
    )
    catalog.commit_source_version(
        SourceVersionCommit(
            document_id=DOCUMENT_ID,
            version_id=source.object_id,
            source=source,
            media_type=RichMediaType.DOCX.value,
            committed_at=NOW,
        )
    )
    manifest = DocumentManifest(
        spec_version="0.1.0",
        document_id=DOCUMENT_ID,
        version_id=source.object_id,
        representation_id=scope.representation_id,
        title="source.docx",
        state=ManifestState.READY,
        created_at=NOW,
        source=SourceDescriptor(
            connector="local",
            locator="/synthetic/source.docx",
            media_type=RichMediaType.DOCX.value,
            byte_length=source.byte_length,
            sha256=source.object_id.removeprefix("sha256:"),
        ),
        parser=ParserDescriptor(
            name=recipe.parser.name,
            version=recipe.parser.version,
            profile=recipe.parser.profile,
            config_hash=recipe.parser.config_hash,
        ),
        schema_versions=SchemaVersions(
            block=recipe.parser.normalization_schema_version,
            derivation="0.1.0",
            relation="0.1.0",
        ),
    )
    manifest_payload = canonical_json_bytes(manifest.model_dump(mode="json"))
    assert store.put_chunks((manifest_payload,)) == _stored_model(manifest)
    base = ReadyRepresentationCommit(
        scope=scope,
        recipe=recipe.parser,
        manifest=manifest,
        manifest_object=_stored_model(manifest),
        native_object=source,
        blocks=(),
        warning_codes=(),
        source_observed_at=NOW,
        ready_at=NOW + timedelta(seconds=1),
    )
    return catalog, store, base, scope


def _attempt(
    store: FilesystemObjectStore,
    scope: RepresentationScope,
    *,
    attempt_id: UUID,
    outcome: RichAttemptOutcome,
    text: str = "synthetic",
    created_at: datetime = NOW + timedelta(seconds=1),
):
    recipe = build_docling_recipe(limits=RichParserLimits(timeout_seconds=30.0))
    return prepare_rich_attempt(
        scope=scope,
        recipe=recipe,
        output=_output(text),
        object_store=store,
        attempt_id=attempt_id,
        outcome=outcome,
        created_at=created_at,
    )


def _commit_canonical(
    catalog: SQLiteCatalog,
    store: FilesystemObjectStore,
    base: ReadyRepresentationCommit,
):
    acquired = catalog.acquire_representation(
        base.scope,
        base.recipe,
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        now=NOW,
        lease_until=NOW + timedelta(minutes=5),
    )
    assert acquired.disposition is RepresentationAcquireDisposition.CLAIMED
    rich = _attempt(
        store,
        base.scope,
        attempt_id=ATTEMPT_A,
        outcome=RichAttemptOutcome.CANONICAL,
    )
    result = catalog.commit_ready_rich_representation(
        ReadyRichRepresentationCommit(base=base, rich=rich),
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        expected_revision=acquired.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    return rich, result


def test_canonical_rich_commit_is_atomic_idempotent_and_fully_reachable(
    tmp_path: Path,
) -> None:
    """Publish, reload and root every rich object through one transaction."""
    catalog, store, base, scope = _setup(tmp_path)
    rich, result = _commit_canonical(catalog, store, base)
    replay = catalog.commit_ready_rich_representation(
        ReadyRichRepresentationCommit(base=base, rich=rich),
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        expected_revision=1,
        disposition=IngestionDisposition.COMMITTED,
    )

    assert replay == result
    assert catalog.load_rich_representation(scope) == result.artifacts
    assert catalog.get_rich_attempt(ATTEMPT_A) == rich.attempt
    assert catalog.list_rich_attempts(scope) == (rich.attempt,)
    roots = set(catalog.reference_snapshot(observed_at=NOW).object_ids)
    expected = {
        rich.attempt.descriptor_object.object_id,
        rich.attempt.provider_native_object.object_id,
        rich.attempt.native_record_object.object_id,
        rich.attempt.evidence_bundle_object.object_id,
        *(
            value.object_id
            for record in rich.bundle.records
            for value in (
                record.reference_object,
                record.projection_object,
                record.retrieval_object,
            )
        ),
    }
    assert expected <= roots


def test_converged_and_diverged_attempts_are_append_only_and_preserve_acceptance(
    tmp_path: Path,
) -> None:
    """Retain complete retries while a divergent result cannot advance the head."""
    catalog, store, base, scope = _setup(tmp_path)
    canonical, result = _commit_canonical(catalog, store, base)
    converged = _attempt(
        store,
        scope,
        attempt_id=ATTEMPT_B,
        outcome=RichAttemptOutcome.CONVERGED,
        created_at=NOW + timedelta(seconds=2),
    )
    converged_result = catalog.append_rich_attempt(
        converged,
        source_observed_at=NOW + timedelta(seconds=2),
        occurred_at=NOW + timedelta(seconds=3),
    )
    replay = catalog.append_rich_attempt(
        converged,
        source_observed_at=NOW + timedelta(seconds=2),
        occurred_at=NOW + timedelta(seconds=3),
    )
    head_before_divergence = catalog.get_document_head(DOCUMENT_ID)
    divergent = _attempt(
        store,
        scope,
        attempt_id=ATTEMPT_C,
        outcome=RichAttemptOutcome.DIVERGED,
        text="different",
        created_at=NOW + timedelta(seconds=4),
    )
    divergent_result = catalog.append_rich_attempt(
        divergent,
        source_observed_at=NOW + timedelta(seconds=4),
        occurred_at=NOW + timedelta(seconds=5),
    )

    assert replay == converged_result
    assert converged_result.accepted_attempt_id == canonical.attempt.attempt_id
    assert divergent_result.accepted_attempt_id == canonical.attempt.attempt_id
    assert divergent_result.event.head_advanced is False
    assert catalog.get_document_head(DOCUMENT_ID) == head_before_divergence
    assert catalog.load_rich_representation(scope) == result.artifacts
    assert catalog.list_rich_attempts(scope) == (
        canonical.attempt,
        converged.attempt,
        divergent.attempt,
    )


def test_rich_attempt_identity_conflict_and_fault_roll_back_all_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject immutable conflicts and leave no base READY state after an injected fault."""
    catalog, store, base, scope = _setup(tmp_path)
    canonical = _attempt(
        store,
        scope,
        attempt_id=ATTEMPT_A,
        outcome=RichAttemptOutcome.CANONICAL,
    )
    acquired = catalog.acquire_representation(
        scope,
        base.recipe,
        owner_id="rich-worker",
        lease_token=FENCING_CAPABILITY,
        now=NOW,
        lease_until=NOW + timedelta(minutes=5),
    )

    def fail(point: str) -> None:
        if point == "after_rich_evidence":
            raise RuntimeError("synthetic rich transaction interruption")

    monkeypatch.setattr(catalog, "_fault_point", fail)
    with pytest.raises(RuntimeError, match="synthetic rich transaction interruption"):
        catalog.commit_ready_rich_representation(
            ReadyRichRepresentationCommit(base=base, rich=canonical),
            owner_id="rich-worker",
            lease_token=FENCING_CAPABILITY,
            expected_revision=acquired.representation.revision,
            disposition=IngestionDisposition.COMMITTED,
        )
    assert catalog.load_rich_representation(scope) is None
    assert catalog.get_rich_attempt(ATTEMPT_A) is None
    assert catalog.load_representation(scope).representation.state.value == "STAGING"  # type: ignore[union-attr]

    monkeypatch.setattr(catalog, "_fault_point", lambda _point: None)
    _commit_canonical(catalog, store, base)
    conflicting = _attempt(
        store,
        scope,
        attempt_id=ATTEMPT_B,
        outcome=RichAttemptOutcome.CONVERGED,
        created_at=NOW + timedelta(seconds=2),
    )
    catalog.append_rich_attempt(
        conflicting,
        source_observed_at=NOW + timedelta(seconds=2),
        occurred_at=NOW + timedelta(seconds=3),
    )
    changed = _attempt(
        store,
        scope,
        attempt_id=ATTEMPT_B,
        outcome=RichAttemptOutcome.CONVERGED,
        text="changed",
        created_at=NOW + timedelta(seconds=2),
    )
    with pytest.raises(RepresentationConflict, match="conflicting"):
        catalog.append_rich_attempt(
            changed,
            source_observed_at=NOW + timedelta(seconds=2),
            occurred_at=NOW + timedelta(seconds=3),
        )


def test_rich_catalog_row_drift_is_rejected_from_one_snapshot(tmp_path: Path) -> None:
    """Cross-check indexed columns and canonical JSON rather than trusting either alone."""
    catalog, store, base, scope = _setup(tmp_path)
    _commit_canonical(catalog, store, base)
    with sqlite3.connect(catalog.path) as connection:
        connection.execute(
            "UPDATE rich_parse_attempts SET outcome = 'CONVERGED' WHERE attempt_id = ?",
            (str(ATTEMPT_A),),
        )
        connection.commit()

    with pytest.raises(RepresentationIntegrityError, match="catalog facts"):
        catalog.load_rich_representation(scope)
