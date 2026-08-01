# Tasks: Retention, Recovery and Migrations

**Input**: Design documents from `/specs/013-retention-recovery-migrations/`

**Tests**: Mandatory and written before implementation where practical. Every stateful
phase includes deterministic failure, restart, concurrency and privacy coverage.

## Phase 1: Setup and decision records

- [x] T001 Restate F013 acceptance criteria and exact commands in `specs/013-retention-recovery-migrations/implementation-notes.md`
- [x] T002 Record destructive authority, cross-resource recovery protocol, backup topology and migration-lock refinement in `docs/adr/0014-retention-recovery-maintenance.md`
- [x] T003 [P] Add internal maintenance port shape tests in `tests/contract/test_maintenance_ports.py`

---

## Phase 2: Foundational domain and catalog revision

**Purpose**: Pure models, contracts and revision 10 block every user story.

- [x] T004 Write identity, bound, UTC, transition and privacy tests in `tests/domain/test_maintenance.py`
- [x] T005 Implement closed maintenance models and canonical identities in `src/openardp/domain/maintenance.py`
- [x] T006 Implement narrow sanitized maintenance protocols/exceptions in `src/openardp/ports/maintenance.py`
- [x] T007 Write populated revision-9 upgrade, statement-fault and concurrent migration tests in `tests/integration/test_f013_migration.py`
- [x] T008 Append immutable revision-10 maintenance/retention migration in `src/openardp/adapters/sqlite_migrations.py`
- [x] T009 Implement revision-10 structural validation and active-operation write fence in `src/openardp/adapters/sqlite_catalog.py`
- [x] T010 Run foundational focused tests and record evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`

**Checkpoint**: revision 10 and pure maintenance contracts are stable.

---

## Phase 3: User Story 1 — Explain Workspace Retention (Priority: P1)

**Goal**: bounded deterministic classification and dry-run with zero mutation.

**Independent Test**: every delivered root family plus synthetic candidates/anomalies
produces one stable explainable plan across repeated/concurrent runs.

- [x] T011 [P] [US1] Write validate-only CAS and rich inventory tests in `tests/integration/test_maintenance_store.py`
- [x] T012 [P] [US1] Write complete root-reason and hold snapshot tests in `tests/integration/test_retention_catalog.py`
- [x] T013 [P] [US1] Write plan determinism, limit+1, candidate-age and anomaly tests in `tests/integration/test_retention_service.py`
- [x] T014 [US1] Add validate-only open and bounded active/quarantine inventory to `src/openardp/adapters/filesystem_cas.py` and `src/openardp/adapters/filesystem_maintenance.py`
- [x] T015 [US1] Add closed root edges, active holds and transactional retention snapshots to `src/openardp/adapters/sqlite_catalog.py`
- [x] T016 [US1] Implement conservative inventory and content-identified dry-run planning in `src/openardp/services/maintenance.py`
- [x] T017 [US1] Add body-free inventory, plan, hold-add and hold-release CLI commands in `src/openardp/interfaces/cli.py`
- [x] T018 [US1] Run the US1 independent test and record exact evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`

---

## Phase 4: User Story 2 — Quarantine and Restore Candidates (Priority: P1)

**Goal**: exact plan quarantine, restore and restart recovery without lost objects.

**Independent Test**: fault every intent/filesystem/finalization boundary and converge
to exact active or recoverable quarantine state.

- [x] T019 [P] [US2] Write catalog operation-intent, batch and idempotency tests in `tests/integration/test_retention_catalog.py`
- [x] T020 [P] [US2] Write POSIX/Windows transition-state, link, conflict and durability tests in `tests/integration/test_maintenance_store.py`
- [x] T021 [P] [US2] Write crash/restart and twenty-way lifecycle tests in `tests/integration/test_retention_recovery.py`
- [x] T022 [US2] Implement exact same-filesystem quarantine/active transitions in `src/openardp/adapters/filesystem_maintenance.py`
- [x] T023 [US2] Implement durable operation claims, ordered entries, batches and audit events in `src/openardp/adapters/sqlite_catalog.py`
- [x] T024 [US2] Implement quarantine, restore and intent-only recovery orchestration in `src/openardp/services/maintenance.py`
- [x] T025 [US2] Add quarantine, restore and recovery CLI commands in `src/openardp/interfaces/cli.py`
- [x] T026 [US2] Run the US2 independent test and record exact evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`

---

## Phase 5: User Story 4 — Back Up, Restore and Migrate Safely (Priority: P1)

**Goal**: verified paired backups, fresh restore and explicit atomic migration.

**Independent Test**: populate A, back up, migrate/write B and restore exact A to a
fresh path with no B-only facts.

- [x] T027 [P] [US4] Write backup manifest, capacity, interruption and publication tests in `tests/integration/test_backup_restore.py`
- [x] T028 [P] [US4] Write fresh restore validation, corruption, overlap and A→B→A tests in `tests/integration/test_backup_restore.py`
- [x] T029 [P] [US4] Extend byte/mtime no-mutation entrypoint tests in `tests/integration/test_workspace.py`
- [x] T030 [US4] Split create-current, validate-only open and explicit migrate behavior in `src/openardp/adapters/local_workspace.py`
- [x] T031 [US4] Add true read-only inspection, online backup session and explicit migration transaction to `src/openardp/adapters/sqlite_catalog.py`
- [x] T032 [US4] Implement bounded manifest, staged backup and fresh restore in `src/openardp/adapters/filesystem_maintenance.py`
- [x] T033 [US4] Implement paired backup/restore/migration orchestration in `src/openardp/services/maintenance.py`
- [x] T034 [US4] Add workspace-backup, workspace-restore and workspace-migrate CLI commands in `src/openardp/interfaces/cli.py`
- [x] T035 [US4] Run the US4 A→B→A drill and record exact evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`

---

## Phase 6: User Story 3 — Commit Explicit Reclamation (Priority: P2)

**Goal**: irreversible removal only after named batch, grace, final verification and
distinct acknowledgement.

**Independent Test**: 23:59:59 deletes nothing, exact minimum deletes only eligible
objects, and new references/holds restore or retain bytes.

- [x] T036 [P] [US3] Write grace/acknowledgement/revalidation tests in `tests/integration/test_retention_service.py`
- [x] T037 [P] [US3] Write delete-intent crash/recovery and conflict tests in `tests/integration/test_retention_recovery.py`
- [x] T038 [US3] Implement exact removal and post-removal verification in `src/openardp/adapters/filesystem_maintenance.py`
- [x] T039 [US3] Implement final commit action claim and durable terminal outcomes in `src/openardp/adapters/sqlite_catalog.py`
- [x] T040 [US3] Implement explicit commit orchestration and forward recovery in `src/openardp/services/maintenance.py`
- [x] T041 [US3] Add separately acknowledged storage-commit CLI command in `src/openardp/interfaces/cli.py`
- [x] T042 [US3] Run the US3 boundary/concurrency test and record exact evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`

---

## Phase 7: User Story 5 — Diagnose Space and Rebuild Indexes (Priority: P2)

**Goal**: exact storage facts, reserve gate and all-or-prior lexical rebuild.

**Independent Test**: reserve-minus-one publishes nothing, reserve-exact succeeds and a
corrupt/orphaned index rebuild matches authoritative search without evidence changes.

- [x] T043 [P] [US5] Write exact category/capacity boundary tests in `tests/integration/test_maintenance_store.py`
- [x] T044 [P] [US5] Write complete global index replacement/rollback tests in `tests/integration/test_index_rebuild.py`
- [x] T045 [US5] Implement logical storage diagnostics and reserve admission in `src/openardp/adapters/filesystem_maintenance.py`
- [x] T046 [US5] Implement global transactional lexical-index replacement in `src/openardp/adapters/sqlite_catalog.py`
- [x] T047 [US5] Implement diagnostics and authoritative index-rebuild orchestration in `src/openardp/services/maintenance.py`
- [x] T048 [US5] Add storage-diagnostics and index-rebuild CLI commands in `src/openardp/interfaces/cli.py`
- [x] T049 [US5] Run the US5 independent test and record exact evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`

---

## Phase 8: Security, documentation and convergence

- [x] T050 Add hostile path/content/output and unauthorized-authority tests in `tests/security/test_maintenance_boundaries.py`
- [x] T051 Update architecture, data model, security, operations and compatibility docs in `docs/03_DATA_MODEL_AND_PACKAGE.md`, `docs/06_SECURITY_MODEL_V2.md`, `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md`, `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md` and `docs/11_OPERATIONAL_AND_ENTERPRISE_REQUIREMENTS.md`
- [x] T052 Update operator entrypoints and project status in `README.md`, `START_HERE.md`, `docs/08_ROADMAP_AND_GOVERNANCE.md` and `CHANGELOG.md`
- [x] T053 Validate `specs/013-retention-recovery-migrations/quickstart.md` against a fresh synthetic workspace
- [x] T054 Run every gate configured by `pyproject.toml` and record Ruff, format, strict mypy, full pytest/coverage, build, schema, evidence and repository validation evidence in `specs/013-retention-recovery-migrations/implementation-notes.md`
- [x] T055 Run Spec Kit convergence, append and complete any evidence-backed gap tasks in `specs/013-retention-recovery-migrations/tasks.md`
- [x] T056 Record final contracts, commands, tradeoffs, residual risks and rollback in `specs/013-retention-recovery-migrations/implementation-notes.md`

---

## Dependencies and execution order

1. Setup and foundational tasks T001–T010 block all stories.
2. US1 creates the plan/snapshot boundary required by US2 and US3.
3. US2 establishes reversible maintenance and recovery.
4. US4 reuses the maintenance fence and can be validated before destructive commit.
5. US3 adds the only irreversible path after reversible behavior is proven.
6. US5 uses the established capacity/fence infrastructure.
7. Security/docs/convergence require all stories.

## Parallel opportunities

- Contract/domain/migration tests T003, T004 and T007 touch different files.
- Each story's test files marked `[P]` can be authored together before implementation.
- Documentation updates may be grouped after every user-story checkpoint passes.
- Story implementation itself remains sequential because all agents share catalog and
  composition-root files; this avoids conflicting authority changes.

## Implementation strategy

Complete phases in the listed order and run each independent story test before moving
on. F013 is one bounded feature commit/PR: task phases are checkpoints, not separate
feature commits. No task is complete until its test and exact evidence are recorded.

## Phase 9: Convergence

- [x] T057 Add systematic before/after persistence and filesystem fault tests for quarantine, restore and commit recovery per SC-004 (partial)
- [x] T058 Prove 100 repeated and 20 concurrent inventories plus twenty-way restore convergence per SC-001 and SC-005 (partial)
- [x] T059 Bind explicit migration to the expected source revision and add concurrent migration plus backup publication interruption tests per FR-027 and FR-036 (partial)
- [x] T060 Reject backups with missing catalog-root bytes and extend A→B→A to authoritative catalog facts per FR-022 and SC-008 (partial)
- [x] T061 Diagnose the Windows low-level read mismatch, add a focused descriptor regression test and rerun every local gate
- [x] T062 Converge concurrent POSIX hard-link transition winners by exact final state, force the race with a barrier regression and rerun every local gate
- [x] T063 Require `O_BINARY` for every low-level Windows file descriptor, retain same-handle identity plus byte/hash replay and rerun every local gate
- [x] T064 Open operation-owned staged files read/write before `fsync`, add the focused Windows `_commit` regression and rerun every local gate
- [x] T065 Converge a late same-plan quarantine caller after the winner changes inventory, reorder the atomic catalog idempotency check and rerun every local gate
