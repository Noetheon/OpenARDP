"""Pure agent-text structure: lines, pages, headings, tokens and passages."""

from __future__ import annotations

import pytest

from openardp.adapters.text_parser import TextParserAdapter
from openardp.domain.agent_text import (
    MAX_HEADING_PATH_CHARACTERS,
    MAX_PASSAGE_CHARACTERS,
    AgentHeading,
    AgentPage,
    PageLabel,
    analyze_structure,
    build_passages,
    decode_source_text,
    estimate_tokens,
    heading_path,
    page_for_line,
    page_marker,
    split_lines,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", []),
        ("\n", [""]),
        ("a", ["a"]),
        ("a\n", ["a"]),
        ("a\n\n", ["a", ""]),
        ("a\r\nb", ["a", "b"]),
        ("a\rb\r", ["a", "b"]),
        ("a\x0bb\u2028c", ["a\x0bb\u2028c"]),
    ],
)
def test_split_lines_uses_only_parser_newlines(text: str, expected: list[str]) -> None:
    """Split on CRLF, CR and LF only, like the text parser, never on other separators."""
    assert split_lines(text) == expected


def test_decoded_source_lines_match_text_parser_line_numbers() -> None:
    """Keep agent line numbers identical to the parser's source-backed line ranges."""
    source = (
        "﻿# Title\r\n\r\nFirst paragraph\rcontinues here.\n\n- item one\n- item two\n\n"
        "```\ncode block\n```\nSetext\n======\n"
    ).encode()
    parsed = TextParserAdapter().parse((source,), media_type="text/markdown")
    lines = decode_source_text(source).split("\n")
    for block in parsed.blocks:
        excerpt = lines[block.line_start - 1 : block.line_end]
        assert block.text.split("\n")[0].lstrip("#- ").strip() in "\n".join(excerpt)
    assert lines[0] == "# Title"
    assert decode_source_text(b"a\r\nb\r\n") == "a\nb"


def test_estimate_tokens_rounds_up_four_characters_per_token() -> None:
    """Estimate conservatively enough for budgeting without a tokenizer."""
    assert [estimate_tokens(text) for text in ("", "a", "abcd", "abcde")] == [0, 1, 1, 2]


def test_structure_detects_headings_outside_fences_and_caps_levels() -> None:
    """Find ATX and setext headings, skip fenced code and cap depth at six."""
    lines = [
        "# One ##",
        "",
        "```",
        "# not a heading",
        "```",
        "########### Deep",
        "Setext title",
        "------------",
        "| a | b |",
        "|---|---|",
    ]
    structure = analyze_structure(lines, markdown=True)
    assert [(item.line, item.level, item.text) for item in structure.headings] == [
        (1, 1, "One"),
        (6, 6, "Deep"),
        (7, 2, "Setext title"),
    ]
    assert analyze_structure(lines, markdown=False).headings == ()


def test_page_markers_count_only_in_rendered_texts() -> None:
    """Treat marker lines as pages only when asked, keeping the first unit."""
    lines = [page_marker(PageLabel.SLIDE, 1), "a", page_marker(PageLabel.PAGE, 9), "b"]
    lines.append(page_marker(PageLabel.SLIDE, 2))
    structure = analyze_structure(lines, markdown=True)
    assert structure.page_label is PageLabel.SLIDE
    assert structure.pages == (AgentPage(number=1, line=1), AgentPage(number=2, line=5))
    assert analyze_structure(lines, markdown=True, pages=False).pages == ()


def test_page_and_heading_lookup() -> None:
    """Resolve the enclosing page and a bounded nearest-last heading path."""
    pages = (AgentPage(number=3, line=10), AgentPage(number=4, line=20))
    assert page_for_line((), 5) is None
    assert page_for_line(pages, 5) is None
    assert page_for_line(pages, 10) == 3
    assert page_for_line(pages, 99) == 4
    headings = (
        AgentHeading(line=1, level=1, text="Report"),
        AgentHeading(line=5, level=2, text="Results"),
        AgentHeading(line=9, level=3, text="Details"),
        AgentHeading(line=12, level=2, text="Appendix"),
    )
    assert heading_path(headings, 10) == "Report > Results > Details"
    assert heading_path(headings, 13) == "Report > Appendix"
    long = (AgentHeading(line=1, level=1, text="x" * 400),)
    path = heading_path(long, 2)
    assert len(path) == MAX_HEADING_PATH_CHARACTERS and path.startswith("…")


def test_passages_follow_blocks_tables_fences_and_skip_empty_content() -> None:
    """Cut passages at blank lines and headings; keep tables and fences whole."""
    lines = [
        "# Guide",
        "",
        "Short intro.",
        "",
        "Another short line.",
        "",
        "## Table",
        "| a | b |",
        "|---|---|",
        "| 1 | 2 |",
        "",
        "```",
        "x = 1",
        "",
        "y = 2",
        "```",
        "",
        "<!-- image -->",
        "",
        "- ",
    ]
    structure = analyze_structure(lines, markdown=True)
    passages = build_passages("doc", lines, structure)
    assert [(item.line_start, item.line_end) for item in passages] == [(3, 5), (8, 10), (12, 16)]
    assert passages[0].heading == "Guide"
    assert passages[1].heading == "Guide > Table"
    assert [item.ordinal for item in passages] == [0, 1, 2]


def test_long_blocks_split_under_the_passage_bound_and_pages_are_separators() -> None:
    """Split oversized paragraphs at line boundaries and start new passages per page."""
    body = ["word " * 60] * 20
    lines = [page_marker(PageLabel.PAGE, 1), *body, page_marker(PageLabel.PAGE, 2), "Tail text."]
    structure = analyze_structure(lines, markdown=True)
    passages = build_passages("doc", lines, structure)
    assert all(len(item.text) <= MAX_PASSAGE_CHARACTERS for item in passages[:-1])
    assert passages[0].line_start == 2 and passages[0].page == 1
    assert passages[-1].text == "Tail text." and passages[-1].page == 2


def test_csv_passages_group_rows_under_the_header() -> None:
    """Keep the header as context and group data rows into bounded runs."""
    lines = ["id,name"] + [f"{index},row {index}" for index in range(1, 61)]
    structure = analyze_structure(lines, markdown=False, pages=False)
    passages = build_passages("doc", lines, structure, csv=True)
    assert passages[0].line_start == 2
    assert all(item.heading == "columns: id,name" for item in passages)
    assert sum(item.line_end - item.line_start + 1 for item in passages) == 60
    assert build_passages("doc", ["only,header"], structure, csv=True)[0].line_start == 1
    assert build_passages("doc", [], structure, csv=True) == ()
