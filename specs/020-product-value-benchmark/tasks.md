# Tasks: Product Value Benchmark

**Input**: Design documents from `/specs/020-product-value-benchmark/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Mandatory and written before corresponding implementation because this feature creates decision-bearing
measurement and evidence behavior.

## Phase 1: Setup

**Purpose**: Register one isolated post-roadmap benchmark feature and freeze inputs before observing results.

- [x] T001 Add F020 to `spec-kit/FEATURE_MAP.md`, `spec-kit/feature-prompts/020-product-value-benchmark.md`, `specs/README.md` and `.specify/feature.json`
- [x] T002 Create frozen `benchmarks/product-value/v0.1.0/protocol.json`, `corpus-spec.json`, `judgments.json` and `value-policy.json`
- [x] T003 Update benchmark/documentation inventory rules in `scripts/validate_repository.py` and `tests/test_repository_contract.py`

---

## Phase 2: Foundational Evidence and Corpus Boundaries

**Purpose**: Establish closed records, identities, deterministic corpus generation and fail-closed publication used by
all user stories.

**Critical**: No measurement treatment starts until these foundations pass.

- [x] T004 [P] Add failing closed-model, identity, invalid-number and duplicate-observation tests in `tests/unit/test_product_benchmark.py`
- [x] T005 Implement benchmark evidence models and invariants in `src/openardp/domain/product_benchmark.py`
- [x] T006 [P] Add failing deterministic smoke/reference/scale corpus tests in `tests/unit/test_product_benchmark.py`
- [x] T007 Implement bounded corpus generation and manifest verification in `src/openardp/adapters/product_benchmarks.py`
- [x] T008 Add the thin corpus generation interface in `scripts/generate_product_benchmark.py`
- [x] T009 [P] Add failing atomic-publication, privacy and tamper tests in `tests/integration/test_product_benchmark.py`
- [x] T010 Implement exact input loading, privacy validation and atomic result publication in `scripts/product_benchmark_runner.py`

**Checkpoint**: Normative inputs are frozen and corpus/evidence identity behavior is independently testable.

---

## Phase 3: User Story 1 — Measure the Real Repeated-Use Value (Priority: P1)

**Goal**: Compare raw reparsing, persisted parsed/native reuse and OpenARDP reuse with one-time cost and break-even.

**Independent Test**: The smoke corpus produces comparable preparation/repeated-task samples, exact parser-call facts and
a recomputable break-even or `not-observed` result without using an external model.

### Tests

- [x] T011 [P] [US1] Add failing raw-reparse and persisted parsed-output reuse treatment tests in `tests/integration/test_product_benchmark.py`
- [x] T012 [P] [US1] Add failing preparation, repeated search and break-even integration tests in `tests/integration/test_product_benchmark.py`

### Implementation

- [x] T013 [US1] Implement raw text reparse and persisted parsed-output treatments in `scripts/product_benchmark_runner.py`
- [x] T014 [US1] Implement delivered text ingestion/search composition and measurement capture in `scripts/product_benchmark_runner.py`
- [x] T015 [US1] Implement comparable workload orchestration and break-even evaluation in `scripts/product_benchmark_runner.py`

**Checkpoint**: Repeated-use value and unfavorable baseline outcomes are measurable from raw evidence.

---

## Phase 4: User Story 2 — Validate Correctness at Useful Scale (Priority: P1)

**Goal**: Measure search, context and replay correctness/latency at 10,000 and 100,000 blocks.

**Independent Test**: Fixed unique judgments produce exact precision/recall/rank/anchor/coverage results in smoke mode,
and the same harness enforces the reference and scale block counts.

### Tests

- [x] T016 [P] [US2] Add failing percentile, MAD, bootstrap and sample-sufficiency tests in `tests/unit/test_product_benchmark.py`
- [x] T017 [P] [US2] Add failing exact search judgment and 100,000-block profile-boundary tests in `tests/unit/test_product_benchmark.py`
- [x] T018 [P] [US2] Add failing context-budget and byte-identical replay integration tests in `tests/integration/test_product_benchmark.py`

### Implementation

- [x] T019 [US2] Implement homogeneous summaries and deterministic uncertainty statistics in `scripts/product_benchmark_evaluation.py`
- [x] T020 [US2] Implement exact search correctness and scale workload measurements in `scripts/product_benchmark_runner.py`
- [x] T021 [US2] Implement bounded context, selected/native ratio and replay measurements in `scripts/product_benchmark_runner.py`

**Checkpoint**: Quality and performance remain jointly inspectable at both decision-bearing scales.

---

## Phase 5: User Story 3 — Measure Rich-Document Reuse Honestly (Priority: P1)

**Goal**: Exercise actual DOCX/PPTX/PDF provider parsing, native loading and OpenARDP unchanged reuse.

**Independent Test**: Committed rich fixtures yield measured available-format results and a closed unavailable PDF result
when no offline model bundle is supplied, with no substitute parser.

### Tests

- [x] T022 [P] [US3] Add failing rich fixture identity, capability and no-substitution tests in `tests/unit/test_product_benchmark.py`
- [x] T023 [P] [US3] Add real Docling cold/warm/native/OpenARDP full-run evidence and committed-result validation in `tests/integration/test_product_benchmark.py` and `tests/test_repository_contract.py`

### Implementation

- [x] T024 [US3] Implement real isolated Docling and persisted-native rich treatments in `scripts/product_benchmark_runner.py`
- [x] T025 [US3] Implement OpenARDP rich unchanged reuse, exact evidence and storage measurements in `scripts/product_benchmark_runner.py`
- [x] T026 [US3] Integrate rich completeness and stable unavailable reasons in `scripts/product_benchmark_evaluation.py`

**Checkpoint**: Rich reuse value is measured only for actual delivered provider capabilities.

---

## Phase 6: User Story 4 — Exercise Freshness, Change and Failure Boundaries (Priority: P1)

**Goal**: Prove warm reuse is current, edits are detected and partial or invalid evidence fails closed.

**Independent Test**: A deterministic fact edit transitions through changed freshness to a new current head, excludes the
old fact from current results and preserves original fixtures; injected evidence defects never yield a favorable result.

### Tests

- [x] T027 [P] [US4] Add failing unchanged identity, changed-source and reverted-source tests in `tests/integration/test_product_benchmark.py`
- [x] T028 [P] [US4] Add failing duplicate, missing, failed, non-finite, privacy-leaking and interrupted-run evidence tests in `tests/unit/test_product_benchmark.py`

### Implementation

- [x] T029 [US4] Implement freshness, warm re-ingest and deterministic source-edit workloads in `scripts/product_benchmark_runner.py`
- [x] T030 [US4] Implement complete-run validation, stale-safety aggregation and closed failure propagation in `scripts/product_benchmark_runner.py`

**Checkpoint**: No favorable measurement can arise from stale, invalid, partial or privacy-unsafe evidence.

---

## Phase 7: User Story 5 — Receive a Reproducible Worth-It Decision (Priority: P1)

**Goal**: Emit deterministic machine/human evidence and answer where the product is worthwhile.

**Independent Test**: A frozen synthetic observation set regenerates byte-identical summaries, decision and report;
changing a hard-safety observation produces `NOT_DEMONSTRATED`, while incomplete capability produces conditional value.

### Tests

- [x] T031 [P] [US5] Add failing three-state policy, stable-reason and F015 separation tests in `tests/unit/test_product_benchmark.py`
- [x] T032 [P] [US5] Add failing report determinism, unfavorable-result prominence and manifest drift tests in `tests/test_product_benchmark_drift.py`
- [x] T033 [P] [US5] Add failing maintainer-command smoke and exit-semantics tests in `tests/integration/test_product_benchmark.py`

### Implementation

- [x] T034 [US5] Implement frozen policy checks and three-state decision generation in `scripts/product_benchmark_evaluation.py`
- [x] T035 [US5] Implement deterministic JSON and Markdown projections in `scripts/product_benchmark_runner.py`
- [x] T036 [US5] Implement run/evaluate interface and sanitized status output in `scripts/run_product_benchmark.py`
- [x] T037 [US5] Implement independent evidence/drift validation in `scripts/validate_product_benchmark.py`

**Checkpoint**: One inspectable report answers the tested value question without changing release readiness.

---

## Phase 8: Reference Execution, Documentation and Quality

**Purpose**: Produce the actual evidence requested by the user and close all repository gates.

- [x] T038 Run focused F020 tests red-to-green and record exact commands/results in `specs/020-product-value-benchmark/implementation-notes.md`
- [x] T039 Execute the complete reference plus 100,000-block benchmark and commit sanitized raw evidence under `benchmarks/product-value/v0.1.0/results/reference-macos-arm64/`
- [x] T040 Independently validate and recompute the committed benchmark decision/report with `scripts/validate_product_benchmark.py`
- [x] T041 Update `README.md`, `docs/07_BENCHMARK_AND_EVIDENCE_PLAN.md`, `docs/07_TEST_AND_BENCHMARK_STRATEGY.md`, `VALIDATION.md` and `CHANGELOG.md` with measured facts and limitations
- [x] T042 Run Ruff check/format, strict mypy, complete offline pytest/coverage, build, pre-commit, repository validation and generator/report drift checks and record them in `specs/020-product-value-benchmark/implementation-notes.md`
- [x] T043 Reconcile both F020 checklists, write `analysis.md`, complete `implementation-notes.md`, run final convergence and close every task
- [x] T044 Commit one F020 feature, push it, open a private ready PR, verify Preflight plus all three platform jobs, merge through protected `main` and verify post-merge Preflight

---

## Dependencies and Execution Order

```text
Setup -> Foundations
          -> US1 comparisons
          -> US2 scale and correctness
          -> US3 rich formats
          -> US4 freshness/failure
          -> US5 decision/report
          -> actual full run -> docs -> full gates -> convergence -> protected publication
```

- US1 and US2 share treatment/evidence foundations and execute sequentially in the main implementation.
- US3 rich treatments are independently testable after foundations.
- US4 hardens evidence from all treatments and precedes any favorable decision.
- US5 consumes the validated outcomes of US1–US4.
- Tasks marked `[P]` affect independent test sections or files but still respect the preceding phase checkpoint.

## Parallel Examples

- T004, T006 and T009 can draft independent red tests before T005/T007/T010 implementation.
- T016–T018 cover statistics, search scale and context replay independently.
- T022 and T023 split closed capability logic from real-provider integration.
- T031–T033 split policy, deterministic projection and command behavior.

## Implementation Strategy

1. Make smoke evidence correct, closed and reproducible before measuring speed.
2. Add comparable text treatments and prove break-even calculations.
3. Scale the same behavior without special benchmark-only production paths.
4. Add rich provider cases and preserve unavailability honestly.
5. Freeze evaluation, then run once on the declared reference host.
6. Report the result as observed, including regressions, missed thresholds and limitations.

## Task Summary

- Total tasks: 44
- Setup/foundation: 10
- US1: 5
- US2: 6
- US3: 5
- US4: 4
- US5: 7
- Evidence/publication: 7
- Suggested MVP: Foundations plus US1 smoke comparison (T001–T015)
- Every task follows the required checkbox, ID, optional parallel marker, story label and file-path format.
