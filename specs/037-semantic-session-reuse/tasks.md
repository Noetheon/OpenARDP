# Tasks: Bounded semantic session reuse

**Scope**: F037, high assurance. Tests precede their implementation. Parallel tracks touch disjoint source/test files. No dependent feature starts before convergence and merge.

## Phase 1: Specification and analysis

- [x] T001 Specify acceptance, clarify lifecycle/limits and complete requirements checklist in `spec.md` and `checklists/requirements.md` (FR-001–008, SC-001–004).
- [x] T002 Record bounded design and contract/version/trust effects in `plan.md`, `research.md`, `data-model.md`, `contracts/session-lifecycle.md` and `quickstart.md` (FR-001–008).
- [x] T003 Analyze specification, plan and tasks against the constitution; resolve critical/high findings before implementation (FR-008).

## Phase 2: User story 1 — MCP session reuse

- [x] T004 [P] [US1] Add failing real-MCP regressions for repeated preparations, full estimator switches, lexical interleaving and failure/recovery in `tests/integration/test_mcp_semantic_session.py`; retain source-change coverage from `tests/integration/test_semantic_candidates.py` and add warm-up then CAS tampering and catalog trust/reference tampering through real MCP dispatch, asserting body-free failure and no stale bundle delivery (FR-001–003, FR-007–008, SC-001, SC-003–004).
- [x] T005 [US1] Implement one estimator-bound compiler slot and failure eviction in `src/openardp/interfaces/mcp_server.py`; run the preceding tests (FR-001–003, FR-007, SC-001, SC-003).

## Phase 3: User story 2 — bounded provider scope replacement

- [x] T006 [P] [US2] Add failing worker regressions in `tests/unit/test_e5_semantic.py` or a focused sibling for disjoint scopes, overlap, shared object vectors, conflict/invalid bounds before mutation, one active handle, changed-limit rejection and direct-score invalidation (FR-004–008, SC-002–004).
- [x] T007 [US2] Implement prevalidated unique-object retention and one limit-bound corpus in `src/openardp/adapters/e5_semantic.py`; run preceding tests (FR-004–007, SC-002–003).

## Phase 4: Convergence and delivery

- [ ] T008 Run combined semantic/MCP/authority regressions and all required Ruff, format, mypy, pytest/coverage, governance, maintainability and packaging gates; record exact results in `implementation-notes.md` (FR-008, SC-004).
- [x] T009 Update relevant `docs/`, `CHANGELOG.md`, `spec-kit/FEATURE_MAP.md` and durable implementation notes for bounded cache behavior and limits; preserve frozen benchmark trees (FR-007–008).
- [ ] T010 Independently converge acceptance against code/tests/evidence; append gap tasks if required, then complete one scoped PR and applicable three-platform CI before merge (FR-008, SC-001–004).

## Dependencies and traceability

T001 -> T002 -> T003. After T003, T004 -> T005 and T006 -> T007 may run in parallel. Both tracks precede T008/T009; T010 closes the package. Every functional requirement and buildable success criterion is mapped above. The later real-task pilot is outside F037 and cannot be used to claim success here.
