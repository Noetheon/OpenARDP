# Tasks: Context Compiler and Selection Receipts

**Input**: Design documents from `/specs/008-context-compiler-receipts/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/selection-receipt.md`, `quickstart.md`

**Tests**: Mandatory and authored before behavior/contract implementation where
practical. Unit tests run without network.

**Organization**: Dependency-ordered and grouped by independently testable user story.
F008 ends at deterministic local compilation/receipt CLI behavior and does not implement
MCP, model ranking, visual extraction, derivation DAG, watcher or export behavior.

## Phase 1: Baseline and Contract Freeze

**Purpose**: Freeze F007 compatibility and make the additive contract boundary explicit.

- [x] T001 Record base commit, Python/source/test counts and all nine schema/two vector hashes in `specs/008-context-compiler-receipts/implementation-notes.md`
- [x] T002 Run and record the locked F007 Ruff, format, native/Windows mypy, full pytest, schema, conformance, repository and build baseline in `specs/008-context-compiler-receipts/implementation-notes.md`
- [x] T003 [P] Add failing package/surface tests for provider-free context imports and unchanged Docling laziness in `tests/test_package.py`
- [x] T004 [P] Add failing byte-freeze tests for all nine F007 schemas, both established vector files and F006 corpus in `tests/test_repository_contract.py`
- [x] T005 Confirm the additive receipt contract requires no ADR and record compatibility/source-of-truth reasoning in `specs/008-context-compiler-receipts/research.md`
- [x] T006 Run the Phase 1 focused red/green contract-freeze tests and record exact evidence in `specs/008-context-compiler-receipts/implementation-notes.md`

**Checkpoint**: F007 behavior/artifacts are frozen; only a new experimental receipt root
and workspace revision may be added.

---

## Phase 2: Foundational Domain, Contract and Ports

**Purpose**: Define strict provider-neutral inputs, outputs, identities and boundaries
before retrieval or persistence.

### Tests first

- [x] T007 [P] Add failing request/policy/limit/snapshot/candidate invariant tests in `tests/domain/test_context_compilation.py`
- [x] T008 [P] Add failing budget-ledger/decision-partition/privacy invariant tests in `tests/domain/test_context_compilation.py`
- [x] T009 [P] Add failing receipt version/identity/policy-digest/canonicalization tests in `tests/domain/test_context_compilation.py`
- [x] T010 [P] Add failing estimator/candidate-source/context-catalog structural protocol tests in `tests/contract/test_context_ports.py`
- [x] T011 [P] Add failing valid/invalid raw JSON and schema parity tests for ContextBundle `0.2.0` and SelectionReceipt `0.1.0` in `tests/domain/test_models.py` and `tests/contract/test_context_schemas.py` (per-contract schema-generation convention; no `tests/test_schema_generation.py` exists)
- [x] T012 [P] Add failing golden bundle/receipt fixtures and independent identity-vector tests under `tests/fixtures/context/` and `tests/domain/test_identity_vectors.py`

### Implementation

- [x] T013 Implement strict limits, estimator identity, policy, request, snapshot, candidate, ledger, discriminated block/projection ContextBundle `0.2.0`, decision, receipt and compilation models in `src/openardp/domain/context_compilation.py`
- [x] T014 Implement domain-separated policy/receipt identities and deterministic ContextBundle UUID projection in `src/openardp/domain/identity.py` and `src/openardp/domain/context_compilation.py`
- [x] T015 Export intentional receipt/compilation domain symbols without provider imports in `src/openardp/domain/__init__.py`
- [x] T016 Define narrow estimator and two-source candidate protocols plus typed cancellation/failure taxonomy in `src/openardp/ports/context.py`
- [x] T017 Extend catalog ports additively with compilation commit/load/list and snapshot shapes in `src/openardp/ports/catalog.py` and `src/openardp/ports/__init__.py`
- [x] T018 Add ContextBundle `0.2.0` and SelectionReceipt `0.1.0` to deterministic schema generation and commit schemas/fixtures/vectors in `scripts/generate_schemas.py`, `schemas/context-bundle-0.2.0.schema.json`, `schemas/selection-receipt.schema.json` and `tests/fixtures/context/`
- [x] T019 Run all foundational model/contract/schema tests plus Ruff, format and strict mypy and record results in `specs/008-context-compiler-receipts/implementation-notes.md`

**Checkpoint**: Receipt, request and compiler boundaries are strict, versioned and fully
provider-neutral; no retrieval or storage behavior is implied by models.

---

## Phase 3: User Story 1 — Compile Bounded Evidence (Priority: P1) 🎯 MVP

**Goal**: Resolve a mixed exact corpus, discover/verify deterministic lexical evidence
and produce a budget-safe bundle plus complete receipt.

**Independent Test**: Compile a synthetic text/rich corpus under a small byte/token
budget; prove exact scopes, deterministic order, untrusted delimiters, honest missing
evidence and zero overflow/network/provider invocation.

### Tests first

- [x] T020 [P] [US1] Add failing exact byte/character/conservative-token estimator and fixed-point accounting tests in `tests/unit/test_context_estimators.py`
- [x] T021 [P] [US1] Add failing text FTS coverage/discovery/full-body verification/rescoring tests in `tests/unit/test_context_candidates.py`
- [x] T022 [P] [US1] Add failing accepted-rich projection scan/body-verification/bound tests in `tests/unit/test_context_candidates.py`
- [x] T023 [P] [US1] Add failing mixed-source total-order/dedup/high-value classification tests in `tests/unit/test_context_candidates.py`
- [x] T024 [P] [US1] Add failing snapshot-resolution/mixed compilation/exact-fit/one-unit-overflow tests in `tests/integration/test_context_compiler.py`
- [x] T025 [P] [US1] Add failing numeric/verification/visual missing-evidence and injection-delimiter tests in `tests/security/test_context_boundaries.py`

### Implementation

- [x] T026 [P] [US1] Implement exact byte, scalar-character and conservative UTF-8 token estimators in `src/openardp/adapters/context_estimators.py`
- [x] T027 [US1] Implement FTS-backed verified text candidate discovery with integer rescoring in `src/openardp/adapters/context_candidates.py`
- [x] T028 [US1] Implement bounded provider-free F007 rich candidate scanning and exact body verification in `src/openardp/adapters/context_candidates.py`
- [x] T029 [US1] Implement exact head snapshot resolution, candidate merge/dedup and deterministic total order in `src/openardp/services/context_compiler.py`
- [x] T030 [US1] Implement policy classification, stale/rejected partitioning and high-value/missing-evidence rules in `src/openardp/services/context_compiler.py`
- [x] T031 [US1] Implement delimited data-only EvidenceItem construction and visual-escalation notices in `src/openardp/services/context_compiler.py`
- [x] T032 [US1] Implement fixed-point canonical ContextBundle measurement, budget admission and receipt construction in `src/openardp/services/context_compiler.py`
- [x] T033 [US1] Export intentional estimator/candidate/compiler surfaces lazily in `src/openardp/adapters/__init__.py` and `src/openardp/services/__init__.py`
- [x] T034 [US1] Run the User Story 1 independent suite, 20-repeat determinism probe and network/provider-import assertions and record exact evidence in `specs/008-context-compiler-receipts/implementation-notes.md`

**Checkpoint**: A pure, non-persisted mixed context result is deterministic, honest,
data-only and exactly within budget.

---

## Phase 4: User Story 2 — Explain, Persist and Replay Selection (Priority: P2)

**Goal**: Make bundle/receipt objects immutable and reachable, inspect them body-free and
replay exact snapshots with byte-identical output.

**Independent Test**: Persist one compilation, load/verify its receipt, repeat/replay five
times and prove identical objects/IDs; change heads but retain exact history and prove
replay stays pinned.

### Tests first

- [x] T035 [P] [US2] Add failing migration-6 upgrade/checksum/gap/rollback/schema-drift tests in `tests/integration/test_sqlite_catalog.py`
- [x] T036 [P] [US2] Add failing atomic compilation commit/load/idempotency/conflict/scope/reachability tests in `tests/integration/test_context_catalog.py`
- [x] T037 [P] [US2] Add failing row/object/canonical/identity/count/scope tamper tests in `tests/integration/test_context_catalog.py`
- [x] T038 [P] [US2] Add failing stable repeat/replay/head-change and task/algorithm/estimator/policy mismatch tests in `tests/integration/test_context_compiler.py`
- [x] T039 [P] [US2] Add failing privacy scans proving task/body/path absence from receipt rows/JSON/logs in `tests/security/test_context_boundaries.py`

### Implementation

- [x] T040 [US2] Add checksummed workspace migration 6 for immutable compilation and exact scope rows in `src/openardp/adapters/sqlite_migrations.py`
- [x] T041 [US2] Implement atomic compilation commit/load/list with canonical row fingerprints and exact idempotency in `src/openardp/adapters/sqlite_catalog.py`
- [x] T042 [US2] Integrate receipt/bundle objects and compilation scopes into catalog schema validation and reachability roots in `src/openardp/adapters/sqlite_catalog.py` and `src/openardp/services/reachability.py`
- [x] T043 [US2] Implement complete receipt/bundle/row/scope/evidence verification before load or return in `src/openardp/services/context_compiler.py`
- [x] T044 [US2] Implement CAS publication, atomic catalog orchestration, exact result reuse and unreachable-object failure semantics in `src/openardp/services/context_compiler.py`
- [x] T045 [US2] Implement exact task-supplied replay with algorithm/estimator/policy checks and byte-identical convergence in `src/openardp/services/context_compiler.py`
- [x] T046 [US2] Run User Story 2 migration/persistence/privacy/replay tests and record exact results in `specs/008-context-compiler-receipts/implementation-notes.md`

**Checkpoint**: Every compilation is immutable, body-free-auditable, exact-snapshot
replayable and fully verified before return.

---

## Phase 5: User Story 3 — Fail Closed on Integrity and Lifecycle Faults (Priority: P3)

**Goal**: Guarantee sanitized cancellation/failure behavior and zero partial
catalog-visible compilation.

**Independent Test**: Fault every discovery, verification, publication and commit phase,
cancel at bounded checkpoints and prove no partial result, leakage or mutation of prior
valid compilations.

### Tests first

- [x] T047 [P] [US3] Add failing index incomplete/orphan/drift and explicit-rebuild-only tests in `tests/security/test_context_boundaries.py`
- [x] T048 [P] [US3] Add failing CAS body/receipt/bundle corruption and scope/trust-promotion tests in `tests/security/test_context_boundaries.py`
- [x] T049 [P] [US3] Add failing discovered/candidate/body/decision/bundle/corpus resource-limit tests in `tests/security/test_context_boundaries.py`
- [x] T050 [P] [US3] Add failing before-retrieval/during-verification/post-CAS/pre-commit cancellation tests in `tests/integration/test_context_compiler.py`
- [x] T051 [P] [US3] Add failing CAS publish/disk/catalog commit/retry and prior-result immutability tests in `tests/integration/test_context_compiler.py`
- [x] T052 [P] [US3] Add failing error/log body-task-path-traceback redaction tests in `tests/security/test_context_boundaries.py`

### Implementation

- [x] T053 [US3] Enforce candidate discovery, object and output limits before unbounded allocation in `src/openardp/adapters/context_candidates.py` and `src/openardp/services/context_compiler.py`
- [x] T054 [US3] Add bounded cancellation checkpoints and sanitized failure mapping without durable job semantics in `src/openardp/services/context_compiler.py`
- [x] T055 [US3] Harden publication/commit rollback and retry convergence for every fault point in `src/openardp/services/context_compiler.py` and `src/openardp/adapters/sqlite_catalog.py`
- [x] T056 [US3] Add body-free structured operational logging and default diagnostic redaction in `src/openardp/services/context_compiler.py`
- [x] T057 [US3] Run the complete User Story 3 hostile-path matrix and record exact zero-partial/leakage evidence in `specs/008-context-compiler-receipts/implementation-notes.md`

**Checkpoint**: Unsafe accelerators/evidence, resource excess, cancellation and storage
faults fail closed without partial results or sensitive diagnostics.

---

## Phase 6: User Story 4 — Stable Local CLI Workflows (Priority: P4)

**Goal**: Expose bounded compile, replay and receipt inspection through existing stable
CLI envelopes.

**Independent Test**: Run context/receipt JSON and human flows in a fresh mixed workspace
for success, no-match, tiny budget, replay mismatch, corruption and usage errors while
prior CLI snapshots remain unchanged.

### Tests first

- [x] T058 [P] [US4] Add failing parser/help/context/context-receipt JSON/human contract tests in `tests/integration/test_cli_context.py`
- [x] T059 [P] [US4] Add failing CLI no-match/tiny-budget/mismatch/corruption/cancellation and body-redaction tests in `tests/integration/test_cli_context.py`
- [x] T060 [P] [US4] Add regression assertions for all existing text/rich/search/evidence JSON and human outputs in `tests/integration/test_cli_context.py`

### Implementation

- [x] T061 [US4] Add bounded `context` arguments, document scope, budget/unit/mode/replay and explicit `--include-bundle` handling in `src/openardp/interfaces/cli.py`
- [x] T062 [US4] Add exact body-free `context-receipt` inspection and stable result summaries in `src/openardp/interfaces/cli.py`
- [x] T063 [US4] Map compilation mismatch/integrity/cancel/limit failures into existing sanitized envelopes in `src/openardp/interfaces/cli.py`
- [x] T064 [US4] Run User Story 4 and full prior CLI compatibility suites and record exact evidence in `specs/008-context-compiler-receipts/implementation-notes.md`

**Checkpoint**: Context compilation and receipt inspection are usable locally and provide
a stable application boundary for later read-only MCP wrapping.

---

## Phase 7: Documentation, Compatibility and Convergence

**Purpose**: Prove the complete feature, new contract, migration, packaging and prior
behavior before publication.

- [x] T065 Update install/context/replay/receipt/budget/privacy/current-truth guidance in `README.md`, `START_HERE.md` and `docs/13_STEP_BY_STEP_USER_GUIDE.md`
- [x] T066 [P] Update delivered architecture/data/security/operations context behavior in `docs/02_ARCHITECTURE.md`, `docs/03_DATA_MODEL_AND_PACKAGE.md`, `docs/05_CONTEXT_COMPILER_AND_MCP.md`, `docs/06_SECURITY_MODEL_V2.md` and `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md`
- [x] T067 [P] Update receipt contract status, schema matrix, changelog and validation history in `contracts/README.md`, `schemas/README.md`, `CHANGELOG.md` and `VALIDATION.md`
- [x] T068 Prove byte-for-byte no-diff against F007 for all nine earlier public schemas, both vector files and the F006 conformance corpus
- [x] T069 Run two consecutive bundle/receipt schema/fixture/vector generations and prove all new bytes deterministic
- [x] T070 Run Ruff, format, native/Windows strict mypy, full network-blocked suite, schema/conformance/repository validators, `git diff --check` and distribution builds
- [x] T071 Run fresh mixed quickstart, 20 repeats, five replays, head-change, exact-fit/overflow, no-match, visual-missing, corruption, cancellation and failure flows
- [x] T072 Verify core-only and rich isolated wheels import context surfaces without provider eager import and execute representative compiler/receipt CLI paths
- [x] T073 Finalize `specs/008-context-compiler-receipts/implementation-notes.md` with exact commands, counts, hashes, migration, tradeoffs, residual risks, rollback and remote placeholders
- [x] T074 Run final Spec Kit analysis and resolve every critical/high finding at its originating artifact
- [x] T075 Run Spec Kit convergence; append and implement any remaining tasks without rewriting completed tasks
- [x] T076 Mark F008 locally converged in `specs/008-context-compiler-receipts/spec.md` and `specs/README.md` only after all checks pass

---

## Dependencies & Execution Order

### Phase dependencies

- Baseline/contract freeze precedes every new public/runtime artifact.
- Foundational domain, identity and ports block all user stories.
- US1 provides pure compilation and is independently valuable.
- US2 depends on US1 output and adds persistence/replay.
- US3 hardens US1/US2 failure paths.
- US4 wraps the complete application service and preserves prior CLI behavior.
- Phase 7 closes public contract, compatibility and convergence evidence.

### Within each story

- Tests are written and observed failing before corresponding implementation where
  practical.
- Pure models/ports precede adapters; adapters precede orchestration; orchestration
  precedes CLI.
- SQLite migration precedes catalog operations; CAS objects precede atomic catalog commit.
- Existing files shared by tasks are edited sequentially even where test files differ.

### Parallel opportunities

- Baseline package and byte-freeze tests are independent.
- Foundational domain, protocol and schema tests are separate files.
- Estimator, text discovery, rich discovery and integration tests can be authored
  independently before implementation.
- Migration/catalog, replay and privacy tests can be authored independently.
- Documentation tasks on disjoint files can run in parallel after behavior freezes.

## Implementation Strategy

### MVP first

1. Freeze F007.
2. Complete strict receipt/request/port foundations.
3. Implement estimators and both verified lexical sources.
4. Complete US1 pure bounded compilation.
5. Validate independently before persistence or CLI.

### Incremental completion

1. Add atomic persistence and exact replay.
2. Harden every fault and cancellation phase.
3. Add CLI wrappers.
4. Prove compatibility, package boundaries and convergence.

### Rollback

Revert the isolated F008 implementation/merge commit before opening production
workspaces at revision 6. After migration/use, restore a revision-5 backup for older
software; never alter migration history or downgrade a live workspace in place.
