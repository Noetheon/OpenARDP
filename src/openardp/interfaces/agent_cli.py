"""CLI grammar, composition and rendering for the token-efficient agent commands.

``add`` prepares files and folders in one process; ``docs``, ``find``, ``read``, ``toc``
and ``verify`` give compact located results; ``agent-view`` writes plain files for agents
with file tools; ``refresh`` rebuilds the disposable agent index.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from openardp.adapters.agent_index import SQLiteAgentIndex
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.adapters.local_source import SUPPORTED_SUFFIXES, LocalSource
from openardp.adapters.local_workspace import LocalWorkspace, WorkspaceMissing
from openardp.domain.agent_results import (
    AddOutcome,
    AddReport,
    AddStatus,
    DocsResult,
    ExportReport,
    FindResult,
    OutlineResult,
    ReadResult,
    VerifyResult,
)
from openardp.domain.ingestion import RichMediaType, TextMediaType
from openardp.interfaces.agent_composition import local_agent_access, local_status_probe
from openardp.interfaces.agent_render import (
    render_add,
    render_docs,
    render_export,
    render_find,
    render_outline,
    render_read,
    render_verify,
    safe,
)
from openardp.interfaces.cli_errors import classify
from openardp.interfaces.cli_file_commands import _load_model_manifest
from openardp.interfaces.ingestion_composition import local_text_ingestion
from openardp.services.agent_view import AgentViewService
from openardp.services.bulk_ingest import BulkIngestService, PreparedResult, discover_files
from openardp.services.ingestion import IngestionService
from openardp.services.rich_ingestion import RichIngestionService


def execute_add(arguments: argparse.Namespace) -> AddReport:
    """Open or create the store, prepare every discovered file and refresh the index."""
    store = Path(arguments.store)
    try:
        workspace = LocalWorkspace.open(store)
    except WorkspaceMissing:
        if store.exists():
            raise
        workspace = LocalWorkspace.initialize(store, now=datetime.now(UTC))
        if not arguments.json_output:
            print(f"Created workspace {workspace.root}", file=sys.stderr)
    discovery = discover_files(
        list(arguments.paths),
        supported_suffixes=SUPPORTED_SUFFIXES,
        exclude=(workspace.root,),
        recursive=not arguments.no_recursive,
    )
    ingest_one = _ingest_router(workspace, arguments)
    probe = local_status_probe(workspace)
    service = BulkIngestService(ingest_one, lambda path: probe(str(path)), _describe_error)
    started = time.monotonic()
    report = service.add(
        discovery,
        progress=None if arguments.json_output else _print_progress,
    )
    local_agent_access(workspace).refresh()
    return report.model_copy(update={"seconds": round(time.monotonic() - started, 3)})


def execute_agent_command(workspace: LocalWorkspace, arguments: argparse.Namespace) -> object:
    """Run one agent read command against an open workspace."""
    command = str(arguments.command)
    if command == "agent-view":
        access = local_agent_access(workspace)
        index = SQLiteAgentIndex.for_workspace(workspace.root)
        return AgentViewService(index, access.refresh).export(
            Path(arguments.directory),
            workspace_root=workspace.root,
        )
    if command == "refresh":
        if arguments.full:
            SQLiteAgentIndex.for_workspace(workspace.root).clear()
        report = local_agent_access(workspace).refresh()
        return {
            "indexed": report.indexed,
            "rebuilt": list(report.rebuilt),
            "removed": report.removed,
            "failed": list(report.failed),
        }
    access = local_agent_access(workspace)
    if command == "docs":
        return access.documents()
    if command == "find":
        return access.find(str(arguments.query), document=arguments.document, limit=arguments.limit)
    if command == "read":
        return access.read(
            str(arguments.document),
            page=arguments.page,
            lines=arguments.lines,
            section=arguments.section,
            max_tokens=int(arguments.max_tokens),
        )
    if command == "toc":
        return access.outline(str(arguments.document))
    if command == "verify":
        return access.verify(
            str(arguments.quote),
            document=arguments.document,
            version=arguments.version,
        )
    raise ValueError("unknown agent command")


def render_agent_result(command: str, data: object, *, line_numbers: bool = True) -> str | None:
    """Return the compact human rendering of one agent command result, if any."""
    if isinstance(data, DocsResult):
        return render_docs(data)
    if isinstance(data, FindResult):
        return render_find(data)
    if isinstance(data, ReadResult):
        return render_read(data, line_numbers=line_numbers)
    if isinstance(data, OutlineResult):
        return render_outline(data)
    if isinstance(data, VerifyResult):
        return render_verify(data)
    if isinstance(data, AddReport):
        return render_add(data)
    if isinstance(data, ExportReport):
        return render_export(data)
    if command == "refresh" and isinstance(data, dict):
        failed = ", ".join(safe(str(item)) for item in data["failed"]) or "none"
        return (
            f"Agent index: {data['indexed']} documents, {len(data['rebuilt'])} rebuilt, "
            f"{data['removed']} removed, failed: {failed}"
        )
    return None


def _ingest_router(
    workspace: LocalWorkspace,
    arguments: argparse.Namespace,
) -> Callable[[Path], PreparedResult]:
    text_services: dict[TextMediaType, IngestionService] = {}
    rich_service: list[RichIngestionService] = []

    def ingest(path: Path) -> PreparedResult:
        media_type = LocalSource(path).media_type
        if isinstance(media_type, RichMediaType):
            if not rich_service:
                rich_service.append(_rich_ingestion(workspace, arguments))
            service = rich_service[0]
            return service.ingest(path, profile=service.recipe.parser.profile)
        if media_type not in text_services:
            text_services[media_type] = local_text_ingestion(workspace, media_type)
        return text_services[media_type].ingest(path, profile="default")

    return ingest


def _rich_ingestion(
    workspace: LocalWorkspace, arguments: argparse.Namespace
) -> RichIngestionService:
    root = arguments.docling_model_root
    manifest_path = arguments.docling_model_manifest
    if (root is None) != (manifest_path is None):
        raise ValueError("model root and manifest must be provided together")
    manifest = _load_model_manifest(Path(manifest_path)) if manifest_path is not None else None
    parser = IsolatedDoclingAdapter(
        model_root=Path(root) if root is not None else None,
        model_manifest=manifest,
    )
    return RichIngestionService(
        workspace.object_store,
        workspace.catalog,
        parser,
        source_factory=LocalSource,
    )


def _describe_error(error: Exception) -> tuple[str, str | None]:
    failure = classify(error)
    return failure.code, failure.hint


def _print_progress(position: int, total: int, outcome: AddOutcome) -> None:
    label = Path(outcome.path).name
    detail = outcome.status.value
    if outcome.status is AddStatus.FAILED and outcome.error_code:
        detail = f"failed ({outcome.error_code})"
    print(
        f"[{position}/{total}] {safe(label)} — {detail} ({outcome.seconds:.1f}s)",
        file=sys.stderr,
        flush=True,
    )


__all__ = [
    "execute_add",
    "execute_agent_command",
    "render_agent_result",
]
