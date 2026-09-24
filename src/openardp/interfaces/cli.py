"""Installable stable CLI composition root for local document intelligence."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO, cast

from openardp.adapters.bagit_interchange import LocalAssetSource
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.adapters.isolated_visual import IsolatedVisualRenderer
from openardp.adapters.local_source import (
    InvalidSourcePath,
    LocalSource,
    SourceChangedDuringSnapshot,
    SourceNotFound,
    SourceTooLarge,
)
from openardp.adapters.local_watch import LocalWatchScanner
from openardp.adapters.local_workspace import (
    LocalWorkspace,
    WorkspaceIncompatible,
)
from openardp.adapters.visual_policy import LocalOnlyVisualPolicy
from openardp.domain.context_compilation import (
    AlgorithmIdentity,
)
from openardp.domain.ingestion import RichMediaType, StatusMode, TextMediaType
from openardp.domain.maintenance import (
    InventoryLimits,
    RetentionPolicy,
)
from openardp.domain.storage import Job
from openardp.domain.watcher import WatchConfig, WatchCycleResult
from openardp.interfaces.agent_cli import execute_add, execute_agent_command, render_agent_result
from openardp.interfaces.agent_cli_arguments import AGENT_COMMANDS
from openardp.interfaces.agent_composition import local_agent_access
from openardp.interfaces.cli_arguments import ContextCommandUsageError as _UsageError
from openardp.interfaces.cli_arguments import parse_uuid as _parse_uuid
from openardp.interfaces.cli_arguments import parser as _parser
from openardp.interfaces.cli_errors import render_failure
from openardp.interfaces.cli_file_commands import (
    _interchange_limits,
    _load_model_manifest,
    _load_package_export_request,
    _load_reclamation_plan,
    _release_evidence,
    _release_gate,
    _release_report,
)
from openardp.interfaces.cli_output import (
    json_value as _json_value,  # noqa: F401 - retained test/adapter seam
)
from openardp.interfaces.cli_output import success as _success
from openardp.interfaces.context_cli import (
    compile_context_command,
)
from openardp.interfaces.context_cli import (
    context_summary as _context_summary,  # noqa: F401 - retained test/adapter seam
)
from openardp.interfaces.context_cli import (
    estimator_for as _estimator_for,
)
from openardp.interfaces.context_cli import (
    open_semantic_provider as _open_semantic_provider,
)
from openardp.interfaces.context_cli import (
    receipt_identity as _receipt_identity,
)
from openardp.interfaces.context_cli import (
    semantic_configuration as _semantic_configuration,
)
from openardp.interfaces.context_composition import (
    RetrievalProfile,
    local_context_compiler_for_profile,
)
from openardp.interfaces.ingestion_composition import local_text_ingestion
from openardp.interfaces.mcp_protocol import SessionLimits
from openardp.interfaces.mcp_server import McpServer
from openardp.ports.catalog import (
    RepresentationBusy,
    RepresentationNotFound,
)
from openardp.ports.context import (
    ContextEstimator,
)
from openardp.ports.maintenance import InsufficientSpace
from openardp.ports.object_store import ObjectStoreError
from openardp.ports.parser import ParserError, ParserTimedOut, UnsupportedTextMedia
from openardp.ports.semantic_retrieval import (
    SemanticRetrievalProvider,
)
from openardp.ports.watcher import (
    WatchCancellationObserved,
    WatchPermanentIngestion,
    WatchRetryableIngestion,
)
from openardp.services.context_compiler import (
    ContextCompilerService,
)
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.interchange import InterchangeService
from openardp.services.maintenance import (
    IRREVERSIBLE_ACKNOWLEDGEMENT,
    MaintenanceService,
)
from openardp.services.rich_evidence import RichEvidenceService
from openardp.services.rich_ingestion import RichIngestionService
from openardp.services.search import SearchService
from openardp.services.storage_optimization import StorageOptimizationService
from openardp.services.visual_evidence import VisualEvidenceService
from openardp.services.watcher import WatcherService

_COMMANDS = {
    "init",
    "ingest",
    "list",
    "status",
    "outline",
    "get",
    "search",
    "reindex",
    "evidence",
    "get-evidence",
    "context",
    "context-receipt",
    "visual-materialize",
    "visual-evidence",
    "mcp",
    "watch",
    "jobs",
    "job-cancel",
    "storage-hold",
    "storage-hold-release",
    "storage-diagnostics",
    "storage-inventory",
    "storage-optimize",
    "storage-plan",
    "storage-quarantine",
    "storage-commit",
    "storage-recover",
    "storage-restore",
    "index-rebuild",
    "workspace-backup",
    "workspace-migrate",
    "workspace-restore",
    "package-export",
    "package-verify",
    "package-import",
    "release-evidence",
    "release-gate",
    "release-report",
    *AGENT_COMMANDS,
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _services(
    workspace: LocalWorkspace,
) -> tuple[IngestionService, DocumentQueryService, SearchService]:
    ingestion = local_text_ingestion(workspace)
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=ingestion.verify_ready_representation,
    )
    search = SearchService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
    )
    return ingestion, query, search


def _rich_services(
    workspace: LocalWorkspace,
    *,
    model_root: Path | None = None,
    model_manifest_path: Path | None = None,
) -> tuple[RichIngestionService, RichEvidenceService]:
    if (model_root is None) != (model_manifest_path is None):
        raise ValueError("model root and manifest must be provided together")
    manifest = (
        _load_model_manifest(model_manifest_path) if model_manifest_path is not None else None
    )
    parser = IsolatedDoclingAdapter(
        model_root=model_root,
        model_manifest=manifest,
    )
    ingestion = RichIngestionService(
        workspace.object_store,
        workspace.catalog,
        parser,
        source_factory=LocalSource,
    )
    evidence = RichEvidenceService(
        workspace.object_store,
        workspace.catalog,
        representation_verifier=ingestion.verify_ready_representation,
    )
    return ingestion, evidence


def _context_compiler(
    workspace: LocalWorkspace,
    estimator: ContextEstimator,
    *,
    algorithm: AlgorithmIdentity | None = None,
    profile: RetrievalProfile = RetrievalProfile.LEXICAL,
    provider: SemanticRetrievalProvider | None = None,
) -> ContextCompilerService:
    """Compose one explicit retrieval profile over the open local workspace."""
    text_ingestion = local_text_ingestion(workspace)
    rich_ingestion, _evidence = _rich_services(workspace)
    verifier = rich_ingestion.verify_ready_representation
    return local_context_compiler_for_profile(
        workspace,
        estimator,
        text_ingestion.verify_ready_representation,
        verifier,
        profile,
        provider=provider,
        algorithm=algorithm,
    )


def _visual_service(workspace: LocalWorkspace) -> VisualEvidenceService:
    """Compose explicit isolated rendering without granting context compiler authority."""
    return VisualEvidenceService(
        workspace.object_store,
        workspace.catalog,
        IsolatedVisualRenderer(),
        LocalOnlyVisualPolicy(),
    )


def _context_compile(workspace: LocalWorkspace, arguments: argparse.Namespace) -> object:
    """Delegate bounded context behavior to its cohesive interface module."""
    return compile_context_command(
        workspace,
        arguments,
        _context_compiler,
        provider_factory=_open_semantic_provider,
    )


def _context_receipt(workspace: LocalWorkspace, arguments: argparse.Namespace) -> object:
    """Load one persisted receipt only after complete verification."""
    compiler = _context_compiler(workspace, _estimator_for("bytes"))
    result = compiler.load_verified(_receipt_identity(str(arguments.receipt_id)))
    return result.receipt


def _mcp_server(
    workspace: LocalWorkspace,
    limits: SessionLimits,
    *,
    semantic_provider: SemanticRetrievalProvider | None = None,
    toolset: str = "legacy",
) -> McpServer:
    """Compose MCP only from verified query, search, evidence and compiler services."""
    _ingestion, query, search = _services(workspace)
    _rich_ingestion, evidence = _rich_services(workspace)
    return McpServer(
        query,
        evidence,
        search=search,
        compiler_factory=lambda estimator: _context_compiler(workspace, estimator),
        semantic_compiler_factory=(
            (
                lambda estimator: _context_compiler(
                    workspace,
                    estimator,
                    profile=RetrievalProfile.SEMANTIC,
                    provider=semantic_provider,
                )
            )
            if semantic_provider is not None
            else None
        ),
        limits=limits,
        agent=local_agent_access(workspace) if toolset != "legacy" else None,
        toolset=toolset,
    )


def _serve_mcp(
    arguments: argparse.Namespace,
    *,
    source: BinaryIO | None = None,
    sink: BinaryIO | None = None,
) -> int:
    """Validate an existing workspace and serve one bounded stdio MCP session."""
    limits = SessionLimits(
        deadline_ms=int(arguments.deadline_ms),
        response_cap_bytes=int(arguments.response_cap_bytes),
    )
    try:
        workspace = LocalWorkspace.open(Path(arguments.store))
    except sqlite3.Error:
        raise WorkspaceIncompatible("workspace is incompatible") from None
    selected_source = cast(BinaryIO, sys.stdin.buffer) if source is None else source
    selected_sink = cast(BinaryIO, sys.stdout.buffer) if sink is None else sink
    configuration = _semantic_configuration(arguments)
    provider = _open_semantic_provider(configuration) if configuration is not None else None
    try:
        return _mcp_server(
            workspace,
            limits,
            semantic_provider=provider,
            toolset=str(getattr(arguments, "tools", "legacy")),
        ).serve(
            selected_source,
            selected_sink,
        )
    finally:
        if provider is not None:
            provider.close()


class _CliWatchRunner:
    """Reuse configured ingestion services behind the watcher runner contract."""

    def __init__(
        self,
        text: IngestionService,
        csv: IngestionService,
        rich: RichIngestionService | None,
    ) -> None:
        self._text = text
        self._csv = csv
        self._rich = rich

    def ingest(
        self,
        path: Path,
        *,
        profile: str,
        cancelled: Callable[[], bool],
    ) -> object:
        """Route one safe target and translate failures to stable watcher classes."""
        if cancelled():
            raise WatchCancellationObserved("watch cancellation observed")
        try:
            media_type = LocalSource(path).media_type
            result: object
            if isinstance(media_type, RichMediaType):
                if self._rich is None:
                    raise WatchPermanentIngestion("rich parser is unavailable")
                result = self._rich.ingest(path, profile=profile)
            elif media_type is TextMediaType.CSV:
                result = self._csv.ingest(path, profile=profile)
            else:
                result = self._text.ingest(path, profile=profile)
        except WatchPermanentIngestion:
            raise
        except (SourceNotFound, SourceChangedDuringSnapshot, ParserTimedOut, RepresentationBusy):
            raise WatchRetryableIngestion("watch ingestion is retryable") from None
        except (InvalidSourcePath, SourceTooLarge, UnsupportedTextMedia, ParserError, ValueError):
            raise WatchPermanentIngestion("watch ingestion is not retryable") from None
        if cancelled():
            raise WatchCancellationObserved("watch cancellation observed")
        return result


def _watch_config(arguments: argparse.Namespace) -> WatchConfig:
    """Construct one closed trusted watcher policy from explicit CLI values."""
    recursive = not bool(arguments.non_recursive)
    return WatchConfig(
        recursive=recursive,
        max_depth=int(arguments.max_depth) if recursive else 0,
        stability_ms=int(arguments.stability_ms),
        poll_ms=int(arguments.poll_ms),
        max_entries=int(arguments.max_entries),
        max_active_jobs=int(arguments.max_active_jobs),
        max_jobs_per_cycle=int(arguments.max_jobs_per_cycle),
        max_attempts=int(arguments.max_attempts),
        retry_base_ms=int(arguments.retry_base_ms),
        retry_max_ms=int(arguments.retry_max_ms),
        text_profile=str(arguments.profile or "default"),
        rich_profile=str(arguments.rich_profile or "openardp-docling-offline-v1"),
    )


def _watch_service(workspace: LocalWorkspace, arguments: argparse.Namespace) -> WatcherService:
    """Compose foreground watching from explicit local capabilities only."""
    text_ingestion, _query, _search = _services(workspace)
    rich: RichIngestionService | None = None
    if arguments.docling_model_root is not None or arguments.docling_model_manifest is not None:
        rich, _evidence = _rich_services(
            workspace,
            model_root=(
                Path(arguments.docling_model_root)
                if arguments.docling_model_root is not None
                else None
            ),
            model_manifest_path=(
                Path(arguments.docling_model_manifest)
                if arguments.docling_model_manifest is not None
                else None
            ),
        )
    return WatcherService(
        workspace.catalog,
        LocalWatchScanner(),
        _CliWatchRunner(text_ingestion, local_text_ingestion(workspace, TextMediaType.CSV), rich),
        workspace_root=workspace.root,
    )


def _job_summary(job: Job) -> dict[str, object]:
    """Project one job onto a body/path/owner/key-free local control surface."""
    return {
        "job_id": str(job.job_id),
        "kind": job.kind,
        "state": job.state.value,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "revision": job.revision,
        "available_at": job.model_dump(mode="json")["available_at"],
        "cancellation_requested": job.cancellation_requested_at is not None,
        "created_at": job.model_dump(mode="json")["created_at"],
        "updated_at": job.model_dump(mode="json")["updated_at"],
        "terminal_at": job.model_dump(mode="json")["terminal_at"],
    }


def _maintenance_service(workspace: LocalWorkspace) -> MaintenanceService:
    """Compose only the explicit local maintenance boundaries."""
    return MaintenanceService(workspace.maintenance_store, workspace.catalog)


def _storage_optimization_service(workspace: LocalWorkspace) -> StorageOptimizationService:
    """Compose the explicit provider-neutral storage optimization capabilities."""
    return StorageOptimizationService(workspace.object_store, workspace.catalog)


def _retention_policy(arguments: argparse.Namespace) -> RetentionPolicy:
    """Build one trusted bounded CLI policy using exact integer units."""
    return RetentionPolicy(
        candidate_min_age_seconds=int(arguments.candidate_min_age_hours) * 3_600,
        quarantine_grace_seconds=int(arguments.quarantine_grace_hours) * 3_600,
        reserve_bytes=int(arguments.reserve_bytes),
        limits=InventoryLimits(
            max_entries=int(arguments.max_entries),
            max_bytes=int(arguments.max_bytes),
        ),
    )


def _watch_cycle_summary(result: WatchCycleResult) -> dict[str, object]:
    """Project a cycle without exposing its private root authority or locators."""
    reconciliation = result.reconciliation
    return {
        "root_id": reconciliation.root.authority.root_id,
        "generation": reconciliation.root.generation,
        "complete": reconciliation.complete,
        "rescan_required": reconciliation.root.rescan_required,
        "counts": {
            "entries": reconciliation.entry_count,
            "candidates": reconciliation.candidate_count,
            "stable": reconciliation.stable_count,
            "scheduled": len(reconciliation.scheduled_job_ids),
            "tombstoned": reconciliation.tombstone_count,
            "recovered_requeued": len(result.recovery.requeued_job_ids),
            "recovered_failed": len(result.recovery.failed_job_ids),
            "recovered_cancelled": len(result.recovery.cancelled_job_ids),
            "succeeded": len(result.succeeded_job_ids),
            "retried": len(result.retried_job_ids),
            "failed": len(result.failed_job_ids),
            "cancelled": len(result.cancelled_job_ids),
        },
        "jobs": {
            "scheduled": tuple(str(value) for value in reconciliation.scheduled_job_ids),
            "succeeded": tuple(str(value) for value in result.succeeded_job_ids),
            "retried": tuple(str(value) for value in result.retried_job_ids),
            "failed": tuple(str(value) for value in result.failed_job_ids),
            "cancelled": tuple(str(value) for value in result.cancelled_job_ids),
        },
    }


_UNHANDLED = object()


def _execute(arguments: argparse.Namespace) -> object:
    """Dispatch one parsed command through its bounded command family."""
    command = str(arguments.command)
    result = _execute_standalone(arguments, command)
    if result is not _UNHANDLED:
        return result
    workspace = LocalWorkspace.open(Path(arguments.store))
    if command in AGENT_COMMANDS:
        return execute_agent_command(workspace, arguments)
    for handler in (
        _execute_watch_jobs,
        _execute_maintenance,
        _execute_ingestion,
        _execute_query,
        _execute_evidence,
    ):
        result = handler(workspace, arguments, command)
        if result is not _UNHANDLED:
            return result
    raise _UsageError("invalid command usage")


def _execute_standalone(arguments: argparse.Namespace, command: str) -> object:
    """Execute commands that do not open an existing workspace."""
    if command == "add":
        return execute_add(arguments)
    if command == "release-evidence":
        return _release_evidence(arguments)
    if command == "release-gate":
        return _release_gate(arguments)
    if command == "release-report":
        return _release_report(arguments)
    if command == "package-export":
        request = _load_package_export_request(Path(arguments.request))
        return InterchangeService().export(
            request.package,
            LocalAssetSource(
                {object_id: Path(path) for object_id, path in request.asset_sources.items()}
            ),
            Path(arguments.destination),
        )
    if command == "package-verify":
        return InterchangeService().verify(
            Path(arguments.package),
            limits=_interchange_limits(arguments),
        )
    if command == "package-import":
        return InterchangeService().import_snapshot(
            Path(arguments.package),
            Path(arguments.destination),
            limits=_interchange_limits(arguments),
        )
    if command == "workspace-restore":
        return LocalWorkspace.restore(
            Path(arguments.backup),
            Path(arguments.destination),
            now=_utc_now(),
        )
    if command == "init":
        workspace = LocalWorkspace.initialize(Path(arguments.store), now=_utc_now())
        return {
            "catalog_schema_version": workspace.catalog.schema_version(),
            "root": str(workspace.root),
        }
    if command == "workspace-migrate":
        workspace = LocalWorkspace.migrate(
            Path(arguments.store),
            Path(arguments.backup_destination),
            now=_utc_now(),
        )
        return {
            "catalog_schema_version": workspace.catalog.schema_version(),
            "root": str(workspace.root),
        }
    return _UNHANDLED


def _execute_watch_jobs(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
    command: str,
) -> object:
    """Execute foreground watch and durable job commands."""
    if command == "workspace-backup":
        return workspace.backup(Path(arguments.destination), now=_utc_now())
    if command == "watch":
        service = _watch_service(workspace, arguments)
        config = _watch_config(arguments)
        root = Path(arguments.root)
        if bool(arguments.once):
            return _watch_cycle_summary(service.run_cycle(root, config=config))
        service.run_forever(root, config=config, stop=lambda: False)
        return {"stopped": True}
    if command == "jobs":
        return tuple(
            _job_summary(job)
            for job in workspace.catalog.list_jobs(
                state=str(arguments.state) if arguments.state is not None else None,
                kind=str(arguments.kind) if arguments.kind is not None else None,
                limit=int(arguments.limit),
            )
        )
    if command == "job-cancel":
        job = workspace.catalog.request_job_cancellation(
            _parse_uuid(str(arguments.job_id)),
            now=_utc_now(),
        )
        return _job_summary(job)
    return _UNHANDLED


def _execute_maintenance(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
    command: str,
) -> object:
    """Execute storage maintenance and index-rebuild commands."""
    if command == "storage-optimize":
        report = _storage_optimization_service(workspace).optimize()
        if report.failed_count:
            raise ObjectStoreError("storage optimization did not converge")
        return report
    if command == "storage-inventory":
        return _maintenance_service(workspace).inventory(
            policy=_retention_policy(arguments),
            now=_utc_now(),
        )
    if command == "storage-diagnostics":
        return _maintenance_service(workspace).diagnostics(
            policy=RetentionPolicy(
                reserve_bytes=int(arguments.reserve_bytes),
                limits=InventoryLimits(max_entries=1_000_000, max_bytes=9_007_199_254_740_991),
            ),
            now=_utc_now(),
        )
    if command == "index-rebuild":
        _ingestion, _query, search = _services(workspace)

        def admit(required_bytes: int) -> None:
            report = workspace.maintenance_store.capacity(
                required_bytes,
                int(arguments.reserve_bytes),
            )
            if not report.admitted:
                raise InsufficientSpace("insufficient capacity for index rebuild")

        return search.rebuild_global(admit=admit)
    if command == "storage-plan":
        return _maintenance_service(workspace).plan(
            policy=_retention_policy(arguments),
            now=_utc_now(),
        )
    if command == "storage-hold":
        now = _utc_now()
        expires_hours = (
            int(arguments.expires_hours) if arguments.expires_hours is not None else None
        )
        return _maintenance_service(workspace).add_hold(
            str(arguments.object_id),
            reason=str(arguments.reason),
            now=now,
            expires_at=(
                now + timedelta(hours=expires_hours) if expires_hours is not None else None
            ),
        )
    if command == "storage-hold-release":
        return _maintenance_service(workspace).release_hold(
            str(arguments.hold_id),
            now=_utc_now(),
        )
    if command == "storage-quarantine":
        return _maintenance_service(workspace).quarantine(
            _load_reclamation_plan(Path(arguments.plan)),
            now=_utc_now(),
        )
    if command == "storage-restore":
        return _maintenance_service(workspace).restore(
            _parse_uuid(str(arguments.batch)),
            now=_utc_now(),
        )
    if command == "storage-recover":
        recovered = _maintenance_service(workspace).recover(now=_utc_now())
        return {
            "recovered": recovered is not None,
            "operation_id": str(recovered.operation_id) if recovered is not None else None,
            "kind": recovered.kind.value if recovered is not None else None,
        }
    if command == "storage-commit":
        return _maintenance_service(workspace).commit(
            _parse_uuid(str(arguments.batch)),
            acknowledgement=(
                IRREVERSIBLE_ACKNOWLEDGEMENT
                if bool(arguments.acknowledge_irreversible_removal)
                else ""
            ),
            now=_utc_now(),
        )
    return _UNHANDLED


def _execute_ingestion(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
    command: str,
) -> object:
    """Execute text or rich ingestion while preserving profile selection."""
    if command != "ingest":
        return _UNHANDLED
    source = Path(arguments.path)
    media_type = LocalSource(source).media_type
    if isinstance(media_type, RichMediaType):
        rich_ingestion, _evidence = _rich_services(
            workspace,
            model_root=(
                Path(arguments.docling_model_root)
                if arguments.docling_model_root is not None
                else None
            ),
            model_manifest_path=(
                Path(arguments.docling_model_manifest)
                if arguments.docling_model_manifest is not None
                else None
            ),
        )
        return rich_ingestion.ingest(
            source,
            profile=(
                str(arguments.profile)
                if arguments.profile is not None
                else rich_ingestion.recipe.parser.profile
            ),
            force=bool(arguments.force),
        )
    return local_text_ingestion(workspace, media_type).ingest(
        source,
        profile=str(arguments.profile) if arguments.profile is not None else "default",
        force=bool(arguments.force),
    )


def _execute_query(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
    command: str,
) -> object:
    """Execute document navigation and lexical search commands."""
    _ingestion, query, search = _services(workspace)
    if command == "list":
        return query.list_documents()
    if command == "status":
        return query.status(
            str(arguments.target),
            mode=StatusMode.FULL if arguments.full_integrity else StatusMode.HEAD,
        )
    if command == "outline":
        return query.outline(
            _parse_uuid(str(arguments.document_id)),
            version_id=str(arguments.version) if arguments.version is not None else None,
        )
    if command == "get":
        return query.get(_parse_uuid(str(arguments.block_id)))
    if command == "search":
        return search.search(
            str(arguments.query),
            document=str(arguments.document) if arguments.document is not None else None,
            version_id=str(arguments.version) if arguments.version is not None else None,
            include_history=bool(arguments.all_versions),
            kind=str(arguments.kind) if arguments.kind is not None else None,
            trust=str(arguments.trust) if arguments.trust is not None else None,
            page=int(arguments.page) if arguments.page is not None else None,
            slide=int(arguments.slide) if arguments.slide is not None else None,
            limit=int(arguments.limit) if arguments.limit is not None else None,
        )
    if command == "reindex":
        return search.reindex(
            document=str(arguments.document) if arguments.document is not None else None,
        )
    return _UNHANDLED


def _execute_evidence(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
    command: str,
) -> object:
    """Execute rich, context and visual evidence commands."""
    if command == "evidence":
        _rich_ingestion, evidence = _rich_services(workspace)
        return evidence.list(
            _parse_uuid(str(arguments.document_id)),
            version_id=str(arguments.version) if arguments.version is not None else None,
        )
    if command == "get-evidence":
        _rich_ingestion, evidence = _rich_services(workspace)
        return evidence.get(
            str(arguments.projection_id),
            document_id=(
                _parse_uuid(str(arguments.document)) if arguments.document is not None else None
            ),
        )
    if command == "context":
        return _context_compile(workspace, arguments)
    if command == "context-receipt":
        return _context_receipt(workspace, arguments)
    if command == "visual-materialize":
        document_id = _parse_uuid(str(arguments.document_id))
        aggregate = workspace.catalog.resolve_ready_representation(
            document_id,
            version_id=(str(arguments.version) if arguments.version is not None else None),
        )
        if aggregate is None:
            raise RepresentationNotFound("ready representation does not exist")
        return _visual_service(workspace).materialize(
            aggregate.representation.scope,
            str(arguments.projection_id),
            created_at=_utc_now(),
        )
    if command == "visual-evidence":
        return _visual_service(workspace).inspect(str(arguments.visual_evidence_id))
    return _UNHANDLED


def _requested_command(argv: Sequence[str]) -> str:
    return next((item for item in argv if item in _COMMANDS), "unknown")


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one CLI command and return its stable process exit classification."""
    supplied = tuple(sys.argv[1:] if argv is None else argv)
    json_requested = "--json" in supplied
    command = _requested_command(supplied)
    try:
        arguments = _parser().parse_args(supplied)
        command = str(arguments.command)
        if command == "mcp":
            return _serve_mcp(arguments)
        data = _execute(arguments)
        rendered = (
            render_agent_result(
                command,
                data,
                line_numbers=not getattr(arguments, "no_line_numbers", False),
            )
            if command in AGENT_COMMANDS and not arguments.json_output
            else None
        )
        if rendered is not None:
            print(rendered)
        else:
            _success(command, data, json_output=bool(arguments.json_output))
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 1
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        return render_failure(command, error, json_output=json_requested)


if __name__ == "__main__":  # pragma: no cover - console script owns normal execution
    raise SystemExit(main())


__all__ = ["main"]
