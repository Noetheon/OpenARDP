# Feature Specification: Local Watcher and Stable Jobs

**Feature Branch**: `codex/f012-local-watcher-and-jobs`

**Created**: 2026-08-01

**Status**: Complete — local convergence passed; publication verification pending

**Input**: Watch explicitly opted-in local roots and schedule one stable, bounded,
deduplicated and cancellable ingestion job per meaningful file change, with crash
recovery, backpressure, retry policy, tombstones, structured redacted events and
bounded rescan recovery.

## Clarifications

### Session 2026-08-01

- Q: Is a native filesystem notification API authoritative? -> A: No. Notifications
  and polling observations are hints. One bounded, deterministic reconciliation scan
  establishes the current watcher facts. The initial cross-platform adapter uses
  polling deliberately; a future native adapter must preserve the same rescan
  contract for overflow and missed-event recovery.
- Q: Which roots may be watched? -> A: Only canonical directories supplied explicitly
  by the operator. Root and workspace may not contain or overlap one another, no
  parent discovery occurs, symlink/junction components and recursive symlink entries
  are rejected, and traversal never crosses the selected root or filesystem device.
- Q: Are network shares supported? -> A: No correctness guarantee is made for network
  or shared filesystems in F012. Recognizable Windows UNC/device paths are rejected;
  traversal is confined to the root device. An undetectable remote POSIX mount remains
  outside the support claim and is reported as such in operational guidance.
- Q: What makes a change stable and meaningful? -> A: A supported regular file must
  retain the same bounded metadata fingerprint (device, file identity, size,
  nanosecond modification time and mode) across complete scans for at least the
  configured stability window. Exact bytes are still hashed by the ingestion service;
  metadata never becomes content identity.
- Q: What are rename and delete semantics? -> A: Every canonical relative path is a
  distinct local source locator. A same-scan rename may be reported as a hint only
  when an unambiguous file identity moves within one root, but it still tombstones the
  old locator and schedules the new locator. Deletion never removes original or
  derived evidence; it creates a durable watcher tombstone. A later reappearance is a
  new observation for that locator.
- Q: What does cancellation guarantee? -> A: Cancellation is a durable, fenced and
  cooperative job transition. Queued jobs become terminal immediately. Running jobs
  receive a persisted request that invalidates the worker revision; workers check it
  at bounded orchestration checkpoints and acknowledge `CANCELLED`. Cancellation does
  not roll back immutable objects or already committed ingestion facts.
- Q: How do retry and crash recovery work? -> A: Retryable failures use deterministic
  capped exponential delay persisted as `available_at`; claims skip jobs before that
  instant. Expired leases are recovered at startup and before each foreground cycle.
  A cancellation-requested expired job becomes cancelled rather than retried.
- Q: How is backpressure handled? -> A: Each root has explicit scan-entry and active-
  queue bounds. A complete scan that exceeds its entry bound publishes no partial
  deletions or schedules; a full queue stops new scheduling and marks the root as
  requiring rescan. A later bounded scan deterministically resumes convergence.
- Q: Does F012 introduce a daemon or MCP write surface? -> A: No. The primary surface
  is a foreground CLI with a testable one-cycle mode. Operators can inspect and cancel
  jobs locally. Service-manager packaging, remote control, retention and garbage
  collection remain outside this feature.
- Q: What content may structured events contain? -> A: Events contain stable
  classifications, opaque root/job/source digests, counts, revisions and timings only.
  They never contain document bodies, raw paths, filenames, parser text, lease tokens
  or exception strings.

## User Scenarios & Testing

### User Story 1 - Schedule One Stable Ingest per Meaningful Change (Priority: P1)

As a local operator, I can opt into a directory and let OpenARDP ingest each supported
regular file only after it is stable, without duplicate work from repeated scans.

**Why this priority**: Stable deduplicated scheduling is the feature's core value and
prevents both incomplete snapshots and redundant parsing.

**Independent Test**: Scan a synthetic local root with a changing text file using an
injected clock; prove no early job is created, one stable job is created, repeated
scans converge, and one foreground worker produces the same exact ingestion result as
the explicit `ingest` command.

**Acceptance Scenarios**:

1. **Given** an explicitly admitted root and a new supported regular file, **When** its
   fingerprint remains unchanged for the stability window, **Then** exactly one job
   bound to that observation is queued and eventually ingested.
2. **Given** repeated identical scans or concurrent schedulers, **When** they observe
   the same stable file fact, **Then** the canonical deduplication key converges to one
   job and one target record.
3. **Given** a file that changes during the window or exact snapshot, **When** a cycle
   runs, **Then** unstable work is not committed as a successful job and the newer
   observation is reconsidered after another complete stability window.
4. **Given** text and configured rich-document support, **When** stable jobs run,
   **Then** they use the same local ingestion services, parser profiles, evidence and
   cache semantics as explicit ingestion rather than a watcher-specific parser path.

---

### User Story 2 - Recover, Retry and Apply Backpressure (Priority: P2)

As an operator, I can stop and restart the foreground watcher and trust it to recover
expired work, delay bounded retries, and converge after queue or scan overflow without
silently losing changes.

**Why this priority**: Watchers encounter crashes, bursts and transient file races in
normal use; correctness depends on durable recovery rather than a happy-path loop.

**Independent Test**: Fault-inject every scan/schedule/claim/ingest/transition
boundary, restart from the same workspace, advance an injected clock and verify exact
lease recovery, retry times, queue bounds, rescan markers and final convergence.

**Acceptance Scenarios**:

1. **Given** a crashed worker with an expired lease, **When** the next cycle starts,
   **Then** the job is requeued or exhausted exactly once according to attempts, unless
   cancellation was requested.
2. **Given** a retryable failure, **When** the job is failed, **Then** its next eligible
   instant follows the documented capped exponential schedule and early claim attempts
   cannot acquire it.
3. **Given** the active-job bound is reached, **When** more stable changes appear,
   **Then** no additional jobs are queued, the root records backpressure/rescan state,
   and a later cycle schedules the omitted changes after capacity returns.
4. **Given** a scan exceeds its file bound or cannot complete, **When** reconciliation
   stops, **Then** partial results cannot tombstone entries or claim completeness and
   the root remains marked for a bounded rescan.

---

### User Story 3 - Cancel and Inspect Work Safely (Priority: P3)

As a local operator, I can inspect body-free job state and durably cancel queued or
running ingestion work without stale workers overriding my decision.

**Why this priority**: Local control must remain reliable during large or unwanted
work, and fencing is required to make cancellation meaningful across processes.

**Independent Test**: Cancel queued and running jobs, replay identical requests,
attempt stale renew/complete/fail operations, expire leases and verify terminal state,
events, token secrecy and already-committed-evidence semantics.

**Acceptance Scenarios**:

1. **Given** a queued job, **When** cancellation is requested, **Then** it transitions
   once to terminal `CANCELLED` and can never be claimed.
2. **Given** a running job, **When** cancellation is requested, **Then** the revision is
   fenced, the request is visible to the owner, and only a valid acknowledgement or
   expired-lease recovery can finalize `CANCELLED`.
3. **Given** a stale owner after cancellation, **When** it renews, succeeds or fails
   using the old revision, **Then** the transition is rejected and no later terminal
   state can replace cancellation.
4. **Given** an already terminal job or repeated identical cancellation, **When** the
   request is replayed, **Then** the result is deterministic and no duplicate event is
   appended.

---

### User Story 4 - Preserve Source, Path and Operational Boundaries (Priority: P4)

As a security-conscious operator, I can watch only explicit local authority and audit
redacted events, tombstones and migrations without allowing document content, links,
paths or remote filesystems to expand capabilities.

**Why this priority**: Recursive filesystem automation can otherwise convert untrusted
content or ambiguous path topology into unintended access and disclosure.

**Independent Test**: Exercise symlink/junction loops, root escapes, device boundaries,
workspace overlap, recognizable network paths, hostile names, deletion/rename,
structured output, concurrent upgrade and rollback fixtures on every CI platform.

**Acceptance Scenarios**:

1. **Given** an omitted root, implicit parent, overlapping workspace, link/junction or
   recognizable unsupported share, **When** watching is requested, **Then** admission
   fails before traversal with a stable body-free classification.
2. **Given** deletion or rename inside a successfully completed scan, **When** watcher
   state reconciles, **Then** old locators become tombstoned without deleting evidence,
   and new locators require their own stable scheduling lifecycle.
3. **Given** a hostile filename or document containing tool-like instructions, **When**
   it is observed or ingested, **Then** it remains untrusted data and never appears in
   an event, log command, policy decision or side-effecting tool invocation.
4. **Given** a revision-8 workspace, **When** F012 initialization upgrades it, **Then**
   one checksummed atomic migration preserves every existing fact and installs complete
   watcher/job state or leaves revision 8 unchanged on failure.

### Edge Cases

- Empty roots, unsupported suffixes, unreadable entries, permission changes, files
  disappearing between directory enumeration and metadata inspection, and a root
  replaced during a scan.
- Case-only rename on case-insensitive filesystems, delete/recreate with reused inode,
  hard links, same file identity at two simultaneous paths, timestamp rollback and
  nanosecond metadata unavailable on a platform.
- A workspace/root overlap through lexical aliases, symlinked ancestors, junctions,
  UNC paths, device paths, mounted descendants and recursive cycles.
- A file exactly at the source byte limit, above it, growing during snapshot, changing
  while parsed, or becoming unsupported before the worker claims it.
- Zero stability window in tests, very long windows, clock rollback, cycle interruption,
  queue saturation, scan overflow and repeated incomplete rescans.
- Concurrent identical scans, concurrent claims, cancellation racing claim/renew/
  complete/fail, cancellation after ingestion commit but before job completion and
  cancellation-requested lease expiry.
- Retry delay overflow, attempt exhaustion, non-retryable parser/input errors, transient
  source races, disk exhaustion after CAS publication and catalog transaction rollback.
- Restart with candidate-but-not-yet-stable entries, queued delayed jobs, active leases,
  rescan-required roots, tombstones and unknown future schema state.

## Requirements

### Functional Requirements

- **FR-001**: F012 MUST admit only operator-supplied canonical absolute directory roots;
  it MUST NOT discover roots, workspaces or parent directories implicitly.
- **FR-002**: Root admission and traversal MUST reject symlink/junction components,
  escapes, workspace overlap and recognizable Windows UNC/device paths, remain on the
  admitted root filesystem device and never follow directory or file links.
- **FR-003**: Network/shared filesystems MUST remain explicitly unsupported in F012;
  documentation MUST distinguish enforceable path rejections from remote POSIX mounts
  that cannot be identified portably.
- **FR-004**: The initial watcher MUST be a provider-neutral service over a narrow scan
  port with one stdlib polling adapter. Observation delivery MUST be treated as a hint;
  a complete bounded rescan is authoritative.
- **FR-005**: One scan MUST enumerate deterministically, admit only supported regular
  files, apply explicit entry/depth/device bounds and produce no partial reconciliation
  when enumeration is incomplete, overflowed or the root identity changes.
- **FR-006**: File stability MUST require an unchanged metadata fingerprint across
  complete scans for at least the configured UTC duration. Metadata MUST NOT serve as
  content or persisted version identity; exact SHA-256 ingestion remains authoritative.
- **FR-007**: One meaningful stable observation MUST derive a domain-separated RFC
  8785/SHA-256 deduplication key from the root/config identity, canonical relative
  locator and full observation fingerprint. Golden vectors MUST freeze every semantic
  input and exclude wall-clock, raw absolute root and execution-owner data.
- **FR-008**: Concurrent/repeated scheduling of one deduplication key MUST converge to
  one immutable generic job and one exact watcher target. Different locators,
  observations, profiles or semantic configuration MUST not collide.
- **FR-009**: Watcher jobs MUST invoke existing text or rich ingestion services with
  their existing exact parser recipe, CAS, catalog and cache semantics. F012 MUST NOT
  add a second parser, source identity or representation lifecycle.
- **FR-010**: Every job target MUST bind one admitted root, relative locator,
  observation fingerprint, parser profile and creation instant; the worker MUST safely
  reconstruct and revalidate the current path inside the root before ingestion.
- **FR-011**: Rename detection MAY emit an unambiguous same-root file-identity hint but
  MUST preserve path-addressed source semantics: old locators are tombstoned and new
  locators enter a distinct stability/job lifecycle. Ambiguous hard-link/reused-
  identity cases MUST degrade to delete/create facts.
- **FR-012**: A complete scan that no longer contains a prior live locator MUST append
  a durable tombstone fact without deleting originals, source versions,
  representations, derivations, context receipts or visual evidence.
- **FR-013**: Reappearance at a tombstoned locator MUST create a fresh observation and
  MAY schedule a new job only after stability; it MUST NOT silently reactivate an old
  queued or failed job.
- **FR-014**: Generic jobs MUST gain a terminal `CANCELLED` state and durable
  cancellation-request metadata while preserving all released job facts through a
  checksummed migration and explicit compatibility documentation.
- **FR-015**: Queued cancellation MUST transition atomically to `CANCELLED`. Running
  cancellation MUST increment the revision, persist the request and reject stale
  lease operations; valid owner acknowledgement or expired-lease recovery completes
  terminal cancellation.
- **FR-016**: Cancellation MUST be cooperative at explicit orchestration checkpoints,
  never imply rollback, and never remove immutable or already committed evidence.
  Repeated cancellation MUST be idempotent and terminal states MUST not be rewritten.
- **FR-017**: Jobs MUST persist an eligibility instant. Claiming MUST ignore queued jobs
  whose `available_at` is later than the supplied UTC instant and preserve deterministic
  ordering among eligible jobs.
- **FR-018**: Retryable watcher failures MUST use a documented deterministic capped
  exponential delay based only on attempt count and trusted configuration. Permanent
  input/policy failures and exhausted attempts MUST become terminal without retry.
- **FR-019**: Startup and every foreground cycle MUST recover all expired leases in one
  deterministic pass. Cancellation-requested expired jobs become `CANCELLED`; other
  jobs requeue or fail according to remaining attempts and retry policy.
- **FR-020**: Per-root active-job and scan-entry bounds MUST be enforced transactionally.
  Backpressure or incomplete/overflowed scans MUST mark the root `rescan_required`,
  avoid partial tombstones and permit later complete bounded convergence.
- **FR-021**: Crash/fault boundaries around scan reconciliation, job/target creation,
  claim, ingestion and terminal transitions MUST preserve either the prior complete
  state or one complete new state. CAS-first unreachable residue remains for F013.
- **FR-022**: Watch roots, observations, tombstones, job targets, rescan state and
  body-free watcher events MUST be durable in SQLite and included in catalog
  structural validation and transactional migration tests.
- **FR-023**: Structured watcher/job events and default logs MUST contain only stable
  classifications, opaque digests/identifiers, counts, revisions and timings; raw
  roots, relative paths, filenames, bodies, lease tokens and exception text MUST be
  excluded.
- **FR-024**: A foreground-first CLI MUST support one explicit root, continuous polling
  and a deterministic `--once` cycle, plus body-free job inspection and cancellation.
  It MUST use the existing JSON/human envelope and stable exit/error classifications.
- **FR-025**: Continuous mode MUST stop cleanly on operator interruption, use an
  injectable clock/sleeper for tests and never start a daemon, service, network listener
  or MCP write tool implicitly.
- **FR-026**: Document content and filenames MUST remain untrusted data and MUST NOT
  alter roots, profiles, retry policy, commands, network behavior or tool authority.
- **FR-027**: Unit and integration tests MUST use synthetic local fixtures, injected
  time and no network, with concurrency/fault/security coverage on Linux, macOS and
  Windows.
- **FR-028**: F012 MUST add one append-only revision-9 migration, preserve migration
  1-8 checksums and all existing public schema bytes, and fail atomically on upgrade,
  structural drift, incompatibility or future versions.
- **FR-029**: F012 MUST NOT implement F013 retention/GC/quarantine, F014 export,
  service-manager installation, cloud synchronization, native notification providers,
  universal network-mount detection or automatic OCR/caption/model acquisition.
- **FR-030**: Operations, security, data-model, CLI, recovery, backup/rollback and
  compatibility documentation MUST describe actual delivered behavior, unsupported
  boundaries and exact validation commands without performance or zero-loss claims
  lacking reproducible evidence.

### Key Entities

- **WatchRoot**: Explicit canonical root authority, immutable semantic configuration,
  opaque identity, root-device evidence, scan generation and rescan state.
- **WatchObservation**: Current path-scoped metadata fingerprint, stability history,
  lifecycle and tombstone state without document content.
- **WatchJobTarget**: Immutable binding from one generic job to an admitted relative
  locator, exact stable observation and parser profile.
- **WatchEvent**: Append-only body/path-free reconciliation, overflow, scheduling,
  tombstone and rename-hint evidence.
- **Job**: Existing fenced durable work projection extended with eligibility,
  cancellation request and terminal cancellation.
- **WatchCycleResult**: Body-free counts and opaque identifiers for one recovery,
  scan, reconciliation and bounded worker cycle.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Across 100 repeated and 20 concurrent identical scan/schedule attempts,
  one stable observation produces exactly one job and one target record.
- **SC-002**: Controlled scans immediately before and at the configured stability
  boundary demonstrate zero early jobs and one eligible job at the boundary.
- **SC-003**: A 1,001-entry synthetic root with a 1,000-entry bound produces zero
  partial tombstones/schedules and one rescan marker; after reducing the fixture below
  the bound, the next complete scan converges without omitted files.
- **SC-004**: Injected retries at attempts 1 through exhaustion match the documented
  eligibility instants exactly, and 100 early claims return no lease.
- **SC-005**: Queued/running cancellation races across 20 clients converge to one
  terminal state; every stale renew/complete/fail attempt is rejected and no raw token
  appears in models, events, logs or CLI output.
- **SC-006**: Restart tests from every durable lifecycle state recover all expired work,
  candidates, backpressure and tombstones without duplicate successful jobs or lost
  complete-scan changes.
- **SC-007**: Rename/delete/reappearance fixtures on supported CI platforms preserve
  all prior evidence, tombstone old locators and schedule new/reappeared locators only
  after their own stability window.
- **SC-008**: Security tests reject all synthetic link/junction, escape, workspace-
  overlap and recognizable network-path cases before ingestion; redaction tests find
  zero raw path, filename, body, token or injected instruction in structured events.
- **SC-009**: Revision-8-to-9 upgrade, concurrent upgrade and every injected migration
  failure preserve all prior rows/checksums and expose either complete revision 8 or
  complete revision 9, never an intermediate schema.
- **SC-010**: Full network-disabled repository gates pass on Linux, macOS and Windows:
  Ruff check/format, strict mypy, pytest with required coverage, build, schema freeze,
  evidence conformance and repository validation.
