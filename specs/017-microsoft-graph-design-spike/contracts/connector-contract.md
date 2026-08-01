# Contract: Mock Enterprise Delta Connector 0.1.0

Status: experimental, internal, mock-only.

## Delta client port

- `initial_cursor(scope) -> cursor_handle`
- `fetch_page(scope, cursor_handle) -> GraphDeltaPage`
- May raise only sanitized reset, throttle or connector failures.
- It owns all raw provider values and returns no URL, token, path, name, body or secret.
- A cursor handle is valid only in the exact scope used to derive it.

## State port

- `load(scope) -> GraphSyncState | None`
- `commit(scope, expected_cursor, final_cursor, changes) -> GraphSyncState`
- Commit is optimistic and atomic. A failed expected-cursor check, validation failure or injected
  fault publishes neither items nor cursor.
- Tombstones remain explicit; callers do not infer deletion from absence.

## Reconciliation service

1. Load current state; otherwise request the adapter's initial scoped handle.
2. Fetch bounded pages and validate exact scope/requested cursor/one-link invariants.
3. Retry 429 responses within policy without losing accumulated pages.
4. Stop with no commit on reset, cycle, malformed page, limit, connector failure or retry-later.
5. Reduce all repeated item keys by final ordered occurrence.
6. Commit the reduced changes and final cursor once.

The service does not fetch content, evaluate ACLs, authorize a caller or execute provider data.

## Notification contract

Constant-time compare subscription and client-state digests, enforce exact scope and expiry, and
return a body-free decision. An accepted decision is only permission to schedule reconciliation.
It is not permission to mutate state, download content or execute any instruction.

## Compatibility

This profile has no JSON interchange schema and is not a stable external API. A production adapter,
persistent enterprise state implementation or changed identity requires a separate feature and ADR.
