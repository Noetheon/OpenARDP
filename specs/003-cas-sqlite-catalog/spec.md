# Feature Specification: Content-Addressed Storage and SQLite Catalog

**Feature Branch**: `codex/f003-cas-sqlite-catalog`

**Created**: 2026-07-22

**Status**: Converged; cross-platform PR and post-merge `main` CI passed

**Input**: User description: "Implement F003 completely, deeply, sustainably and according to best practice. Persist immutable content objects, documents, versions and jobs safely on one machine so repeated ingestion can reuse exact content and interrupted work cannot expose partial state."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve and reuse exact content (Priority: P1)

As a local OpenARDP component, I can store an exact byte sequence once and retrieve it by its content identity, so originals and large artifacts remain immutable while duplicate content is reused safely.

**Why this priority**: Durable, byte-exact evidence is the foundation for every later parser, ingestion and retrieval feature. A corrupt or mutable object store would invalidate provenance throughout the platform.

**Independent Test**: Store synthetic byte streams, retrieve each by its returned identity, and prove byte equality, integrity metadata, immutability and duplicate convergence without using the catalog, a parser or network access.

**Acceptance Scenarios**:

1. **Given** a new byte stream, **When** it is stored, **Then** the returned identity equals the SHA-256 digest of the exact bytes and a subsequent read returns those exact bytes and recorded length.
2. **Given** the same bytes are stored repeatedly or concurrently, **When** all operations finish, **Then** every caller receives the same identity and exactly one valid immutable object is visible.
3. **Given** an operation is interrupted before an object is published, **When** the store is inspected or the operation is retried, **Then** no partial object is addressable and the retry can safely publish the complete object.
4. **Given** a malformed identity, traversal-like input or identity whose stored bytes fail verification, **When** access is attempted, **Then** access fails explicitly without reading or modifying content outside the configured store.

---

### User Story 2 - Commit complete logical versions atomically (Priority: P2)

As an ingestion coordinator, I can register a logical document and commit an exact source version with all of its object references as one unit, so readers never observe a partially committed version.

**Why this priority**: Later ingestion and search can only trust catalog state if a visible version always represents a complete, internally consistent commit.

**Independent Test**: Register a document, attempt successful and deliberately interrupted version commits, then query the catalog from an independent connection and prove that only complete committed versions and references are visible.

**Acceptance Scenarios**:

1. **Given** a previously unseen source identity, **When** it is registered, **Then** one stable logical document identifier is assigned and repeated registration of the same source key returns that identifier without creating a duplicate document.
2. **Given** a valid immutable source object and version identity, **When** a version commit succeeds, **Then** the version, source-object metadata and references become visible together and repeated commits are idempotent.
3. **Given** a failure at any point before the catalog commit completes, **When** another reader queries visible versions, **Then** it observes neither the incomplete version nor any partial reference set.
4. **Given** a version identity that does not match the authoritative source object, a missing object or conflicting immutable metadata, **When** commit is attempted, **Then** the entire commit is rejected and existing state is unchanged.

---

### User Story 3 - Recover catalog work safely across restarts (Priority: P3)

As a local operator, I can initialize or upgrade the catalog and persist job lifecycle transitions, so an interrupted process can restart with an unambiguous view of completed, failed and recoverable work.

**Why this priority**: Local-first operation must tolerate process termination without manual database repair or ambiguous work ownership.

**Independent Test**: Initialize fresh and existing catalogs, exercise valid and invalid job transitions, simulate expired work ownership, reopen the catalog, and verify deterministic recovery and migration state.

**Acceptance Scenarios**:

1. **Given** an empty storage root, **When** initialization runs, **Then** the complete supported catalog schema is installed exactly once and a repeated initialization leaves the same logical schema and data intact.
2. **Given** a catalog at an installed older schema revision, **When** it is opened, **Then** pending migrations apply transactionally in order; a failed migration exposes neither a partially upgraded schema nor a falsely advanced schema version.
3. **Given** queued work, **When** a worker claims, renews and completes or fails it using valid ownership, **Then** each lifecycle transition is durable, auditable by identifiers and timestamps, and repeat calls are idempotent where the outcome already matches.
4. **Given** running work whose ownership lease expired before a restart, **When** recovery runs, **Then** it becomes eligible for bounded retry without changing committed document versions or reviving terminal work.
5. **Given** an unsupported newer catalog schema or an invalid job transition, **When** the catalog is opened or updated, **Then** the operation fails clearly without modifying durable state.

---

### User Story 4 - Identify storage that is safe to review for reclamation (Priority: P4)

As a local operator, I can obtain a deterministic reachability report for stored objects, so unreferenced data can be investigated without automatically deleting live evidence.

**Why this priority**: Failed or interrupted commits may legitimately leave complete but unreferenced objects. Operators need safe observability before any later garbage-deletion policy exists.

**Independent Test**: Create referenced and deliberately orphaned objects, request a reachability report, and prove that all committed references remain reachable while only unreferenced complete objects are reported as candidates and no bytes are deleted.

**Acceptance Scenarios**:

1. **Given** objects referenced by committed versions and jobs plus unreferenced objects, **When** reachability is analyzed, **Then** every referenced object is classified as reachable and every complete unreferenced object is classified as a candidate with its identity and size.
2. **Given** catalog references to a missing or integrity-invalid object, **When** analysis runs, **Then** the inconsistency is reported separately from ordinary unreferenced candidates.
3. **Given** any reachability analysis result, **When** the operation finishes, **Then** neither catalog records nor stored object bytes have been changed or deleted.

### Edge Cases

- The stored payload is empty, very large relative to a unit-test fixture, or supplied as chunks with unusual boundaries.
- Multiple processes attempt to publish identical or different content at the same time.
- The process stops after a temporary file is durable but before publication, or after object publication but before catalog commit.
- A temporary file, unrelated filesystem entry, symbolic link or directory exists where an object or store directory is expected.
- An identity contains uppercase hexadecimal, the wrong digest length, an unsupported algorithm, path separators, dot segments, control characters or a valid digest for different bytes.
- A source key is registered concurrently and repeated registrations disagree on immutable source attributes.
- The same source bytes are referenced by multiple logical documents or multiple versions.
- A version or job creation is retried after the previous caller lost its response.
- A job lease expires exactly at a renewal or completion boundary, or the wall clock moves between process runs.
- A migration is interrupted, partially executes before rollback, or encounters a catalog schema newer than this release supports.
- A reachability scan encounters an incomplete temporary object, a malformed object-tree entry or a catalog reference to a missing object.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST derive every stored-object identity from the SHA-256 digest of the exact supplied bytes and MUST preserve those bytes without normalization or rewriting.
- **FR-002**: The system MUST publish complete objects atomically so an object identity is never addressable while only a prefix or otherwise incomplete payload exists.
- **FR-003**: The system MUST treat published objects as immutable and MUST reject any attempt to associate conflicting bytes, length or integrity metadata with an existing identity.
- **FR-004**: Concurrent and repeated storage of identical bytes MUST converge idempotently on one valid visible object and the same object metadata.
- **FR-005**: Object reads MUST accept only validated content identities, derive all internal locations within the configured store, and reject traversal, unsafe-link and malformed-tree conditions without accessing content outside that store.
- **FR-006**: The system MUST support streaming or chunked object writes and reads so callers are not required to materialize an entire object in memory.
- **FR-007**: Integrity verification MUST compare the stored byte length and SHA-256 digest to the requested identity and distinguish missing, corrupt and malformed objects.
- **FR-008**: The catalog MUST register one stable logical document for a unique source key while permitting byte-identical content to be referenced by different logical documents.
- **FR-009**: The catalog MUST record immutable source versions, stored-object metadata and explicit object references without storing original body content in ordinary logs or error messages.
- **FR-010**: A committed version MUST become visible together with its complete required reference set in one atomic logical commit; failed or interrupted commits MUST expose no partial version.
- **FR-011**: Version commits and document registration MUST be idempotent for equivalent retries and MUST reject conflicting reuse of any persisted identity or source key.
- **FR-012**: A version commit MUST verify that every referenced object exists and matches its declared identity and immutable metadata before the version is made visible.
- **FR-013**: Catalog reads from independent connections MUST observe only committed state and MUST not depend on process-local caches for correctness.
- **FR-014**: The catalog MUST install and upgrade a versioned schema through ordered, transactional migrations, recording a migration only after the complete migration succeeds.
- **FR-015**: Opening a catalog whose schema is newer than the installed reader supports MUST fail safely and clearly without changing that catalog.
- **FR-016**: The catalog MUST persist job identity, kind, state, bounded attempt count, lease ownership and expiry, timestamps, and a sanitized failure classification sufficient for deterministic restart recovery.
- **FR-017**: Job lifecycle transitions MUST enforce ownership and allowed-state rules, use compare-and-set semantics where concurrent workers could race, and be idempotent when a retry repeats an already-achieved outcome.
- **FR-018**: Recovery MUST make expired non-terminal jobs eligible for bounded retry while leaving terminal jobs and committed document versions unchanged.
- **FR-019**: Reachability analysis MUST classify complete objects referenced by committed catalog records as reachable, complete unreferenced objects as candidates, and missing, corrupt or malformed entries as inconsistencies.
- **FR-020**: Reachability analysis in this feature MUST be read-only and MUST never delete objects or catalog records.
- **FR-021**: Every public storage and catalog contract, persisted behavior, security boundary, migration and recovery transition introduced by this feature MUST have deterministic automated tests using synthetic or redistributable fixtures and no network access.
- **FR-022**: The feature MUST remain bounded to storage and catalog persistence; parsing, normalization, full ingestion commands, search indexing, automatic garbage deletion and cloud storage are outside this feature.

### Key Entities

- **Stored Object**: Immutable exact bytes identified by SHA-256, with byte length and integrity state; it may be referenced by many catalog records.
- **Logical Document**: Stable document identity associated with a connector namespace and opaque source locator key across source versions.
- **Document Version**: Immutable association between one logical document, an exact source version identity and its required stored-object references; visible only after complete commit.
- **Object Reference**: Typed, role-bearing edge from a committed catalog record to a stored object, used for integrity checks and reachability.
- **Migration Record**: Ordered catalog schema revision that is recorded only after its transaction succeeds.
- **Job**: Durable unit of local work with state, bounded retries, ownership lease and sanitized outcome classification.
- **Reachability Report**: Read-only classification of reachable objects, unreferenced candidates and integrity inconsistencies at one observed catalog state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across at least 32 concurrent attempts to store the same synthetic payload, every caller receives the same identity, exactly one complete object is visible, and its bytes pass length and SHA-256 verification.
- **SC-002**: Deliberate interruption at every tested publication and catalog-commit boundary produces zero addressable partial objects and zero visible partial document versions.
- **SC-003**: Repeating every supported document, version and job operation after a simulated lost response either returns the original successful outcome or a specific immutable conflict; it never creates duplicate logical records.
- **SC-004**: Fresh initialization, repeated initialization, every supported upgrade path and an injected migration failure all produce the exact expected schema version and preserve pre-existing committed data.
- **SC-005**: After closing and reopening the storage layer, all committed versions remain queryable, expired recoverable jobs are identified exactly once per recovery attempt, and terminal jobs remain terminal.
- **SC-006**: A security corpus covering malformed identities, traversal strings, symbolic-link escapes and malformed object-tree entries performs zero reads or writes outside the configured storage root.
- **SC-007**: In a synthetic mixed store, reachability classification has no false-unreachable result for live references, reports every deliberately orphaned complete object, surfaces every injected missing/corrupt reference, and deletes zero bytes.
- **SC-008**: The full repository quality gates pass offline on the supported Python baseline, and the storage/catalog test suite passes on Linux, macOS and Windows CI.

## Assumptions

- This feature is a single-machine persistence layer; distributed databases, remote object stores and cross-host locking remain future adapter concerns.
- SHA-256 object identities and F002 source-version identities are already authoritative and are not changed by this feature.
- A unique source key is the pair of connector namespace and opaque locator value; it is catalog metadata, never interpreted as a filesystem path by the persistence core.
- An object may be durably published before the catalog transaction that references it. If that later transaction fails, the complete object is an unreferenced reachability candidate, not a partial logical version.
- Job leases use UTC instants for durable comparison, while callers must provide current time explicitly so recovery tests remain deterministic.
- Bounded retry policy is supplied as validated job data; automatic scheduling, backoff timers and watcher behavior remain later work.
- Historical committed versions remain live evidence even if a later lifecycle flag marks them superseded or deleted; reclamation policy is deliberately outside F003.
- The existing SQLite catalog and unpacked filesystem content-addressed store decisions remain in force; this feature does not replace either architecture component.

## Dependencies

- F001 repository baseline and quality gates.
- F002 canonical SHA-256 identities, strict domain values and document/version contracts.
- OpenARDP constitution, `AGENTS.md`, architecture documents and ADRs governing local storage, identity and atomicity.

## Out of Scope

- TXT, Markdown, PDF, DOCX or PPTX parsing and normalization.
- Block, relation or derivation persistence beyond reserving future migration-safe catalog boundaries.
- FTS5 indexes, lexical or semantic retrieval, embeddings and context compilation.
- File watching, debounce and automatic job scheduling.
- Automatic deletion, retention policy, secure erasure or compaction of unreferenced objects.
- Portable `.ardp.zip` export/import and archive extraction.
- Cloud databases, remote blob stores, multi-tenant authorization and production distributed locking.
