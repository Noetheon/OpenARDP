# ADR 0013: Reconcile explicit local roots into cancellable durable jobs

Status: Accepted for Feature 012

Date: 2026-08-01

## Context

OpenARDP can ingest one explicit local file and already persists generic fenced jobs,
but it cannot monitor an operator-selected corpus. Filesystem notification APIs are
platform-specific hints that can overflow or miss events. A local watcher also creates
durable path authority and therefore must define root admission, link/device boundaries,
stability, rename/deletion, queue pressure, cancellation and crash recovery before it
can run safely.

The released revision-2 job state machine supports queued, running, succeeded and failed
work with leases and revisions. It has no delayed eligibility or cancellation state.
Calling cancellation a failure would make operator intent and retry behavior false; a
second watcher-only scheduler would duplicate ownership and fencing authority.

## Decision

### Use bounded polling reconciliation as the correctness kernel

Feature 012 introduces a provider-neutral scanner boundary and one stdlib polling
adapter. Each foreground cycle performs a deterministic bounded scan. Only a complete
scan whose root identity remains unchanged may update observations, infer absence or
schedule work. Overflow and other incomplete conditions discard partial observations,
set a durable rescan marker and append a redacted event.

Native notifications may be added later only as wake-up hints around this same
reconciliation contract. F012 makes no zero-loss or low-latency event-delivery claim.

### Grant only explicit disjoint local root authority

The operator supplies one directory root and workspace explicitly. Admission rejects
symlink/junction components, recognizable Windows network/device paths and overlap in
either direction between root and workspace. Traversal never follows links, escapes the
root, crosses the root device or exceeds depth/entry bounds.

Network/shared filesystems are unsupported. Portable stdlib cannot identify every
remote POSIX mount, so F012 documents that enforcement limitation rather than claiming
universal detection.

### Persist stability and path-addressed tombstones

File metadata is a scheduling hint. The same device/file identity, size, nanosecond
mtime and mode must persist across complete scans for the configured window before a
job is created. The existing source adapter still reads a stable descriptor and hashes
exact bytes for authoritative version identity.

Local `SourceKey` remains path-addressed. A rename tombstones the old locator and starts
a new lifecycle for the new locator even when a unique same-root file identity provides
a rename hint. Deletion creates a watcher tombstone only; no source, version, evidence,
derivation, context or visual record is deleted. Changing this identity or retention
rule requires another ADR.

### Extend the generic job state machine

Workspace revision 9 replaces the three job tables inside one atomic migration to add
the terminal `CANCELLED` state, persisted `available_at` eligibility and optional
running `cancellation_requested_at`. Every revision-2 row/event/reference is copied
unchanged except `available_at=created_at`; migrations 1-8 and their checksums remain
untouched.

Queued cancellation becomes terminal immediately. Running cancellation persists a
request, increments revision and leaves the current lease in place. The owner must read
the new revision and acknowledge using the same token; stale renew/complete/fail calls
are rejected. Expired cancellation-requested leases recover to `CANCELLED`.
Cancellation is cooperative at bounded service checkpoints and never promises rollback
of immutable objects or ingestion facts committed before the cancellation won.

Queued claims require `available_at <= now` and use total ordering. Watch retries use a
trusted, capped, integer exponential schedule without jitter. Eligibility and retry
facts survive restart.

### Persist watcher state and exact job targets atomically

Revision 9 also adds STRICT tables for roots, observations, watcher job targets and
redacted events. A semantic watch-ingest key binds root/config identity, relative
locator digest, metadata observation and parser profile through a versioned RFC
8785/SHA-256 domain. Raw paths stay in private root/target rows required for execution;
events, logs and default CLI projections contain only opaque digests/ids and counts.

One catalog transaction reconciles a complete scan, applies tombstones/stability,
enforces the active-job bound and creates or reuses the generic job plus its exact
target. Queue pressure records a rescan requirement so later cycles converge rather
than silently dropping work.

### Keep operation foreground-first and local

The supported surface is one foreground CLI cycle or an interruptible polling loop,
plus body-free job inspection and cancellation. It reuses the existing text and rich
ingestion services. F012 installs no daemon, background service, native watcher,
network listener, cloud provider or MCP write tool and adds no dependency.

## Compatibility

- Workspace schema advances additively from revision 8 to revision 9, although existing
  job tables are transactionally rebuilt to widen their immutable CHECK constraints.
- Existing job rows retain identity, state, attempts, revisions, leases, references and
  event sequence exactly. New eligibility defaults to original creation time.
- All twelve existing public schemas, evidence fixtures, MCP descriptors, parser
  profiles, visual recipes and export profiles remain byte-compatible.
- Older binaries reject revision 9. Downgrade requires restoring a paired pre-upgrade
  workspace backup; editing tables or migration history is unsupported.

## Consequences

- Stable source changes converge to one durable exact ingestion job across repeated
  scans, concurrent schedulers and restarts.
- Operators gain truthful cancellation and delayed retry without a parallel scheduler.
- Polling performs bounded metadata I/O each cycle and may detect changes only after the
  poll plus stability intervals.
- Tombstones preserve history but do not hide or reclaim evidence; F013 owns retention
  and garbage collection.
- Cancellation latency is bounded by existing parser/checkpoint behavior, not instant
  process preemption.
- Remote POSIX mounts can evade portable detection and remain explicitly unsupported.

## Alternatives considered

- Make OS notification events authoritative: rejected because missed/overflowed events
  cannot establish current truth.
- Add a mandatory watcher package: rejected because reconciliation works portably with
  stdlib and no supply-chain increase.
- Encode cancellation as failure: rejected because it falsifies terminal semantics.
- Add a watcher-specific job state machine: rejected because ownership/fencing would
  have two authorities.
- Move document identity on rename: rejected because it silently changes persisted
  source identity.
- Watch the workspace and exclude known internal filenames: rejected because it risks
  feedback loops and implicit authority.
- Delete evidence on source deletion: rejected by original-authority and retention
  governance; F013 is the bounded deletion feature.
