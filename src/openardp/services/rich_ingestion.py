"""CAS-backed construction of F006 evidence from strict rich parser output."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from openardp.domain.common import (
    ContentRole,
    IntegrityState,
    ParserDescriptor,
    Sensitivity,
    TrustZone,
    validate_json,
)
from openardp.domain.evidence import (
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    ProjectionProvenance,
    RetrievalHandle,
    TrustClassification,
    validate_evidence_records,
)
from openardp.domain.identity import (
    canonical_json_bytes,
    evidence_projection_id,
    evidence_reference_id,
    native_representation_id,
)
from openardp.domain.ingestion import (
    IngestionDisposition,
    ReadyRepresentationCommit,
    RepresentationAcquireDisposition,
    RepresentationAggregate,
    RepresentationScope,
    RichMediaType,
    SourceSnapshot,
)
from openardp.domain.manifest import (
    DocumentManifest,
    ManifestState,
    SchemaVersions,
    SourceDescriptor,
)
from openardp.domain.rich_ingestion import (
    DOCLING_NATIVE_MEDIA_TYPE,
    NativeArtifactDescriptor,
    ReadyRichRepresentationCommit,
    RichAttemptCommit,
    RichAttemptOutcome,
    RichEvidenceBundle,
    RichEvidenceRecord,
    RichIngestionResult,
    RichParseAttempt,
    RichParseOutput,
    RichParserRecipe,
    RichRepresentationArtifacts,
)
from openardp.domain.storage import (
    DocumentVersion,
    LogicalDocument,
    SourceVersionCommit,
    StoredObject,
    generate_uuid7,
)
from openardp.ports.catalog import (
    DocumentConflict,
    RepresentationBusy,
    RepresentationIntegrityError,
    RichCatalog,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError
from openardp.ports.parser import ParserError, RichParserAdapter

_REPRESENTATION_LEASE = timedelta(minutes=5)


class _SourceBoundary(Protocol):
    """Narrow stable-source boundary injected by the composition root."""

    def snapshot_to(
        self,
        object_store: ObjectStore,
        *,
        observed_at: datetime,
    ) -> SourceSnapshot:
        """Publish one exact stable source snapshot."""
        ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _owner_id() -> str:
    return f"openardp-rich-{os.getpid()}"


def _lease_token() -> str:
    return secrets.token_hex(32)


def _random_uuid7_bits() -> int:
    return secrets.randbits(74)


def prepare_rich_attempt(
    *,
    scope: RepresentationScope,
    recipe: RichParserRecipe,
    output: RichParseOutput,
    object_store: ObjectStore,
    attempt_id: UUID,
    outcome: RichAttemptOutcome,
    created_at: datetime,
) -> RichAttemptCommit:
    """Publish immutable derived objects and return one validated attempt aggregate."""
    native_bytes = output.canonical_native_bytes
    provider_native_object = _put_exact(object_store, native_bytes)
    native_id = native_representation_id(
        source_version_id=scope.version_id,
        native_artifact_id=provider_native_object.object_id,
        native_artifact_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        provider_name=recipe.provider.name,
        provider_version=recipe.provider.version,
        provider_profile=recipe.provider.profile,
        provider_profile_version=recipe.provider.profile_version,
        provider_config_hash=recipe.provider.config_hash,
    )
    native = NativeRepresentation(
        native_representation_id=native_id,
        source_version_id=scope.version_id,
        native_artifact_id=provider_native_object.object_id,
        native_artifact_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        native_artifact_byte_length=provider_native_object.byte_length,
        provider=recipe.provider,
        created_at=created_at,
    )
    native_record_object = _put_model(object_store, native)
    descriptor = NativeArtifactDescriptor(
        source_version_id=scope.version_id,
        native_representation=native,
        provider_native_object=provider_native_object,
        native_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        native_export_profile=recipe.native_export_profile,
        projection_profile=recipe.projection_profile,
        component_versions=output.component_versions,
        model_bundle_id=recipe.model_bundle_id,
        created_at=created_at,
        nondeterminism=output.warning_codes,
    )
    descriptor_object = _put_exact(object_store, descriptor.canonical_bytes)

    references: list[EvidenceReference] = []
    projections: list[EvidenceProjection] = []
    records: list[RichEvidenceRecord] = []
    projection_id_by_ordinal: dict[int, str] = {}
    for candidate in output.candidates:
        reference_id = evidence_reference_id(
            source_version_id=scope.version_id,
            native_representation_id=native.native_representation_id,
            anchor=candidate.anchor.model_dump(mode="json"),
        )
        reference = EvidenceReference(
            evidence_reference_id=reference_id,
            source_version_id=scope.version_id,
            native_representation_id=native.native_representation_id,
            anchor=candidate.anchor,
        )
        retrieval_object = _put_exact(object_store, candidate.retrieval_bytes)
        parent_projection_id = (
            projection_id_by_ordinal[candidate.parent_ordinal]
            if candidate.parent_ordinal is not None
            else None
        )
        provenance = ProjectionProvenance(
            generator_name=recipe.provider.name,
            generator_version=recipe.provider.version,
            generator_config_hash=recipe.provider.config_hash,
            created_at=created_at,
        )
        projection_id = evidence_projection_id(
            source_version_id=scope.version_id,
            native_representation_id=native.native_representation_id,
            evidence_reference_id=reference.evidence_reference_id,
            retrieval_artifact_id=retrieval_object.object_id,
            retrieval_media_type=candidate.retrieval_media_type,
            parent_projection_id=parent_projection_id,
            ordinal=candidate.ordinal,
            generator_name=provenance.generator_name,
            generator_version=provenance.generator_version,
            generator_config_hash=provenance.generator_config_hash,
        )
        projection = EvidenceProjection(
            evidence_projection_id=projection_id,
            source_version_id=scope.version_id,
            native_representation_id=native.native_representation_id,
            reference=reference,
            retrieval=RetrievalHandle(
                artifact_id=retrieval_object.object_id,
                media_type=candidate.retrieval_media_type,
                byte_length=retrieval_object.byte_length,
            ),
            parent_projection_id=parent_projection_id,
            ordinal=candidate.ordinal,
            trust=TrustClassification(
                origin_zone=TrustZone.EXTERNAL_UNTRUSTED,
                effective_zone=TrustZone.EXTERNAL_UNTRUSTED,
                role=ContentRole.DATA,
                instruction_execution_allowed=False,
                integrity=IntegrityState.VERIFIED_SHA256,
                sensitivity=Sensitivity.INTERNAL,
            ),
            provenance=provenance,
        )
        record = RichEvidenceRecord(
            ordinal=candidate.ordinal,
            parent_projection_id=parent_projection_id,
            reference=reference,
            projection=projection,
            reference_object=_put_model(object_store, reference),
            projection_object=_put_model(object_store, projection),
            retrieval_object=retrieval_object,
        )
        references.append(reference)
        projections.append(projection)
        records.append(record)
        projection_id_by_ordinal[candidate.ordinal] = projection_id

    validate_evidence_records(
        native,
        references,
        projections,
        expected_source_version_id=scope.version_id,
    )
    bundle = RichEvidenceBundle(
        scope=scope,
        descriptor=descriptor,
        descriptor_object=descriptor_object,
        native_record_object=native_record_object,
        native_representation=native,
        references=tuple(references),
        projections=tuple(projections),
        records=tuple(records),
        created_at=created_at,
    )
    bundle_object = _put_exact(object_store, bundle.canonical_bytes)
    attempt = RichParseAttempt(
        attempt_id=attempt_id,
        scope=scope,
        outcome=outcome,
        descriptor_object=descriptor_object,
        provider_native_object=provider_native_object,
        native_record_object=native_record_object,
        evidence_bundle_object=bundle_object,
        projection_count=len(projections),
        created_at=created_at,
    )
    return RichAttemptCommit(attempt=attempt, bundle=bundle)


class RichIngestionService:
    """Coordinate exact rich-source reuse, isolated parsing and atomic publication."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: RichCatalog,
        parser: RichParserAdapter,
        *,
        source_factory: Callable[[Path], _SourceBoundary],
        clock: Callable[[], datetime] = _utc_now,
        owner_id_factory: Callable[[], str] = _owner_id,
        lease_token_factory: Callable[[], str] = _lease_token,
        random_bits: Callable[[], int] = _random_uuid7_bits,
    ) -> None:
        """Bind provider-neutral ports and injectable nondeterminism sources."""
        self._object_store = object_store
        self._catalog = catalog
        self._parser = parser
        self._source_factory = source_factory
        self._clock = clock
        self._owner_id_factory = owner_id_factory
        self._lease_token_factory = lease_token_factory
        self._random_bits = random_bits

    @property
    def recipe(self) -> RichParserRecipe:
        """Return the exact immutable rich processing recipe."""
        return self._parser.recipe

    def ingest(
        self,
        source: Path,
        *,
        profile: str = "openardp-docling-native",
        force: bool = False,
    ) -> RichIngestionResult:
        """Ingest or fully verify and reuse one exact local rich representation."""
        recipe = self._parser.recipe
        if profile != recipe.parser.profile:
            raise ValueError("unsupported parser profile")
        observed_at = self._clock()
        snapshot = self._source_factory(source).snapshot_to(
            self._object_store,
            observed_at=observed_at,
        )
        if not isinstance(snapshot.media_type, RichMediaType):
            raise ValueError("rich ingestion requires PDF, DOCX or PPTX media")
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

        scope = RepresentationScope(
            document_id=document.document_id,
            version_id=version.version_id,
            representation_id=recipe.parser.representation_id_for(version.version_id),
        )
        owner_id = self._owner_id_factory()
        lease_token = self._lease_token_factory()
        acquired = self._catalog.acquire_representation(
            scope,
            recipe.parser,
            owner_id=owner_id,
            lease_token=lease_token,
            now=observed_at,
            lease_until=observed_at + _REPRESENTATION_LEASE,
        )
        if acquired.disposition is RepresentationAcquireDisposition.BUSY:
            raise RepresentationBusy("representation is busy")

        accepted: RichRepresentationArtifacts | None = None
        if acquired.disposition is RepresentationAcquireDisposition.READY:
            accepted = self._catalog.load_rich_representation(scope)
            if accepted is None:
                raise RepresentationIntegrityError("ready rich representation is missing")
            self.verify_ready_representation(accepted)
            if not force:
                ingested_at = self._clock()
                update = self._catalog.record_ready_ingest(
                    scope,
                    source_observed_at=observed_at,
                    ingested_at=ingested_at,
                    disposition=IngestionDisposition.CACHE_HIT,
                )
                return self._result(
                    accepted,
                    attempt=accepted.accepted_attempt,
                    disposition=update.event.disposition,
                    parser_invoked=False,
                    head_advanced=update.event.head_advanced,
                    ingested_at=ingested_at,
                )

        claimed = acquired.disposition is RepresentationAcquireDisposition.CLAIMED
        try:
            output = self._parser.parse(
                self._object_store.iter_chunks(version.version_id),
                media_type=version.media_type,
            )
            if output.media_type is not snapshot.media_type:
                raise RepresentationIntegrityError("parser media type differs from source")
            completed_at = self._clock()
            provisional = prepare_rich_attempt(
                scope=scope,
                recipe=recipe,
                output=output,
                object_store=self._object_store,
                attempt_id=generate_uuid7(
                    now=completed_at,
                    random_bits=self._random_bits(),
                ),
                outcome=(RichAttemptOutcome.CANONICAL if claimed else RichAttemptOutcome.DIVERGED),
                created_at=completed_at,
            )
            if claimed:
                base = self._prepare_base_commit(
                    snapshot=snapshot,
                    version=version,
                    output=output,
                    ready_at=completed_at,
                )
                result = self._catalog.commit_ready_rich_representation(
                    ReadyRichRepresentationCommit(base=base, rich=provisional),
                    owner_id=owner_id,
                    lease_token=lease_token,
                    expected_revision=acquired.representation.revision,
                    disposition=IngestionDisposition.COMMITTED,
                )
                artifacts = result.artifacts
                event = result.event
                attempt = provisional.attempt
            else:
                if accepted is None:
                    raise RepresentationIntegrityError("accepted rich representation is missing")
                outcome = (
                    RichAttemptOutcome.CONVERGED
                    if self._attempts_converge(accepted, provisional)
                    else RichAttemptOutcome.DIVERGED
                )
                candidate = RichAttemptCommit(
                    attempt=provisional.attempt.model_copy(update={"outcome": outcome}),
                    bundle=provisional.bundle,
                )
                appended = self._catalog.append_rich_attempt(
                    candidate,
                    source_observed_at=observed_at,
                    occurred_at=completed_at,
                )
                artifacts = accepted
                event = appended.event
                attempt = candidate.attempt
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

        self.verify_ready_representation(artifacts)
        return self._result(
            artifacts,
            attempt=attempt,
            disposition=event.disposition,
            parser_invoked=True,
            head_advanced=event.head_advanced,
            ingested_at=event.occurred_at,
        )

    def verify_ready_representation(self, artifacts: RichRepresentationArtifacts) -> None:
        """Physically and semantically verify every accepted base and rich artifact."""
        try:
            self._verify_base(artifacts.aggregate)
            attempt = artifacts.accepted_attempt
            bundle = artifacts.bundle
            self._assert_exact_model(attempt.descriptor_object, bundle.descriptor)
            self._assert_exact_model(attempt.native_record_object, bundle.native_representation)
            self._assert_exact_model(attempt.evidence_bundle_object, bundle)
            native_payload = self._read_object(attempt.provider_native_object)
            native_value = json.loads(native_payload)
            if (
                not isinstance(native_value, dict)
                or canonical_json_bytes(native_value) != native_payload
                or attempt.provider_native_object != bundle.descriptor.provider_native_object
            ):
                raise RepresentationIntegrityError("provider native artifact is inconsistent")
            for record in bundle.records:
                self._assert_exact_model(record.reference_object, record.reference)
                self._assert_exact_model(record.projection_object, record.projection)
                self._object_store.verify(
                    record.retrieval_object.object_id,
                    expected_length=record.retrieval_object.byte_length,
                )
        except RepresentationIntegrityError:
            raise
        except (ObjectStoreError, ValidationError, ValueError, json.JSONDecodeError) as error:
            raise RepresentationIntegrityError("rich representation integrity failed") from error

    def _verify_base(self, aggregate: RepresentationAggregate) -> None:
        representation = aggregate.representation
        if (
            representation.manifest_object is None
            or representation.native_object is None
            or aggregate.blocks
        ):
            raise RepresentationIntegrityError("rich base representation is incomplete")
        self._object_store.verify(
            representation.native_object.object_id,
            expected_length=representation.native_object.byte_length,
        )
        manifest_payload = self._read_object(representation.manifest_object)
        manifest = validate_json(DocumentManifest, manifest_payload)
        if manifest_payload != canonical_json_bytes(manifest.model_dump(mode="json")):
            raise RepresentationIntegrityError("rich manifest bytes are non-canonical")
        if (
            manifest.document_id != representation.scope.document_id
            or manifest.version_id != representation.scope.version_id
            or manifest.representation_id != representation.scope.representation_id
            or manifest.state is not ManifestState.READY
            or manifest.parser.name != representation.recipe.name
            or manifest.parser.version != representation.recipe.version
            or manifest.parser.profile != representation.recipe.profile
            or manifest.parser.config_hash != representation.recipe.config_hash
            or manifest.source.byte_length != representation.native_object.byte_length
            or "sha256:" + manifest.source.sha256 != representation.native_object.object_id
        ):
            raise RepresentationIntegrityError("rich manifest does not match representation")

    def _prepare_base_commit(
        self,
        *,
        snapshot: SourceSnapshot,
        version: DocumentVersion,
        output: RichParseOutput,
        ready_at: datetime,
    ) -> ReadyRepresentationCommit:
        recipe = self._parser.recipe.parser
        scope = RepresentationScope(
            document_id=version.document_id,
            version_id=version.version_id,
            representation_id=recipe.representation_id_for(version.version_id),
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
                name=recipe.name,
                version=recipe.version,
                profile=recipe.profile,
                config_hash=recipe.config_hash,
            ),
            schema_versions=SchemaVersions(
                block=recipe.normalization_schema_version,
                derivation="0.1.0",
                relation="0.1.0",
            ),
        )
        return ReadyRepresentationCommit(
            scope=scope,
            recipe=recipe,
            manifest=manifest,
            manifest_object=self._put_canonical_model(manifest),
            native_object=snapshot.object,
            blocks=(),
            warning_codes=output.warning_codes,
            source_observed_at=snapshot.observed_at,
            ready_at=ready_at,
        )

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

    def _put_canonical_model(self, model: DocumentManifest) -> StoredObject:
        payload = canonical_json_bytes(model.model_dump(mode="json"))
        expected = StoredObject(
            object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
        )
        stored = self._object_store.put_chunks((payload,))
        if stored != expected:
            raise RepresentationIntegrityError("canonical object publication is inconsistent")
        return self._object_store.verify(
            stored.object_id,
            expected_length=stored.byte_length,
        )

    def _assert_exact_model(self, stored: StoredObject, model: object) -> None:
        if not hasattr(model, "model_dump"):
            raise RepresentationIntegrityError("canonical rich model is invalid")
        payload = self._read_object(stored)
        expected = canonical_json_bytes(model.model_dump(mode="json"))
        if payload != expected:
            raise RepresentationIntegrityError("canonical rich record bytes are inconsistent")

    def _read_object(self, stored: StoredObject) -> bytes:
        verified = self._object_store.verify(
            stored.object_id,
            expected_length=stored.byte_length,
        )
        payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        if len(payload) != verified.byte_length:
            raise RepresentationIntegrityError("rich object length changed during read")
        return payload

    @staticmethod
    def _attempts_converge(
        accepted: RichRepresentationArtifacts,
        candidate: RichAttemptCommit,
    ) -> bool:
        left = accepted.bundle
        right = candidate.bundle
        return (
            left.descriptor.provider_native_object == right.descriptor.provider_native_object
            and left.descriptor.component_versions == right.descriptor.component_versions
            and left.descriptor.model_bundle_id == right.descriptor.model_bundle_id
            and left.descriptor.nondeterminism == right.descriptor.nondeterminism
            and left.native_representation.native_representation_id
            == right.native_representation.native_representation_id
            and tuple(item.evidence_reference_id for item in left.references)
            == tuple(item.evidence_reference_id for item in right.references)
            and tuple(item.evidence_projection_id for item in left.projections)
            == tuple(item.evidence_projection_id for item in right.projections)
            and tuple(item.retrieval_object for item in left.records)
            == tuple(item.retrieval_object for item in right.records)
        )

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
        artifacts: RichRepresentationArtifacts,
        *,
        attempt: RichParseAttempt,
        disposition: IngestionDisposition,
        parser_invoked: bool,
        head_advanced: bool,
        ingested_at: datetime,
    ) -> RichIngestionResult:
        descriptor = artifacts.bundle.descriptor
        return RichIngestionResult(
            scope=attempt.scope,
            disposition=disposition,
            parser_invoked=parser_invoked,
            cache_hit=disposition is IngestionDisposition.CACHE_HIT,
            head_advanced=head_advanced,
            native_representation_id=descriptor.native_representation.native_representation_id,
            native_artifact_id=descriptor.provider_native_object.object_id,
            evidence_count=len(artifacts.bundle.projections),
            warning_codes=descriptor.nondeterminism,
            attempt_id=attempt.attempt_id,
            accepted_attempt_id=artifacts.accepted_attempt_id,
            attempt_outcome=attempt.outcome,
            ingested_at=ingested_at,
        )


def _put_model(object_store: ObjectStore, model: object) -> StoredObject:
    if not hasattr(model, "model_dump"):
        raise TypeError("canonical model required")
    return _put_exact(
        object_store,
        canonical_json_bytes(model.model_dump(mode="json")),
    )


def _put_exact(object_store: ObjectStore, payload: bytes) -> StoredObject:
    stored = object_store.put_chunks((payload,))
    return object_store.verify(
        stored.object_id,
        expected_length=stored.byte_length,
    )


__all__ = ["RichIngestionService", "prepare_rich_attempt"]
