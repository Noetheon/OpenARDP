# Research: Local Watcher and Stable Jobs

## Decision 1 — Polling observations, complete reconciliation truth

**Decision**: F012 defines a `WatchScanner` port and ships one stdlib polling adapter.
Every cycle performs a deterministic bounded rescan. A scan result is authoritative
only when enumeration finishes within all bounds and the root identity is unchanged.
Overflow or any incomplete condition records `rescan_required` without applying partial
entries, deletions or scheduling.

**Rationale**: Native event APIs differ across platforms and can overflow. Even a future
native provider requires a reconciliation scan, so beginning with that correctness
kernel minimizes dependencies and unsupported delivery claims.

**Alternatives considered**:

- Watchdog/native events as truth: rejected because queue overflow and platform rename
  semantics cannot establish current state.
- Recursive glob in the service: rejected because path/device/link policy belongs in a
  filesystem adapter.
- Unbounded periodic walk: rejected as a local denial-of-service surface.

## Decision 2 — Strict explicit root authority

**Decision**: Root admission uses a canonical absolute directory supplied by the
operator, rejects every symlink/junction component and recognizable Windows UNC/device
form, records its `(device, inode/file identity)` evidence and refuses overlap in either
direction with the workspace. Recursive traversal never follows links, never crosses
the root device and never exceeds configured depth or entry count.

**Rationale**: A watcher is durable filesystem authority. Implicit parents, workspace
feedback loops and linked escape paths would expand that authority unexpectedly.

On POSIX, portable stdlib cannot reliably classify every remote mount. F012 therefore
states that network/shared filesystems are unsupported, enforces recognizable cases and
same-device traversal, and does not claim universal detection.

**Alternatives considered**:

- Automatically exclude `.openardp`: rejected because a differently named or nested
  workspace can still create a feedback loop; disjoint roots are auditable.
- Follow links that resolve inside the root: rejected because targets can be replaced
  and platform junction semantics differ.
- Cross mounted descendants: rejected because remote/removable boundaries can change
  scan and durability semantics.

## Decision 3 — Persist metadata stability, hash bytes only during ingestion

**Decision**: A path observation fingerprint includes root-device identifier, file
identity, byte length, nanosecond mtime and mode. The same fingerprint must appear in
complete scans spanning the configured stability duration. Exact bytes are not read by
the scanner and only the existing ingestion service creates the SHA-256 version.

**Rationale**: Hashing every file every polling cycle would recreate redundant I/O and
still could not replace the snapshot service's descriptor stability checks. Metadata is
safe as debounce evidence, not content identity.

Clock rollback leaves the entry a candidate until a later monotonic UTC observation;
it never shortens the stability window. A zero duration is accepted only as explicit
configuration and still requires one complete observation.

**Alternatives considered**:

- Size/mtime only: rejected because replacement can retain both.
- One successful stat: rejected because writers commonly update in place.
- Scanner content hashing: rejected as redundant and potentially expensive.

## Decision 4 — Path-addressed rename and tombstone semantics

**Decision**: Watch entries are keyed by `(root_id, relative_locator_digest)` and retain
the validated relative locator privately in SQLite. A missing live entry after a
complete scan becomes a tombstone. An unambiguous old/new file-identity match may append
a redacted rename-hint event, but the old source remains tombstoned and the new locator
starts a fresh stability lifecycle.

**Rationale**: Existing `SourceKey(connector="local", locator=absolute_path)` is
path-addressed. Treating an inode move as the same document would silently change a
released identity algorithm and is unsafe with inode reuse/hard links.

**Alternatives considered**:

- Move the existing document identity: rejected as an unapproved persisted-identity
  change.
- Hash all missing/new files to infer moves: rejected as expensive and ambiguous.
- Delete catalog documents: rejected because originals/evidence history are immutable.

## Decision 5 — Canonical stable-observation jobs and separate targets

**Decision**: Job kind is `watch_ingest`. The deduplication key is a versioned,
domain-separated JCS/SHA-256 digest over root semantic identity, relative locator
digest, exact observation fingerprint, parser profile and scheduling configuration
that affects meaning. A `watch_job_targets` row stores the validated root/relative path
and observation facts; generic job events never carry them.

**Rationale**: Generic jobs intentionally store only a key and CAS reference roots.
Encoding a raw path in that key would leak into diagnostics and weaken a generic
contract. One transactional catalog method must create/reuse both job and target so a
worker never observes an unbound job.

Operational timestamps, process/owner identity, absolute root and retry count are
excluded from semantic identity. Different observations at the same path create
different jobs, preventing a failed/stale job from being silently resurrected.

## Decision 6 — Extend the released job machine truthfully

**Decision**: Workspace revision 9 rebuilds `jobs`, `job_events` and
`job_object_references` inside one migration transaction because SQLite cannot alter
their released CHECK constraints. It adds:

- terminal state `CANCELLED`;
- `available_at` for claim eligibility;
- nullable `cancellation_requested_at` for a running cooperative request;
- events `CANCEL_REQUESTED` and `CANCELLED`;
- cancellation-aware recovery results.

Every revision-2 fact is copied exactly with `available_at=created_at` and no
cancellation request, and row/event/reference counts plus foreign-key integrity are
tested after the swap.

**Rationale**: Encoding cancellation as `FAILED` would make user intent and retry
semantics false. A separate watcher-only state machine would duplicate established
lease/fencing logic and allow inconsistent ownership.

**Alternatives considered**:

- Side-table cancellation projected as failure: rejected as semantically dishonest.
- Leave job constraints untouched and add a new scheduler table: rejected as duplicate
  state authority.
- Modify migration 2: prohibited because its released checksum is immutable.

## Decision 7 — Fenced cooperative cancellation

**Decision**: A queued cancellation atomically becomes `CANCELLED`. A running request
sets `cancellation_requested_at`, increments revision and appends one RUNNING→RUNNING
event. The owner learns the new revision by reading its job and acknowledges with the
same lease token; acknowledgement transitions RUNNING→CANCELLED. Old revisions cannot
renew, complete or fail. Expired cancellation-requested jobs recover directly to
`CANCELLED`.

Worker checkpoints occur before target reconstruction, before ingestion, at exposed
ingestion orchestration checkpoints and before job completion. Cancellation is
cooperative and bounded by the active parser operation's existing timeout; it does not
undo an ingestion commit that won the race.

**Rationale**: Revision invalidation makes the operator decision dominate stale worker
messages. Retaining the lease during a request lets the real owner stop cleanly without
another claimant entering.

**Alternatives considered**:

- Kill arbitrary worker processes: rejected as unsafe and not portable across
  independently invoked CLI processes.
- Immediately cancel RUNNING without acknowledgement: rejected because the active
  owner needs a durable checkpoint signal and audit of the final transition.
- Roll back committed evidence: impossible for immutable evidence and contrary to
  authority/history rules.

## Decision 8 — Eligible retries and deterministic recovery

**Decision**: `available_at` is persisted for all jobs and used in claim ordering
`(available_at, created_at, job_id)`. Watch retry delay is
`min(base_delay * 2 ** (attempt_count - 1), maximum_delay)` using bounded integer
milliseconds and no jitter. Retry transition persists `available_at=now+delay`.

Startup and each cycle call expired-lease recovery before scanning. Ordinary expired
jobs requeue immediately when attempts remain and otherwise fail; watch service failure
uses the configured delayed retry. Cancellation-requested expiry cancels. All transition
times must be monotonic relative to stored `updated_at`.

**Rationale**: Persisted eligibility survives restart and prevents tight retry loops.
No jitter makes tests and local audit exact; SQLite serialization already prevents a
claim stampede within one workspace.

## Decision 9 — Transactional backpressure and rescan

**Decision**: A watch configuration includes maximum scan entries, depth, active jobs,
jobs processed per cycle, attempts and retry bounds. Complete-scan reconciliation runs
in one SQLite write transaction. It counts nonterminal targets for the root before each
new schedule. At capacity it stops scheduling, records `BACKPRESSURE`, sets
`rescan_required`, but may still reconcile observed/tombstone facts from the complete
scan. Incomplete scans perform only a root-level `RESCAN_REQUIRED` update/event.

**Rationale**: A durable marker converts omitted scheduling into recoverable work. A
complete scan can safely update existence even when the worker queue is full; an
incomplete scan cannot safely infer absence.

**Alternatives considered**:

- Drop excess events: rejected because changes could be silently lost.
- Queue every change: rejected as unbounded storage/work amplification.
- Apply partial deletions on overflow: rejected because unseen entries are not absent.

## Decision 10 — Foreground composition and redacted events

**Decision**: CLI commands are:

- `openardp watch ROOT --store STORE [--once]` with explicit bounded configuration;
- `openardp jobs --store STORE [--state ...] [--limit ...]`;
- `openardp job-cancel JOB_ID --store STORE`.

`watch --once` performs recovery, one complete scan/reconciliation and a bounded number
of eligible jobs. Continuous mode repeats with an interruptible injected sleeper. Rich
files use the same explicit Docling model-root/manifest configuration as `ingest`; if
not configured, their jobs fail with a stable permanent capability classification.

Catalog watcher events store root/job/source digests, classifications, counts and UTC
time only. Job inspection returns job id/kind/state/attempts/revision/eligibility and
cancellation facts, never deduplication keys, paths, owners, tokens or failure strings
not on the stable allowlist.

**Rationale**: Foreground-first operation is observable and easy to stop. A daemon or
remote write API requires a separate threat/operations design.

## Decision 11 — No public schema or new dependency

**Decision**: F012 runtime records remain internal Pydantic/catalog contracts. Existing
public schema bytes, MCP descriptors, evidence vectors and export profiles are frozen.
No dependency or lock change is planned.

**Rationale**: No external interchange consumer exists for local watcher state. Adding
a public contract now would prematurely freeze operational fields.

## Known limitations

- Polling latency is configuration-bound and no zero-loss event-delivery claim is made.
- Remote POSIX mount detection is not portable; those roots are unsupported even when
  admission cannot identify them.
- Cancellation cannot preempt arbitrary native parser instructions instantly and does
  not undo committed evidence.
- One foreground process executes jobs serially by default; horizontal scheduling is
  supported by catalog fencing but not tuned as a throughput feature.
- Tombstones affect watcher availability facts only; F013 decides retention and F004
  historical evidence remains queryable.
