"""Provider-neutral estimator and verified context-candidate boundaries."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openardp.domain.context_compilation import (
    ContextCandidate,
    ContextCompileLimits,
    CorpusSnapshot,
    EstimatorIdentity,
)


@runtime_checkable
class CancellationCheck(Protocol):
    """Non-blocking caller-supplied cancellation observation."""

    def __call__(self) -> bool:
        """Return true when the current bounded operation should stop."""
        ...


class ContextCompilationFailure(RuntimeError):
    """Base class for sanitized context-compilation failures."""


class ContextCompilationCancelled(ContextCompilationFailure):
    """Raised at a bounded phase when the caller requests cancellation."""


class ContextIntegrityFailure(ContextCompilationFailure):
    """Raised when catalog, index, body or public-contract evidence fails verification."""


class ContextLimitExceeded(ContextCompilationFailure):
    """Raised before a configured bounded resource limit would be exceeded."""


class ContextConfigurationMismatch(ContextCompilationFailure):
    """Raised when replay runtime identities differ from the recorded contract."""


class ContextNotFound(ContextCompilationFailure):
    """Raised when an exact requested scope or persisted compilation is absent."""


@runtime_checkable
class ContextEstimator(Protocol):
    """Exact deterministic measurement strategy for serialized context."""

    @property
    def identity(self) -> EstimatorIdentity:
        """Return the complete versioned estimator identity."""
        ...

    def measure(self, payload: bytes) -> int:
        """Measure exact serialized UTF-8 payload bytes in the estimator unit."""
        ...


@runtime_checkable
class ContextCandidateSource(Protocol):
    """One bounded verified source of lexical context candidates."""

    def discover(
        self,
        task: str,
        snapshot: CorpusSnapshot,
        limits: ContextCompileLimits,
        cancel: CancellationCheck,
    ) -> tuple[ContextCandidate, ...]:
        """Return verified candidates without model or network provider calls."""
        ...


@runtime_checkable
class TextContextCandidateSource(ContextCandidateSource, Protocol):
    """Verified FTS-backed source for authoritative F002 text blocks."""


@runtime_checkable
class RichContextCandidateSource(ContextCandidateSource, Protocol):
    """Bounded provider-free source for accepted F006 evidence projections."""
