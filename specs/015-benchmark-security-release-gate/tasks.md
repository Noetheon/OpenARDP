# Tasks: Benchmark, Security and v0.1 Release Gate

**Input**: Design documents from `specs/015-benchmark-security-release-gate/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by the feature specification, Constitution Article VIII and the repository workflow. Test tasks precede implementation where practical.

**Organization**: Tasks are grouped by user story so each evidence slice remains independently reviewable and testable.

## Phase 1: Setup and frozen inputs

**Purpose**: Establish traceable feature artifacts and pre-result policy/corpus sources.

- [x] T001 Record the F015 acceptance criteria, exact authoritative inputs and initial rollback point in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T002 [P] Add the benchmark/release source registry and generated-artifact expectations to `specs/README.md`
- [x] T003 [P] Set candidate `0.1.0rc1`, add claim IDs/non-claims and freeze the source-tree allowlist in `pyproject.toml`, `benchmarks/release/v0.1.0/claim-policy.json` and `benchmarks/release/v0.1.0/source-tree-policy.json`
- [x] T004 Freeze the five-baseline protocol, metric/unit/statistics rules and resource ceilings in `benchmarks/release/v0.1.0/protocol.json`
- [x] T005 Freeze the binding thresholds, required suites/platforms and no-waiver rule in `benchmarks/release/v0.1.0/gate-policy.json`
- [x] T006 [P] Create the complete locked-component license inventory plus direct dependency maintenance/security and workflow-action review source in `benchmarks/release/v0.1.0/dependency-review.json`

---

## Phase 2: Foundational release-evidence contracts

**Purpose**: Build the closed identity/statistics/gate primitives required by every story.

**Critical**: No story implementation starts until these contracts and negative tests pass.

- [x] T007 Add schema/identity/statistics/policy/decision contract tests in `tests/domain/test_release.py`
- [x] T008 [P] Add schema strictness, unsupported-version and model/schema agreement tests in `tests/contract/test_release_schema.py`
- [x] T009 [P] Add evidence-directory traversal, duplicate, size, privacy and atomic-publication tests in `tests/security/test_release_boundaries.py`
- [x] T010 Implement closed release evidence, observation, suite, policy, check and decision models in `src/openardp/domain/release.py`
- [x] T011 Implement canonical source-tree/release-evidence identities, uniqueness/unit/finite-number invariants and stable failure categories in `src/openardp/domain/release.py`
- [x] T012 Define narrow evidence repository, clock, benchmark treatment and artifact inspector protocols in `src/openardp/ports/release.py`
- [x] T013 Implement deterministic median, MAD, percentile bootstrap, interval and threshold primitives in `src/openardp/services/release_gate.py`
- [x] T014 Implement bounded manifest-first canonical JSON/JSONL evidence reads and no-overwrite atomic writes in `src/openardp/adapters/release_evidence.py`
- [x] T015 Generate strict JSON Schema 2020-12 output for all public F015 roots in `scripts/generate_schemas.py` and `schemas/openardp-release-evidence.schema.json`
- [x] T016 Register release schema/current-version/drift rules in `scripts/validate_repository.py`
- [x] T017 [P] Add release package exports to `src/openardp/domain/__init__.py`, `src/openardp/ports/__init__.py` and `src/openardp/services/__init__.py`
- [x] T018 Add focused invariant, malformed-input, bootstrap reproducibility and atomic publication coverage in `tests/domain/test_release.py` and `tests/security/test_release_boundaries.py`
- [x] T019 Run focused foundation checks and record exact results in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T020 Reconcile any contract/plan drift before story work in `specs/015-benchmark-security-release-gate/spec.md` and `specs/015-benchmark-security-release-gate/plan.md`

**Checkpoint**: Closed evidence models, schema, statistics and safe filesystem boundary are independently usable.

---

## Phase 3: User Story 1 — Compare the complete retrieval pipeline fairly (Priority: P1)

**Goal**: Produce raw, fair observations for all five baselines without altering runtime behavior.

**Independent Test**: Run the frozen corpus and prove equal inputs, complete treatment coverage, parser-call instrumentation, raw samples and explicit negative/unavailable outcomes.

### Tests for User Story 1

- [x] T021 [P] [US1] Add corpus generator and manifest drift tests in `tests/test_release_evidence_drift.py`
- [x] T022 [P] [US1] Add equal-input/five-baseline/instrumentation tests in `tests/integration/test_release_benchmarks.py`
- [x] T023 [P] [US1] Add cold/warm/edit/storage/invalid-sample and unfavorable-result tests in `tests/integration/test_release_benchmarks.py`

### Implementation for User Story 1

- [x] T024 [US1] Implement deterministic text/DOCX/PPTX/edit corpus generation in `scripts/generate_release_corpus.py`
- [x] T025 [US1] Commit corpus manifest, sources, edit recipes and license facts under `benchmarks/release/v0.1.0/`
- [x] T026 [US1] Implement allowlisted source-tree inventory, redacted environment profiles and monotonic observation capture in `src/openardp/adapters/release_evidence.py`
- [x] T027 [US1] Implement raw-reparse and persisted-native direct-reuse treatments in `src/openardp/adapters/release_benchmarks.py`
- [x] T028 [US1] Implement declared Docling hierarchical-chunk lexical retrieval treatment in `src/openardp/adapters/release_benchmarks.py`
- [x] T029 [US1] Implement OpenARDP retrieval and existing compiler/receipt-replay treatments in `src/openardp/adapters/release_benchmarks.py`
- [x] T030 [US1] Instrument parser invocations, CAS/catalog/native bytes and phase timings without production fast paths in `src/openardp/adapters/release_benchmarks.py`
- [x] T031 [US1] Implement fair case orchestration, warm-up, repetition, cancellation and unavailable-treatment capture in `src/openardp/services/release_benchmarks.py`
- [x] T032 [US1] Implement exact source-edit/invalidation/reuse benchmark phases in `src/openardp/services/release_benchmarks.py`
- [x] T033 [US1] Add `release-evidence` benchmark composition and bounded flags in `src/openardp/interfaces/cli.py`
- [x] T034 [US1] Add body-free CLI/evidence serialization tests for successful, unfavorable and unavailable baselines in `tests/integration/test_release_cli.py`
- [x] T035 [US1] Record complete raw baseline evidence and limitations in `specs/015-benchmark-security-release-gate/implementation-notes.md`

**Checkpoint**: Every required baseline is observable and comparable from raw evidence; absence cannot be hidden.

---

## Phase 4: User Story 2 — Measure correctness and budgeted quality (Priority: P1)

**Goal**: Recompute retrieval/anchor/coverage/budget/replay quality from committed judgments with uncertainty and abstentions.

**Independent Test**: Evaluate all fixed queries/tasks and prove exact expected rankings/anchors, three budgets, byte coverage, insufficiency and deterministic replay.

### Tests for User Story 2

- [x] T036 [P] [US2] Add judgment identity, relevance and anchor invariant tests in `tests/domain/test_release.py`
- [x] T037 [P] [US2] Add retrieval precision/recall/rank/anchor evaluation tests in `tests/integration/test_release_correctness.py`
- [x] T038 [P] [US2] Add three-budget coverage, insufficiency and replay tests in `tests/integration/test_release_correctness.py`

### Implementation for User Story 2

- [x] T039 [US2] Commit exact queries/tasks, expected evidence/anchors and three budgets in `benchmarks/release/v0.1.0/judgments.json`
- [x] T040 [US2] Extend corpus drift generation to bind judgments and task/query digests in `scripts/generate_release_corpus.py`
- [x] T041 [US2] Implement precision, recall, reciprocal-rank, anchor and stale/replay scoring in `src/openardp/services/release_gate.py`
- [x] T042 [US2] Implement budget coverage, selected/native byte ratio, case-stratified quality confidence intervals, exact full-corpus checks, insufficiency and explicit evaluator-abstention evidence in `src/openardp/services/release_gate.py`
- [x] T043 [US2] Integrate correctness and budget suites into `src/openardp/services/release_benchmarks.py`
- [x] T044 [US2] Document mechanical-quality scope and model-evaluator non-claim in `docs/07_BENCHMARK_AND_EVIDENCE_PLAN.md`

**Checkpoint**: All binding quality claims derive from inspectable judgments; no unavailable evaluator creates a score.

---

## Phase 5: User Story 3 — Exercise security and failure boundaries (Priority: P1)

**Goal**: Turn hostile-input, malformed-provider, stale-state, privacy and cleanup controls into complete release evidence.

**Independent Test**: Execute the declared security manifest offline and prove every mandatory control/node exists, passes without skips and emits no forbidden canary outside allowed payloads.

### Tests for User Story 3

- [x] T045 [P] [US3] Add security-control manifest completeness/renaming/skip tests in `tests/security/test_release_boundaries.py`
- [x] T046 [P] [US3] Add end-to-end prompt-injection and zero-authority tests in `tests/security/test_release_injection.py`
- [x] T047 [P] [US3] Add malformed parser hang/crash/output/network/cleanup evidence tests in `tests/security/test_release_parser_isolation.py`
- [x] T048 [P] [US3] Add stale/reconciliation/CAS/index drift and privacy-canary scan tests in `tests/security/test_release_privacy.py`

### Implementation for User Story 3

- [x] T049 [US3] Commit the complete threat-to-test-node/invariant mapping in `benchmarks/release/v0.1.0/security-controls.json`
- [x] T050 [US3] Generate deterministic hostile sources/metadata/native-output canaries in `scripts/generate_release_corpus.py` and `benchmarks/release/v0.1.0/hostile/`
- [x] T051 [US3] Implement allowlisted test-manifest execution and sanitized result capture in `src/openardp/adapters/release_security.py`
- [x] T052 [US3] Implement digest-only privacy canary scanning across results, logs, archives and reports in `src/openardp/adapters/release_security.py`
- [x] T053 [US3] Integrate security/privacy completeness and zero-skip gate checks in `src/openardp/services/release_gate.py`
- [x] T054 [US3] Update exact delivered controls/non-claims in `docs/06_SECURITY_MODEL_V2.md` and `SECURITY.md`
- [x] T055 [US3] Record threat coverage, negative fixtures and residual sandbox/scanner risk in `specs/015-benchmark-security-release-gate/implementation-notes.md`

**Checkpoint**: Every declared control is traceable and security/privacy omissions bind to `NO-GO`.

---

## Phase 6: User Story 4 — Reproduce installation, upgrade and recovery (Priority: P1)

**Goal**: Validate exact artifacts, dependency/SBOM review, clean offline install, F014 `0.0.1` to F015 `0.1.0rc1` application upgrade and revision-9 migration/rollback on every supported platform.

**Independent Test**: Build and inspect F014/F015 wheel/sdist, enrich the locked SBOM, install from local artifacts, have F014 create the previous workspace, reopen it with F015 and perform verified revision-9 backup-migrate-restore.

### Tests for User Story 4

- [x] T056 [P] [US4] Add CycloneDX normalization/component/license/dependency completeness and review drift tests in `tests/integration/test_release_supply_chain.py`
- [x] T057 [P] [US4] Add artifact member/hash/privacy and clean-install tests in `tests/integration/test_release_reproduction.py`
- [x] T058 [P] [US4] Add F014 previous-artifact/workspace provenance, F015 candidate reopen, revision-9 migration and complete backup/restore tests in `tests/integration/test_release_reproduction.py`
- [x] T059 [P] [US4] Add platform-bundle identity and semantic-divergence tests in `tests/integration/test_release_reproduction.py`

### Implementation for User Story 4

- [x] T060 [US4] Implement locked CycloneDX 1.5 export normalization, reviewed license enrichment and complete graph validation in `src/openardp/adapters/release_supply_chain.py`
- [x] T061 [US4] Implement dependency/license/OSV snapshot reconciliation and disposition checks in `src/openardp/adapters/release_supply_chain.py`
- [x] T062 [US4] Implement candidate wheel/sdist build inventory, member/privacy inspection and checksums in `src/openardp/adapters/release_reproduction.py`
- [x] T063 [US4] Commit independently inventoried F014 `0.0.1` revision-10 and historical revision-9 synthetic workspace fixtures under `tests/fixtures/release/previous-v0.0.1/` and `tests/fixtures/release/revision-9/`
- [x] T064 [US4] Implement F014 artifact build/workspace creation, F015 clean install/reopen/smoke and backup-migrate-restore orchestration in `src/openardp/adapters/release_reproduction.py`
- [x] T065 [US4] Add per-platform release-evidence generation with pinned artifact upload/download plus one all-platform aggregate gate job to `.github/workflows/ci.yml`

**Checkpoint**: Each supported platform proves the same candidate semantics from install through rollback; missing evidence remains visible.

---

## Phase 7: User Story 5 — Make a traceable GO or NO-GO decision (Priority: P1)

**Goal**: Apply the frozen policy to complete evidence and generate one authoritative decision plus consistent human/claim projections.

**Independent Test**: Evaluate complete and tampered/missing/stale/failed evidence, prove conjunctive `GO`, mandatory `NO-GO`, no waiver surface and byte-stable report/claim generation.

### Tests for User Story 5

- [x] T066 [P] [US5] Add complete-policy, all-blocker and no-waiver model tests in `tests/domain/test_release.py`
- [x] T067 [P] [US5] Add evidence merge/platform/reference-timing and tamper tests in `tests/integration/test_release_gate.py`
- [x] T068 [P] [US5] Add machine/human/claim-map consistency and report privacy/drift tests in `tests/integration/test_release_gate.py`
- [x] T069 [P] [US5] Add CLI exit semantics, missing inputs, conflicting output and sanitized failure tests in `tests/integration/test_release_cli.py`

### Implementation for User Story 5

- [x] T070 [US5] Implement complete suite verification and platform evidence merge in `src/openardp/services/release_gate.py`
- [x] T071 [US5] Implement exhaustive ordered policy checks, blocker collection and immutable decision identity in `src/openardp/services/release_gate.py`
- [x] T072 [US5] Implement deterministic Markdown report, support matrix and claim-map projections in `src/openardp/services/release_gate.py`
- [x] T073 [US5] Implement `release-gate` and `release-report` CLI commands without override paths in `src/openardp/interfaces/cli.py`
- [x] T074 [US5] Implement standalone corpus/evidence generation and validation commands in `scripts/generate_release_evidence.py` and `scripts/validate_release_evidence.py`
- [x] T075 [US5] Generate and commit the current candidate decision/report/claim-map/SBOM/checksums under `release/evidence/v0.1.0/`
- [x] T076 [US5] Map every README performance/security/support claim to allowed evidence IDs in `README.md` and `release/evidence/v0.1.0/claim-map.json`
- [x] T077 [US5] Update release/support/operations guidance and rollback instructions in `docs/08_RELEASE_AND_ADOPTION_STRATEGY.md`, `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md` and `docs/13_STEP_BY_STEP_USER_GUIDE.md`
- [x] T078 [US5] Record the exact current `GO` or `NO-GO`, all blockers and prohibited claims in `CHANGELOG.md`
- [x] T079 [US5] Record commands, raw evidence identity, tradeoffs and residual risks in `specs/015-benchmark-security-release-gate/implementation-notes.md`

**Checkpoint**: A reviewer can reproduce why the exact candidate is or is not releasable without trusting narrative text.

---

## Phase 8: Polish and cross-cutting convergence

**Purpose**: Validate every contract, generated artifact and supported platform before publication.

- [x] T080 [P] Complete and revalidate `specs/015-benchmark-security-release-gate/checklists/requirements.md`
- [x] T081 [P] Complete and revalidate `specs/015-benchmark-security-release-gate/checklists/release-evidence.md`
- [x] T082 Run focused F015 tests and repair root causes in `tests/domain/test_release.py`, `tests/contract/test_release_schema.py`, `tests/integration/test_release_benchmarks.py`, `tests/integration/test_release_correctness.py`, `tests/integration/test_release_gate.py`, `tests/integration/test_release_reproduction.py` and `tests/security/test_release_boundaries.py`
- [x] T083 Run `uv run ruff check .` and record the result in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T084 Run `uv run ruff format --check .` and record the result in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T085 Run `uv run mypy src` and record the result in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T086 Run full `uv run pytest` with network disabled and record tests/coverage in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T087 Run schema/corpus/evidence/SBOM/repository drift checks and record identities in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T088 Run `uv build`, inspect/install candidate artifacts and record hashes/results in `specs/015-benchmark-security-release-gate/implementation-notes.md`
- [x] T089 Run `uv run pre-commit run --all-files`, review the complete diff and reconcile spec/plan/tasks/docs/code in `specs/015-benchmark-security-release-gate/analysis.md`
- [x] T090 Commit and push one F015 change set, open a focused PR, verify Linux/macOS/Windows PR CI, merge, verify post-merge `main` CI and record immutable run evidence in `specs/015-benchmark-security-release-gate/implementation-notes.md`

---

## Phase 9: Convergence

- [x] T091 CRITICAL Implement complete hostile-surface and malformed-provider execution for instruction-shaped metadata/table/image/native data, invalid output, oversize, hang, crash, resource breach, network attempt and cleanup in `benchmarks/release/v0.1.0/security-controls.json`, `benchmarks/release/v0.1.0/hostile/`, `src/openardp/adapters/release_security.py` and `tests/security/` per FR-013–FR-016 and Constitution V/VIII (partial)
- [x] T092 CRITICAL Replace unbound caller-asserted suite passes with a closed required-check registry whose exact sanitized evidence identities are independently validated by `src/openardp/services/release_gate.py`, `src/openardp/interfaces/cli.py` and `.github/workflows/ci.yml` per FR-027–FR-029 and US5/AC2 (contradicts)
- [x] T093 Complete cold, warm, update, retrieval, compile and replay observations; storage/parser instrumentation; rejected-sample retention; per-observation input identity; and a real persisted provider-native reuse/retrieval baseline in `src/openardp/domain/release.py`, `src/openardp/adapters/release_benchmarks.py` and `src/openardp/services/release_benchmarks.py` per FR-001–FR-007, FR-012 and US1 (partial)
- [x] T094 Bind exact evidence identities, source anchors, precision, recall, reciprocal rank, stale/replay outcomes, all three budgets and evaluator abstention to committed judgments and real benchmark observations in `benchmarks/release/v0.1.0/judgments.json`, `src/openardp/services/release_benchmarks.py` and `src/openardp/services/release_gate.py` per FR-009–FR-011 and US2 (partial)
- [x] T095 Integrate digest-only privacy scanning plus cancellation, interruption, capacity, migration, backup, restore and rollback evidence into the platform suite pipeline in `src/openardp/adapters/release_security.py`, `src/openardp/adapters/release_reproduction.py` and `scripts/generate_ci_suite_results.py` per FR-017–FR-018 and US3 (missing)
- [x] T096 Implement clean-revision wheel/sdist inspection, offline installation, independently bound previous-workspace migration and disjoint backup-upgrade-restore reproduction on every CI platform, then emit exact artifact/check identities in `.github/workflows/ci.yml`, `src/openardp/adapters/release_reproduction.py` and `tests/fixtures/release/` per FR-021–FR-026 and US4 (missing)
- [x] T097 Generate the committed candidate bundle from actual verified local observations, summaries, rejected samples, artifact facts and suite evidence; make every report/README projection reproducible and drift-checked in `scripts/generate_release_evidence.py`, `release/evidence/v0.1.0/` and `README.md` per FR-006, FR-030–FR-032 and SC-002/SC-010/SC-011 (partial)

---

## Dependencies and execution order

### Phase dependencies

- Phase 1 has no feature dependency beyond merged F014.
- Phase 2 depends on frozen Phase 1 inputs and blocks all user stories.
- US1 depends on Phase 2.
- US2 depends on the US1 corpus/treatment result shape but not on release reporting.
- US3 depends only on Phase 2 plus the frozen corpus manifest and can be implemented alongside US1/US2 in separate files.
- US4 depends on Phase 2 and the exact candidate source/lock; it does not depend on benchmark thresholds.
- US5 depends on completed US1–US4 suite evidence.
- Phase 8 depends on every story.

### User story dependency graph

```text
Setup -> Foundation -> US1 -> US2 --+
                    \-> US3 -------+-> US5 -> Convergence
                    \-> US4 -------+
```

### Parallel examples

- US1: corpus drift tests (T021), treatment contract tests (T022) and phase tests (T023) touch independent test sections before adapter work.
- US2: judgment-domain tests (T036), retrieval correctness tests (T037) and budget/replay tests (T038) can be authored independently.
- US3: manifest, injection, parser-isolation and privacy test files (T045–T048) are independent before service integration.
- US4: SBOM, artifact/install, upgrade/recovery and platform identity tests (T056–T059) cover separate adapters.
- US5: policy, merge/tamper, projection and CLI tests (T066–T069) are independent before the gate service is integrated.

## Implementation strategy

### Smallest coherent increment

Phase 1 + Phase 2 + US1 produce fair raw evidence and immediately falsify incomplete benchmark claims, without requiring a favorable release decision.

### Incremental delivery

1. Freeze policy/corpus before results.
2. Build strict identities/statistics/storage contracts.
3. Measure all baselines without runtime changes.
4. Add correctness and budget judgments.
5. Add security/privacy evidence.
6. Add artifact/install/upgrade/recovery and platform bundles.
7. Generate the binding decision and claim-limited reports.
8. Converge all quality/platform gates, then merge before F016.

## Task format validation

All 97 tasks use the required checkbox plus sequential `T###` identifier. User-story
tasks carry `[US#]`; only file-independent work carries `[P]`; every task names an exact
file or command/result destination. T091-T097 are append-only convergence work discovered
after the first implementation pass.
