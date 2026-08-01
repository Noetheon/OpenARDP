"""Narrow provider-neutral boundaries for visual rendering and interpretation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from openardp.domain.evidence import EvidenceProjection, ProviderRecipe
from openardp.domain.visual import (
    Rotation,
    VisualInterpretationRequest,
    VisualInterpretationResult,
    VisualRenderRecipe,
    VisualUsagePolicy,
)


class VisualError(RuntimeError):
    """Base class for stable body-free visual failures."""

    code = "visual_failed"


class VisualDependencyUnavailable(VisualError):
    """Raised when an explicitly requested optional provider is unavailable."""

    code = "visual_dependency_unavailable"


class UnsupportedVisualMedia(VisualError):
    """Raised when no installed renderer supports the exact media type."""

    code = "unsupported_visual_media"


class VisualMalformedInput(VisualError):
    """Raised when untrusted encoded content cannot be decoded safely."""

    code = "visual_malformed_input"


class VisualEncryptedInput(VisualError):
    """Raised when encrypted content cannot be opened without hidden authority."""

    code = "visual_encrypted_input"


class VisualResourceLimitExceeded(VisualError):
    """Raised when any independent admission or output cap is exceeded."""

    code = "visual_resource_limit_exceeded"


class VisualTimedOut(VisualError):
    """Raised when a spawned visual worker exceeds its wall-clock deadline."""

    code = "visual_timed_out"


class VisualProcessCrashed(VisualError):
    """Raised when a spawned worker exits without one valid result."""

    code = "visual_process_crashed"


class VisualCancelled(VisualError):
    """Raised when the caller cooperatively cancels visual work."""

    code = "visual_cancelled"


class VisualGeometryMismatch(VisualError):
    """Raised when native and renderer page geometry disagree beyond policy."""

    code = "visual_geometry_mismatch"


class VisualTargetUnavailable(VisualError):
    """Raised when accepted evidence cannot resolve to one exact visual region."""

    code = "visual_target_unavailable"


class VisualIntegrityError(VisualError):
    """Raised when catalog, CAS or declared visual identity does not verify."""

    code = "visual_integrity_error"


class VisualConflict(VisualError):
    """Raised when one persisted identity is reused with different facts."""

    code = "visual_conflict"


class VisualInterpretationUnavailable(VisualError):
    """Raised when no interpretation provider was explicitly supplied."""

    code = "visual_interpretation_unavailable"


@dataclass(frozen=True, slots=True)
class RenderedVisualPage:
    """Bounded exact page result crossing a renderer boundary."""

    png_bytes: bytes
    page_count: int
    source_width_mpt: int
    source_height_mpt: int
    source_rotation: Rotation
    applied_rotation: Rotation
    pixel_width: int
    pixel_height: int


@dataclass(frozen=True, slots=True)
class RenderedVisualCrop:
    """Bounded exact RGB PNG crop result."""

    png_bytes: bytes
    pixel_width: int
    pixel_height: int


@runtime_checkable
class VisualRenderer(Protocol):
    """Render and crop encoded source data without path or network authority."""

    @property
    def recipe(self) -> VisualRenderRecipe:
        """Return the complete immutable output recipe."""
        ...

    def supports(self, media_type: str) -> bool:
        """Return whether this renderer accepts the exact media type."""
        ...

    def render_page(
        self,
        source: bytes,
        *,
        media_type: str,
        page_number: int,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualPage:
        """Render one one-based page to a deterministic RGB PNG."""
        ...

    def crop_page(
        self,
        page_png: bytes,
        *,
        bounds: tuple[int, int, int, int],
        cancellation_check: Callable[[], bool] | None = None,
    ) -> RenderedVisualCrop:
        """Crop one verified page PNG using half-open pixel bounds."""
        ...


@runtime_checkable
class VisualRightsPolicy(Protocol):
    """Derive effective usage rights only from trusted local policy."""

    def evaluate(self, projection: EvidenceProjection) -> VisualUsagePolicy:
        """Return the effective policy without trusting document metadata."""
        ...


@runtime_checkable
class VisualInterpreter(Protocol):
    """Optional explicit OCR/caption provider over verified crop bytes."""

    @property
    def provider(self) -> ProviderRecipe:
        """Return the exact model/provider/config recipe."""
        ...

    def interpret(
        self,
        request: VisualInterpretationRequest,
        crop_png: bytes,
    ) -> VisualInterpretationResult:
        """Return one bounded untrusted interpretation result."""
        ...


__all__ = [
    "RenderedVisualCrop",
    "RenderedVisualPage",
    "UnsupportedVisualMedia",
    "VisualCancelled",
    "VisualConflict",
    "VisualDependencyUnavailable",
    "VisualEncryptedInput",
    "VisualError",
    "VisualGeometryMismatch",
    "VisualIntegrityError",
    "VisualInterpretationUnavailable",
    "VisualInterpreter",
    "VisualMalformedInput",
    "VisualProcessCrashed",
    "VisualRenderer",
    "VisualResourceLimitExceeded",
    "VisualRightsPolicy",
    "VisualTargetUnavailable",
    "VisualTimedOut",
]
