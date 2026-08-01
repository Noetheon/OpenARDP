"""Runtime contract tests for mock-only Graph ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from openardp.adapters.mock_graph import (
    InMemoryGraphStateStore,
    MockGraphDeltaAdapter,
    MockGraphPage,
)
from openardp.domain.graph import (
    GraphChangeKind,
    GraphDeltaChange,
    GraphScope,
    GraphSyncPolicy,
    graph_item_key,
    graph_scope,
)
from openardp.ports.graph import (
    GraphConnectorError,
    GraphCursorReset,
    GraphDeltaClient,
    GraphStateStore,
    GraphThrottle,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
TENANT = UUID("11111111-1111-4111-8111-111111111111")


def _scope() -> GraphScope:
    return graph_scope(tenant_id=TENANT, site_id="site-A", drive_id="drive-A")


def test_mock_implementations_satisfy_runtime_protocols() -> None:
    """Keep orchestration dependent on narrow provider-neutral contracts."""
    assert isinstance(MockGraphDeltaAdapter(), GraphDeltaClient)
    assert isinstance(InMemoryGraphStateStore(), GraphStateStore)


def test_mock_cursor_registry_never_exposes_raw_tokens_and_is_scope_bound() -> None:
    """Resolve private tokens only through exact scoped opaque handles."""
    adapter = MockGraphDeltaAdapter()
    scope = _scope()
    adapter.register_initial(scope, "https://graph.example/raw-secret-start")
    adapter.add_page(
        scope,
        "https://graph.example/raw-secret-start",
        MockGraphPage(changes=(), delta_cursor="opaque-final-secret"),
    )
    handle = adapter.initial_cursor(scope)
    page = adapter.fetch_page(scope, handle)
    exported = repr((handle, page, adapter.requests))
    assert "raw-secret" not in exported
    assert "opaque-final-secret" not in exported

    other = graph_scope(
        tenant_id=UUID("22222222-2222-4222-8222-222222222222"),
        site_id="site-A",
        drive_id="drive-A",
    )
    with pytest.raises(GraphConnectorError, match="cursor unavailable"):
        adapter.fetch_page(other, handle)


def test_mock_scenarios_queue_throttle_reset_and_page_deterministically() -> None:
    """Provide repeatable provider outcomes without network or ambient state."""
    adapter = MockGraphDeltaAdapter()
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_throttle(scope, "start", retry_after_seconds=3)
    adapter.add_reset(scope, "start")
    adapter.add_page(scope, "start", MockGraphPage(changes=(), delta_cursor="end"))
    cursor = adapter.initial_cursor(scope)
    with pytest.raises(GraphThrottle) as throttled:
        adapter.fetch_page(scope, cursor)
    assert throttled.value.retry_after_seconds == 3
    with pytest.raises(GraphCursorReset):
        adapter.fetch_page(scope, cursor)
    assert adapter.fetch_page(scope, cursor).delta_cursor is not None


def test_port_errors_are_sanitized() -> None:
    """Keep provider bodies, URLs and identifiers out of public failure text."""
    assert str(GraphConnectorError("connector unavailable")) == "connector unavailable"
    assert str(GraphCursorReset()) == "delta cursor reset is required"
    assert str(GraphThrottle(retry_after_seconds=None)) == "connector throttled"
    with pytest.raises(ValueError, match="retry_after_seconds"):
        GraphThrottle(retry_after_seconds=-1)


def test_store_rejects_cross_scope_changes_before_publication() -> None:
    """Prevent an item from another authority entering scoped state."""
    store = InMemoryGraphStateStore()
    scope = _scope()
    other = graph_scope(
        tenant_id=UUID("22222222-2222-4222-8222-222222222222"),
        site_id="site-A",
        drive_id="drive-A",
    )
    wrong = GraphDeltaChange(
        ordinal=0,
        key=graph_item_key(other, "Item"),
        kind=GraphChangeKind.DELETE,
    )
    with pytest.raises(GraphConnectorError, match="scope"):
        store.commit(
            scope,
            expected_cursor=None,
            final_cursor="sha256:" + "1" * 64,
            changes=(wrong,),
        )
    assert store.load(scope) is None


def test_policy_type_is_not_smuggled_through_adapter() -> None:
    """Keep retry policy in orchestration rather than provider response data."""
    assert GraphSyncPolicy().max_pages == 100
