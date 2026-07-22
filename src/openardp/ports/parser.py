"""Provider-neutral parser protocol and sanitized parser failures."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from openardp.domain.ingestion import ParsedTextDocument, ParserRecipe


class ParserError(RuntimeError):
    """Base class for sanitized parser-boundary failures."""


class UnsupportedTextMedia(ParserError, ValueError):
    """Raised when an adapter does not support the declared text media type."""


class TextDecodingError(ParserError, ValueError):
    """Raised when strict UTF-8 decoding fails."""


class UnsafeTextContent(ParserError, ValueError):
    """Raised when prohibited text such as NUL is observed."""


class TextResourceLimitExceeded(ParserError):
    """Raised when a byte, line, block or worker resource bound is exceeded."""


class ParserTimedOut(ParserError, TimeoutError):
    """Raised after the isolated parser deadline expires."""


class ParserProcessCrashed(ParserError):
    """Raised when the isolated parser exits without a valid result."""


class InvalidParserOutput(ParserError):
    """Raised when worker output fails the strict parser contract."""


@runtime_checkable
class ParserAdapter(Protocol):
    """Deterministic source-byte parser provider."""

    @property
    def recipe(self) -> ParserRecipe:
        """Return the exact immutable processing recipe."""
        ...

    def supports(self, media_type: str) -> bool:
        """Return whether this adapter accepts the declared media type."""
        ...

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> ParsedTextDocument:
        """Parse one verified byte stream without source-path authority."""
        ...


__all__ = [
    "InvalidParserOutput",
    "ParserAdapter",
    "ParserError",
    "ParserProcessCrashed",
    "ParserTimedOut",
    "TextDecodingError",
    "TextResourceLimitExceeded",
    "UnsafeTextContent",
    "UnsupportedTextMedia",
]
