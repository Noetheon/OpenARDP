"""Version-pinned auditable context bundle contract."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue, field_validator, model_validator

from openardp.domain.common import (
    CanonicalUuid,
    DataTrustClassification,
    DocumentId,
    DomainModel,
    ExtensibleModel,
    NonEmptyStr,
    Sha256Id,
    SourceLocator,
    SupportedSchemaVersion,
    UtcDatetime,
    ensure_json_value,
)


class ContextMode(StrEnum):
    """Evidence-selection intent recorded by a bundle."""

    SUMMARY = "summary"
    EXACT = "exact"
    NUMERIC = "numeric"
    VISUAL = "visual"
    VERIFICATION = "verification"
    MIXED = "mixed"


class BudgetUnit(StrEnum):
    """Unit used by a context budget estimator."""

    TOKENS = "tokens"
    CHARACTERS = "characters"
    BYTES = "bytes"


class EvidenceRepresentation(StrEnum):
    """Representation level included or reported missing in a bundle."""

    METADATA = "metadata"
    OUTLINE = "outline"
    SUMMARY = "summary"
    EXACT = "exact"
    STRUCTURED = "structured"
    VISUAL_HANDLE = "visual_handle"
    ORIGINAL_HANDLE = "original_handle"


class ContextBudget(DomainModel):
    """Declared bound and observed estimator usage for a context bundle."""

    unit: BudgetUnit
    limit: int = Field(ge=1)
    estimated_used: int = Field(ge=0)
    estimator: NonEmptyStr
    actual_used: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _estimate_does_not_exceed_limit(self) -> ContextBudget:
        if self.estimated_used > self.limit:
            raise ValueError("context budget estimated_used exceeds limit")
        return self


class VersionScope(DomainModel):
    """One exact logical document, source and representation revision."""

    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id


class EvidenceProvenance(DomainModel):
    """Exact source-backed provenance for one selected block."""

    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id
    block_id: CanonicalUuid
    source: SourceLocator


class EvidenceItem(ExtensibleModel):
    """One selected evidence representation and its trust boundary."""

    provenance: EvidenceProvenance
    representation: EvidenceRepresentation
    content: JsonValue | None = None
    artifact_handle: NonEmptyStr | None = None
    artifact_id: Sha256Id | None = None
    reason: NonEmptyStr
    trust: DataTrustClassification

    @field_validator("content", mode="before")
    @classmethod
    def _content_is_json(cls, value: object) -> object:
        return ensure_json_value(value, path="$.content")

    @model_validator(mode="after")
    def _payload_matches_representation(self) -> EvidenceItem:
        if self.content is None and self.artifact_handle is None:
            raise ValueError("evidence item requires content or an artifact handle")
        if (
            self.representation
            in {
                EvidenceRepresentation.VISUAL_HANDLE,
                EvidenceRepresentation.ORIGINAL_HANDLE,
            }
            and self.artifact_handle is None
        ):
            raise ValueError("visual/original evidence requires an artifact handle")
        if self.representation is EvidenceRepresentation.SUMMARY and self.artifact_id is None:
            raise ValueError("summary evidence requires an artifact_id")
        return self


class SelectionDecision(ExtensibleModel):
    """Auditable context-selection decision."""

    stage: NonEmptyStr
    decision: NonEmptyStr
    reason: NonEmptyStr
    subject_id: NonEmptyStr | None = None


class BundleNotice(ExtensibleModel):
    """Stable warning code and human-readable bundle message."""

    code: NonEmptyStr
    message: NonEmptyStr


class MissingEvidence(ExtensibleModel):
    """Evidence requirement that could not be satisfied honestly."""

    evidence_type: EvidenceRepresentation
    reason: NonEmptyStr
    scope: VersionScope | None = None


class ContextBundle(ExtensibleModel):
    """Immutable audit record of selected, version-pinned evidence."""

    schema_version: SupportedSchemaVersion
    bundle_id: CanonicalUuid
    created_at: UtcDatetime
    query: NonEmptyStr
    mode: ContextMode
    budget: ContextBudget
    versions: tuple[VersionScope, ...] = Field(min_length=1)
    items: tuple[EvidenceItem, ...] = ()
    selection_trace: tuple[SelectionDecision, ...] = ()
    warnings: tuple[BundleNotice, ...] = ()
    missing_evidence: tuple[MissingEvidence, ...] = ()

    @model_validator(mode="after")
    def _scopes_items_and_missing_evidence_are_consistent(self) -> ContextBundle:
        scope_keys = [
            (str(scope.document_id), scope.version_id, scope.representation_id)
            for scope in self.versions
        ]
        if len(set(scope_keys)) != len(scope_keys):
            raise ValueError("context versions must contain unique exact scopes")
        pinned = set(scope_keys)
        item_keys: set[tuple[str, str, str, str, str, str | None]] = set()
        for item in self.items:
            provenance = item.provenance
            scope_key = (
                str(provenance.document_id),
                provenance.version_id,
                provenance.representation_id,
            )
            if scope_key not in pinned:
                raise ValueError("evidence item scope is not pinned by context versions")
            item_key = (
                *scope_key,
                str(provenance.block_id),
                item.representation.value,
                item.artifact_id,
            )
            if item_key in item_keys:
                raise ValueError("context bundle contains duplicate evidence items")
            item_keys.add(item_key)
        if not self.items and not self.missing_evidence:
            raise ValueError("empty context items require missing_evidence")
        return self
