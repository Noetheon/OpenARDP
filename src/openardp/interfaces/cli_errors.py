"""Stable body-free CLI failure classification with fixed actionable hints.

Every failure maps to one exit code, one stable machine code and one fixed message. An
optional hint names the next useful operator action. Hints are fixed strings chosen by
exception class only; they never echo paths, document text or other caller input.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from openardp.adapters.local_source import (
    InvalidSourcePath,
    SourceNotFound,
    SourceTooLarge,
)
from openardp.adapters.local_workspace import WorkspaceError, WorkspaceMissing
from openardp.domain.common import SCHEMA_VERSION
from openardp.domain.release import EvidenceMalformed, ReleaseEvidenceError
from openardp.domain.search import SearchQueryRejected
from openardp.interfaces.cli_arguments import ContextCommandUsageError
from openardp.interfaces.cli_output import write_json
from openardp.ports.agent import AgentDocumentAmbiguous, AgentDocumentNotFound
from openardp.ports.catalog import (
    AmbiguousBlock,
    BlockNotFound,
    CatalogError,
    CatalogIncompatible,
    CatalogTooNew,
    DocumentNotFound,
    InvalidJobTransition,
    JobConflict,
    JobNotFound,
    LeaseConflict,
    RepresentationBusy,
    RepresentationConflict,
    RepresentationIntegrityError,
    RepresentationLeaseConflict,
    RepresentationNotFound,
    SearchCapabilityUnavailable,
    SearchIndexDrifted,
    SearchIndexIncomplete,
)
from openardp.ports.context import (
    ContextCompilationCancelled,
    ContextConfigurationMismatch,
    ContextIntegrityFailure,
    ContextLimitExceeded,
    ContextNotFound,
)
from openardp.ports.interchange import (
    InterchangeDestinationConflict,
    InterchangeError,
    InterchangeIntegrityInvalid,
    InterchangePolicyRejected,
    InterchangePublicationFailed,
    InterchangeRelationshipInvalid,
    InterchangeResourceExceeded,
    InterchangeSourceChanged,
    MalformedPackage,
    UnsupportedInterchangeVersion,
)
from openardp.ports.maintenance import MaintenanceError
from openardp.ports.object_store import ObjectStoreError
from openardp.ports.parser import (
    ParserError,
    ParserProcessCrashed,
    ParserTimedOut,
    RichParserDependencyUnavailable,
    RichParserMalformedDocument,
    RichParserModelAssetsInvalid,
    RichParserModelAssetsRequired,
    RichParserResourceLimitExceeded,
    TextDecodingError,
    UnsupportedRichMedia,
    UnsupportedTextMedia,
)
from openardp.ports.release import ReleaseEvidenceStoreError
from openardp.ports.semantic_retrieval import SemanticRetrievalFailure
from openardp.ports.visual import (
    UnsupportedVisualMedia,
    VisualConflict,
    VisualDependencyUnavailable,
    VisualIntegrityError,
    VisualResourceLimitExceeded,
    VisualTargetUnavailable,
)
from openardp.ports.watcher import (
    WatchRootInvalid,
    WatchRootOverlap,
    WatchRootUnsupported,
)
from openardp.services.bulk_ingest import SourcePathMissing
from openardp.services.release_benchmarks import ReleaseCorpusMalformed

SUPPORTED_TYPES_HINT = "Supported file types: .txt .md .markdown .csv .pdf .docx .pptx"

# Ordered most-specific first; the first matching class supplies the fixed hint.
_HINTS: tuple[tuple[type[BaseException], str], ...] = (
    (ContextCommandUsageError, "Run `openardp <command> --help` for the expected arguments."),
    (
        RichParserModelAssetsRequired,
        "PDF parsing needs the verified offline model bundle: pass --docling-model-root and "
        "--docling-model-manifest (see docs/22_OFFLINE_PDF_MODEL_BUNDLE.md). "
        "DOCX and PPTX work without it.",
    ),
    (
        RichParserModelAssetsInvalid,
        "The PDF model bundle failed verification; re-install it as described in "
        "docs/22_OFFLINE_PDF_MODEL_BUNDLE.md.",
    ),
    (
        RichParserDependencyUnavailable,
        "Rich document parsing needs the optional extra: uv sync --extra docling",
    ),
    (
        ParserProcessCrashed,
        "The isolated parser process crashed. Retry once; if it persists, the document "
        "may exceed the parser memory limit.",
    ),
    (ParserTimedOut, "Parsing exceeded the time limit; split very large documents."),
    (
        RichParserResourceLimitExceeded,
        "The document exceeds a parser limit (size, pages or memory).",
    ),
    (
        RichParserMalformedDocument,
        "The file could not be parsed; it may be corrupt or password-protected.",
    ),
    (TextDecodingError, "Text files must be UTF-8 encoded."),
    (UnsupportedTextMedia, SUPPORTED_TYPES_HINT),
    (UnsupportedRichMedia, SUPPORTED_TYPES_HINT),
    (SourceNotFound, "Check that the file exists and is readable."),
    (SourcePathMissing, "Check the path: this file or folder does not exist."),
    (SourceTooLarge, "The file exceeds the supported source size."),
    (
        ContextLimitExceeded,
        "The budget is too small for the selected documents: raise --budget, select fewer "
        "documents, or use `openardp find` and `openardp read` for token-efficient access.",
    ),
    (
        SearchQueryRejected,
        'Use plain words or "quoted phrases"; `openardp find` accepts questions.',
    ),
    (
        WatchRootOverlap,
        "The watched folder and the workspace (--store) must not contain each other.",
    ),
    (WorkspaceMissing, "Create a workspace first: openardp init --store PATH"),
    (AgentDocumentAmbiguous, "Use the document ID shown by `openardp docs` instead of the name."),
    (AgentDocumentNotFound, "Run `openardp docs` to list the prepared documents."),
    (DocumentNotFound, "Run `openardp docs` to list the prepared documents."),
    (
        SearchIndexDrifted,
        "The disposable search index is out of date; run `openardp reindex`.",
    ),
    (
        SearchIndexIncomplete,
        "The disposable search index is incomplete; run `openardp reindex`.",
    ),
)


@dataclass(frozen=True, slots=True)
class FailureClass:
    """One stable classification of a CLI failure."""

    exit_code: int
    code: str
    message: str
    hint: str | None


def hint_for(error: BaseException) -> str | None:
    """Return the fixed actionable hint for one failure class, if any."""
    for error_type, hint in _HINTS:
        if isinstance(error, error_type):
            return hint
    return None


def classify(error: Exception) -> FailureClass:
    """Map any failure to its stable exit code, machine code, message and hint."""
    exit_code, code, message = _classification(error)
    return FailureClass(exit_code=exit_code, code=code, message=message, hint=hint_for(error))


def render_failure(command: str, error: Exception, *, json_output: bool) -> int:
    """Write one sanitized failure envelope and return its exit code."""
    failure = classify(error)
    if json_output:
        body: dict[str, object] = {"code": failure.code, "message": failure.message}
        if failure.hint is not None:
            body["hint"] = failure.hint
        write_json(
            {
                "command": command,
                "error": body,
                "ok": False,
                "schema_version": SCHEMA_VERSION,
            }
        )
    else:
        print(f"error[{failure.code}]: {failure.message}", file=sys.stderr)
        if failure.hint is not None:
            print(f"hint: {failure.hint}", file=sys.stderr)
    return failure.exit_code


def _classification(error: Exception) -> tuple[int, str, str]:
    if isinstance(error, ContextCommandUsageError):
        return 2, "invalid_usage", "command usage is invalid"
    if isinstance(error, ReleaseCorpusMalformed):
        return 4, "release_input_rejected", "release input was rejected"
    if isinstance(error, (ReleaseEvidenceStoreError, ReleaseEvidenceError, EvidenceMalformed)):
        return 6, "release_evidence_invalid", "release evidence is invalid or conflicts"
    interchange = _interchange_code(error)
    if interchange is not None:
        return 2, interchange, "interchange operation was rejected"
    if isinstance(error, MaintenanceError):
        return 5, "maintenance_rejected", "maintenance operation was rejected"
    if isinstance(error, AgentDocumentAmbiguous):
        return 5, "conflict", "document reference is ambiguous"
    if isinstance(error, (ContextNotFound, AgentDocumentNotFound)):
        return 3, "not_found", "requested evidence was not found"
    if isinstance(error, VisualTargetUnavailable):
        return 3, "not_found", "requested visual evidence was not found"
    if isinstance(error, ContextLimitExceeded):
        return 4, "rejected_input", "input was rejected"
    if isinstance(error, (ContextConfigurationMismatch, ContextCompilationCancelled)):
        return 5, "conflict", "operation conflicts with current state"
    if isinstance(error, SemanticRetrievalFailure):
        return 5, "semantic_provider_rejected", "semantic provider is unavailable or rejected"
    if isinstance(error, ContextIntegrityFailure):
        return 6, "integrity_or_workspace", "workspace or persisted evidence is invalid"
    return _general_classification(error)


def _interchange_code(error: Exception) -> str | None:
    interchange_codes: tuple[tuple[type[InterchangeError], str], ...] = (
        (UnsupportedInterchangeVersion, "unsupported_version"),
        (InterchangeResourceExceeded, "resource_exhausted"),
        (InterchangeIntegrityInvalid, "integrity_invalid"),
        (InterchangeRelationshipInvalid, "relationship_invalid"),
        (InterchangeSourceChanged, "source_changed"),
        (InterchangeDestinationConflict, "destination_conflict"),
        (InterchangePublicationFailed, "publication_failed"),
        (InterchangePolicyRejected, "policy_rejected"),
        (MalformedPackage, "malformed_package"),
    )
    for error_type, code in interchange_codes:
        if isinstance(error, error_type):
            return code
    return None


def _general_classification(error: Exception) -> tuple[int, str, str]:
    if isinstance(
        error,
        (
            SourceNotFound,
            SourcePathMissing,
            DocumentNotFound,
            RepresentationNotFound,
            BlockNotFound,
            JobNotFound,
        ),
    ):
        return 3, "not_found", "requested evidence was not found"
    if isinstance(
        error,
        (
            InvalidSourcePath,
            SourceTooLarge,
            UnsupportedTextMedia,
            ParserError,
            SearchQueryRejected,
            UnsupportedVisualMedia,
            VisualDependencyUnavailable,
            VisualResourceLimitExceeded,
            WatchRootInvalid,
            WatchRootOverlap,
            WatchRootUnsupported,
            ValueError,
        ),
    ):
        return 4, "rejected_input", "input was rejected"
    if isinstance(
        error,
        (
            RepresentationBusy,
            RepresentationConflict,
            RepresentationLeaseConflict,
            InvalidJobTransition,
            JobConflict,
            LeaseConflict,
            AmbiguousBlock,
            VisualConflict,
        ),
    ):
        return 5, "conflict", "operation conflicts with current state"
    if isinstance(
        error,
        (
            WorkspaceError,
            CatalogIncompatible,
            CatalogTooNew,
            RepresentationIntegrityError,
            SearchCapabilityUnavailable,
            SearchIndexIncomplete,
            SearchIndexDrifted,
            ObjectStoreError,
            CatalogError,
            VisualIntegrityError,
        ),
    ):
        return 6, "integrity_or_workspace", "workspace or persisted evidence is invalid"
    return 1, "unexpected_failure", "operation failed"


__all__ = [
    "SUPPORTED_TYPES_HINT",
    "FailureClass",
    "classify",
    "hint_for",
    "render_failure",
]
