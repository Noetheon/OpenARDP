"""Pure tenant-scoped contracts for the mock Microsoft Graph design spike."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, JsonValue, model_validator

from openardp.domain.common import CanonicalUuid, DomainModel, Sha256Id, UtcDatetime
from openardp.domain.identity import canonical_sha256

GRAPH_CONTRACT_VERSION = "0.1.0"
GRAPH_IDENTITY_VERSION = 1
_DIGEST_KIND = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_MAX_PROVIDER_VALUE_CHARACTERS = 4096


def _identity(domain: str, payload: dict[str, JsonValue]) -> str:
    return canonical_sha256(
        {
            "domain": domain,
            "identity_version": GRAPH_IDENTITY_VERSION,
            "payload": payload,
        }
    )


def _validate_provider_value(value: str) -> None:
    if not value or len(value) > _MAX_PROVIDER_VALUE_CHARACTERS:
        raise ValueError("provider value must be non-empty and bounded")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("provider value must be control-free")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("provider value must be valid Unicode") from error


def graph_scoped_digest(scope_id: str, *, kind: str, value: str) -> str:
    """Digest one bounded case-sensitive provider value inside exact scope."""
    if _DIGEST_KIND.fullmatch(kind) is None:
        raise ValueError("digest kind must be a lowercase identifier")
    _validate_provider_value(value)
    return _identity(
        "openardp:graph-scoped-provider-value",
        {"scope_id": scope_id, "kind": kind, "value": value},
    )


def _scope_identity(tenant_id: UUID, site_id_digest: str, drive_id_digest: str) -> str:
    return _identity(
        "openardp:graph-scope",
        {
            "tenant_id": str(tenant_id),
            "site_id_digest": site_id_digest,
            "drive_id_digest": drive_id_digest,
        },
    )


class GraphScope(DomainModel):
    """Exact tenant/site/drive authority without raw provider resource IDs."""

    tenant_id: CanonicalUuid
    site_id_digest: Sha256Id
    drive_id_digest: Sha256Id
    scope_id: Sha256Id

    @model_validator(mode="after")
    def _identity_matches(self) -> Self:
        expected = _scope_identity(self.tenant_id, self.site_id_digest, self.drive_id_digest)
        if self.scope_id != expected:
            raise ValueError("scope_id does not match tenant/site/drive identity")
        return self


def graph_scope(*, tenant_id: UUID, site_id: str, drive_id: str) -> GraphScope:
    """Convert raw provider scope IDs into one self-validating tenant-scoped record."""
    tenant_scope = _identity("openardp:graph-tenant", {"tenant_id": str(tenant_id)})
    site_digest = graph_scoped_digest(tenant_scope, kind="site", value=site_id)
    drive_scope = _identity(
        "openardp:graph-site-scope",
        {"tenant_id": str(tenant_id), "site_id_digest": site_digest},
    )
    drive_digest = graph_scoped_digest(drive_scope, kind="drive", value=drive_id)
    return GraphScope(
        tenant_id=tenant_id,
        site_id_digest=site_digest,
        drive_id_digest=drive_digest,
        scope_id=_scope_identity(tenant_id, site_digest, drive_digest),
    )


def _item_identity(scope_id: str, item_id_digest: str) -> str:
    return _identity(
        "openardp:graph-item",
        {"scope_id": scope_id, "item_id_digest": item_id_digest},
    )


class GraphItemKey(DomainModel):
    """Stable case-sensitive provider item identity bound to one scope."""

    scope_id: Sha256Id
    item_id_digest: Sha256Id
    item_key: Sha256Id

    @model_validator(mode="after")
    def _identity_matches(self) -> Self:
        if self.item_key != _item_identity(self.scope_id, self.item_id_digest):
            raise ValueError("item_key does not match scoped item identity")
        return self


def graph_item_key(scope: GraphScope, item_id: str) -> GraphItemKey:
    """Digest a case-sensitive provider item ID without using path or name."""
    item_digest = graph_scoped_digest(scope.scope_id, kind="item", value=item_id)
    return GraphItemKey(
        scope_id=scope.scope_id,
        item_id_digest=item_digest,
        item_key=_item_identity(scope.scope_id, item_digest),
    )


class GraphRevisionHints(DomainModel):
    """Remote change hints that never substitute for original-byte identity."""

    scope_id: Sha256Id
    item_key: Sha256Id
    etag_digest: Sha256Id | None = None
    ctag_digest: Sha256Id | None = None
    version_digest: Sha256Id | None = None

    @model_validator(mode="after")
    def _has_a_hint(self) -> Self:
        if self.etag_digest is None and self.ctag_digest is None and self.version_digest is None:
            raise ValueError("at least one remote revision hint is required")
        return self


def graph_revision_hints(
    scope: GraphScope,
    key: GraphItemKey,
    *,
    etag: str | None = None,
    ctag: str | None = None,
    version: str | None = None,
) -> GraphRevisionHints:
    """Digest available provider revision values in their exact item scope."""
    if key.scope_id != scope.scope_id:
        raise ValueError("item key does not belong to graph scope")
    return GraphRevisionHints(
        scope_id=scope.scope_id,
        item_key=key.item_key,
        etag_digest=(
            graph_scoped_digest(key.item_key, kind="etag", value=etag) if etag is not None else None
        ),
        ctag_digest=(
            graph_scoped_digest(key.item_key, kind="ctag", value=ctag) if ctag is not None else None
        ),
        version_digest=(
            graph_scoped_digest(key.item_key, kind="version", value=version)
            if version is not None
            else None
        ),
    )


class PermissionSnapshotRef(DomainModel):
    """Complete external permission evidence for one exact item and authorization context."""

    snapshot_id: Sha256Id
    scope_id: Sha256Id
    item_key: Sha256Id
    authorization_context_digest: Sha256Id
    observed_at: UtcDatetime
    complete: Literal[True] = True


def graph_permission_snapshot_ref(
    scope: GraphScope,
    key: GraphItemKey,
    *,
    snapshot_version: str,
    authorization_context: str,
    observed_at: datetime,
) -> PermissionSnapshotRef:
    """Build an opaque complete permission reference without ACL bodies or principal names."""
    if key.scope_id != scope.scope_id:
        raise ValueError("item key does not belong to graph scope")
    version_digest = graph_scoped_digest(
        key.item_key,
        kind="permission_version",
        value=snapshot_version,
    )
    context_digest = graph_scoped_digest(
        scope.scope_id,
        kind="authorization",
        value=authorization_context,
    )
    observed = observed_at.isoformat(timespec="auto").replace("+00:00", "Z")
    snapshot_id = _identity(
        "openardp:graph-permission-snapshot",
        {
            "scope_id": scope.scope_id,
            "item_key": key.item_key,
            "version_digest": version_digest,
            "authorization_context_digest": context_digest,
            "observed_at": observed,
        },
    )
    return PermissionSnapshotRef(
        snapshot_id=snapshot_id,
        scope_id=scope.scope_id,
        item_key=key.item_key,
        authorization_context_digest=context_digest,
        observed_at=observed_at,
    )


class GraphChangeKind(StrEnum):
    """Authoritative provider change category."""

    UPSERT = "upsert"
    DELETE = "delete"


class GraphDeltaChange(DomainModel):
    """One ordered upsert or explicit tombstone observation."""

    ordinal: int = Field(ge=0, le=10_000_000)
    key: GraphItemKey
    kind: GraphChangeKind
    revision: GraphRevisionHints | None = None
    permission: PermissionSnapshotRef | None = None

    @model_validator(mode="after")
    def _change_is_closed(self) -> Self:
        if self.kind is GraphChangeKind.UPSERT:
            if self.revision is None or self.permission is None:
                raise ValueError("upsert requires revision and complete permission reference")
            if (
                self.revision.scope_id != self.key.scope_id
                or self.revision.item_key != self.key.item_key
                or self.permission.scope_id != self.key.scope_id
                or self.permission.item_key != self.key.item_key
                or not self.permission.complete
            ):
                raise ValueError("upsert evidence does not match item_key scope")
        elif self.revision is not None or self.permission is not None:
            raise ValueError("delete tombstone cannot carry revision or permission evidence")
        return self


class GraphDeltaPage(DomainModel):
    """One ordered page with exactly one continuation or final cursor handle."""

    scope_id: Sha256Id
    requested_cursor: Sha256Id
    changes: tuple[GraphDeltaChange, ...]
    next_cursor: Sha256Id | None = None
    delta_cursor: Sha256Id | None = None

    @model_validator(mode="after")
    def _page_is_closed(self) -> Self:
        if (self.next_cursor is None) == (self.delta_cursor is None):
            raise ValueError("page requires exactly one next_cursor or delta_cursor")
        previous = -1
        for change in self.changes:
            if change.key.scope_id != self.scope_id:
                raise ValueError("page change scope does not match page scope")
            if change.ordinal <= previous:
                raise ValueError("page changes must be strictly ordered by ordinal")
            previous = change.ordinal
        return self


class GraphSyncPolicy(DomainModel):
    """Bounded deterministic mock synchronization policy."""

    max_pages: int = Field(default=100, ge=1, le=1_000)
    max_changes: int = Field(default=10_000, ge=1, le=100_000)
    max_retries: int = Field(default=5, ge=0, le=10)
    retry_base_seconds: int = Field(default=1, ge=1, le=60)
    retry_cap_seconds: int = Field(default=30, ge=1, le=300)
    max_server_delay_seconds: int = Field(default=120, ge=1, le=3_600)

    @model_validator(mode="after")
    def _backoff_is_coherent(self) -> Self:
        if self.retry_cap_seconds < self.retry_base_seconds:
            raise ValueError("retry cap must not be below retry base")
        return self

    def fallback_delay(self, attempt: int) -> int:
        """Return deterministic capped exponential delay for a zero-based attempt."""
        if attempt < 0:
            raise ValueError("attempt must be non-negative")
        return min(self.retry_base_seconds * (1 << attempt), self.retry_cap_seconds)


class GraphItemState(StrEnum):
    """Durable mock state of a remote item."""

    ACTIVE = "active"
    TOMBSTONE = "tombstone"


class GraphStoredItem(DomainModel):
    """Current active item evidence or an explicit deletion tombstone."""

    key: GraphItemKey
    state: GraphItemState
    revision: GraphRevisionHints | None = None
    permission: PermissionSnapshotRef | None = None

    @model_validator(mode="after")
    def _state_is_closed(self) -> Self:
        if self.state is GraphItemState.ACTIVE:
            if self.revision is None or self.permission is None:
                raise ValueError("active item requires revision and permission evidence")
            if (
                self.revision.scope_id != self.key.scope_id
                or self.revision.item_key != self.key.item_key
                or self.permission.scope_id != self.key.scope_id
                or self.permission.item_key != self.key.item_key
            ):
                raise ValueError("active item evidence does not match item key")
        elif self.revision is not None or self.permission is not None:
            raise ValueError("tombstone cannot carry revision or permission evidence")
        return self


class GraphSyncState(DomainModel):
    """Atomically published tenant-scoped cursor and current item/tombstone set."""

    scope_id: Sha256Id
    cursor: Sha256Id
    generation: int = Field(ge=1)
    items: tuple[GraphStoredItem, ...]

    @model_validator(mode="after")
    def _items_are_scoped_sorted_unique(self) -> Self:
        keys = tuple(item.key.item_key for item in self.items)
        if any(item.key.scope_id != self.scope_id for item in self.items):
            raise ValueError("state item scope does not match state scope")
        if keys != tuple(sorted(set(keys))):
            raise ValueError("state items must be sorted and unique")
        return self


class GraphSyncOutcome(StrEnum):
    """Sanitized reconciliation outcome."""

    APPLIED = "applied"
    UNCHANGED = "unchanged"
    RESET_REQUIRED = "reset_required"
    RETRY_LATER = "retry_later"


class GraphSyncResult(DomainModel):
    """Body-free orchestration result that distinguishes non-commit outcomes."""

    outcome: GraphSyncOutcome
    scope_id: Sha256Id
    pages_seen: int = Field(ge=0)
    changes_seen: int = Field(ge=0)
    changes_applied: int = Field(ge=0)
    committed_cursor: Sha256Id | None = None
    retry_after_seconds: int | None = Field(default=None, ge=0, le=86_400)

    @model_validator(mode="after")
    def _result_is_closed(self) -> Self:
        committed = self.outcome in {GraphSyncOutcome.APPLIED, GraphSyncOutcome.UNCHANGED}
        if committed != (self.committed_cursor is not None):
            raise ValueError("committed outcomes require exactly one committed cursor")
        if self.outcome is GraphSyncOutcome.RETRY_LATER:
            if self.retry_after_seconds is None:
                raise ValueError("retry_later requires retry delay")
        elif self.retry_after_seconds is not None:
            raise ValueError("retry delay is valid only for retry_later")
        if self.changes_applied > self.changes_seen:
            raise ValueError("applied change count cannot exceed observed change count")
        return self


class GraphSubscriptionBinding(DomainModel):
    """Secret-free binding for one provider subscription."""

    scope_id: Sha256Id
    subscription_id_digest: Sha256Id
    client_state_digest: Sha256Id
    expires_at: UtcDatetime
    include_resource_data: Literal[False] = False


class GraphNotificationEnvelope(DomainModel):
    """Digested notification authenticity material and receipt time."""

    scope_id: Sha256Id
    subscription_id_digest: Sha256Id
    client_state_digest: Sha256Id
    received_at: UtcDatetime


class GraphNotificationStatus(StrEnum):
    """Public body-free notification decision category."""

    ACCEPTED = "accepted"
    INVALID = "invalid"
    EXPIRED = "expired"


class GraphNotificationDecision(DomainModel):
    """Wakeup-only decision; accepted is the sole scheduling state."""

    status: GraphNotificationStatus
    schedule_reconciliation: bool

    @model_validator(mode="after")
    def _schedule_matches_status(self) -> Self:
        if self.schedule_reconciliation != (self.status is GraphNotificationStatus.ACCEPTED):
            raise ValueError("schedule decision does not match notification status")
        return self
