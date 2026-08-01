"""Bounded atomic orchestration for the mock enterprise delta contract."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import datetime, timedelta

from openardp.domain.graph import (
    GraphDeltaChange,
    GraphDeltaPage,
    GraphNotificationDecision,
    GraphNotificationEnvelope,
    GraphNotificationStatus,
    GraphScope,
    GraphSubscriptionBinding,
    GraphSyncOutcome,
    GraphSyncPolicy,
    GraphSyncResult,
)
from openardp.ports.graph import (
    GraphConnectorError,
    GraphCursorReset,
    GraphDeltaClient,
    GraphStateStore,
    GraphThrottle,
)


def _no_sleep(_seconds: int) -> None:
    return


class GraphSyncService:
    """Collect one complete delta cycle and publish its reduced state exactly once."""

    def __init__(
        self,
        client: GraphDeltaClient,
        store: GraphStateStore,
        *,
        sleeper: Callable[[int], None] = _no_sleep,
    ) -> None:
        """Bind mock provider/state ports and an injectable deterministic sleeper."""
        self._client = client
        self._store = store
        self._sleeper = sleeper

    def reconcile(
        self,
        scope: GraphScope,
        *,
        policy: GraphSyncPolicy | None = None,
    ) -> GraphSyncResult:
        """Run one bounded page cycle with no partial cursor or item publication."""
        selected = policy or GraphSyncPolicy()
        current = self._store.load(scope)
        expected_cursor = current.cursor if current is not None else None
        cursor = expected_cursor or self._client.initial_cursor(scope)
        visited: set[str] = set()
        reduced: dict[str, GraphDeltaChange] = {}
        pages_seen = 0
        changes_seen = 0

        while True:
            if cursor in visited:
                raise GraphConnectorError("delta cursor cycle detected")
            visited.add(cursor)
            fetched = self._fetch_with_retry(
                scope,
                cursor,
                selected,
                pages_seen=pages_seen,
                changes_seen=changes_seen,
            )
            if isinstance(fetched, GraphSyncResult):
                return fetched
            page = fetched
            pages_seen += 1
            if pages_seen > selected.max_pages:
                raise GraphConnectorError("delta page limit exceeded")
            if page.scope_id != scope.scope_id or page.requested_cursor != cursor:
                raise GraphConnectorError("delta page scope is invalid")
            changes_seen += len(page.changes)
            if changes_seen > selected.max_changes:
                raise GraphConnectorError("delta change limit exceeded")
            for change in page.changes:
                if change.key.scope_id != scope.scope_id:
                    raise GraphConnectorError("delta change scope is invalid")
                reduced[change.key.item_key] = change
            if page.next_cursor is not None:
                cursor = page.next_cursor
                continue
            final_cursor = page.delta_cursor
            if final_cursor is None:
                raise GraphConnectorError("delta final cursor is absent")
            break

        changes = tuple(reduced[key] for key in sorted(reduced))
        published = self._store.commit(
            scope,
            expected_cursor=expected_cursor,
            final_cursor=final_cursor,
            changes=changes,
        )
        return GraphSyncResult(
            outcome=(GraphSyncOutcome.APPLIED if changes else GraphSyncOutcome.UNCHANGED),
            scope_id=scope.scope_id,
            pages_seen=pages_seen,
            changes_seen=changes_seen,
            changes_applied=len(changes),
            committed_cursor=published.cursor,
        )

    def _fetch_with_retry(
        self,
        scope: GraphScope,
        cursor: str,
        policy: GraphSyncPolicy,
        *,
        pages_seen: int,
        changes_seen: int,
    ) -> GraphDeltaPage | GraphSyncResult:
        retry_attempt = 0
        while True:
            try:
                return self._client.fetch_page(scope, cursor)
            except GraphCursorReset:
                return GraphSyncResult(
                    outcome=GraphSyncOutcome.RESET_REQUIRED,
                    scope_id=scope.scope_id,
                    pages_seen=pages_seen,
                    changes_seen=changes_seen,
                    changes_applied=0,
                )
            except GraphThrottle as error:
                delay = (
                    error.retry_after_seconds
                    if error.retry_after_seconds is not None
                    else policy.fallback_delay(retry_attempt)
                )
                if delay > policy.max_server_delay_seconds or retry_attempt >= policy.max_retries:
                    return GraphSyncResult(
                        outcome=GraphSyncOutcome.RETRY_LATER,
                        scope_id=scope.scope_id,
                        pages_seen=pages_seen,
                        changes_seen=changes_seen,
                        changes_applied=0,
                        retry_after_seconds=delay,
                    )
                self._sleeper(delay)
                retry_attempt += 1


def validate_graph_notification(
    binding: GraphSubscriptionBinding,
    envelope: GraphNotificationEnvelope,
    *,
    now: datetime,
) -> GraphNotificationDecision:
    """Validate one wakeup without mutating state, fetching content or advancing delta."""
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("notification validation time must be UTC")
    subscription_matches = hmac.compare_digest(
        binding.subscription_id_digest.encode("ascii"),
        envelope.subscription_id_digest.encode("ascii"),
    )
    client_state_matches = hmac.compare_digest(
        binding.client_state_digest.encode("ascii"),
        envelope.client_state_digest.encode("ascii"),
    )
    if now >= binding.expires_at:
        return GraphNotificationDecision(
            status=GraphNotificationStatus.EXPIRED,
            schedule_reconciliation=False,
        )
    if (
        binding.scope_id != envelope.scope_id
        or not subscription_matches
        or not client_state_matches
    ):
        return GraphNotificationDecision(
            status=GraphNotificationStatus.INVALID,
            schedule_reconciliation=False,
        )
    return GraphNotificationDecision(
        status=GraphNotificationStatus.ACCEPTED,
        schedule_reconciliation=True,
    )
