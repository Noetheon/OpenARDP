# Tasks: Local Watcher and Stable Jobs

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [ADR 0013](../../docs/adr/0013-local-watch-reconciliation-and-cancellable-jobs.md)

**Tests**: Required first where practical. Every fixture is synthetic and the complete
suite remains network-disabled.

## Phase 1 — Governance and green baseline

- [x] T001 Confirm active feature metadata, branch and rollback commit in
  `.specify/feature.json` and `implementation-notes.md`.
- [x] T002 Freeze the v3.1 F012 prompt digest and acceptance reconciliation in
  `implementation-notes.md`.
- [x] T003 Validate specification and watcher/job checklists and record the result.
- [x] T004 Update active-feature repository governance expectations for F012 without
  weakening prior artifact checks.
- [x] T005 Run Ruff check/format, strict mypy, full pytest, build, schema, evidence and
  repository validators; record the authoritative baseline.

## Phase 2 — Generic job evolution (US3, foundation)

**Goal**: Add truthful eligibility and cancellation to the existing fenced job machine.

### Tests

- [x] T006 [P] Add failing pure job-model tests for `CANCELLED`, eligibility,
  cancellation request and terminal invariants in `tests/domain/test_jobs.py`.
- [x] T007 [P] Add failing event-transition and redaction tests for request/acknowledge/
  recovery cancellation in `tests/domain/test_jobs.py`.
- [x] T008 [P] Add failing migration-9 upgrade tests from empty and populated revision 8
  catalogs in `tests/integration/test_f012_migration.py`.
- [x] T009 [P] Add injected migration failure, concurrent upgrade, future-version and
  released-checksum tests in `tests/integration/test_f012_migration.py`.
- [x] T010 [P] Add failing claim eligibility/order and delayed retry tests in
  `tests/integration/test_job_cancellation.py`.
- [x] T011 [P] Add queued/running/replayed/terminal cancellation tests in
  `tests/integration/test_job_cancellation.py`.
- [x] T012 [P] Add twenty-client cancellation race and stale renew/complete/fail fencing
  tests in `tests/integration/test_job_cancellation.py`.
- [x] T013 [P] Add cancellation-aware expired-lease recovery and restart tests in
  `tests/integration/test_job_cancellation.py`.

### Implementation

- [x] T014 Extend job states, projections, events and recovery results in
  `src/openardp/domain/storage.py` and exports.
- [x] T015 Add revision-9 replacement job tables, copy/swap/index logic and migration
  export in `src/openardp/adapters/sqlite_migrations.py`.
- [x] T016 Update exact revision-9 table expectations and structural diagnostics in
  `src/openardp/adapters/sqlite_catalog.py`.
- [x] T017 Extend catalog port methods for retry eligibility and cancellation in
  `src/openardp/ports/catalog.py`.
- [x] T018 Implement eligibility-aware creation/claim/fail projection and idempotent
  matching in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T019 Implement queued/running cancellation request and fenced acknowledgement in
  `src/openardp/adapters/sqlite_catalog.py`.
- [x] T020 Implement cancellation-aware lease recovery and exact body-free events in
  `src/openardp/adapters/sqlite_catalog.py`.
- [x] T021 Run focused generic job/migration tests and record transition/count evidence.

**Checkpoint**: Revision 9 preserves every old job fact and supports fully fenced,
durable eligibility/cancellation independently of watcher code.

## Phase 3 — Pure watcher contract and safe scanner (US1, US4)

**Goal**: Define deterministic watch facts and admit/scan only explicit local authority.

### Tests

- [x] T022 [P] Add failing config, fingerprint, relative-locator, root and observation
  invariant tests in `tests/domain/test_watcher.py`.
- [x] T023 [P] Add failing root/config/locator/observation/job identity golden vectors in
  `tests/domain/test_watcher.py` and fixtures.
- [x] T024 [P] Add failing retry schedule, event shape and cycle-result tests in
  `tests/domain/test_watcher.py`.
- [x] T025 [P] Add runtime protocol conformance tests in
  `tests/contract/test_watcher_ports.py`.
- [x] T026 [P] Add scanner tests for empty/nonrecursive/recursive/sorted/supported-file
  results in `tests/integration/test_local_watch.py`.
- [x] T027 [P] Add scan overflow, depth, root replacement, disappearing entry and device
  boundary tests in `tests/integration/test_local_watch.py`.
- [x] T028 [P] Add path escape, symlink/junction, overlap, hostile-name, UNC/device and
  redaction tests in `tests/security/test_watcher_boundaries.py`.

### Implementation

- [x] T029 Implement closed watcher models, identities and retry policy in
  `src/openardp/domain/watcher.py` and domain exports.
- [x] T030 Define scanner, watcher catalog and ingestion runner protocols plus stable
  exceptions in `src/openardp/ports/watcher.py` and exports.
- [x] T031 Implement explicit root admission, component/device/workspace checks and
  private path normalization in `src/openardp/adapters/local_watch.py`.
- [x] T032 Implement deterministic bounded `os.scandir` traversal and complete/
  incomplete scan results in `src/openardp/adapters/local_watch.py`.
- [x] T033 Run focused watcher domain/scanner/security tests and record path-boundary
  evidence.

**Checkpoint**: A scanner can return only complete bounded safe metadata facts or an
empty incomplete result; it cannot expand authority or expose content.

## Phase 4 — Durable watcher catalog and scheduling (US1, US2, US4)

**Goal**: Reconcile complete scans into persistent stability, tombstones and one target/job.

### Tests

- [x] T034 [P] Extend migration tests with exact watcher tables/indexes/constraints and
  populated revision-8 fact preservation.
- [x] T035 [P] Add root registration/idempotency/config-conflict and row-fingerprint
  tests in `tests/integration/test_watcher_catalog.py`.
- [x] T036 [P] Add candidate/change/stable scheduling-boundary tests with injected UTC
  in `tests/integration/test_watcher_catalog.py`.
- [x] T037 [P] Add 100-repeat and twenty-client job/target deduplication convergence
  tests in `tests/integration/test_watcher_catalog.py`.
- [x] T038 [P] Add delete, rename-hint, hard-link ambiguity and reappearance lifecycle
  tests in `tests/integration/test_watcher_catalog.py`.
- [x] T039 [P] Add incomplete/overflow zero-partial-mutation and complete-scan
  backpressure/rescan recovery tests in `tests/integration/test_watcher_catalog.py`.
- [x] T040 [P] Add transaction fault injection around root, observation, tombstone,
  job, target and event writes in `tests/integration/test_watcher_catalog.py`.
- [x] T041 [P] Add event allowlist and private path/filename/token absence tests in
  `tests/security/test_watcher_boundaries.py`.

### Implementation

- [x] T042 Add revision-9 watcher STRICT tables/indexes and structural expectations in
  `sqlite_migrations.py` and `sqlite_catalog.py`.
- [x] T043 Implement root registration/get and exact conflict handling in
  `src/openardp/adapters/sqlite_catalog.py`.
- [x] T044 Implement complete/incomplete scan reconciliation, generation and stability
  transitions in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T045 Implement tombstone/reappearance/unique rename-hint logic without deleting
  evidence in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T046 Implement transactional capacity check plus generic job/target creation and
  deterministic convergence in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T047 Implement watcher target/event/list projections with fingerprint verification
  in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T048 Include watcher schema/reachability truth in catalog diagnostics and repository
  validation without treating paths as object roots.
- [x] T049 Run focused catalog concurrency/fault/migration/security tests and record
  exact counts.

**Checkpoint**: Complete scans atomically converge to persistent observations,
tombstones and bounded exact jobs; incomplete scans cannot corrupt truth.

## Phase 5 — Foreground worker and cycle orchestration (US1, US2, US3)

**Goal**: Recover, scan, schedule and run bounded jobs through existing ingestion.

### Tests

- [x] T050 [P] Add failing one-cycle recovery/scan/schedule/no-job service tests in
  `tests/integration/test_watcher_service.py`.
- [x] T051 [P] Add text ingestion/cache-hit and configured rich-runner reuse tests in
  `tests/integration/test_watcher_service.py`.
- [x] T052 [P] Add target reconstruction, observation-race, source disappearance and
  unsupported/permanent failure classification tests.
- [x] T053 [P] Add retry timing, exhaustion, backpressure drain and restart convergence
  tests in `tests/integration/test_watcher_service.py`.
- [x] T054 [P] Add cancellation-before-run, running-request checkpoint, post-commit race
  and stale-completion tests in `tests/integration/test_watcher_service.py`.
- [x] T055 [P] Add clock rollback, interruptible continuous loop and no-wall-sleep tests
  in `tests/integration/test_watcher_service.py`.
- [x] T056 [P] Add service log/event path/body/error/token redaction and no-network tests
  in `tests/security/test_watcher_boundaries.py`.

### Implementation

- [x] T057 Implement `WatcherService` cycle ordering, injected clock/sleeper/token/
  owner factories and bounded processing in `src/openardp/services/watcher.py`.
- [x] T058 Implement safe target reconstruction/revalidation and generic lease lifecycle
  in `src/openardp/services/watcher.py`.
- [x] T059 Implement stable failure taxonomy, deterministic delayed retry and terminal
  classification in `src/openardp/services/watcher.py`.
- [x] T060 Implement cancellation polling/acknowledgement checkpoints and cancellation-
  wins fencing in `src/openardp/services/watcher.py`.
- [x] T061 Adapt existing text and rich ingestion composition behind the watcher runner
  without changing parser/source/representation identities.
- [x] T062 Add optional cancellation callbacks at safe ingestion orchestration
  checkpoints where needed, with complete regression tests.
- [x] T063 Run focused end-to-end cycle/restart/cancellation/rich/text evidence and
  record exact results.

**Checkpoint**: One foreground cycle safely converges stable changes through existing
ingestion, recovery, retry and cancellation with bounded work.

## Phase 6 — CLI and operational truth (US4)

- [x] T064 [P] Add failing parser/help/usage tests for `watch`, `jobs` and `job-cancel`
  in `tests/integration/test_watcher_cli.py`.
- [x] T065 [P] Add one-cycle candidate/stable/success JSON/human envelope tests.
- [x] T066 [P] Add continuous interrupt, invalid root/overlap, rich configuration,
  inspection/cancellation and redacted error tests.
- [x] T067 Implement bounded watcher CLI arguments and explicit composition in
  `src/openardp/interfaces/cli.py`.
- [x] T068 Implement body-free job list/cancel projections and error mapping in
  `src/openardp/interfaces/cli.py`.
- [x] T069 Validate every planned quickstart command on a fresh disjoint workspace and
  correct `quickstart.md` to actual syntax/output.

## Phase 7 — Documentation, compatibility and full convergence

- [x] T070 [P] Update `docs/02_ARCHITECTURE.md` and
  `docs/03_DATA_MODEL_AND_PACKAGE.md` with polling reconciliation, job state and
  revision-9 facts.
- [x] T071 [P] Update `docs/06_SECURITY_MODEL_V2.md` and
  `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md` with path, redaction, retry,
  cancellation, recovery and network-share boundaries.
- [x] T072 [P] Update `docs/08_ROADMAP_AND_GOVERNANCE.md`,
  `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md` and
  `docs/11_OPERATIONAL_AND_ENTERPRISE_REQUIREMENTS.md` with status and version axes.
- [x] T073 [P] Update `README.md`, `START_HERE.md`, `CHANGELOG.md`, `VALIDATION.md` and
  `specs/README.md` with delivered commands, limitations and F012 status.
- [x] T074 Freeze all prior public schemas/fixtures/MCP descriptors/parser/visual/export
  profiles and prove `pyproject.toml`/`uv.lock` unchanged.
- [x] T075 Run focused compatibility, repository-contract and isolated wheel smoke tests.
- [x] T076 Complete `implementation-notes.md` with FR/SC/task traceability, exact
  metrics, fault/concurrency evidence, tradeoffs, residual risks and rollback.
- [x] T077 Run Ruff check/format, strict mypy, full network-disabled pytest, build,
  schema, evidence and repository validation gates.
- [x] T078 Execute final read-only Spec Kit convergence across specification, plan,
  tasks, constitution, code, tests, migration, ADR, CLI and docs.
- [x] T079 Append and complete any convergence task required by a real gap; rerun every
  affected focused and complete gate.
- [x] T080 Mark specification/tasks complete only after zero unresolved convergence
  findings and record final local evidence.
- [x] T081 Commit F012 as one bounded feature, push, open PR and require green Linux,
  macOS and Windows CI.
- [x] T082 Merge F012 only after final PR-head CI, verify post-merge `main` CI on all
  three platforms, delete the remote branch and return the worktree to clean main.

## Dependencies and execution order

- Phase 2 precedes watcher persistence because migration 9 owns both job and watcher
  constraints.
- Phase 3 pure models/scanner can proceed independently after governance baseline.
- Phase 4 requires Phases 2-3 and precedes service orchestration.
- Phase 5 requires catalog transactions and existing ingestion services.
- Phase 6 requires the stable service contract.
- Phase 7 completes only after all story checkpoints pass.

## Traceability summary

| Requirements | Primary tasks |
|---|---|
| FR-001–FR-005, FR-026 | T022–T033, T064–T069 |
| FR-006–FR-013 | T022–T049, T050–T063 |
| FR-014–FR-019 | T006–T021, T050–T063, T068 |
| FR-020–FR-023 | T034–T049, T053, T056, T070–T073 |
| FR-024–FR-025 | T055, T064–T069 |
| FR-027–FR-030 | T070–T082 |

Every FR and SC has an executable task. No task expands into F013-F017.

## Phase 8: Convergence

- [x] T083 Reject relative and lexically non-canonical operator root paths before
  traversal, with CLI/adapter regression coverage, per FR-001 and US4/AC1 (contradicts).
- [x] T084 Count every enumerated filesystem entry against `max_entries` and prove the
  exact 1,001-entry overflow, zero-partial-mutation and reduced-root convergence path
  per FR-005 and SC-003 (partial).
- [x] T085 Prove all configured retry eligibility instants through exhaustion and 100
  consecutive pre-eligibility claims returning no lease per SC-004 (partial).
- [x] T086 Add a twenty-client running-cancellation race with deterministic single
  request/finalization evidence and stale renew/complete/fail fencing per SC-005 (partial).
- [x] T087 Add restart convergence coverage for candidate, delayed queued job, expired
  active lease, rescan/backpressure and tombstone durable states per SC-006 and FR-019
  (partial).
- [x] T088 Exercise source disappearance and observation replacement through the
  foreground service, proving retry rather than stale success per US1/AC3 and T052
  (partial).
- [x] T089 Inject failures around watcher success, retry, failure, cancellation and
  expired-lease outcome-event publication and prove atomic prior-or-complete state per
  FR-021 and T040 (partial).
- [x] T090 Fault migration 9 at every executable statement boundary and prove exact
  revision-8 rollback before a clean revision-9 retry per SC-009 (partial).
- [x] T091 Add a standalone cross-platform delete/reappearance lifecycle test that does
  not depend on hard-link support per SC-007 (partial).
- [x] T092 Preserve the persisted attempt count when cancelling a retried queued job and
  add exact event-projection regression coverage per FR-023 (contradicts).
