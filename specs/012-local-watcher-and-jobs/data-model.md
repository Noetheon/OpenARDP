# Data Model: Local Watcher and Stable Jobs

## 1. Version dimensions

| Dimension | F012 value | Impact |
|---|---|---|
| application | package release | additive watcher service/CLI |
| workspace | SQLite revision `9` | job-table rebuild plus watcher tables |
| watch identity | version `1` JCS/SHA-256 domains | new internal persisted identities |
| public schemas | unchanged | all twelve generated schema bytes frozen |
| MCP | `0.1.0` unchanged | no tool or mutation added |
| provider/export profiles | unchanged | existing parser recipes reused |

## 2. Watch configuration

`WatchConfig` is a closed internal model containing:

- `recursive` and maximum depth;
- stability and polling intervals in integer milliseconds;
- maximum entries, active jobs and jobs processed per cycle;
- maximum attempts;
- retry base and maximum delay in integer milliseconds;
- text/rich parser profile names.

All values are bounded positive I-JSON-safe integers except stability, which may be
zero. Maximum retry delay is at least base delay. Non-recursive mode has effective
depth zero. The configuration hash includes every semantic field and excludes clock,
owner and absolute path.

## 3. Watch root

`WatchRoot` fields:

| Field | Rule |
|---|---|
| `root_id` | domain-separated digest of canonical root authority plus config identity |
| `root_path` | private canonical absolute path, bounded, never emitted in events |
| `root_path_digest` | SHA-256 of exact platform path encoding |
| `device_id` / `file_id` | bounded stable metadata strings from admitted directory |
| `config` / `config_hash` | exact semantic configuration |
| `generation` | non-negative complete-scan counter |
| `rescan_required` | durable convergence flag |
| `created_at` / `updated_at` | monotonic UTC |

An exact `root_id` retry must match all immutable fields. Changing configuration creates
a distinct root registration; it never silently mutates scheduling identity.

## 4. File observation and relative locator

`WatchFileFingerprint` contains device id, file id, byte length, nanosecond mtime and
regular-file mode. It contains no content hash.

`WatchObservation` fields:

- root id and opaque relative-locator digest;
- private normalized POSIX-style relative locator;
- state `CANDIDATE`, `STABLE` or `TOMBSTONED`;
- current fingerprint or null only when tombstoned;
- first/last observed UTC and stable-since UTC;
- last complete scan generation;
- last scheduled deduplication digest or null;
- revision and row fingerprint.

Relative locators are nonempty, contain no control/NUL, absolute prefix, `.` or `..`
segment and reconstruct strictly beneath the canonical root. Case is preserved. The
digest is over exact UTF-8 locator bytes and is used in all body-free projections.

State transitions:

```text
absent -> CANDIDATE
CANDIDATE --same fingerprint/window reached--> STABLE
CANDIDATE/STABLE --different fingerprint--> CANDIDATE
CANDIDATE/STABLE --missing complete scan--> TOMBSTONED
TOMBSTONED --reappears--> CANDIDATE
```

An incomplete scan performs no observation transition.

## 5. Stable watcher job target

`WatchJobTarget` is immutable:

| Field | Rule |
|---|---|
| `job_id` | foreign key to one generic `watch_ingest` job |
| `root_id` | admitted root |
| locator/digest | exact validated relative target |
| `fingerprint` | stable observation scheduled |
| `profile` | exact configured parser profile |
| `deduplication_key` | recomputed watch identity and equals generic job key |
| `created_at` | same as generic job creation |

The worker reconstructs `root_path / relative_locator`, repeats boundary/link/regular
file checks and requires the current fingerprint to equal the target before invoking
ingestion. A mismatch is a retryable source-race classification and a future complete
scan creates the job for the new fingerprint.

## 6. Generic job revision 9 projection

Existing `Job` adds:

- terminal `JobState.CANCELLED`;
- `available_at`, required and not before `created_at`;
- `cancellation_requested_at`, allowed only while RUNNING;
- `JobEventType.CANCEL_REQUESTED` and `CANCELLED`.

State invariants:

```text
QUEUED: no lease, no cancellation request, no terminal_at
RUNNING: owner + lease, optional cancellation request, no terminal_at
SUCCEEDED/FAILED/CANCELLED: no lease/request, terminal_at required
```

`available_at` is meaningful for QUEUED and retained as historical evidence in all
other states. A cancellation request increments revision but retains owner/token/lease.
Only a matching token with current revision may acknowledge it.

Job transition additions:

```text
QUEUED -> CANCELLED              CANCELLED
RUNNING -> RUNNING(requested)    CANCEL_REQUESTED
RUNNING(requested) -> CANCELLED  CANCELLED
RUNNING(requested, expired) -> CANCELLED  CANCELLED
```

Existing complete/fail/renew reject a cancellation-requested job. Replayed exact
cancel requests return current state without another event.

`RecoveryResult` adds sorted `cancelled_job_ids`; all result sets are disjoint.

## 7. Watch event

`WatchEventType` includes:

- `ROOT_REGISTERED`, `SCAN_COMPLETED`, `RESCAN_REQUIRED`;
- `OBSERVATION_CREATED`, `OBSERVATION_CHANGED`, `OBSERVATION_STABLE`;
- `TARGET_SCHEDULED`, `BACKPRESSURE`, `TOMBSTONED`, `REAPPEARED`;
- `RENAME_HINT`, `JOB_SUCCEEDED`, `JOB_RETRY`, `JOB_FAILED`, `JOB_CANCELLED`.

`WatchEvent` contains root id, sequence, type, optional source digest/job id, generation,
occurred-at, and non-negative entry/scheduled/tombstone counts. It contains no path,
filename, document body, owner, token or free-form message. Event-specific validation
permits only the identifiers/counts appropriate for the classification.

## 8. Scan result and cycle result

`WatchScan` contains the exact admitted root identity, scan start/end, complete boolean,
stable reason code when incomplete and sorted observations only when complete. A
complete result has at most `max_entries`; an incomplete result has no entries, which
prevents accidental partial reconciliation.

`WatchCycleResult` contains root id/generation, recovery counts, observed/candidate/
stable/tombstone/scheduled counts, queue/backpressure/rescan state and sorted processed
job summaries. It is body/path-free and drives CLI output.

## 9. Migration 9

Migration 9 atomically:

1. creates replacement revision-9 `jobs`, `job_events` and `job_object_references`;
2. copies every existing row, setting `available_at=created_at` and cancellation null;
3. swaps the tables and recreates released indexes with the eligible queue order;
4. creates `watch_roots`, `watch_observations`, `watch_job_targets` and `watch_events`;
5. creates deterministic lookup, queue and event indexes.

Foreign-key checks, counts and released migration checksums are verified by tests.
Failure rolls the full transaction back to revision 8.

## 10. Watcher catalog transaction

`reconcile_watch_scan(root, scan, now)`:

- rejects root/scan identity or time mismatch;
- for incomplete scans, updates only rescan state/event;
- for complete scans, increments generation and upserts every sorted observation;
- tombstones absent live rows only after all supplied entries validate;
- derives rename hints only for unique one-to-one file identities;
- promotes candidates whose persisted window elapsed;
- creates generic job plus target atomically while capacity remains;
- marks backpressure/rescan for stable unscheduled observations;
- appends body-free events and returns one complete cycle projection.

Same scan facts at the same or later valid time converge; older time/generation facts
fail closed. Exact concurrent job creation converges through generic unique keys.

## 11. Atomicity and reachability

Watcher state contains no document content or CAS object. A job invokes existing
ingestion, whose CAS-first/catalog-commit behavior remains unchanged. If ingestion
commits and the process crashes before completing the generic job, retry verifies and
reuses the same source representation before terminal success. Any complete unreachable
CAS residue is outside the watcher tables and remains F013 scope.
