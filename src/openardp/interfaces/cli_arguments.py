"""Stable bounded argparse grammar for the OpenARDP CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import NoReturn
from uuid import UUID

from openardp.domain.context import ContextMode
from openardp.domain.interchange import InterchangeLimits
from openardp.domain.storage import JobState
from openardp.interfaces.cli_query_arguments import add_query_arguments
from openardp.interfaces.context_cli import ContextCommandUsageError
from openardp.interfaces.context_composition import RetrievalProfile

_CONTEXT_MODES = tuple(mode.value for mode in ContextMode)
_CONTEXT_UNITS = ("bytes", "characters", "tokens")


class ArgumentParser(argparse.ArgumentParser):
    """Raise a body-free usage classification instead of exiting on errors."""

    def error(self, message: str) -> NoReturn:
        """Raise the stable usage category without reflecting parser input."""
        del message
        raise ContextCommandUsageError("invalid command usage")


type _Subparsers = argparse._SubParsersAction[ArgumentParser]


def parser() -> ArgumentParser:
    """Build the complete stable command grammar from bounded command groups."""
    result = ArgumentParser(
        prog="openardp",
        description="Local-first immutable document intelligence",
    )
    subparsers = result.add_subparsers(dest="command", required=True)
    _add_ingestion_commands(subparsers)
    _add_job_commands(subparsers)
    _add_retention_commands(subparsers)
    _add_workspace_commands(subparsers)
    _add_interchange_commands(subparsers)
    _add_release_commands(subparsers)
    add_query_arguments(subparsers, common_options=_common_options)
    _add_evidence_commands(subparsers)
    _add_context_commands(subparsers)
    _add_mcp_command(subparsers)
    return result


def _add_ingestion_commands(subparsers: _Subparsers) -> None:
    init = subparsers.add_parser("init", help="initialize an explicit local workspace")
    _common_options(init)
    ingest = subparsers.add_parser("ingest", help="ingest one supported local document")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--profile")
    ingest.add_argument("--force", action="store_true")
    ingest.add_argument("--docling-model-root", type=Path)
    ingest.add_argument("--docling-model-manifest", type=Path)
    _common_options(ingest)
    watch = subparsers.add_parser("watch", help="watch one explicit local root in foreground")
    watch.add_argument("root", type=Path)
    watch.add_argument("--once", action="store_true")
    watch.add_argument("--non-recursive", action="store_true", dest="non_recursive")
    watch.add_argument("--max-depth", type=int, default=32, dest="max_depth")
    watch.add_argument("--stability-ms", type=int, default=5_000, dest="stability_ms")
    watch.add_argument("--poll-ms", type=int, default=2_000, dest="poll_ms")
    watch.add_argument("--max-entries", type=int, default=10_000, dest="max_entries")
    watch.add_argument("--max-active-jobs", type=int, default=1_000, dest="max_active_jobs")
    watch.add_argument("--max-jobs-per-cycle", type=int, default=1, dest="max_jobs_per_cycle")
    watch.add_argument("--max-attempts", type=int, default=3, dest="max_attempts")
    watch.add_argument("--retry-base-ms", type=int, default=1_000, dest="retry_base_ms")
    watch.add_argument("--retry-max-ms", type=int, default=60_000, dest="retry_max_ms")
    watch.add_argument("--profile")
    watch.add_argument("--rich-profile")
    watch.add_argument("--docling-model-root", type=Path)
    watch.add_argument("--docling-model-manifest", type=Path)
    _common_options(watch)


def _add_job_commands(subparsers: _Subparsers) -> None:
    jobs = subparsers.add_parser("jobs", help="list body-free durable job state")
    jobs.add_argument("--state", choices=tuple(state.value for state in JobState))
    jobs.add_argument("--kind")
    jobs.add_argument("--limit", type=int, default=100)
    _common_options(jobs)
    cancel = subparsers.add_parser("job-cancel", help="cancel one durable local job")
    cancel.add_argument("job_id")
    _common_options(cancel)


def _add_retention_commands(subparsers: _Subparsers) -> None:
    for name, help_text in (
        ("storage-inventory", "explain bounded local retention state"),
        ("storage-plan", "create a read-only exact reclamation plan"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--max-entries", type=int, default=100_000)
        command.add_argument("--max-bytes", type=int, default=1_099_511_627_776)
        command.add_argument("--candidate-min-age-hours", type=int, default=24)
        command.add_argument("--quarantine-grace-hours", type=int, default=168)
        command.add_argument("--reserve-bytes", type=int, default=67_108_864)
        _common_options(command)
    _add_retention_mutations(subparsers)
    for name, help_text in (
        ("storage-diagnostics", "report exact local storage and reserve facts"),
        ("index-rebuild", "atomically rebuild the complete disposable lexical index"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--reserve-bytes", type=int, default=67_108_864)
        _common_options(command)
    optimize = subparsers.add_parser(
        "storage-optimize",
        help="explicitly compact eligible derived blocks and reclaim catalog pages",
    )
    _common_options(optimize)


def _add_retention_mutations(subparsers: _Subparsers) -> None:
    hold = subparsers.add_parser("storage-hold", help="protect one exact managed object")
    hold.add_argument("object_id")
    hold.add_argument("--reason", default="operator_hold")
    hold.add_argument("--expires-hours", type=int)
    _common_options(hold)
    release = subparsers.add_parser("storage-hold-release", help="release one exact retention hold")
    release.add_argument("hold_id")
    _common_options(release)
    quarantine = subparsers.add_parser(
        "storage-quarantine", help="quarantine one exact supplied reclamation plan"
    )
    quarantine.add_argument("--plan", type=Path, required=True)
    _common_options(quarantine)
    restore = subparsers.add_parser("storage-restore", help="restore one named quarantine batch")
    restore.add_argument("--batch", required=True)
    _common_options(restore)
    _common_options(
        subparsers.add_parser(
            "storage-recover", help="recover one already-persisted maintenance intent"
        )
    )
    commit = subparsers.add_parser(
        "storage-commit", help="irreversibly commit one expired named quarantine batch"
    )
    commit.add_argument("--batch", required=True)
    commit.add_argument(
        "--acknowledge-irreversible-removal",
        action="store_true",
        dest="acknowledge_irreversible_removal",
    )
    _common_options(commit)


def _add_workspace_commands(subparsers: _Subparsers) -> None:
    backup = subparsers.add_parser(
        "workspace-backup", help="create one verified internal workspace backup"
    )
    backup.add_argument("--destination", type=Path, required=True)
    _common_options(backup)
    restore = subparsers.add_parser(
        "workspace-restore", help="restore one verified backup to a fresh workspace"
    )
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    restore.add_argument("--json", action="store_true", dest="json_output")
    migrate = subparsers.add_parser(
        "workspace-migrate", help="back up then explicitly migrate one supported older workspace"
    )
    migrate.add_argument("--backup-destination", type=Path, required=True)
    _common_options(migrate)


def _add_interchange_commands(subparsers: _Subparsers) -> None:
    export = subparsers.add_parser(
        "package-export", help="create one experimental deterministic BagIt package"
    )
    export.add_argument("--request", type=Path, required=True)
    export.add_argument("--destination", type=Path, required=True)
    export.add_argument("--json", action="store_true", dest="json_output")
    verify = subparsers.add_parser(
        "package-verify", help="verify one experimental BagIt package without extraction"
    )
    verify.add_argument("--package", type=Path, required=True)
    _interchange_limit_options(verify)
    verify.add_argument("--json", action="store_true", dest="json_output")
    import_command = subparsers.add_parser(
        "package-import", help="publish one verified package as a fresh immutable snapshot"
    )
    import_command.add_argument("--package", type=Path, required=True)
    import_command.add_argument("--destination", type=Path, required=True)
    _interchange_limit_options(import_command)
    import_command.add_argument("--json", action="store_true", dest="json_output")


def _add_release_commands(subparsers: _Subparsers) -> None:
    evidence = subparsers.add_parser(
        "release-evidence", help="generate one immutable body-free platform evidence bundle"
    )
    evidence.add_argument("--corpus", type=Path, required=True)
    evidence.add_argument("--output", type=Path, required=True)
    evidence.add_argument("--source-root", type=Path, required=True)
    evidence.add_argument("--suite-results", type=Path)
    evidence.add_argument("--reference-timing", action="store_true")
    evidence.add_argument("--json", action="store_true", dest="json_output")
    gate = subparsers.add_parser(
        "release-gate", help="evaluate all frozen release clauses without waivers"
    )
    gate.add_argument("--policy", type=Path, required=True)
    gate.add_argument("--evidence", type=Path, action="append", required=True)
    gate.add_argument("--output", type=Path, required=True)
    gate.add_argument("--decision-at", required=True)
    gate.add_argument("--json", action="store_true", dest="json_output")
    report = subparsers.add_parser(
        "release-report", help="write or drift-check human and claim projections"
    )
    report.add_argument("--decision", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--check", action="store_true")
    report.add_argument("--json", action="store_true", dest="json_output")


def _add_evidence_commands(subparsers: _Subparsers) -> None:
    evidence = subparsers.add_parser("evidence", help="list body-free accepted rich evidence")
    evidence.add_argument("document_id")
    evidence.add_argument("--version")
    _common_options(evidence)
    get_evidence = subparsers.add_parser(
        "get-evidence", help="retrieve one exact accepted rich evidence body"
    )
    get_evidence.add_argument("projection_id")
    get_evidence.add_argument("--document")
    _common_options(get_evidence)
    materialize = subparsers.add_parser(
        "visual-materialize",
        help="materialize one accepted evidence projection as exact visual evidence",
    )
    materialize.add_argument("document_id")
    materialize.add_argument("projection_id")
    materialize.add_argument("--version")
    _common_options(materialize)
    visual = subparsers.add_parser(
        "visual-evidence", help="inspect one exact verified visual evidence descriptor"
    )
    visual.add_argument("visual_evidence_id")
    _common_options(visual)


def _add_context_commands(subparsers: _Subparsers) -> None:
    context = subparsers.add_parser(
        "context", help="compile bounded evidence context with a body-free receipt"
    )
    context.add_argument("task")
    context.add_argument("--document", action="append", default=[])
    context.add_argument("--budget", type=int)
    context.add_argument("--unit", choices=_CONTEXT_UNITS)
    context.add_argument("--mode", choices=_CONTEXT_MODES)
    context.add_argument("--include-bundle", action="store_true", dest="include_bundle")
    context.add_argument("--replay")
    context.add_argument("--retrieval-profile", choices=tuple(RetrievalProfile))
    context.add_argument("--semantic-bundle", type=Path)
    context.add_argument("--semantic-source-lock", type=Path, dest="semantic_source_lock")
    _common_options(context)
    receipt = subparsers.add_parser(
        "context-receipt", help="inspect one exact verified body-free selection receipt"
    )
    receipt.add_argument("receipt_id")
    _common_options(receipt)


def _add_mcp_command(subparsers: _Subparsers) -> None:
    mcp = subparsers.add_parser("mcp", help="serve the bounded read-only MCP interface over stdio")
    mcp.add_argument("--store", type=Path, default=Path.cwd() / ".openardp")
    mcp.add_argument("--deadline-ms", type=int, default=30_000, dest="deadline_ms")
    mcp.add_argument("--response-cap-bytes", type=int, default=1_048_576, dest="response_cap_bytes")
    mcp.add_argument("--semantic-bundle", type=Path)
    mcp.add_argument("--semantic-source-lock", type=Path, dest="semantic_source_lock")


def _common_options(command: argparse.ArgumentParser) -> None:
    command.add_argument("--store", type=Path, default=Path.cwd() / ".openardp")
    command.add_argument("--json", action="store_true", dest="json_output")


def _interchange_limit_options(command: argparse.ArgumentParser) -> None:
    defaults = InterchangeLimits()
    command.add_argument("--max-archive-bytes", type=int, default=defaults.max_archive_bytes)
    command.add_argument("--max-expanded-bytes", type=int, default=defaults.max_expanded_bytes)
    command.add_argument("--max-entry-count", type=int, default=defaults.max_entry_count)
    command.add_argument("--max-entry-bytes", type=int, default=defaults.max_entry_bytes)
    command.add_argument("--max-metadata-bytes", type=int, default=defaults.max_metadata_bytes)
    command.add_argument("--max-path-bytes", type=int, default=defaults.max_path_bytes)
    command.add_argument("--max-path-depth", type=int, default=defaults.max_path_depth)
    command.add_argument("--max-relationships", type=int, default=defaults.max_relationships)


def parse_uuid(value: str) -> UUID:
    """Parse one CLI UUID without leaking provider-specific validation detail."""
    try:
        return UUID(value)
    except ValueError as error:
        raise ContextCommandUsageError("identifier must be a UUID") from error


__all__ = ["ArgumentParser", "ContextCommandUsageError", "parse_uuid", "parser"]
