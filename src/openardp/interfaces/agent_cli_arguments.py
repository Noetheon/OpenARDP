"""Argparse grammar of the token-efficient agent commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from openardp.services.agent_access import DEFAULT_FIND_LIMIT, DEFAULT_READ_TOKENS

AGENT_COMMANDS = frozenset(
    {"add", "docs", "find", "read", "toc", "verify", "agent-view", "refresh"}
)


class _Subparsers(Protocol):
    def add_parser(self, name: str, **kwargs: Any) -> argparse.ArgumentParser:
        """Add and return one command parser."""
        ...


def add_agent_arguments(
    subparsers: _Subparsers,
    *,
    common_options: Callable[[argparse.ArgumentParser], None],
) -> None:
    """Register the agent command grammar."""
    add = subparsers.add_parser("add", help="prepare files and folders (creates the store)")
    add.add_argument("paths", nargs="+", type=Path, help="files or folders to prepare")
    add.add_argument(
        "--no-recursive",
        action="store_true",
        dest="no_recursive",
        help="do not descend into subfolders",
    )
    add.add_argument(
        "--docling-model-root",
        type=Path,
        help="offline PDF model bundle (see docs/22_OFFLINE_PDF_MODEL_BUNDLE.md)",
    )
    add.add_argument("--docling-model-manifest", type=Path, help="manifest of that bundle")
    common_options(add)

    docs = subparsers.add_parser("docs", help="list prepared documents with size and freshness")
    common_options(docs)

    find = subparsers.add_parser("find", help="find located passages for a question or keywords")
    find.add_argument("query", help="question or keywords, in any wording")
    find.add_argument("--in", dest="document", help="only this document (name, path or id)")
    find.add_argument(
        "--limit", type=int, default=DEFAULT_FIND_LIMIT, help="maximum passages (default 8)"
    )
    common_options(find)

    read = subparsers.add_parser("read", help="read a page, slide, line range or section")
    read.add_argument("document", help="name, path suffix or id")
    read.add_argument("--page", help="page or slide: 3, 3-5 or 3-")
    read.add_argument("--lines", help="line range: 120, 120-180 or 120-")
    read.add_argument("--section", help="heading text")
    read.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_READ_TOKENS,
        dest="max_tokens",
        help="output bound (default 2000)",
    )
    read.add_argument("--no-line-numbers", action="store_true", dest="no_line_numbers")
    common_options(read)

    toc = subparsers.add_parser("toc", help="show headings or pages with line numbers and sizes")
    toc.add_argument("document", help="name, path suffix or id")
    common_options(toc)

    verify = subparsers.add_parser("verify", help="check that a quote occurs in a document")
    verify.add_argument("quote", help="the text you want to cite")
    verify.add_argument("--in", dest="document", help="only this document (name, path or id)")
    verify.add_argument("--version", help="the version id you cited earlier")
    common_options(verify)

    view = subparsers.add_parser("agent-view", help="write Markdown files plus INDEX.md")
    view.add_argument("directory", type=Path, help="target folder outside the store")
    common_options(view)

    refresh = subparsers.add_parser("refresh", help="rebuild the disposable agent index")
    refresh.add_argument("--full", action="store_true", help="discard and rebuild everything")
    common_options(refresh)


__all__ = ["AGENT_COMMANDS", "add_agent_arguments"]
