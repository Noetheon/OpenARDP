# Tasks: Minimum Relevance and Explicit Abstention

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/context-relevance.md`, `quickstart.md`

**Tests**: Mandatory and authored before corresponding implementation.

## Phase 1: Governance and Frozen Boundaries

- [x] T001 Add F026 prompt, feature-map sequence and active feature pointer in `spec-kit/feature-prompts/026-relevance-abstention.md`, `spec-kit/FEATURE_MAP.md`, `.specify/feature.json`
- [x] T002 Complete clarification, plan, research, data model, contract and quickstart in `specs/026-relevance-abstention/`
- [x] T003 Complete requirements and relevance-integrity checklists in `specs/026-relevance-abstention/checklists/`
- [x] T004 Freeze unchanged F025 comparison IDs and Q02/Q03/Q06/Q13/Q14/Q19/Q17/Q18 expectations in `specs/026-relevance-abstention/research.md`
- [x] T005 Register F026 governed artifacts and later-feature exclusions in `scripts/validate_repository.py`

**Checkpoint**: Policy intent, anti-overfitting comparison and compatibility boundary are frozen.

## Phase 2: Foundational Contract Tests

- [x] T006 [P] Add policy validation, canonical identity and sorted-set tests in `tests/domain/test_context_relevance.py`
- [x] T007 [P] Add NFC/casefold, punctuation, Unicode and bounded-token tests in `tests/domain/test_context_relevance.py`
- [x] T008 [P] Add ordinary/identifier/date/acronym signal weighting and repetition-invariance tests in `tests/domain/test_context_relevance.py`
- [x] T009 [P] Add exact below/at/above integer-floor tests in `tests/domain/test_context_relevance.py`
- [x] T010 [P] Add volatile-time requirement and no-signal tests in `tests/domain/test_context_relevance.py`
- [x] T011 [P] Add internal candidate relevance model validation tests in `tests/domain/test_context_compilation.py`
- [x] T012 [P] Add existing receipt-extension compatibility and closed audit-shape tests in `tests/contract/test_context_schemas.py`
- [x] T013 [P] Add legacy algorithm identity and F026 policy-bound identity tests in `tests/domain/test_context_compilation.py`

**Checkpoint**: Pure contract tests fail for the absent policy and establish every deterministic boundary.

## Phase 3: User Story 1 - Abstain Instead of Returning Weak Evidence (Priority: P1)

**Goal**: Reject incidental matches and emit genuine explicit abstention.

**Independent Test**: Unrelated and F025 Q17/Q18 tasks yield zero evidence plus both abstention notices without a failure.

- [x] T014 [P] [US1] Add verified decorator empty-discovery and all-below-floor tests in `tests/unit/test_context_relevance.py`
- [x] T015 [P] [US1] Add mixed retained/rejected candidate partition tests in `tests/unit/test_context_relevance.py`
- [x] T016 [P] [US1] Add compiler bundle/receipt abstention notice and fixed-point budget tests in `tests/integration/test_context_relevance.py`
- [x] T017 [P] [US1] Add no-false-abstention tests for budget-only omission and trust-only rejection in `tests/integration/test_context_relevance.py`
- [x] T018 [US1] Implement immutable relevance policy, signals, observations and integer evaluation in `src/openardp/domain/context_relevance.py`
- [x] T019 [US1] Add optional body-free relevance observation to internal candidates in `src/openardp/domain/context_compilation.py`
- [x] T020 [US1] Implement CAS-reverifying relevance decorator for text and rich bodies in `src/openardp/adapters/context_relevance.py`
- [x] T021 [US1] Integrate insufficient-relevance rejection after trust/freshness and before budget selection in `src/openardp/services/context_compiler.py`
- [x] T022 [US1] Emit exact `no_relevant_evidence` bundle and receipt notices with correct budget accounting in `src/openardp/services/context_compiler.py`

**Checkpoint**: Weak evidence is rejected and a valid zero-result is explicit without hiding failures.

## Phase 4: User Story 2 - Preserve Strong Exact Evidence (Priority: P1)

**Goal**: Retain useful exact evidence and all existing verification/provenance guarantees.

**Independent Test**: Strong synthetic identifiers/prose and prior-success F025 questions keep support and citations.

- [x] T023 [P] [US2] Add strong prose, identifier, date and acronym retention tests in `tests/unit/test_context_relevance.py`
- [x] T024 [P] [US2] Add text/rich parity and exact evidence-resolution tests in `tests/integration/test_context_relevance.py`
- [x] T025 [P] [US2] Add unchanged F025 prior-success comparison test in `tests/integration/test_context_relevance_reference.py`
- [x] T026 [US2] Project body-free relevance audit facts through the existing receipt extension in `src/openardp/services/context_compiler.py`
- [x] T027 [US2] Add F026 algorithm identity factory bound to the complete relevance policy in `src/openardp/services/context_compiler.py`
- [x] T028 [US2] Compose the F026 relevance profile for CLI context compilation while retaining an explicit legacy factory in `src/openardp/interfaces/cli.py`

**Checkpoint**: F026 eliminates false positives without reducing the frozen prior-success support floor.

## Phase 5: User Story 3 - Audit and Reproduce the Decision (Priority: P2)

**Goal**: Make every relevance decision deterministic, body-free and replay-safe.

**Independent Test**: Fresh runs and replay agree byte-for-byte; policy mismatch and tampering fail closed.

- [x] T029 [P] [US3] Add fresh-workspace determinism, persisted replay and policy-mismatch tests in `tests/integration/test_context_relevance.py`
- [x] T030 [P] [US3] Add corrupt object, drifted body and missing observation tests in `tests/security/test_context_relevance_boundaries.py`
- [x] T031 [P] [US3] Add cancellation, resource-limit, truncation and privacy tests in `tests/security/test_context_relevance_boundaries.py`
- [x] T032 [US3] Expose domain/adapter symbols through reviewed package exports in `src/openardp/domain/__init__.py` and `src/openardp/adapters/__init__.py`
- [x] T033 [US3] Add deterministic focused F025 comparison harness and body-free output validation in `scripts/run_relevance_benchmark.py` and `scripts/validate_relevance_benchmark.py`
- [x] T034 [US3] Run the unchanged comparison twice and commit its reference result under `benchmarks/relevance/v0.1.0/results/reference-macos-arm64/`

**Checkpoint**: Policy decisions, audit facts and abstention reproduce independently without content leakage.

## Phase 6: Documentation and Convergence

- [x] T035 [P] Document behavior, results, limitations and rollback in `docs/25_RELEVANCE_AND_ABSTENTION.md`
- [x] T036 [P] Update `README.md`, `VALIDATION.md`, `CHANGELOG.md` and `REFERENCES.md` with exact measured claims
- [x] T037 Update repository module/schema/governance inventories and drift checks in `scripts/validate_repository.py` and `tests/test_repository_contract.py`
- [x] T038 Run all focused commands from `specs/026-relevance-abstention/quickstart.md` and record exact outcomes in `specs/026-relevance-abstention/implementation-notes.md`
- [x] T039 Run Ruff, format, strict mypy, full pytest/coverage, repository validation, build and pre-commit
- [x] T040 Run Spec-Kit analysis and resolve every critical/high contradiction before implementation closeout
- [x] T041 Run Spec-Kit convergence across all requirements, criteria, tasks and evidence; append and implement any proven gaps
- [ ] T042 Commit F026 independently, push the private branch, open a ready PR and merge only after required checks pass

## Dependencies and Execution Order

- Phase 1 blocks code changes; Phase 2 tests precede all implementation.
- US1 establishes the policy and abstention behavior required by US2 and US3.
- US2 must prove non-regression before the binding comparison is accepted.
- US3 must prove replay, privacy and failure distinctions before documentation claims are written.
- F027 cannot begin until F026 converges and merges.

## Parallel Opportunities

- Tasks marked `[P]` affect separate test or documentation files and may be prepared independently.
- Implementation tasks sharing domain/compiler files remain sequential.
- The binding benchmark is sequential and runs only after all synthetic/integration tests pass.

## Implementation Strategy

1. Freeze requirements and comparison expectations.
2. Write pure boundary and integration tests first and observe focused failures.
3. Implement US1 minimum relevance and explicit abstention.
4. Prove US2 strong-evidence non-regression.
5. Complete US3 replay/security and binding measurement.
6. Run full gates and converge before publication.
