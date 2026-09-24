"""Agent texts for DOCX and PPTX: Docling rendering, slide markers and fallback."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from openardp.adapters.docling_markdown import DoclingMarkdownRenderer, normalize_markdown
from openardp.adapters.local_workspace import LocalWorkspace
from openardp.domain.agent_text import PageLabel
from openardp.domain.ingestion import RepresentationScope
from openardp.interfaces.agent_composition import local_agent_access
from openardp.interfaces.cli import main
from openardp.ports.agent import AgentRenderUnavailable
from openardp.ports.catalog import RepresentationIntegrityError
from openardp.services.agent_texts import PROJECTION_TEXT_RENDERER, AgentTextBuilder

pytest.importorskip("docling")

FIXTURES = Path(__file__).parents[1] / "fixtures" / "rich"


@pytest.fixture(scope="module")
def rich_store(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Prepare the synthetic DOCX and PPTX once through the public add command."""
    store = tmp_path_factory.mktemp("rich") / "store"
    code = main(
        [
            "add",
            str(FIXTURES / "synthetic.docx"),
            str(FIXTURES / "synthetic.pptx"),
            "--store",
            str(store),
            "--json",
        ]
    )
    assert code == 0
    return store


def test_rich_documents_become_paged_markdown_agent_texts(rich_store: Path) -> None:
    """Render slides with markers, keep DOCX unpaged and make both searchable."""
    access = local_agent_access(LocalWorkspace.open(rich_store))
    documents = {entry.label: entry for entry in access.documents().documents}
    deck = documents["synthetic.pptx"]
    assert deck.page_label is PageLabel.SLIDE and deck.page_count == 2
    first_slide = access.read("synthetic.pptx", page="1")
    assert first_slide.pages == (1,) and first_slide.text.strip()
    assert documents["synthetic.docx"].page_count == 0
    word = access.find(first_slide.text.split()[-1])
    assert word.hits
    quote = first_slide.text.strip().splitlines()[-1].lstrip("#- ").strip()
    verified = access.verify(quote, document="synthetic.pptx")
    assert verified.matches and verified.matches[0].page == 1


def test_projection_fallback_renders_without_docling_core(rich_store: Path) -> None:
    """Build provider-free agent texts from accepted projections when no renderer exists."""
    workspace = LocalWorkspace.open(rich_store)
    access = local_agent_access(workspace)
    deck = access.resolve("synthetic.pptx")

    def unavailable() -> DoclingMarkdownRenderer:
        raise AgentRenderUnavailable("docling-core is not installed")

    builder = AgentTextBuilder(
        workspace.object_store,
        workspace.catalog,
        renderer_factory=unavailable,
    )
    assert builder.expected_renderer(deck.media_type) == PROJECTION_TEXT_RENDERER
    summary = next(
        item for item in builder.ready_summaries() if str(item.document_id) == deck.document_id
    )
    built = builder.build(summary)
    assert built.record.renderer == PROJECTION_TEXT_RENDERER
    assert "<!-- slide 1 -->" in built.record.text and built.passages


def test_markdown_normalization_caps_depth_and_trims_noise() -> None:
    """Cap headings at six levels, drop empty headings and collapse blank runs."""
    raw = "########## Deep\n\n\n\n## \nText   \n"
    assert normalize_markdown(raw) == "###### Deep\n\nText"


def test_native_object_lookup_reads_only_the_accepted_attempt(
    rich_store: Path,
    tmp_path: Path,
) -> None:
    """Name the accepted native object from catalog facts and refuse inconsistent rows."""
    workspace = LocalWorkspace.open(rich_store)
    deck = local_agent_access(workspace).resolve("synthetic.pptx")
    scope = RepresentationScope(
        document_id=UUID(deck.document_id),
        version_id=deck.version_id,
        representation_id=deck.representation_id,
    )
    artifacts = workspace.catalog.load_rich_representation(scope)
    assert artifacts is not None
    native = workspace.catalog.accepted_rich_native_object(scope)
    assert native == artifacts.accepted_attempt.provider_native_object
    unknown = scope.model_copy(update={"representation_id": "sha256:" + "0" * 64})
    assert workspace.catalog.accepted_rich_native_object(unknown) is None
    copy = tmp_path / "store"
    shutil.copytree(rich_store, copy)
    with sqlite3.connect(copy / "catalog.sqlite3") as connection:
        connection.execute(
            "UPDATE rich_parse_attempts SET provider_native_object_id = ?",
            ("sha256:" + "f" * 64,),
        )
    with pytest.raises(RepresentationIntegrityError):
        LocalWorkspace.open(copy).catalog.accepted_rich_native_object(scope)
