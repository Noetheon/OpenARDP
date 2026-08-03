"""Local stable ingestion composition without media-specific CLI coupling."""

from __future__ import annotations

from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.ingestion import TextMediaType
from openardp.services.ingestion import IngestionService


def local_text_ingestion(
    workspace: LocalWorkspace,
    media_type: TextMediaType = TextMediaType.PLAIN,
) -> IngestionService:
    """Compose the stable text or distinct CSV recipe over local persistence."""
    parser_kind = "csv" if media_type is TextMediaType.CSV else "text"
    return IngestionService(
        workspace.object_store,
        workspace.catalog,
        IsolatedParserAdapter(parser_kind=parser_kind),
        source_factory=LocalSource,
    )


__all__ = ["local_text_ingestion"]
