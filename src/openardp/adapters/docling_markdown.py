"""Render retained DoclingDocument JSON into compact agent Markdown.

Rendering runs in-process on the already verified provider-native artifact produced by
the isolated parser; it parses no source bytes and imports only ``docling-core``. The
output is a disposable derived view: escaping is disabled so that quotes copied from it
match the document text, and page or slide markers let agents cite exact locations.
"""

from __future__ import annotations

import importlib.metadata
import re
import warnings
from collections.abc import Mapping
from typing import Any

from pydantic import JsonValue

from openardp.domain.agent_text import PageLabel, page_marker
from openardp.domain.ingestion import RichMediaType
from openardp.ports.agent import AgentRenderUnavailable

DOCLING_MARKDOWN_RENDERER = "openardp-docling-markdown/1"
IMAGE_PLACEHOLDER = "<!-- image -->"
# Per-page rendering must retain at least this share of the complete rendering's
# non-whitespace characters; otherwise unpaged items exist and pages are dropped.
_MIN_PAGED_COVERAGE = 0.98

_DEEP_HEADING = re.compile(r"^#{7,}(?=[ \t])", re.MULTILINE)
_EMPTY_HEADING = re.compile(r"^#{1,6}[ \t]*$", re.MULTILINE)
_TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)
_BLANK_RUN = re.compile(r"\n{3,}")


class DoclingMarkdownRenderer:
    """Versioned Docling-core Markdown renderer with page or slide markers."""

    def __init__(self) -> None:
        """Resolve the exact renderer identity, failing clearly without docling-core."""
        try:
            version = importlib.metadata.version("docling-core")
        except importlib.metadata.PackageNotFoundError as error:
            raise AgentRenderUnavailable("docling-core is not installed") from error
        self._renderer_id = f"{DOCLING_MARKDOWN_RENDERER}+docling-core-{version}"

    @property
    def renderer_id(self) -> str:
        """Return the exact versioned renderer identity recorded with each text."""
        return self._renderer_id

    def render(self, native_document: Mapping[str, JsonValue], *, media_type: str) -> str:
        """Return Markdown for one DoclingDocument, paged where the provider knows pages."""
        document = _load_document(native_document)
        label = PageLabel.SLIDE if media_type == RichMediaType.PPTX.value else PageLabel.PAGE
        complete = _export(document)
        page_numbers = sorted(int(number) for number in document.pages)
        if not page_numbers:
            return normalize_markdown(complete)
        sections = [(number, _export(document, page_no=number)) for number in page_numbers]
        paged_size = sum(_visible_size(body) for _number, body in sections)
        if paged_size < _MIN_PAGED_COVERAGE * _visible_size(complete):
            return normalize_markdown(complete)
        parts: list[str] = []
        for number, body in sections:
            parts.append(page_marker(label, number))
            if body.strip():
                parts.append(body.strip())
        return normalize_markdown("\n\n".join(parts))


def normalize_markdown(markdown: str) -> str:
    """Cap heading depth, drop empty headings, trim trailing space and blank runs."""
    text = _DEEP_HEADING.sub("######", markdown)
    text = _EMPTY_HEADING.sub("", text)
    text = _TRAILING_SPACE.sub("", text)
    text = _BLANK_RUN.sub("\n\n", text)
    return text.strip("\n")


def _visible_size(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _load_document(native_document: Mapping[str, JsonValue]) -> Any:
    try:
        from docling_core.types.doc.document import DoclingDocument
    except ImportError as error:
        raise AgentRenderUnavailable("docling-core is not installed") from error
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return DoclingDocument.model_validate(dict(native_document))


def _export(document: Any, *, page_no: int | None = None) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rendered = document.export_to_markdown(
            escape_html=False,
            escape_underscores=False,
            compact_tables=True,
            image_placeholder=IMAGE_PLACEHOLDER,
            page_no=page_no,
        )
    return str(rendered)


__all__ = [
    "DOCLING_MARKDOWN_RENDERER",
    "IMAGE_PLACEHOLDER",
    "DoclingMarkdownRenderer",
    "normalize_markdown",
]
