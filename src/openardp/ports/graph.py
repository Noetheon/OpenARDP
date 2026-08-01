"""Provider-neutral mock delta and atomic state boundaries."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openardp.domain.graph import (
    GraphDeltaChange,
    GraphDeltaPage,
    GraphScope,
    GraphSyncState,
)


class GraphConnectorError(RuntimeError):
    """Base sanitized connector boundary failure."""


class GraphCursorReset(GraphConnectorError):
    """Signal that the provider rejected a cursor and full resync is required."""

    def __init__(self) -> None:
        """Create the stable body-free reset error."""
        super().__init__("delta cursor reset is required")


class GraphThrottle(GraphConnectorError):
    """Signal bounded provider throttling without response body exposure."""

    def __init__(self, *, retry_after_seconds: int | None) -> None:
        """Retain only one validated delay hint and a stable public message."""
        if retry_after_seconds is not None and (
            type(retry_after_seconds) is not int or retry_after_seconds < 0
        ):
            raise ValueError("retry_after_seconds must be a non-negative integer or None")
        self.retry_after_seconds = retry_after_seconds
        super().__init__("connector throttled")


class GraphStateConflict(GraphConnectorError):
    """Signal optimistic cursor conflict at the atomic state boundary."""


@runtime_checkable
class GraphDeltaClient(Protocol):
    """Fetch scoped delta pages while owning raw provider cursor values."""

    def initial_cursor(self, scope: GraphScope) -> str:
        """Return an opaque scoped handle for the configured initial provider cursor."""
        ...

    def fetch_page(self, scope: GraphScope, cursor_handle: str) -> GraphDeltaPage:
        """Fetch one mocked page or raise one sanitized connector outcome."""
        ...


@runtime_checkable
class GraphStateStore(Protocol):
    """Atomically publish one final cursor and reduced item/tombstone set."""

    def load(self, scope: GraphScope) -> GraphSyncState | None:
        """Return current immutable state for one exact scope."""
        ...

    def commit(
        self,
        scope: GraphScope,
        *,
        expected_cursor: str | None,
        final_cursor: str,
        changes: tuple[GraphDeltaChange, ...],
    ) -> GraphSyncState:
        """Validate expected state and atomically publish all reduced changes."""
        ...
