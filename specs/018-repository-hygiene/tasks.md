# Tasks: Repository Hygiene and Maintainability

**Input**: Design documents from `/specs/018-repository-hygiene/`

**Tests**: Required by the specification and Constitution Article VIII. Characterization and policy-failure tests
precede source refactoring.

## Phase 1: Setup and governance

- [x] T001 Record the user request, F017 baseline, acceptance criteria and non-change boundaries in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T002 Capture reproducible initial module/function/gate measurements in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T003 Update F018 feature prompt, canonical map and active governance assertions in `spec-kit/feature-prompts/018-repository-hygiene.md`, `spec-kit/FEATURE_MAP.md` and `tests/test_repository_contract.py`

## Phase 2: Foundational maintainability guard

- [x] T004 [P] Add strict policy parsing, unsafe-path, duplicate-key, deterministic-order and regression tests in `tests/unit/test_maintainability_audit.py`
- [x] T005 [P] Add repository integration assertions for F018 artifacts, unchanged version axes and tracked generated-state hygiene in `tests/test_repository_contract.py`
- [x] T006 Run the new maintainability tests before implementation and record the intentional red result in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T007 Implement deterministic AST measurement and body-free findings in `scripts/audit_maintainability.py`
- [x] T008 Add the explicit monotonic baseline in `quality/maintainability-policy.json`
- [x] T009 Integrate the maintainability audit into `scripts/validate_repository.py` without importing product code

## Phase 3: User Story 1 — maintain high-risk workflows safely

### Tests

- [x] T010 [P] [US1] Strengthen release decision check-order, identity and malformed-evidence characterization in `tests/integration/test_release_gate.py`
- [x] T011 [P] [US1] Add CLI command-family dispatch and invalid-command characterization in `tests/integration/test_cli.py`
- [x] T012 [P] [US1] Strengthen incomplete, rename, backpressure, tombstone and fault-rollback characterization in `tests/integration/test_watcher_catalog.py`
- [x] T013 [US1] Run the focused characterization suite before refactoring and record its exact baseline in `specs/018-repository-hygiene/implementation-notes.md`

### Implementation

- [x] T014 [US1] Extract release evidence validation, check groups and decision construction in `src/openardp/services/release_gate.py`
- [x] T015 [US1] Extract bounded command-family handlers from `_execute` in `src/openardp/interfaces/cli.py`
- [x] T016 [US1] Extract incomplete-scan, identity/hint, entry, tombstone and publication helpers from `reconcile_watch_scan` in `src/openardp/adapters/sqlite_catalog.py`
- [x] T017 [US1] Prove each selected hotspot improves at least 40 percent and record unchanged characterization outcomes in `specs/018-repository-hygiene/implementation-notes.md`

## Phase 4: User Story 2 — run truthful validation commands

- [x] T018 [P] [US2] Correct feature-focused commands to use explicit partial-suite coverage semantics in affected `specs/*/quickstart.md` files
- [x] T019 [P] [US2] Correct the F017 constitution cross-reference, complete convergence task T041 and retain the full-suite gate in `specs/017-microsoft-graph-design-spike/`
- [x] T020 [US2] Add validation-guide regression assertions to `tests/test_repository_contract.py`
- [x] T021 [US2] Prove changed focused commands exit zero and record the unchanged socket and 85 percent branch-coverage policy in `specs/018-repository-hygiene/implementation-notes.md`

## Phase 5: User Story 3 — review an honest hygiene baseline

- [x] T022 [P] [US3] Synchronize implemented status and the F018 maintenance entry in `README.md`, `CHANGELOG.md`, `spec-kit/FEATURE_MAP.md` and `specs/README.md`
- [x] T023 [P] [US3] Document baseline, improvements, residual debt, exclusions and rollback in `docs/17_CODEBASE_HYGIENE.md`
- [x] T024 [US3] Confirm no generated/cache artifact is tracked and record safe disposable-output cleanup excluding `.venv` and user worktrees in `docs/17_CODEBASE_HYGIENE.md`
- [x] T025 [US3] Run the audit twice and record deterministic equal output plus successful repository integration in `specs/018-repository-hygiene/implementation-notes.md`

## Phase 6: Convergence and publication

- [x] T026 Run focused policy, release, watcher and CLI suites and record exact results in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T027 Run locked Ruff check/format and strict mypy and record exact results in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T028 Run the full offline pytest/coverage and repository validation and record exact results in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T029 Run package build, artifact inspection and pre-commit and record exact results in `specs/018-repository-hygiene/implementation-notes.md`
- [x] T030 Reconcile `specs/018-repository-hygiene/checklists/`, `analysis.md`, `implementation-notes.md` and run final convergence
- [x] T031 Commit and push one F018 change set, open a PR, verify all platforms, merge and record post-merge `main` CI in `specs/018-repository-hygiene/implementation-notes.md`

## Dependencies and order

```text
Governance -> failing audit tests -> audit/policy -> characterization -> three hotspot refactors
           -> truthful commands -> status/evidence -> full gates -> convergence/publication
```

T004 and T005 can run in parallel before T007–T009. T010–T012 can be authored independently but all must pass before
T014–T016. Documentation tasks T018, T019, T022 and T023 are independent after their authoritative facts are known.

## Independent test criteria

- **US1**: Existing and strengthened release, CLI and watcher integration suites produce identical public results and
  transaction/error behavior while each selected hotspot falls by at least 40 percent.
- **US2**: Every changed focused command exits zero with passing tests, while the separate full suite retains socket
  blocking and at least 85 percent branch coverage.
- **US3**: Two audit runs are byte-identical; generated state is untracked; the documentation names both improvements
  and residual debt without changing release or production-connector decisions.

## Format validation

All 31 tasks use checkboxes, sequential IDs, story labels where required, explicit paths and test-first ordering.
