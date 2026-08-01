# Data Model: Retention, Recovery and Migrations

## 1. Version dimensions

| Dimension | F013 value | Impact |
|---|---|---|
| workspace | SQLite revision `10` | additive maintenance/retention state |
| retention/plan identity | internal version `1` | JCS/SHA-256, not public interchange |
| backup manifest | internal `openardp-backup-v1` | exact-runtime recovery artifact |
| public schemas | unchanged | all generated schema bytes frozen |
| MCP/provider/export | unchanged | no mutation, provider or interchange decision |

## 2. Retention policy and hold

`RetentionPolicy` contains candidate minimum age, quarantine grace, reserve bytes and
inventory entry/byte limits. Minimum candidate age is at least 24 hours; grace defaults
to seven days and its irreversible floor is at least 24 hours. Operators may only
extend the time floors.

`RetentionHold` contains exact object identity, a closed reason code, created UTC,
optional expiry UTC and optional release UTC. A hold is active when unreleased and
unexpired at the plan observation instant. Free-form document or path text is not
stored.

## 3. Root snapshot and inventory

`RetentionRoot` contains `object_id`, a closed reference-family reason and an opaque
SHA-256 digest of the exact catalog row identity. Duplicate object roots remain
explainable but sort/deduplicate as exact edges.

`MaintenanceObject` contains exact object identity, length, safe modification
nanoseconds and location state `ACTIVE` or `QUARANTINE`. The filesystem adapter also
returns closed inconsistencies for malformed, unsafe, corrupt, hard-linked and staging
entries. A completed bounded inventory has a canonical semantic digest.

## 4. Reclamation plan

`ReclamationPlan` is immutable and not persisted by dry run:

- profile/version and semantic `plan_id`;
- policy and policy identity;
- catalog revision and root/hold snapshot digest;
- active inventory/anomaly digest;
- exact sorted protected explanations and candidates;
- observation UTC as reporting metadata only.

The plan projection used for `plan_id` excludes observation/rendering time but includes
every semantic field and exact candidate object metadata. An incomplete/anomalous scan
has no actionable plan.

## 5. Revision-10 durable tables

### `retention_holds`

Exact object, closed reason, created/expires/released UTC and body-free release reason.
Released/expired rows remain audit history. Active lookup is indexed by object/time.

### `quarantine_batches`

Batch ID, plan/policy/root/inventory identities, quarantine/not-before UTC, state
`PREPARED`, `QUARANTINED`, `PARTIALLY_RESTORED`, `RESTORED`, `COMMITTING`, `COMMITTED`
or `BLOCKED`, exact entry count/bytes and terminal UTC.

### `quarantine_entries`

Batch/object identity, exact length, reason, lifecycle `PLANNED`, `QUARANTINED`,
`RESTORED`, `COMMITTED_REMOVED` or `CONFLICT_RETAINED`, and transition UTCs. Identity
and length remain by value even after the unreferenced `objects` registry row is removed.
At most one nonterminal quarantine owner exists per object.

### `maintenance_operations`

Operation ID, kind `QUARANTINE`, `RESTORE`, `COMMIT`, `BACKUP`, `MIGRATE` or
`INDEX_REBUILD`; subject digest; state `PREPARED`, `APPLYING`, `SUCCEEDED`, `FAILED` or
`BLOCKED`; exact acknowledgement digest where commit requires it; created/updated/
terminal UTC and stable failure code. A partial unique index allows one active
`PREPARED`/`APPLYING` row.

### `maintenance_operation_entries`

Operation ID plus sequence, exact object identity/length, action `MOVE_TO_QUARANTINE`,
`MOVE_TO_ACTIVE`, `DELETE`, `RESTORE_CONFLICT` or `COPY`, expected source/destination
state and terminal outcome. Entries are complete before any filesystem mutation.

### `maintenance_events`

Operation/batch scoped sequence, closed event type, object identity when necessary,
counts/bytes and UTC. No arbitrary message, path or exception text.

### `migration_backups`

Target revision, source revision, internal manifest identity, created UTC and verified
flag. Migration 10 inserts this fact in the same transaction that installs the schema
when upgrading revision 9; fresh revision-10 initialization records none.

## 6. State transitions

```text
plan (external value)
  -> PREPARED quarantine intent -> APPLYING -> QUARANTINED
  -> PREPARED restore intent    -> APPLYING -> RESTORED
  -> PREPARED commit intent     -> APPLYING -> COMMITTED/BLOCKED
```

An operation becomes active only after its complete entries commit. Recovery only
replays that exact active operation. Before an intent commits, no managed file moves.
Commit intent is forward-only after its first delete-capable entry can run.

For each move entry:

| Active | Quarantine | Meaning |
|---|---|---|
| exact | absent | quarantine not started / restore complete |
| absent | exact | quarantine complete / restore not started |
| same inode exact | same inode exact | POSIX link/unlink transition; replayable |
| independent/corrupt | any | ambiguous; block |
| absent | absent | data loss/inconsistent; block unless commit entry already records removal |

## 7. Backup manifest

The canonical internal manifest records profile/version, created UTC, marker hash,
catalog file hash/length/revision/migration checksums, exact sorted file entries,
active-root and recoverable-quarantine sets, retention-state digests, excluded category
counts and complete marker identity. Paths are bounded relative POSIX paths only.

`created_at` is descriptive manifest content and therefore contributes to manifest
identity; deterministic equivalence is evaluated through the recorded catalog/object
sets, not by claiming repeated backups have the same manifest ID.

## 8. Diagnostics and index rebuild

`StorageDiagnostic` reports counts/logical bytes for active CAS, quarantine, staging
anomalies, catalog/sidecars and disposable index plus disk total/free/reserve and health
`HEALTHY`, `LOW_SPACE`, `INCONSISTENT` or `UNAVAILABLE`.

`IndexRebuildReport` records authoritative scope count, verified object count, prior and
new index row counts, orphan removal count, one corpus digest and UTC. The rebuild
transaction deletes/replaces the global accelerator only after every source entry has
been verified.
