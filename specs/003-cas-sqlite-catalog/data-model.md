# Data Model: Content-Addressed Storage and SQLite Catalog

**Date**: 2026-07-22

This feature adds internal persistence records. They reuse F002 identity and UTC contracts but do not create new public interchange schemas or alter F002 identifier algorithms.

## Shared value rules

### Object identity

- Text form: `sha256:` plus exactly 64 lowercase hexadecimal characters.
- Meaning: SHA-256 over exact stored bytes.
- The source-version identity and source object identity are equal.
- Never accepted as a filesystem path; only validated digest segments are mapped internally.

### Fixed storage timestamp

- UTC-aware instant only.
- Stored as fixed-width RFC 3339 with exactly six fractional digits and `Z`, for example `2026-07-22T14:03:05.123456Z`.
- Lexicographic comparison is chronological because width and timezone are fixed.
- Public models may expose `datetime`; storage formatting is an adapter contract, not a new domain identity input.

### Source key

- `connector`: non-empty connector namespace.
- `locator`: non-empty opaque connector value.
- Identity is the exact pair `(connector, locator)` using binary string comparison.
- No case folding, whitespace trimming, Unicode normalization or path interpretation.

### Reference role

- Lowercase token beginning with a letter and containing letters, digits or underscores.
- Scoped by owner type; it is descriptive data, not executable authority.
- `ordinal >= 0` distinguishes repeated ordered roles.

## Domain records

### `StoredObject`

| Field | Type | Rule |
|---|---|---|
| `object_id` | SHA-256 ID | Must match exact object bytes |
| `byte_length` | integer | `>= 0` |

Immutable. It does not contain media type, path, body or mutable integrity state. Verification either returns this record or raises a typed error.

### `ObjectInventoryEntry`

| Field | Type | Rule |
|---|---|---|
| `object_id` | SHA-256 ID | Present for a canonical valid leaf |
| `byte_length` | integer | Size observed after verification |

Only fully verified canonical leaves become entries. Unsafe or malformed tree locations become `StoreAnomaly` records instead.

### `StoreAnomaly`

| Field | Type | Rule |
|---|---|---|
| `code` | enum | `MALFORMED_ENTRY`, `UNSAFE_ENTRY`, `CORRUPT_OBJECT`, `STAGING_RESIDUE` |
| `relative_location` | string | Sanitized path relative to the configured root |
| `object_id` | optional SHA-256 ID | Included only when safely derivable |

No anomaly message contains document bodies or absolute external paths.

### `LogicalDocument`

| Field | Type | Rule |
|---|---|---|
| `document_id` | UUIDv7 | Existing F002 `DocumentId` contract |
| `source_key` | `SourceKey` | Exact unique pair |
| `created_at` | UTC datetime | Original registration instant |

State is stable once registered. Re-registering the same source key returns the existing record. Reusing a document ID for another source key is a conflict.

### `ObjectReference`

| Field | Type | Rule |
|---|---|---|
| `role` | reference role | Non-empty validated token |
| `ordinal` | integer | `>= 0` |
| `object_id` | SHA-256 ID | Must exist and verify before commit |
| `byte_length` | integer | Verified immutable length, `>= 0` |
| `media_type` | optional string | Contextual reference metadata, not global object identity |

References are unique by `(role, ordinal)` within one owner. The same object may be referenced in multiple roles.

### `SourceVersionCommit`

| Field | Type | Rule |
|---|---|---|
| `document_id` | UUIDv7 | Must reference a registered document |
| `version_id` | SHA-256 ID | Exact original bytes |
| `source` | `StoredObject` | `source.object_id == version_id` |
| `media_type` | non-empty string | Source reference metadata |
| `source_modified_at` | optional UTC datetime | Connector-reported fact, not identity |
| `references` | ordered tuple of `ObjectReference` | Unique `(role, ordinal)`; source is not duplicated here |
| `committed_at` | UTC datetime | Commit observation time |

All referenced objects, including `source`, are verified by the persistence service before the catalog transaction. This record is a committed source-version fact, not a complete `READY` representation.

### `DocumentVersion`

Persisted result of `SourceVersionCommit`. It has the same immutable fields and composite identity
`(document_id, version_id)`. Retry comparison canonicalizes references by `(role, ordinal)` and compares source metadata,
including `source_modified_at`; a mismatch is `VersionConflict`. `committed_at` retains the first successful outcome and
may differ in a lost-response retry request without creating a conflict.

### `JobSpec`

| Field | Type | Rule |
|---|---|---|
| `job_id` | canonical UUID | Caller-provided idempotency identity |
| `kind` | token | Non-empty machine-readable job class |
| `deduplication_key` | non-empty string | Unique within `kind`; does not contain body content |
| `max_attempts` | integer | `1..100` |
| `references` | ordered tuple of `ObjectReference` | All retained as reachability roots |
| `created_at` | UTC datetime | Queue time |

Equivalent `(kind, deduplication_key)` retries return the same job. A differing immutable specification conflicts.

### `JobState`

```text
QUEUED
RUNNING
SUCCEEDED
FAILED
```

### `Job`

| Field | Type | Rule |
|---|---|---|
| `job_id` | canonical UUID | Stable |
| `kind` | token | Immutable |
| `deduplication_key` | string | Immutable with kind |
| `state` | `JobState` | State-machine constrained |
| `attempt_count` | integer | `0 <= attempt_count <= max_attempts` |
| `max_attempts` | integer | `1..100`, immutable |
| `revision` | integer | Starts at 0, increases for every mutation |
| `active_owner_id` | optional string | Required only while running |
| `lease_expires_at` | optional UTC datetime | Required only while running |
| `last_failure_code` | optional token | Sanitized classification only |
| `created_at` | UTC datetime | Immutable |
| `updated_at` | UTC datetime | Monotonic by caller-supplied time |
| `terminal_at` | optional UTC datetime | Required only for terminal states |
| `references` | tuple of `ObjectReference` | Immutable roots |

Lease token hashes and last-transition token hashes are persistence-private, canonical SHA-256 capability proofs and are
not exposed as body-like domain data. Mutating transition timestamps cannot precede the current projection's
`updated_at`.

### `JobLease`

| Field | Type | Rule |
|---|---|---|
| `job` | `Job` | Must be `RUNNING` |
| `lease_token` | secret string | Raw caller capability, never persisted or represented in logs |

The caller supplies the strong random token for idempotent lost-response retries; the adapter stores only SHA-256.

### `JobEvent`

| Field | Type | Rule |
|---|---|---|
| `job_id` | UUID | Parent job |
| `sequence` | integer | Starts at 1, contiguous per job |
| `event_type` | enum/token | `ENQUEUED`, `CLAIMED`, `RENEWED`, `COMPLETED`, `RETRY_QUEUED`, `FAILED`, `LEASE_RECOVERED`, `LEASE_EXHAUSTED` |
| `from_state` | optional state | Null only for enqueue |
| `to_state` | state | Resulting state |
| `occurred_at` | UTC datetime | Fixed-width persisted time |
| `attempt_count` | integer | Attempt after transition |
| `owner_id` | optional string | Identifier only |
| `failure_code` | optional token | Sanitized classification |

Projection mutation and event append occur in the same SQLite transaction. Event records validate that classification,
from/to state, attempt/owner shape and failure-code presence agree. Events contain no raw token, source locator, payload
or exception text.

### `RecoveryResult`

| Field | Type | Rule |
|---|---|---|
| `requeued_job_ids` | sorted tuple of UUID | Expired jobs with attempts remaining |
| `failed_job_ids` | sorted tuple of UUID | Expired jobs at attempt limit |
| `recovered_at` | UTC datetime | Caller-supplied recovery instant |

Repeating recovery at the same or later instant without new expired running jobs yields empty job-id tuples.

### `ReferenceSnapshot`

| Field | Type | Rule |
|---|---|---|
| `object_ids` | sorted tuple of SHA-256 IDs | Union of committed version and all job references |
| `observed_at` | UTC datetime | Snapshot time supplied by service |
| `catalog_schema_version` | integer | Installed revision |

The `objects` metadata table is not itself a reachability root.

### `ReachabilityReport`

| Field | Type | Rule |
|---|---|---|
| `observed_at` | UTC datetime | Catalog snapshot observation |
| `catalog_schema_version` | integer | Snapshot revision |
| `reachable` | sorted tuple of `StoredObject` | Verified and referenced |
| `candidates` | sorted tuple of `StoredObject` | Verified but unreferenced in snapshot |
| `inconsistencies` | sorted tuple of `ReachabilityIssue` | Missing/corrupt live references, corrupt candidates, unsafe/malformed layout or staging residue |

`candidate` never means approved for deletion. The report operation has no mutation or delete capability.

## SQLite relations

```text
documents 1 ---- * document_versions
objects   1 ---- * document_versions (source_object_id)
document_versions 1 ---- * version_object_references * ---- 1 objects
jobs      1 ---- * job_events
jobs      1 ---- * job_object_references * ---- 1 objects
```

### Revision 1

- `schema_migrations`
- `objects`
- `documents`
- `document_versions`
- `version_object_references`
- index on version reference `object_id`

### Revision 2

- `jobs`
- `job_events`
- `job_object_references`
- queue, lease-expiry, unique active-token and job-reference indexes

All tables are strict where supported by the pinned Python 3.12 SQLite runtime. Foreign keys are enabled and checked on every migrated catalog.

## State transitions

```text
create:          none      -> QUEUED     attempt 0
claim:           QUEUED    -> RUNNING    attempt +1, new owner/token/expiry
renew:           RUNNING   -> RUNNING    same unexpired owner/token
complete:        RUNNING   -> SUCCEEDED  lease cleared, terminal time set
retryable fail:  RUNNING   -> QUEUED     when attempt < max_attempts
terminal fail:   RUNNING   -> FAILED     otherwise
recover expired: RUNNING   -> QUEUED     when attempt < max_attempts
recover exhausted: RUNNING -> FAILED     when attempt == max_attempts
```

An active lease satisfies `lease_expires_at > now`. At equality it is expired. `SUCCEEDED` and `FAILED` are terminal and never return to a non-terminal state.

## Invariant ownership

| Invariant | Owner |
|---|---|
| Identity syntax, UUID version, timestamp awareness, reference uniqueness | Domain models |
| Digest/length matches exact physical bytes | Object-store adapter |
| Source and every reference physically verify before commit | Persistence service |
| Uniqueness, foreign keys, state shape, composite ownership | SQLite schema and adapter |
| Idempotent immutable equality and fenced compare-and-set | Catalog adapter |
| Cross-resource orphan classification | Reachability service |
| Parser completeness and `READY` representation | Later ingestion/index features |
