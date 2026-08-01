"""Runtime conformance for provider-neutral watcher boundaries."""

from __future__ import annotations

from openardp.adapters.local_watch import LocalWatchScanner
from openardp.ports.watcher import WatchScanner


def test_local_scanner_satisfies_runtime_protocol() -> None:
    """Keep the concrete filesystem adapter behind the narrow scanner shape."""
    assert isinstance(LocalWatchScanner(), WatchScanner)
