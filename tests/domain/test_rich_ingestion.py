"""Pure model and identity tests for bounded rich ingestion."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.common import IntegrityState, Sensitivity, TrustZone
from openardp.domain.evidence import (
    EvidenceProjection,
    EvidenceReference,
    NativeRepresentation,
    OpaqueProviderPointerAnchor,
    ProjectionProvenance,
    ProviderPointer,
    ProviderRecipe,
    RetrievalHandle,
    TrustClassification,
)
from openardp.domain.identity import (
    canonical_json_bytes,
    evidence_projection_id,
    evidence_reference_id,
    native_representation_id,
)
from openardp.domain.ingestion import (
    IngestionDisposition,
    ParserRecipe,
    RepresentationScope,
)
from openardp.domain.rich_ingestion import (
    DOCLING_NATIVE_MEDIA_TYPE,
    NATIVE_EXPORT_PROFILE,
    PROJECTION_PROFILE,
    ComponentVersion,
    ModelBundleFile,
    ModelBundleManifest,
    NativeArtifactDescriptor,
    RichAttemptCommit,
    RichAttemptOutcome,
    RichEvidenceBundle,
    RichEvidenceCandidate,
    RichEvidenceKind,
    RichEvidenceRecord,
    RichIngestionResult,
    RichMediaType,
    RichParseAttempt,
    RichParseOutput,
    RichParserLimits,
    RichParserRecipe,
)
from openardp.domain.storage import StoredObject

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
SOURCE_ID = "sha256:" + "1" * 64
NATIVE_ID = "sha256:" + "2" * 64
CONFIG_ID = "sha256:" + "3" * 64
OBJECT_ID = "sha256:" + "4" * 64
DOCUMENT_ID = UUID("018f1000-0000-7000-8000-000000000001")
ATTEMPT_ID = UUID("018f1000-0000-7000-8000-000000000002")


def _limits() -> RichParserLimits:
    return RichParserLimits()


def _recipe() -> RichParserRecipe:
    parser = ParserRecipe(
        name="docling",
        version="2.114.0",
        profile="openardp-docling-native",
        config_hash=CONFIG_ID,
        normalization_schema_version="0.1.0",
    )
    provider = ProviderRecipe(
        name="docling",
        version="2.114.0",
        profile="openardp-docling-native",
        profile_version="0.1.0",
        config_hash=CONFIG_ID,
    )
    return RichParserRecipe(
        parser=parser,
        provider=provider,
        native_export_profile=NATIVE_EXPORT_PROFILE,
        projection_profile=PROJECTION_PROFILE,
        supported_media=tuple(RichMediaType),
        limits=_limits(),
    )


def _native() -> NativeRepresentation:
    provider = _recipe().provider
    identifier = native_representation_id(
        source_version_id=SOURCE_ID,
        native_artifact_id=NATIVE_ID,
        native_artifact_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        provider_name=provider.name,
        provider_version=provider.version,
        provider_profile=provider.profile,
        provider_profile_version=provider.profile_version,
        provider_config_hash=provider.config_hash,
    )
    return NativeRepresentation(
        native_representation_id=identifier,
        source_version_id=SOURCE_ID,
        native_artifact_id=NATIVE_ID,
        native_artifact_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        native_artifact_byte_length=123,
        provider=provider,
        created_at=NOW,
    )


def _reference(native: NativeRepresentation) -> EvidenceReference:
    anchor = OpaqueProviderPointerAnchor(
        anchor_type="provider_pointer",
        target=ProviderPointer(
            provider_profile="openardp-docling-native",
            provider_profile_version="0.1.0",
            pointer_format="rfc6901-json-pointer",
            pointer="#/texts/0",
        ),
    )
    identifier = evidence_reference_id(
        source_version_id=SOURCE_ID,
        native_representation_id=native.native_representation_id,
        anchor=anchor.model_dump(mode="json"),
    )
    return EvidenceReference(
        evidence_reference_id=identifier,
        source_version_id=SOURCE_ID,
        native_representation_id=native.native_representation_id,
        anchor=anchor,
    )


def _stored_model(model: object) -> StoredObject:
    assert hasattr(model, "model_dump")
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    return StoredObject(
        object_id="sha256:" + hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
    )


def _projection(
    native: NativeRepresentation, reference: EvidenceReference
) -> tuple[
    EvidenceProjection,
    StoredObject,
]:
    retrieval_bytes = b"synthetic text"
    retrieval = StoredObject(
        object_id="sha256:" + hashlib.sha256(retrieval_bytes).hexdigest(),
        byte_length=len(retrieval_bytes),
    )
    provenance = ProjectionProvenance(
        generator_name="docling",
        generator_version="2.114.0",
        generator_config_hash=CONFIG_ID,
        created_at=NOW,
    )
    projection_id = evidence_projection_id(
        source_version_id=SOURCE_ID,
        native_representation_id=native.native_representation_id,
        evidence_reference_id=reference.evidence_reference_id,
        retrieval_artifact_id=retrieval.object_id,
        retrieval_media_type="text/plain",
        parent_projection_id=None,
        ordinal=0,
        generator_name=provenance.generator_name,
        generator_version=provenance.generator_version,
        generator_config_hash=provenance.generator_config_hash,
    )
    projection = EvidenceProjection(
        evidence_projection_id=projection_id,
        source_version_id=SOURCE_ID,
        native_representation_id=native.native_representation_id,
        reference=reference,
        retrieval=RetrievalHandle(
            artifact_id=retrieval.object_id,
            media_type="text/plain",
            byte_length=retrieval.byte_length,
        ),
        ordinal=0,
        trust=TrustClassification(
            origin_zone=TrustZone.EXTERNAL_UNTRUSTED,
            effective_zone=TrustZone.EXTERNAL_UNTRUSTED,
            role="data",
            instruction_execution_allowed=False,
            integrity=IntegrityState.VERIFIED_SHA256,
            sensitivity=Sensitivity.INTERNAL,
        ),
        provenance=provenance,
    )
    return projection, retrieval


def test_rich_media_and_default_limits_are_closed_and_explicit() -> None:
    """Freeze the F007 media allowlist and documented portable defaults."""
    assert tuple(item.value for item in RichMediaType) == (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    assert _limits().model_dump() == {
        "max_source_bytes": 104_857_600,
        "max_pages": 500,
        "timeout_seconds": 120.0,
        "max_address_space_bytes": 4_294_967_296,
        "max_open_files": 64,
        "max_native_bytes": 268_435_456,
        "max_projections": 100_000,
        "max_retrieval_body_bytes": 8_388_608,
        "max_total_retrieval_bytes": 268_435_456,
    }
    with pytest.raises(ValidationError):
        RichParserLimits(timeout_seconds=0)
    with pytest.raises(ValidationError):
        RichParserLimits(max_pages=2_001)


def test_model_bundle_identity_is_path_independent_and_order_strict() -> None:
    """Identify reviewed model bytes without incorporating their local root path."""
    files = (
        ModelBundleFile(
            path="layout/model.safetensors",
            sha256="sha256:" + "a" * 64,
            byte_length=10,
            license_id="Apache-2.0",
        ),
        ModelBundleFile(
            path="table/model.safetensors",
            sha256="sha256:" + "b" * 64,
            byte_length=20,
            license_id="MIT",
        ),
    )
    manifest = ModelBundleManifest(
        schema_version="0.1.0",
        bundle_name="docling-default",
        bundle_version="2.114.0",
        files=files,
    )
    reconstructed = ModelBundleManifest.model_validate_json(manifest.model_dump_json())

    assert manifest.bundle_id == reconstructed.bundle_id
    assert manifest.bundle_id.startswith("sha256:")
    with pytest.raises(ValidationError, match="sorted"):
        ModelBundleManifest(
            schema_version="0.1.0",
            bundle_name="docling-default",
            bundle_version="2.114.0",
            files=tuple(reversed(files)),
        )


def test_rich_recipe_aligns_existing_and_f006_provider_identities() -> None:
    """Prevent parser/provider profile drift under one representation identity."""
    recipe = _recipe()
    assert recipe.parser.config_hash == recipe.provider.config_hash
    assert recipe.provider.profile_version == "0.1.0"
    assert recipe.model_bundle_id is None

    with pytest.raises(ValidationError, match="provider"):
        RichParserRecipe(
            parser=recipe.parser,
            provider=recipe.provider.model_copy(update={"version": "2.113.0"}),
            native_export_profile=NATIVE_EXPORT_PROFILE,
            projection_profile=PROJECTION_PROFILE,
            supported_media=tuple(RichMediaType),
            limits=_limits(),
        )


def test_candidate_and_parse_output_require_contiguous_bounded_provider_order() -> None:
    """Keep worker output deterministic without exposing provider classes."""
    pointer = ProviderPointer(
        provider_profile="openardp-docling-native",
        provider_profile_version="0.1.0",
        pointer_format="rfc6901-json-pointer",
        pointer="#/texts/0",
    )
    candidate = RichEvidenceCandidate(
        ordinal=0,
        kind=RichEvidenceKind.TEXT,
        anchor=OpaqueProviderPointerAnchor(anchor_type="provider_pointer", target=pointer),
        retrieval_media_type="text/plain",
        retrieval_text="synthetic text",
        native_pointer=pointer,
    )
    output = RichParseOutput(
        media_type=RichMediaType.DOCX,
        native_document={"schema_name": "DoclingDocument", "texts": [{"text": "synthetic"}]},
        candidates=(candidate,),
        component_versions=(
            ComponentVersion(name="docling", version="2.114.0"),
            ComponentVersion(name="docling-core", version="2.87.1"),
        ),
    )

    assert output.candidates[0].retrieval_bytes == b"synthetic text"
    assert "docling" not in type(output).__module__
    with pytest.raises(ValidationError, match="contiguous"):
        RichParseOutput(
            media_type=RichMediaType.DOCX,
            native_document={},
            candidates=(candidate.model_copy(update={"ordinal": 1}),),
            component_versions=output.component_versions,
        )
    with pytest.raises(ValidationError, match="parent"):
        RichEvidenceCandidate(
            ordinal=0,
            parent_ordinal=0,
            kind=RichEvidenceKind.TEXT,
            anchor=candidate.anchor,
            retrieval_media_type="text/plain",
            retrieval_text="body",
            native_pointer=pointer,
        )


def test_descriptor_bundle_and_attempt_bind_exact_native_scope() -> None:
    """Reject internal aggregate drift before any catalog I/O."""
    native = _native()
    reference = _reference(native)
    native_object = StoredObject(object_id=NATIVE_ID, byte_length=123)
    descriptor = NativeArtifactDescriptor(
        schema_version="0.1.0",
        source_version_id=SOURCE_ID,
        native_representation=native,
        provider_native_object=native_object,
        native_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        native_export_profile=NATIVE_EXPORT_PROFILE,
        projection_profile=PROJECTION_PROFILE,
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
        created_at=NOW,
    )
    descriptor_bytes = descriptor.canonical_bytes
    descriptor_object = StoredObject(
        object_id="sha256:" + hashlib.sha256(descriptor_bytes).hexdigest(),
        byte_length=len(descriptor_bytes),
    )
    native_record_bytes = canonical_json_bytes(native.model_dump(mode="json"))
    native_record_object = StoredObject(
        object_id="sha256:" + hashlib.sha256(native_record_bytes).hexdigest(),
        byte_length=len(native_record_bytes),
    )
    scope = RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=SOURCE_ID,
        representation_id=_recipe().parser.representation_id_for(SOURCE_ID),
    )
    bundle = RichEvidenceBundle(
        schema_version="0.1.0",
        scope=scope,
        descriptor=descriptor,
        descriptor_object=descriptor_object,
        native_record_object=native_record_object,
        native_representation=native,
        references=(reference,),
        projections=(),
        created_at=NOW,
    )
    attempt = RichParseAttempt(
        attempt_id=ATTEMPT_ID,
        scope=scope,
        outcome=RichAttemptOutcome.CANONICAL,
        descriptor_object=descriptor_object,
        provider_native_object=native_object,
        native_record_object=native_record_object,
        evidence_bundle_object=StoredObject(object_id=OBJECT_ID, byte_length=10),
        projection_count=0,
        created_at=NOW,
    )

    assert bundle.native_representation.native_artifact_id == native_object.object_id
    assert attempt.outcome is RichAttemptOutcome.CANONICAL
    with pytest.raises(ValidationError, match="source"):
        NativeArtifactDescriptor(
            schema_version=descriptor.schema_version,
            source_version_id="sha256:" + "9" * 64,
            native_representation=descriptor.native_representation,
            provider_native_object=descriptor.provider_native_object,
            native_media_type=descriptor.native_media_type,
            native_export_profile=descriptor.native_export_profile,
            projection_profile=descriptor.projection_profile,
            component_versions=descriptor.component_versions,
            model_bundle_id=descriptor.model_bundle_id,
            created_at=descriptor.created_at,
            nondeterminism=descriptor.nondeterminism,
        )


def test_persistence_records_attempts_and_result_preserve_complete_identity() -> None:
    """Bind each persistence object and expose only body-free successful result facts."""
    native = _native()
    reference = _reference(native)
    projection, retrieval_object = _projection(native, reference)
    native_object = StoredObject(object_id=NATIVE_ID, byte_length=123)
    descriptor = NativeArtifactDescriptor(
        source_version_id=SOURCE_ID,
        native_representation=native,
        provider_native_object=native_object,
        native_media_type=DOCLING_NATIVE_MEDIA_TYPE,
        native_export_profile=NATIVE_EXPORT_PROFILE,
        projection_profile=PROJECTION_PROFILE,
        component_versions=(ComponentVersion(name="docling", version="2.114.0"),),
        created_at=NOW,
    )
    scope = RepresentationScope(
        document_id=DOCUMENT_ID,
        version_id=SOURCE_ID,
        representation_id=_recipe().parser.representation_id_for(SOURCE_ID),
    )
    record = RichEvidenceRecord(
        ordinal=0,
        reference=reference,
        projection=projection,
        reference_object=_stored_model(reference),
        projection_object=_stored_model(projection),
        retrieval_object=retrieval_object,
    )
    bundle = RichEvidenceBundle(
        scope=scope,
        descriptor=descriptor,
        descriptor_object=_stored_model(descriptor),
        native_record_object=_stored_model(native),
        native_representation=native,
        references=(reference,),
        projections=(projection,),
        records=(record,),
        created_at=NOW,
    )
    attempt = RichParseAttempt(
        attempt_id=ATTEMPT_ID,
        scope=scope,
        outcome=RichAttemptOutcome.CANONICAL,
        descriptor_object=bundle.descriptor_object,
        provider_native_object=native_object,
        native_record_object=bundle.native_record_object,
        evidence_bundle_object=_stored_model(bundle),
        projection_count=1,
        created_at=NOW,
    )
    commit = RichAttemptCommit(attempt=attempt, bundle=bundle)
    result = RichIngestionResult(
        scope=scope,
        disposition=IngestionDisposition.COMMITTED,
        parser_invoked=True,
        cache_hit=False,
        head_advanced=True,
        native_representation_id=native.native_representation_id,
        native_artifact_id=native.native_artifact_id,
        evidence_count=1,
        warning_codes=(),
        attempt_id=ATTEMPT_ID,
        accepted_attempt_id=ATTEMPT_ID,
        attempt_outcome=RichAttemptOutcome.CANONICAL,
        ingested_at=NOW,
    )

    assert commit.bundle.records == (record,)
    assert result.evidence_count == 1
    with pytest.raises(ValidationError, match="projection count"):
        RichAttemptCommit(
            attempt=attempt.model_copy(update={"projection_count": 0}),
            bundle=bundle,
        )
    with pytest.raises(ValidationError, match="cache"):
        RichIngestionResult(
            scope=scope,
            disposition=IngestionDisposition.COMMITTED,
            parser_invoked=True,
            cache_hit=True,
            head_advanced=True,
            native_representation_id=native.native_representation_id,
            native_artifact_id=native.native_artifact_id,
            evidence_count=1,
            warning_codes=(),
            attempt_id=ATTEMPT_ID,
            accepted_attempt_id=ATTEMPT_ID,
            attempt_outcome=RichAttemptOutcome.CANONICAL,
            ingested_at=NOW,
        )
