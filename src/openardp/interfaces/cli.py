"""Installable stable CLI composition root for the F004 local text slice."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn
from uuid import UUID

from pydantic import BaseModel

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
)
from openardp.domain.common import SCHEMA_VERSION
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
)
from openardp.ports.object_store import ObjectStoreError
from openardp.ports.parser import ParserError, UnsupportedTextMedia
from openardp.services.document_query import DocumentQueryService
from openardp.services.ingestion import IngestionService

_COMMANDS = {"init", "ingest", "list", "status", "outline", "get"}


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

    ingest = subparsers.add_parser("ingest", help="ingest one TXT or Markdown source")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--profile", default="default")
    ingest.add_argument("--force", action="store_true")
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
    return parser


def _common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", type=Path, default=Path.cwd() / ".openardp")
    parser.add_argument("--json", action="store_true", dest="json_output")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _services(workspace: LocalWorkspace) -> tuple[IngestionService, DocumentQueryService]:
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
    return ingestion, query


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
    ingestion, query = _services(workspace)
    if command == "ingest":
        return ingestion.ingest(
            Path(arguments.path),
            profile=str(arguments.profile),
            force=bool(arguments.force),
        )
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
    else:
        print(json.dumps(converted, ensure_ascii=False, indent=2, sort_keys=True))


def _safe_text(value: str) -> str:
    """Escape terminal control characters in human-oriented document labels."""
    encoded = json.dumps(value, ensure_ascii=False)
    return encoded[1:-1]


def _classification(error: Exception) -> tuple[int, str, str]:
    if isinstance(error, _UsageError):
        return 2, "invalid_usage", "command usage is invalid"
    if isinstance(
        error,
        (SourceNotFound, DocumentNotFound, RepresentationNotFound, BlockNotFound),
    ):
        return 3, "not_found", "requested evidence was not found"
    if isinstance(
        error,
        (InvalidSourcePath, SourceTooLarge, UnsupportedTextMedia, ParserError, ValueError),
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
