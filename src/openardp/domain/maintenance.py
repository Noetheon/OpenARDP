"""Pure bounded retention, recovery and maintenance records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, JsonValue, StringConstraints, model_validator

from openardp.domain.common import CanonicalUuid, DomainModel, Sha256Id, UtcDatetime
from openardp.domain.identity import canonical_sha256

_MINIMUM_SECONDS = 86_400
_DEFAULT_GRACE_SECONDS = 604_800

ClosedReason = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$"),
]


class ObjectLocation(StrEnum):
    """One managed physical ownership location."""

    ACTIVE = "ACTIVE"
    QUARANTINE = "QUARANTINE"


class MaintenanceAnomalyCode(StrEnum):
    """Closed safe classification of unusable managed storage state."""

    MALFORMED_ENTRY = "MALFORMED_ENTRY"
    UNSAFE_ENTRY = "UNSAFE_ENTRY"
    CORRUPT_OBJECT = "CORRUPT_OBJECT"
    HARDLINKED_OBJECT = "HARDLINKED_OBJECT"
    STAGING_RESIDUE = "STAGING_RESIDUE"
    DUPLICATE_LOCATION = "DUPLICATE_LOCATION"
    DUPLICATE_PHYSICAL_FORM = "DUPLICATE_PHYSICAL_FORM"
    MISSING_QUARANTINE = "MISSING_QUARANTINE"


class InventoryLimits(DomainModel):
    """Trusted bounds for one complete maintenance enumeration."""

    max_entries: int = Field(ge=1, le=1_000_000)
    max_bytes: int = Field(ge=1, le=9_007_199_254_740_991)


class RetentionPolicy(DomainModel):
    """Conservative v0.1 retention and maintenance capacity policy."""

    profile: Literal["openardp-retention-v1"] = "openardp-retention-v1"
    candidate_min_age_seconds: int = Field(default=_MINIMUM_SECONDS, ge=_MINIMUM_SECONDS)
    quarantine_grace_seconds: int = Field(default=_DEFAULT_GRACE_SECONDS, ge=_MINIMUM_SECONDS)
    reserve_bytes: int = Field(default=64 * 1024 * 1024, ge=0)
    limits: InventoryLimits

    @property
    def policy_id(self) -> str:
        """Return the canonical identity of every semantic policy field."""
        return canonical_sha256(self.model_dump(mode="json"))


class MaintenanceObject(DomainModel):
    """Verified exact object metadata in one managed location."""

    object_id: Sha256Id
    byte_length: int = Field(ge=0)
    modified_at: UtcDatetime
    location: ObjectLocation
    physical_profile: Literal["ordinary", "openardp-deflate-dict-v1"] = "ordinary"


class MaintenanceAnomaly(DomainModel):
    """Body- and path-free managed storage inconsistency."""

    code: MaintenanceAnomalyCode
    location_digest: Sha256Id
    object_id: Sha256Id | None = None


class MaintenanceInventory(DomainModel):
    """One complete bounded active/quarantine storage observation."""

    profile: Literal["openardp-maintenance-inventory-v1"] = "openardp-maintenance-inventory-v1"
    active: tuple[MaintenanceObject, ...]
    quarantined: tuple[MaintenanceObject, ...]
    anomalies: tuple[MaintenanceAnomaly, ...]
    scanned_entries: int = Field(ge=0)
    scanned_bytes: int = Field(ge=0)

    @model_validator(mode="after")
    def _entries_are_canonical(self) -> MaintenanceInventory:
        for field, entries, location in (
            ("active", self.active, ObjectLocation.ACTIVE),
            ("quarantined", self.quarantined, ObjectLocation.QUARANTINE),
        ):
            identifiers = tuple(item.object_id for item in entries)
            if identifiers != tuple(sorted(set(identifiers))):
                raise ValueError(f"{field} objects must be sorted and unique")
            if any(item.location is not location for item in entries):
                raise ValueError(f"{field} objects have inconsistent locations")
        anomaly_keys = tuple(
            (item.location_digest, item.code.value, item.object_id or "") for item in self.anomalies
        )
        if anomaly_keys != tuple(sorted(set(anomaly_keys))):
            raise ValueError("inventory anomalies must be sorted and unique")
        if self.scanned_entries < len(self.active) + len(self.quarantined) + len(self.anomalies):
            raise ValueError("scanned entry count is incomplete")
        if self.scanned_bytes < sum(item.byte_length for item in (*self.active, *self.quarantined)):
            raise ValueError("scanned byte count is incomplete")
        return self

    @property
    def inventory_id(self) -> str:
        """Return a canonical identity over exact semantic inventory facts."""
        return canonical_sha256(self.model_dump(mode="json"))


class RootReason(StrEnum):
    """Closed delivered catalog reference families."""

    SOURCE_VERSION = "source_version"
    VERSION_REFERENCE = "version_reference"
    JOB_REFERENCE = "job_reference"
    TEXT_MANIFEST = "text_manifest"
    TEXT_NATIVE = "text_native"
    TEXT_BLOCK = "text_block"
    RICH_DESCRIPTOR = "rich_descriptor"
    RICH_NATIVE = "rich_native"
    RICH_RECORD = "rich_record"
    RICH_EVIDENCE_BUNDLE = "rich_evidence_bundle"
    RICH_REFERENCE = "rich_reference"
    RICH_PROJECTION = "rich_projection"
    RICH_RETRIEVAL = "rich_retrieval"
    CONTEXT_RECEIPT = "context_receipt"
    CONTEXT_BUNDLE = "context_bundle"
    RECONCILIATION_RELATION = "reconciliation_relation"
    DERIVATION_RECORD = "derivation_record"
    DERIVATION_OUTPUT = "derivation_output"
    VISUAL_RASTER_RECORD = "visual_raster_record"
    VISUAL_RASTER = "visual_raster"
    VISUAL_DESCRIPTOR = "visual_descriptor"
    VISUAL_CROP = "visual_crop"


class RetentionRoot(DomainModel):
    """One explainable catalog edge protecting an exact object."""

    object_id: Sha256Id
    reason: RootReason
    reference_digest: Sha256Id


class RetentionHold(DomainModel):
    """Explicit operator protection for one object identity."""

    hold_id: Sha256Id
    object_id: Sha256Id
    reason: ClosedReason
    created_at: UtcDatetime
    expires_at: UtcDatetime | None = None
    released_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _times_are_ordered(self) -> RetentionHold:
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("hold expiry must follow creation")
        if self.released_at is not None and self.released_at < self.created_at:
            raise ValueError("hold release must not precede creation")
        return self

    def active_at(self, instant: datetime) -> bool:
        """Return whether this hold protects its object at one UTC instant."""
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("instant must be timezone-aware UTC")
        return self.released_at is None and (self.expires_at is None or self.expires_at > instant)


class RetentionSnapshot(DomainModel):
    """One transactional catalog root and hold observation."""

    catalog_schema_version: int = Field(ge=1)
    roots: tuple[RetentionRoot, ...]
    holds: tuple[RetentionHold, ...]
    observed_at: UtcDatetime

    @model_validator(mode="after")
    def _facts_are_canonical(self) -> RetentionSnapshot:
        root_keys = tuple(
            (item.object_id, item.reason.value, item.reference_digest) for item in self.roots
        )
        if root_keys != tuple(sorted(set(root_keys))):
            raise ValueError("retention roots must be sorted and unique")
        hold_keys = tuple((item.object_id, item.hold_id) for item in self.holds)
        if hold_keys != tuple(sorted(set(hold_keys))):
            raise ValueError("retention holds must be sorted and unique")
        return self

    @property
    def root_snapshot_id(self) -> str:
        """Identify exact schema and root edges independently of observation time."""
        return canonical_sha256(
            {
                "catalog_schema_version": self.catalog_schema_version,
                "roots": [item.model_dump(mode="json") for item in self.roots],
            }
        )

    @property
    def hold_snapshot_id(self) -> str:
        """Identify exact active holds independently of observation time."""
        return canonical_sha256({"holds": [item.model_dump(mode="json") for item in self.holds]})


class ReclamationCandidate(DomainModel):
    """One verified unreferenced object selected by a closed policy reason."""

    item: MaintenanceObject
    reason: ClosedReason

    @model_validator(mode="after")
    def _is_active(self) -> ReclamationCandidate:
        if self.item.location is not ObjectLocation.ACTIVE:
            raise ValueError("reclamation candidate must be active")
        return self


class RetentionClassification(StrEnum):
    """Closed explanation result for one verified object."""

    PROTECTED = "PROTECTED"
    CANDIDATE = "CANDIDATE"
    QUARANTINED = "QUARANTINED"


class RetentionExplanation(DomainModel):
    """Body-free reasons for one exact object classification."""

    object_id: Sha256Id
    byte_length: int = Field(ge=0)
    classification: RetentionClassification
    reasons: tuple[ClosedReason, ...]

    @model_validator(mode="after")
    def _reasons_are_canonical(self) -> RetentionExplanation:
        if not self.reasons or self.reasons != tuple(sorted(set(self.reasons))):
            raise ValueError("retention reasons must be sorted and unique")
        return self


class RetentionInventoryReport(DomainModel):
    """Bounded explainable retention projection without paths or bodies."""

    observed_at: UtcDatetime
    catalog_schema_version: int = Field(ge=1)
    root_snapshot_id: Sha256Id
    hold_snapshot_id: Sha256Id
    inventory_id: Sha256Id
    explanations: tuple[RetentionExplanation, ...]
    anomalies: tuple[MaintenanceAnomaly, ...]

    @model_validator(mode="after")
    def _explanations_are_canonical(self) -> RetentionInventoryReport:
        identifiers = tuple(item.object_id for item in self.explanations)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("retention explanations must be sorted and unique")
        return self


class ReclamationPlan(DomainModel):
    """Immutable exact dry-run value required by quarantine."""

    profile: Literal["openardp-reclamation-plan-v1"] = "openardp-reclamation-plan-v1"
    plan_id: Sha256Id
    policy: RetentionPolicy
    catalog_schema_version: int = Field(ge=1)
    root_snapshot_id: Sha256Id
    hold_snapshot_id: Sha256Id
    inventory_id: Sha256Id
    candidates: tuple[ReclamationCandidate, ...]
    observed_at: UtcDatetime

    @model_validator(mode="after")
    def _identity_and_order_are_canonical(self) -> ReclamationPlan:
        identifiers = tuple(item.item.object_id for item in self.candidates)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("reclamation candidates must be sorted and unique")
        if self.plan_id != canonical_sha256(self._identity_payload()):
            raise ValueError("plan identity does not match semantic facts")
        return self

    def _identity_payload(self) -> dict[str, JsonValue]:
        return {
            "profile": self.profile,
            "policy": self.policy.model_dump(mode="json"),
            "catalog_schema_version": self.catalog_schema_version,
            "root_snapshot_id": self.root_snapshot_id,
            "hold_snapshot_id": self.hold_snapshot_id,
            "inventory_id": self.inventory_id,
            "candidates": [item.model_dump(mode="json") for item in self.candidates],
        }

    @classmethod
    def create(
        cls,
        *,
        policy: RetentionPolicy,
        catalog_schema_version: int,
        root_snapshot_id: str,
        hold_snapshot_id: str,
        inventory: MaintenanceInventory,
        candidates: tuple[ReclamationCandidate, ...],
        observed_at: datetime,
    ) -> ReclamationPlan:
        """Build and identify one canonical plan from complete exact inputs."""
        candidate_list = tuple(sorted(candidates, key=lambda item: item.item.object_id))
        payload: dict[str, JsonValue] = {
            "profile": "openardp-reclamation-plan-v1",
            "policy": policy.model_dump(mode="json"),
            "catalog_schema_version": catalog_schema_version,
            "root_snapshot_id": root_snapshot_id,
            "hold_snapshot_id": hold_snapshot_id,
            "inventory_id": inventory.inventory_id,
            "candidates": [item.model_dump(mode="json") for item in candidate_list],
        }
        return cls(
            plan_id=canonical_sha256(payload),
            policy=policy,
            catalog_schema_version=catalog_schema_version,
            root_snapshot_id=root_snapshot_id,
            hold_snapshot_id=hold_snapshot_id,
            inventory_id=inventory.inventory_id,
            candidates=candidate_list,
            observed_at=observed_at,
        )


class MaintenanceAction(StrEnum):
    """Closed exact filesystem actions authorized by durable intent."""

    MOVE_TO_QUARANTINE = "MOVE_TO_QUARANTINE"
    MOVE_TO_ACTIVE = "MOVE_TO_ACTIVE"
    DELETE = "DELETE"
    RESTORE_CONFLICT = "RESTORE_CONFLICT"
    COPY = "COPY"


class MaintenanceOperationKind(StrEnum):
    """Closed maintenance operation families."""

    QUARANTINE = "QUARANTINE"
    RESTORE = "RESTORE"
    COMMIT = "COMMIT"
    BACKUP = "BACKUP"
    MIGRATE = "MIGRATE"
    INDEX_REBUILD = "INDEX_REBUILD"
    STORAGE_OPTIMIZE = "STORAGE_OPTIMIZE"


class MaintenanceOperationState(StrEnum):
    """Durable cross-resource operation lifecycle."""

    PREPARED = "PREPARED"
    APPLYING = "APPLYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class QuarantineBatchState(StrEnum):
    """Durable reversible batch lifecycle."""

    PREPARED = "PREPARED"
    QUARANTINED = "QUARANTINED"
    PARTIALLY_RESTORED = "PARTIALLY_RESTORED"
    RESTORED = "RESTORED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    BLOCKED = "BLOCKED"


class QuarantineEntryState(StrEnum):
    """Durable exact-object quarantine lifecycle."""

    PLANNED = "PLANNED"
    QUARANTINED = "QUARANTINED"
    RESTORED = "RESTORED"
    COMMITTED_REMOVED = "COMMITTED_REMOVED"
    CONFLICT_RETAINED = "CONFLICT_RETAINED"


class MaintenanceOperationEntry(DomainModel):
    """One exact ordered action persisted before filesystem mutation."""

    sequence: int = Field(ge=1)
    object_id: Sha256Id
    byte_length: int = Field(ge=0)
    action: MaintenanceAction
    source_state: Literal["ACTIVE", "QUARANTINE", "NONE"]
    destination_state: Literal["ACTIVE", "QUARANTINE", "NONE"]
    outcome: Literal["MOVED", "REMOVED", "RETAINED", "COPIED"] | None = None


class MaintenanceOperation(DomainModel):
    """Complete durable cross-resource intent and current lifecycle."""

    operation_id: CanonicalUuid
    kind: MaintenanceOperationKind
    subject_id: Sha256Id
    state: MaintenanceOperationState
    acknowledgement_digest: Sha256Id | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    terminal_at: UtcDatetime | None = None
    failure_code: ClosedReason | None = None
    entries: tuple[MaintenanceOperationEntry, ...]

    @model_validator(mode="after")
    def _operation_is_consistent(self) -> MaintenanceOperation:
        sequences = tuple(item.sequence for item in self.entries)
        if sequences != tuple(range(1, len(self.entries) + 1)):
            raise ValueError("maintenance entries must have contiguous sequence")
        if self.updated_at < self.created_at:
            raise ValueError("operation update must not precede creation")
        active = self.state in {
            MaintenanceOperationState.PREPARED,
            MaintenanceOperationState.APPLYING,
        }
        if active == (self.terminal_at is not None):
            raise ValueError("operation terminal time is inconsistent")
        return self


class QuarantineEntry(DomainModel):
    """One exact object's reversible/terminal quarantine history."""

    object_id: Sha256Id
    byte_length: int = Field(ge=0)
    reason: ClosedReason
    state: QuarantineEntryState
    quarantined_at: UtcDatetime | None = None
    restored_at: UtcDatetime | None = None
    committed_at: UtcDatetime | None = None


class QuarantineBatch(DomainModel):
    """Named durable batch created from one exact reclamation plan."""

    batch_id: CanonicalUuid
    plan_id: Sha256Id
    policy_id: Sha256Id
    root_snapshot_id: Sha256Id
    inventory_id: Sha256Id
    state: QuarantineBatchState
    quarantined_at: UtcDatetime
    not_before: UtcDatetime
    entry_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    terminal_at: UtcDatetime | None = None
    entries: tuple[QuarantineEntry, ...]

    @model_validator(mode="after")
    def _batch_is_consistent(self) -> QuarantineBatch:
        identifiers = tuple(item.object_id for item in self.entries)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("quarantine entries must be sorted and unique")
        if self.entry_count != len(self.entries):
            raise ValueError("quarantine entry count does not match entries")
        if self.byte_count != sum(item.byte_length for item in self.entries):
            raise ValueError("quarantine byte count does not match entries")
        if self.not_before < self.quarantined_at:
            raise ValueError("quarantine grace must not precede batch creation")
        return self


class BackupFile(DomainModel):
    """One exact regular file allowlisted by an internal backup manifest."""

    relative_path: Annotated[
        str,
        StringConstraints(strict=True, min_length=1, max_length=4096, pattern=r"^[^\\]+$"),
    ]
    byte_length: int = Field(ge=0)
    sha256: Sha256Id

    @model_validator(mode="after")
    def _path_is_safe(self) -> BackupFile:
        parts = self.relative_path.split("/")
        if (
            self.relative_path.startswith("/")
            or any(part in {"", ".", ".."} for part in parts)
            or any(":" in part or any(ord(character) < 32 for character in part) for part in parts)
        ):
            raise ValueError("backup path must be a safe relative POSIX path")
        return self


class BackupManifest(DomainModel):
    """Canonical internal recovery inventory, not a portable export contract."""

    profile: Literal["openardp-backup-v1"] = "openardp-backup-v1"
    manifest_id: Sha256Id
    created_at: UtcDatetime
    catalog_schema_version: int = Field(ge=1)
    migration_checksums: tuple[Sha256Id, ...]
    files: tuple[BackupFile, ...]
    active_object_ids: tuple[Sha256Id, ...]
    quarantined_object_ids: tuple[Sha256Id, ...]
    excluded_staging_count: int = Field(ge=0)
    lexical_index_excluded: Literal[True] = True

    @model_validator(mode="after")
    def _manifest_is_canonical(self) -> BackupManifest:
        paths = tuple(item.relative_path for item in self.files)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("backup files must be sorted and unique")
        for field, identifiers in (
            ("active", self.active_object_ids),
            ("quarantined", self.quarantined_object_ids),
        ):
            if identifiers != tuple(sorted(set(identifiers))):
                raise ValueError(f"{field} backup objects must be sorted and unique")
        payload = self.model_dump(mode="json", exclude={"manifest_id"})
        if self.manifest_id != canonical_sha256(payload):
            raise ValueError("backup manifest identity does not match exact facts")
        return self

    @classmethod
    def create(
        cls,
        *,
        created_at: datetime,
        catalog_schema_version: int,
        migration_checksums: tuple[str, ...],
        files: tuple[BackupFile, ...],
        active_object_ids: tuple[str, ...],
        quarantined_object_ids: tuple[str, ...],
        excluded_staging_count: int,
    ) -> BackupManifest:
        """Sort and identify one complete verified internal manifest."""
        sorted_files = tuple(sorted(files, key=lambda item: item.relative_path))
        sorted_active = tuple(sorted(active_object_ids))
        sorted_quarantined = tuple(sorted(quarantined_object_ids))
        payload: dict[str, JsonValue] = {
            "profile": "openardp-backup-v1",
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
            "catalog_schema_version": catalog_schema_version,
            "migration_checksums": list(migration_checksums),
            "files": [item.model_dump(mode="json") for item in sorted_files],
            "active_object_ids": list(sorted_active),
            "quarantined_object_ids": list(sorted_quarantined),
            "excluded_staging_count": excluded_staging_count,
            "lexical_index_excluded": True,
        }
        return cls(
            manifest_id=canonical_sha256(payload),
            created_at=created_at,
            catalog_schema_version=catalog_schema_version,
            migration_checksums=migration_checksums,
            files=sorted_files,
            active_object_ids=sorted_active,
            quarantined_object_ids=sorted_quarantined,
            excluded_staging_count=excluded_staging_count,
        )


class BackupReport(DomainModel):
    """Body-free proof of one complete published backup."""

    manifest_id: Sha256Id
    catalog_schema_version: int = Field(ge=1)
    file_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    active_object_count: int = Field(ge=0)
    quarantined_object_count: int = Field(ge=0)
    completed_at: UtcDatetime


class RestoreReport(DomainModel):
    """Body-free proof of a complete fresh restore publication."""

    manifest_id: Sha256Id
    catalog_schema_version: int = Field(ge=1)
    file_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    completed_at: UtcDatetime


class StorageHealth(StrEnum):
    """Closed local capacity and integrity state."""

    HEALTHY = "HEALTHY"
    LOW_SPACE = "LOW_SPACE"
    INCONSISTENT = "INCONSISTENT"
    UNAVAILABLE = "UNAVAILABLE"


class StorageCategory(DomainModel):
    """Exact logical count and byte total for one closed storage category."""

    name: Literal["active", "catalog", "disposable_index", "quarantine", "staging"]
    count: int = Field(ge=0)
    byte_count: int = Field(ge=0)


class CapacityReport(DomainModel):
    """Point-in-time admission result for known bytes plus configured reserve."""

    required_bytes: int = Field(ge=0)
    reserve_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    admitted: bool

    @model_validator(mode="after")
    def _admission_matches_numbers(self) -> CapacityReport:
        if self.admitted != (self.free_bytes >= self.required_bytes + self.reserve_bytes):
            raise ValueError("capacity admission does not match exact byte facts")
        return self


class StorageDiagnostic(DomainModel):
    """Body-free exact logical usage plus current local filesystem capacity."""

    observed_at: UtcDatetime
    categories: tuple[StorageCategory, ...]
    disk_total_bytes: int = Field(ge=0)
    disk_free_bytes: int = Field(ge=0)
    reserve_bytes: int = Field(ge=0)
    health: StorageHealth

    @model_validator(mode="after")
    def _categories_are_canonical(self) -> StorageDiagnostic:
        names = tuple(item.name for item in self.categories)
        if names != tuple(sorted(set(names))):
            raise ValueError("storage categories must be sorted and unique")
        return self


class StorageOptimizationOutcome(StrEnum):
    """Closed result for one eligible derived block object."""

    COMPACTED = "compacted"
    ORDINARY_SMALLER = "ordinary_smaller"
    ALREADY_COMPACT = "already_compact"
    DUPLICATE_CONVERGED = "duplicate_converged"
    FAILED = "failed"


class StorageOptimizationItem(DomainModel):
    """Body- and path-free result for one logical object identity."""

    object_id: Sha256Id
    outcome: StorageOptimizationOutcome
    logical_bytes: int = Field(ge=0)
    stored_bytes_before: int = Field(ge=0)
    stored_bytes_after: int = Field(ge=0)
    reason_code: ClosedReason | None = None


class StorageOptimizationReport(DomainModel):
    """Deterministic aggregate from one explicit storage optimization run."""

    workspace_revision: int = Field(ge=1)
    items: tuple[StorageOptimizationItem, ...]
    catalog_bytes_before: int = Field(ge=0)
    catalog_bytes_after: int = Field(ge=0)

    @model_validator(mode="after")
    def _items_are_canonical(self) -> StorageOptimizationReport:
        identifiers = tuple(item.object_id for item in self.items)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("optimization items must be sorted and unique")
        return self

    @property
    def failed_count(self) -> int:
        """Return the number of safely retained failures."""
        return sum(item.outcome is StorageOptimizationOutcome.FAILED for item in self.items)

    @property
    def eligible_count(self) -> int:
        """Return the number of catalog-approved logical objects considered."""
        return len(self.items)

    @property
    def completed_count(self) -> int:
        """Return the number of objects that safely reached a terminal outcome."""
        return self.eligible_count - self.failed_count

    @property
    def stored_bytes_saved(self) -> int:
        """Return exact non-negative physical object bytes removed."""
        return sum(
            max(0, item.stored_bytes_before - item.stored_bytes_after) for item in self.items
        ) + max(0, self.catalog_bytes_before - self.catalog_bytes_after)


__all__ = [
    "BackupFile",
    "BackupManifest",
    "BackupReport",
    "CapacityReport",
    "ClosedReason",
    "InventoryLimits",
    "MaintenanceAction",
    "MaintenanceAnomaly",
    "MaintenanceAnomalyCode",
    "MaintenanceInventory",
    "MaintenanceObject",
    "MaintenanceOperation",
    "MaintenanceOperationEntry",
    "MaintenanceOperationKind",
    "MaintenanceOperationState",
    "ObjectLocation",
    "QuarantineBatch",
    "QuarantineBatchState",
    "QuarantineEntry",
    "QuarantineEntryState",
    "ReclamationCandidate",
    "ReclamationPlan",
    "RestoreReport",
    "RetentionClassification",
    "RetentionExplanation",
    "RetentionHold",
    "RetentionInventoryReport",
    "RetentionPolicy",
    "RetentionRoot",
    "RetentionSnapshot",
    "RootReason",
    "StorageCategory",
    "StorageDiagnostic",
    "StorageHealth",
    "StorageOptimizationItem",
    "StorageOptimizationOutcome",
    "StorageOptimizationReport",
]
