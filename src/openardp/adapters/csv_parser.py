"""Bounded deterministic UTF-8 CSV parser adapter."""

from __future__ import annotations

import codecs
import csv
import io
import sys
import threading
from collections.abc import Iterable
from typing import cast

from pydantic import JsonValue

from openardp.domain.block import BlockKind
from openardp.domain.identity import canonical_json_bytes, canonical_sha256
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
    MalformedCsv,
    TextDecodingError,
    TextResourceLimitExceeded,
    UnsafeTextContent,
    UnsupportedTextMedia,
)

MAX_CSV_COLUMNS = 256
MAX_CSV_FIELD_CHARACTERS = MAX_LINE_CHARACTERS
MAX_CSV_RECORD_CHARACTERS = MAX_LINE_CHARACTERS

_FIELD_LIMIT_LOCK = threading.Lock()


class CsvParserAdapter:
    """Pure CSV parser used directly by tests and inside the isolated worker."""

    def __init__(
        self,
        *,
        profile: str = "default",
        max_source_bytes: int = MAX_SOURCE_BYTES,
        max_line_characters: int = MAX_LINE_CHARACTERS,
        max_blocks: int = MAX_NORMALIZED_BLOCKS,
        max_columns: int = MAX_CSV_COLUMNS,
        max_field_characters: int = MAX_CSV_FIELD_CHARACTERS,
        max_record_characters: int = MAX_CSV_RECORD_CHARACTERS,
    ) -> None:
        """Configure the immutable CSV profile and every amplification bound."""
        if profile != "default":
            raise ValueError("unsupported parser profile")
        if max_source_bytes < 0:
            raise ValueError("max_source_bytes must be non-negative")
        if max_line_characters < 1:
            raise ValueError("max_line_characters must be positive")
        if max_blocks < 1:
            raise ValueError("max_blocks must be positive")
        if max_columns < 1:
            raise ValueError("max_columns must be positive")
        if max_field_characters < 1 or max_field_characters > sys.maxsize:
            raise ValueError("max_field_characters is invalid")
        if max_record_characters < 1:
            raise ValueError("max_record_characters must be positive")
        self._max_source_bytes = max_source_bytes
        self._max_line_characters = max_line_characters
        self._max_blocks = max_blocks
        self._max_columns = max_columns
        self._max_field_characters = max_field_characters
        self._max_record_characters = max_record_characters
        self._recipe = ParserRecipe(
            name="openardp-csv",
            version="1",
            profile=profile,
            config_hash=canonical_sha256(
                {
                    "accepted_media_types": [TextMediaType.CSV.value],
                    "bom": "single-leading-utf8-signature",
                    "dialect": {
                        "delimiter": ",",
                        "doublequote": True,
                        "escapechar": None,
                        "quotechar": '"',
                        "quoting": "minimal",
                        "skipinitialspace": False,
                        "strict": True,
                    },
                    "header": "first_logical_record",
                    "limits": {
                        "blocks": max_blocks,
                        "columns": max_columns,
                        "field_characters": max_field_characters,
                        "line_characters": max_line_characters,
                        "record_characters": max_record_characters,
                        "source_bytes": max_source_bytes,
                    },
                    "line_endings": ["cr", "crlf", "lf"],
                    "projection": "ordered-header-cell-pairs-v1",
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
        """Return whether the exact declared CSV media type is supported."""
        return media_type == TextMediaType.CSV.value

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument:
        """Parse one bounded CSV byte stream without path, network or execution access."""
        if not self.supports(media_type):
            raise UnsupportedTextMedia("unsupported text media")
        text, bom_present = self._decode(chunks)
        blocks = self._parse_records(text)
        return ParsedTextDocument(
            media_type=TextMediaType.CSV,
            blocks=tuple(blocks),
            warnings=("utf8_bom",) if bom_present else (),
            bom_present=bom_present,
        )

    def _decode(self, chunks: Iterable[bytes]) -> tuple[str, bool]:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        total_bytes = 0
        parts: list[str] = []
        try:
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise UnsafeTextContent("invalid byte stream")
                total_bytes += len(chunk)
                if total_bytes > self._max_source_bytes:
                    raise TextResourceLimitExceeded("source byte limit exceeded")
                parts.append(decoder.decode(chunk, final=False))
            parts.append(decoder.decode(b"", final=True))
        except UnicodeDecodeError as error:
            raise TextDecodingError("text decoding failed") from error
        text = "".join(parts)
        bom_present = text.startswith("\ufeff")
        if bom_present:
            text = text[1:]
        if "\x00" in text:
            raise UnsafeTextContent("unsafe text content")
        self._check_physical_lines(text)
        return text, bom_present

    def _check_physical_lines(self, text: str) -> None:
        current = 0
        for character in text:
            if character in "\r\n":
                current = 0
                continue
            current += 1
            if current > self._max_line_characters:
                raise TextResourceLimitExceeded("line character limit exceeded")

    def _parse_records(self, text: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        header: list[str] | None = None
        prior_line = 0
        with _FIELD_LIMIT_LOCK:
            previous_limit = csv.field_size_limit()
            try:
                csv.field_size_limit(self._max_field_characters)
                reader = csv.reader(
                    io.StringIO(text, newline=""),
                    delimiter=",",
                    quotechar='"',
                    doublequote=True,
                    escapechar=None,
                    skipinitialspace=False,
                    strict=True,
                )
                for record_number, row in enumerate(reader, start=1):
                    if len(blocks) >= self._max_blocks:
                        raise TextResourceLimitExceeded("normalized block limit exceeded")
                    if len(row) > self._max_columns:
                        raise TextResourceLimitExceeded("csv column limit exceeded")
                    if any(len(field) > self._max_field_characters for field in row):
                        raise TextResourceLimitExceeded("csv field limit exceeded")
                    line_end = reader.line_num
                    line_start = prior_line + 1
                    prior_line = line_end
                    if header is None:
                        header = list(row)
                        projection: dict[str, JsonValue] = {
                            "header": cast(JsonValue, header),
                            "record": record_number,
                            "type": "csv_header",
                        }
                    else:
                        fields: list[JsonValue] = [
                            [header[index] if index < len(header) else None, value]
                            for index, value in enumerate(row)
                        ]
                        projection = {
                            "fields": fields,
                            "record": record_number,
                            "type": "csv_record",
                        }
                    normalized = canonical_json_bytes(projection).decode("utf-8")
                    if len(normalized) > self._max_record_characters:
                        raise TextResourceLimitExceeded("csv record limit exceeded")
                    order = len(blocks)
                    blocks.append(
                        ParsedBlock(
                            kind=BlockKind.TABLE,
                            text=normalized,
                            parent_index=None,
                            order=order,
                            line_start=line_start,
                            line_end=line_end,
                            structural_path=("root", f"table:{order}"),
                        )
                    )
            except csv.Error as error:
                if "field larger than field limit" in str(error).casefold():
                    raise TextResourceLimitExceeded("csv field limit exceeded") from error
                raise MalformedCsv("malformed csv") from error
            finally:
                csv.field_size_limit(previous_limit)
        return blocks


__all__ = [
    "MAX_CSV_COLUMNS",
    "MAX_CSV_FIELD_CHARACTERS",
    "MAX_CSV_RECORD_CHARACTERS",
    "CsvParserAdapter",
]
