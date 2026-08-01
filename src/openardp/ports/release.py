"""Narrow provider-neutral ports for release evidence operations."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from pydantic import JsonValue

from openardp.domain.release import BenchmarkObservation, PlatformEvidence


class ReleaseEvidenceStoreError(RuntimeError):
    """Base class for evidence storage failures."""


class ReleaseEvidenceConflict(ReleaseEvidenceStoreError):
    """Raised when publication would overwrite foreign or different evidence."""


class ReleaseEvidenceIntegrityError(ReleaseEvidenceStoreError):
    """Raised when persisted evidence fails structure or digest verification."""


class ReleaseEvidenceStore(Protocol):
    """Immutable platform-evidence persistence boundary."""

    def publish(self, destination: Path, evidence: PlatformEvidence) -> None:
        """Publish one completely verified evidence bundle without overwrite."""

    def load(self, source: Path) -> PlatformEvidence:
        """Load and fully verify one evidence bundle."""


class BenchmarkTreatment(Protocol):
    """One named benchmark treatment executed over an exact case."""

    def run(self, *, case_id: str, repetition: int) -> Sequence[BenchmarkObservation]:
        """Return complete raw observations for one case and repetition."""


class ArtifactInspector(Protocol):
    """Inspect a local distribution without extracting it into the workspace."""

    def inspect(self, path: Path) -> Mapping[str, JsonValue]:
        """Return a body-free closed artifact inventory."""


MonotonicNanoseconds = Callable[[], int]
