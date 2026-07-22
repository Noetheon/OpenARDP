# Tasks: Repository Baseline

**Input**: Design documents from `specs/001-repository-baseline/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/repository-baseline.md`,
`quickstart.md`, and both requirements checklists are complete.

**Tests**: Required by the Constitution and feature specification. Each story writes or extends its negative contract tests
before the corresponding implementation.

## Phase 1: Setup and implementation record

**Purpose**: Establish the feature-local acceptance/evidence record and prevent local artifacts from contaminating the
baseline.

- [x] T001 Restate FR-001–FR-018 and SC-001–SC-008 as an acceptance/evidence matrix in `specs/001-repository-baseline/implementation-notes.md`
- [x] T002 [P] Expand portable cache, coverage, operating-system and environment-secret exclusions in `.gitignore`
- [x] T003 [P] Add a typed repository-root fixture for contract tests in `tests/conftest.py`

---

## Phase 2: Foundational test and packaging boundaries

**Purpose**: Create the shared test-first boundary that blocks accidental later-feature behavior.

**Critical**: Complete before user-story implementation.

- [x] T004 Replace premature behavior tests with failing baseline package/version/boundary/absence contracts in `tests/test_package.py` and remove `tests/test_core.py` and `tests/test_models.py`
- [x] T005 Add the initial repository metadata, required-file, public JSON-Schema syntax and tracked-agent allowlist assertions in `tests/test_repository_contract.py`

**Checkpoint**: Tests describe the desired baseline and are expected to fail against the blueprint scaffold.

---

## Phase 3: User Story 1 — Reproduce a clean development environment (Priority: P1) 🎯 MVP

**Goal**: A clean checkout reproduces a locked Python 3.12 development environment and exposes only the minimal package
contract.

**Independent Test**: Run locked synchronization, import the package/version and five namespaces, build distributions and
confirm no product modules or console entry point exist.

### Tests for User Story 1

- [x] T006 [US1] Extend `tests/test_package.py` with installed-distribution version, `py.typed`, wheel-content and forbidden-console-script assertions
- [x] T007 [US1] Extend `tests/test_repository_contract.py` with Python-series, empty-runtime-dependency, Apache-license and uv-tool-version assertions

### Implementation for User Story 1

- [x] T008 [US1] Remove premature product modules `src/openardp/core.py`, `src/openardp/domain/models.py` and `src/openardp/interfaces/cli.py`, then document every namespace `__init__.py` under `src/openardp/`
- [x] T009 [US1] Add the typing marker in `src/openardp/py.typed` and keep `src/openardp/__init__.py` limited to the package version contract
- [x] T010 [US1] Rework build/package/runtime metadata, Python 3.12 range, Apache license declaration, uv requirement and locked development group in `pyproject.toml`
- [x] T011 [US1] Generate and review the exact dependency graph in `uv.lock` with the repository-required uv version
- [x] T012 [US1] Prove locked synchronization plus wheel/sdist build and isolated wheel import using `uv.lock`, `dist/` and `tests/test_package.py`

**Checkpoint**: User Story 1 is independently usable as the minimal repository MVP.

---

## Phase 4: User Story 2 — Run one authoritative local quality gate (Priority: P2)

**Goal**: The documented Ruff, format, strict mypy and offline pytest/coverage gates share one locked toolchain and are
available at commit time.

**Independent Test**: Run each mandatory command and all pre-commit hooks; prove an attempted socket operation is blocked
and the test command itself enforces branch coverage and the threshold.

### Tests for User Story 2

- [x] T013 [US2] Add an explicit pytest-socket negative contract and quality-configuration assertions in `tests/test_repository_contract.py`
- [x] T014 [US2] Add pre-commit command/parity/configuration assertions in `tests/test_repository_contract.py`

### Implementation for User Story 2

- [x] T015 [US2] Configure Ruff docstrings, strict mypy, required pytest plugins, socket blocking, branch coverage and 85 percent failure threshold in `pyproject.toml`
- [x] T016 [US2] Add locked local Ruff, format, mypy and pytest hooks in `.pre-commit-config.yaml`
- [x] T017 [US2] Validate and execute the complete commit-time gate with `.pre-commit-config.yaml` and record results in `specs/001-repository-baseline/implementation-notes.md`

**Checkpoint**: User Stories 1 and 2 both pass through the same local locked environment.

---

## Phase 5: User Story 3 — Receive least-privilege automated validation (Priority: P3)

**Goal**: Pull requests and main-branch pushes declare the full quality matrix without mutable actions, write authority,
persistent checkout credentials or lock mutation.

**Independent Test**: Run repository-policy tests against the workflow, verify each action SHA against its reviewed
release tag and retain the successful GitHub-hosted Ubuntu, macOS and Windows run as external execution evidence.

### Tests for User Story 3

- [x] T018 [US3] Add CI trigger/matrix/permission/credential/action-SHA/release-comment/lock/no-cache/no-diff policy assertions in `tests/test_repository_contract.py`

### Implementation for User Story 3

- [x] T019 [US3] Replace mutable actions with reviewed full-SHA pins and add read-only permissions, non-persistent credentials, timeout, no-cache setup and fail-fast false in `.github/workflows/ci.yml`
- [x] T020 [US3] Make `.github/workflows/ci.yml` run locked sync, pre-commit config validation, all four quality gates, package build and tracked-diff verification on Linux, macOS and Windows

**Checkpoint**: The CI contract is statically proven locally; actual remote matrix results are not overstated.

---

## Phase 6: User Story 4 — Understand governance and bounded scope (Priority: P4)

**Goal**: Contributors and security reporters can follow coherent, offline-validated repository guidance while later
product behavior stays absent.

**Independent Test**: Run the validator and pytest against real documents plus synthetic broken-link/governance fixtures;
all internal targets and policy relationships pass without any network access.

### Tests for User Story 4

- [x] T021 [US4] Add validator tests for Markdown files, headings, duplicate anchors, exact case, URL encoding, CRLF, inline/fenced code and external URLs in `tests/test_repository_validation.py`
- [x] T022 [US4] Add negative validator tests for missing/empty targets, path escape, external symlinks, absolute/POSIX/Windows/backslash paths and `file:`/`sandbox:` schemes in `tests/test_repository_validation.py`
- [x] T023 [US4] Add governance discoverability, license/version/command consistency and deterministic diagnostic-order tests in `tests/test_repository_validation.py`

### Implementation for User Story 4

- [x] T024 [US4] Implement the typed, standard-library, no-network Markdown and governance validator in `scripts/validate_repository.py`
- [x] T025 [P] [US4] Add the full Apache-2.0 text and Unreleased baseline history in `LICENSE` and `CHANGELOG.md`
- [x] T026 [P] [US4] Expand setup, locked commands, tests-first expectations, Spec Kit flow and pull-request rules in `CONTRIBUTING.md`
- [x] T027 [P] [US4] Define supported status, private-first reporting, required report details, response expectations and coordinated disclosure in `SECURITY.md`
- [x] T028 [P] [US4] Replace pre-bootstrap instructions with current clone/setup/validation/status guidance and link governance files in `README.md` and `START_HERE.md`
- [x] T029 [US4] Mark the completed bootstrap checks and current feature boundary in `spec-kit/AFTER_BOOTSTRAP_CHECKLIST.md`

**Checkpoint**: All four user stories are independently documented and testable without later OpenARDP product behavior.

---

## Phase 7: Cross-cutting validation and convergence evidence

**Purpose**: Run every local gate, challenge negative contracts and make the evidence truthful.

- [x] T030 Run `uv lock --check`, locked synchronization, the four mandatory gates, pre-commit validation/all-files, build and offline/no-sync pytest; record exact results in `specs/001-repository-baseline/implementation-notes.md`
- [x] T031 [P] Exercise stale/missing lock rejection and representative lint/format/type/test/coverage failures in a disposable copy; record outcomes in `specs/001-repository-baseline/implementation-notes.md`
- [x] T032 Update current Spec Kit/bootstrap/feature gate evidence, known platform limits and remaining risks in `VALIDATION.md`, `BLUEPRINT_INVENTORY.txt` and `CHANGELOG.md`
- [x] T033 Run repository validation, `git diff --check`, inspect the complete diff and confirm no unintended or generated local files are tracked
- [x] T034 Reconcile FR-001–FR-018 and SC-001–SC-008 with the repository in `specs/001-repository-baseline/implementation-notes.md` and complete every satisfied task/checklist item

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1**: Starts immediately.
- **Phase 2**: Depends on Phase 1 and deliberately creates failing contracts before implementation.
- **User Story 1 (Phase 3)**: Depends on Phase 2 and establishes the installable/locked MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1 because the quality tools come from its locked development group.
- **User Story 3 (Phase 5)**: Depends on User Story 2 because CI invokes the authoritative local gates.
- **User Story 4 (Phase 6)**: Depends on the pytest foundation but can otherwise proceed alongside CI work after User
  Story 1.
- **Phase 7**: Depends on all user stories.

### User Story Dependencies

```text
US1 reproducible environment
 ├──> US2 local quality gate ──> US3 automated validation
 └──> US4 governance and offline documentation validation
                         US3 + US4 ──> convergence evidence
```

### Parallel Opportunities

- T002 and T003 touch independent setup files.
- T013 and T014 are sequential because both update `tests/test_repository_contract.py`.
- T021, T022 and T023 are sequential because all three update `tests/test_repository_validation.py`.
- T025, T026, T027 and T028 edit independent governance documents after their tests exist.
- T031 can run in a disposable copy while T032 prepares evidence text, but final recorded results must be reconciled.

## Parallel Example: User Story 4

```text
Task T021: positive Markdown/anchor/external-link tests
→ Task T022: path-safety and non-portable-link negative tests
→ Task T023: governance/consistency/diagnostic tests
→ Task T024: validator implementation
→ Tasks T025–T028: independent governance documents
```

## Implementation Strategy

### MVP first

1. Complete Phases 1 and 2.
2. Complete User Story 1 through T012.
3. Run its independent locked-sync/import/build checks.
4. Continue only after the package exposes no later-feature behavior.

### Incremental delivery

1. Add User Story 2 and prove identical local/pre-commit gates.
2. Add User Story 3 and prove the least-privilege workflow contract statically.
3. Add User Story 4 and prove documentation/governance validation offline.
4. Run Phase 7, analyze, implement any discovered gaps and converge before committing feature 001.

## Format Validation

- All 34 tasks use the required checkbox and sequential `T###` identifier.
- User-story tasks include `[US1]` through `[US4]`; setup/foundation/cross-cutting tasks intentionally do not.
- `[P]` appears only where separate files allow parallel work.
- Every task names the repository path or artifact it changes or validates.
