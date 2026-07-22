# Tasks: Content-Addressed Storage and SQLite Catalog

**Input**: Design documents from `specs/003-cas-sqlite-catalog/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/storage-catalog.md`, `quickstart.md`

**Tests**: Required for every public contract, persisted behavior, migration, recovery rule and security boundary. Test tasks precede their corresponding implementation tasks.

**Organization**: Shared strict persistence records and provider ports are foundational. User stories then deliver CAS, atomic source versions, recoverable jobs and reachability in priority order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches separate files and has no incomplete dependency.
- **[Story]**: Maps to US1, US2, US3 or US4 in `spec.md`.
- Every task names its primary file path.

## Phase 1: Governance and Setup

**Purpose**: Make the selected persistence architecture authoritative before code and preserve the no-new-dependency boundary.

- [X] T001 Accept and expand the SQLite/filesystem-CAS crash, durability, journal and reachability decision in `docs/adr/0002-sqlite-and-filesystem-cas-for-mvp.md`
- [X] T002 Record the F003 acceptance criteria, research decisions, test-first sequence and exact verification commands in `specs/003-cas-sqlite-catalog/implementation-notes.md`
- [X] T003 Confirm the standard-library-only runtime plan leaves `pyproject.toml` and `uv.lock` unchanged and add the expected F003 module boundary assertions in `tests/test_package.py` and `tests/test_repository_contract.py`

---

## Phase 2: Foundational Persistence Contracts

**Purpose**: Establish pure records, sanitized errors, narrow ports, fixed time encoding and migration machinery before any story adapter.

**Critical**: No user-story implementation begins until these tests fail for missing behavior and the foundation passes.

- [X] T004 [P] Write failing strict storage-record, UUIDv7 generation, source-key exactness, reference-uniqueness, fixed-UTC and job-invariant tests in `tests/domain/test_storage.py`
- [X] T005 [P] Write failing structural contract tests for object-store and catalog protocols plus sanitized error inheritance in `tests/contract/test_storage_ports.py`
- [X] T006 Implement strict immutable storage, version, job, inventory and reachability records in `src/openardp/domain/storage.py`
- [X] T007 Implement the RFC 9562 UUIDv7 generator and fixed-width UTC storage codec with injected time/randomness in `src/openardp/domain/storage.py`
- [X] T008 Implement sanitized persistence error types and the narrow `ObjectStore` protocol in `src/openardp/ports/object_store.py`
- [X] T009 Implement the narrow document/version/job/reference `Catalog` protocol in `src/openardp/ports/catalog.py`
- [X] T010 Export only reviewed F003 records, protocols and errors from `src/openardp/domain/__init__.py` and `src/openardp/ports/__init__.py`
- [X] T011 Make all foundational domain and port contract tests pass in `tests/domain/test_storage.py` and `tests/contract/test_storage_ports.py`

**Checkpoint**: F003 has pure, typed, provider-neutral contracts without filesystem or SQL I/O in domain/ports.

---

## Phase 3: User Story 1 — Preserve and reuse exact content (Priority: P1) MVP

**Goal**: Stream exact bytes into an immutable SHA-256 object store with atomic visibility, duplicate convergence and safe reads.

**Independent Test**: Store, verify and read synthetic chunks without SQLite; prove 32 concurrent and spawn-process duplicates converge and hostile identities/layouts never escape the root.

### Tests for User Story 1

- [X] T012 [US1] Write failing exact-byte, empty/chunked, bounded-read and expected-length tests in `tests/integration/test_filesystem_cas.py`
- [X] T013 [US1] Write failing 32-thread and spawn-compatible multiprocess duplicate/different-payload convergence tests in `tests/integration/test_filesystem_cas.py`
- [X] T014 [US1] Write failing iterator/write/fsync/publish interruption, temporary cleanup, pre-existing corruption and retry tests in `tests/integration/test_filesystem_cas.py`
- [X] T015 [P] [US1] Write failing malformed-ID, traversal, symlink/junction, hard-link, directory/FIFO and outside-sentinel tests with platform capability guards in `tests/security/test_storage_boundaries.py`
- [X] T016 [US1] Write failing deterministic inventory tests for valid, corrupt, malformed and staging entries in `tests/integration/test_filesystem_cas.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement canonical digest-to-path mapping, managed-tree validation and safe regular-file opening in `src/openardp/adapters/filesystem_cas.py`
- [X] T018 [US1] Implement one-pass staged chunk writes, SHA-256/length calculation, file synchronization and atomic same-root publication in `src/openardp/adapters/filesystem_cas.py`
- [X] T019 [US1] Implement idempotent concurrent destination handling, post-publication verification and durability-error retry semantics in `src/openardp/adapters/filesystem_cas.py`
- [X] T020 [US1] Implement bounded streaming reads, full digest/length verification and deterministic non-following inventory in `src/openardp/adapters/filesystem_cas.py`
- [X] T021 [US1] Export `FilesystemObjectStore` from `src/openardp/adapters/__init__.py` and make all US1 integration/security tests pass

**Checkpoint**: US1 preserves and reuses exact objects independently of any catalog, parser or network service.

---

## Phase 4: User Story 2 — Commit complete logical versions atomically (Priority: P2)

**Goal**: Register stable logical documents and make complete source-version facts/reference sets visible in one catalog transaction after physical verification.

**Independent Test**: Use independent SQLite connections around successful, retried, conflicting and fault-injected commits; readers see either no version or the complete immutable reference set.

### Tests for User Story 2

- [X] T022 [US2] Write failing revision-1 schema, constraints, foreign-key, journal-profile and migration-checksum tests in `tests/integration/test_sqlite_catalog.py`
- [X] T023 [US2] Write failing exact/concurrent source-key registration, UUIDv7 stability and hostile bound-value tests in `tests/integration/test_sqlite_catalog.py`
- [X] T024 [US2] Write failing equivalent-retry, cross-document same-bytes, immutable-conflict and complete-reference tests in `tests/integration/test_sqlite_catalog.py`
- [X] T025 [US2] Write failing independent-reader and fault-after-header/reference/pre-commit rollback tests in `tests/integration/test_sqlite_catalog.py`
- [X] T026 [P] [US2] Write failing missing/corrupt-object rejection and CAS-success/catalog-failure orphan tests in `tests/integration/test_persistence.py`
- [X] T027 [P] [US2] Write failing sensitive-locator/hostile-SQL corpus tests proving parameters, errors and logs do not expose untrusted values in `tests/security/test_storage_boundaries.py`

### Implementation for User Story 2

- [X] T028 [US2] Implement immutable checksummed revision definitions and revision-1 object/document/version/reference schema in `src/openardp/adapters/sqlite_migrations.py`
- [X] T029 [US2] Implement compatibility inspection, explicit connection PRAGMAs and transactional migration execution in `src/openardp/adapters/sqlite_catalog.py`
- [X] T030 [US2] Implement exact idempotent document registration without replacement conflict clauses in `src/openardp/adapters/sqlite_catalog.py`
- [X] T031 [US2] Implement transactional object metadata and composite source-version/reference commit plus immutable retry comparison in `src/openardp/adapters/sqlite_catalog.py`
- [X] T032 [US2] Implement deterministic document/version reads and one-transaction independent reference snapshots in `src/openardp/adapters/sqlite_catalog.py`
- [X] T033 [US2] Implement UUIDv7 document registration and CAS-verification-before-catalog orchestration in `src/openardp/services/persistence.py`
- [X] T034 [US2] Export `SQLiteCatalog` and `PersistenceService` from `src/openardp/adapters/__init__.py` and `src/openardp/services/__init__.py`, then make all US2 tests pass

**Checkpoint**: US2 exposes only complete committed source-version facts; no F002 `READY` representation is claimed.

---

## Phase 5: User Story 3 — Recover catalog work safely across restarts (Priority: P3)

**Goal**: Install/upgrade the complete schema and persist a fenced, auditable job state machine that recovers expired work deterministically.

**Independent Test**: Open fresh, revision-1, failed and too-new catalogs; exercise every job transition, exact lease boundary and restart recovery using new connections/processes.

### Tests for User Story 3

- [X] T035 [US3] Write failing fresh-to-v2, repeated-open, v1-to-v2, pending-chain rollback and too-new no-mutation tests in `tests/integration/test_sqlite_catalog.py`
- [X] T036 [US3] Write failing foreign-schema, migration-gap/checksum-drift, `foreign_key_check`, `quick_check` and DELETE/EXTRA profile tests in `tests/integration/test_sqlite_catalog.py`
- [X] T037 [US3] Write failing idempotent enqueue/deduplication and immutable job-reference tests in `tests/integration/test_sqlite_catalog.py`
- [X] T038 [US3] Write failing fenced claim/lost-response/renew/complete/retryable-fail/terminal-fail and event-sequence tests in `tests/integration/test_sqlite_catalog.py`
- [X] T039 [US3] Write failing exact-expiry, stale-owner/token/revision, attempt-limit and repeated-recovery tests in `tests/integration/test_sqlite_catalog.py`
- [X] T040 [US3] Write failing new-instance restart plus spawn-process uncommitted-transaction crash recovery tests in `tests/integration/test_sqlite_catalog.py`

### Implementation for User Story 3

- [X] T041 [US3] Add revision-2 jobs, append-only events, object references and operational indexes in `src/openardp/adapters/sqlite_migrations.py`
- [X] T042 [US3] Complete gap/checksum/newer/foreign-schema validation and all-pending exclusive migration rollback in `src/openardp/adapters/sqlite_catalog.py`
- [X] T043 [US3] Implement idempotent job creation and deterministic queued selection in `src/openardp/adapters/sqlite_catalog.py`
- [X] T044 [US3] Implement SHA-256 lease-token fencing, revision compare-and-set, renewal and idempotent completion/failure in `src/openardp/adapters/sqlite_catalog.py`
- [X] T045 [US3] Implement append-only transition events and exact-boundary expired-lease recovery with bounded attempts in `src/openardp/adapters/sqlite_catalog.py`
- [X] T046 [US3] Make the complete migration, job, restart and crash-recovery suite pass in `tests/integration/test_sqlite_catalog.py`

**Checkpoint**: US3 can reopen safely, upgrade transactionally and distinguish terminal from bounded recoverable work.

---

## Phase 6: User Story 4 — Identify storage safe to review for reclamation (Priority: P4)

**Goal**: Produce a deterministic read-only classification of live objects, candidates and integrity inconsistencies.

**Independent Test**: Mix historical version roots, job roots, complete orphans, missing/corrupt objects, malformed tree entries and staging residue; compare store/catalog state before and after analysis.

### Tests for User Story 4

- [X] T047 [US4] Write failing live-version, terminal-job, complete-orphan and deterministic ordering tests in `tests/integration/test_reachability.py`
- [X] T048 [US4] Write failing missing/corrupt-reference, malformed-tree, unsafe-link and staging-residue classification tests in `tests/integration/test_reachability.py`
- [X] T049 [US4] Write failing byte-for-byte store and catalog pre/post snapshots proving analysis performs no delete or mutation in `tests/integration/test_reachability.py`
- [X] T050 [US4] Write failing catalog-snapshot/CAS-publish race classification test documenting advisory candidate semantics in `tests/integration/test_reachability.py`

### Implementation for User Story 4

- [X] T051 [US4] Implement catalog-root union, verified inventory comparison and deterministic issue classification in `src/openardp/services/reachability.py`
- [X] T052 [US4] Export `ReachabilityService` from `src/openardp/services/__init__.py` and make all US4 tests pass

**Checkpoint**: US4 reports candidates and inconsistencies without any deletion authority.

---

## Phase 7: Documentation, Governance and Verification

**Purpose**: Align project truth, record exact evidence and close all Spec Kit/repository gates without expanding to F004.

- [X] T053 [P] Update concrete storage, source-version transaction and failure behavior in `docs/02_ARCHITECTURE.md` and `docs/03_DATA_MODEL_AND_PACKAGE.md`
- [X] T054 [P] Update F003 migration/CAS/job/reachability test strategy and operational recovery boundaries in `docs/07_TEST_AND_BENCHMARK_STRATEGY.md` and `docs/11_OPERATIONAL_AND_ENTERPRISE_REQUIREMENTS.md`
- [X] T055 [P] Mark Work Package 2 implementation evidence and preserve later package boundaries in `docs/09_CODEX_EXECUTION_PLAN.md` and `specs/README.md`
- [X] T056 [P] Update F003 current status, APIs, non-goals and changelog entries in `README.md`, `START_HERE.md` and `CHANGELOG.md`
- [X] T057 Verify no parser, ingestion CLI, FTS, cloud adapter, automatic deletion, F002 schema drift or runtime dependency entered scope using `tests/test_package.py`, `tests/test_repository_contract.py` and `git diff`
- [X] T058 Run all focused quickstart test commands and record counts, runtime SQLite version, journal mode and negative-boundary evidence in `specs/003-cas-sqlite-catalog/implementation-notes.md`
- [X] T059 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` and `uv run pytest`, then record exact results in `specs/003-cas-sqlite-catalog/implementation-notes.md`
- [X] T060 Run `uv run --locked pre-commit run --all-files`, `uv build`, `git diff --check` and tracked-file drift verification, then record exact results in `specs/003-cas-sqlite-catalog/implementation-notes.md`
- [X] T061 Verify the existing CI still defines Linux/macOS/Windows gates and prepare PR-head/post-merge evidence fields in `specs/003-cas-sqlite-catalog/implementation-notes.md`
- [X] T062 Update every completed task checkbox, specification status and final convergence evidence in `specs/003-cas-sqlite-catalog/tasks.md`, `spec.md` and `implementation-notes.md`

---

## Dependencies & Execution Order

### Phase dependencies

- **Governance and Setup** has no dependencies.
- **Foundational Contracts** depends on accepted ADR 0002 and blocks all stories.
- **US1** depends only on the foundation and delivers the independent CAS MVP.
- **US2** depends on US1 physical verification plus the foundation.
- **US3** depends on the catalog/migration foundation delivered with US2.
- **US4** depends on US1 inventory and the US2/US3 catalog reference snapshot.
- **Documentation/Verification** depends on all stories.

### User-story dependency graph

```text
Governance -> Foundation -> US1 -> US2 -> US3 -> US4 -> Verification
```

The feature is executed sequentially by one maintainer even where test authoring is marked parallel, so each independently demonstrable checkpoint remains green before the next story.

### Parallel opportunities

- T004 and T005 affect separate test files.
- T015 can be authored in parallel with T012–T014 because the security and integration files are separate; T016 follows the shared CAS test file.
- T026 and T027 can be authored in parallel after T022–T025 establish the shared catalog test file.
- T035–T040 remain sequential because they intentionally build one coherent catalog recovery contract in the same file.
- T047–T050 remain sequential because they build one coherent reachability contract in the same file.
- T053–T056 update separate documentation groups after contracts stabilize.

## Requirement Coverage

| Requirement group | Primary tasks |
|---|---|
| FR-001–FR-007 exact objects, atomicity, path safety, streaming | T012–T021 |
| FR-008–FR-013 documents, source versions, references, independent visibility | T022–T034 |
| FR-014–FR-015 migrations and compatibility | T022, T028–T029, T035–T036, T041–T042 |
| FR-016–FR-018 jobs, fencing and recovery | T004, T037–T046 |
| FR-019–FR-020 reachability and no deletion | T016, T047–T052 |
| FR-021 tests, security and offline evidence | T004–T005, T012–T016, T022–T027, T035–T040, T047–T050, T058–T061 |
| FR-022 bounded scope | T001–T003, T053–T057 |
| SC-001–SC-003 concurrency, interruption and idempotency | T013–T015, T023–T026, T037–T040 |
| SC-004–SC-005 migration and restart recovery | T035–T046 |
| SC-006–SC-007 path safety and reachability accuracy | T015–T016, T027, T047–T052 |
| SC-008 repository and platform gates | T057–T061 |

## Implementation Strategy

### MVP first

1. Accept ADR 0002 and complete foundational contracts.
2. Complete US1 and prove safe exact-byte storage independently.
3. Do not begin catalog work until the CAS checkpoint passes.

### Incremental delivery

1. US1 makes immutable exact objects reusable.
2. US2 adds stable logical documents and atomic source-version facts.
3. US3 adds transactional upgrades and durable fenced work recovery.
4. US4 adds advisory read-only reachability.
5. Full documentation, quality and cross-platform gates close F003 before F004 begins.

### Task discipline

- Tests are authored and observed failing before corresponding implementation.
- A completed task is marked `[X]` immediately.
- Dynamic SQL values use parameters; migration/PRAGMA text is static closed code.
- No task authorizes automatic deletion, parser behavior or a `READY` representation.
- Persisted identity changes require a separate ADR and migration analysis.

## Phase 8: Convergence

- [X] T063 Harden immutable source-version retry comparison for `source_modified_at` and canonical reference ordering, with lost-response/conflict tests, per FR-011 and SC-003 (partial)
- [X] T064 Enforce monotonic durable job transitions plus coherent event, inventory and recovery-result invariants with deterministic tests per FR-016, FR-017 and US3/AC3 (partial)
- [X] T065 Suppress raw iterator and operating-system exception details from public CAS exception chains and add non-disclosure tests per plan security constraints and Constitution IV (partial)
- [X] T066 Constrain every persisted lease-token proof to canonical SHA-256 syntax and verify rejection in migration/schema tests per plan: job fencing (partial)
