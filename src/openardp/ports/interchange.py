"""Provider-neutral ports and sanitized failures for experimental interchange."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from openardp.domain.interchange import (
    InterchangeLimits,
    InterchangePackage,
    InterchangeResult,
    PortableAsset,
    VerifiedPackage,
)


class InterchangeError(RuntimeError):
    """Base sanitized package failure."""


class MalformedPackage(InterchangeError):
    """Package shape or encoding is invalid."""


class UnsupportedInterchangeVersion(InterchangeError):
    """Package declares a well-formed but uninstalled version."""


class InterchangePolicyRejected(InterchangeError):
    """Package or request violates an explicit profile policy."""


class InterchangeResourceExceeded(InterchangeError):
    """Configured resource bound was exceeded."""


class InterchangeIntegrityInvalid(InterchangeError):
    """Inventory, length or digest verification failed."""


class InterchangeRelationshipInvalid(InterchangeError):
    """Cross-record relationships are invalid."""


class InterchangeSourceChanged(InterchangeError):
    """An export source changed during exact-byte observation."""


class InterchangeDestinationConflict(InterchangeError):
    """Destination is overlapping, foreign or conflicting."""


class InterchangePublicationFailed(InterchangeError):
    """Operation-owned staging could not be durably published."""


@runtime_checkable
class AssetByteSource(Protocol):
    """Stream exact bytes selected by a trusted export operator."""

    def iter_asset(self, asset: PortableAsset, *, chunk_size: int) -> Iterator[bytes]:
        """Yield exact bounded bytes for one included asset."""
        ...


@runtime_checkable
class PackageValidator(Protocol):
    """Independent read-only package verifier."""

    def verify(self, package: Path, *, limits: InterchangeLimits) -> VerifiedPackage:
        """Verify completely without extraction or publication."""
        ...


@runtime_checkable
class PackageExporter(Protocol):
    """Atomic deterministic package writer."""

    def export(
        self,
        package: InterchangePackage,
        source: AssetByteSource,
        destination: Path,
        *,
        limits: InterchangeLimits,
    ) -> InterchangeResult:
        """Publish one self-verified package at a fresh destination."""
        ...


@runtime_checkable
class PackageImporter(Protocol):
    """Fresh verified snapshot publisher."""

    def import_snapshot(
        self,
        package: Path,
        destination: Path,
        *,
        limits: InterchangeLimits,
    ) -> InterchangeResult:
        """Publish one complete immutable package snapshot or none."""
        ...


__all__ = [
    "AssetByteSource",
    "InterchangeDestinationConflict",
    "InterchangeError",
    "InterchangeIntegrityInvalid",
    "InterchangePolicyRejected",
    "InterchangePublicationFailed",
    "InterchangeRelationshipInvalid",
    "InterchangeResourceExceeded",
    "InterchangeSourceChanged",
    "MalformedPackage",
    "PackageExporter",
    "PackageImporter",
    "PackageValidator",
    "UnsupportedInterchangeVersion",
]
