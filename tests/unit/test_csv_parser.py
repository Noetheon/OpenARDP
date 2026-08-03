"""Deterministic unit tests for the bounded built-in CSV parser."""

from __future__ import annotations

import json

import pytest

from openardp.adapters.csv_parser import CsvParserAdapter
from openardp.domain.block import BlockKind
from openardp.domain.ingestion import TextMediaType
from openardp.ports.parser import (
    MalformedCsv,
    TextDecodingError,
    TextResourceLimitExceeded,
    UnsafeTextContent,
    UnsupportedTextMedia,
)


def _parse(payload: bytes, *, split: int = 0):
    parser = CsvParserAdapter()
    chunks = (
        (payload,)
        if split == 0
        else tuple(payload[index : index + split] for index in range(0, len(payload), split))
    )
    return parser.parse(chunks, media_type=TextMediaType.CSV.value)


def _records(payload: bytes, *, split: int = 0) -> list[dict[str, object]]:
    return [json.loads(block.text) for block in _parse(payload, split=split).blocks]


@pytest.mark.parametrize("payload", [b"", b"\xef\xbb\xbf"])
def test_empty_csv_has_no_invented_records(payload: bytes) -> None:
    """Accept an empty table while retaining BOM evidence when present."""
    result = _parse(payload, split=1)
    assert result.blocks == ()
    assert result.bom_present == (payload != b"")
    assert result.warnings == (("utf8_bom",) if payload else ())


def test_csv_preserves_headers_cells_ragged_rows_and_unicode() -> None:
    """Keep ordered logical values without mapping coercion or type inference."""
    payload = (
        '\ufeffname,name,,note\r\n"Grüße","猫",,"quoted, value"\r\nshort\r\nwide,2,3,4,overflow\r\n'
    ).encode()
    result = _parse(payload, split=1)

    assert result.media_type is TextMediaType.CSV
    assert result.warnings == ("utf8_bom",)
    assert [block.kind for block in result.blocks] == [BlockKind.TABLE] * 4
    assert [(block.line_start, block.line_end) for block in result.blocks] == [
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
    ]
    assert _records(payload, split=1) == [
        {
            "header": ["name", "name", "", "note"],
            "record": 1,
            "type": "csv_header",
        },
        {
            "fields": [
                ["name", "Grüße"],
                ["name", "猫"],
                ["", ""],
                ["note", "quoted, value"],
            ],
            "record": 2,
            "type": "csv_record",
        },
        {
            "fields": [["name", "short"]],
            "record": 3,
            "type": "csv_record",
        },
        {
            "fields": [
                ["name", "wide"],
                ["name", "2"],
                ["", "3"],
                ["note", "4"],
                [None, "overflow"],
            ],
            "record": 4,
            "type": "csv_record",
        },
    ]


def test_csv_preserves_quoted_newlines_and_exact_physical_ranges() -> None:
    """Keep embedded newlines in fields and attribute every consumed physical line."""
    payload = b'key,description\nA,"first\nsecond"\nB,"third\r\nfourth"'
    result = _parse(payload, split=2)
    records = [json.loads(block.text) for block in result.blocks]

    assert [(block.line_start, block.line_end) for block in result.blocks] == [
        (1, 1),
        (2, 3),
        (4, 5),
    ]
    assert records[1]["fields"] == [["key", "A"], ["description", "first\nsecond"]]
    assert records[2]["fields"] == [["key", "B"], ["description", "third\r\nfourth"]]


def test_formula_like_cells_remain_inert_exact_strings() -> None:
    """Do not execute, escape, rewrite or infer spreadsheet formula cells."""
    records = _records(b"kind,value\nformula,=2+3\ncommand,@SUM(A1:A2)\n")
    assert records[1]["fields"] == [["kind", "formula"], ["value", "=2+3"]]
    assert records[2]["fields"] == [["kind", "command"], ["value", "@SUM(A1:A2)"]]


def test_csv_recipe_is_distinct_and_text_recipe_need_not_change() -> None:
    """Pin every behavior-affecting CSV setting behind its own recipe identity."""
    default = CsvParserAdapter().recipe
    assert default.name == "openardp-csv"
    assert default.version == "1"
    assert default.profile == "default"
    assert default == CsvParserAdapter().recipe
    assert default.config_hash != CsvParserAdapter(max_columns=2).recipe.config_hash


@pytest.mark.parametrize("media_type", ["text/plain", "TEXT/CSV", ""])
def test_csv_parser_rejects_undeclared_media(media_type: str) -> None:
    """Expose one exact closed media capability without reflecting source content."""
    parser = CsvParserAdapter()
    assert parser.supports(media_type) is False
    with pytest.raises(UnsupportedTextMedia, match="unsupported text media") as error:
        parser.parse((b"secret-body",), media_type=media_type)
    assert "secret-body" not in str(error.value)


@pytest.mark.parametrize(
    ("payload", "error_type", "message"),
    [
        (b"head\n\xffsecret", TextDecodingError, "text decoding failed"),
        (b"head\nsafe\x00secret", UnsafeTextContent, "unsafe text content"),
        (b'head\n"unclosed', MalformedCsv, "malformed csv"),
    ],
)
def test_csv_failures_are_typed_and_body_free(
    payload: bytes,
    error_type: type[Exception],
    message: str,
) -> None:
    """Reject invalid tables with stable classifications and no cell reflection."""
    with pytest.raises(error_type, match=message) as error:
        _parse(payload, split=1)
    assert "secret" not in str(error.value)
    assert "unclosed" not in str(error.value)


def test_csv_resource_limits_bound_source_fields_columns_records_and_projection() -> None:
    """Bound input and all material amplification dimensions independently."""
    with pytest.raises(TextResourceLimitExceeded, match="source byte limit exceeded"):
        CsvParserAdapter(max_source_bytes=3).parse((b"1234",), media_type="text/csv")
    with pytest.raises(TextResourceLimitExceeded, match="line character limit exceeded"):
        CsvParserAdapter(max_line_characters=3).parse((b"abcd",), media_type="text/csv")
    with pytest.raises(TextResourceLimitExceeded, match="csv field limit exceeded"):
        CsvParserAdapter(max_field_characters=3).parse((b"head\nabcd",), media_type="text/csv")
    with pytest.raises(TextResourceLimitExceeded, match="csv column limit exceeded"):
        CsvParserAdapter(max_columns=2).parse((b"a,b,c",), media_type="text/csv")
    with pytest.raises(TextResourceLimitExceeded, match="normalized block limit exceeded"):
        CsvParserAdapter(max_blocks=1).parse((b"head\nvalue",), media_type="text/csv")
    with pytest.raises(TextResourceLimitExceeded, match="csv record limit exceeded"):
        CsvParserAdapter(max_record_characters=40).parse((b"header\nvalue",), media_type="text/csv")


def test_csv_rejects_non_bytes_without_reflection() -> None:
    """Sanitize broken provider streams before CSV interpretation."""
    with pytest.raises(UnsafeTextContent, match="invalid byte stream"):
        CsvParserAdapter().parse(  # type: ignore[arg-type]
            (b"safe", "secret"),
            media_type="text/csv",
        )
