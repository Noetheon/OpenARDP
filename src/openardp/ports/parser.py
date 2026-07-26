"""Provider-neutral parser protocol and sanitized parser failures."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from openardp.domain.ingestion import ParsedTextDocument, ParserRecipe
from openardp.domain.rich_ingestion import RichParseOutput, RichParserRecipe


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


class RichParserDependencyUnavailable(ParserError):
    """Raised when the exact optional rich parser dependency is unavailable."""


class UnsupportedRichMedia(ParserError, ValueError):
    """Raised when media is outside the closed rich-document allowlist."""


class RichParserModelAssetsRequired(ParserError):
    """Raised when a PDF parse has no reviewed local model bundle."""


class RichParserModelAssetsInvalid(ParserError):
    """Raised when reviewed local model assets fail integrity validation."""


class RichParserMalformedDocument(ParserError, ValueError):
    """Raised when a rich source does not match the declared valid format."""


class RichParserPartialConversion(ParserError):
    """Raised when the provider does not produce one complete conversion."""


class RichParserNetworkDenied(ParserError):
    """Raised when provider behavior attempts prohibited network access."""


class RichParserResourceLimitExceeded(ParserError):
    """Raised when a rich source, worker or output exceeds a configured bound."""


class RichParserCancelled(ParserError):
    """Raised when the parent cancels an in-flight rich conversion."""


class InvalidRichParserOutput(ParserError):
    """Raised when worker output fails the strict rich parser contract."""


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


@runtime_checkable
class RichParserAdapter(Protocol):
    """Bounded provider-neutral rich parser accepting only source bytes."""

    @property
    def recipe(self) -> RichParserRecipe:
        """Return the exact immutable rich parsing recipe."""
        ...

    def supports(self, media_type: str) -> bool:
        """Return whether this adapter accepts the declared rich media type."""
        ...

    def parse(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: str,
    ) -> RichParseOutput:
        """Parse one verified rich byte stream without path or URL authority."""
        ...

    def resolve(
        self,
        native_document: dict[str, object],
        *,
        pointer: str,
    ) -> object:
        """Resolve one adapter-issued pointer within an already loaded native value."""
        ...


__all__ = [
    "InvalidParserOutput",
    "InvalidRichParserOutput",
    "ParserAdapter",
    "ParserError",
    "ParserProcessCrashed",
    "ParserTimedOut",
    "RichParserAdapter",
    "RichParserCancelled",
    "RichParserDependencyUnavailable",
    "RichParserMalformedDocument",
    "RichParserModelAssetsInvalid",
    "RichParserModelAssetsRequired",
    "RichParserNetworkDenied",
    "RichParserPartialConversion",
    "RichParserResourceLimitExceeded",
    "TextDecodingError",
    "TextResourceLimitExceeded",
    "UnsafeTextContent",
    "UnsupportedRichMedia",
    "UnsupportedTextMedia",
]
