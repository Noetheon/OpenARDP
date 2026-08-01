# Tasks: Alternate Parser Conformance Spike

**Input**: Design documents from `/specs/016-alternate-parser-conformance-spike/`

**Tests**: Required by the feature specification and Constitution Article VIII. Test tasks precede implementation tasks.

## Phase 1: Setup and frozen evidence profile

**Purpose**: Establish exact inputs, limits and generated-artifact ownership before executable work.

- [x] T001 Record the authoritative prompt digest, restated acceptance criteria and F015 baseline in `specs/016-alternate-parser-conformance-spike/implementation-notes.md`
- [x] T002 [P] Register the F016 conformance family and regeneration command in `conformance/README.md` and `specs/README.md`
- [x] T003 Freeze source descriptors, corpus/vector digests, required coverage, resource limits and expected outputs in `conformance/alternate-parser/v0.1.0/manifest.json`
- [x] T004 [P] Add deterministic untrusted text and RFC 4180-style table inputs in `conformance/alternate-parser/v0.1.0/sources/sample.txt` and `conformance/alternate-parser/v0.1.0/sources/sample.csv`

---

## Phase 2: Foundational isolation and profile tests

**Purpose**: Prove the independent boundary and fail-closed input rules before contract logic.

**Critical**: No consumer or producer implementation starts until these tests fail for the intended missing behavior.

- [x] T005 Add isolated-process self-check, import prohibition and canonical response tests in `tests/contract/test_alternate_conformance.py`
- [x] T006 [P] Add manifest traversal, absolute path, symlink, undeclared file, byte/file/output limit and timeout tests in `tests/security/test_alternate_conformance_boundaries.py`
- [x] T007 [P] Add canonical JSON safe-domain, unsafe integer, float, surrogate and stable diagnostic tests in `tests/contract/test_alternate_conformance.py`
- [x] T008 Implement CLI framing, isolated self-check, closed canonical JSON and stable error categories in `scripts/alternate_evidence_process.py`
- [x] T009 Implement confined regular-file loading and all manifest/request/process resource limits in `scripts/alternate_evidence_process.py` and `scripts/validate_alternate_conformance.py`
- [x] T010 Run the focused foundation tests and record the intentional red/green transition in `specs/016-alternate-parser-conformance-spike/implementation-notes.md`

**Checkpoint**: The alternate process is observably independent, bounded and deterministic.

---

## Phase 3: User Story 1 — Independently consume the evidence contract (Priority: P1)

**Goal**: Evaluate every F006 root, record set and identity vector without reference-runtime imports.

**Independent Test**: Invoke `consume` under `-I -S` and prove exact parity with every manifest expectation and required anchor class.

### Tests for User Story 1

- [x] T011 [P] [US1] Add complete valid/invalid root parity and all-anchor coverage tests in `tests/contract/test_alternate_conformance.py`
- [x] T012 [P] [US1] Add semantic scope, trust, identity and record-set mutation tests in `tests/contract/test_alternate_conformance.py`
- [x] T013 [P] [US1] Add all-vector canonical bytes/digest parity and deterministic observation-order tests in `tests/contract/test_alternate_conformance.py`

### Implementation for User Story 1

- [x] T014 [US1] Implement closed common/version/extension/scalar validators in `scripts/alternate_evidence_process.py`
- [x] T015 [US1] Implement native, trust, text/page/table/pointer reference and projection validation in `scripts/alternate_evidence_process.py`
- [x] T016 [US1] Implement purpose-specific identity envelopes and all golden-vector evaluation in `scripts/alternate_evidence_process.py`
- [x] T017 [US1] Implement cross-record source/native/reference/collision validation in `scripts/alternate_evidence_process.py`
- [x] T018 [US1] Implement complete manifest expectation orchestration and body-free observations in `scripts/alternate_evidence_process.py`

**Checkpoint**: The independent consumer agrees with all published F006 expectations without using OpenARDP code.

---

## Phase 4: User Story 2 — Produce evidence with an alternate parser (Priority: P1)

**Goal**: Produce deterministic non-Docling evidence for synthetic text and table sources and validate it with the reference implementation.

**Independent Test**: Run `produce` three times, compare canonical bytes and validate all required records through OpenARDP domain models.

### Tests for User Story 2

- [x] T019 [P] [US2] Add TXT/CSV native preservation, exact source binding and non-Docling profile tests in `tests/contract/test_alternate_conformance.py`
- [x] T020 [P] [US2] Add text/page/table anchor, thin projection and reference-consumer round-trip tests in `tests/contract/test_alternate_conformance.py`
- [x] T021 [P] [US2] Add repeat-run byte determinism, line-ending/locale independence and instruction-as-data tests in `tests/security/test_alternate_conformance_boundaries.py`

### Implementation for User Story 2

- [x] T022 [US2] Implement deterministic TXT and CSV native parsing without ambient configuration in `scripts/alternate_evidence_process.py`
- [x] T023 [US2] Implement alternate native/reference/projection identity construction and canonical record-set output in `scripts/alternate_evidence_process.py`
- [x] T024 [US2] Implement deterministic declared page/grid mapping for page-region and table-cell anchors in `scripts/alternate_evidence_process.py`
- [x] T025 [US2] Implement reference-model consumption, artifact digest/length checks and cross-direction observations in `scripts/validate_alternate_conformance.py`
- [x] T026 [US2] Generate and review the canonical alternate record set in `conformance/alternate-parser/v0.1.0/expected/alternate-record-set.json`

**Checkpoint**: Both contract directions pass with a retained alternate native artifact and thin evidence records.

---

## Phase 5: User Story 3 — Make a bounded provider-neutrality decision (Priority: P1)

**Goal**: Turn exact observations into a reproducible, conservative architecture decision.

**Independent Test**: Regenerate the decision, then remove or mutate each mandatory evidence class and prove the status fails closed with no override.

### Tests for User Story 3

- [x] T027 [P] [US3] Add observation/input/executable/output identity and decision determinism tests in `tests/contract/test_alternate_conformance.py`
- [x] T028 [P] [US3] Add missing, failed, duplicate, tampered and no-waiver decision tests in `tests/contract/test_alternate_conformance.py`
- [x] T029 [P] [US3] Add Docling-token leakage scan and narrow-claim/prohibited-claim tests in `tests/contract/test_alternate_conformance.py`

### Implementation for User Story 3

- [x] T030 [US3] Implement coordinator subprocess invocation, request binding, coverage closure and fail-closed decision generation in `scripts/validate_alternate_conformance.py`
- [x] T031 [US3] Encode observed friction, provider leakage, limitations, required changes and non-claims in `scripts/validate_alternate_conformance.py`
- [x] T032 [US3] Generate and review the canonical decision in `conformance/alternate-parser/v0.1.0/expected/decision.json`
- [x] T033 [US3] Add manifest/report regeneration and drift validation to `scripts/validate_repository.py`
- [x] T034 [US3] Document the scoped result, contract friction and continued experimental status in `docs/15_EVIDENCE_CONTRACT_STANDARDS_MAPPING.md`, `CHANGELOG.md` and `conformance/README.md`

**Checkpoint**: The repository has one traceable decision whose claims cannot exceed the measured evidence.

---

## Phase 6: Polish and cross-cutting validation

**Purpose**: Complete documentation, generated evidence and all repository gates before publication.

- [x] T035 [P] Complete and revalidate `specs/016-alternate-parser-conformance-spike/checklists/requirements.md`
- [x] T036 [P] Complete and revalidate `specs/016-alternate-parser-conformance-spike/checklists/conformance.md`
- [x] T037 Run focused F016 tests and repair root causes in `tests/contract/test_alternate_conformance.py` and `tests/security/test_alternate_conformance_boundaries.py`
- [x] T038 Run `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy src` and record results in `specs/016-alternate-parser-conformance-spike/implementation-notes.md`
- [x] T039 Run full network-blocked `uv run pytest` and record tests/coverage in `specs/016-alternate-parser-conformance-spike/implementation-notes.md`
- [x] T040 Run all schema/conformance/repository drift validators, `uv build`, artifact inspection and `uv run pre-commit run --all-files`; record exact results in `specs/016-alternate-parser-conformance-spike/implementation-notes.md`
- [x] T041 Review the complete diff and reconcile spec/plan/tasks/docs/tooling/evidence in `specs/016-alternate-parser-conformance-spike/analysis.md`
- [x] T042 Commit and push one F016 change set, open a focused PR, verify Linux/macOS/Windows PR CI, merge, verify post-merge `main` CI and record immutable run evidence in `specs/016-alternate-parser-conformance-spike/implementation-notes.md`

---

## Dependencies and execution order

### Phase dependencies

- Phase 1 has no feature-internal dependency and freezes normative inputs.
- Phase 2 depends on Phase 1 and blocks every user story.
- Phase 3 (US1) and Phase 4 test preparation may proceed after Phase 2; producer reference validation depends on the alternate identity primitives from US1.
- Phase 5 depends on complete US1 and US2 observations.
- Phase 6 depends on all user stories.

### User-story dependency graph

```text
Setup → Foundation → US1 independent consumer ─┐
                         US2 producer ─────────┼→ US3 decision → Polish
                                              ┘
```

### Parallel opportunities

- T002 and T004 touch separate documentation/source files.
- T005-T007 define independent foundation behaviors in separate test modules.
- T011-T013, T019-T021 and T027-T029 are parallelizable test slices before their corresponding implementation.
- T035 and T036 revalidate separate checklist files.

## Implementation strategy

### MVP first

Complete Phases 1-3 to obtain an independent consumer result. Do not publish a provider-neutrality conclusion until the producer direction and fail-closed decision in Phases 4-5 are complete.

### Incremental delivery

1. Freeze evidence and isolation boundaries.
2. Deliver independent consumer parity.
3. Deliver alternate producer/reference round-trip.
4. Generate the bounded decision and claims.
5. Converge, validate on all platforms and publish one feature PR.

## Format validation

All 42 tasks use the required checkbox, sequential ID, optional `[P]`, story label and explicit file-path format.
