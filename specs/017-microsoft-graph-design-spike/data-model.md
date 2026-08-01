# Data Model: Microsoft Graph Design Spike

## Identity envelope

Every derived identifier is `SHA-256(RFC8785({domain, identity_version, payload}))`. Provider
identifiers are validated as bounded control-free strings only at the mock adapter boundary and
immediately converted to scope-bound digests. Python `hash()` is never used.

## GraphScope

- `tenant_id`: canonical Microsoft Entra tenant UUID.
- `site_id_digest`, `drive_id_digest`: provider identifiers hashed with tenant/scope context.
- `scope_id`: recomputed composite identity.
- Invariant: all four values agree; the same provider ID in another tenant produces another digest.

## GraphItemKey

- `scope_id`, `item_id_digest` and derived `item_key`.
- Invariant: item ID input is case-sensitive; path/name never appear.

## GraphRevisionHints

- optional scoped `etag_digest`, `ctag_digest`, `version_digest`.
- Invariant: at least one is present; values are remote change hints, not content hashes.

## PermissionSnapshotRef

- snapshot ID, exact scope/item key, authorization-context digest, observed UTC time.
- `complete` is structurally fixed to true.
- Invariant: every upsert references a complete exact-scope snapshot; ACL bodies/principals are absent.

## GraphDeltaChange

- ordered `ordinal`, item key, kind (`upsert` or `delete`), revision and permission reference.
- Upsert requires revision and permission; delete requires neither and becomes a tombstone.
- Repeated keys are permitted in ordered provider input.

## GraphDeltaPage

- scope, requested cursor handle, ordered changes and exactly one `next_cursor` or `delta_cursor`.
- Cursor values are adapter-owned opaque SHA-256 handles, never Graph URLs/tokens.

## GraphSyncPolicy

- bounded pages, changes, retries, fallback backoff and maximum allowed server wait.
- Invariants prevent zero/negative limits and contradictory backoff caps.

## GraphSyncState / GraphStoredItem

- exact scope, final cursor, monotonically increasing generation and sorted unique item records.
- Item records are active (revision + permission) or tombstone (neither).
- The state store publishes the complete new value atomically after expected-cursor validation.

## GraphSyncResult

- outcome (`applied`, `unchanged`, `reset_required`, `retry_later`), bounded counts, optional
  committed cursor and optional retry delay.
- Reset/retry results contain no committed cursor and imply no state publication.

## SubscriptionBinding / NotificationEnvelope / NotificationDecision

- Bind scope, subscription digest, client-state digest, expiry and `include_resource_data=false`.
- Envelope contains only digests and receipt time.
- Decision is `accepted`, `invalid` or `expired`; only accepted schedules reconciliation.
- Notification processing never advances a cursor or mutates item state.

## State transitions

```text
no state / committed state
  -> collect and validate all pages
  -> reduce repeated keys (last occurrence wins)
  -> compare expected cursor
  -> atomically publish generation + cursor + items

any reset / malformed page / cycle / limit / scope mismatch / store conflict
  -> no publication
```
