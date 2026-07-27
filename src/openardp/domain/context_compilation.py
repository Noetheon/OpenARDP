"""Deterministic bounded-context and privacy-conscious receipt contracts."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    BeforeValidator,
    Field,
    JsonValue,
    StringConstraints,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from openardp.domain.common import (
    MAX_SAFE_INTEGER,
    CanonicalUuid,
    DataTrustClassification,
    DocumentId,
    DomainModel,
    Sensitivity,
    Sha256Id,
    SourceLocator,
    TrustZone,
    UtcDatetime,
    ensure_json_value,
)
from openardp.domain.context import (
    BudgetUnit,
    ContextMode,
    EvidenceRepresentation,
    VersionScope,
)
from openardp.domain.identity import (
    context_bundle_id,
    context_compilation_fingerprint,
    context_policy_id,
    selection_receipt_id,
)
from openardp.domain.storage import StoredObject

CONTEXT_BUNDLE_SCHEMA_VERSION = "0.2.0"
SELECTION_RECEIPT_CONTRACT_VERSION = "0.1.0"
CONTEXT_COMPILATION_IDENTITY_VERSION: Literal[1] = 1
CONTEXT_ALGORITHM_NAME = "openardp.lexical-context"
CONTEXT_ALGORITHM_VERSION = "1.0.0"
RESPONSE_RESERVE_PERCENT: Literal[10] = 10
PROVENANCE_TARGET_PERCENT: Literal[10] = 10

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_ABSOLUTE_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_MACHINE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_EVIDENCE_ID = re.compile(
    r"^(?:sha256:[0-9a-f]{64}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})$"
)

BoundedName = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128),
]
SemanticVersion = Annotated[
    str,
    StringConstraints(strict=True, pattern=_SEMVER.pattern),
]
MachineCode = Annotated[
    str,
    StringConstraints(strict=True, pattern=_MACHINE_CODE.pattern),
]
EvidenceId = Annotated[
    str,
    StringConstraints(strict=True, pattern=_EVIDENCE_ID.pattern),
]
MediaType = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=3,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$",
    ),
]
ExtensionNamespace = Annotated[
    str,
    StringConstraints(strict=True, pattern=_ABSOLUTE_URI.pattern),
]


def _validate_exact_version(
    value: object,
    *,
    installed: str,
    kind: str,
) -> object:
    if not isinstance(value, str) or _SEMVER.fullmatch(value) is None:
        raise ValueError(f"{kind} version must be semantic version MAJOR.MINOR.PATCH")
    major = int(value.split(".", maxsplit=1)[0])
    if major != 0:
        raise ValueError(f"unsupported {kind} major {major}; supported major: 0")
    if value != installed:
        raise ValueError(f"{kind} version {value} is not installed; supported: {installed}")
    return value


def _validate_bundle_version(value: object) -> object:
    return _validate_exact_version(
        value,
        installed=CONTEXT_BUNDLE_SCHEMA_VERSION,
        kind="schema",
    )


def _validate_receipt_version(value: object) -> object:
    return _validate_exact_version(
        value,
        installed=SELECTION_RECEIPT_CONTRACT_VERSION,
        kind="contract",
    )


ContextBundleSchemaVersion = Annotated[
    str,
    BeforeValidator(_validate_bundle_version),
    StringConstraints(strict=True),
    WithJsonSchema(
        {"type": "string", "const": CONTEXT_BUNDLE_SCHEMA_VERSION},
        mode="validation",
    ),
]
SelectionReceiptContractVersion = Annotated[
    str,
    BeforeValidator(_validate_receipt_version),
    StringConstraints(strict=True),
    WithJsonSchema(
        {"type": "string", "const": SELECTION_RECEIPT_CONTRACT_VERSION},
        mode="validation",
    ),
]


class ContextContractModel(DomainModel):
    """Closed model with inert JSON under absolute-URI extension namespaces."""

    extensions: dict[ExtensionNamespace, JsonValue] = Field(default_factory=dict)

    @field_validator("extensions", mode="before")
    @classmethod
    def _extensions_are_namespaced_json(cls, value: object) -> object:
        ensure_json_value(value, path="$.extensions")
        if not isinstance(value, dict):
            raise ValueError("extensions must be a JSON object")
        for key in value:
            if _ABSOLUTE_URI.fullmatch(key) is None:
                raise ValueError("extension keys must be absolute URI namespace identifiers")
        return value


class ContextFreshnessPolicy(StrEnum):
    """Installed initial-compilation freshness policy."""

    CURRENT_ONLY = "current_only"


class CandidateFreshness(StrEnum):
    """Observed relationship between candidate scope and requested snapshot."""

    CURRENT = "current"
    HISTORICAL_EXACT = "historical_exact"
    STALE = "stale"


class SelectionOutcome(StrEnum):
    """Receipt inventory containing one discovered subject."""

    SELECTED = "selected"
    OMITTED = "omitted"
    REJECTED = "rejected"
    STALE = "stale"


class ContextCompileLimits(DomainModel):
    """Hard allocation and output bounds for one compiler invocation."""

    max_scopes: int = Field(default=32, strict=True, ge=1, le=32)
    max_discovered: int = Field(default=10_000, strict=True, ge=1, le=10_000)
    max_candidates: int = Field(default=512, strict=True, ge=1, le=512)
    max_body_bytes: int = Field(default=8 * 1024 * 1024, strict=True, ge=1024, le=8 * 1024 * 1024)
    max_decisions: int = Field(default=12_000, strict=True, ge=1, le=12_000)
    max_bundle_units: int = Field(
        default=16 * 1024 * 1024,
        strict=True,
        ge=1024,
        le=16 * 1024 * 1024,
    )

    @model_validator(mode="after")
    def _candidate_caps_are_nested(self) -> Self:
        if self.max_candidates > self.max_discovered:
            raise ValueError("max_candidates must not exceed max_discovered")
        if self.max_decisions < self.max_candidates:
            raise ValueError("max_decisions must cover max_candidates")
        return self


class EstimatorIdentity(DomainModel):
    """Exact replaceable budget estimator identity."""

    name: BoundedName
    version: SemanticVersion
    unit: BudgetUnit
    config_hash: Sha256Id

    @property
    def display_name(self) -> str:
        """Return a stable compact estimator identity for bundle metadata."""
        return f"{self.name}@{self.version}:{self.unit.value}:{self.config_hash}"


class AlgorithmIdentity(DomainModel):
    """Exact deterministic context algorithm identity."""

    name: BoundedName
    version: SemanticVersion
    config_hash: Sha256Id


class ContextSelectionPolicy(DomainModel):
    """Complete safe context selection policy recorded in each receipt."""

    mode: ContextMode
    required_evidence: tuple[EvidenceRepresentation, ...] = ()
    allowed_trust_zones: tuple[TrustZone, ...] = (TrustZone.EXTERNAL_UNTRUSTED,)
    maximum_sensitivity: Sensitivity = Sensitivity.INTERNAL
    freshness: Literal[ContextFreshnessPolicy.CURRENT_ONLY] = ContextFreshnessPolicy.CURRENT_ONLY
    include_history: Literal[False] = False
    response_reserve_percent: Literal[10] = RESPONSE_RESERVE_PERCENT
    provenance_target_percent: Literal[10] = PROVENANCE_TARGET_PERCENT

    @model_validator(mode="after")
    def _ordered_sets_are_canonical(self) -> Self:
        evidence = tuple(item.value for item in self.required_evidence)
        if evidence != tuple(sorted(set(evidence))):
            raise ValueError("required_evidence must be sorted and unique")
        zones = tuple(item.value for item in self.allowed_trust_zones)
        if not zones:
            raise ValueError("allowed_trust_zones must be non-empty")
        if zones != tuple(sorted(set(zones))):
            raise ValueError("allowed_trust_zones must be sorted and unique")
        return self


class ContextCompileRequest(DomainModel):
    """Validated task, exact corpus intent, budget and selection configuration."""

    task: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4096)]
    document_ids: tuple[DocumentId, ...] = Field(min_length=1, max_length=32)
    budget_limit: int = Field(strict=True, ge=1, le=16 * 1024 * 1024)
    estimator: EstimatorIdentity
    policy: ContextSelectionPolicy
    limits: ContextCompileLimits = Field(default_factory=ContextCompileLimits)

    @model_validator(mode="after")
    def _request_is_canonical_and_bounded(self) -> Self:
        identities = tuple(str(value) for value in self.document_ids)
        if identities != tuple(sorted(set(identities))):
            raise ValueError("document_ids must be sorted and unique")
        if len(identities) > self.limits.max_scopes:
            raise ValueError("document_ids exceed max_scopes")
        if self.budget_limit > self.limits.max_bundle_units:
            raise ValueError("budget_limit exceeds max_bundle_units")
        return self


class CorpusSnapshot(DomainModel):
    """One deterministic exact READY corpus snapshot."""

    scopes: tuple[VersionScope, ...] = Field(min_length=1, max_length=32)
    created_at: UtcDatetime

    @model_validator(mode="after")
    def _scopes_are_sorted_and_unique(self) -> Self:
        keys = tuple(_scope_key(scope) for scope in self.scopes)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("snapshot scopes must be sorted and unique")
        return self


class ContextBlockProvenance(DomainModel):
    """Exact F002 block-backed context provenance."""

    record_type: Literal["block"]
    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id
    block_id: CanonicalUuid
    source: SourceLocator


class ContextProjectionProvenance(DomainModel):
    """Exact F006 projection-backed context provenance without fabricated block identity."""

    record_type: Literal["evidence_projection"]
    document_id: DocumentId
    version_id: Sha256Id
    representation_id: Sha256Id
    source_version_id: Sha256Id
    native_representation_id: Sha256Id
    evidence_reference_id: Sha256Id
    evidence_projection_id: Sha256Id

    @model_validator(mode="after")
    def _source_version_matches_scope(self) -> Self:
        if self.version_id != self.source_version_id:
            raise ValueError("projection source_version_id must equal scope version_id")
        return self


ContextEvidenceProvenance = Annotated[
    ContextBlockProvenance | ContextProjectionProvenance,
    Field(discriminator="record_type"),
]


class ContextCandidate(DomainModel):
    """One verified body-bearing candidate before deterministic selection."""

    evidence_id: EvidenceId
    scope: VersionScope
    provenance: ContextEvidenceProvenance
    representation: EvidenceRepresentation
    source_order: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    body_object: StoredObject
    body_media_type: MediaType
    trust: DataTrustClassification
    freshness: CandidateFreshness
    term_coverage: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    occurrences: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    reason_code: MachineCode
    high_value: bool

    @model_validator(mode="after")
    def _identity_and_scope_match_provenance(self) -> Self:
        provenance = self.provenance
        if _scope_key(self.scope) != (
            str(provenance.document_id),
            provenance.version_id,
            provenance.representation_id,
        ):
            raise ValueError("candidate scope does not match provenance")
        expected = (
            str(provenance.block_id)
            if isinstance(provenance, ContextBlockProvenance)
            else provenance.evidence_projection_id
        )
        if self.evidence_id != expected:
            raise ValueError("candidate evidence_id does not match provenance")
        return self


class BudgetLedger(DomainModel):
    """Exact fixed-point context budget accounting."""

    unit: BudgetUnit
    limit: int = Field(strict=True, ge=1, le=16 * 1024 * 1024)
    response_reserved: int = Field(strict=True, ge=1)
    bundle_ceiling: int = Field(strict=True, ge=0)
    provenance_target: int = Field(strict=True, ge=1)
    base_bundle_used: int = Field(strict=True, ge=0)
    selected_incremental_used: int = Field(strict=True, ge=0)
    bundle_used: int = Field(strict=True, ge=0)
    remaining: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def _ledger_is_exact(self) -> Self:
        reserve = (self.limit + 9) // 10
        if self.response_reserved != reserve:
            raise ValueError("response_reserved must be ceil(limit / 10)")
        if self.provenance_target != reserve:
            raise ValueError("provenance_target must be ceil(limit / 10)")
        if self.bundle_ceiling != self.limit - reserve:
            raise ValueError("bundle_ceiling must equal limit minus response reserve")
        if self.bundle_used != self.base_bundle_used + self.selected_incremental_used:
            raise ValueError("bundle_used must equal base plus selected incremental usage")
        if self.bundle_used > self.bundle_ceiling:
            raise ValueError("bundle_used exceeds bundle_ceiling")
        if self.remaining != self.bundle_ceiling - self.bundle_used:
            raise ValueError("remaining does not match exact budget accounting")
        return self


class UntrustedContentEnvelope(DomainModel):
    """Structural data-only delimiter for one verified evidence body."""

    content_role: Literal["untrusted_data"] = "untrusted_data"
    delimiter: Literal["openardp-evidence-v1"] = "openardp-evidence-v1"
    media_type: MediaType
    body: JsonValue

    @field_validator("body", mode="before")
    @classmethod
    def _body_is_json(cls, value: object) -> object:
        return ensure_json_value(value, path="$.body")


class ContextEvidenceItem(ContextContractModel):
    """Selected exact evidence in a ContextBundle 0.2.0."""

    provenance: ContextEvidenceProvenance
    representation: EvidenceRepresentation
    content: UntrustedContentEnvelope | None = None
    artifact_handle: Annotated[str, StringConstraints(strict=True, min_length=1)] | None = None
    artifact_id: Sha256Id | None = None
    reason: MachineCode
    trust: DataTrustClassification

    @model_validator(mode="after")
    def _payload_matches_representation(self) -> Self:
        if self.content is None and self.artifact_handle is None:
            raise ValueError("context evidence requires content or artifact_handle")
        if (
            self.representation
            in {
                EvidenceRepresentation.VISUAL_HANDLE,
                EvidenceRepresentation.ORIGINAL_HANDLE,
            }
            and self.artifact_handle is None
        ):
            raise ValueError("visual/original evidence requires artifact_handle")
        if self.representation is EvidenceRepresentation.SUMMARY and self.artifact_id is None:
            raise ValueError("summary evidence requires artifact_id")
        return self


class ContextBundleBudget(DomainModel):
    """Declared bound and exact final estimator use for ContextBundle 0.2.0."""

    unit: BudgetUnit
    limit: int = Field(strict=True, ge=1, le=16 * 1024 * 1024)
    estimated_used: int = Field(strict=True, ge=0)
    estimator: EstimatorIdentity
    actual_used: int | None = Field(default=None, strict=True, ge=0)

    @model_validator(mode="after")
    def _usage_fits(self) -> Self:
        if self.estimated_used > self.limit:
            raise ValueError("context budget estimated_used exceeds limit")
        if self.actual_used is not None and self.actual_used != self.estimated_used:
            raise ValueError("actual_used must equal exact estimated_used when present")
        return self


class ContextSelectionTrace(ContextContractModel):
    """Compact body-free selected-stage fact embedded in the handoff."""

    evidence_id: EvidenceId
    final_order: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    reason_code: MachineCode


class ContextBundleNotice(ContextContractModel):
    """Stable warning code and bounded non-sensitive message."""

    code: MachineCode
    message: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=512)]


class ContextMissingEvidence(ContextContractModel):
    """Evidence requirement that could not be satisfied honestly."""

    evidence_type: EvidenceRepresentation
    reason_code: MachineCode
    scope: VersionScope | None = None


class ContextBundleV020(ContextContractModel):
    """Immutable deterministic context handoff with true block/projection provenance."""

    schema_version: ContextBundleSchemaVersion = CONTEXT_BUNDLE_SCHEMA_VERSION
    bundle_id: CanonicalUuid
    created_at: UtcDatetime
    query: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4096)]
    mode: ContextMode
    budget: ContextBundleBudget
    versions: tuple[VersionScope, ...] = Field(min_length=1, max_length=32)
    items: tuple[ContextEvidenceItem, ...] = ()
    selection_trace: tuple[ContextSelectionTrace, ...] = ()
    warnings: tuple[ContextBundleNotice, ...] = ()
    missing_evidence: tuple[ContextMissingEvidence, ...] = ()

    @model_validator(mode="after")
    def _aggregate_and_identity_are_consistent(self) -> Self:
        scope_keys = tuple(_scope_key(scope) for scope in self.versions)
        if scope_keys != tuple(sorted(set(scope_keys))):
            raise ValueError("context versions must be sorted and unique")
        pinned = set(scope_keys)
        evidence_keys: list[tuple[str, ...]] = []
        for item in self.items:
            provenance = item.provenance
            scope = (
                str(provenance.document_id),
                provenance.version_id,
                provenance.representation_id,
            )
            if scope not in pinned:
                raise ValueError("evidence item scope is not pinned by context versions")
            identity = (
                str(provenance.block_id)
                if isinstance(provenance, ContextBlockProvenance)
                else provenance.evidence_projection_id
            )
            evidence_keys.append(
                (*scope, provenance.record_type, identity, item.representation.value)
            )
        if len(evidence_keys) != len(set(evidence_keys)):
            raise ValueError("context bundle contains duplicate evidence items")
        for missing in self.missing_evidence:
            if missing.scope is not None and _scope_key(missing.scope) not in pinned:
                raise ValueError("missing evidence scope is not pinned by context versions")
        if not self.items and not self.missing_evidence:
            raise ValueError("empty context items require missing_evidence")
        if self.bundle_id.version != 5:
            raise ValueError("bundle_id must be UUIDv5")
        payload = self.model_dump(mode="json", exclude={"bundle_id"})
        if self.bundle_id != context_bundle_id(payload):
            raise ValueError("bundle_id does not match canonical identity")
        return self


class ReceiptDecision(ContextContractModel):
    """One body-free member of the exhaustive receipt decision partition."""

    outcome: SelectionOutcome
    evidence_id: EvidenceId
    scope: VersionScope
    representation: EvidenceRepresentation
    reason_code: MachineCode
    high_value: bool
    term_coverage: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    occurrences: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    source_order: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    estimated_cost: int = Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)
    final_order: int | None = Field(default=None, strict=True, ge=0, le=MAX_SAFE_INTEGER)

    @model_validator(mode="after")
    def _selected_order_is_unambiguous(self) -> Self:
        if self.outcome is SelectionOutcome.SELECTED and self.final_order is None:
            raise ValueError("selected decision requires final_order")
        if self.outcome is not SelectionOutcome.SELECTED and self.final_order is not None:
            raise ValueError("only selected decisions may have final_order")
        return self


class ReceiptNotice(ContextContractModel):
    """Stable body-free missing, escalation or coverage notice."""

    code: MachineCode
    subject_id: EvidenceId | None = None


class SelectionReceipt(ContextContractModel):
    """Deterministic body-free explanation of one context compilation."""

    contract_version: SelectionReceiptContractVersion = SELECTION_RECEIPT_CONTRACT_VERSION
    stability: Literal["experimental"] = "experimental"
    identity_version: Literal[1] = CONTEXT_COMPILATION_IDENTITY_VERSION
    receipt_id: Sha256Id
    created_at: UtcDatetime
    task_digest: Sha256Id
    algorithm: AlgorithmIdentity
    estimator: EstimatorIdentity
    policy: ContextSelectionPolicy
    policy_digest: Sha256Id
    corpus_snapshot: tuple[VersionScope, ...] = Field(min_length=1, max_length=32)
    budget: BudgetLedger
    selected: tuple[ReceiptDecision, ...] = ()
    omitted: tuple[ReceiptDecision, ...] = ()
    rejected: tuple[ReceiptDecision, ...] = ()
    stale: tuple[ReceiptDecision, ...] = ()
    truncated: bool
    notices: tuple[ReceiptNotice, ...] = ()

    @model_validator(mode="after")
    def _partition_budget_and_identities_are_exact(self) -> Self:
        scopes = tuple(_scope_key(scope) for scope in self.corpus_snapshot)
        if scopes != tuple(sorted(set(scopes))):
            raise ValueError("corpus_snapshot must be sorted and unique")
        inventories = (
            (SelectionOutcome.SELECTED, self.selected),
            (SelectionOutcome.OMITTED, self.omitted),
            (SelectionOutcome.REJECTED, self.rejected),
            (SelectionOutcome.STALE, self.stale),
        )
        subjects: list[tuple[str, ...]] = []
        for outcome, decisions in inventories:
            for decision in decisions:
                if decision.outcome is not outcome:
                    raise ValueError("decision outcome does not match its inventory")
                if _scope_key(decision.scope) not in set(scopes):
                    raise ValueError("decision scope is outside corpus_snapshot")
                subjects.append(
                    (
                        *_scope_key(decision.scope),
                        decision.evidence_id,
                        decision.representation.value,
                    )
                )
        if len(subjects) != len(set(subjects)):
            raise ValueError("decision inventories must be mutually exclusive")
        orders = tuple(item.final_order for item in self.selected)
        if orders != tuple(range(len(self.selected))):
            raise ValueError("selected final_order values must be contiguous")
        expected_policy = context_policy_digest(self.policy)
        if self.policy_digest != expected_policy:
            raise ValueError("policy_digest does not match canonical policy")
        if self.estimator.unit is not self.budget.unit:
            raise ValueError("receipt estimator unit does not match budget")
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != selection_receipt_id(payload):
            raise ValueError("receipt_id does not match canonical identity")
        return self


class ContextCompilationResult(DomainModel):
    """Pure compiler output before or after verified persistence."""

    bundle: ContextBundleV020
    receipt: SelectionReceipt

    @model_validator(mode="after")
    def _aggregate_matches(self) -> Self:
        if self.bundle.created_at != self.receipt.created_at:
            raise ValueError("bundle and receipt created_at values differ")
        if self.bundle.versions != self.receipt.corpus_snapshot:
            raise ValueError("bundle and receipt corpus scopes differ")
        if self.bundle.budget.estimator != self.receipt.estimator:
            raise ValueError("bundle and receipt estimator identities differ")
        if self.bundle.budget.estimated_used != self.receipt.budget.bundle_used:
            raise ValueError("bundle and receipt budget usage differs")
        return self


class ContextCompilationRecord(DomainModel):
    """Body-free immutable catalog projection for a persisted compilation."""

    receipt_id: Sha256Id
    receipt_object: StoredObject
    bundle_object: StoredObject
    bundle_id: CanonicalUuid
    task_digest: Sha256Id
    algorithm: AlgorithmIdentity
    estimator: EstimatorIdentity
    policy_digest: Sha256Id
    budget_limit: int = Field(strict=True, ge=1, le=16 * 1024 * 1024)
    budget_unit: BudgetUnit
    created_at: UtcDatetime
    selected_count: int = Field(strict=True, ge=0, le=12_000)
    omitted_count: int = Field(strict=True, ge=0, le=12_000)
    rejected_count: int = Field(strict=True, ge=0, le=12_000)
    stale_count: int = Field(strict=True, ge=0, le=12_000)
    row_fingerprint: Sha256Id

    @model_validator(mode="after")
    def _row_fingerprint_matches(self) -> Self:
        if self.receipt_id != self.receipt_object.object_id:
            raise ValueError("receipt_id must equal receipt object identity")
        if self.estimator.unit is not self.budget_unit:
            raise ValueError("estimator unit must equal budget_unit")
        if self.bundle_id.version != 5:
            raise ValueError("bundle_id must be UUIDv5")
        payload = self.model_dump(mode="json", exclude={"row_fingerprint"})
        if self.row_fingerprint != context_compilation_fingerprint(payload):
            raise ValueError("row_fingerprint does not match immutable row facts")
        return self


class ContextCompilationScope(DomainModel):
    """One ordered exact corpus scope linked to a persisted receipt."""

    receipt_id: Sha256Id
    ordinal: int = Field(strict=True, ge=0, le=31)
    scope: VersionScope


class ContextCompilationCommit(DomainModel):
    """Complete immutable row and ordered scope set requested for atomic commit."""

    record: ContextCompilationRecord
    scopes: tuple[ContextCompilationScope, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def _scopes_match_record_and_order(self) -> Self:
        if any(scope.receipt_id != self.record.receipt_id for scope in self.scopes):
            raise ValueError("compilation scopes must match record receipt_id")
        ordinals = tuple(scope.ordinal for scope in self.scopes)
        if ordinals != tuple(range(len(self.scopes))):
            raise ValueError("compilation scope ordinals must be contiguous")
        keys = tuple(_scope_key(item.scope) for item in self.scopes)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("compilation scopes must be sorted and unique")
        return self


def _scope_key(scope: VersionScope) -> tuple[str, str, str]:
    return (str(scope.document_id), scope.version_id, scope.representation_id)


def task_digest(task: str) -> str:
    """Hash exact untrusted task UTF-8 bytes without retaining the task."""
    return "sha256:" + hashlib.sha256(task.encode("utf-8")).hexdigest()


def context_policy_digest(policy: ContextSelectionPolicy) -> str:
    """Return the domain-separated identity of a complete policy."""
    return context_policy_id(policy.model_dump(mode="json"))
