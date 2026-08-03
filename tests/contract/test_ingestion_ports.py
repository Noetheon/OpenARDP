"""Structural contracts for F004 parser and catalog boundaries."""

from __future__ import annotations

import multiprocessing
import os
import socket
import time
from collections.abc import Iterable
from multiprocessing.connection import Connection
from typing import assert_type

import pytest

from openardp.adapters.isolated_parser import IsolatedParserAdapter
from openardp.domain.block import BlockKind
from openardp.domain.ingestion import ParsedTextDocument, ParserRecipe, TextMediaType
from openardp.ports.catalog import Catalog, RichCatalog
from openardp.ports.parser import (
    InvalidParserOutput,
    InvalidRichParserOutput,
    MalformedCsv,
    ParserAdapter,
    ParserError,
    ParserProcessCrashed,
    ParserTimedOut,
    RichParserAdapter,
    RichParserCancelled,
    RichParserDependencyUnavailable,
    RichParserModelAssetsInvalid,
    RichParserModelAssetsRequired,
    RichParserNetworkDenied,
    RichParserPartialConversion,
    RichParserResourceLimitExceeded,
    TextDecodingError,
    TextResourceLimitExceeded,
    UnsafeTextContent,
    UnsupportedRichMedia,
    UnsupportedTextMedia,
)


def test_rich_parser_port_and_errors_remain_provider_neutral() -> None:
    """Expose no Docling class or import from the provider-neutral port module."""
    expected_errors = (
        RichParserDependencyUnavailable("rich parser dependency unavailable"),
        UnsupportedRichMedia("unsupported rich media"),
        RichParserModelAssetsRequired("rich parser model assets required"),
        RichParserModelAssetsInvalid("rich parser model assets invalid"),
        RichParserPartialConversion("rich parser partial conversion"),
        RichParserNetworkDenied("rich parser network denied"),
        RichParserResourceLimitExceeded("rich parser resource limit exceeded"),
        RichParserCancelled("rich parser cancelled"),
        InvalidRichParserOutput("rich parser output invalid"),
    )
    assert all(isinstance(error, ParserError) for error in expected_errors)
    assert all("docling" not in type(error).__module__ for error in expected_errors)
    assert RichParserAdapter.__module__ == "openardp.ports.parser"


def _hanging_worker(
    input_receiver: Connection,
    result_sender: Connection,
    config: object,
) -> None:
    time.sleep(5)


def _crashing_worker(
    input_receiver: Connection,
    result_sender: Connection,
    config: object,
) -> None:
    os._exit(17)


def _malformed_worker(
    input_receiver: Connection,
    result_sender: Connection,
    config: object,
) -> None:
    result_sender.send({"secret-body": True})


def _network_probe_worker(
    input_receiver: Connection,
    result_sender: Connection,
    config: object,
) -> None:
    blocked = False
    try:
        socket.socket()
    except RuntimeError:
        blocked = True
    result_sender.send(
        (
            "ok",
            ParsedTextDocument(
                media_type=(
                    TextMediaType.CSV
                    if getattr(config, "parser_kind", "text") == "csv"
                    else TextMediaType.PLAIN
                ),
                blocks=(),
                warnings=("network_blocked",) if blocked else ("network_available",),
                bom_present=False,
            ).model_dump_json(),
        )
    )


class _ParserDouble:
    """Minimal provider-neutral structural parser double."""

    @property
    def recipe(self) -> ParserRecipe:
        return ParserRecipe(
            name="double",
            version="1",
            profile="default",
            config_hash="sha256:" + "0" * 64,
            normalization_schema_version="0.1.0",
        )

    def supports(self, media_type: str) -> bool:
        return media_type == TextMediaType.PLAIN.value

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument:
        tuple(chunks)
        return ParsedTextDocument(
            media_type=TextMediaType(media_type),
            blocks=(),
            warnings=(),
            bom_present=False,
        )


def test_parser_protocol_accepts_structural_double() -> None:
    """Keep parser providers replaceable behind one narrow byte-stream contract."""
    parser: ParserAdapter = _ParserDouble()
    assert_type(parser, ParserAdapter)
    assert isinstance(parser, ParserAdapter)


def test_parser_error_taxonomy_is_typed_and_sanitized() -> None:
    """Expose only bounded parser classifications at the application boundary."""
    errors = (
        UnsupportedTextMedia("unsupported text media"),
        TextDecodingError("text decoding failed"),
        UnsafeTextContent("unsafe text content"),
        TextResourceLimitExceeded("text resource limit exceeded"),
        ParserTimedOut("parser timed out"),
        ParserProcessCrashed("parser process crashed"),
        InvalidParserOutput("parser output invalid"),
        MalformedCsv("malformed csv"),
    )
    assert all(isinstance(error, ParserError) for error in errors)
    assert all("secret-body" not in str(error) for error in errors)


def test_catalog_protocol_exposes_complete_f004_boundary() -> None:
    """Require representation, head, event and navigation operations on the catalog port."""
    expected = {
        "get_document",
        "get_document_by_source",
        "list_documents",
        "acquire_representation",
        "renew_representation",
        "fail_representation",
        "commit_ready_representation",
        "load_representation",
        "record_ready_ingest",
        "get_document_head",
        "list_document_summaries",
        "resolve_ready_representation",
        "find_current_blocks",
        "list_ingestion_events",
    }
    assert all(hasattr(Catalog, name) for name in expected)


def test_catalog_protocol_extends_the_existing_boundary_for_rich_commits() -> None:
    """Keep canonical and later rich attempts behind one atomic catalog port."""
    expected = {
        "commit_ready_rich_representation",
        "append_rich_attempt",
        "load_rich_representation",
        "get_rich_attempt",
        "list_rich_attempts",
    }
    assert all(hasattr(RichCatalog, name) for name in expected)


def test_isolated_parser_uses_spawned_ipc_and_matches_pure_contract() -> None:
    """Return strict parser output while leaving no live parser child behind."""
    before = {process.pid for process in multiprocessing.active_children()}
    parser = IsolatedParserAdapter(timeout_seconds=5)
    result = parser.parse(
        (b"# He", b"ading\n\nbody"),
        media_type=TextMediaType.MARKDOWN.value,
    )
    after = {process.pid for process in multiprocessing.active_children()}
    assert [block.text for block in result.blocks] == ["Heading", "body"]
    assert parser.recipe.name == "openardp-text"
    assert after == before


def test_isolated_parser_rejects_content_without_leaking_it() -> None:
    """Translate worker failures to body-free typed errors."""
    parser = IsolatedParserAdapter(timeout_seconds=5)
    with pytest.raises(TextDecodingError, match="text decoding failed") as error:
        parser.parse((b"\xffsecret-body",), media_type="text/plain")
    assert "secret-body" not in str(error.value)


def test_isolated_parser_handles_empty_markdown_block_quote() -> None:
    """Keep valid empty quote syntax inside the deterministic worker contract."""
    result = IsolatedParserAdapter(timeout_seconds=5).parse(
        (b"> ",),
        media_type=TextMediaType.MARKDOWN.value,
    )
    assert result.blocks == ()
    assert result.warnings == ("empty_block_quote_ignored",)


def test_isolated_parser_runs_csv_recipe_in_the_same_network_denied_boundary() -> None:
    """Select the distinct CSV recipe without changing the historical text recipe."""
    text = IsolatedParserAdapter(timeout_seconds=5)
    csv_parser = IsolatedParserAdapter(parser_kind="csv", timeout_seconds=5)
    result = csv_parser.parse(
        (b"key,value\nCVE-2021-44228,2021-12-24",),
        media_type=TextMediaType.CSV.value,
    )

    assert csv_parser.recipe.name == "openardp-csv"
    assert text.recipe == IsolatedParserAdapter(timeout_seconds=5).recipe
    assert [block.kind for block in result.blocks] == [
        BlockKind.TABLE,
        BlockKind.TABLE,
    ]
    assert "CVE-2021-44228" in result.blocks[1].text


def test_isolated_csv_parser_inherits_worker_network_denial() -> None:
    """Deny socket construction before selected CSV worker behavior executes."""
    result = IsolatedParserAdapter(
        parser_kind="csv",
        timeout_seconds=5,
        _worker_behavior=_network_probe_worker,
    ).parse((), media_type=TextMediaType.CSV.value)
    assert result.warnings == ("network_blocked",)


def test_isolated_parser_enforces_worker_network_denial() -> None:
    """Apply socket denial before any selected worker behavior executes."""
    result = IsolatedParserAdapter(
        timeout_seconds=5,
        _worker_behavior=_network_probe_worker,
    ).parse((), media_type="text/plain")
    assert result.warnings == ("network_blocked",)


def test_isolated_parser_terminates_timed_out_worker() -> None:
    """Terminate and reap a worker that misses the wall-clock deadline."""
    before = {process.pid for process in multiprocessing.active_children()}
    parser = IsolatedParserAdapter(
        timeout_seconds=0.05,
        _worker_behavior=_hanging_worker,
    )
    with pytest.raises(ParserTimedOut, match="parser timed out"):
        parser.parse((b"safe",), media_type="text/plain")
    assert {process.pid for process in multiprocessing.active_children()} == before


def test_isolated_parser_sanitizes_crash_and_malformed_output() -> None:
    """Distinguish a dead worker from an invalid protocol without reflecting output."""
    crash = IsolatedParserAdapter(
        timeout_seconds=5,
        _worker_behavior=_crashing_worker,
    )
    with pytest.raises(ParserProcessCrashed, match="parser process crashed"):
        crash.parse((), media_type="text/plain")

    malformed = IsolatedParserAdapter(
        timeout_seconds=5,
        _worker_behavior=_malformed_worker,
    )
    with pytest.raises(InvalidParserOutput, match="parser output invalid") as error:
        malformed.parse((), media_type="text/plain")
    assert "secret-body" not in str(error.value)
