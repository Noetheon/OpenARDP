---

description: "Implementation tasks for incremental freshness status"
---

# Tasks: Incremental Freshness Status

**Input**: Design documents from `/specs/021-incremental-freshness/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/status-contract.md, ADR 0017

**Tests**: Behavioral and contract tests are written before their corresponding implementation. Performance claims require
committed raw evidence plus an independent validator.

**Organization**: Tasks follow the four independently testable user stories and are executed sequentially for F021.

## Phase 1: Setup and Frozen Decisions

**Purpose**: Freeze assurance semantics and benchmark inputs before production code changes.

- [x] T001 Record accepted coverage and mode semantics in docs/adr/0017-freshness-integrity-coverage.md
- [x] T002 Freeze the F021 status contract in specs/021-incremental-freshness/contracts/status-contract.md
- [x] T003 Freeze benchmark scales, sample policy, counters and F020 baselines in benchmarks/freshness/v0.1.0/protocol.json
- [x] T004 Validate feature requirements with specs/021-incremental-freshness/checklists/freshness-assurance.md

---

## Phase 2: Foundational Domain and Catalog Boundary

**Purpose**: Add the closed vocabulary and self-consistent header snapshot required by every story.

**Critical**: User-story implementation starts only after the domain and catalog boundary pass focused tests.

- [x] T005 [P] Add failing coverage-vocabulary and shape tests in tests/domain/test_ingestion.py
- [x] T006 [P] Add catalog snapshot shape tests in tests/integration/test_ingestion_catalog.py
- [x] T007 Add atomic SQLite snapshot and no-projection-load tests in tests/integration/test_ingestion_catalog.py and tests/integration/test_document_query.py
- [x] T008 Add IntegrityCoverage, StatusMode and DocumentStatusSnapshot models in src/openardp/domain/ingestion.py
- [x] T009 Export the new domain vocabulary through src/openardp/domain/__init__.py
- [x] T010 Extend the Catalog protocol with the atomic status snapshot in src/openardp/ports/catalog.py
- [x] T011 Implement the transactionally consistent header-only snapshot in src/openardp/adapters/sqlite_catalog.py and src/openardp/adapters/sqlite_document_queries.py
- [x] T012 Run focused domain and SQLite catalog tests and record the result in specs/021-incremental-freshness/implementation-notes.md

**Checkpoint**: A READY document can be described from one catalog snapshot without materializing blocks.

---

## Phase 3: User Story 1 - Fast Exact Freshness (Priority: P1)

**Goal**: Return exact source freshness without work proportional to prepared block count.

**Independent Test**: Status for 10k and 100k READY heads hashes the source, loads no block projections or bodies and
detects a same-size/same-mtime byte edit.

### Tests for User Story 1

- [x] T013 [P] [US1] Add failing default-current and same-metadata-change tests in tests/integration/test_document_query.py
- [x] T014 [P] [US1] Add failing missing, unregistered, unprepared and non-local tests in tests/integration/test_document_query.py
- [x] T015 [US1] Add failing operation-spy tests proving zero parser, projection and verifier calls in tests/integration/test_document_query.py
- [x] T016 [US1] Add concurrent-head consistency test in tests/integration/test_ingestion_catalog.py

### Implementation for User Story 1

- [x] T017 [US1] Replace aggregate loading with the atomic header snapshot in src/openardp/services/document_query.py
- [x] T018 [US1] Project explicit NONE or HEAD coverage for every default outcome in src/openardp/services/document_query.py
- [x] T019 [US1] Preserve exact SHA-256 source inspection and sanitized closed failures in src/openardp/services/document_query.py
- [x] T020 [US1] Run the User Story 1 focused tests and document exact commands in specs/021-incremental-freshness/implementation-notes.md

**Checkpoint**: Default freshness is exact, coverage-explicit and independent of prepared block count.

---

## Phase 4: User Story 2 - Explicit Full Integrity (Priority: P1)

**Goal**: Retain the exhaustive verifier through deliberate service and CLI selection.

**Independent Test**: Full mode reports FULL only after success and detects injected native, manifest, projection and
block corruption while default mode makes no complete-integrity claim.

### Tests for User Story 2

- [x] T021 [P] [US2] Add failing full-mode success and coverage tests in tests/integration/test_document_query.py
- [x] T022 [US2] Add failing native, manifest, projection and block corruption matrix in tests/integration/test_document_query.py
- [x] T023 [US2] Add source/evidence immutability assertions in tests/integration/test_document_query.py and the F021 benchmark

### Implementation for User Story 2

- [x] T024 [US2] Route explicit full mode through the existing complete verifier in src/openardp/services/document_query.py
- [x] T025 [US2] Prevent FULL coverage on any incomplete or failed verification in src/openardp/services/document_query.py
- [x] T026 [US2] Run the User Story 2 corruption and immutability suite and update specs/021-incremental-freshness/implementation-notes.md

**Checkpoint**: Fast freshness and exhaustive integrity are separate, honest and independently testable.

---

## Phase 5: User Story 3 - Interface and Failure Safety (Priority: P1)

**Goal**: Expose deterministic coverage through CLI and MCP while keeping MCP bounded.

**Independent Test**: Service, CLI and MCP serialize one vocabulary; CLI can explicitly request full verification; MCP
cannot accept a path or request full verification.

### Tests for User Story 3

- [x] T027 [P] [US3] Add failing CLI JSON/human default and --full-integrity golden tests in tests/integration/test_cli.py
- [x] T028 [P] [US3] Add failing MCP coverage and unchanged-input-schema tests in tests/integration/test_mcp_server.py
- [x] T029 [US3] Add sanitized-output and non-local failure tests across tests/integration/test_document_query.py, tests/integration/test_cli.py and tests/integration/test_mcp_server.py

### Implementation for User Story 3

- [x] T030 [US3] Add deliberate --full-integrity status selection and coverage output in src/openardp/interfaces/cli.py
- [x] T031 [US3] Add bounded default coverage projection without a full-mode input in src/openardp/interfaces/mcp_server.py
- [x] T032 [US3] Update interface golden tests and contract documentation in tests/integration and specs/021-incremental-freshness/contracts/status-contract.md
- [x] T033 [US3] Run service, CLI and MCP focused tests and update specs/021-incremental-freshness/implementation-notes.md

**Checkpoint**: All interfaces are vocabulary-compatible, body-free and capability-bounded.

---

## Phase 6: User Story 4 - Reproducible Optimization Evidence (Priority: P2)

**Goal**: Publish independently validated before/after evidence on the frozen F020 scales.

**Independent Test**: A fresh offline run retains all raw samples and counters; a separate validator recomputes every
summary, policy result, hash and report byte.

### Tests for User Story 4

- [x] T034 [P] [US4] Add failing benchmark protocol and deterministic-report tests in tests/integration/test_freshness_benchmark.py
- [x] T035 [P] [US4] Add failing tamper, sample-count, privacy and drift tests in tests/test_freshness_benchmark_drift.py
- [x] T036 [US4] Add failing counter tests for zero default projection/verifier work and explicit full work in tests/integration/test_freshness_benchmark.py

### Implementation for User Story 4

- [x] T037 [US4] Implement frozen observations, aggregation, policy and deterministic reporting in scripts/freshness_benchmark.py
- [x] T038 [US4] Implement the isolated offline runner and operation instrumentation in scripts/run_freshness_benchmark.py
- [x] T039 [US4] Implement independent recomputation, artifact hashing and privacy validation in scripts/validate_freshness_benchmark.py
- [x] T040 [US4] Execute the decision-bearing 10k/100k benchmark and publish artifacts under benchmarks/freshness/v0.1.0/results/reference-macos-arm64/
- [x] T041 [US4] Validate committed evidence from scratch and record target result, improvement and limitations in specs/021-incremental-freshness/implementation-notes.md

**Checkpoint**: F021 has an honest, reproducible performance result rather than an inferred complexity claim.

---

## Phase 7: Documentation, Validation and Convergence

**Purpose**: Integrate the bounded result without rewriting historical decisions and prove repository-wide readiness.

- [x] T042 [P] Update feature navigation and roadmap status in specs/README.md and spec-kit/FEATURE_MAP.md
- [x] T043 [P] Document status modes and measured result in README.md, CHANGELOG.md, VALIDATION.md and docs/19_PRODUCT_VALUE_BENCHMARK.md
- [x] T044 Add final traceability and tradeoffs to specs/021-incremental-freshness/implementation-notes.md and specs/021-incremental-freshness/analysis.md
- [x] T045 Run uv run ruff check . and uv run ruff format --check .
- [x] T046 Run uv run mypy src and uv run pytest with branch-aware coverage
- [x] T047 Run repository, benchmark, build, pre-commit and git diff --check gates from specs/021-incremental-freshness/quickstart.md
- [x] T048 Run the Spec Kit convergence audit, resolve every blocking finding and mark all completed tasks in specs/021-incremental-freshness/tasks.md
- [x] T049 Commit F021 as one bounded feature, push a private-remote branch and require green Linux/macOS/Windows checks before merge

---

## Dependencies and Execution Order

### Phase Dependencies

- Phase 1 freezes semantics before code or measurements.
- Phase 2 depends on Phase 1 and blocks all user stories.
- User Story 1 depends on Phase 2.
- User Story 2 depends on User Story 1's request shape but remains independently selectable and testable.
- User Story 3 depends on the service semantics established by User Stories 1 and 2.
- User Story 4 depends on production behavior and counters from User Stories 1 through 3.
- Phase 7 depends on all user stories and the committed benchmark result.

### Within Each User Story

- Add contract and negative tests first and observe the relevant failures.
- Implement the smallest production change that satisfies those tests.
- Run the story checkpoint before starting the next story.
- Preserve the original F020 evidence and release decision throughout.

### Parallel Opportunities

- `[P]` marks files whose authoring has no write dependency, but F021 is intentionally executed sequentially by one
  maintainer.
- Cross-platform CI jobs may run concurrently only after all local gates pass.

## Implementation Strategy

1. Freeze the vocabulary and header snapshot.
2. Land exact bounded freshness as the independently useful core.
3. Restore complete verification as an explicit mode and then expose interfaces.
4. Measure both paths on the frozen scales with non-timing counters.
5. Converge and merge F021 before opening storage-amplification work in F022.

## Notes

- A checked task means its implementation or evidence exists and its focused validation passed.
- Timing targets are never waived because of environment variability; non-reference runs are labeled non-binding.
- No F022-F025 implementation belongs in this branch.
