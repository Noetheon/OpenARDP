"""Installable stable CLI composition root for local document intelligence."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, NoReturn, cast
from uuid import UUID

from pydantic import BaseModel

from openardp.adapters.context_candidates import (
    RichLexicalCandidateSource,
    TextLexicalCandidateSource,
)
from openardp.adapters.context_estimators import (
    ConservativeTokenEstimator,
    UnicodeCharacterEstimator,
    Utf8ByteEstimator,
)
from openardp.adapters.isolated_docling import IsolatedDoclingAdapter
from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import (
    InvalidSourcePath,
    LocalSource,
    SourceNotFound,
    SourceTooLarge,
)
from openardp.adapters.local_workspace import (
    LocalWorkspace,
    WorkspaceError,
    WorkspaceIncompatible,
)
from openardp.domain.common import SCHEMA_VERSION, Sensitivity
from openardp.domain.context import ContextMode
from openardp.domain.context_compilation import (
    ContextCompilationResult,
    ContextCompileRequest,
    ContextSelectionPolicy,
)
from openardp.domain.ingestion import RichMediaType
from openardp.domain.rich_ingestion import ModelBundleManifest
from openardp.domain.search import SearchOutcome, SearchQueryRejected
from openardp.interfaces.mcp_protocol import SessionLimits
from openardp.interfaces.mcp_server import McpServer
from openardp.ports.catalog import (
    AmbiguousBlock,
    BlockNotFound,
    CatalogError,
    CatalogIncompatible,
    CatalogTooNew,
    DocumentNotFound,
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
    ContextEstimator,
    ContextIntegrityFailure,
    ContextLimitExceeded,
    ContextNotFound,
)
from openardp.ports.object_store import ObjectStoreError
from openardp.ports.parser import ParserError, UnsupportedTextMedia
from openardp.services.context_compiler import ContextCompilerService
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService
from openardp.services.rich_evidence import RichEvidenceService
from openardp.services.rich_ingestion import RichIngestionService
from openardp.services.search import SearchService

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
    "mcp",
}

_CONTEXT_MODES = tuple(mode.value for mode in ContextMode)
_CONTEXT_UNITS = ("bytes", "characters", "tokens")


class _UsageError(ValueError):
    """Bounded argparse failure that can use the stable JSON envelope."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        """Raise a body-free usage classification instead of exiting."""
        del message
        raise _UsageError("invalid command usage")


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser(
        prog="openardp",
        description="Local-first immutable document intelligence",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize an explicit local workspace")
    _common_options(init)

    ingest = subparsers.add_parser("ingest", help="ingest one supported local document")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--profile")
    ingest.add_argument("--force", action="store_true")
    ingest.add_argument("--docling-model-root", type=Path)
    ingest.add_argument("--docling-model-manifest", type=Path)
    _common_options(ingest)

    list_parser = subparsers.add_parser("list", help="list body-free document summaries")
    _common_options(list_parser)

    status = subparsers.add_parser("status", help="compare current source freshness")
    status.add_argument("target")
    _common_options(status)

    outline = subparsers.add_parser("outline", help="show one structural document outline")
    outline.add_argument("document_id")
    outline.add_argument("--version")
    _common_options(outline)

    get = subparsers.add_parser("get", help="retrieve one exact current block")
    get.add_argument("block_id")
    _common_options(get)

    search = subparsers.add_parser("search", help="exact lexical search over prepared evidence")
    search.add_argument("query")
    search.add_argument("--document")
    search.add_argument("--version")
    search.add_argument("--all-versions", action="store_true")
    search.add_argument("--kind")
    search.add_argument("--trust")
    search.add_argument("--page", type=int)
    search.add_argument("--slide", type=int)
    search.add_argument("--limit", type=int)
    _common_options(search)

    reindex = subparsers.add_parser(
        "reindex",
        help="rebuild lexical index rows from verified READY evidence",
    )
    reindex.add_argument("--document")
    _common_options(reindex)

    evidence = subparsers.add_parser(
        "evidence",
        help="list body-free accepted rich evidence",
    )
    evidence.add_argument("document_id")
    evidence.add_argument("--version")
    _common_options(evidence)

    get_evidence = subparsers.add_parser(
        "get-evidence",
        help="retrieve one exact accepted rich evidence body",
    )
    get_evidence.add_argument("projection_id")
    get_evidence.add_argument("--document")
    _common_options(get_evidence)

    context = subparsers.add_parser(
        "context",
        help="compile bounded evidence context with a body-free receipt",
    )
    context.add_argument("task")
    context.add_argument("--document", action="append", default=[])
    context.add_argument("--budget", type=int)
    context.add_argument("--unit", choices=_CONTEXT_UNITS)
    context.add_argument("--mode", choices=_CONTEXT_MODES)
    context.add_argument("--include-bundle", action="store_true", dest="include_bundle")
    context.add_argument("--replay")
    _common_options(context)

    context_receipt = subparsers.add_parser(
        "context-receipt",
        help="inspect one exact verified body-free selection receipt",
    )
    context_receipt.add_argument("receipt_id")
    _common_options(context_receipt)

    mcp = subparsers.add_parser(
        "mcp",
        help="serve the bounded read-only MCP interface over stdio",
    )
    mcp.add_argument("--store", type=Path, default=Path.cwd() / ".openardp")
    mcp.add_argument("--deadline-ms", type=int, default=30_000, dest="deadline_ms")
    mcp.add_argument(
        "--response-cap-bytes",
        type=int,
        default=1_048_576,
        dest="response_cap_bytes",
    )
    return parser


def _common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", type=Path, default=Path.cwd() / ".openardp")
    parser.add_argument("--json", action="store_true", dest="json_output")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _services(
    workspace: LocalWorkspace,
) -> tuple[IngestionService, DocumentQueryService, SearchService]:
    parser = IsolatedParserAdapter()
    ingestion = IngestionService(
        workspace.object_store,
        workspace.catalog,
        parser,
        source_factory=LocalSource,
    )
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


def _estimator_for(unit: str) -> ContextEstimator:
    """Resolve one exact built-in estimator for the bounded CLI unit name."""
    if unit == "characters":
        return UnicodeCharacterEstimator()
    if unit == "tokens":
        return ConservativeTokenEstimator()
    return Utf8ByteEstimator()


def _context_compiler(
    workspace: LocalWorkspace,
    estimator: ContextEstimator,
) -> ContextCompilerService:
    """Compose the provider-free compiler over the open local workspace."""
    rich_ingestion, _evidence = _rich_services(workspace)
    return ContextCompilerService(
        workspace.object_store,
        workspace.catalog,
        estimator,
        (
            TextLexicalCandidateSource(workspace.object_store, workspace.catalog),
            RichLexicalCandidateSource(
                workspace.object_store,
                workspace.catalog,
                representation_verifier=rich_ingestion.verify_ready_representation,
            ),
        ),
    )


def _receipt_identity(value: str) -> str:
    """Validate one exact selection-receipt identity without inspecting state."""
    digest = value.removeprefix("sha256:")
    if (
        len(digest) != 64
        or len(value) != 71
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise _UsageError("receipt identifier is invalid")
    return value


def _context_summary(
    result: ContextCompilationResult,
    *,
    replayed: bool,
    include_bundle: bool,
) -> dict[str, object]:
    """Project one compile/replay result into bounded handles and accounting."""
    receipt = result.receipt
    summary: dict[str, object] = {
        "bundle_id": str(result.bundle.bundle_id),
        "receipt_id": receipt.receipt_id,
        "persisted": True,
        "replayed": replayed,
        "created_at": receipt.model_dump(mode="json")["created_at"],
        "mode": receipt.policy.mode.value,
        "estimator": receipt.estimator,
        "scopes": receipt.corpus_snapshot,
        "budget": receipt.budget,
        "counts": {
            "selected": len(receipt.selected),
            "omitted": len(receipt.omitted),
            "rejected": len(receipt.rejected),
            "stale": len(receipt.stale),
        },
        "truncated": receipt.truncated,
        "notices": receipt.notices,
        "warnings": result.bundle.warnings,
        "missing_evidence": result.bundle.missing_evidence,
    }
    if include_bundle:
        summary["bundle"] = result.bundle
    return summary


def _context_compile(workspace: LocalWorkspace, arguments: argparse.Namespace) -> object:
    """Compile or replay bounded context and persist it atomically."""
    estimator = _estimator_for(str(arguments.unit or "bytes"))
    compiler = _context_compiler(workspace, estimator)
    task = str(arguments.task)
    if arguments.replay is not None:
        if arguments.document or arguments.budget is not None or arguments.mode is not None:
            raise _UsageError("replay accepts only task, unit, receipt and store options")
        result = compiler.replay(task, _receipt_identity(str(arguments.replay)))
        return _context_summary(
            result,
            replayed=True,
            include_bundle=bool(arguments.include_bundle),
        )
    if not arguments.document:
        raise _UsageError("at least one document is required")
    if arguments.budget is None:
        raise _UsageError("a budget is required")
    document_ids = tuple(sorted({_parse_uuid(str(value)) for value in arguments.document}, key=str))
    request = ContextCompileRequest(
        task=task,
        document_ids=document_ids,
        budget_limit=int(arguments.budget),
        estimator=estimator.identity,
        # The local CLI admits every sensitivity of the owner's own corpus and
        # records the classified trust body-free; instruction execution stays
        # disabled structurally for every selected body.
        policy=ContextSelectionPolicy(
            mode=ContextMode(str(arguments.mode or "mixed")),
            maximum_sensitivity=Sensitivity.UNKNOWN,
        ),
    )
    persisted = compiler.compile_and_persist(request)
    return _context_summary(
        persisted.result,
        replayed=False,
        include_bundle=bool(arguments.include_bundle),
    )


def _context_receipt(workspace: LocalWorkspace, arguments: argparse.Namespace) -> object:
    """Load one persisted receipt only after complete verification."""
    compiler = _context_compiler(workspace, _estimator_for("bytes"))
    result = compiler.load_verified(_receipt_identity(str(arguments.receipt_id)))
    return result.receipt


def _mcp_server(workspace: LocalWorkspace, limits: SessionLimits) -> McpServer:
    """Compose MCP only from verified query, search, evidence and compiler services."""
    _ingestion, query, search = _services(workspace)
    _rich_ingestion, evidence = _rich_services(workspace)
    return McpServer(
        query,
        evidence,
        search=search,
        compiler_factory=lambda estimator: _context_compiler(workspace, estimator),
        limits=limits,
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
    return _mcp_server(workspace, limits).serve(selected_source, selected_sink)


def _load_model_manifest(path: Path) -> ModelBundleManifest:
    selected = path.expanduser().absolute()
    descriptor: int | None = None
    try:
        metadata = selected.lstat()
        if selected.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ValueError
        if metadata.st_size > 8_388_608:
            raise ValueError
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(selected, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (metadata.st_dev, metadata.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise ValueError
        chunks: list[bytes] = []
        observed = 0
        while chunk := os.read(descriptor, 1_048_576):
            observed += len(chunk)
            if observed > 8_388_608:
                raise ValueError
            chunks.append(chunk)
        if observed != metadata.st_size:
            raise ValueError
        payload = b"".join(chunks)
        return ModelBundleManifest.model_validate_json(payload)
    except (OSError, ValueError):
        raise ValueError("local model manifest is invalid") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _execute(arguments: argparse.Namespace) -> object:
    command = str(arguments.command)
    store = Path(arguments.store)
    if command == "init":
        workspace = LocalWorkspace.initialize(store, now=_utc_now())
        return {
            "catalog_schema_version": workspace.catalog.schema_version(),
            "root": str(workspace.root),
        }

    workspace = LocalWorkspace.open(store)
    if command == "ingest":
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
        ingestion, _query, _search = _services(workspace)
        return ingestion.ingest(
            source,
            profile=str(arguments.profile) if arguments.profile is not None else "default",
            force=bool(arguments.force),
        )

    _ingestion, query, search = _services(workspace)
    if command == "list":
        return query.list_documents()
    if command == "status":
        return query.status(str(arguments.target))
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
    raise _UsageError("invalid command usage")


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as error:
        raise _UsageError("identifier must be a UUID") from error


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _write_json(payload: dict[str, object]) -> None:
    sys.stdout.write(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def _success(command: str, data: object, *, json_output: bool) -> None:
    converted = _json_value(data)
    if json_output:
        _write_json(
            {
                "command": command,
                "data": converted,
                "ok": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        return
    if command == "init":
        assert isinstance(converted, dict)
        print(f"Initialized OpenARDP workspace: {converted['root']}")
    elif command == "ingest":
        assert isinstance(converted, dict)
        scope = converted["scope"]
        assert isinstance(scope, dict)
        if "evidence_count" in converted:
            print(
                "Ingested "
                f"{scope['document_id']} "
                f"({converted['disposition']}, {converted['evidence_count']} evidence items)"
            )
        else:
            print(
                "Ingested "
                f"{scope['document_id']} "
                f"({converted['disposition']}, {converted['block_count']} blocks)"
            )
    elif command == "list":
        assert isinstance(converted, list)
        for item in converted:
            assert isinstance(item, dict)
            source = item["source_key"]
            assert isinstance(source, dict)
            print(f"{item['document_id']}\t{source['locator']}\t{item['state'] or 'UNPREPARED'}")
    elif command == "status":
        assert isinstance(converted, dict)
        print(str(converted["freshness"]))
    elif command == "outline":
        assert isinstance(converted, list)
        for item in converted:
            assert isinstance(item, dict)
            print(f"{'  ' * int(item['depth'])}{item['kind']}\t{_safe_text(str(item['label']))}")
    elif command == "search":
        assert isinstance(data, SearchOutcome)
        for hit in data.hits:
            print(
                f"{hit.scope.document_id}\t{hit.block_id}\t{hit.kind.value}\t"
                f"{hit.line_start}-{hit.line_end}\t{_safe_text(hit.snippet)}"
            )
        print(f"returned={data.returned} available={data.available} truncated={data.truncated}")
    elif command == "reindex":
        assert isinstance(converted, dict)
        scopes = converted["scopes"]
        assert isinstance(scopes, list)
        for item in scopes:
            assert isinstance(item, dict)
            scope = item["scope"]
            assert isinstance(scope, dict)
            print(f"{scope['document_id']}\t{item['outcome']}\tentries={item['entry_count']}")
    elif command == "evidence":
        assert isinstance(converted, list)
        for item in converted:
            assert isinstance(item, dict)
            retrieval = item["retrieval"]
            assert isinstance(retrieval, dict)
            print(
                f"{item['evidence_projection_id']}\t"
                f"{retrieval['media_type']}\t{retrieval['byte_length']} bytes"
            )
    elif command == "get-evidence":
        assert isinstance(converted, dict)
        projection = converted["projection"]
        assert isinstance(projection, dict)
        print(f"{projection['evidence_projection_id']}\t{_safe_text(str(converted['body']))}")
    elif command == "context":
        assert isinstance(converted, dict)
        counts = converted["counts"]
        assert isinstance(counts, dict)
        budget = converted["budget"]
        assert isinstance(budget, dict)
        print(f"receipt={converted['receipt_id']}")
        print(f"bundle={converted['bundle_id']}")
        print(
            f"selected={counts['selected']} omitted={counts['omitted']} "
            f"rejected={counts['rejected']} stale={counts['stale']} "
            f"truncated={str(converted['truncated']).lower()}"
        )
        print(
            f"budget={budget['bundle_used']}/{budget['bundle_ceiling']} "
            f"{budget['unit']} limit={budget['limit']}"
        )
        warnings = converted["warnings"]
        assert isinstance(warnings, list)
        for warning in warnings:
            assert isinstance(warning, dict)
            print(f"warning {warning['code']}: {_safe_text(str(warning['message']))}")
        missing = converted["missing_evidence"]
        assert isinstance(missing, list)
        for entry in missing:
            assert isinstance(entry, dict)
            print(f"missing {entry['evidence_type']} ({entry['reason_code']})")
    elif command == "context-receipt":
        assert isinstance(converted, dict)
        policy = converted["policy"]
        assert isinstance(policy, dict)
        budget = converted["budget"]
        assert isinstance(budget, dict)
        print(f"receipt={converted['receipt_id']}")
        print(f"created={converted['created_at']}")
        print(f"task_digest={converted['task_digest']}")
        print(f"mode={policy['mode']}")
        print(
            f"budget={budget['bundle_used']}/{budget['bundle_ceiling']} "
            f"{budget['unit']} limit={budget['limit']}"
        )
        print(
            f"scopes={len(converted['corpus_snapshot'])} "
            f"selected={len(converted['selected'])} omitted={len(converted['omitted'])} "
            f"rejected={len(converted['rejected'])} stale={len(converted['stale'])} "
            f"truncated={str(converted['truncated']).lower()}"
        )
    else:
        print(json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True))


def _safe_text(value: str) -> str:
    """Escape terminal control characters in human-oriented document labels."""
    encoded = json.dumps(value, ensure_ascii=False)
    return encoded[1:-1]


def _classification(error: Exception) -> tuple[int, str, str]:
    if isinstance(error, _UsageError):
        return 2, "invalid_usage", "command usage is invalid"
    if isinstance(error, ContextNotFound):
        return 3, "not_found", "requested evidence was not found"
    if isinstance(error, ContextLimitExceeded):
        return 4, "rejected_input", "input was rejected"
    if isinstance(error, (ContextConfigurationMismatch, ContextCompilationCancelled)):
        return 5, "conflict", "operation conflicts with current state"
    if isinstance(error, ContextIntegrityFailure):
        return 6, "integrity_or_workspace", "workspace or persisted evidence is invalid"
    if isinstance(
        error,
        (SourceNotFound, DocumentNotFound, RepresentationNotFound, BlockNotFound),
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
            AmbiguousBlock,
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
        ),
    ):
        return 6, "integrity_or_workspace", "workspace or persisted evidence is invalid"
    return 1, "unexpected_failure", "operation failed"


def _failure(
    command: str,
    error: Exception,
    *,
    json_output: bool,
) -> int:
    exit_code, code, message = _classification(error)
    if json_output:
        _write_json(
            {
                "command": command,
                "error": {"code": code, "message": message},
                "ok": False,
                "schema_version": SCHEMA_VERSION,
            }
        )
    else:
        print(f"error[{code}]: {message}", file=sys.stderr)
    return exit_code


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
        _success(command, data, json_output=bool(arguments.json_output))
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 1
    except Exception as error:
        return _failure(command, error, json_output=json_requested)


if __name__ == "__main__":  # pragma: no cover - console script owns normal execution
    raise SystemExit(main())


__all__ = ["main"]
