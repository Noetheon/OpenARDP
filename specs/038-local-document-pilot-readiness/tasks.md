# Tasks: Local document pilot readiness

## Specification and analysis

- [x] T001 Specify bounded user workflow, claim/decision limits and high-assurance classification; complete clarification and requirements checklist in `spec.md` and `checklists/requirements.md` (FR-001–008).
- [x] T002 Record minimal design, compatibility, manual data and validation in `plan.md`, `research.md`, `data-model.md` and `quickstart.md` (FR-001–008).
- [x] T003 Complete prospective `contracts/pilot-protocol.md`, then independently analyze spec/plan/tasks/protocol and resolve critical/high findings before implementation (FR-004–006, FR-008, SC-003).

## US1 — source-verifiable human workflow

- [ ] T004 [P] [US1] Add failing explicit/default/JSON, text/structured/handle/empty and C0/DEL/C1/bidi-control and normal-umlaut regressions in `tests/integration/test_cli_context.py` or a focused sibling (FR-001–002, FR-008, SC-001, SC-004).
- [ ] T005 [US1] Add the smallest human bundle renderer and enumerated shared control-character hardening in `src/openardp/interfaces/cli_output.py`; preserve existing JSON, grammar, source and receipt bytes; pass T004 (FR-001–002, SC-001).
- [ ] T006 [US1] Write `docs/30_LOCAL_DOCUMENT_WORKFLOW.md`; smoke-test locked install/init/ingest/reuse/list/context/source inspection/replay in a fresh synthetic workspace and record exact evidence in `implementation-notes.md` (FR-003, SC-002).

## US2 — prospective utility decision

- [ ] T007 [P] [US2] Create empty task/attempt/overhead/review CSVs, pending decision template and concise private-run instructions under `pilots/local-document/v0.1.0/`; cross-check all gates/fields and prohibit fabricated user data (FR-004–006, SC-003).
- [ ] T008 [US2] Align `README.md`, `START_HERE.md`, canonical product/strategy/governance, `docs/29_SEMANTIC_RETRIEVAL_PRODUCT_SURFACE.md`, `CHANGELOG.md` and `spec-kit/FEATURE_MAP.md` with the narrow focus, pause rule and explicit legacy evidence limitations; preserve frozen benchmark/evaluator bytes (FR-007, SC-004).

## Convergence and delivery

- [ ] T009 Update the feature locator expectation in `tests/test_repository_contract.py`; run required locked lint/format/mypy/full pytest/coverage, repository/maintainability/CI audits, build and unchanged-evidence checks; record exact results (FR-008, SC-001–004).
- [ ] T010 Independently converge code, guide, protocol and templates; append gap tasks if needed, preserve lifecycle history and compact final durable records, then pass final governance and all platform CI on one scoped PR before merging (FR-008, SC-001–004).

Dependencies: T001 -> T002 -> T003. Then T004 -> T005 -> T006 may run beside T007 and T008 in disjoint files. T009/T010 follow both tracks. All 8 functional and 4 buildable success requirements are mapped. Real pilot execution cannot begin without real tasks, frozen inputs/assignment and reviewer; F038 claims readiness only.
