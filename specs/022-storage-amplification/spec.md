# Feature Specification: Storage Amplification Reduction

**Feature Branch**: `codex/f022-storage-amplification`

**Created**: 2026-08-02

**Status**: Clarified; planning pending

**Input**: Systematically reduce F020's approximately 37.9-times text-workspace amplification without weakening
original evidence, provenance, replay, local-first operation or historical benchmark truth.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prepare New Text Workspaces Efficiently (Priority: P1)

As a local operator, I can ingest and reuse large text documents without the workspace consuming dozens of times the
source size, while exact evidence navigation, search and replay continue to behave identically.

**Why this priority**: F020 measured 73,874,827 workspace bytes for a 1,949,999-byte reference source and 739,947,189
workspace bytes for a 19,499,999-byte scale source. That cost materially weakens the local-first value proposition.

**Independent Test**: Prepare fresh 10,000- and 100,000-block frozen corpora, exercise the same edit/revert, search,
context and replay workload as F020, then compare exact outcomes plus logical and allocated workspace bytes with the
committed baseline.

**Acceptance Scenarios**:

1. **Given** a fresh workspace and the frozen reference corpus, **When** the complete text workload runs, **Then** the
   logical amplification is at most 15 times source bytes and every F020 correctness judgment remains true.
2. **Given** the frozen scale corpus, **When** the same workload runs, **Then** the target is met without omitting
   historical versions, search coverage or persisted evidence from the measurement.
3. **Given** a derived block whose compact form would not save space, **When** it is published, **Then** the system may
   retain its exact ordinary form without changing its identity or behavior.

---

### User Story 2 - Read and Verify Exact Evidence Transparently (Priority: P1)

As an evidence consumer, I retrieve the same canonical block bytes and identifiers regardless of their internal physical
encoding, and corruption never turns into silently altered content.

**Why this priority**: Storage reduction is unacceptable if it changes the bytes addressed by an existing identifier or
turns the storage representation into an unverified authority.

**Independent Test**: Persist identical canonical blocks through ordinary and compact physical forms, retrieve them in
bounded chunks, verify their SHA-256 identities and inject header, payload, truncation, length and dictionary faults.

**Acceptance Scenarios**:

1. **Given** an ordinary or compactly stored derived block, **When** it is read or verified, **Then** the exact canonical
   logical bytes, SHA-256 identity and byte length are identical.
2. **Given** malformed, truncated, over-expanding or digest-inconsistent stored data, **When** it is inspected, **Then**
   the operation fails closed with a sanitized integrity classification and returns no partial body.
3. **Given** an original source or provider-native artifact, **When** storage optimization runs, **Then** its existing
   exact physical bytes are not rewritten or removed.

---

### User Story 3 - Upgrade Existing Workspaces Safely (Priority: P1)

As an existing operator, I can explicitly migrate and optimize a prior workspace after a verified backup, resume safely
after interruption and roll back without losing any source version, block, relation, index-rebuild path or audit fact.

**Why this priority**: Improving only fresh workspaces would strand current users, while an automatic rewrite during
ordinary open would violate the project's explicit migration and recovery rules.

**Independent Test**: Build a revision-10 workspace containing current/history, search, contexts, relations and
maintenance facts; migrate it with faults before and after each durable boundary; reopen, resume, validate, rebuild search
and restore the pre-migration backup.

**Acceptance Scenarios**:

1. **Given** a compatible prior workspace and a fresh backup destination, **When** migration succeeds, **Then** every
   authoritative record and logical object remains exact and the workspace reaches one supported current revision.
2. **Given** interruption during optimization, **When** the operator retries, **Then** ordinary and compact duplicates
   converge safely without changing logical identity or requiring source re-parsing.
3. **Given** an older workspace, **When** it is merely opened, **Then** no catalog, object or source byte is rewritten and
   an explicit migration requirement is returned.
4. **Given** the verified backup, **When** it is restored, **Then** the original revision and exact pre-migration evidence
   are recovered independently of the optimized workspace.

---

### User Story 4 - Preserve Search, Maintenance and Portability (Priority: P1)

As an operator, I can still search, reindex, audit reachability, quarantine eligible objects, back up and restore the
workspace after compaction, with indexes remaining disposable and evidence verification remaining authoritative.

**Why this priority**: A lower byte count is not useful if lifecycle operations no longer understand the storage layout
or if search metadata becomes a second source of truth.

**Independent Test**: Run exact lexical queries, deliberate index drift/rebuild, full integrity, inventory, backup,
restore and bounded quarantine scenarios against fresh and migrated optimized workspaces on all supported platforms.

**Acceptance Scenarios**:

1. **Given** normalized persisted projections, **When** search or context selection returns a hit, **Then** body, trust,
   scope and provenance are still verified against authoritative catalog and content-addressed facts.
2. **Given** disposable search data is removed, **When** the explicit rebuild runs, **Then** coverage and deterministic
   results are restored without changing evidence objects.
3. **Given** compact derived objects, **When** inventory, backup and restore run, **Then** logical identities and physical
   encodings are completely accounted for with no double counting.

---

### User Story 5 - Reproduce the Storage Claim (Priority: P2)

As a maintainer, I can independently reproduce a before/after storage report that distinguishes useful logical content,
physical allocation, metadata, disposable indexes and filesystem overhead, so the reduction claim cannot hide costs.

**Why this priority**: F020 counted logical file lengths only. Per-block files consume materially more allocated space,
so a sustainable result must expose both views and retain unfavorable evidence.

**Independent Test**: Run a versioned offline benchmark from clean inputs, independently validate all inventories,
identities and arithmetic, and regenerate the report solely from retained body-free machine evidence.

**Acceptance Scenarios**:

1. **Given** the frozen F020 profiles, **When** the benchmark runs, **Then** it reports logical bytes, allocated bytes,
   regular-file count and closed category breakdowns before and after optimization.
2. **Given** a target miss or regression, **When** evidence is published, **Then** the miss remains visible and the
   historical 37.9-times observation is not rewritten.
3. **Given** retained machine evidence, **When** the independent validator runs, **Then** every ratio, delta, inventory
   total, identity and decision is recomputed without trusting the report text.

### Edge Cases

- Empty and tiny canonical blocks for which an encoding envelope costs more than it saves.
- Compact payloads with valid framing but wrong logical length, checksum, dictionary version or trailing bytes.
- The same logical object exists in both ordinary and compact form after a crash or concurrent publication.
- Migration stops after backup, after schema publication, after compact publication or before ordinary derived cleanup.
- A workspace has READY representations whose disposable search coverage was intentionally removed by backup.
- A compact block is reachable from multiple historical facts while another compact block is unreferenced.
- The filesystem reports sparse/compressed allocation semantics or lacks portable allocated-byte accounting.
- Disk space becomes insufficient between capacity admission and durable publication.
- Concurrent ingestion, verification, migration or maintenance observes an optimization boundary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST retain the committed F020 reference and scale inputs, source sizes, workspace sizes and
  `CONDITIONALLY_WORTHWHILE` decision as immutable historical evidence.
- **FR-002**: Fresh text ingestion MUST reduce complete-workload logical workspace amplification to at most 15.0 times
  source bytes for both frozen 10,000- and 100,000-block profiles.
- **FR-003**: The optimized reference workload MUST use no more than 55.0 times source bytes in filesystem-allocated
  regular-file space on the declared binding environment; unsupported allocation reporting MUST be explicit.
- **FR-004**: The measured workspace MUST retain current and historical source versions, every required authoritative
  evidence object, exact lexical coverage and the same context/replay artifacts as the frozen workload.
- **FR-005**: Persisted content identifiers MUST remain SHA-256 over exact logical bytes; source, representation, block,
  manifest, context and relation identity algorithms MUST NOT change.
- **FR-006**: Authoritative source and provider-native objects MUST remain byte-for-byte ordinary immutable objects and
  MUST NOT be transcoded or deleted by storage optimization.
- **FR-007**: A compact physical form MAY be used only for reproducible derived canonical block objects and MUST be
  lossless, deterministic, versioned, bounded and transparently reversible.
- **FR-008**: Compact publication MUST fall back to the ordinary immutable form whenever compaction does not produce a
  smaller complete stored representation.
- **FR-009**: Reads and verification MUST return or validate exact logical bytes and MUST reject malformed framing,
  unknown encoding versions, truncation, trailing data, excessive expansion, length mismatch and digest mismatch.
- **FR-010**: Concurrent publication of identical logical bytes MUST converge on one valid logical object; an interrupted
  optimization that leaves both physical forms MUST be detectable and safely resumable.
- **FR-011**: The catalog MUST remove repeated block/search scope metadata and redundant persisted indexes without
  storing a second authoritative document body or weakening deterministic lookup and ordering.
- **FR-012**: Search data MUST remain disposable, explicitly rebuildable and incapable of satisfying a returned-body,
  trust, scope or provenance check without authoritative verification.
- **FR-013**: Existing compatible workspaces MUST advance through one ordered checksummed workspace migration with a
  verified pre-migration backup and documented rollback path.
- **FR-014**: Ordinary workspace open MUST NOT migrate, compact, rebuild or otherwise mutate a prior workspace.
- **FR-015**: Optimization of existing derived blocks MUST be explicit, idempotent and restartable without parser
  invocation, source access or identity change.
- **FR-016**: Migration and optimization MUST fail closed on an unsafe layout, active maintenance operation, corrupt live
  object, insufficient capacity, unsupported revision or backup inconsistency.
- **FR-017**: Reachability, full-integrity verification, diagnostics, quarantine, backup and restore MUST account for every
  supported physical form and MUST neither omit nor double-count one logical object.
- **FR-018**: Backup manifests MUST bind the exact physical files copied and the logical object inventory; restore MUST
  verify both before publishing a fresh workspace.
- **FR-019**: All failures, logs, benchmark artifacts and interface results MUST remain body-free and path-safe by default,
  with no absolute paths, source text, credentials or raw exceptions.
- **FR-020**: The feature MUST introduce no network access, cloud service, mandatory model, telemetry or new runtime
  dependency.
- **FR-021**: A versioned offline benchmark MUST measure fresh and migrated reference workspaces plus a fresh scale
  workspace using exact logical bytes, allocated bytes, file counts and closed category totals.
- **FR-022**: The benchmark MUST retain complete raw body-free observations, immutable input identities, environment
  classification, before/after values, failures, limitations and a deterministic decision.
- **FR-023**: Independent validation MUST recompute inventories, arithmetic, thresholds, report projection and drift from
  committed evidence rather than trusting producer summaries.
- **FR-024**: Storage reduction MUST NOT regress exact search, context coverage, replay equality, edit/revert behavior,
  parser avoidance on reuse or freshness semantics from F020/F021.
- **FR-025**: All repository quality, migration, recovery, privacy, deterministic-drift and Linux/macOS/Windows gates MUST
  pass before merge.

### Non-Goals and Compatibility Impact

- **Non-goal**: Provision PDF models, add the redistributable real-world corpus or evaluate semantic questions; these
  remain F023–F025.
- **Non-goal**: Delete historical versions, weaken evidence retention, change public evidence schemas or make indexes
  authoritative to obtain a favorable ratio.
- **Non-goal**: Claim that logical file length equals consumed disk space on every filesystem.
- **Compatibility impact**: The internal workspace/catalog revision advances and the derived-block physical layout gains
  one versioned optional form. Public schema versions, application version, export profile and content identity algorithms
  remain unchanged. Older binaries continue to reject the newer workspace as unsupported.

### Key Entities

- **Logical Object**: Exact immutable bytes, SHA-256 identity and logical byte length independent of physical form.
- **Physical Object Form**: Ordinary or compact storage of one logical object with explicit version and stored length.
- **Compact Block Projection**: One body-free persisted block/search record with normalized scope and rebuildable search
  metadata.
- **Optimization Run**: Restartable operator-authorized conversion of eligible derived physical objects.
- **Storage Observation**: Body-free logical, allocated, count and category facts for one exact workload state.
- **Storage Decision**: Deterministic pass/fail outcome over correctness, compatibility and amplification thresholds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fresh reference logical workspace bytes are no more than 29,249,985 bytes (15.0 times the frozen
  1,949,999-byte source), including the complete edit/revert history and context workload.
- **SC-002**: Fresh scale logical workspace bytes are no more than 292,499,985 bytes (15.0 times the frozen
  19,499,999-byte source) under the same complete workload.
- **SC-003**: Binding-reference allocated regular-file bytes are no more than 107,249,945 bytes (55.0 times source), and
  the report explains filesystem dependence rather than generalizing that number universally.
- **SC-004**: Logical amplification falls by at least 60 percent relative to both committed F020 profile values.
- **SC-005**: One hundred percent of ordinary/compact equivalence vectors produce identical logical bytes, identities and
  lengths; one hundred percent of injected framing, truncation, expansion, length and digest faults fail closed.
- **SC-006**: Fresh and migrated optimized workspaces achieve identical precision, recall, reciprocal rank, anchor
  correctness, context coverage and replay equality to the committed workload, with zero stale incidents and zero parser
  invocations on unchanged reuse.
- **SC-007**: Every tested migration interruption converges on retry or restores from backup with zero missing logical
  objects, zero changed authoritative records and zero source re-parses.
- **SC-008**: Search rebuild, full integrity, reachability, diagnostics, backup, restore and bounded retention tests pass
  for ordinary, compact and interrupted-duplicate layouts without object double counting.
- **SC-009**: The benchmark independently reconciles category totals to complete workspace inventories and regenerates
  the same decision/report from retained machine evidence.
- **SC-010**: The complete offline suite retains at least 85 percent branch-aware coverage and passes lint, formatting,
  strict typing, repository validation, build, deterministic drift and supported-platform CI.
- **SC-011**: The final report states the logical and allocated reductions separately and names any remaining file-count,
  filesystem-allocation, migration-time or compatibility limitation.

## Assumptions

- F020's logical `st_size` total remains the historical comparison metric; F022 adds, rather than substitutes,
  allocation and file-count evidence.
- The binding allocated-byte target applies to the declared macOS/APFS reference environment; semantic and corruption
  behavior remains cross-platform.
- Exact canonical block bytes are reproducible derived evidence and may use a transparent lossless physical encoding;
  originals and provider-native artifacts remain ordinary exact files.
- Existing revision-10 workspaces require explicit backup-first migration; no multi-revision leap or downgrade-in-place is
  promised.
