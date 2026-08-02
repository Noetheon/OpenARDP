# Tasks: Reduce Storage Amplification Without Weakening Evidence

**Input**: Design documents from `/specs/022-storage-amplification/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/storage-optimization.md`

**Tests**: Tests are mandatory and are written before behavior and contract changes where practical.

**Organization**: Tasks are grouped by user story. Because persistence formats share invariants, the user stories are
delivered sequentially even where individual test or documentation tasks can be prepared independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with adjacent tasks because it changes different files and has no unmet dependency
- **[Story]**: Maps the task to the corresponding story in `spec.md`

## Phase 1: Setup and Governance

**Purpose**: Freeze the measured problem, accepted design and compatibility boundary before product changes.

- [X] T001 Record the accepted persisted-layout decision in `docs/adr/0018-compact-derived-block-storage.md`
- [X] T002 [P] Complete feature requirements and design artifacts in `specs/022-storage-amplification/`
- [X] T003 [P] Pin the F020 input/result comparison facts in `benchmarks/storage/v0.1.0/baseline.json`
- [X] T004 Add F022 artifact and ADR references to `spec-kit/FEATURE_MAP.md` and `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md`

---

## Phase 2: Foundational Contracts

**Purpose**: Introduce body-free types and optional provider-neutral capabilities used by all stories.

**Critical**: No user-story implementation begins until these contracts are type-safe and their existing-provider fallback
is covered.

- [X] T005 [P] Add failing model tests for closed optimization outcomes and body-free reports in `tests/domain/test_maintenance.py`
- [X] T006 [P] Add failing port conformance tests for optional compact publication and optimization capabilities in `tests/contract/test_storage_ports.py`
- [X] T007 Define immutable optimization item/report models with strict invariants in `src/openardp/domain/maintenance.py`
- [X] T008 Define runtime-checkable optional compact-record and existing-object optimization protocols in `src/openardp/ports/object_store.py`
- [X] T009 Add a deterministic derived-block optimization inventory contract in `src/openardp/ports/catalog.py`
- [X] T010 Export only the new stable internal symbols from `src/openardp/domain/__init__.py` and `src/openardp/ports/__init__.py`
- [X] T011 Run and satisfy foundational model/port tests in `tests/domain/test_maintenance.py` and `tests/contract/test_storage_ports.py`

**Checkpoint**: Providers implementing only the ordinary object-store contract remain conformant.

---

## Phase 3: User Story 1 — Prepare New Text Workspaces Efficiently (Priority: P1) MVP

**Goal**: New canonical F002 block objects are stored compactly when beneficial and catalog projections stop repeating the
same representation/search scope metadata.

**Independent Test**: Ingest the frozen reference workload into a fresh revision-11 workspace, reopen it, reconcile all
versions and demonstrate logical amplification at or below 15x without changing logical IDs or bytes.

### Tests for User Story 1

- [X] T012 [P] [US1] Add failing codec vectors for deterministic round-trip, threshold fallback and exact envelope parsing in `tests/unit/test_compact_objects.py`
- [X] T013 [P] [US1] Add failing hostile codec boundary cases in `tests/security/test_storage_compaction_boundaries.py`
- [X] T014 [P] [US1] Add failing dual-layout publication and provider-fallback tests in `tests/integration/test_filesystem_cas.py`
- [X] T015 [P] [US1] Add failing revision-11 fresh-schema and normalized projection tests in `tests/integration/test_persistence.py`
- [X] T016 [P] [US1] Add failing fresh-ingestion logical-byte and exact-replay tests in `tests/integration/test_storage_compaction.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement the fixed-dictionary bounded v1 codec and sanitized error mapping in `src/openardp/adapters/compact_objects.py`
- [X] T018 [US1] Add atomic compact publication, form discovery and verified logical reads to `src/openardp/adapters/filesystem_cas.py`
- [X] T019 [US1] Define revision-11 normalized scope/block tables and migration inventory in `src/openardp/adapters/sqlite_migrations.py`
- [X] T020 [US1] Rewrite block persistence, scope lookup and reconciliation queries for revision 11 in `src/openardp/adapters/sqlite_catalog.py`
- [X] T021 [US1] Rewrite contentless FTS indexing, coverage and search joins for merged block metadata in `src/openardp/adapters/sqlite_document_queries.py`
- [X] T022 [US1] Route canonical derived text blocks through the optional compact capability with ordinary fallback in `src/openardp/services/ingestion.py`
- [X] T023 [US1] Update fresh-workspace revision creation and supported-revision checks in `src/openardp/adapters/local_workspace.py`
- [X] T024 [US1] Satisfy codec, fresh-CAS, schema, ingestion, search and reconciliation tests in `tests/unit/test_compact_objects.py`, `tests/integration/test_filesystem_cas.py`, `tests/integration/test_persistence.py` and `tests/integration/test_storage_compaction.py`

**Checkpoint**: Fresh workspaces are smaller, exact and independently usable; no migration or maintenance behavior is
required for this checkpoint.

---

## Phase 4: User Story 2 — Read and Verify Exact Evidence Transparently (Priority: P1)

**Goal**: Ordinary retrieval, streaming, verification, search and context compilation are encoding-blind while every
present physical form is checked before returning exact logical evidence.

**Independent Test**: Run the same document query, search and context assertions over ordinary-only, compact-only and
valid-duplicate fixtures; bytes and IDs are identical, while any corrupt peer fails closed.

### Tests for User Story 2

- [X] T025 [P] [US2] Add failing ordinary/compact/duplicate read and stream equivalence cases in `tests/integration/test_filesystem_cas.py`
- [X] T026 [P] [US2] Add failing corrupt-peer, over-expansion and trailing-data cases in `tests/security/test_storage_compaction_boundaries.py`
- [X] T027 [P] [US2] Add failing search-body cross-check and rebuilt-index equivalence cases in `tests/integration/test_document_query.py`
- [X] T028 [P] [US2] Add failing context-selection equivalence cases in `tests/domain/test_context_compilation.py`

### Implementation for User Story 2

- [X] T029 [US2] Complete encoding-blind `get`, `iter_chunks`, `verify` and logical-inventory semantics in `src/openardp/adapters/filesystem_cas.py`
- [X] T030 [US2] Enforce complete nullable search metadata and CAS-backed body verification in `src/openardp/adapters/sqlite_document_queries.py`
- [X] T031 [US2] Preserve exact query and context service behavior over compact objects in `src/openardp/services/document_query.py` and `src/openardp/services/context_compiler.py`
- [X] T032 [US2] Satisfy read, security, search and context equivalence tests in `tests/integration/test_filesystem_cas.py`, `tests/security/test_storage_compaction_boundaries.py`, `tests/integration/test_document_query.py` and `tests/domain/test_context_compilation.py`

**Checkpoint**: No product reader can observe an encoding-dependent logical result or silently hide a corrupt duplicate.

---

## Phase 5: User Story 3 — Upgrade Existing Workspaces Safely (Priority: P1)

**Goal**: Revision-10 workspaces migrate through a verified backup and existing eligible block objects compact through an
explicit, idempotent and interruption-safe operation.

**Independent Test**: Migrate a populated revision-10 edit/revert workspace, inject interruption at each durable physical
transition, retry to convergence, and restore the revision-10 backup with zero missing logical objects.

### Tests for User Story 3

- [X] T033 [P] [US3] Add failing revision-10 to revision-11 row/count/FTS/ID migration tests in `tests/integration/test_f022_migration.py`
- [X] T034 [P] [US3] Add failing backup-before-mutation and revision-10 restore tests in `tests/integration/test_backup_restore.py`
- [X] T035 [P] [US3] Add failing optimizer outcome, eligibility and idempotence tests in `tests/unit/test_storage_optimization.py`
- [X] T036 [P] [US3] Add failing interruption and duplicate-convergence tests in `tests/integration/test_storage_optimization.py`
- [X] T037 [P] [US3] Add failing CLI envelope, revision and sanitized-failure tests in `tests/integration/test_cli_storage.py`

### Implementation for User Story 3

- [X] T038 [US3] Implement checksummed revision-11 migration with stable indexed row IDs and equivalence validation in `src/openardp/adapters/sqlite_migrations.py`
- [X] T039 [US3] Generalize verified migration-backup revision recording and restore compatibility in `src/openardp/adapters/local_workspace.py`
- [X] T040 [US3] Implement deterministic eligible derived-block inventory with authoritative-reference exclusions in `src/openardp/adapters/sqlite_catalog.py`
- [X] T041 [US3] Implement existing-object compact/skip/converge operations and injectable fault boundaries in `src/openardp/adapters/filesystem_cas.py`
- [X] T042 [US3] Implement body-free idempotent optimization orchestration in `src/openardp/services/storage_optimization.py`
- [X] T043 [US3] Add `storage-optimize --store WORKSPACE [--json]` with bounded error semantics in `src/openardp/interfaces/cli.py`
- [X] T044 [US3] Satisfy migration, backup, optimizer recovery and CLI tests in `tests/integration/test_f022_migration.py`, `tests/integration/test_backup_restore.py`, `tests/unit/test_storage_optimization.py`, `tests/integration/test_storage_optimization.py` and `tests/integration/test_cli_storage.py`

**Checkpoint**: Existing revision-10 data has a verified rollback artifact and every tested interruption safely converges
or restores.

---

## Phase 6: User Story 4 — Preserve Search, Maintenance and Portability (Priority: P1)

**Goal**: Integrity, reachability, diagnostics, retention, quarantine, backup and restore understand both physical layouts
and never count one logical identity twice.

**Independent Test**: Exercise full verify, reachability, search rebuild, quarantine, retention, exact backup and restore
over raw-only, compact-only and recoverable duplicate fixtures, including bounded failure and cancellation.

### Tests for User Story 4

- [X] T045 [P] [US4] Add failing dual-layout inventory, quarantine and retention tests in `tests/unit/test_filesystem_maintenance.py`
- [X] T046 [P] [US4] Add failing duplicate-blocking and corrupt-form diagnostics in `tests/security/test_maintenance_boundaries.py`
- [X] T047 [P] [US4] Add failing compact exact-file backup/restore inventory cases in `tests/integration/test_backup_restore.py`
- [X] T048 [P] [US4] Add failing reachability and full-integrity equivalence cases in `tests/domain/test_maintenance.py` and `tests/domain/test_storage.py`
- [X] T049 [P] [US4] Add failing revision-11 search clear/rebuild and coverage cases in `tests/integration/test_document_query.py`

### Implementation for User Story 4

- [X] T050 [US4] Extend bounded active/quarantine scans and physical-form observations in `src/openardp/adapters/filesystem_maintenance.py`
- [X] T051 [US4] Make maintenance planning and transitions block unsafe duplicates and preserve the unique valid form in `src/openardp/services/maintenance.py`
- [X] T052 [US4] Extend exact backup manifests and restore verification for compact physical files in `src/openardp/adapters/local_workspace.py`
- [X] T053 [US4] Preserve deduplicated logical reachability and full verification in `src/openardp/services/reachability.py` and `src/openardp/services/persistence.py`
- [X] T054 [US4] Complete revision-11 disposable search rebuild semantics in `src/openardp/adapters/sqlite_document_queries.py`
- [X] T055 [US4] Satisfy maintenance, security, backup/restore, reachability and rebuild tests in `tests/unit/test_filesystem_maintenance.py`, `tests/security/test_maintenance_boundaries.py`, `tests/integration/test_backup_restore.py`, `tests/domain/test_maintenance.py`, `tests/domain/test_storage.py` and `tests/integration/test_document_query.py`

**Checkpoint**: All lifecycle operations retain the same evidence and recovery boundaries across both physical layouts.

---

## Phase 7: User Story 5 — Reproduce the Storage Claim (Priority: P2)

**Goal**: A clean-room offline run independently proves or disproves the storage claim at reference and scale while
reporting logical bytes, allocated bytes and correctness separately.

**Independent Test**: Generate the exact five-file result set in a fresh output directory and validate it independently;
any drift, extra file, body/path leakage, arithmetic mismatch or unmet threshold produces `FAIL`.

### Tests for User Story 5

- [X] T056 [P] [US5] Add failing protocol, arithmetic, privacy and drift validator cases in `tests/unit/test_storage_benchmark.py`
- [X] T057 [P] [US5] Add failing committed-result reproduction contract in `tests/test_storage_benchmark_drift.py`
- [X] T058 [P] [US5] Add failing repository inventory rules for storage artifacts in `tests/test_repository_validation.py`

### Implementation for User Story 5

- [X] T059 [US5] Define the frozen body-free benchmark protocol in `benchmarks/storage/v0.1.0/protocol.json`
- [X] T060 [US5] Implement deterministic workload, inventory and allocation observations in `scripts/storage_benchmark.py`
- [X] T061 [US5] Implement the fresh-reference, migrated-reference and fresh-scale execution harness in `scripts/run_storage_benchmark.py`
- [X] T062 [US5] Implement independent closed-inventory and decision validation in `scripts/validate_storage_benchmark.py`
- [X] T063 [US5] Generate and retain the binding reference and scale artifacts in `benchmarks/storage/v0.1.0/results/reference-macos-arm64/`
- [X] T064 [US5] Document reproduction, category reconciliation and limitations in `benchmarks/storage/v0.1.0/README.md`
- [X] T065 [US5] Satisfy benchmark unit, drift and repository validation tests in `tests/unit/test_storage_benchmark.py`, `tests/test_storage_benchmark_drift.py` and `tests/test_repository_validation.py`

**Checkpoint**: The committed evidence supports `PASS` only if every storage, integrity and equivalence threshold is met.

---

## Phase 8: Polish and Cross-Cutting Validation

**Purpose**: Converge contracts, documentation, maintainability and full cross-platform evidence.

- [X] T066 [P] Update storage, migration, CLI and benchmark guidance in `README.md`, `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md` and `CHANGELOG.md`
- [X] T067 [P] Update architecture and public-contract inventories without changing schema versions in `docs/02_ARCHITECTURE.md` and `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md`
- [X] T068 Regenerate or validate checked-in schemas and repository inventories with `scripts/generate_schemas.py` and `scripts/validate_repository.py`
- [X] T069 Audit codec, filesystem, catalog and migration hotspots against `scripts/audit_maintainability.py` and refactor only measured F022 debt
- [X] T070 Run the focused commands in `specs/022-storage-amplification/quickstart.md` and record exact outcomes in `specs/022-storage-amplification/tasks.md`
- [X] T071 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest`, `uv run python scripts/validate_repository.py`, `uv build` and `uv run pre-commit run --all-files`
- [X] T072 Run Spec-Kit analysis and convergence, resolve every critical/high issue, and record remaining risks in `specs/022-storage-amplification/tasks.md`
- [ ] T073 Open the private GitHub pull request, pass trusted Linux/macOS/Windows quality gates, merge it and verify post-merge CI

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)** has no code dependency and freezes governance.
- **Foundational (Phase 2)** depends on Phase 1 and blocks all stories.
- **US1 (Phase 3)** depends on the optional capability contracts and revision-11 design.
- **US2 (Phase 4)** depends on US1 physical publication and normalized projections.
- **US3 (Phase 5)** depends on US1/US2 so migration targets a fully usable revision 11.
- **US4 (Phase 6)** depends on US3 duplicate and recovery semantics.
- **US5 (Phase 7)** depends on US1–US4 because it measures the complete product behavior.
- **Polish (Phase 8)** depends on every selected story and benchmark evidence.

### Parallel Opportunities

- Governance documents T002–T003 can be prepared alongside T001.
- Each story's `[P]` test tasks touch independent suites and can be authored together before implementation.
- Documentation tasks T066–T067 can proceed together after behavior and evidence stabilize.
- Story phases themselves remain sequential because they share persisted-state invariants and the user explicitly requested
  one completed work package at a time.

## Implementation Strategy

### MVP First

1. Complete governance and provider-neutral contracts.
2. Deliver US1 fresh-workspace compaction and normalized catalog.
3. Stop and prove exact replay plus the reference logical threshold before broadening lifecycle behavior.

### Incremental Delivery

1. Add encoding-transparent evidence reads and hostile-input rejection (US2).
2. Add explicit migration and optimization with verified rollback (US3).
3. Extend every maintenance/backup/restore consumer (US4).
4. Freeze and reproduce both favorable and unfavorable storage evidence (US5).
5. Run full local and three-platform CI gates before merge.

## Notes

- No task may delete history, change logical identifiers, compress originals/native artifacts, add cloud access or weaken
  body verification to meet a byte threshold.
- Check tasks only after their named tests or artifacts are actually complete; record exact commands for T070–T073.
- If implementation reveals a requirements conflict, fix `spec.md`/`plan.md` first and regenerate downstream tasks.

## Phase 9: Convergence

- [X] T074 Add a restart-persistent, explicitly recoverable storage-optimization write fence and concurrent-ingestion/crash tests per FR-010, FR-016 and the concurrent optimization edge case (partial)

## Validation record — 2026-08-02

- Quickstart fresh behavior: `45 passed in 0.94s`; migration/recovery: `17 passed in 1.47s`.
- Binding storage benchmark: `PASS` in 490.73 seconds; independent committed-artifact validation: `PASS`. A second fresh
  run reproduced optimized summary/report/decision content exactly; only pre-`VACUUM` SQLite allocation and duration varied.
- Static and full local gates: Ruff check/format and strict mypy passed; `1479 passed in 168.51s` with 85.20% coverage.
- Repository and packaging gates: repository validation, maintainability audit, source/wheel build and every pre-commit hook passed.
- Spec-Kit analysis found no critical contradiction. Convergence reviewed 48 requirements/acceptance criteria, 14 plan
  decisions and 12 constitution principles; its one partial high-severity write-fence gap is closed by T074 and the
  restart/concurrent-ingestion integration tests. T073 remains open until private PR, three-platform CI, merge and
  post-merge CI evidence exist.
