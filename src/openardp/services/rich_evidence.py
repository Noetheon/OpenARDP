"""Provider-free inspection and exact retrieval for accepted rich evidence."""

from __future__ import annotations

import json
from collections.abc import Callable
from uuid import UUID

from pydantic import JsonValue

from openardp.adapters.docling_native import resolve_json_pointer
from openardp.domain.common import DomainModel
from openardp.domain.evidence import EvidenceProjection, ProviderPointer
from openardp.domain.identity import canonical_json_bytes
from openardp.domain.rich_ingestion import RichRepresentationArtifacts
from openardp.domain.storage import StoredObject
from openardp.ports.catalog import (
    DocumentNotFound,
    RepresentationConflict,
    RepresentationIntegrityError,
    RepresentationNotFound,
    RichCatalog,
)
from openardp.ports.object_store import ObjectStore, ObjectStoreError


class RetrievedRichEvidence(DomainModel):
    """One explicitly requested exact retrieval body and its verified projection."""

    projection: EvidenceProjection
    body: str


class RichEvidenceService:
    """Inspect accepted rich evidence without importing or invoking its provider."""

    def __init__(
        self,
        object_store: ObjectStore,
        catalog: RichCatalog,
        *,
        representation_verifier: Callable[[RichRepresentationArtifacts], None],
    ) -> None:
        """Bind provider-neutral persistence and integrity boundaries."""
        self._object_store = object_store
        self._catalog = catalog
        self._representation_verifier = representation_verifier

    def list(
        self,
        document_id: UUID,
        *,
        version_id: str | None = None,
    ) -> tuple[EvidenceProjection, ...]:
        """Return deterministic body-free evidence for one accepted rich representation."""
        artifacts = self._resolve_artifacts(document_id, version_id=version_id)
        self._representation_verifier(artifacts)
        return artifacts.bundle.projections

    def get(
        self,
        evidence_projection_id: str,
        *,
        document_id: UUID | None = None,
    ) -> RetrievedRichEvidence:
        """Return one unambiguous current projection and its exact verified UTF-8 body."""
        matches: list[tuple[RichRepresentationArtifacts, EvidenceProjection, StoredObject]] = []
        for artifacts in self._current_artifacts(document_id=document_id):
            for record in artifacts.bundle.records:
                if record.projection.evidence_projection_id == evidence_projection_id:
                    matches.append((artifacts, record.projection, record.retrieval_object))
        if not matches:
            raise RepresentationNotFound("rich evidence projection does not exist")
        if len(matches) > 1:
            raise RepresentationConflict("rich evidence projection is ambiguous")
        artifacts, projection, stored = matches[0]
        self._representation_verifier(artifacts)
        payload = self._read_object(stored)
        try:
            body = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RepresentationIntegrityError("rich retrieval body is not UTF-8") from error
        if projection.retrieval.media_type == "application/json":
            try:
                value = json.loads(body)
                if canonical_json_bytes(value) != payload:
                    raise ValueError
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise RepresentationIntegrityError(
                    "rich retrieval JSON is non-canonical"
                ) from error
        return RetrievedRichEvidence(projection=projection, body=body)

    def native(
        self,
        document_id: UUID,
        *,
        version_id: str | None = None,
    ) -> dict[str, JsonValue]:
        """Return one exact retained native JSON value for object-scoped callers."""
        artifacts = self._resolve_artifacts(document_id, version_id=version_id)
        self._representation_verifier(artifacts)
        payload = self._read_object(artifacts.accepted_attempt.provider_native_object)
        try:
            value = json.loads(payload)
            if not isinstance(value, dict) or canonical_json_bytes(value) != payload:
                raise ValueError
            return value
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise RepresentationIntegrityError("provider native JSON is invalid") from error

    def resolve(
        self,
        document_id: UUID,
        pointer: ProviderPointer,
        *,
        version_id: str | None = None,
        max_resolved_bytes: int = 8_388_608,
    ) -> JsonValue:
        """Resolve one exact profile-scoped pointer inside retained native JSON only."""
        artifacts = self._resolve_artifacts(document_id, version_id=version_id)
        provider = artifacts.bundle.descriptor.native_representation.provider
        if (
            pointer.provider_profile != provider.profile
            or pointer.provider_profile_version != provider.profile_version
            or pointer.pointer_format != "rfc6901-json-pointer"
        ):
            raise ValueError("provider pointer profile is not accepted")
        native = self.native(document_id, version_id=version_id)
        return resolve_json_pointer(
            native,
            pointer.pointer,
            max_resolved_bytes=max_resolved_bytes,
        )

    def _resolve_artifacts(
        self,
        document_id: UUID,
        *,
        version_id: str | None,
    ) -> RichRepresentationArtifacts:
        aggregate = self._catalog.resolve_ready_representation(
            document_id,
            version_id=version_id,
        )
        if aggregate is None:
            if self._catalog.get_document(document_id) is None:
                raise DocumentNotFound(str(document_id))
            raise RepresentationNotFound("ready representation does not exist")
        artifacts = self._catalog.load_rich_representation(aggregate.representation.scope)
        if artifacts is None:
            raise RepresentationNotFound("rich representation does not exist")
        return artifacts

    def _current_artifacts(
        self,
        *,
        document_id: UUID | None,
    ) -> tuple[RichRepresentationArtifacts, ...]:
        summaries = self._catalog.list_document_summaries()
        artifacts: list[RichRepresentationArtifacts] = []
        for summary in summaries:
            if document_id is not None and summary.document_id != document_id:
                continue
            if summary.head is None:
                continue
            rich = self._catalog.load_rich_representation(summary.head)
            if rich is not None:
                artifacts.append(rich)
        return tuple(artifacts)

    def _read_object(self, stored: StoredObject) -> bytes:
        try:
            verified = self._object_store.verify(
                stored.object_id,
                expected_length=stored.byte_length,
            )
            payload = b"".join(self._object_store.iter_chunks(verified.object_id))
        except ObjectStoreError as error:
            raise RepresentationIntegrityError("rich evidence object is invalid") from error
        if len(payload) != verified.byte_length:
            raise RepresentationIntegrityError("rich evidence object length changed")
        return payload


__all__ = ["RetrievedRichEvidence", "RichEvidenceService"]
