"""Parse-once orchestration for local immutable text representations."""

from __future__ import annotations

import hashlib
import os
import secrets
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from openardp.domain.block import BlockKind, ContentBlock
from openardp.domain.common import (
    ContentRole,
    DataTrustClassification,
    IntegrityState,
    ParserDescriptor,
    Sensitivity,
    SourceLocator,
    TrustZone,
    validate_json,
)
from openardp.domain.identity import block_content_hash, canonical_json_bytes
from openardp.domain.ingestion import (
    DocumentRepresentation,
    IngestionDisposition,
    IngestionResult,
    ParsedTextDocument,
    PreparedRepresentationBlock,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationAggregate,
    RepresentationBlock,
    RepresentationScope,
    SourceSnapshot,
    deterministic_block_id,
)
from openardp.domain.manifest import (
    DocumentManifest,
    ManifestState,
    SchemaVersions,
    SourceDescriptor,
)
from openardp.domain.storage import (
    DocumentVersion,
    LogicalDocument,
    SourceVersionCommit,
    StoredObject,
    generate_uuid7,
)
from openardp.ports.catalog import (
    Catalog,
    DocumentConflict,
    RepresentationBusy,
    RepresentationIntegrityError,
)
from openardp.ports.object_store import (
    CompactBlockStore,
    ObjectStore,
    ObjectStoreError,
    OrdinaryAuthorityStore,
)
from openardp.ports.parser import ParserAdapter, ParserError

_REPRESENTATION_LEASE = timedelta(minutes=5)


class _SourceBoundary(Protocol):
    """Narrow source snapshot shape injected by the outer composition root."""

    def snapshot_to(
        self,
        object_store: ObjectStore,
        *,
        observed_at: datetime,
    ) -> SourceSnapshot:
        """Publish one stable exact source snapshot."""
        ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _owner_id() -> str:
    return f"openardp-{os.getpid()}"


def _lease_token() -> str:
    return secrets.token_hex(32)


def _random_uuid7_bits() -> int:
    return secrets.randbits(74)


class IngestionService:
    """Coordinate source snapshot, cache verification, parsing and atomic commit."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: Catalog,
        parser: ParserAdapter,
        *,
        source_factory: Callable[[Path], _SourceBoundary],
        clock: Callable[[], datetime] = _utc_now,
        owner_id_factory: Callable[[], str] = _owner_id,
        lease_token_factory: Callable[[], str] = _lease_token,
        random_bits: Callable[[], int] = _random_uuid7_bits,
    ) -> None:
        """Bind provider ports and injectable nondeterminism sources."""
        self._object_store = object_store
        self._catalog = catalog
        self._parser = parser
        self._source_factory = source_factory
        self._clock = clock
        self._owner_id_factory = owner_id_factory
        self._lease_token_factory = lease_token_factory
        self._random_bits = random_bits

    def ingest(
        self,
        source: Path,
        *,
        profile: str = "default",
        force: bool = False,
    ) -> IngestionResult:
        """Ingest or verified-reuse one exact local source and parser recipe."""
        if profile != self._parser.recipe.profile:
            raise ValueError("unsupported parser profile")
        observed_at = self._clock()
        snapshot = self._source_factory(source).snapshot_to(
            self._object_store,
            observed_at=observed_at,
        )
        document = self._catalog.get_document_by_source(snapshot.source_key)
        if document is None:
            document = self._register_document(snapshot, now=observed_at)
        version = self._catalog.get_version(document.document_id, snapshot.object.object_id)
        if version is None:
            version = self._catalog.commit_source_version(
                SourceVersionCommit(
                    document_id=document.document_id,
                    version_id=snapshot.object.object_id,
                    source=snapshot.object,
                    media_type=snapshot.media_type.value,
                    source_modified_at=snapshot.modified_at,
                    committed_at=observed_at,
                )
            )
        elif version.source != snapshot.object or version.media_type != snapshot.media_type.value:
            raise RepresentationIntegrityError("source version metadata is inconsistent")
        self._retain_ordinary_authority(version.source)

        scope = RepresentationScope(
            document_id=document.document_id,
            version_id=version.version_id,
            representation_id=self._parser.recipe.representation_id_for(version.version_id),
        )
        owner_id = self._owner_id_factory()
        lease_token = self._lease_token_factory()
        acquired = self._catalog.acquire_representation(
            scope,
            self._parser.recipe,
            owner_id=owner_id,
            lease_token=lease_token,
            now=observed_at,
            lease_until=observed_at + _REPRESENTATION_LEASE,
        )
        if acquired.disposition is RepresentationAcquireDisposition.BUSY:
            raise RepresentationBusy("representation is busy")
        if acquired.disposition is RepresentationAcquireDisposition.READY:
            aggregate = self._catalog.load_representation(scope)
            if aggregate is None:
                raise RepresentationIntegrityError("ready representation is missing")
            self.verify_ready_representation(aggregate)
            if not force:
                ingested_at = self._clock()
                update = self._catalog.record_ready_ingest(
                    scope,
                    source_observed_at=observed_at,
                    ingested_at=ingested_at,
                    disposition=IngestionDisposition.CACHE_HIT,
                )
                return self._result(
                    aggregate.representation,
                    disposition=IngestionDisposition.CACHE_HIT,
                    parser_invoked=False,
                    head_advanced=update.event.head_advanced,
                    ingested_at=ingested_at,
                )

        claimed = acquired.disposition is RepresentationAcquireDisposition.CLAIMED
        try:
            parsed = self._parser.parse(
                self._object_store.iter_chunks(version.version_id),
                media_type=version.media_type,
            )
            ready_at = self._clock()
            commit = self._prepare_commit(
                snapshot=snapshot,
                version=version,
                scope=scope,
                parsed=parsed,
                ready_at=ready_at,
            )
            result = self._catalog.commit_ready_representation(
                commit,
                owner_id=owner_id if claimed else None,
                lease_token=lease_token if claimed else None,
                expected_revision=acquired.representation.revision if claimed else None,
                disposition=(
                    IngestionDisposition.FORCED_REPARSE if force else IngestionDisposition.COMMITTED
                ),
            )
        except Exception as error:
            if claimed:
                self._record_failed_attempt(
                    scope,
                    owner_id=owner_id,
                    lease_token=lease_token,
                    expected_revision=acquired.representation.revision,
                    error=error,
                )
            raise
        self.verify_ready_representation(result.aggregate)
        return self._result(
            result.aggregate.representation,
            disposition=result.event.disposition,
            parser_invoked=True,
            head_advanced=result.event.head_advanced,
            ingested_at=result.event.occurred_at,
        )

    def verify_ready_representation(self, aggregate: RepresentationAggregate) -> None:
        """Physically and semantically verify every required READY artifact."""
        representation = aggregate.representation
        if representation.manifest_object is None or representation.native_object is None:
            raise RepresentationIntegrityError("ready representation artifacts are incomplete")
        try:
            self._object_store.verify(
                representation.native_object.object_id,
                expected_length=representation.native_object.byte_length,
            )
            manifest_payload = self._read_object(representation.manifest_object)
            manifest = validate_json(DocumentManifest, manifest_payload)
            self._assert_canonical_payload(manifest_payload, manifest)
            self._verify_manifest(manifest, representation)
            self._verify_blocks(aggregate.blocks, representation)
        except RepresentationIntegrityError:
            raise
        except (ObjectStoreError, ValidationError, ValueError) as error:
            raise RepresentationIntegrityError("ready representation integrity failed") from error

    def _register_document(
        self,
        snapshot: SourceSnapshot,
        *,
        now: datetime,
    ) -> LogicalDocument:
        for _attempt in range(8):
            try:
                return self._catalog.register_document(
                    snapshot.source_key,
                    document_id=generate_uuid7(now=now, random_bits=self._random_bits()),
                    now=now,
                )
            except DocumentConflict:
                existing = self._catalog.get_document_by_source(snapshot.source_key)
                if existing is not None:
                    return existing
        raise DocumentConflict("document UUID generation repeatedly collided")

    def _prepare_commit(
        self,
        *,
        snapshot: SourceSnapshot,
        version: DocumentVersion,
        scope: RepresentationScope,
        parsed: ParsedTextDocument,
        ready_at: datetime,
    ) -> ReadyRepresentationCommit:
        prepared: list[PreparedRepresentationBlock] = []
        identifiers: list[UUID] = []
        occurrences: defaultdict[tuple[UUID | None, tuple[str, ...], BlockKind, str, int, int], int]
        occurrences = defaultdict(int)
        for ordinal, candidate in enumerate(parsed.blocks):
            parent_id = (
                identifiers[candidate.parent_index] if candidate.parent_index is not None else None
            )
            canonical_hash = block_content_hash(
                kind=candidate.kind.value,
                text=candidate.text,
                structured=None,
                asset_id=None,
            )
            occurrence_key = (
                parent_id,
                candidate.structural_path,
                candidate.kind,
                canonical_hash,
                candidate.line_start,
                candidate.line_end,
            )
            occurrence = occurrences[occurrence_key]
            occurrences[occurrence_key] += 1
            block_id = deterministic_block_id(
                document_id=scope.document_id,
                structural_path=candidate.structural_path,
                kind=candidate.kind,
                canonical_hash=canonical_hash,
                line_start=candidate.line_start,
                line_end=candidate.line_end,
                occurrence=occurrence,
            )
            block = ContentBlock(
                schema_version="0.1.0",
                block_id=block_id,
                document_id=scope.document_id,
                version_id=scope.version_id,
                representation_id=scope.representation_id,
                parent_id=parent_id,
                kind=candidate.kind,
                order=candidate.order,
                text=candidate.text,
                canonical_hash=canonical_hash,
                source=SourceLocator(
                    extraction_method="openardp-text-v1",
                    extensions={
                        "openardp.text": {
                            "line_start": candidate.line_start,
                            "line_end": candidate.line_end,
                        }
                    },
                ),
                trust=DataTrustClassification(
                    zone=TrustZone.EXTERNAL_UNTRUSTED,
                    role=ContentRole.DATA,
                    instruction_execution_allowed=False,
                    integrity=IntegrityState.VERIFIED_SHA256,
                    sensitivity=Sensitivity.UNKNOWN,
                ),
            )
            identifiers.append(block_id)
            prepared.append(
                PreparedRepresentationBlock(
                    block=block,
                    object=self._put_canonical_model(block),
                    ordinal=ordinal,
                    line_start=candidate.line_start,
                    line_end=candidate.line_end,
                )
            )

        manifest = DocumentManifest(
            spec_version="0.1.0",
            document_id=scope.document_id,
            version_id=scope.version_id,
            representation_id=scope.representation_id,
            title=Path(snapshot.source_key.locator).name,
            state=ManifestState.READY,
            created_at=version.committed_at,
            source=SourceDescriptor(
                connector=snapshot.source_key.connector,
                locator=snapshot.source_key.locator,
                media_type=version.media_type,
                byte_length=version.source.byte_length,
                sha256=version.version_id.removeprefix("sha256:"),
                modified_at=version.source_modified_at,
            ),
            parser=ParserDescriptor(
                name=self._parser.recipe.name,
                version=self._parser.recipe.version,
                profile=self._parser.recipe.profile,
                config_hash=self._parser.recipe.config_hash,
            ),
            schema_versions=SchemaVersions(
                block=self._parser.recipe.normalization_schema_version,
                derivation="0.1.0",
                relation="0.1.0",
            ),
        )
        return ReadyRepresentationCommit(
            scope=scope,
            recipe=self._parser.recipe,
            manifest=manifest,
            manifest_object=self._put_canonical_model(manifest),
            native_object=snapshot.object,
            blocks=tuple(prepared),
            warning_codes=parsed.warnings,
            source_observed_at=snapshot.observed_at,
            ready_at=ready_at,
        )

    def _put_canonical_model(self, model: ContentBlock | DocumentManifest) -> StoredObject:
        payload = canonical_json_bytes(model.model_dump(mode="json"))
        expected = StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )
        if isinstance(model, ContentBlock) and isinstance(self._object_store, CompactBlockStore):
            stored = self._object_store.put_canonical_block(payload)
        else:
            stored = self._object_store.put_chunks((payload,))
        if stored != expected:
            raise RepresentationIntegrityError("canonical object publication is inconsistent")
        return self._object_store.verify(
            stored.object_id,
            expected_length=stored.byte_length,
        )

    def _read_object(self, stored: StoredObject) -> bytes:
        verified = self._object_store.verify(
            stored.object_id,
            expected_length=stored.byte_length,
        )
        payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        if len(payload) != verified.byte_length:
            raise RepresentationIntegrityError("object length changed during read")
        return payload

    def _retain_ordinary_authority(self, stored: StoredObject) -> None:
        """Converge a catalog-authoritative source only when the store supports it."""
        if isinstance(self._object_store, OrdinaryAuthorityStore):
            retained = self._object_store.retain_ordinary_authority(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            if retained != stored:
                raise RepresentationIntegrityError("ordinary source authority is inconsistent")

    @staticmethod
    def _assert_canonical_payload(
        payload: bytes,
        model: ContentBlock | DocumentManifest,
    ) -> None:
        if payload != canonical_json_bytes(model.model_dump(mode="json")):
            raise RepresentationIntegrityError("canonical record bytes are non-canonical")

    def _verify_manifest(
        self,
        manifest: DocumentManifest,
        representation: DocumentRepresentation,
    ) -> None:
        scope = representation.scope
        recipe = representation.recipe
        native = representation.native_object
        if native is None:
            raise RepresentationIntegrityError("ready representation native object is missing")
        if (
            manifest.document_id != scope.document_id
            or manifest.version_id != scope.version_id
            or manifest.representation_id != scope.representation_id
            or manifest.state is not ManifestState.READY
            or manifest.parser.name != recipe.name
            or manifest.parser.version != recipe.version
            or manifest.parser.profile != recipe.profile
            or manifest.parser.config_hash != recipe.config_hash
            or manifest.schema_versions.block != recipe.normalization_schema_version
            or manifest.source.byte_length != native.byte_length
            or "sha256:" + manifest.source.sha256 != native.object_id
        ):
            raise RepresentationIntegrityError("manifest does not match representation")

    def _verify_blocks(
        self,
        projections: tuple[RepresentationBlock, ...],
        representation: DocumentRepresentation,
    ) -> None:
        if tuple(item.ordinal for item in projections) != tuple(range(len(projections))):
            raise RepresentationIntegrityError("block ordinals are incomplete")
        identifiers = {item.block_id for item in projections}
        sibling_orders: defaultdict[UUID | None, list[int]] = defaultdict(list)
        parents: dict[UUID, UUID | None] = {}
        for projection in projections:
            payload = self._read_object(projection.object)
            block = validate_json(ContentBlock, payload)
            self._assert_canonical_payload(payload, block)
            if (
                projection.scope != representation.scope
                or block.document_id != projection.scope.document_id
                or block.version_id != projection.scope.version_id
                or block.representation_id != projection.scope.representation_id
                or block.block_id != projection.block_id
                or block.parent_id != projection.parent_id
                or block.kind != projection.kind
                or block.order != projection.order
                or block.source.extensions.get("openardp.text")
                != {
                    "line_start": projection.line_start,
                    "line_end": projection.line_end,
                }
            ):
                raise RepresentationIntegrityError("block does not match catalog projection")
            if projection.parent_id is not None and projection.parent_id not in identifiers:
                raise RepresentationIntegrityError("block parent is missing")
            sibling_orders[projection.parent_id].append(projection.order)
            parents[projection.block_id] = projection.parent_id
        for orders in sibling_orders.values():
            if tuple(sorted(orders)) != tuple(range(len(orders))):
                raise RepresentationIntegrityError("block sibling order is incomplete")
        for block_id in identifiers:
            seen: set[UUID] = set()
            current: UUID | None = block_id
            while current is not None:
                if current in seen:
                    raise RepresentationIntegrityError("block hierarchy contains a cycle")
                seen.add(current)
                current = parents.get(current)

    def _record_failed_attempt(
        self,
        scope: RepresentationScope,
        *,
        owner_id: str,
        lease_token: str,
        expected_revision: int,
        error: Exception,
    ) -> None:
        failure_code = "parser_failed" if isinstance(error, ParserError) else "ingestion_failed"
        self._catalog.fail_representation(
            scope,
            owner_id=owner_id,
            lease_token=lease_token,
            expected_revision=expected_revision,
            now=self._clock(),
            failure_code=failure_code,
        )

    @staticmethod
    def _result(
        representation: DocumentRepresentation,
        *,
        disposition: IngestionDisposition,
        parser_invoked: bool,
        head_advanced: bool,
        ingested_at: datetime,
    ) -> IngestionResult:
        return IngestionResult(
            scope=representation.scope,
            disposition=disposition,
            parser_invoked=parser_invoked,
            cache_hit=disposition is IngestionDisposition.CACHE_HIT,
            head_advanced=head_advanced,
            block_count=representation.block_count,
            warning_codes=representation.warning_codes,
            ingested_at=ingested_at,
        )


__all__ = ["IngestionService"]
