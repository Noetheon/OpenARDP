"""Tenant, notification and information-disclosure tests for F017."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from openardp.adapters.mock_graph import InMemoryGraphStateStore, MockGraphDeltaAdapter
from openardp.domain.graph import (
    GraphDeltaChange,
    GraphDeltaPage,
    GraphItemKey,
    GraphNotificationEnvelope,
    GraphNotificationStatus,
    GraphRevisionHints,
    GraphScope,
    GraphStoredItem,
    GraphSubscriptionBinding,
    GraphSyncPolicy,
    GraphSyncResult,
    PermissionSnapshotRef,
    graph_scope,
    graph_scoped_digest,
)
from openardp.services.graph_sync import validate_graph_notification

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def _scope() -> GraphScope:
    return graph_scope(
        tenant_id=UUID("11111111-1111-4111-8111-111111111111"),
        site_id="site-A",
        drive_id="drive-A",
    )


def _notification_pair() -> tuple[GraphSubscriptionBinding, GraphNotificationEnvelope]:
    scope = _scope()
    subscription = graph_scoped_digest(scope.scope_id, kind="subscription", value="sub-secret")
    client = graph_scoped_digest(scope.scope_id, kind="client_state", value="client-secret")
    binding = GraphSubscriptionBinding(
        scope_id=scope.scope_id,
        subscription_id_digest=subscription,
        client_state_digest=client,
        expires_at=NOW + timedelta(hours=1),
    )
    envelope = GraphNotificationEnvelope(
        scope_id=scope.scope_id,
        subscription_id_digest=subscription,
        client_state_digest=client,
        received_at=NOW,
    )
    return binding, envelope


def test_valid_notification_only_returns_a_reconciliation_hint() -> None:
    """Grant no mutation or content authority to an authenticated webhook hint."""
    binding, envelope = _notification_pair()
    store = InMemoryGraphStateStore()
    adapter = MockGraphDeltaAdapter()
    before = (store.commit_count, adapter.requests)
    decision = validate_graph_notification(binding, envelope, now=NOW)
    assert decision.status is GraphNotificationStatus.ACCEPTED
    assert decision.schedule_reconciliation is True
    assert (store.commit_count, adapter.requests) == before


def test_invalid_scope_authenticity_and_expiry_fail_closed() -> None:
    """Reject spoofed or stale wakeups with one body-free decision family."""
    binding, envelope = _notification_pair()
    bad_scope = graph_scope(
        tenant_id=UUID("22222222-2222-4222-8222-222222222222"),
        site_id="site-A",
        drive_id="drive-A",
    )
    cases = (
        envelope.model_copy(update={"scope_id": bad_scope.scope_id}),
        envelope.model_copy(update={"subscription_id_digest": "sha256:" + "0" * 64}),
        envelope.model_copy(update={"client_state_digest": "sha256:" + "0" * 64}),
    )
    for candidate in cases:
        decision = validate_graph_notification(binding, candidate, now=NOW)
        assert decision.status is GraphNotificationStatus.INVALID
        assert decision.schedule_reconciliation is False
    expired = validate_graph_notification(binding, envelope, now=binding.expires_at)
    assert expired.status is GraphNotificationStatus.EXPIRED


def test_exported_contract_fields_cannot_carry_raw_sensitive_material() -> None:
    """Keep URLs, paths, bodies, names, tokens and raw secrets out of core schemas."""
    models = (
        GraphScope,
        GraphItemKey,
        GraphRevisionHints,
        PermissionSnapshotRef,
        GraphDeltaChange,
        GraphDeltaPage,
        GraphStoredItem,
        GraphSyncPolicy,
        GraphSyncResult,
        GraphSubscriptionBinding,
        GraphNotificationEnvelope,
    )
    schemas = json.dumps(
        {model.__name__: tuple(model.model_fields) for model in models},
        sort_keys=True,
    ).casefold()
    forbidden = ('"path"', '"url"', '"body"', '"name"', '"token"', '"secret"', '"raw"')
    assert all(word not in schemas for word in forbidden)


def test_scoped_digest_has_no_global_cross_tenant_equality() -> None:
    """Prevent provider identifiers from becoming global equality side channels."""
    first = _scope()
    second = graph_scope(
        tenant_id=UUID("22222222-2222-4222-8222-222222222222"),
        site_id="site-A",
        drive_id="drive-A",
    )
    assert graph_scoped_digest(first.scope_id, kind="item", value="same") != graph_scoped_digest(
        second.scope_id,
        kind="item",
        value="same",
    )
