"""Shared constants and closed record helpers for SQLite catalog modules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from openardp.domain.identity import canonical_sha256
from openardp.domain.maintenance import (
    RootReason,
)
from openardp.domain.storage import (
    ObjectReference,
)
from openardp.domain.watcher import (
    WatchEventType,
    WatchObservationState,
)

_WATCH_JOB_NAMESPACE = UUID("a2b64ef3-5813-57bb-a297-903183b34d6d")

_OWNER = re.compile(r"^.{1,255}$", re.DOTALL)
_MACHINE_TOKEN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_PDF_RENDER_PROFILE = re.compile(r"pdf-rgb-v1\+wheel-sha256:[0-9a-f]{64}")
_PNG_ENCODER_PROFILE = re.compile(r"png-rgb-v1\+wheel-sha256:[0-9a-f]{64}")
_MIN_LEASE_TOKEN_LENGTH = 16
_SCHEMA_TABLES = {
    1: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
        }
    ),
    2: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
        }
    ),
    3: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
            "document_representations",
            "representation_blocks",
            "document_heads",
            "ingestion_events",
        }
    ),
    4: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
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
        }
    ),
    5: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
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
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
        }
    ),
    6: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
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
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
            "context_compilations",
            "context_compilation_scopes",
        }
    ),
    7: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
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
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
            "context_compilations",
            "context_compilation_scopes",
            "reconciliation_runs",
            "block_lineages",
            "block_lineage_members",
            "reconciliation_relations",
            "derivation_slots",
            "derivation_nodes",
            "derivation_dependencies",
            "derivation_events",
        }
    ),
    8: frozenset(
        {
            "schema_migrations",
            "objects",
            "documents",
            "document_versions",
            "version_object_references",
            "jobs",
            "job_events",
            "job_object_references",
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
            "rich_parse_attempts",
            "rich_attempt_evidence",
            "rich_accepted_representations",
            "context_compilations",
            "context_compilation_scopes",
            "reconciliation_runs",
            "block_lineages",
            "block_lineage_members",
            "reconciliation_relations",
            "derivation_slots",
            "derivation_nodes",
            "derivation_dependencies",
            "derivation_events",
            "visual_page_rasters",
            "visual_evidence",
        }
    ),
}
_SCHEMA_TABLES[9] = _SCHEMA_TABLES[8] | frozenset(
    {"watch_roots", "watch_observations", "watch_job_targets", "watch_events"}
)
_SCHEMA_TABLES[10] = _SCHEMA_TABLES[9] | frozenset(
    {
        "retention_holds",
        "quarantine_batches",
        "quarantine_entries",
        "maintenance_operations",
        "maintenance_operation_entries",
        "maintenance_events",
        "migration_backups",
    }
)
_SCHEMA_TABLES[11] = _SCHEMA_TABLES[10] - frozenset({"block_search_entries"}) | frozenset(
    {"representation_scopes", "lineage_block_keys"}
)
_SCHEMA_VIEWS: dict[int, frozenset[str]] = {
    11: frozenset({"representation_block_projection"}),
}
_MAINTENANCE_NAMESPACE = UUID("a52173f8-2084-5c4e-9e2d-430e873fa415")
_STORAGE_OPTIMIZATION_SUBJECT = canonical_sha256({"profile": "openardp-storage-optimization-v1"})
_RETENTION_REFERENCES = (
    ("document_versions", "source_object_id", RootReason.SOURCE_VERSION),
    ("version_object_references", "object_id", RootReason.VERSION_REFERENCE),
    ("job_object_references", "object_id", RootReason.JOB_REFERENCE),
    ("document_representations", "manifest_object_id", RootReason.TEXT_MANIFEST),
    ("document_representations", "native_object_id", RootReason.TEXT_NATIVE),
    ("representation_blocks", "object_id", RootReason.TEXT_BLOCK),
    ("rich_parse_attempts", "descriptor_object_id", RootReason.RICH_DESCRIPTOR),
    ("rich_parse_attempts", "provider_native_object_id", RootReason.RICH_NATIVE),
    ("rich_parse_attempts", "native_record_object_id", RootReason.RICH_RECORD),
    ("rich_parse_attempts", "evidence_bundle_object_id", RootReason.RICH_EVIDENCE_BUNDLE),
    ("rich_attempt_evidence", "reference_object_id", RootReason.RICH_REFERENCE),
    ("rich_attempt_evidence", "projection_object_id", RootReason.RICH_PROJECTION),
    ("rich_attempt_evidence", "retrieval_object_id", RootReason.RICH_RETRIEVAL),
    ("context_compilations", "receipt_object_id", RootReason.CONTEXT_RECEIPT),
    ("context_compilations", "bundle_object_id", RootReason.CONTEXT_BUNDLE),
    ("reconciliation_relations", "relation_object_id", RootReason.RECONCILIATION_RELATION),
    ("derivation_nodes", "record_object_id", RootReason.DERIVATION_RECORD),
    ("derivation_nodes", "output_object_id", RootReason.DERIVATION_OUTPUT),
    ("visual_page_rasters", "raster_record_object_id", RootReason.VISUAL_RASTER_RECORD),
    ("visual_page_rasters", "raster_object_id", RootReason.VISUAL_RASTER),
    ("visual_evidence", "descriptor_object_id", RootReason.VISUAL_DESCRIPTOR),
    ("visual_evidence", "crop_object_id", RootReason.VISUAL_CROP),
)


def _canonical_references(
    references: tuple[ObjectReference, ...],
) -> tuple[ObjectReference, ...]:
    """Return references in their persisted canonical order."""
    return tuple(sorted(references, key=lambda item: (item.role, item.ordinal)))


@dataclass(frozen=True, slots=True)
class _WatchObservationTransition:
    """Pure next-state facts for one scanned watcher entry."""

    state: WatchObservationState
    first_observed_at: datetime
    stable_since: datetime | None
    last_scheduled_key: str | None
    revision: int
    event_type: WatchEventType | None


@dataclass(slots=True)
class _WatchScanProgress:
    """Mutable counters scoped to one enclosing SQLite transaction."""

    active_count: int
    candidate_count: int = 0
    stable_count: int = 0
    tombstone_count: int = 0
    backpressure: bool = False
    scheduled: list[UUID] = field(default_factory=list)


__all__ = [
    "_MACHINE_TOKEN",
    "_MAINTENANCE_NAMESPACE",
    "_MIN_LEASE_TOKEN_LENGTH",
    "_OWNER",
    "_PDF_RENDER_PROFILE",
    "_PNG_ENCODER_PROFILE",
    "_RETENTION_REFERENCES",
    "_SCHEMA_TABLES",
    "_SCHEMA_VIEWS",
    "_STORAGE_OPTIMIZATION_SUBJECT",
    "_WATCH_JOB_NAMESPACE",
    "_WatchObservationTransition",
    "_WatchScanProgress",
    "_canonical_references",
]
