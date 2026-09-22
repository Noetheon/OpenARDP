# Tasks: Secure development test runner

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [supply-chain checklist](checklists/supply-chain.md)

**Governance**: High assurance. Existing tests already exercise the entire gate; this dependency-only package needs no test code that would merely mirror a version constraint.

## Phase 1: Setup

**Purpose**: Confirm exact security and repository baseline before mutation.

- [x] T001 Capture current pytest/dev requirement, lock version, advisory target and plugin versions in `specs/039-pytest-security-maintenance/research.md`.

## Phase 2: Foundational

**Purpose**: Ensure scope and requirements are unambiguous.

- [x] T002 Complete quality review of `specs/039-pytest-security-maintenance/spec.md`, `plan.md` and `checklists/supply-chain.md` with no unresolved critical/high finding.

## Phase 3: User Story 1 — Safe, reproducible contributor test run (P1)

**Goal**: Patched, locked pytest dev environment with unchanged project behavior and quality policy.

**Independent Test**: A locked sync resolves the patched pytest; existing complete gate and scoped advisory audit pass without unrelated lock drift.

- [x] T003 [US1] Raise only the pytest dev-group requirement to the patched floor in `pyproject.toml`.
- [x] T004 [US1] Regenerate only the pytest package resolution and hashes in `uv.lock`, preserving other locked package versions.
- [x] T005 [US1] Diff `pyproject.toml` and `uv.lock` against the worktree base and reject unrelated runtime or optional version changes.
- [x] T006 [US1] Run a representative locked pytest/plugin/socket check and the dependency audit; record preliminary results in `specs/039-pytest-security-maintenance/implementation-notes.md`.

**Checkpoint**: Dependency compatibility is preliminarily verified. Full repository gates run after convergence and artifact compaction because the existing repository contract requires completed feature records.

## Phase 4: Polish and handoff

- [x] T007 Record tradeoffs, residual optional advisories, GitHub alert boundary, rollback and exact validation commands in `specs/039-pytest-security-maintenance/implementation-notes.md`.
- [x] T008 Record F039 as security maintenance outside the paused product roadmap in `spec-kit/FEATURE_MAP.md` and verify the temporary `.specify/feature.json` locator points to F039 during this lifecycle.

## Dependencies

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → convergence → compact transient planning files and restore F038 locator → full locked gates and final evidence. No parallel mutation: dependency files and evidence depend on the preceding result. Remote CI follows a reviewed push/PR and is not represented as a completed local task.

## Implementation strategy

One dev-tool security fix, one lock regeneration, existing full tests, then bounded documentation and review. Stop on incompatible resolution or failed unchanged gate; do not expand into optional model dependency upgrades.
