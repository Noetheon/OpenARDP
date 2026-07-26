# Tasks: Strategic Realignment and Contract Boundary

**Input**: Design documents from `specs/005A-strategic-realignment/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/governance-migration.md`, completed checklists

**Tests**: Mandatory. Repository authority, public claims, roadmap sequencing, ADR relationships, contract maturity, and runtime neutrality require deterministic offline validation. Author failing repository-contract tests before integrating the governed documentation.

**Organization**: Tasks are dependency-ordered and grouped by independently reviewable user outcome. F006 work is explicitly excluded.

## Phase 1: Setup and migration boundary

**Purpose**: Record the clean rollback point, restate acceptance, and freeze the runtime surface.

- [x] T001 Confirm the clean F005 merge base and selected feature, then restate all F005A acceptance criteria in `specs/005A-strategic-realignment/implementation-notes.md`
- [x] T002 Record the pre-change locked quality-gate results and a path-scoped runtime/schema/dependency baseline in `specs/005A-strategic-realignment/implementation-notes.md`
- [x] T003 Account for every non-platform blueprint overlay file and its reviewed destination in `specs/005A-strategic-realignment/implementation-notes.md`
- [x] T004 Add failing governance contract tests for constitution version/clauses, canonical authority paths, and exact roadmap order in `tests/test_repository_contract.py`
- [x] T005 Add failing governance contract tests for prompt inventory, ADR statuses/supersession, experimental contract labels, valid receipt JSON, prohibited standards claims, and overlay hygiene in `tests/test_repository_contract.py`
- [x] T006 Run the focused new tests, confirm they fail only for missing F005A artifacts, and record the red-state evidence in `specs/005A-strategic-realignment/implementation-notes.md`

---

## Phase 2: Foundational governance and decision boundary

**Purpose**: Establish the binding project-wide rules and decisions required by every user story.

**⚠️ CRITICAL**: No positioning, roadmap, or contract guidance is authoritative until this phase is complete.

- [x] T007 Amend `.specify/memory/constitution.md` to version 2.0.0 with a Sync Impact Report, preserving all 1.0.0 obligations while adopting implementation-first, reuse, thin-projection, accelerator-verification, fair-baseline, feature-isolation, cross-platform, and evolution rules
- [x] T008 Mirror the ratified constitution exactly in `spec-kit/CONSTITUTION_SOURCE.md` and add the labelled adoption source `spec-kit/CONSTITUTION_V3_SOURCE.md`
- [x] T009 Add accepted ADRs `docs/adr/0007-implementation-first.md`, `docs/adr/0008-preserve-provider-native-representations.md`, `docs/adr/0009-indexes-are-non-authoritative.md`, and `docs/adr/0010-contracts-before-adapters.md`
- [x] T010 Annotate partial supersession in `docs/adr/0001-use-docling-as-default-parser.md` and defer the unaccepted packaging decision in `docs/adr/0005-portable-zip-runtime-cas.md` to Feature 014
- [x] T011 Update `AGENTS.md` so the architecture boundary, evidence verification, implementation-first posture, and full blocking lifecycle agree with Constitution 2.0.0 without weakening existing engineering rules
- [x] T012 Run focused constitution/ADR/authority tests and record the passing foundational evidence in `specs/005A-strategic-realignment/implementation-notes.md`

**Checkpoint**: The live repository has one binding strategy and four accepted decisions, with historical relationships intact.

---

## Phase 3: User Story 1 — Trust the current project claims (Priority: P1)

**Goal**: Make implemented status and external claims accurate from the repository entry points.

**Independent Test**: Reviewers can classify every material claim in the entry points and find no stale “no search” or unqualified standards statement.

- [x] T013 [US1] Reconcile `README.md` with Features 001–005, implementation-first positioning, experimental contracts, current limitations, evidence links, working-name caveat, and the next feature boundary
- [x] T014 [US1] Reconcile `START_HERE.md`, `docs/00_EXECUTIVE_BRIEF.md`, `docs/01_PRODUCT_REQUIREMENTS.md`, and `docs/08_ROADMAP_AND_GOVERNANCE.md` with the same status and claims discipline
- [x] T015 [US1] Update `CHANGELOG.md`, `VALIDATION.md`, and `specs/README.md` with F005 completion and F005A’s documentation-only scope
- [x] T016 [US1] Add `docs/00_REVISED_EXECUTIVE_BRIEF.md` and `docs/01_VISION_AND_POSITIONING.md` with explicit relationship to the canonical entry points and evidence-state vocabulary
- [x] T017 [US1] Run focused status/claim tests and repository searches; record the passing US1 evidence in `specs/005A-strategic-realignment/implementation-notes.md`

**Checkpoint**: A first-time reader sees accurate current behavior and qualified future intent.

---

## Phase 4: User Story 2 — Follow one authoritative roadmap (Priority: P2)

**Goal**: Adopt one dependency-ordered continuation sequence and remove obsolete future execution instructions.

**Independent Test**: The canonical map and active prompts agree exactly on 005A–017, and no old prompt offers a competing next step.

- [x] T018 [US2] Replace `spec-kit/FEATURE_MAP.md` with the reconciled 005A–017 map and add labelled source `spec-kit/FEATURE_MAP_V3.md`
- [x] T019 [US2] Replace `spec-kit/OPERATING_PROCEDURE.md` with the complete blocking lifecycle and add labelled source `spec-kit/OPERATING_PROCEDURE_V3.md`
- [x] T020 [US2] Add active prompts `spec-kit/feature-prompts/005A-strategic-realignment.md` through `spec-kit/feature-prompts/017-microsoft-graph-design-spike.md`
- [x] T021 [US2] Remove obsolete unimplemented prompts `spec-kit/feature-prompts/006-docling-adapter.md` through `014-microsoft-graph-spike.md` only after their replacements and canonical map exist
- [x] T022 [US2] Reconcile `spec-kit/README.md`, `spec-kit/FIRST_CODEX_SESSION.md`, `docs/09_CODEX_EXECUTION_PLAN.md`, `docs/12_SPEC_KIT_INTEGRATION.md`, and `docs/14_MIGRATION_FROM_PREVIOUS_BLUEPRINT.md`
- [x] T023 [US2] Add `codex/MASTER_SESSION_PROMPT.md` with a repository-governance subordination notice and no claim that prompt text grants authority
- [x] T024 [US2] Run exact roadmap/prompt/lifecycle tests and record the passing US2 evidence in `specs/005A-strategic-realignment/implementation-notes.md`

**Checkpoint**: Contributors have one ordered workflow and cannot accidentally execute the superseded F006 plan.

---

## Phase 5: User Story 3 — Evolve experimental contracts safely (Priority: P3)

**Goal**: Document the native/evidence/index/version boundary before Feature 006 defines its first contract.

**Independent Test**: Integrators can classify all artifact families and version axes without treating examples as stable schemas.

- [x] T025 [US3] Add experimental design guidance `contracts/README.md`, `contracts/example-selection-receipt.json`, and `conformance/README.md` with explicit F006/F016 ownership
- [x] T026 [US3] Add `docs/02_NORMATIVE_SCOPE_CANDIDATE.md`, `docs/03_NON_GOALS.md`, and `docs/05_TARGET_ARCHITECTURE.md`
- [x] T027 [US3] Add `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md` with independent version axes, rejection/migration rules, deprecation discipline, and evidence-based stabilization
- [x] T028 [US3] Reconcile `docs/02_ARCHITECTURE.md`, `docs/03_DATA_MODEL_AND_PACKAGE.md`, `docs/04_INCREMENTAL_PROCESSING.md`, `docs/05_CONTEXT_COMPILER_AND_MCP.md`, and `docs/10_PRIOR_ART_AND_BUILD_DECISIONS.md` so no second full IR, authoritative index, or decided custom export remains
- [x] T029 [US3] Run focused artifact-boundary, contract-maturity, JSON, and ADR relationship tests; record the passing US3 evidence in `specs/005A-strategic-realignment/implementation-notes.md`

**Checkpoint**: Contract intent is clear, experimental, and strictly precedes adapter implementation.

---

## Phase 6: User Story 4 — Operate and adopt conservatively (Priority: P4)

**Goal**: Make prior-art, non-goal, benchmark, release, security, privacy, operations, and supply-chain obligations discoverable.

**Independent Test**: An adoption review finds each risk area, its current status, and the future feature that owns undelivered controls.

- [x] T030 [US4] Add `docs/04_PRIOR_ART_AND_DD.md`, `docs/06_SECURITY_MODEL_V2.md`, `docs/07_BENCHMARK_AND_EVIDENCE_PLAN.md`, `docs/08_RELEASE_AND_ADOPTION_STRATEGY.md`, and `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md`
- [x] T031 [US4] Reconcile `docs/06_SECURITY_THREAT_MODEL.md`, `docs/07_TEST_AND_BENCHMARK_STRATEGY.md`, and `docs/11_OPERATIONAL_AND_ENTERPRISE_REQUIREMENTS.md` with bounded-isolation, evidence, privacy, retention/recovery, and supply-chain language
- [x] T032 [US4] Reconcile `docs/13_STEP_BY_STEP_USER_GUIDE.md` so current commands are distinguished from future roadmap behavior
- [x] T033 [US4] Run adoption-risk coverage and unsupported-claim checks; record the passing US4 evidence in `specs/005A-strategic-realignment/implementation-notes.md`

**Checkpoint**: Operational and adoption guidance is complete without presenting future controls as delivered.

---

## Phase 7: Polish, validation, and convergence

**Purpose**: Prove migration completeness, runtime neutrality, repository quality, and clean Spec Kit convergence.

- [x] T034 Add deterministic relative-link, source-label, overlay-accounting, and preserved-surface checks to `scripts/validate_repository.py` where not already covered by pytest
- [x] T035 Run every scenario in `specs/005A-strategic-realignment/quickstart.md` and record exact observed results in `specs/005A-strategic-realignment/implementation-notes.md`
- [x] T036 Run `git diff --check`, JSON validation, prohibited-claim searches, blueprint/platform-metadata hygiene checks, and path-scoped no-runtime-diff validation
- [x] T037 Run the complete locked gates (`ruff check`, `ruff format --check`, strict `mypy src`, `pytest`, `pre-commit run --all-files`, repository validator, `uv build`, isolated wheel import) and record exact results
- [x] T038 Re-run Spec Kit analysis and convergence against spec/plan/tasks/constitution/ADRs/docs/tests/diff, append any remediation tasks rather than rewriting completed tasks, and close every critical/high finding
- [x] T039 Finalize `specs/005A-strategic-realignment/implementation-notes.md` with tradeoffs, residual risks, rollback instructions, and remote-CI placeholders

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependency beyond the green F005 merge base.
- **Foundational (Phase 2)**: Depends on Phase 1 and blocks every user story.
- **US1 (Phase 3)**: Depends on authoritative governance; establishes truthful entry points.
- **US2 (Phase 4)**: Depends on Phase 2 and should follow US1 so the entry points can link to the adopted roadmap.
- **US3 (Phase 5)**: Depends on the accepted representation/index/contracts decisions and adopted Feature 006 boundary.
- **US4 (Phase 6)**: Depends on claim vocabulary and roadmap ownership established by US1–US3.
- **Polish (Phase 7)**: Depends on all user stories.

### Within Each Phase

- New repository-contract tests MUST be observed failing before governed files are integrated.
- Canonical artifacts are updated before their labelled adoption sources are linked.
- Replacement prompts and map exist before obsolete prompts are removed.
- ADRs are accepted before dependent architectural documentation is asserted.
- A phase checkpoint must pass before the next phase begins.

### Parallel Opportunities

- Within US3 and US4, independent new documents may be curated in parallel after their governing ADRs exist.
- Validation commands in T036 are independent but their results are recorded together.

## Implementation Strategy

### Minimum coherent migration

1. Freeze and test the boundary.
2. Ratify Constitution 2.0.0 and ADRs 0007–0010.
3. Correct current claims.
4. Adopt one roadmap and replace obsolete prompts.
5. Add experimental contract and adoption guidance.
6. Prove zero runtime drift and full convergence.

### Rollback

Revert the isolated F005A commit or merge commit. The feature adds no dependency, runtime behavior, public schema, persisted data, or workspace migration, so no operational rollback procedure is required.
