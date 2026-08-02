"""Bounded convergence helpers for cross-platform filesystem mutations."""

from __future__ import annotations

import os
from pathlib import Path
from time import sleep

from openardp.ports.maintenance import MaintenanceError

_WINDOWS_ATTEMPTS = 10
_WINDOWS_DELAY_SECONDS = 0.05


def await_transition_metadata(
    source: Path,
    destination: Path,
) -> tuple[os.stat_result, os.stat_result | None]:
    """Await the bounded Windows rename convergence window."""
    attempts = _WINDOWS_ATTEMPTS if os.name == "nt" else 1
    destination_metadata: os.stat_result | None = None
    source_metadata: os.stat_result | None = None
    for attempt in range(attempts):
        try:
            destination_metadata = destination.lstat()
        except FileNotFoundError:
            destination_metadata = None
        try:
            source_metadata = source.lstat()
        except FileNotFoundError:
            source_metadata = None
        if destination_metadata is not None and (os.name != "nt" or source_metadata is None):
            return destination_metadata, source_metadata
        if attempt + 1 < attempts:
            sleep(_WINDOWS_DELAY_SECONDS)
    if destination_metadata is None:
        raise MaintenanceError("transition destination is missing")
    return destination_metadata, source_metadata


__all__ = ["await_transition_metadata"]
