"""Integration tests for migration 3 and atomic representation persistence."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.sqlite_catalog import SQLiteCatalog
from openardp.adapters.sqlite_migrations import MIGRATION_1, MIGRATION_2
from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    ParserDescriptor,
    Sensitivity,
    SourceLocator,
    TrustZone,
)
from openardp.domain.identity import block_content_hash, canonical_json_bytes
from openardp.domain.ingestion import (
    IngestionDisposition,
    ParserRecipe,
    PreparedRepresentationBlock,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationScope,
    RepresentationState,
    TextMediaType,
    deterministic_block_id,
)
from openardp.domain.manifest import (
    DocumentManifest,
    ManifestState,
    SchemaVersions,
    SourceDescriptor,
)
from openardp.domain.storage import SourceKey, SourceVersionCommit, StoredObject
from openardp.ports.catalog import (
    RepresentationConflict,
    RepresentationLeaseConflict,
)

NOW = datetime(2026, 7, 22, 17, 0, tzinfo=UTC)
DOCUMENT_ID = UUID("01890f62-24e8-7c00-8000-000000000001")
VERSION_A = "sha256:" + "1" * 64
VERSION_B = "sha256:" + "3" * 64
TOKEN_A = "a" * 32
TOKEN_B = "b" * 32


def _stored_json(model: ContentBlock | DocumentManifest) -> StoredObject:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def _recipe(*, config: str = "2") -> ParserRecipe:
    return ParserRecipe(
        name="openardp-text",
        version="1",
        profile="default",
        config_hash="sha256:" + config * 64,
        normalization_schema_version="0.1.0",
    )


def _scope(
    version_id: str = VERSION_A,
    *,
    recipe: ParserRecipe | None = None,
) -> RepresentationScope:
    selected = recipe or _recipe()
    return RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=version_id,
        representation_id=selected.representation_id_for(version_id),
    )


def _ready_commit(
    version_id: str = VERSION_A,
    *,
    recipe: ParserRecipe | None = None,
    observed_at: datetime = NOW,
    ready_at: datetime = NOW + timedelta(seconds=1),
) -> ReadyRepresentationCommit:
    selected = recipe or _recipe()
    scope = _scope(version_id, recipe=selected)
    canonical_hash = block_content_hash(
        kind=BlockKind.PARAGRAPH.value,
        text="Evidence",
        structured=None,
        asset_id=None,
    )
    block = ContentBlock(
        schema_version="0.1.0",
        block_id=deterministic_block_id(
            document_id=DOCUMENT_ID,
            structural_path=("root", "paragraph:0"),
            kind=BlockKind.PARAGRAPH,
            canonical_hash=canonical_hash,
            line_start=1,
            line_end=1,
            occurrence=0,
        ),
        document_id=DOCUMENT_ID,
        version_id=version_id,
        representation_id=scope.representation_id,
        kind=BlockKind.PARAGRAPH,
        order=0,
        text="Evidence",
        canonical_hash=canonical_hash,
        source=SourceLocator(
            extraction_method="openardp-text-v1",
            extensions={"openardp.text": {"line_start": 1, "line_end": 1}},
        ),
        trust=DataTrustClassification(
            zone=TrustZone.EXTERNAL_UNTRUSTED,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.UNKNOWN,
        ),
    )
    manifest = DocumentManifest(
        spec_version="0.1.0",
        document_id=DOCUMENT_ID,
        version_id=version_id,
        representation_id=scope.representation_id,
        title="source.txt",
        state=ManifestState.READY,
        created_at=NOW,
        source=SourceDescriptor(
            connector="local",
            locator="/synthetic/source.txt",
            media_type=TextMediaType.PLAIN.value,
            byte_length=8,
            sha256=version_id.removeprefix("sha256:"),
            modified_at=NOW,
        ),
        parser=ParserDescriptor(
            name=selected.name,
            version=selected.version,
            profile=selected.profile,
            config_hash=selected.config_hash,
        ),
        schema_versions=SchemaVersions(
            block="0.1.0",
            derivation="0.1.0",
            relation="0.1.0",
        ),
    )
    return ReadyRepresentationCommit(
        scope=scope,
        recipe=selected,
        manifest=manifest,
        manifest_object=_stored_json(manifest),
        native_object=StoredObject(object_id=version_id, byte_length=8),
        blocks=(
            PreparedRepresentationBlock(
                block=block,
                object=_stored_json(block),
                ordinal=0,
                line_start=1,
                line_end=1,
            ),
        ),
        warning_codes=(),
        source_observed_at=observed_at,
        ready_at=ready_at,
    )


def _catalog(path: Path) -> SQLiteCatalog:
    catalog = SQLiteCatalog(path)
    assert catalog.initialize(now=NOW) == 6
    catalog.register_document(
        SourceKey(connector="local", locator="/synthetic/source.txt"),
        document_id=DOCUMENT_ID,
        now=NOW,
    )
    _add_version(catalog, VERSION_A)
    return catalog


def _add_version(catalog: SQLiteCatalog, version_id: str) -> None:
    catalog.commit_source_version(
        SourceVersionCommit(
            document_id=DOCUMENT_ID,
            version_id=version_id,
            source=StoredObject(object_id=version_id, byte_length=8),
            media_type="text/plain",
            committed_at=NOW,
        )
    )


def _claim(
    catalog: SQLiteCatalog,
    scope: RepresentationScope,
    *,
    token: str = TOKEN_A,
    now: datetime = NOW,
):
    return catalog.acquire_representation(
        scope,
        _recipe(),
        owner_id="worker-a",
        lease_token=token,
        now=now,
        lease_until=now + timedelta(minutes=5),
    )


def test_migration_three_upgrades_real_prior_catalogs_and_has_exact_tables(tmp_path: Path) -> None:
    """Append migrations 3-4 without changing the released first two migrations."""
    path = tmp_path / "catalog.sqlite3"
    prior_checksums = (MIGRATION_1.checksum, MIGRATION_2.checksum)
    old = SQLiteCatalog(path, migrations=(MIGRATION_1, MIGRATION_2))
    assert old.initialize(now=NOW) == 2

    current = SQLiteCatalog(path)
    assert current.initialize(now=NOW + timedelta(seconds=1)) == 6
    assert current.initialize(now=NOW + timedelta(seconds=2)) == 6
    assert (MIGRATION_1.checksum, MIGRATION_2.checksum) == prior_checksums
    with sqlite3.connect(path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert {
        "document_representations",
        "representation_blocks",
        "document_heads",
        "ingestion_events",
        "block_search_entries",
        "block_search_index",
        "block_search_index_config",
        "block_search_index_data",
        "block_search_index_docsize",
        "block_search_index_idx",
    }.issubset(tables)


def test_claim_busy_same_token_renew_fail_and_expired_takeover(tmp_path: Path) -> None:
    """Fence exactly one active owner and make failed/expired work retryable."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    scope = _scope()
    claimed = _claim(catalog, scope)
    assert claimed.disposition is RepresentationAcquireDisposition.CLAIMED
    assert _claim(catalog, scope).lease == claimed.lease

    busy = catalog.acquire_representation(
        scope,
        _recipe(),
        owner_id="worker-b",
        lease_token=TOKEN_B,
        now=NOW + timedelta(seconds=1),
        lease_until=NOW + timedelta(minutes=6),
    )
    assert busy.disposition is RepresentationAcquireDisposition.BUSY

    renewed = catalog.renew_representation(
        scope,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=1,
        now=NOW + timedelta(seconds=1),
        lease_until=NOW + timedelta(minutes=6),
    )
    assert renewed.representation.revision == 2
    failed = catalog.fail_representation(
        scope,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=2,
        now=NOW + timedelta(seconds=2),
        failure_code="parser_failed",
    )
    assert failed.representation.state is RepresentationState.FAILED
    retry = catalog.acquire_representation(
        scope,
        _recipe(),
        owner_id="worker-b",
        lease_token=TOKEN_B,
        now=NOW + timedelta(seconds=3),
        lease_until=NOW + timedelta(minutes=7),
    )
    assert retry.representation.attempt_count == 2

    with pytest.raises(RepresentationLeaseConflict):
        catalog.fail_representation(
            scope,
            owner_id="worker-a",
            lease_token=TOKEN_A,
            expected_revision=2,
            now=NOW + timedelta(seconds=4),
            failure_code="parser_failed",
        )


def test_ready_commit_is_atomic_idempotent_and_queryable(tmp_path: Path) -> None:
    """Publish complete immutable representation evidence through one transaction."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    commit = _ready_commit()
    claim = _claim(catalog, commit.scope)
    assert claim.lease is not None

    result = catalog.commit_ready_representation(
        commit,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=claim.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    replay = catalog.commit_ready_representation(
        commit,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=claim.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )

    assert replay == result
    assert result.aggregate.representation.state is RepresentationState.READY
    assert result.aggregate.blocks[0].block_id == commit.blocks[0].block.block_id
    assert catalog.load_representation(commit.scope) == result.aggregate
    assert catalog.get_document_head(DOCUMENT_ID) == result.head
    assert catalog.list_ingestion_events(DOCUMENT_ID) == (result.event,)
    assert catalog.list_document_summaries()[0].block_count == 1
    roots = catalog.reference_snapshot(observed_at=NOW).object_ids
    assert commit.manifest_object.object_id in roots
    assert commit.blocks[0].object.object_id in roots


def test_verified_ready_reuse_records_cache_event_without_mutating_representation(
    tmp_path: Path,
) -> None:
    """Append cache evidence and advance observation time without parsing state drift."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    commit = _ready_commit()
    claim = _claim(catalog, commit.scope)
    catalog.commit_ready_representation(
        commit,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=claim.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    before = catalog.load_representation(commit.scope)
    update = catalog.record_ready_ingest(
        commit.scope,
        source_observed_at=NOW + timedelta(minutes=1),
        ingested_at=NOW + timedelta(minutes=1, seconds=1),
        disposition=IngestionDisposition.CACHE_HIT,
    )

    assert update.event.parser_invoked is False
    assert update.event.head_advanced is True
    assert catalog.load_representation(commit.scope) == before
    assert [event.disposition for event in catalog.list_ingestion_events(DOCUMENT_ID)] == [
        IngestionDisposition.COMMITTED,
        IngestionDisposition.CACHE_HIT,
    ]


@pytest.mark.parametrize(
    "failure_point",
    [
        "after_representation_objects",
        "after_representation_block",
        "after_representation_ready",
        "after_document_head",
        "after_ingestion_event",
        "before_representation_commit",
    ],
)
def test_ready_fault_points_leave_no_partial_visible_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    """Roll back objects, blocks, READY, head and event from every injected boundary."""
    path = tmp_path / "catalog.sqlite3"
    catalog = _catalog(path)
    commit = _ready_commit()
    claim = _claim(catalog, commit.scope)

    def fail(point: str) -> None:
        if point == failure_point:
            raise RuntimeError("synthetic representation interruption")

    monkeypatch.setattr(catalog, "_fault_point", fail)
    with pytest.raises(RuntimeError, match="synthetic representation interruption"):
        catalog.commit_ready_representation(
            commit,
            owner_id="worker-a",
            lease_token=TOKEN_A,
            expected_revision=claim.representation.revision,
            disposition=IngestionDisposition.COMMITTED,
        )

    independent = SQLiteCatalog(path)
    aggregate = independent.load_representation(commit.scope)
    assert aggregate is not None
    assert aggregate.representation.state is RepresentationState.STAGING
    assert aggregate.blocks == ()
    assert independent.get_document_head(DOCUMENT_ID) is None
    assert independent.list_ingestion_events(DOCUMENT_ID) == ()


def test_head_tracks_a_to_b_to_a_by_observation_not_first_commit_time(tmp_path: Path) -> None:
    """Advance to reused historical A after B without rewriting either representation."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    _add_version(catalog, VERSION_B)
    commit_a = _ready_commit(observed_at=NOW, ready_at=NOW + timedelta(seconds=1))
    claim_a = _claim(catalog, commit_a.scope)
    catalog.commit_ready_representation(
        commit_a,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=claim_a.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    commit_b = _ready_commit(
        VERSION_B,
        observed_at=NOW + timedelta(minutes=1),
        ready_at=NOW + timedelta(minutes=1, seconds=1),
    )
    claim_b = _claim(catalog, commit_b.scope, token=TOKEN_B, now=NOW + timedelta(minutes=1))
    catalog.commit_ready_representation(
        commit_b,
        owner_id="worker-a",
        lease_token=TOKEN_B,
        expected_revision=claim_b.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    catalog.record_ready_ingest(
        commit_a.scope,
        source_observed_at=NOW + timedelta(minutes=2),
        ingested_at=NOW + timedelta(minutes=2, seconds=1),
        disposition=IngestionDisposition.CACHE_HIT,
    )
    assert catalog.get_document_head(DOCUMENT_ID).scope == commit_a.scope  # type: ignore[union-attr]


def test_forced_equal_output_is_recorded_and_divergent_output_conflicts(tmp_path: Path) -> None:
    """Accept exact forced output as evidence but never overwrite READY facts."""
    catalog = _catalog(tmp_path / "catalog.sqlite3")
    commit = _ready_commit()
    claim = _claim(catalog, commit.scope)
    catalog.commit_ready_representation(
        commit,
        owner_id="worker-a",
        lease_token=TOKEN_A,
        expected_revision=claim.representation.revision,
        disposition=IngestionDisposition.COMMITTED,
    )
    converged = commit.model_copy(
        update={
            "source_observed_at": NOW + timedelta(minutes=1),
            "ready_at": NOW + timedelta(minutes=1, seconds=1),
        }
    )
    result = catalog.commit_ready_representation(
        converged,
        owner_id=None,
        lease_token=None,
        expected_revision=None,
        disposition=IngestionDisposition.FORCED_REPARSE,
    )
    assert result.event.disposition is IngestionDisposition.FORCED_REPARSE

    divergent = converged.model_copy(update={"warning_codes": ("different",)})
    with pytest.raises(RepresentationConflict, match="differs"):
        catalog.commit_ready_representation(
            divergent,
            owner_id=None,
            lease_token=None,
            expected_revision=None,
            disposition=IngestionDisposition.FORCED_REPARSE,
        )
