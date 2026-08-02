# Tasks: CI Cost and Latency Optimization

**Input**: Design documents from `/specs/019-ci-cost-optimization/`

**Tests**: Required by the specification and Constitution Article VIII. Classifier, audit, estimator and workflow
contract tests precede implementation.

## Phase 1: Setup and evidence baseline

- [x] T001 Record the user request, acceptance criteria, current commit/topology and non-change boundaries in `specs/019-ci-cost-optimization/implementation-notes.md`
- [x] T002 Capture the dated 2026-08-01 aggregate run/job/minute/runner-price baseline in `quality/ci-cost-baseline-2026-08-01.json`
- [x] T003 Update the bounded feature prompt, authoritative map and active feature metadata in `spec-kit/feature-prompts/019-ci-cost-optimization.md`, `spec-kit/FEATURE_MAP.md` and `.specify/feature.json`

## Phase 2: Foundational deterministic CI policy

- [x] T004 [P] Add policy-schema, fail-closed path, deterministic output and cost arithmetic tests in `tests/unit/test_ci_audit.py`
- [x] T005 [P] Replace prior combined-workflow assertions with F019 topology, security and invariant assertions in `tests/test_repository_contract.py`
- [x] T006 Run the new focused tests before implementation and record the intentional failure in `specs/019-ci-cost-optimization/implementation-notes.md`
- [x] T007 Implement strict standard-library policy loading, path classification, workflow audit and cost estimation in `scripts/audit_ci.py`
- [x] T008 Add reviewed safe-skip, platform, stable-check, release-boundary and cache rules in `quality/ci-policy.json`
- [x] T009 Integrate the CI audit into `scripts/validate_repository.py` with deterministic body-free diagnostics

## Phase 3: User Story 1 — preserve authoritative final quality

### Tests

- [x] T010 [US1] Add red contract assertions for one Ubuntu coverage owner, complete three-platform test inventory and single platform-independent gate ownership in `tests/test_repository_contract.py`

### Implementation

- [x] T011 [US1] Replace `.github/workflows/ci.yml` with stable Preflight and Linux/macOS/Windows final quality lanes
- [x] T012 [US1] Retain locked synchronization, socket denial, action SHA pinning, read-only permissions, checkout hardening, timeouts and concurrency in `.github/workflows/ci.yml`
- [x] T013 [US1] Enable lock-keyed setup-uv caching and safe `uv cache prune --ci` without caching `.venv` in `.github/workflows/ci.yml`
- [x] T014 [US1] Prove all local workflow/audit contract tests pass and record exact results in `specs/019-ci-cost-optimization/implementation-notes.md`

## Phase 4: User Story 2 — cheap draft and governance iteration

### Tests

- [x] T015 [US2] Add at least ten governance, mixed, empty, unsafe, unknown, workflow, dependency, source, test and release classification cases in `tests/unit/test_ci_audit.py`
- [x] T016 [US2] Add red workflow assertions for draft, ready-for-review, job-level skip and main-preflight conditions in `tests/test_repository_contract.py`

### Implementation

- [x] T017 [US2] Wire the fail-closed change classifier and stable outputs into `.github/workflows/ci.yml`
- [x] T018 [US2] Implement draft-only preflight, ready full gate, governance-only job skips and non-duplicating `main` behavior in `.github/workflows/ci.yml`
- [x] T019 [US2] Document the Draft-to-Ready operating model and prohibited skip shortcuts in `VALIDATION.md` and `CONTRIBUTING.md`

## Phase 5: User Story 3 — bounded release evidence

### Tests

- [x] T020 [US3] Add red release-trigger, non-draft, path-boundary and unchanged all-platform aggregate assertions in `tests/test_repository_contract.py`

### Implementation

- [x] T021 [US3] Move the unchanged F015 platform evidence and aggregate gate from `.github/workflows/ci.yml` to `.github/workflows/release-evidence.yml`
- [x] T022 [US3] Limit release evidence to manual dispatch, `v*` tags and non-draft release-owned pull requests while retaining immutable artifacts and `NO-GO` assertion
- [x] T023 [US3] Verify release-evidence workflow syntax/contracts locally and record the deliberate trigger tradeoff in `specs/019-ci-cost-optimization/implementation-notes.md`

## Phase 6: User Story 4 — measured enforcement and documentation

- [x] T024 [US4] Recompute the cost snapshot and prove audit/estimate output is byte-identical on two runs
- [x] T025 [P] [US4] Document measured baseline, projected 55–65 percent range, limitations, operations and rollback in `docs/18_CI_COST_AND_QUALITY.md`
- [x] T026 [P] [US4] Synchronize F019 status and unchanged product/release boundaries in `README.md`, `CHANGELOG.md`, `specs/README.md` and `spec-kit/FEATURE_MAP.md`
- [x] T027 [US4] Update `scripts/validate_repository.py` required governance records and ensure no action/dependency/public-contract/version drift

## Phase 7: Convergence and protected publication

- [x] T028 Run focused CI policy/repository suites and record exact results in `specs/019-ci-cost-optimization/implementation-notes.md`
- [x] T029 Run locked Ruff check/format, strict mypy, full offline pytest/coverage and repository validation and record exact results
- [x] T030 Run package build, artifact inspection, pre-commit and clean-diff checks and record exact results
- [x] T031 Reconcile both F019 checklists, `analysis.md`, task completion and implementation notes; run final convergence
- [x] T032 Commit and push one F019 change set, open a private PR, make it ready, verify Preflight plus all three platform jobs, configure strict solo-safe `main` protection, merge, and verify post-merge Preflight

## Dependencies and order

```text
baseline/governance -> failing policy and repository tests -> audit/policy -> core quality lanes
                    -> draft/classification lanes -> release workflow -> evidence/docs
                    -> full local gates -> convergence -> protected remote publication
```

T004 and T005 affect different files and can be prepared together before T006. T010, T016 and T020 are sequential
within `tests/test_repository_contract.py`. Documentation T025 and T026 can proceed after final measured facts exist.

## Independent test criteria

- **US1**: A full-ready event maps to complete tests on all three platforms, only Ubuntu owns coverage and platform-
  independent gates, and all security/cache constraints audit successfully.
- **US2**: Draft and governance-only events skip final platform work via successful job conditions; ready code events run
  it; all unsafe, empty, mixed and unknown classification cases are full.
- **US3**: Ordinary events do not select the release workflow, while manual/tag/release-owned ready PR events retain all
  three evidence jobs and aggregate decision.
- **US4**: Two audits and estimates are byte-identical; stored arithmetic reconciles; documentation clearly separates
  gross model, observed invoice and future uncertainty.

## Format validation

All 32 tasks use checkboxes, sequential IDs, story labels where applicable, explicit repository paths and test-first
ordering. T032 is an immediate publication closeout whose authoritative remote result is reported outside the commit;
if any remote gate fails, the task reopens and the feature does not merge.
