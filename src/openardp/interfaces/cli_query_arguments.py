"""Bounded argparse grammar for document query commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any, Protocol


class _Subparsers(Protocol):
    def add_parser(self, name: str, **kwargs: Any) -> argparse.ArgumentParser:
        """Add and return one command parser."""
        ...


def add_query_arguments(
    subparsers: _Subparsers,
    *,
    common_options: Callable[[argparse.ArgumentParser], None],
) -> None:
    """Register list, status, outline, get, search and reindex arguments."""
    list_parser = subparsers.add_parser("list", help="list body-free document summaries")
    common_options(list_parser)

    status = subparsers.add_parser("status", help="compare current source freshness")
    status.add_argument("target")
    status.add_argument(
        "--full-integrity",
        action="store_true",
        help="verify every persisted representation artifact (potentially expensive)",
    )
    common_options(status)

    outline = subparsers.add_parser("outline", help="show one structural document outline")
    outline.add_argument("document_id")
    outline.add_argument("--version")
    common_options(outline)

    get = subparsers.add_parser("get", help="retrieve one exact current block")
    get.add_argument("block_id")
    common_options(get)

    search = subparsers.add_parser("search", help="exact lexical search over prepared evidence")
    search.add_argument("query")
    search.add_argument("--document")
    search.add_argument("--version")
    search.add_argument("--all-versions", action="store_true")
    search.add_argument("--kind")
    search.add_argument("--trust")
    search.add_argument("--page", type=int)
    search.add_argument("--slide", type=int)
    search.add_argument("--limit", type=int)
    common_options(search)

    reindex = subparsers.add_parser(
        "reindex",
        help="rebuild lexical index rows from verified READY evidence",
    )
    reindex.add_argument("--document")
    common_options(reindex)


__all__ = ["add_query_arguments"]
