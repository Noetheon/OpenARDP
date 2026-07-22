"""Pure F004 ingestion, representation and navigation invariants."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import SecretStr, ValidationError

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
from openardp.domain.identity import block_content_hash, canonical_json_bytes, representation_id
from openardp.domain.ingestion import (
    MAX_NORMALIZED_BLOCKS,
    DocumentHead,
    DocumentRepresentation,
    IngestionDisposition,
    IngestionEvent,
    IngestionResult,
    OutlineItem,
    ParsedBlock,
    ParsedTextDocument,
    ParserRecipe,
    PreparedRepresentationBlock,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationAcquireResult,
    RepresentationLease,
    RepresentationScope,
    RepresentationState,
    SourceFreshness,
    SourceStatus,
    TextMediaType,
    deterministic_block_id,
)
from openardp.domain.manifest import (
    DocumentManifest,
    ManifestState,
    SchemaVersions,
    SourceDescriptor,
)
from openardp.domain.storage import StoredObject

DOCUMENT_ID = UUID("01890f62-24e8-7c00-8000-000000000001")
VERSION_ID = "sha256:" + "1" * 64
CONFIG_HASH = "sha256:" + "2" * 64
NOW = datetime(2026, 7, 22, 17, 0, tzinfo=UTC)


def _recipe() -> ParserRecipe:
    return ParserRecipe(
        name="openardp-text",
        version="1",
        profile="default",
        config_hash=CONFIG_HASH,
        normalization_schema_version="0.1.0",
    )


def _scope() -> RepresentationScope:
    recipe = _recipe()
    return RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=VERSION_ID,
        representation_id=representation_id(
            version_id=VERSION_ID,
            parser_name=recipe.name,
            parser_version=recipe.version,
            parser_profile=recipe.profile,
            parser_config_hash=recipe.config_hash,
            normalization_schema_version=recipe.normalization_schema_version,
        ),
    )


def _stored_json(model: ContentBlock | DocumentManifest) -> StoredObject:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def _block(
    *,
    text: str = "Evidence",
    line_start: int = 1,
    line_end: int = 1,
    order: int = 0,
    parent_id: UUID | None = None,
    structural_path: tuple[str, ...] = ("root", "paragraph:0"),
    occurrence: int = 0,
) -> ContentBlock:
    scope = _scope()
    canonical_hash = block_content_hash(
        kind=BlockKind.PARAGRAPH.value,
        text=text,
        structured=None,
        asset_id=None,
    )
    return ContentBlock(
        schema_version="0.1.0",
        block_id=deterministic_block_id(
            document_id=DOCUMENT_ID,
            structural_path=structural_path,
            kind=BlockKind.PARAGRAPH,
            canonical_hash=canonical_hash,
            line_start=line_start,
            line_end=line_end,
            occurrence=occurrence,
        ),
        document_id=DOCUMENT_ID,
        version_id=VERSION_ID,
        representation_id=scope.representation_id,
        parent_id=parent_id,
        kind=BlockKind.PARAGRAPH,
        order=order,
        text=text,
        canonical_hash=canonical_hash,
        source=SourceLocator(
            extraction_method="openardp-text-v1",
            extensions={"openardp.text": {"line_start": line_start, "line_end": line_end}},
        ),
        trust=DataTrustClassification(
            zone=TrustZone.EXTERNAL_UNTRUSTED,
            role=ContentRole.DATA,
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.UNKNOWN,
        ),
    )


def _manifest(*, block_count: int = 1) -> DocumentManifest:
    del block_count
    scope = _scope()
    recipe = _recipe()
    return DocumentManifest(
        spec_version="0.1.0",
        document_id=DOCUMENT_ID,
        version_id=VERSION_ID,
        representation_id=scope.representation_id,
        title="source.md",
        state=ManifestState.READY,
        created_at=NOW,
        source=SourceDescriptor(
            connector="local",
            locator="/synthetic/source.md",
            media_type=TextMediaType.MARKDOWN.value,
            byte_length=8,
            sha256="1" * 64,
            modified_at=NOW,
        ),
        parser=ParserDescriptor(
            name=recipe.name,
            version=recipe.version,
            profile=recipe.profile,
            config_hash=recipe.config_hash,
        ),
        schema_versions=SchemaVersions(
            block="0.1.0",
            derivation="0.1.0",
            relation="0.1.0",
        ),
    )


def _ready_commit(*, blocks: tuple[PreparedRepresentationBlock, ...] | None = None):
    selected = blocks
    if selected is None:
        block = _block()
        selected = (
            PreparedRepresentationBlock(
                block=block,
                object=_stored_json(block),
                ordinal=0,
                line_start=1,
                line_end=1,
            ),
        )
    manifest = _manifest(block_count=len(selected))
    return ReadyRepresentationCommit(
        scope=_scope(),
        recipe=_recipe(),
        manifest=manifest,
        manifest_object=_stored_json(manifest),
        native_object=StoredObject(object_id=VERSION_ID, byte_length=8),
        blocks=selected,
        warning_codes=(),
        source_observed_at=NOW,
        ready_at=NOW,
    )


def test_parser_recipe_derives_the_existing_representation_identity() -> None:
    """Keep recipe projection owned by the accepted ADR-0006 helper."""
    recipe = _recipe()
    assert recipe.representation_id_for(VERSION_ID) == _scope().representation_id


@pytest.mark.parametrize("field", ("name", "version", "profile"))
def test_parser_recipe_rejects_empty_identity_fields(field: str) -> None:
    """Prevent ambiguous parser recipe identities."""
    values = _recipe().model_dump()
    values[field] = ""
    with pytest.raises(ValidationError):
        ParserRecipe.model_validate(values)


def test_deterministic_block_id_has_fixed_sha256_uuid8_vector() -> None:
    """Freeze the documented version-1 block-handle algorithm."""
    block_id = deterministic_block_id(
        document_id=DOCUMENT_ID,
        structural_path=("root", "paragraph:0"),
        kind=BlockKind.PARAGRAPH,
        canonical_hash="sha256:" + "1" * 64,
        line_start=1,
        line_end=2,
        occurrence=0,
    )
    assert str(block_id) == "efe2cf3a-3c22-8c00-adcc-237de0936768"
    assert block_id.version == 8
    assert block_id.variant == "specified in RFC 4122"


def test_block_id_preserves_unicode_code_point_distinctions() -> None:
    """Do not normalize structurally distinct Unicode paths."""
    common = {
        "document_id": DOCUMENT_ID,
        "kind": BlockKind.PARAGRAPH,
        "canonical_hash": "sha256:" + "1" * 64,
        "line_start": 1,
        "line_end": 1,
        "occurrence": 0,
    }
    assert deterministic_block_id(structural_path=("é",), **common) != deterministic_block_id(
        structural_path=("e\u0301",), **common
    )


def test_parsed_document_validates_parent_and_sibling_order() -> None:
    """Accept only one deterministic reading-order hierarchy."""
    document = ParsedTextDocument(
        media_type=TextMediaType.MARKDOWN,
        blocks=(
            ParsedBlock(
                kind=BlockKind.HEADING,
                text="Title",
                parent_index=None,
                order=0,
                line_start=1,
                line_end=1,
                structural_path=("heading:0",),
            ),
            ParsedBlock(
                kind=BlockKind.PARAGRAPH,
                text="Body",
                parent_index=0,
                order=0,
                line_start=2,
                line_end=2,
                structural_path=("heading:0", "paragraph:0"),
            ),
        ),
        warnings=(),
        bom_present=False,
    )
    assert len(document.blocks) == 2

    invalid = document.model_dump()
    invalid["blocks"][1]["parent_index"] = 1
    with pytest.raises(ValidationError, match="parent"):
        ParsedTextDocument.model_validate(invalid)


def test_parsed_document_requires_sorted_unique_warning_codes() -> None:
    """Keep persisted parser warnings deterministic and body-free."""
    with pytest.raises(ValidationError, match="warnings"):
        ParsedTextDocument(
            media_type=TextMediaType.PLAIN,
            blocks=(),
            warnings=("z_warning", "a_warning"),
            bom_present=False,
        )


def test_parsed_document_enforces_block_limit() -> None:
    """Reject hostile aggregate sizes at the pure boundary."""
    block = ParsedBlock(
        kind=BlockKind.PARAGRAPH,
        text="x",
        parent_index=None,
        order=0,
        line_start=1,
        line_end=1,
        structural_path=("paragraph:0",),
    )
    with pytest.raises(ValidationError, match="block limit"):
        ParsedTextDocument(
            media_type=TextMediaType.PLAIN,
            blocks=(block,) * (MAX_NORMALIZED_BLOCKS + 1),
            warnings=(),
            bom_present=False,
        )


@pytest.mark.parametrize(
    ("state", "changes"),
    (
        (RepresentationState.STAGING, {}),
        (RepresentationState.READY, {"active_owner_id": None, "lease_expires_at": None}),
        (
            RepresentationState.FAILED,
            {
                "active_owner_id": None,
                "lease_expires_at": None,
                "last_failure_code": "parser_failed",
            },
        ),
    ),
)
def test_representation_lifecycle_shapes_are_explicit(
    state: RepresentationState, changes: dict[str, object]
) -> None:
    """Keep staging, failed and ready projections mutually exclusive."""
    values: dict[str, object] = {
        "scope": _scope(),
        "recipe": _recipe(),
        "state": state,
        "attempt_count": 1,
        "revision": 1,
        "active_owner_id": "worker-1",
        "lease_expires_at": NOW + timedelta(minutes=5),
        "last_failure_code": None,
        "manifest_object": None,
        "native_object": None,
        "block_count": 0,
        "warning_codes": (),
        "created_at": NOW,
        "updated_at": NOW,
        "ready_at": None,
    }
    values.update(changes)
    if state is RepresentationState.READY:
        commit = _ready_commit()
        values.update(
            manifest_object=commit.manifest_object,
            native_object=commit.native_object,
            block_count=1,
            ready_at=NOW,
        )
    projection = DocumentRepresentation(**values)
    assert projection.state is state


def test_representation_lease_masks_and_requires_strong_token() -> None:
    """Never expose a raw representation fencing capability."""
    representation = DocumentRepresentation(
        scope=_scope(),
        recipe=_recipe(),
        state=RepresentationState.STAGING,
        attempt_count=1,
        revision=1,
        active_owner_id="worker-1",
        lease_expires_at=NOW + timedelta(minutes=5),
        block_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    lease = RepresentationLease(
        representation=representation,
        lease_token=SecretStr("strong-token-value"),
    )
    assert "strong-token-value" not in repr(lease)
    with pytest.raises(ValidationError, match="at least 16"):
        RepresentationLease(representation=representation, lease_token=SecretStr("short"))


def test_acquire_result_shape_matches_disposition() -> None:
    """Expose an unambiguous claimed, ready or busy acquisition outcome."""
    representation = DocumentRepresentation(
        scope=_scope(),
        recipe=_recipe(),
        state=RepresentationState.STAGING,
        attempt_count=1,
        revision=1,
        active_owner_id="worker-1",
        lease_expires_at=NOW + timedelta(minutes=5),
        block_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    lease = RepresentationLease(
        representation=representation,
        lease_token=SecretStr("strong-token-value"),
    )
    claimed = RepresentationAcquireResult(
        disposition=RepresentationAcquireDisposition.CLAIMED,
        representation=representation,
        lease=lease,
    )
    assert claimed.lease == lease
    with pytest.raises(ValidationError, match="lease"):
        RepresentationAcquireResult(
            disposition=RepresentationAcquireDisposition.BUSY,
            representation=representation,
            lease=lease,
        )


def test_prepared_representation_block_requires_exact_line_extension_and_object() -> None:
    """Cross-check SQLite projection fields against exact serialized F002 evidence."""
    block = _block()
    record = PreparedRepresentationBlock(
        block=block,
        object=_stored_json(block),
        ordinal=0,
        line_start=1,
        line_end=1,
    )
    assert record.block.block_id == block.block_id
    with pytest.raises(ValidationError, match="line provenance"):
        PreparedRepresentationBlock(
            block=block,
            object=_stored_json(block),
            ordinal=0,
            line_start=2,
            line_end=2,
        )


def test_ready_commit_validates_complete_manifest_and_blocks() -> None:
    """Accept one complete scope-consistent ready aggregate."""
    commit = _ready_commit()
    assert commit.manifest.state is ManifestState.READY
    assert commit.blocks[0].block.representation_id == commit.scope.representation_id


def test_ready_commit_rejects_noncontiguous_ordinals_and_missing_parent() -> None:
    """Prevent partial or cross-aggregate hierarchy from reaching SQLite."""
    first = _block(structural_path=("root", "paragraph:0"))
    second = _block(
        text="Second",
        line_start=2,
        line_end=2,
        parent_id=UUID("12345678-1234-4234-9234-123456789abc"),
        structural_path=("root", "paragraph:1"),
    )
    records = (
        PreparedRepresentationBlock(
            block=first,
            object=_stored_json(first),
            ordinal=0,
            line_start=1,
            line_end=1,
        ),
        PreparedRepresentationBlock(
            block=second,
            object=_stored_json(second),
            ordinal=2,
            line_start=2,
            line_end=2,
        ),
    )
    with pytest.raises(ValidationError, match=r"ordinals|parent"):
        _ready_commit(blocks=records)


def test_document_head_and_event_enforce_time_and_cache_semantics() -> None:
    """Keep the mutable head monotonic and cache evidence truthful."""
    head = DocumentHead(
        scope=_scope(),
        source_observed_at=NOW,
        last_ingested_at=NOW,
        last_disposition=IngestionDisposition.CACHE_HIT,
        revision=1,
    )
    event = IngestionEvent(
        document_id=DOCUMENT_ID,
        sequence=1,
        scope=_scope(),
        disposition=IngestionDisposition.CACHE_HIT,
        parser_invoked=False,
        head_advanced=True,
        occurred_at=NOW,
        source_observed_at=NOW,
    )
    assert head.scope == event.scope
    with pytest.raises(ValidationError, match="parser"):
        IngestionEvent(
            document_id=DOCUMENT_ID,
            sequence=1,
            scope=_scope(),
            disposition=IngestionDisposition.CACHE_HIT,
            parser_invoked=True,
            head_advanced=True,
            occurred_at=NOW,
            source_observed_at=NOW,
        )


def test_ingestion_result_keeps_body_out_and_cache_flags_consistent() -> None:
    """Expose bounded machine output without source text."""
    result = IngestionResult(
        scope=_scope(),
        disposition=IngestionDisposition.CACHE_HIT,
        parser_invoked=False,
        cache_hit=True,
        head_advanced=True,
        block_count=1,
        warning_codes=(),
        ingested_at=NOW,
    )
    assert "Evidence" not in result.model_dump_json()
    with pytest.raises(ValidationError, match="cache"):
        IngestionResult(
            scope=result.scope,
            disposition=result.disposition,
            parser_invoked=result.parser_invoked,
            cache_hit=False,
            head_advanced=result.head_advanced,
            block_count=result.block_count,
            warning_codes=result.warning_codes,
            ingested_at=result.ingested_at,
        )


def test_status_and_outline_are_body_minimizing() -> None:
    """Keep progressive navigation contracts free of paragraph bodies."""
    status = SourceStatus(
        freshness=SourceFreshness.CURRENT,
        document_id=DOCUMENT_ID,
        head=_scope(),
        observed_version_id=VERSION_ID,
        checked_at=NOW,
    )
    outline = OutlineItem(
        block_id=UUID("efe2cf3a-3c22-8c00-adcc-237de0936768"),
        kind=BlockKind.HEADING,
        parent_id=None,
        order=0,
        depth=0,
        label="Title",
        line_start=1,
        line_end=1,
    )
    assert status.freshness is SourceFreshness.CURRENT
    assert not hasattr(outline, "text")
