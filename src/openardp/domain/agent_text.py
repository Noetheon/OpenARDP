"""Pure structure of disposable agent texts: lines, pages, headings and passages.

An agent text is the compact Markdown view an agent reads instead of the original file.
For TXT, Markdown and CSV sources it is the exact decoded source, so agent line numbers
are source line numbers. For PDF, DOCX and PPTX it is rendered from the retained
provider-native document, with ``<!-- page N -->`` or ``<!-- slide N -->`` marker lines.
"""

from __future__ import annotations

import bisect
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from pydantic import Field

from openardp.domain.common import DomainModel, Sha256Id, UtcDatetime

AGENT_TEXT_ALGORITHM = "openardp-agent-text/1"
SOURCE_TEXT_RENDERER = "openardp-source-text/1"
MAX_HEADING_LEVEL = 6

_NEWLINE = re.compile(r"\r\n|\r|\n")
_PAGE_MARKER = re.compile(r"^<!-- (page|slide) (\d{1,6}) -->$")
_ATX_HEADING = re.compile(r"^ {0,3}(#{1,64})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_SETEXT_UNDERLINE = re.compile(r"^ {0,3}(=+|-{2,})[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_TABLE_LINE = re.compile(r"^ {0,3}\|")
_LIST_OR_QUOTE = re.compile(r"^ {0,3}(?:[-+*]|\d+[.)]|>)[ \t]")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

MIN_PASSAGE_CHARACTERS = 160
TARGET_PASSAGE_CHARACTERS = 700
MAX_PASSAGE_CHARACTERS = 1_600
CSV_ROWS_PER_PASSAGE = 25
MAX_HEADING_PATH_CHARACTERS = 160


class PageLabel(StrEnum):
    """Unit a document's page markers count."""

    PAGE = "page"
    SLIDE = "slide"


class AgentHeading(DomainModel):
    """One Markdown heading line of an agent text."""

    line: int = Field(ge=1)
    level: int = Field(ge=1, le=MAX_HEADING_LEVEL)
    text: str = Field(min_length=1)


class AgentPage(DomainModel):
    """First agent-text line of one page or slide."""

    number: int = Field(ge=1)
    line: int = Field(ge=1)


class IndexedDocument(DomainModel):
    """Body-free facts about one indexed agent text."""

    document_id: str = Field(min_length=1)
    version_id: Sha256Id
    representation_id: Sha256Id
    locator: str
    label: str
    media_type: str
    renderer: str
    text_sha256: Sha256Id
    token_estimate: int = Field(ge=0)
    line_count: int = Field(ge=0)
    page_label: PageLabel | None = None
    page_count: int = Field(default=0, ge=0)
    heading_count: int = Field(default=0, ge=0)
    source_byte_length: int = Field(ge=0)
    source_modified_at: UtcDatetime | None = None
    indexed_at: UtcDatetime


class AgentTextRecord(IndexedDocument):
    """One complete agent text with its page and heading structure."""

    text: str
    pages: tuple[AgentPage, ...] = ()
    headings: tuple[AgentHeading, ...] = ()


class AgentPassage(DomainModel):
    """One retrievable passage addressed by agent-text lines."""

    document_id: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    page: int | None = Field(default=None, ge=1)
    heading: str = ""
    text: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class TextStructure:
    """Pages, page unit and headings detected in one agent text."""

    pages: tuple[AgentPage, ...]
    page_label: PageLabel | None
    headings: tuple[AgentHeading, ...]


def decode_source_text(data: bytes) -> str:
    """Decode UTF-8 source bytes exactly as the text parser numbers their lines."""
    text = data.decode("utf-8", errors="strict")
    if text.startswith("﻿"):
        text = text[1:]
    return "\n".join(split_lines(text))


def split_lines(text: str) -> list[str]:
    """Split on CRLF, CR and LF only; a final newline does not open a new line."""
    if not text:
        return []
    lines = _NEWLINE.split(text)
    if lines[-1] == "":
        lines.pop()
    return lines


def estimate_tokens(text: str) -> int:
    """Estimate model tokens as one token per four characters, rounded up."""
    return (len(text) + 3) // 4


def page_marker(label: PageLabel, number: int) -> str:
    """Return the canonical marker line opening one page or slide."""
    return f"<!-- {label.value} {number} -->"


def analyze_structure(
    lines: Sequence[str],
    *,
    markdown: bool,
    pages: bool = True,
) -> TextStructure:
    """Detect rendered page markers and, for Markdown, ATX and setext headings.

    Page markers are only structure in rendered texts; exact source texts pass
    ``pages=False`` so that a literal marker line in a user's file stays content.
    """
    page_items: list[AgentPage] = []
    headings: list[AgentHeading] = []
    page_label: PageLabel | None = None
    fence: str | None = None
    for index, line in enumerate(lines):
        number = index + 1
        marker = _PAGE_MARKER.match(line) if pages else None
        if marker is not None and fence is None:
            label = PageLabel(marker.group(1))
            page_label = page_label or label
            if label is page_label:
                page_items.append(AgentPage(number=int(marker.group(2)), line=number))
            continue
        if not markdown:
            continue
        fence_match = _FENCE.match(line)
        if fence_match is not None:
            token = fence_match.group(1)[0]
            if fence is None:
                fence = token
            elif token == fence:
                fence = None
            continue
        if fence is not None:
            continue
        heading = _heading_at(lines, index)
        if heading is not None:
            headings.append(AgentHeading(line=heading[0], level=heading[1], text=heading[2]))
    return TextStructure(pages=tuple(page_items), page_label=page_label, headings=tuple(headings))


def _heading_at(lines: Sequence[str], index: int) -> tuple[int, int, str] | None:
    line = lines[index]
    atx = _ATX_HEADING.match(line)
    if atx is not None:
        text = atx.group(2).strip()
        if text:
            return index + 1, min(len(atx.group(1)), MAX_HEADING_LEVEL), text
        return None
    if index + 1 < len(lines):
        underline = _SETEXT_UNDERLINE.match(lines[index + 1])
        text = line.strip()
        if (
            underline is not None
            and text
            and _TABLE_LINE.match(line) is None
            and _LIST_OR_QUOTE.match(line) is None
        ):
            level = 1 if underline.group(1).startswith("=") else 2
            return index + 1, level, text
    return None


def page_for_line(pages: Sequence[AgentPage], line: int) -> int | None:
    """Return the page or slide containing one agent-text line, if pages are known."""
    if not pages:
        return None
    starts = [page.line for page in pages]
    position = bisect.bisect_right(starts, line) - 1
    if position < 0:
        return None
    return pages[position].number


def heading_path(headings: Sequence[AgentHeading], line: int) -> str:
    """Return the enclosing heading path of one line, nearest heading last."""
    stack: list[AgentHeading] = []
    for heading in headings:
        if heading.line > line:
            break
        while stack and stack[-1].level >= heading.level:
            stack.pop()
        stack.append(heading)
    path = " > ".join(item.text for item in stack)
    if len(path) > MAX_HEADING_PATH_CHARACTERS:
        path = "…" + path[-(MAX_HEADING_PATH_CHARACTERS - 1) :]
    return path


def build_passages(
    document_id: str,
    lines: Sequence[str],
    structure: TextStructure,
    *,
    csv: bool = False,
) -> tuple[AgentPassage, ...]:
    """Cut an agent text into bounded retrieval passages addressed by line ranges."""
    blocks = _csv_blocks(lines) if csv else layout_passages(lines, structure)
    header = f"columns: {lines[0]}"[:MAX_HEADING_PATH_CHARACTERS] if csv and lines else ""
    passages: list[AgentPassage] = []
    for start, end in blocks:
        text = "\n".join(lines[start - 1 : end]).strip()
        if not _has_content(text):
            continue
        passages.append(
            AgentPassage(
                document_id=document_id,
                ordinal=len(passages),
                line_start=start,
                line_end=end,
                page=page_for_line(structure.pages, start),
                heading=header if csv else heading_path(structure.headings, start),
                text=text,
            )
        )
    return tuple(passages)


def _has_content(text: str) -> bool:
    """Return whether a block holds at least a few letters or digits outside comments."""
    visible = _COMMENT.sub(" ", text)
    return sum(1 for char in visible if char.isalnum()) >= 3


def _raw_blocks(lines: Sequence[str], separators: set[int]) -> list[tuple[int, int]]:
    """Group non-blank lines into blocks; fences stay whole, tables stay together."""
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    fence: str | None = None
    for index, line in enumerate(lines):
        number = index + 1
        fence_match = _FENCE.match(line)
        if fence is not None:
            if fence_match is not None and fence_match.group(1)[0] == fence:
                fence = None
            continue
        if fence_match is not None:
            if start is None:
                start = number
            fence = fence_match.group(1)[0]
            continue
        if number in separators or not line.strip():
            if start is not None:
                blocks.append((start, number - 1))
                start = None
            continue
        if start is not None and _is_table(lines[index - 1]) != _is_table(line):
            blocks.append((start, number - 1))
            start = number
            continue
        if start is None:
            start = number
    if start is not None:
        blocks.append((start, len(lines)))
    return [(first, last) for first, last in blocks if first <= last]


def _is_table(line: str) -> bool:
    return _TABLE_LINE.match(line) is not None


def _is_whole(line: str) -> bool:
    """Return whether a block starting with this line must never be merged."""
    return _is_table(line) or _FENCE.match(line) is not None


def _span_length(lines: Sequence[str], start: int, end: int) -> int:
    return sum(len(line) + 1 for line in lines[start - 1 : end])


def layout_passages(
    lines: Sequence[str],
    structure: TextStructure,
) -> list[tuple[int, int]]:
    """Return final passage line ranges: split oversized blocks, merge small neighbours."""
    heading_lines = {heading.line for heading in structure.headings}
    heading_lines.update(
        heading.line + 1
        for heading in structure.headings
        if heading.line < len(lines) and _SETEXT_UNDERLINE.match(lines[heading.line])
    )
    separators = heading_lines | {page.line for page in structure.pages}
    split: list[tuple[int, int]] = []
    for start, end in _raw_blocks(lines, separators):
        if _has_content("\n".join(lines[start - 1 : end])):
            split.extend(_split_block(lines, start, end))
    return _merge_blocks(lines, split, structure)


def _split_block(lines: Sequence[str], start: int, end: int) -> list[tuple[int, int]]:
    if _span_length(lines, start, end) <= MAX_PASSAGE_CHARACTERS:
        return [(start, end)]
    pieces: list[tuple[int, int]] = []
    first = start
    size = 0
    for number in range(start, end + 1):
        width = len(lines[number - 1]) + 1
        if size and size + width > MAX_PASSAGE_CHARACTERS:
            pieces.append((first, number - 1))
            first = number
            size = 0
        size += width
    pieces.append((first, end))
    return pieces


def _merge_blocks(
    lines: Sequence[str],
    blocks: list[tuple[int, int]],
    structure: TextStructure,
) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in blocks:
        if merged:
            previous_start, previous_end = merged[-1]
            same_context = page_for_line(structure.pages, previous_start) == page_for_line(
                structure.pages, start
            ) and heading_path(structure.headings, previous_start) == heading_path(
                structure.headings, start
            )
            previous_size = _span_length(lines, previous_start, previous_end)
            current_size = _span_length(lines, start, end)
            if (
                same_context
                and not _is_whole(lines[start - 1])
                and not _is_whole(lines[previous_start - 1])
                and min(previous_size, current_size) < MIN_PASSAGE_CHARACTERS
                and previous_size + current_size <= TARGET_PASSAGE_CHARACTERS
            ):
                merged[-1] = (previous_start, end)
                continue
        merged.append((start, end))
    return merged


def _csv_blocks(lines: Sequence[str]) -> list[tuple[int, int]]:
    """Group CSV data rows into bounded runs after the header row."""
    blocks: list[tuple[int, int]] = []
    if len(lines) < 2:
        return [(1, len(lines))] if lines else []
    start = 2
    size = 0
    count = 0
    for number in range(2, len(lines) + 1):
        width = len(lines[number - 1]) + 1
        if count and (count >= CSV_ROWS_PER_PASSAGE or size + width > MAX_PASSAGE_CHARACTERS):
            blocks.append((start, number - 1))
            start = number
            size = 0
            count = 0
        size += width
        count += 1
    blocks.append((start, len(lines)))
    return blocks


__all__ = [
    "AGENT_TEXT_ALGORITHM",
    "MAX_HEADING_LEVEL",
    "SOURCE_TEXT_RENDERER",
    "AgentHeading",
    "AgentPage",
    "AgentPassage",
    "AgentTextRecord",
    "IndexedDocument",
    "PageLabel",
    "TextStructure",
    "analyze_structure",
    "build_passages",
    "decode_source_text",
    "estimate_tokens",
    "heading_path",
    "layout_passages",
    "page_for_line",
    "page_marker",
    "split_lines",
]
