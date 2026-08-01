"""Pure Microsoft Graph design-spike contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from openardp.domain.graph import (
    GraphChangeKind,
    GraphDeltaChange,
    GraphDeltaPage,
    GraphItemState,
    GraphNotificationDecision,
    GraphNotificationEnvelope,
    GraphNotificationStatus,
    GraphScope,
    GraphStoredItem,
    GraphSubscriptionBinding,
    GraphSyncPolicy,
    graph_item_key,
    graph_permission_snapshot_ref,
    graph_revision_hints,
    graph_scope,
    graph_scoped_digest,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
TENANT = UUID("11111111-1111-4111-8111-111111111111")


def _scope() -> GraphScope:
    return graph_scope(tenant_id=TENANT, site_id="site-A", drive_id="drive-A")


def _upsert(ordinal: int = 0) -> GraphDeltaChange:
    scope = _scope()
    key = graph_item_key(scope, "CaseSensitiveItem")
    return GraphDeltaChange(
        ordinal=ordinal,
        key=key,
        kind=GraphChangeKind.UPSERT,
        revision=graph_revision_hints(scope, key, etag='"etag-1"'),
        permission=graph_permission_snapshot_ref(
            scope,
            key,
            snapshot_version="permissions-1",
            authorization_context="selected-site-reader",
            observed_at=NOW,
        ),
    )


def test_scope_and_item_identity_are_tenant_bound_case_sensitive_and_path_free() -> None:
    """Bind provider identity to exact scope without mutable locator metadata."""
    scope = _scope()
    same = graph_scope(tenant_id=TENANT, site_id="site-A", drive_id="drive-A")
    other_tenant = graph_scope(
        tenant_id=UUID("22222222-2222-4222-8222-222222222222"),
        site_id="site-A",
        drive_id="drive-A",
    )
    assert scope == same
    assert scope.scope_id != other_tenant.scope_id
    assert graph_item_key(scope, "Item").item_key != graph_item_key(scope, "item").item_key
    assert set(scope.model_dump()) == {"tenant_id", "site_id_digest", "drive_id_digest", "scope_id"}
    assert set(graph_item_key(scope, "Item").model_dump()) == {
        "scope_id",
        "item_id_digest",
        "item_key",
    }


def test_scope_and_item_reject_tampered_derived_identity() -> None:
    """Make every composite identity self-validating."""
    scope = _scope()
    with pytest.raises(ValidationError, match="scope_id"):
        GraphScope(
            tenant_id=scope.tenant_id,
            site_id_digest=scope.site_id_digest,
            drive_id_digest=scope.drive_id_digest,
            scope_id="sha256:" + "0" * 64,
        )
    key = graph_item_key(scope, "Item")
    with pytest.raises(ValidationError, match="item_key"):
        type(key)(
            scope_id=key.scope_id,
            item_id_digest=key.item_id_digest,
            item_key="sha256:" + "0" * 64,
        )


def test_revision_hints_require_one_scoped_value() -> None:
    """Represent remote revisions as optional hints, never source hashes."""
    scope = _scope()
    key = graph_item_key(scope, "Item")
    with pytest.raises(ValueError, match="revision hint"):
        graph_revision_hints(scope, key)
    hints = graph_revision_hints(scope, key, etag="one", version="7")
    assert hints.ctag_digest is None
    assert hints.etag_digest != hints.version_digest
    assert hints.scope_id == scope.scope_id and hints.item_key == key.item_key


def test_upsert_requires_exact_complete_permission_and_delete_is_tombstone() -> None:
    """Fail closed on missing ACL evidence while allowing sparse deletion facts."""
    upsert = _upsert()
    with pytest.raises(ValidationError, match="upsert"):
        GraphDeltaChange(
            ordinal=upsert.ordinal,
            key=upsert.key,
            kind=upsert.kind,
            revision=upsert.revision,
        )
    tampered_permission = upsert.permission.model_copy(update={"item_key": "sha256:" + "0" * 64})
    with pytest.raises(ValidationError, match="item_key"):
        GraphDeltaChange(
            ordinal=upsert.ordinal,
            key=upsert.key,
            kind=upsert.kind,
            revision=upsert.revision,
            permission=tampered_permission,
        )
    deleted = GraphDeltaChange(
        ordinal=1,
        key=upsert.key,
        kind=GraphChangeKind.DELETE,
    )
    assert deleted.revision is None and deleted.permission is None
    with pytest.raises(ValidationError, match="delete"):
        GraphDeltaChange(
            ordinal=deleted.ordinal,
            key=deleted.key,
            kind=deleted.kind,
            revision=upsert.revision,
        )


def test_page_requires_ordered_changes_and_exactly_one_cursor() -> None:
    """Keep provider order and one unambiguous continuation/final state."""
    scope = _scope()
    start = graph_scoped_digest(scope.scope_id, kind="cursor", value="start")
    end = graph_scoped_digest(scope.scope_id, kind="cursor", value="end")
    page = GraphDeltaPage(
        scope_id=scope.scope_id,
        requested_cursor=start,
        changes=(_upsert(0), _upsert(1)),
        delta_cursor=end,
    )
    assert page.delta_cursor == end
    with pytest.raises(ValidationError, match="exactly one"):
        GraphDeltaPage(
            scope_id=page.scope_id,
            requested_cursor=page.requested_cursor,
            changes=page.changes,
            next_cursor=end,
            delta_cursor=end,
        )
    with pytest.raises(ValidationError, match="ordered"):
        GraphDeltaPage(
            scope_id=page.scope_id,
            requested_cursor=page.requested_cursor,
            changes=(_upsert(2), _upsert(1)),
            delta_cursor=end,
        )


def test_policy_is_bounded_and_backoff_is_deterministic() -> None:
    """Make resource and retry ceilings explicit immutable policy."""
    policy = GraphSyncPolicy(retry_base_seconds=2, retry_cap_seconds=5)
    assert [policy.fallback_delay(attempt) for attempt in range(4)] == [2, 4, 5, 5]
    with pytest.raises(ValidationError):
        GraphSyncPolicy(max_pages=0)
    with pytest.raises(ValidationError, match="retry cap"):
        GraphSyncPolicy(retry_base_seconds=5, retry_cap_seconds=4)


def test_stored_item_state_is_closed() -> None:
    """Require active evidence and sparse explicit tombstones."""
    change = _upsert()
    active = GraphStoredItem(
        key=change.key,
        state=GraphItemState.ACTIVE,
        revision=change.revision,
        permission=change.permission,
    )
    tombstone = GraphStoredItem(key=change.key, state=GraphItemState.TOMBSTONE)
    assert active.permission is not None
    assert tombstone.revision is None
    with pytest.raises(ValidationError, match="tombstone"):
        GraphStoredItem(
            key=tombstone.key,
            state=tombstone.state,
            permission=change.permission,
        )


def test_notification_records_are_secret_free_and_decision_invariants_are_closed() -> None:
    """Represent only digests and ensure accepted is the only scheduling status."""
    scope = _scope()
    subscription = graph_scoped_digest(scope.scope_id, kind="subscription", value="sub-1")
    client_state = graph_scoped_digest(scope.scope_id, kind="client_state", value="secret-value")
    binding = GraphSubscriptionBinding(
        scope_id=scope.scope_id,
        subscription_id_digest=subscription,
        client_state_digest=client_state,
        expires_at=NOW + timedelta(hours=1),
    )
    envelope = GraphNotificationEnvelope(
        scope_id=scope.scope_id,
        subscription_id_digest=subscription,
        client_state_digest=client_state,
        received_at=NOW,
    )
    assert binding.include_resource_data is False
    assert "secret-value" not in repr(binding)
    assert envelope.scope_id == scope.scope_id
    decision = GraphNotificationDecision(
        status=GraphNotificationStatus.ACCEPTED,
        schedule_reconciliation=True,
    )
    assert decision.schedule_reconciliation
    with pytest.raises(ValidationError, match="schedule"):
        GraphNotificationDecision.model_validate(
            {
                **decision.model_dump(),
                "status": GraphNotificationStatus.INVALID,
            }
        )


def test_raw_provider_values_are_bounded_control_free() -> None:
    """Reject ambiguous or dangerous values before hashing them into handles."""
    scope = _scope()
    with pytest.raises(ValueError, match="provider value"):
        graph_scoped_digest(scope.scope_id, kind="cursor", value="bad\nvalue")
    with pytest.raises(ValueError, match="provider value"):
        graph_scoped_digest(scope.scope_id, kind="cursor", value="x" * 4097)
    with pytest.raises(ValueError, match="digest kind"):
        graph_scoped_digest(scope.scope_id, kind="bad kind", value="okay")
