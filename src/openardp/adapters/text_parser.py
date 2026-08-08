"""Bounded deterministic UTF-8 TXT and Markdown parser adapter."""

from __future__ import annotations

import codecs
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence

from openardp.domain.block import BlockKind
from openardp.domain.identity import canonical_sha256
from openardp.domain.ingestion import (
    MAX_LINE_CHARACTERS,
    MAX_NORMALIZED_BLOCKS,
    MAX_SOURCE_BYTES,
    ParsedBlock,
    ParsedTextDocument,
    ParserRecipe,
    TextMediaType,
)
from openardp.ports.parser import (
    TextDecodingError,
    TextResourceLimitExceeded,
    UnsafeTextContent,
    UnsupportedTextMedia,
)

_ATX_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$")
_SETEXT_HEADING = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")
_LIST_ITEM = re.compile(r"^ {0,3}([-+*]|\d+[.)])[ \t]+(.*)$")
_BLOCK_QUOTE = re.compile(r"^ {0,3}>[ \t]?(.*)$")


class _BlockBuilder:
    """Build candidates while enforcing ordering and amplification limits."""

    def __init__(self, *, max_blocks: int) -> None:
        self.blocks: list[ParsedBlock] = []
        self._next_order: defaultdict[int | None, int] = defaultdict(int)
        self._max_blocks = max_blocks

    def add(
        self,
        *,
        kind: BlockKind,
        text: str,
        parent_index: int | None,
        line_start: int,
        line_end: int,
    ) -> int:
        """Append one deterministic block and return its global index."""
        if len(self.blocks) >= self._max_blocks:
            raise TextResourceLimitExceeded("normalized block limit exceeded")
        order = self._next_order[parent_index]
        parent_path = (
            ("root",) if parent_index is None else self.blocks[parent_index].structural_path
        )
        block = ParsedBlock(
            kind=kind,
            text=text,
            parent_index=parent_index,
            order=order,
            line_start=line_start,
            line_end=line_end,
            structural_path=(*parent_path, f"{kind.value}:{order}"),
        )
        self.blocks.append(block)
        self._next_order[parent_index] += 1
        return len(self.blocks) - 1


class _MarkdownParser:
    """Consume the reviewed Markdown subset through explicit bounded transitions."""

    def __init__(self, *, max_blocks: int) -> None:
        self._builder = _BlockBuilder(max_blocks=max_blocks)
        self._warnings: set[str] = set()
        self._heading_by_level: dict[int, int] = {}
        self._active_heading: int | None = None
        self._previous_heading_level = 0
        self._paragraph: list[tuple[int, str]] = []

    def parse(self, lines: Sequence[tuple[int, str]]) -> tuple[list[ParsedBlock], set[str]]:
        """Return exact blocks and warnings for one normalized line sequence."""
        index = 0
        while index < len(lines):
            line_number, line = lines[index]
            if not line.strip():
                self._flush_paragraph()
                index += 1
            elif (next_index := self._consume_fence(lines, index)) is not None:
                index = next_index
            elif self._consume_atx(line_number, line):
                index += 1
            else:
                next_index = self._consume_compound(lines, index)
                if next_index is None:
                    self._paragraph.append((line_number, line))
                    index += 1
                else:
                    index = next_index
        self._flush_paragraph()
        return self._builder.blocks, self._warnings

    def _consume_compound(self, lines: Sequence[tuple[int, str]], index: int) -> int | None:
        for consumer in (self._consume_setext, self._consume_list, self._consume_quote):
            if (next_index := consumer(lines, index)) is not None:
                return next_index
        return None

    def _consume_fence(self, lines: Sequence[tuple[int, str]], index: int) -> int | None:
        line_number, line = lines[index]
        fence = _FENCE_OPEN.match(line)
        if fence is None:
            return None
        self._flush_paragraph()
        marker = fence.group(1)
        closing = re.compile(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$")
        body: list[str] = []
        end_line = line_number
        index += 1
        while index < len(lines):
            current_number, current = lines[index]
            end_line = current_number
            if closing.match(current):
                index += 1
                break
            body.append(current)
            index += 1
        else:
            self._warnings.add("unclosed_fence")
        self._builder.add(
            kind=BlockKind.CODE,
            text="\n".join(body),
            parent_index=self._active_heading,
            line_start=line_number,
            line_end=end_line,
        )
        return index

    def _consume_atx(self, line_number: int, line: str) -> bool:
        atx = _ATX_HEADING.match(line)
        if atx is None:
            return False
        self._flush_paragraph()
        text = _strip_atx_closing(atx.group(2) or "")
        if text:
            self._add_heading(
                text,
                level=len(atx.group(1)),
                start=line_number,
                end=line_number,
            )
        else:
            self._warnings.add("empty_heading_ignored")
        return True

    def _consume_setext(self, lines: Sequence[tuple[int, str]], index: int) -> int | None:
        if index + 1 >= len(lines):
            return None
        line_number, line = lines[index]
        next_number, next_line = lines[index + 1]
        setext = _SETEXT_HEADING.match(next_line)
        if setext is None or not line.strip():
            return None
        self._flush_paragraph()
        self._add_heading(
            line,
            level=1 if setext.group(1).startswith("=") else 2,
            start=line_number,
            end=next_number,
        )
        return index + 2

    def _consume_list(self, lines: Sequence[tuple[int, str]], index: int) -> int | None:
        first = _LIST_ITEM.match(lines[index][1])
        if first is None:
            return None
        self._flush_paragraph()
        ordered = first.group(1)[0].isdigit()
        members: list[tuple[int, str, str]] = []
        while index < len(lines):
            line_number, line = lines[index]
            item = _LIST_ITEM.match(line)
            if item is None or item.group(1)[0].isdigit() != ordered:
                break
            if item.group(2):
                members.append((line_number, line, item.group(2)))
            else:
                self._warnings.add("empty_list_item_ignored")
            index += 1
        self._add_list_members(members)
        return index

    def _add_list_members(self, members: Sequence[tuple[int, str, str]]) -> None:
        if not members:
            return
        list_index = self._builder.add(
            kind=BlockKind.LIST,
            text="\n".join(raw for _, raw, _ in members),
            parent_index=self._active_heading,
            line_start=members[0][0],
            line_end=members[-1][0],
        )
        for line_number, _, text in members:
            self._builder.add(
                kind=BlockKind.LIST_ITEM,
                text=text,
                parent_index=list_index,
                line_start=line_number,
                line_end=line_number,
            )

    def _consume_quote(self, lines: Sequence[tuple[int, str]], index: int) -> int | None:
        if _BLOCK_QUOTE.match(lines[index][1]) is None:
            return None
        self._flush_paragraph()
        quoted: list[tuple[int, str]] = []
        while index < len(lines):
            line_number, line = lines[index]
            quote = _BLOCK_QUOTE.match(line)
            if quote is None:
                break
            quoted.append((line_number, quote.group(1)))
            index += 1
        text = "\n".join(value for _, value in quoted)
        if text.strip():
            self._builder.add(
                kind=BlockKind.NOTE,
                text=text,
                parent_index=self._active_heading,
                line_start=quoted[0][0],
                line_end=quoted[-1][0],
            )
        else:
            self._warnings.add("empty_block_quote_ignored")
        return index

    def _add_heading(self, text: str, *, level: int, start: int, end: int) -> None:
        if self._previous_heading_level and level > self._previous_heading_level + 1:
            self._warnings.add("heading_level_jump")
        candidates = [item for item in self._heading_by_level if item < level]
        parent = self._heading_by_level[max(candidates)] if candidates else None
        self._active_heading = self._builder.add(
            kind=BlockKind.HEADING,
            text=text,
            parent_index=parent,
            line_start=start,
            line_end=end,
        )
        self._heading_by_level[level] = self._active_heading
        for stale_level in [item for item in self._heading_by_level if item > level]:
            del self._heading_by_level[stale_level]
        self._previous_heading_level = level

    def _flush_paragraph(self) -> None:
        if not self._paragraph:
            return
        self._builder.add(
            kind=BlockKind.PARAGRAPH,
            text="\n".join(text for _, text in self._paragraph),
            parent_index=self._active_heading,
            line_start=self._paragraph[0][0],
            line_end=self._paragraph[-1][0],
        )
        self._paragraph.clear()


class TextParserAdapter:
    """Pure deterministic parser used directly only by tests and isolated workers."""

    def __init__(
        self,
        *,
        profile: str = "default",
        max_source_bytes: int = MAX_SOURCE_BYTES,
        max_line_characters: int = MAX_LINE_CHARACTERS,
        max_blocks: int = MAX_NORMALIZED_BLOCKS,
    ) -> None:
        """Configure the reviewed profile and hard resource bounds."""
        if profile != "default":
            raise ValueError("unsupported parser profile")
        if max_source_bytes < 0:
            raise ValueError("max_source_bytes must be non-negative")
        if max_line_characters < 1:
            raise ValueError("max_line_characters must be positive")
        if max_blocks < 1:
            raise ValueError("max_blocks must be positive")
        self._profile = profile
        self._max_source_bytes = max_source_bytes
        self._max_line_characters = max_line_characters
        self._max_blocks = max_blocks
        self._recipe = ParserRecipe(
            name="openardp-text",
            version="1",
            profile=profile,
            config_hash=canonical_sha256(
                {
                    "accepted_media_types": [
                        TextMediaType.MARKDOWN.value,
                        TextMediaType.PLAIN.value,
                    ],
                    "bom": "single-leading-utf8-signature",
                    "limits": {
                        "blocks": max_blocks,
                        "line_characters": max_line_characters,
                        "source_bytes": max_source_bytes,
                    },
                    "markdown_subset": [
                        "atx_heading",
                        "setext_heading",
                        "paragraph",
                        "fenced_code",
                        "list",
                        "list_item",
                        "block_quote",
                    ],
                    "newline_normalization": "lf",
                    "utf8_errors": "strict",
                }
            ),
            normalization_schema_version="0.1.0",
        )

    @property
    def recipe(self) -> ParserRecipe:
        """Return the immutable behavior recipe for this adapter."""
        return self._recipe

    def supports(self, media_type: str) -> bool:
        """Return whether the exact declared text media type is supported."""
        return media_type in {item.value for item in TextMediaType}

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument:
        """Parse a bounded byte stream without path, network or model access."""
        if not self.supports(media_type):
            raise UnsupportedTextMedia("unsupported text media")
        lines, bom_present = self._decode_lines(chunks)
        if media_type == TextMediaType.PLAIN.value:
            blocks, warnings = self._parse_plain(lines)
        else:
            blocks, warnings = self._parse_markdown(lines)
        if bom_present:
            warnings.add("utf8_bom")
        return ParsedTextDocument(
            media_type=TextMediaType(media_type),
            blocks=tuple(blocks),
            warnings=tuple(sorted(warnings)),
            bom_present=bom_present,
        )

    def _decode_lines(self, chunks: Iterable[bytes]) -> tuple[list[tuple[int, str]], bool]:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        total_bytes = 0
        buffer = ""
        lines: list[tuple[int, str]] = []
        bom_present = False
        first_character_pending = True
        saw_input = False

        def consume(text: str, *, final: bool) -> None:
            nonlocal buffer, bom_present, first_character_pending
            if first_character_pending and text:
                first_character_pending = False
                if text.startswith("\ufeff"):
                    bom_present = True
                    text = text[1:]
            if "\x00" in text:
                raise UnsafeTextContent("unsafe text content")
            buffer += text
            cursor = 0
            while cursor < len(buffer):
                newline = _next_newline(buffer, cursor)
                if newline is None:
                    break
                index, width = newline
                if width == 0 and not final:
                    break
                if width == 0:
                    width = 1
                _append_bounded_line(
                    lines,
                    buffer[cursor:index],
                    max_characters=self._max_line_characters,
                )
                cursor = index + width
            buffer = buffer[cursor:]
            pending_cr = not final and buffer.endswith("\r")
            measurable = buffer[:-1] if pending_cr else buffer
            if len(measurable) > self._max_line_characters:
                raise TextResourceLimitExceeded("line character limit exceeded")

        try:
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise UnsafeTextContent("invalid byte stream")
                saw_input = saw_input or bool(chunk)
                total_bytes += len(chunk)
                if total_bytes > self._max_source_bytes:
                    raise TextResourceLimitExceeded("source byte limit exceeded")
                consume(decoder.decode(chunk, final=False), final=False)
            consume(decoder.decode(b"", final=True), final=True)
        except UnicodeDecodeError as error:
            raise TextDecodingError("text decoding failed") from error

        if buffer:
            _append_bounded_line(
                lines,
                buffer,
                max_characters=self._max_line_characters,
            )
        elif saw_input and not lines:
            # A stream containing only a BOM still has no source-backed line content.
            pass
        return lines, bom_present

    def _parse_plain(
        self,
        lines: Sequence[tuple[int, str]],
    ) -> tuple[list[ParsedBlock], set[str]]:
        builder = _BlockBuilder(max_blocks=self._max_blocks)
        paragraph: list[tuple[int, str]] = []

        def flush() -> None:
            if not paragraph:
                return
            builder.add(
                kind=BlockKind.PARAGRAPH,
                text="\n".join(text for _, text in paragraph),
                parent_index=None,
                line_start=paragraph[0][0],
                line_end=paragraph[-1][0],
            )
            paragraph.clear()

        for line_number, line in lines:
            if line.strip():
                paragraph.append((line_number, line))
            else:
                flush()
        flush()
        return builder.blocks, set()

    def _parse_markdown(
        self,
        lines: Sequence[tuple[int, str]],
    ) -> tuple[list[ParsedBlock], set[str]]:
        """Parse the reviewed Markdown subset through bounded transitions."""
        return _MarkdownParser(max_blocks=self._max_blocks).parse(lines)


def _next_newline(value: str, start: int) -> tuple[int, int] | None:
    """Return the next normalized newline position and consumed width."""
    cr = value.find("\r", start)
    lf = value.find("\n", start)
    candidates = [index for index in (cr, lf) if index >= 0]
    if not candidates:
        return None
    index = min(candidates)
    if value[index] == "\r":
        if index + 1 == len(value):
            return index, 0
        return index, 2 if value[index + 1] == "\n" else 1
    return index, 1


def _append_bounded_line(
    lines: list[tuple[int, str]],
    value: str,
    *,
    max_characters: int,
) -> None:
    """Append a line after enforcing the character bound."""
    if len(value) > max_characters:
        raise TextResourceLimitExceeded("line character limit exceeded")
    lines.append((len(lines) + 1, value))


def _strip_atx_closing(value: str) -> str:
    """Remove optional whitespace-delimited closing ATX markers."""
    return re.sub(r"[ \t]+#+[ \t]*$", "", value).strip()


__all__ = ["TextParserAdapter"]
