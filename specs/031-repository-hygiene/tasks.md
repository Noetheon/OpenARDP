# Tasks: Repository Hygiene and Bounded Refactoring

**Input**: Design documents from `/specs/031-repository-hygiene/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Every behavior change is test-first. Existing characterization may satisfy the red phase only when a new
structural assertion fails before extraction; otherwise add the missing behavioral case first.

## Phase 1: Setup and baseline

**Purpose**: Freeze the exact evidence against which F031 claims are judged.

- [x] T001 Record base SHA, Git topology and clean-worktree gate state in `specs/031-repository-hygiene/implementation-notes.md`
- [x] T002 Record source/module/function and Ruff complexity baselines in `specs/031-repository-hygiene/implementation-notes.md`
- [x] T003 Recompute and record the complete worktree/Git-metadata duplicate inventory without mutation in `specs/031-repository-hygiene/implementation-notes.md`
- [x] T004 Validate `specs/031-repository-hygiene/checklists/requirements.md` and `specs/031-repository-hygiene/checklists/maintainability.md`

---

## Phase 2: Foundational analysis gate

**Purpose**: Prove the feature artifacts are mutually consistent before implementation.

- [x] T005 Run cross-artifact analysis and record zero unresolved critical/high findings in `specs/031-repository-hygiene/analysis.md`
- [x] T006 Trace FR-001–FR-020 and SC-001–SC-010 to tasks in `specs/031-repository-hygiene/analysis.md`
- [x] T007 Confirm no ADR, schema migration, dependency or runtime contract change is required in `specs/031-repository-hygiene/analysis.md`

**Checkpoint**: Implementation remains blocked until T005–T007 pass.

---

## Phase 3: User Story 1 — Trust the repository state (P1) 🎯 MVP

**Goal**: Detect sync-conflict artifacts deterministically and restore the observed local repository to a verified clean
state without risking canonical or ambiguous work.

**Independent Test**: The synthetic audit suite identifies every contract class without mutation; the post-clean live
audit and Git integrity checks report no conflict-copy artifact.

### Tests for User Story 1

- [x] T008 [US1] Add failing clean/identical/divergent/missing-canonical/tracked tests in `tests/unit/test_repository_hygiene.py`
- [x] T009 [US1] Add failing symlink/non-regular/path-safety and no-mutation tests in `tests/unit/test_repository_hygiene.py`
- [x] T010 [US1] Add failing Git-index/loose-ref/linked-worktree metadata tests in `tests/unit/test_repository_hygiene.py`
- [x] T011 [US1] Add failing composition coverage for the new validator gate in `tests/test_repository_validation.py`

### Implementation for User Story 1

- [x] T012 [US1] Implement immutable finding/report models and strict rendering in `scripts/audit_repository_hygiene.py`
- [x] T013 [US1] Implement bounded Git inventory, worktree classification and SHA-256 comparison in `scripts/audit_repository_hygiene.py`
- [x] T014 [US1] Implement explicit safe Git-metadata discovery in `scripts/audit_repository_hygiene.py`
- [x] T015 [US1] Compose the read-only audit into `scripts/validate_repository.py`
- [x] T016 [US1] Run focused tests and verify the audit contract and mutation-free invariant
- [x] T017 [US1] Revalidate the exact live inventory; stop if any candidate is missing, new, unsafe or newer than canonical
- [x] T018 [US1] Remove exactly the approved 151 worktree copies and four inactive Git-index copies, preserving all canonical files
- [x] T019 [US1] Run the post-clean audit, canonical-hash comparison, `git status` and `git fsck`; record results in `specs/031-repository-hygiene/implementation-notes.md`
- [x] T020 [US1] Add prevention and fail-closed recovery guidance to `docs/17_CODEBASE_HYGIENE.md`

**Checkpoint**: US1 passes independently and the working tree contains only intentional F031 changes.

---

## Phase 4: User Story 2 — Maintain complex workflows safely (P2)

**Goal**: Remove four function-level policy exceptions through behavior-preserving extraction.

**Independent Test**: Focused CLI, Markdown and scanner suites pass before/after, all original functions are below the
normal threshold, combined original span falls by at least 40 percent and no new exception appears.

### CLI characterization and extraction

- [x] T021 [US2] Add or confirm parser characterization for every command/default/choice group in `tests/integration/test_cli.py` and `tests/integration/test_cli_mcp.py`
- [x] T022 [US2] Add or confirm JSON/human output characterization across all renderer families in `tests/integration/test_cli.py`
- [x] T023 [US2] Extract bounded command-group builders into `src/openardp/interfaces/cli_arguments.py` while preserving `cli._parser`
- [x] T024 [US2] Extract bounded body-free renderers into `src/openardp/interfaces/cli_output.py` while preserving `cli._success`
- [x] T025 [US2] Run focused CLI suites plus Ruff/mypy for the affected interface modules

### Markdown characterization and extraction

- [x] T026 [US2] Add missing Markdown transition/boundary equivalence cases in `tests/unit/test_text_parser.py`
- [x] T027 [US2] Decompose heading, fence, list, quote and paragraph transitions in `src/openardp/adapters/text_parser.py`
- [x] T028 [US2] Run the full text-parser, ingestion, search and semantic-candidate regression slice

### Local-watch characterization and extraction

- [x] T029 [US2] Add missing traversal/overflow/race/device/link equivalence cases in `tests/integration/test_local_watch.py`
- [x] T030 [US2] Decompose directory enumeration, admission and entry projection in `src/openardp/adapters/local_watch.py`
- [x] T031 [US2] Run watcher contract, scanner, service and catalog regression suites

### Maintainability closure

- [x] T032 [US2] Remove the four obsolete function exceptions and lower any safely reduced module ceiling in `quality/maintainability-policy.json`
- [x] T033 [US2] Run AST span and Ruff complexity comparison; record exact before/after results in `specs/031-repository-hygiene/implementation-notes.md`
- [x] T034 [US2] Run maintainability and architecture validators and prove no new/grown exception or dependency cycle

**Checkpoint**: US2 passes independently with behavior equivalence and measurable maintainability gain.

---

## Phase 5: User Story 3 — Verify and sustain a 10/10 hygiene state (P3)

**Goal**: Make every completion claim reproducible and prevent policy/documentation drift.

**Independent Test**: A clean checkout follows `quickstart.md`; all ten gates have exact passing evidence and any injected
finding causes the relevant gate to fail.

### Tests and governance

- [x] T035 [US3] Add the F031 audit/tool/docs to repository required-file and drift validation in `scripts/validate_repository.py`
- [x] T036 [US3] Update architecture/module ownership and hygiene contract in `docs/02_ARCHITECTURE.md` and `docs/17_CODEBASE_HYGIENE.md`
- [x] T037 [US3] Add F031 to `spec-kit/FEATURE_MAP.md`, `CHANGELOG.md` and affected contributor validation guidance
- [x] T038 [US3] Complete all exact commands, tradeoffs, residual risks and rollback evidence in `specs/031-repository-hygiene/implementation-notes.md`

### Ten-gate validation

- [x] T039 [US3] Run Ruff check/format and strict mypy and record SC-005
- [x] T040 [US3] Run the full pytest suite with branch coverage at or above 85 percent and record SC-006
- [x] T041 [US3] Run repository, generated-artifact, pre-commit and package-build gates and record SC-007
- [x] T042 [US3] Run Spec Kit convergence and record zero unresolved critical/high findings
- [x] T043 [US3] Push only after local convergence, open one PR, trigger one ready three-platform matrix and record exact check URLs/results for SC-008
- [x] T044 [US3] Merge normally, synchronize `main`, prune the F031 branches and record SC-010

**Checkpoint**: SC-001–SC-010 all pass; otherwise the result is not reported as 10/10.

---

## Dependencies & Execution Order

- Phase 1 precedes all implementation because it freezes the evidence baseline.
- Phase 2 blocks Phase 3–5.
- US1 precedes source refactoring so the working tree is trustworthy.
- Within US2, CLI, Markdown and watcher slices are sequential commits/checkpoints to make regressions attributable.
- Policy exceptions are removed only after all three refactoring slices pass.
- US3 depends on US1 and US2 and is the only phase authorized to claim completion.

## Requirement Traceability

| Requirements | Tasks |
|---|---|
| FR-001, FR-010–FR-014 | T021–T034 |
| FR-002–FR-006 | T008–T016 |
| FR-007–FR-009 | T017–T020 |
| FR-015 | T011, T015, T034–T035 |
| FR-016 | T036–T038 |
| FR-017–FR-019 | T039–T044 |
| FR-020 | T001–T003, T019, T033, T038–T044 |
| SC-001–SC-002 | T008–T020 |
| SC-003–SC-004 | T021–T034 |
| SC-005–SC-010 | T035–T044 |

## Implementation Strategy

Commit coherent checkpoints in order: (1) complete Spec Kit planning, (2) audit and verified cleanup, (3) CLI
extraction, (4) Markdown/scanner extraction and policy tightening, (5) documentation/convergence. Keep the PR draft or
local until all gates pass; transition to ready once so the cost-controlled full matrix runs once.
