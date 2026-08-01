"""Deterministic zero-network adapters for the Microsoft Graph design spike."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import RLock

from pydantic import ValidationError

from openardp.domain.graph import (
    GraphChangeKind,
    GraphDeltaChange,
    GraphDeltaPage,
    GraphItemState,
    GraphScope,
    GraphStoredItem,
    GraphSyncState,
    graph_scoped_digest,
)
from openardp.ports.graph import (
    GraphConnectorError,
    GraphCursorReset,
    GraphStateConflict,
    GraphThrottle,
)


@dataclass(frozen=True, repr=False)
class MockGraphPage:
    """Adapter-private page scenario whose raw cursors never enter core records."""

    changes: tuple[GraphDeltaChange, ...]
    next_cursor: str | None = None
    delta_cursor: str | None = None

    def __post_init__(self) -> None:
        """Require exactly one raw continuation or final cursor."""
        if (self.next_cursor is None) == (self.delta_cursor is None):
            raise ValueError("mock page requires exactly one continuation or final cursor")

    def __repr__(self) -> str:
        """Return a deliberately raw-cursor-free diagnostic representation."""
        kind = "next" if self.next_cursor is not None else "delta"
        return f"MockGraphPage(changes={len(self.changes)}, cursor_kind={kind!r})"


MockOutcome = MockGraphPage | GraphConnectorError


class MockGraphDeltaAdapter:
    """Resolve private raw cursors into scope-bound handles and queued outcomes."""

    def __init__(self) -> None:
        """Create one empty isolated scenario registry."""
        self._initial: dict[str, str] = {}
        self._raw_by_handle: dict[tuple[str, str], str] = {}
        self._scenarios: dict[tuple[str, str], deque[MockOutcome]] = defaultdict(deque)
        self._requests: list[tuple[str, str]] = []

    @property
    def requests(self) -> tuple[tuple[str, str], ...]:
        """Return only scope IDs and opaque cursor handles observed by the adapter."""
        return tuple(self._requests)

    def register_initial(self, scope: GraphScope, raw_cursor: str) -> str:
        """Register one private starting cursor and return its opaque scoped handle."""
        handle = self._register_cursor(scope, raw_cursor)
        self._initial[scope.scope_id] = handle
        return handle

    def add_page(self, scope: GraphScope, raw_cursor: str, page: MockGraphPage) -> None:
        """Queue one deterministic page for an adapter-private input cursor."""
        self._register_cursor(scope, raw_cursor)
        if page.next_cursor is not None:
            self._register_cursor(scope, page.next_cursor)
        if page.delta_cursor is not None:
            self._register_cursor(scope, page.delta_cursor)
        self._scenarios[(scope.scope_id, raw_cursor)].append(page)

    def add_throttle(
        self,
        scope: GraphScope,
        raw_cursor: str,
        *,
        retry_after_seconds: int | None,
    ) -> None:
        """Queue one sanitized throttling response."""
        self._register_cursor(scope, raw_cursor)
        self._scenarios[(scope.scope_id, raw_cursor)].append(
            GraphThrottle(retry_after_seconds=retry_after_seconds)
        )

    def add_reset(self, scope: GraphScope, raw_cursor: str) -> None:
        """Queue one sanitized 410/reset response."""
        self._register_cursor(scope, raw_cursor)
        self._scenarios[(scope.scope_id, raw_cursor)].append(GraphCursorReset())

    def initial_cursor(self, scope: GraphScope) -> str:
        """Return the configured scope-bound initial handle."""
        try:
            return self._initial[scope.scope_id]
        except KeyError as error:
            raise GraphConnectorError("initial cursor unavailable") from error

    def fetch_page(self, scope: GraphScope, cursor_handle: str) -> GraphDeltaPage:
        """Resolve one handle and return a sanitized immutable core page."""
        try:
            raw_cursor = self._raw_by_handle[(scope.scope_id, cursor_handle)]
            outcomes = self._scenarios[(scope.scope_id, raw_cursor)]
            outcome = outcomes.popleft()
        except (KeyError, IndexError) as error:
            raise GraphConnectorError("cursor unavailable") from error
        self._requests.append((scope.scope_id, cursor_handle))
        if isinstance(outcome, GraphConnectorError):
            raise outcome
        next_handle = (
            self._handle(scope, outcome.next_cursor) if outcome.next_cursor is not None else None
        )
        delta_handle = (
            self._handle(scope, outcome.delta_cursor) if outcome.delta_cursor is not None else None
        )
        try:
            return GraphDeltaPage(
                scope_id=scope.scope_id,
                requested_cursor=cursor_handle,
                changes=outcome.changes,
                next_cursor=next_handle,
                delta_cursor=delta_handle,
            )
        except ValidationError as error:
            raise GraphConnectorError("connector page invalid") from error

    def _register_cursor(self, scope: GraphScope, raw_cursor: str) -> str:
        handle = graph_scoped_digest(scope.scope_id, kind="cursor", value=raw_cursor)
        self._raw_by_handle[(scope.scope_id, handle)] = raw_cursor
        return handle

    def _handle(self, scope: GraphScope, raw_cursor: str) -> str:
        handle = graph_scoped_digest(scope.scope_id, kind="cursor", value=raw_cursor)
        if self._raw_by_handle.get((scope.scope_id, handle)) != raw_cursor:
            raise GraphConnectorError("cursor unavailable")
        return handle


class InMemoryGraphStateStore:
    """Thread-safe atomic mock store with optimistic cursor validation."""

    def __init__(self) -> None:
        """Create one empty thread-safe mock state partition map."""
        self._states: dict[str, GraphSyncState] = {}
        self._lock = RLock()
        self._fail_next = False
        self._commit_count = 0

    @property
    def commit_count(self) -> int:
        """Return the number of successfully published transactions."""
        with self._lock:
            return self._commit_count

    def fail_next_commit(self) -> None:
        """Inject one failure after prospective validation and before publication."""
        with self._lock:
            self._fail_next = True

    def load(self, scope: GraphScope) -> GraphSyncState | None:
        """Return current immutable state for one exact scope."""
        with self._lock:
            return self._states.get(scope.scope_id)

    def commit(
        self,
        scope: GraphScope,
        *,
        expected_cursor: str | None,
        final_cursor: str,
        changes: tuple[GraphDeltaChange, ...],
    ) -> GraphSyncState:
        """Build a complete prospective state and publish it under one lock."""
        with self._lock:
            current = self._states.get(scope.scope_id)
            current_cursor = current.cursor if current is not None else None
            if current_cursor != expected_cursor:
                raise GraphStateConflict("graph state cursor changed")
            if any(change.key.scope_id != scope.scope_id for change in changes):
                raise GraphConnectorError("state change scope is invalid")
            items = (
                {item.key.item_key: item for item in current.items} if current is not None else {}
            )
            for change in changes:
                if change.kind is GraphChangeKind.UPSERT:
                    items[change.key.item_key] = GraphStoredItem(
                        key=change.key,
                        state=GraphItemState.ACTIVE,
                        revision=change.revision,
                        permission=change.permission,
                    )
                else:
                    items[change.key.item_key] = GraphStoredItem(
                        key=change.key,
                        state=GraphItemState.TOMBSTONE,
                    )
            try:
                prospective = GraphSyncState(
                    scope_id=scope.scope_id,
                    cursor=final_cursor,
                    generation=(current.generation + 1 if current is not None else 1),
                    items=tuple(items[key] for key in sorted(items)),
                )
            except (ValidationError, ValueError) as error:
                raise GraphConnectorError("state publication failed") from error
            if self._fail_next:
                self._fail_next = False
                raise GraphConnectorError("state publication failed")
            self._states[scope.scope_id] = prospective
            self._commit_count += 1
            return prospective
