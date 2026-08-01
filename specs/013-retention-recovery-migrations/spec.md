# Feature Specification: Retention, Recovery and Migrations

**Feature Branch**: `codex/f013-retention-gc-quarantine`

**Created**: 2026-08-01

**Status**: Draft

**Input**: Authoritative Feature 013 prompt
`spec-kit/feature-prompts/013-retention-recovery-migrations.md` (SHA-256
`d087446406c9e2b6451392c5999ae7ac4e1807353bf2ca1a7d749cffd0debdec`) plus the
request to complete the remaining project sequentially with best-practice,
long-lived and sustainable implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explain Workspace Retention (Priority: P1)

As a local operator, I can inspect a bounded, deterministic inventory that explains
which stored bytes are protected, which are inconsistent, which are disposable index
state and which verified unreferenced objects are possible reclamation candidates,
without changing the workspace.

**Why this priority**: No safe retention, backup or reclamation action is possible until
the complete live-root boundary and every candidate reason are inspectable.

**Independent Test**: Create a synthetic workspace containing every delivered record
family, one complete unreferenced object and representative malformed/corrupt entries;
run the inventory repeatedly and prove identical classifications, totals and reasons
with no byte or catalog change.

**Acceptance Scenarios**:

1. **Given** source versions, text/rich representations, evidence, context,
   reconciliation, derivation, visual and watcher/job history, **When** the operator
   requests an inventory, **Then** every referenced object is protected with at least
   one reason that traces to an authoritative catalog root.
2. **Given** a complete verified object with no catalog reference, **When** the operator
   requests a dry run, **Then** it is reported as a candidate with exact identity,
   length, observation time and the policy reason, but is not moved or deleted.
3. **Given** any missing, corrupt, unsafe, malformed or staging entry, **When** the
   inventory runs, **Then** it is reported as an inconsistency and never promoted to a
   reclamation candidate.
4. **Given** an object protected by an operator hold, **When** a dry run is repeated,
   **Then** the object remains protected even if it has no other live reference.

---

### User Story 2 - Quarantine and Restore Candidates (Priority: P1)

As a local operator, I can explicitly quarantine only candidates from an unchanged,
verified dry-run plan and restore them during a grace period, while crashes and stale
plans leave either the prior state or one complete auditable state.

**Why this priority**: A reversible separation step is the core safety control between
advisory reachability and irreversible reclamation.

**Independent Test**: Produce one eligible plan, inject a failure at every catalog and
filesystem transition, restart after each failure, and show that an object is either
active or recoverably quarantined, never silently lost or multiply owned.

**Acceptance Scenarios**:

1. **Given** an unchanged dry-run plan containing eligible candidates, **When** the
   operator explicitly quarantines that plan, **Then** each candidate becomes
   unavailable from the active object tree, remains verifiable in quarantine and gains
   an append-only reasoned audit record plus a not-before reclamation time.
2. **Given** a stale plan, a newly added reference, a hold, an inconsistency or a changed
   object, **When** quarantine is requested, **Then** the complete operation fails
   closed before that object is moved.
3. **Given** a quarantined object within its grace period, **When** restore is requested,
   **Then** the exact object is atomically returned to its canonical active location and
   its identity and length are reverified.
4. **Given** a crash during quarantine or restore, **When** the workspace is reopened
   and recovery is run, **Then** deterministic reconciliation completes or rolls back
   the interrupted operation without guessing from filenames or deleting evidence.

---

### User Story 3 - Commit Explicit Reclamation (Priority: P2)

As a local operator, I can irreversibly remove a quarantined object only by naming an
unchanged quarantine batch after its grace period, with a final reachability/hold check
and an explicit acknowledgement that the action cannot be undone.

**Why this priority**: Long-running workspaces need bounded physical reclamation, but it
must never occur automatically or bypass the reversible phase.

**Independent Test**: Advance a synthetic clock across the grace boundary and prove
that early, stale, held or newly referenced commits delete nothing, while an eligible
explicit commit removes exactly the named verified quarantine entries and records the
outcome.

**Acceptance Scenarios**:

1. **Given** a quarantine batch whose grace period has not expired, **When** commit is
   requested, **Then** no entry is deleted.
2. **Given** an expired unchanged batch and explicit irreversible-action
   acknowledgement, **When** commit is requested, **Then** exactly its still-eligible
   entries are removed and a durable body-free audit result is recorded.
3. **Given** an expired batch whose object is now held or referenced, **When** commit is
   requested, **Then** that object is restored or retained, not deleted, and the
   conflict is explained.
4. **Given** no operator command, **When** any normal open, ingest, watch, query,
   compilation, migration or recovery path runs, **Then** no irreversible reclamation
   occurs.

---

### User Story 4 - Back Up, Restore and Migrate Safely (Priority: P1)

As a local operator, I can create a complete verified paired backup, restore it only to
a fresh disjoint location and explicitly migrate an older supported workspace with a
pre-upgrade backup, while unsupported newer workspaces fail without mutation.

**Why this priority**: Retention without practiced recovery increases risk; every
forward-only catalog change needs an evidence-backed rollback path.

**Independent Test**: Back up a populated prior-revision workspace, migrate it, perform
new writes, restore the backup to a fresh location and prove the restored workspace is
the exact earlier state and remains fully usable.

**Acceptance Scenarios**:

1. **Given** a current healthy workspace, **When** backup is requested to a fresh
   disjoint local destination, **Then** one self-contained snapshot is published only
   after its catalog, objects, marker and manifest all pass integrity verification.
2. **Given** a valid complete backup, **When** restore targets a fresh disjoint local
   directory, **Then** the restored workspace opens at the recorded revision and every
   manifest entry, catalog reference and object verifies before publication.
3. **Given** an older supported workspace, **When** explicit migration is requested,
   **Then** a verified pre-upgrade backup is created first and the entire pending
   migration chain becomes visible atomically or remains at the prior revision.
4. **Given** a newer, gapped, checksum-drifted or malformed workspace/backup, **When**
   open, restore or migrate is attempted, **Then** it fails with no mutation to source,
   destination or backup.
5. **Given** state A backed up, migrated/changed state B and a restore of A to a fresh
   location, **When** both workspaces are verified, **Then** restored A contains the
   exact recorded A facts and objects without silently incorporating B.

---

### User Story 5 - Diagnose Space and Rebuild Disposable Indexes (Priority: P2)

As a local operator, I can see deterministic disk-usage totals and reserve status, and
I can rebuild disposable search indexes from verified authoritative evidence without
changing evidence identities.

**Why this priority**: Sustainable local operation requires actionable storage facts
and a safe response to index drift or low space that does not delete evidence.

**Independent Test**: Compare reported byte totals to a synthetic workspace, simulate
space above/at/below the reserve, corrupt or remove index rows, and prove bounded
fail-closed writes plus an exact rebuild with unchanged evidence objects.

**Acceptance Scenarios**:

1. **Given** a workspace with active objects, quarantine, staging residue, catalog and
   indexes, **When** diagnostics are requested, **Then** category counts/bytes, free
   space, configured reserve and warning state are reported without paths or bodies.
2. **Given** insufficient free space for a maintenance operation plus reserve, **When**
   that operation starts, **Then** it fails before publication and performs no hidden
   reclamation.
3. **Given** a missing, orphaned or drifted disposable lexical index, **When** rebuild
   is explicitly requested, **Then** a complete replacement is derived from verified
   current authoritative evidence or the prior index remains visible.
4. **Given** a successful rebuild, **When** evidence and search results are compared,
   **Then** all evidence identities are unchanged and result ordering/content matches
   the authoritative prepared corpus.

### Edge Cases

- The candidate set changes between dry run, quarantine and commit.
- A complete unreferenced object becomes referenced concurrently.
- The same object is named by multiple reasons, plans, holds or historical batches.
- An object exists in active and quarantine locations, in neither location, or changes
  identity during a move.
- A quarantine batch is empty, partially restored or already committed.
- Wall-clock time moves backwards or a naive/non-UTC time is supplied.
- The operator repeats the same command or two processes issue it concurrently.
- Backup destination overlaps the workspace, is a link/junction, is non-empty, is on a
  recognizable remote/device path, or changes identity during publication.
- Backup is interrupted before/after catalog snapshot, object copy, manifest creation,
  verification or final publication.
- Restore encounters duplicate, missing, extra, corrupt, hard-linked, linked or unsafe
  entries, or an unsupported manifest version.
- Migration fails before/after each schema statement or process termination leaves a
  journal/staging residue.
- Free-space readings are unavailable, change during streaming or fall below reserve.
- Index rebuild is cancelled or runs concurrently with ingestion/head changes.
- Filenames, source locators, query text, document bodies, lease tokens and provider
  exception strings appear in diagnostic or audit output.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST inventory reachability for every catalog object reference
  delivered through Feature 012, including source/version, job, text/rich
  representation, evidence, context, reconciliation, derivation and visual records.
- **FR-002**: The inventory MUST classify active verified objects, quarantined objects,
  verified unreferenced candidates, disposable index state and inconsistencies as
  disjoint categories with deterministic counts and byte totals.
- **FR-003**: Every protected object and candidate MUST carry closed reason codes and
  opaque reference identifiers sufficient to explain the decision without exposing
  paths, filenames or content.
- **FR-004**: Missing, corrupt, malformed, unsafe, linked, hard-linked and staging
  entries MUST be inconsistencies and MUST NOT be reclamation candidates.
- **FR-005**: Inventory and dry-run operations MUST be read-only and byte-for-byte
  non-mutating, including on failure and against unsupported newer workspaces.
- **FR-006**: Inventory enumeration MUST be bounded by explicit entry and byte limits;
  limit exhaustion MUST expose no partial authoritative plan.
- **FR-007**: The system MUST support operator holds over exact object identities with a
  reason, creation time and optional expiry; active holds MUST override every
  reclamation rule.
- **FR-008**: The v0.1 retention policy MUST conservatively protect every
  catalog-referenced object regardless of age or derived status. It MUST protect an
  unreferenced object for at least 24 hours after its safe store modification time and
  MAY only select complete verified objects that remain unreferenced; operators MAY
  extend but not shorten this minimum.
- **FR-009**: A dry run MUST return an immutable, content-identified plan over the exact
  policy, catalog revision/snapshot, object inventory, holds and candidate set without
  persisting it in the workspace; quarantine MUST require the operator to supply that
  exact plan record.
- **FR-010**: Repeating a dry run against unchanged inputs MUST produce the same semantic
  plan identity independent of wall-clock reporting metadata.
- **FR-011**: Quarantine MUST require an explicitly named plan and MUST revalidate every
  candidate, reference, hold, limit and source location before mutation.
- **FR-012**: Quarantine MUST move only complete regular verified candidate objects to a
  managed same-workspace quarantine tree without following links or crossing device
  boundaries.
- **FR-013**: One quarantine request MUST publish a complete durable batch, entry set,
  audit events and active/quarantine ownership state, or remain recoverably at the
  prior state after interruption.
- **FR-014**: Each quarantined entry MUST retain exact object identity, byte length,
  plan/policy identity, reason, quarantine time, not-before time and current lifecycle.
- **FR-015**: Restore MUST reverify the quarantined bytes and canonical destination,
  refuse conflicting active bytes and atomically return the exact object before
  recording completion.
- **FR-016**: Interrupted quarantine, restore and commit operations MUST be explicitly
  recoverable and idempotent after process restart; filesystem presence alone MUST NOT
  authorize deletion.
- **FR-017**: The default quarantine grace period MUST be seven days. A trusted operator
  MAY extend it per plan, but v0.1 MUST NOT permit an irreversible commit before at
  least 24 hours have elapsed.
- **FR-018**: Irreversible reclamation MUST require a named quarantine batch, expired
  grace period, final unchanged reachability/hold verification and an explicit
  acknowledgement distinct from the command name.
- **FR-019**: Commit MUST delete exactly the still-eligible entries in the named batch,
  record each outcome durably and leave conflicted/newly protected entries recoverable.
- **FR-020**: No timer, startup, migration, low-space path, watcher, ingestion, query,
  MCP request or generic recovery operation MAY invoke irreversible reclamation.
- **FR-021**: The system MUST make no secure-erasure claim; committed removal means only
  removal from the managed logical store using supported local filesystem operations.
- **FR-022**: Backup MUST capture one consistent current catalog snapshot, exact
  workspace marker, every active reachable object, every recoverable quarantined
  object, retention/hold/quarantine metadata and a deterministic integrity manifest.
- **FR-023**: Backup publication MUST use a fresh disjoint local destination and MUST
  remain invisible as complete until all manifest entries, lengths and hashes verify.
- **FR-024**: A backup MUST exclude disposable indexes and incomplete staging residue
  while recording enough trusted metadata to rebuild indexes and report excluded
  inconsistencies after restore.
- **FR-025**: Restore MUST accept only a supported manifest, validate all paths before
  reading bytes, verify the complete inventory before publication and target only a
  fresh disjoint local directory.
- **FR-026**: A restored workspace MUST reproduce the backed-up catalog revision,
  authoritative object set, holds and recoverable quarantine state exactly; index
  state MUST be rebuilt separately.
- **FR-027**: Migration of an existing supported workspace MUST be an explicit operator
  action and MUST require a successfully verified paired pre-upgrade backup.
- **FR-028**: The complete pending catalog migration chain and its history records MUST
  commit transactionally; restart after any failure MUST expose the exact prior or
  complete new revision.
- **FR-029**: Normal workspace open MUST never initialize, repair or migrate, and an
  unsupported newer, gapped or checksum-drifted history MUST fail without any byte or
  timestamp mutation.
- **FR-030**: New workspace initialization MUST remain explicit and MAY create the
  current revision directly without a pre-upgrade backup.
- **FR-031**: Diagnostics MUST report bounded body-free counts and bytes for catalog,
  active CAS, quarantine, staging anomalies and disposable indexes plus current free
  space, configured reserve and a closed health state.
- **FR-032**: Maintenance writes MUST reserve configurable free space and fail closed
  before publication when the known required bytes plus reserve are unavailable;
  mid-stream space errors MUST clean only owned staging state.
- **FR-033**: Low-space behavior MUST warn and reject unsafe writes; it MUST NOT trigger
  automatic deletion, quarantine, index removal or retention-policy changes.
- **FR-034**: The system MUST rebuild the complete disposable lexical index from
  verified authoritative prepared evidence using an all-or-prior visibility boundary.
- **FR-035**: Rebuild MUST remove orphaned/drifted accelerator state, preserve all
  evidence identities and fail closed on missing/corrupt authoritative evidence.
- **FR-036**: Backup, restore, migration, retention and index rebuild operations MUST
  reject concurrent conflicting maintenance and converge safely under repeated or
  duplicate requests.
- **FR-037**: All maintenance commands MUST support bounded human and structured output
  with stable error categories, opaque identifiers, counts, bytes and UTC times only.
- **FR-038**: Maintenance logs and audit records MUST omit document bodies, extracted
  text, absolute paths, filenames, query/task text, raw SQL, owner/lease tokens and
  untrusted exception strings by default.
- **FR-039**: All timestamps MUST be UTC/RFC 3339, persisted identities MUST use the
  project's canonical SHA-256 rules and durable metadata writes MUST be atomic.
- **FR-040**: The feature MUST add no network call, telemetry, cloud dependency,
  background deletion service, public-schema change, provider-profile change,
  export-format decision or MCP mutation.
- **FR-041**: Unit tests MUST remain network-free and use only synthetic or
  redistributable fixtures across Linux, macOS and Windows.

### Non-Goals and Compatibility Impact

- **Non-goal**: Automatic, scheduled, pressure-triggered or policy-triggered irreversible
  garbage collection.
- **Non-goal**: Secure erasure, filesystem forensics guarantees, physical-media
  sanitization or recovery guarantees after operator commit.
- **Non-goal**: Policy-driven deletion of catalog-referenced historical evidence in
  v0.1; all delivered catalog references remain conservative roots.
- **Non-goal**: In-place restore/downgrade, point-in-time log shipping, remote backup,
  shared/network-filesystem correctness or multi-workspace orchestration.
- **Non-goal**: A portable interchange/export archive; backup is an implementation
  recovery artifact and Feature 014 owns interchange decisions.
- **Non-goal**: A daemon, scheduler, UI, production Graph connector, new parser,
  embedding index or stronger sandbox claim.
- **Compatibility impact**: Additive internal application/CLI and workspace migration
  from revision 9 to revision 10. Existing twelve public schemas, identity vectors,
  provider/renderer/watcher profiles, MCP descriptors, dependency set and export-profile
  state remain unchanged. Older applications reject revision 10; supported rollback is
  restore of the paired revision-9 backup to a fresh location.

### Key Entities

- **Retention Policy**: Trusted bounded policy containing observation age, grace,
  reserve and inventory limits; its semantic identity excludes reporting time.
- **Retention Hold**: Operator protection for one exact object, with reason and optional
  expiry.
- **Reachability Explanation**: One protected/candidate/inconsistent classification with
  closed reasons and opaque references.
- **Reclamation Plan**: Immutable exact dry-run snapshot of policy, catalog revision,
  holds, inventory and ordered candidates.
- **Quarantine Batch and Entry**: Durable reversible lifecycle for the exact objects
  admitted by one plan, including recovery state and not-before time.
- **Maintenance Event**: Append-only body-free audit fact for plan, hold, quarantine,
  restore, commit, backup, migration and rebuild transitions.
- **Backup Manifest**: Versioned complete inventory of the catalog snapshot, marker,
  authoritative objects and retention/quarantine facts, plus exclusions and hashes.
- **Restore Report**: Deterministic proof that a fresh destination matches one backup
  manifest and opens at the recorded revision.
- **Storage Diagnostic**: Point-in-time bounded category counts/bytes, free space,
  reserve and closed health state.
- **Index Rebuild Report**: Exact authoritative scope and before/after accelerator
  coverage without evidence bodies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A synthetic corpus containing every delivered object-reference family has
  zero protected objects classified as candidates across 100 repeated and 20 concurrent
  inventories.
- **SC-002**: Twenty unchanged dry runs produce one semantic plan identity and exactly
  ordered candidate/reason output; dry-run changes zero workspace bytes and timestamps.
- **SC-003**: Entry-limit overflow at exactly limit+1 exposes zero partial candidates;
  reducing to the limit produces the complete expected inventory on the next run.
- **SC-004**: Failures injected before and after every quarantine, restore and commit
  persistence/filesystem transition recover after restart to the exact prior or complete
  state with zero lost, duplicated or ambiguous objects.
- **SC-005**: Twenty concurrent quarantine/restore/commit requests for the same plan or
  batch converge to one valid lifecycle and one terminal outcome per object.
- **SC-006**: Commit at 23:59:59 after quarantine removes zero objects; commit at the
  configured 24-hour minimum boundary removes exactly eligible named objects, and a
  newly referenced or held object is never removed.
- **SC-007**: A populated current workspace backs up and restores to a fresh path with
  100% manifest/hash/length agreement; all authoritative read operations and a rebuilt
  search index return the same deterministic results.
- **SC-008**: The A→B→A drill reproduces every recorded A catalog fact/object and excludes
  all B-only facts without editing migration history or original backup bytes.
- **SC-009**: Failure before/after every revision-10 migration statement exposes exact
  revision 9 or exact revision 10; 20 concurrent migrators converge to one checksummed
  revision-10 history row.
- **SC-010**: Opening a synthetically newer workspace through every read/write entrypoint
  changes zero bytes and nanosecond timestamps.
- **SC-011**: Space diagnostics match independently measured synthetic category totals
  exactly; operations at reserve-1 byte publish nothing, while reserve-exact succeeds
  when all other preconditions hold.
- **SC-012**: Rebuilding a missing, orphaned and drifted lexical index yields complete
  authoritative coverage and byte-equivalent ordered search results while changing zero
  evidence/object identities.
- **SC-013**: Structured-output and log privacy scans over hostile names/content find zero
  bodies, absolute paths, filenames, queries, tokens or provider error strings.
- **SC-014**: The complete locked offline repository gate passes on Linux, macOS and
  Windows, including formatting, strict typing, all tests, coverage threshold,
  deterministic validation, distribution build and tracked-file drift checks.

## Assumptions

- v0.1 remains a local, single-user, single-workspace modular monolith on a supported
  local filesystem; remote/shared filesystems are unsupported.
- The operator can provide a fresh disjoint local destination with sufficient capacity
  for each backup and restore.
- A 24-hour minimum candidate age plus a seven-day default quarantine grace with a hard
  24-hour commit minimum is the conservative project default; operators may only extend
  these intervals in this feature.
- Every catalog reference delivered through F012 remains a live retention root. This
  intentionally favors false retention over false reclamation; later policy-driven
  retirement of historical evidence requires a separate feature/ADR.
- Backup is a recovery artifact for this implementation, not a standardized export or
  long-term archival format.
- Existing exact source, CAS, migration, index and application service boundaries are
  reused; storage replacement, identity changes and cloud services remain out of scope.
