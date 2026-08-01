# Tasks: Microsoft Graph Design Spike

**Input**: Design documents from `/specs/017-microsoft-graph-design-spike/`

**Tests**: Required by the feature specification and Constitution Article VIII. Test tasks precede implementation.

## Phase 1: Setup and governance

- [x] T001 Record prompt digest, F016 baseline and acceptance criteria in `implementation-notes.md`
- [x] T002 [P] Accept the mock-only exception and production prohibition in `docs/adr/0016-microsoft-graph-mock-design.md`
- [x] T003 [P] Record official-source decisions in `research.md`
- [x] T004 Freeze connector, permission, threat and data-protection contracts under `contracts/`

## Phase 2: Foundational tests and domain contracts

- [x] T005 Add scope/item/revision/permission model tests in `tests/domain/test_graph.py`
- [x] T006 [P] Add delta/page/policy/state/notification invariant tests in `tests/domain/test_graph.py`
- [x] T007 [P] Add runtime protocol and sanitized exception tests in `tests/contract/test_graph_ports.py`
- [x] T008 Run focused collection before source implementation and record the intentional red result
- [x] T009 Implement scoped identity helpers and pure contracts in `src/openardp/domain/graph.py`
- [x] T010 Implement delta/state protocols and sanitized failures in `src/openardp/ports/graph.py`

## Phase 3: User Story 1 — tenant-scoped atomic delta reconciliation

### Tests

- [x] T011 [P] [US1] Add deterministic mock cursor/scope/private-token tests in `tests/contract/test_graph_ports.py`
- [x] T012 [P] [US1] Add multi-page and last-occurrence-wins tests in `tests/integration/test_graph_sync.py`
- [x] T013 [P] [US1] Add tombstone/update transition and path-independent identity tests
- [x] T014 [P] [US1] Add reset, cycle, page/change limit and malformed-page no-commit tests
- [x] T015 [P] [US1] Add expected-cursor conflict and injected atomic commit failure tests

### Implementation

- [x] T016 [US1] Implement private scoped cursor registry and deterministic page scenarios in `src/openardp/adapters/mock_graph.py`
- [x] T017 [US1] Implement optimistic atomic in-memory state/tombstone store in `src/openardp/adapters/mock_graph.py`
- [x] T018 [US1] Implement bounded page collection and scope/cycle validation in `src/openardp/services/graph_sync.py`
- [x] T019 [US1] Implement whole-cycle last-occurrence reduction and one final commit
- [x] T020 [US1] Implement reset/error results with zero partial publication

## Phase 4: User Story 2 — least-privilege operational boundaries

### Tests

- [x] T021 [P] [US2] Add Retry-After, fallback backoff, exhaustion and over-policy tests
- [x] T022 [P] [US2] Add notification constant-time scope/authenticity/expiry tests
- [x] T023 [P] [US2] Add cross-tenant cursor/item/snapshot confusion tests in `tests/security/test_graph_boundaries.py`
- [x] T024 [P] [US2] Add raw token/secret/path/body/name field and diagnostic leakage tests
- [x] T025 [P] [US2] Prove notification validation performs zero state or adapter mutation

### Implementation

- [x] T026 [US2] Implement bounded 429 retry behavior with injectable sleeper
- [x] T027 [US2] Implement constant-time wakeup-only notification validation
- [x] T028 [US2] Harden every adapter/service boundary with sanitized body-free failures
- [x] T029 [US2] Enforce scope binding and absence of global cross-tenant caches

## Phase 5: User Story 3 — conservative decision evidence

- [x] T030 [P] [US3] Complete permission matrix in `contracts/permission-matrix.md`
- [x] T031 [P] [US3] Complete threat model in `contracts/threat-model.md`
- [x] T032 [P] [US3] Complete data-protection assessment in `contracts/data-protection-assessment.md`
- [x] T033 [US3] Document mock GO/production NO-GO and blockers in `docs/16_MICROSOFT_GRAPH_DESIGN_SPIKE.md`
- [x] T034 [US3] Add repository governance assertions for F017 artifacts and ADR
- [x] T035 [US3] Update feature registry and changelog without altering version claims

## Phase 6: Convergence and publication

- [x] T036 Complete focused tests and update implementation notes with exact evidence
- [x] T037 Run Ruff check/format and strict mypy; record results
- [x] T038 Run full network-blocked pytest, repository validation and build; record results
- [x] T039 Run pre-commit, review full diff and reconcile analysis/checklists/tasks
- [x] T040 Commit/push one F017 change set, open PR, verify all platforms, merge and verify post-merge main CI

## Dependencies and order

```text
Governance -> failing contracts -> domain/ports -> US1 mock/state/service
                                      -> US2 retries/notifications/security
                                      -> US3 decision -> convergence/publication
```

T005-T007 must be red before T009-T010. US1 and US2 tests precede their implementation. No
production adapter or live call is permitted at any phase.

## Format validation

All 40 tasks use required checkboxes, sequential IDs, optional `[P]`, user-story labels and paths.

## Phase 7: Convergence

- [x] T041 Correct the documented focused verification command so it passes independently while preserving the separate full-suite coverage gate per SC-009 (partial)
