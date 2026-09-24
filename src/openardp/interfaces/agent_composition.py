"""Compose token-efficient agent access over one open local workspace."""

from __future__ import annotations

from collections.abc import Callable

from openardp.adapters.agent_index import SQLiteAgentIndex
from openardp.adapters.docling_markdown import DoclingMarkdownRenderer
from openardp.adapters.local_source import LocalSource
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.ingestion import SourceStatus, StatusMode
from openardp.interfaces.ingestion_composition import local_text_ingestion
from openardp.services.agent_access import AgentAccessService
from openardp.services.agent_texts import AgentTextBuilder
from openardp.services.document_query import DocumentQueryService


def local_status_probe(workspace: LocalWorkspace) -> Callable[[str], SourceStatus]:
    """Return the exact HEAD freshness probe for a document id or a local source path."""
    text_ingestion = local_text_ingestion(workspace)
    query = DocumentQueryService(
        workspace.object_store,
        workspace.catalog,
        source_factory=LocalSource,
        representation_verifier=text_ingestion.verify_ready_representation,
    )

    def probe(target: str) -> SourceStatus:
        return query.status(target, mode=StatusMode.HEAD)

    return probe


def local_agent_access(workspace: LocalWorkspace) -> AgentAccessService:
    """Compose agent access from the catalog, the object store and a disposable index."""
    builder = AgentTextBuilder(
        workspace.object_store,
        workspace.catalog,
        renderer_factory=DoclingMarkdownRenderer,
    )
    return AgentAccessService(
        builder,
        SQLiteAgentIndex.for_workspace(workspace.root),
        status_probe=local_status_probe(workspace),
    )


__all__ = ["local_agent_access", "local_status_probe"]
