"""Deterministic unit tests for the bounded built-in text parser."""

from __future__ import annotations

import pytest

from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.block import BlockKind
from openardp.domain.ingestion import TextMediaType
from openardp.ports.parser import (
    TextDecodingError,
    TextResourceLimitExceeded,
    UnsafeTextContent,
    UnsupportedTextMedia,
)


def _parse(payload: bytes, *, media_type: str = "text/plain", split: int = 0):
    parser = TextParserAdapter()
    chunks = (
        (payload,)
        if split == 0
        else tuple(payload[index : index + split] for index in range(0, len(payload), split))
    )
    return parser.parse(chunks, media_type=media_type)


@pytest.mark.parametrize("payload", [b"", b" \t\r\n\r\n"])
def test_empty_or_whitespace_only_text_has_no_blocks(payload: bytes) -> None:
    """Accept empty evidence without inventing normalized content."""
    result = _parse(payload)
    assert result.blocks == ()


@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b"\r"])
def test_txt_paragraphs_normalize_line_endings_and_keep_line_ranges(ending: bytes) -> None:
    """Treat all documented line endings identically while retaining exact lines."""
    result = _parse(ending.join((b"  alpha  ", b"beta", b"", b"gamma")))
    assert [(block.text, block.line_start, block.line_end) for block in result.blocks] == [
        ("  alpha  \nbeta", 1, 2),
        ("gamma", 4, 4),
    ]
    assert [block.order for block in result.blocks] == [0, 1]


def test_txt_without_trailing_newline_and_split_unicode_is_stable() -> None:
    """Decode code points incrementally even when every byte is a separate chunk."""
    payload = "Grüße\n\n猫 e\u0301 é".encode()
    whole = _parse(payload)
    split = _parse(payload, split=1)
    assert split == whole
    assert [block.text for block in split.blocks] == ["Grüße", "猫 e\u0301 é"]
    assert split.blocks[1].text.endswith("e\u0301 é")


def test_leading_bom_is_recorded_and_removed_only_from_normalized_text() -> None:
    """Accept one UTF-8 signature without normalizing other Unicode content."""
    result = _parse(b"\xef\xbb\xbfhello")
    assert result.bom_present is True
    assert result.warnings == ("utf8_bom",)
    assert result.blocks[0].text == "hello"


def test_markdown_hierarchy_and_supported_block_forms() -> None:
    """Recognize only the documented source-backed Markdown subset."""
    payload = b"""Preface

# Root
body

### Skipped
~~~py
# not a heading
~~~

- first
- second

> quoted
> text

Setext
------
tail
"""
    result = _parse(payload, media_type="text/markdown", split=2)
    assert [block.kind for block in result.blocks] == [
        BlockKind.PARAGRAPH,
        BlockKind.HEADING,
        BlockKind.PARAGRAPH,
        BlockKind.HEADING,
        BlockKind.CODE,
        BlockKind.LIST,
        BlockKind.LIST_ITEM,
        BlockKind.LIST_ITEM,
        BlockKind.NOTE,
        BlockKind.HEADING,
        BlockKind.PARAGRAPH,
    ]
    assert [block.text for block in result.blocks] == [
        "Preface",
        "Root",
        "body",
        "Skipped",
        "# not a heading",
        "- first\n- second",
        "first",
        "second",
        "quoted\ntext",
        "Setext",
        "tail",
    ]
    assert result.blocks[3].parent_index == 1
    assert result.blocks[4].parent_index == 3
    assert result.blocks[6].parent_index == 5
    assert result.blocks[9].parent_index == 1
    assert result.warnings == ("heading_level_jump",)


def test_markdown_fence_delimiters_inside_code_are_literal() -> None:
    """Close a fence only with its matching character and minimum width."""
    result = _parse(
        b"````\n```\n~~~\n````\n",
        media_type=TextMediaType.MARKDOWN.value,
        split=1,
    )
    assert len(result.blocks) == 1
    assert result.blocks[0].kind is BlockKind.CODE
    assert result.blocks[0].text == "```\n~~~"
    assert (result.blocks[0].line_start, result.blocks[0].line_end) == (1, 4)


def test_unclosed_markdown_fence_is_bounded_and_warned() -> None:
    """Return source-backed code at EOF with a stable warning."""
    result = _parse(b"```\ncode", media_type="text/markdown")
    assert result.blocks[0].text == "code"
    assert result.warnings == ("unclosed_fence",)


@pytest.mark.parametrize("payload", [b">", b"> ", b">\n>"])
def test_empty_markdown_block_quote_is_ignored_with_bounded_warning(payload: bytes) -> None:
    """Accept empty source-backed quotes without inventing content or leaking validation details."""
    result = _parse(payload, media_type=TextMediaType.MARKDOWN.value, split=1)
    assert result.blocks == ()
    assert result.warnings == ("empty_block_quote_ignored",)


def test_recipe_is_stable_and_changes_with_reviewed_limits() -> None:
    """Pin all behavior-affecting parser configuration in the recipe hash."""
    default = TextParserAdapter().recipe
    assert default.name == "openardp-text"
    assert default.version == "1"
    assert default.profile == "default"
    assert default == TextParserAdapter().recipe
    assert default.config_hash != TextParserAdapter(max_source_bytes=1024).recipe.config_hash
    assert default == TextParserAdapter().recipe


@pytest.mark.parametrize("media_type", ["application/pdf", "TEXT/PLAIN", ""])
def test_unsupported_media_is_rejected_without_body_text(media_type: str) -> None:
    """Reject undeclared formats with a bounded error."""
    parser = TextParserAdapter()
    assert parser.supports(media_type) is False
    with pytest.raises(UnsupportedTextMedia, match="unsupported text media") as error:
        parser.parse((b"secret-body",), media_type=media_type)
    assert "secret-body" not in str(error.value)


def test_unsupported_profile_is_rejected() -> None:
    """Avoid accepting an unversioned parser behavior profile."""
    with pytest.raises(ValueError, match="unsupported parser profile"):
        TextParserAdapter(profile="experimental")


@pytest.mark.parametrize(
    ("payload", "error_type", "message"),
    [
        (b"\xffsecret", TextDecodingError, "text decoding failed"),
        (b"safe\x00secret", UnsafeTextContent, "unsafe text content"),
    ],
)
def test_invalid_text_errors_are_sanitized(
    payload: bytes,
    error_type: type[Exception],
    message: str,
) -> None:
    """Do not echo rejected document bytes in parser failures."""
    with pytest.raises(error_type, match=message) as error:
        _parse(payload, split=1)
    assert "secret" not in str(error.value)


def test_total_byte_limit_is_enforced_before_decoding() -> None:
    """Reject streams as soon as their configured byte bound is exceeded."""
    parser = TextParserAdapter(max_source_bytes=4)
    with pytest.raises(TextResourceLimitExceeded, match="source byte limit exceeded"):
        parser.parse((b"123", b"45"), media_type="text/plain")


def test_line_and_block_limits_are_enforced() -> None:
    """Bound adversarial line and normalized-block amplification."""
    with pytest.raises(TextResourceLimitExceeded, match="line character limit exceeded"):
        TextParserAdapter(max_line_characters=3).parse((b"abcd",), media_type="text/plain")
    with pytest.raises(TextResourceLimitExceeded, match="normalized block limit exceeded"):
        TextParserAdapter(max_blocks=1).parse(
            (b"one\n\ntwo",),
            media_type="text/plain",
        )


def test_non_bytes_chunk_is_sanitized() -> None:
    """Reject a broken provider stream without reflecting its value."""
    with pytest.raises(UnsafeTextContent, match="invalid byte stream"):
        TextParserAdapter().parse(  # type: ignore[arg-type]
            (b"safe", "secret"),
            media_type="text/plain",
        )
