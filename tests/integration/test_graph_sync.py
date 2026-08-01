"""Atomic multi-page Graph mock orchestration tests."""

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
    GraphItemState,
    GraphScope,
    GraphSyncOutcome,
    GraphSyncPolicy,
    graph_item_key,
    graph_permission_snapshot_ref,
    graph_revision_hints,
    graph_scope,
)
from openardp.ports.graph import GraphConnectorError, GraphStateConflict
from openardp.services.graph_sync import GraphSyncService

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
TENANT = UUID("11111111-1111-4111-8111-111111111111")


def _scope() -> GraphScope:
    return graph_scope(tenant_id=TENANT, site_id="site-A", drive_id="drive-A")


def _change(item: str, ordinal: int, *, revision: str = "v1") -> GraphDeltaChange:
    scope = _scope()
    key = graph_item_key(scope, item)
    return GraphDeltaChange(
        ordinal=ordinal,
        key=key,
        kind=GraphChangeKind.UPSERT,
        revision=graph_revision_hints(scope, key, etag=revision),
        permission=graph_permission_snapshot_ref(
            scope,
            key,
            snapshot_version=f"acl-{revision}",
            authorization_context="selected-site-reader",
            observed_at=NOW,
        ),
    )


def _service() -> tuple[MockGraphDeltaAdapter, InMemoryGraphStateStore, GraphSyncService]:
    adapter = MockGraphDeltaAdapter()
    store = InMemoryGraphStateStore()
    return adapter, store, GraphSyncService(adapter, store, sleeper=lambda _seconds: None)


def test_multi_page_cycle_commits_last_occurrence_and_final_cursor_once() -> None:
    """Reduce the whole ordered cycle before one atomic publication."""
    adapter, store, service = _service()
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_page(
        scope,
        "start",
        MockGraphPage(changes=(_change("A", 0), _change("B", 1)), next_cursor="page-2"),
    )
    adapter.add_page(
        scope,
        "page-2",
        MockGraphPage(
            changes=(_change("A", 2, revision="v2"),),
            delta_cursor="delta-1",
        ),
    )
    result = service.reconcile(scope)
    state = store.load(scope)
    assert result.outcome is GraphSyncOutcome.APPLIED
    assert (result.pages_seen, result.changes_seen, result.changes_applied) == (2, 3, 2)
    assert state is not None and state.generation == 1
    assert state.cursor == result.committed_cursor
    items = {item.key.item_key: item for item in state.items}
    assert (
        items[graph_item_key(scope, "A").item_key].revision
        == _change("A", 0, revision="v2").revision
    )
    assert store.commit_count == 1


def test_delete_is_retained_as_tombstone_and_later_upsert_restores_active() -> None:
    """Never infer deletion from absence and permit a later observed restoration."""
    adapter, store, service = _service()
    scope = _scope()
    key = graph_item_key(scope, "A")
    adapter.register_initial(scope, "start")
    adapter.add_page(
        scope,
        "start",
        MockGraphPage(
            changes=(
                _change("A", 0),
                GraphDeltaChange(ordinal=1, key=key, kind=GraphChangeKind.DELETE),
            ),
            delta_cursor="delta-1",
        ),
    )
    service.reconcile(scope)
    state = store.load(scope)
    assert state is not None and state.items[0].state is GraphItemState.TOMBSTONE

    adapter.add_page(
        scope,
        "delta-1",
        MockGraphPage(changes=(_change("A", 0, revision="v2"),), delta_cursor="delta-2"),
    )
    service.reconcile(scope)
    state = store.load(scope)
    assert state is not None and state.items[0].state is GraphItemState.ACTIVE
    assert state.generation == 2


@pytest.mark.parametrize("failure", ["reset", "cycle", "page_limit", "change_limit"])
def test_late_cycle_failures_publish_no_partial_state(failure: str) -> None:
    """Fail closed even after valid earlier pages were accumulated."""
    adapter, store, service = _service()
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_page(
        scope,
        "start",
        MockGraphPage(changes=(_change("A", 0),), next_cursor="page-2"),
    )
    policy = GraphSyncPolicy()
    if failure == "reset":
        adapter.add_reset(scope, "page-2")
    elif failure == "cycle":
        adapter.add_page(
            scope,
            "page-2",
            MockGraphPage(changes=(), next_cursor="start"),
        )
    elif failure == "page_limit":
        adapter.add_page(
            scope,
            "page-2",
            MockGraphPage(changes=(), delta_cursor="end"),
        )
        policy = GraphSyncPolicy(max_pages=1)
    else:
        adapter.add_page(
            scope,
            "page-2",
            MockGraphPage(changes=(_change("B", 1),), delta_cursor="end"),
        )
        policy = GraphSyncPolicy(max_changes=1)

    if failure == "reset":
        result = service.reconcile(scope, policy=policy)
        assert result.outcome is GraphSyncOutcome.RESET_REQUIRED
    else:
        with pytest.raises(GraphConnectorError):
            service.reconcile(scope, policy=policy)
    assert store.load(scope) is None and store.commit_count == 0


def test_store_failure_and_expected_cursor_conflict_are_atomic() -> None:
    """Publish neither cursor nor item changes when the transaction boundary fails."""
    adapter, store, service = _service()
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_page(
        scope,
        "start",
        MockGraphPage(changes=(_change("A", 0),), delta_cursor="delta-1"),
    )
    store.fail_next_commit()
    with pytest.raises(GraphConnectorError, match="state publication failed"):
        service.reconcile(scope)
    assert store.load(scope) is None

    current = adapter.initial_cursor(scope)
    with pytest.raises(GraphStateConflict):
        store.commit(
            scope,
            expected_cursor=current,
            final_cursor=current,
            changes=(),
        )
    assert store.load(scope) is None


def test_retry_after_and_fallback_backoff_are_bounded() -> None:
    """Honor server delay, then deterministic fallback, before successful atomic commit."""
    adapter = MockGraphDeltaAdapter()
    store = InMemoryGraphStateStore()
    delays: list[int] = []
    service = GraphSyncService(adapter, store, sleeper=delays.append)
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_throttle(scope, "start", retry_after_seconds=3)
    adapter.add_throttle(scope, "start", retry_after_seconds=None)
    adapter.add_page(
        scope,
        "start",
        MockGraphPage(changes=(), delta_cursor="end"),
    )
    result = service.reconcile(scope, policy=GraphSyncPolicy(retry_base_seconds=2))
    assert result.outcome is GraphSyncOutcome.UNCHANGED
    assert delays == [3, 4]
    assert store.commit_count == 1


def test_over_policy_throttle_returns_retry_later_without_sleep_or_commit() -> None:
    """Defer a server-requested wait that exceeds local execution policy."""
    adapter = MockGraphDeltaAdapter()
    store = InMemoryGraphStateStore()
    delays: list[int] = []
    service = GraphSyncService(adapter, store, sleeper=delays.append)
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_throttle(scope, "start", retry_after_seconds=600)
    result = service.reconcile(scope, policy=GraphSyncPolicy(max_server_delay_seconds=30))
    assert result.outcome is GraphSyncOutcome.RETRY_LATER
    assert result.retry_after_seconds == 600
    assert delays == [] and store.load(scope) is None


def test_retry_exhaustion_returns_retry_later() -> None:
    """Bound repeated throttling even when every individual delay is acceptable."""
    adapter, store, _service_unused = _service()
    delays: list[int] = []
    service = GraphSyncService(adapter, store, sleeper=delays.append)
    scope = _scope()
    adapter.register_initial(scope, "start")
    adapter.add_throttle(scope, "start", retry_after_seconds=1)
    adapter.add_throttle(scope, "start", retry_after_seconds=1)
    result = service.reconcile(scope, policy=GraphSyncPolicy(max_retries=1))
    assert result.outcome is GraphSyncOutcome.RETRY_LATER
    assert delays == [1] and store.load(scope) is None
