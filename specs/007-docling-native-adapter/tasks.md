# Tasks: Docling Native Adapter

**Input**: Design documents from `specs/007-docling-native-adapter/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/docling-adapter.md`, `quickstart.md`

**Tests**: Every provider, process, persistence, security, contract and CLI behavior is
test-first where practical. Tests use synthetic/redistributable inputs and run with
network disabled.

**Organization**: Tasks are dependency-ordered and grouped by independently testable
user story. F007 ends at rich local ingestion/evidence inspection and does not implement
F008+ behavior.

## Phase 1: Baseline, Dependency and Supply Chain

**Purpose**: Freeze compatibility and prove the selected optional provider graph is
reviewable on all supported platforms.

- [x] T001 Record the exact F006 main commit, local gate, source count and nine-schema/two-vector hashes in `specs/007-docling-native-adapter/implementation-notes.md`
- [x] T002 [P] Add the F007 status/inventory row to `specs/README.md`
- [x] T003 [P] Add failing package tests proving the core imports without Docling and the `docling` extra is exact in `tests/contract/test_docling_dependency.py`
- [x] T004 Add exact optional `docling==2.114.0` metadata and resolve `uv.lock` for Python 3.12/Linux/macOS/Windows in `pyproject.toml` and `uv.lock`
- [x] T005 Verify the resolved provider/component versions and record license, provenance, advisory, model-license and platform findings in `specs/007-docling-native-adapter/research.md`
- [x] T006 Run core-only and all-extras locked installation/import probes and record results in `specs/007-docling-native-adapter/implementation-notes.md`

**Checkpoint**: The provider is optional for consumers, exact for rich installs and
fully locked/reviewed before runtime code.

---

## Phase 2: Foundational Rich Domain and Port Contracts

**Purpose**: Define provider-neutral internal inputs, outputs, limits and persistence
facts before importing Docling.

**⚠️ CRITICAL**: No provider or service implementation begins until this phase passes.

### Tests first

- [x] T007 Add failing media/profile/limit/config-identity tests in `tests/domain/test_rich_ingestion.py`
- [x] T008 [P] Add failing model-bundle manifest path/digest/license/bounds tests in `tests/security/test_docling_boundaries.py`
- [x] T009 [P] Add failing descriptor/candidate/output/bundle/commit invariant tests in `tests/domain/test_rich_ingestion.py`
- [x] T010 [P] Add failing runtime protocol checks that prohibit provider types and require sanitized errors in `tests/contract/test_ingestion_ports.py`
- [x] T011 [P] Add failing local-source classification and existing text-compatibility tests in `tests/integration/test_local_source.py`

### Implementation

- [x] T012 Extend source media classification additively while preserving `TextMediaType` compatibility in `src/openardp/domain/ingestion.py` and `src/openardp/adapters/local_source.py`
- [x] T013 Implement strict limits, model-bundle, recipe, descriptor, candidate/output, bundle, persistence and result models in `src/openardp/domain/rich_ingestion.py`
- [x] T014 Extend the existing parser port with rich protocol/error taxonomy and no provider runtime imports in `src/openardp/ports/parser.py`
- [x] T015 Extend the catalog port with atomic rich-commit/load/list/get shapes in `src/openardp/ports/catalog.py`
- [x] T016 Export only intentional domain/port symbols and update package-surface expectations in `src/openardp/domain/__init__.py`, `src/openardp/ports/__init__.py` and `tests/test_package.py`
- [x] T017 Run the Phase 2 focused tests and record the observed red-to-green transition in `specs/007-docling-native-adapter/implementation-notes.md`

**Checkpoint**: Provider-neutral strict contracts and identity inputs pass with no
Docling import and no public F006 change.

---

## Phase 3: User Story 1 — Ingest Rich Local Documents Offline (Priority: P1) 🎯 MVP

**Goal**: Convert valid DOCX/PPTX and configured PDF bytes in a bounded offline worker,
retain complete native JSON and construct valid F006 evidence.

**Independent Test**: Execute actual provider smoke conversions for deterministic
synthetic DOCX/PPTX, exercise the PDF missing-assets gate, and validate complete native
and projected output without persistence.

### Tests first

- [x] T018 [P] [US1] Add failing deterministic synthetic DOCX/PPTX/PDF fixture-generation and provenance tests in `tests/fixtures/rich/generate_fixtures.py` and `tests/integration/test_docling_smoke.py`
- [x] T019 [P] [US1] Add failing native-export, text-view, heading, table-cell, picture/page and unknown-label projection tests in `tests/unit/test_docling_native.py`
- [x] T020 [P] [US1] Add failing coordinate conversion, ordering, duplicate/cycle, native/output and retrieval-bound tests in `tests/unit/test_docling_native.py`
- [x] T021 [P] [US1] Add failing spawn/offline/network/source-path/version/result-protocol tests in `tests/unit/test_isolated_docling.py`
- [x] T022 [P] [US1] Add failing actual DOCX/PPTX provider smoke and PDF local-assets requirement tests in `tests/integration/test_docling_smoke.py`
- [x] T023 [US1] Add failing F006 native/reference/projection aggregate construction tests in `tests/integration/test_rich_ingestion.py`

### Implementation

- [x] T024 [P] [US1] Implement deterministic synthetic OOXML/PDF fixture generation and commit reviewed outputs under `tests/fixtures/rich/`
- [x] T025 [US1] Implement complete native JSON export validation, deterministic evidence candidate projection and coordinate conversion in `src/openardp/adapters/docling_native.py`
- [x] T026 [US1] Implement actual allowlisted Docling 2.114 conversion with strict offline profile and component/version checks in `src/openardp/adapters/docling_native.py`
- [x] T027 [US1] Implement spawned worker IPC, socket denial, offline environment, portable/output limits and kill/close guard in `src/openardp/adapters/isolated_docling.py`
- [x] T028 [US1] Implement candidate-to-CAS/F006 record construction and pure aggregate validation in `src/openardp/services/rich_ingestion.py`
- [x] T029 [US1] Run the User Story 1 independent tests on actual DOCX/PPTX and record exact provider versions/output counts in `specs/007-docling-native-adapter/implementation-notes.md`

**Checkpoint**: Rich bytes become complete bounded native output plus valid thin F006
records without path/network authority.

---

## Phase 4: User Story 2 — Reuse Exact Native Work Safely (Priority: P2)

**Goal**: Persist rich evidence atomically, verify it completely and avoid provider
invocation for unchanged exact input/recipe.

**Independent Test**: Ingest once, reuse ten times, force reparse, change bytes/recipe,
tamper each object class and upgrade a revision-4 workspace.

### Tests first

- [x] T030 [P] [US2] Add failing migration 4→5, checksum, rollback, newer-schema and restart tests in `tests/integration/test_sqlite_catalog.py`
- [x] T031 [P] [US2] Add failing atomic canonical/converged/diverged attempt commit/load/idempotency/conflict/object-reachability tests in `tests/integration/test_rich_catalog.py`
- [x] T032 [P] [US2] Add failing cache-hit, ten-repeat zero-invocation, changed-source and changed-recipe tests in `tests/integration/test_rich_ingestion.py`
- [x] T033 [P] [US2] Add failing forced-reparse convergence/divergence, append-only attempt and unchanged accepted-head tests in `tests/integration/test_rich_ingestion.py`
- [x] T034 [P] [US2] Add failing descriptor/native/native-record/bundle/reference/projection/retrieval tamper tests in `tests/integration/test_rich_ingestion.py`

### Implementation

- [x] T035 [US2] Add checksummed additive migration 5 for accepted rich links, append-only parse attempts and attempt evidence rows in `src/openardp/adapters/sqlite_migrations.py`
- [x] T036 [US2] Implement atomic canonical/converged/diverged attempt commits, immutable conflict handling, load/list/get and snapshot-safe row decoding in `src/openardp/adapters/sqlite_catalog.py`
- [x] T037 [US2] Extend catalog reachability snapshots to include every rich object without changing existing references in `src/openardp/adapters/sqlite_catalog.py` and `src/openardp/services/reachability.py`
- [x] T038 [US2] Implement complete base-plus-rich CAS/catalog/F006 cache verification in `src/openardp/services/rich_ingestion.py`
- [x] T039 [US2] Implement rich source registration, acquisition, retry/failure, canonical commit, cache hit, force-attempt convergence/divergence and head/event orchestration in `src/openardp/services/rich_ingestion.py`
- [x] T040 [US2] Run User Story 2 independent tests, migration upgrade proof and compatibility checks and record exact results in `specs/007-docling-native-adapter/implementation-notes.md`

**Checkpoint**: Exact rich work is atomically durable and safely reusable without
silently accepting drift.

---

## Phase 5: User Story 3 — Fail Closed Under Parser and Storage Faults (Priority: P3)

**Goal**: Guarantee bounded termination, sanitized diagnostics and absence of incomplete
READY state across hostile failure paths.

**Independent Test**: Inject every specified worker/parser/output/storage failure and
verify process cleanup, failure classification and safe retry.

### Tests first

- [x] T041 [P] [US3] Add failing timeout/crash/cancel/IPC-close/child-leak tests in `tests/unit/test_isolated_docling.py`
- [x] T042 [P] [US3] Add failing network-attempt/provider-version/malformed/partial-result tests in `tests/security/test_docling_boundaries.py`
- [x] T043 [P] [US3] Add failing source/page/native/projection/per-body/aggregate resource-limit tests in `tests/security/test_docling_boundaries.py`
- [x] T044 [P] [US3] Add failing CAS publish/disk-full/catalog-commit/failed-retry tests in `tests/integration/test_rich_ingestion.py`
- [x] T045 [P] [US3] Add failing redaction tests for paths, bodies, native values, tracebacks and provider messages in `tests/security/test_docling_boundaries.py`

### Implementation

- [x] T046 [US3] Complete worker cancellation, timeout, emergency kill and IPC cleanup behavior in `src/openardp/adapters/isolated_docling.py`
- [x] T047 [US3] Complete sanitized provider/output/resource error mapping in `src/openardp/adapters/docling_native.py`, `src/openardp/adapters/isolated_docling.py` and `src/openardp/ports/parser.py`
- [x] T048 [US3] Complete failed-attempt recording and atomic publication cleanup behavior in `src/openardp/services/rich_ingestion.py`
- [x] T049 [US3] Run User Story 3 failure matrix, assert the five-second termination bound and record exact results in `specs/007-docling-native-adapter/implementation-notes.md`

**Checkpoint**: Rich ingestion fails closed and never leaves provider work or incomplete
READY evidence behind.

---

## Phase 6: User Story 4 — Inspect and Resolve Evidence Without Provider Leakage (Priority: P4)

**Goal**: Enumerate, retrieve and resolve exact rich evidence through object-scoped
provider-neutral services and stable CLI envelopes.

**Independent Test**: List one rich document's body-free evidence, fetch one exact body,
resolve valid pointers and reject every unsafe/mismatched pointer without Docling import.

### Tests first

- [x] T050 [P] [US4] Add failing RFC 6901 grammar, escaping, depth, wrong-profile, missing-target and bounded-value tests in `tests/unit/test_docling_native.py`
- [x] T051 [P] [US4] Add failing provider-free aggregate listing, exact retrieval/native fetch and integrity tests in `tests/integration/test_rich_evidence.py`
- [x] T052 [P] [US4] Add failing rich ingest/evidence/get-evidence CLI JSON/human/error/redaction tests in `tests/integration/test_cli_rich.py`
- [x] T053 [P] [US4] Add failing existing text CLI snapshot tests to prove unchanged behavior in `tests/integration/test_cli.py`

### Implementation

- [x] T054 [US4] Implement bounded exact JSON-reference resolution over parsed native values in `src/openardp/adapters/docling_native.py`
- [x] T055 [US4] Implement provider-free rich aggregate listing, verified retrieval and native-object access in `src/openardp/services/rich_evidence.py`
- [x] T056 [US4] Route rich media and add evidence/get-evidence commands with stable bounded envelopes in `src/openardp/interfaces/cli.py`
- [x] T057 [US4] Export intentional rich services/adapters and preserve import-laziness in `src/openardp/adapters/__init__.py` and `src/openardp/services/__init__.py`
- [x] T058 [US4] Run User Story 4 independent and text-compatibility tests and record exact results in `specs/007-docling-native-adapter/implementation-notes.md`

**Checkpoint**: Stored rich evidence is consumable through F006/CAS facts without
provider dependency, pointer authority expansion or text regression.

---

## Phase 7: Documentation, Compatibility and Convergence

**Purpose**: Prove the full feature, supply-chain boundary, migration, packaging and prior
contracts before publication.

- [x] T059 Update installation, rich-ingest/inspection behavior, local asset requirements and current truth in `README.md` and `START_HERE.md`
- [x] T060 [P] Update architecture/data/security/operations guidance for delivered F007 behavior without claiming later features in `docs/03_DATA_MODEL_AND_PACKAGE.md`, `docs/05_TARGET_ARCHITECTURE.md`, `docs/06_SECURITY_MODEL_V2.md` and `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md`
- [x] T061 [P] Update dependency/migration/validation history in `CHANGELOG.md`, `VALIDATION.md` and `schemas/README.md`
- [x] T062 Verify dependency licenses/versions, actual package metadata, no provider import in core-only wheel and all-extras wheel/provider smoke behavior
- [x] T063 Prove byte-for-byte no-diff against base for all nine public schemas, both identity-vector files and the F006 conformance corpus
- [x] T064 Run Ruff, format, native and Windows strict mypy, the complete network-blocked suite, schema/conformance/repository validators, `git diff --check` and distribution builds
- [x] T065 Run the quickstart flows in fresh workspaces, actual DOCX/PPTX smoke, PDF missing-assets gate, repeat/force/change/tamper/failure flows and isolated wheel imports
- [x] T066 Finalize `specs/007-docling-native-adapter/implementation-notes.md` with exact commands, counts, versions, tradeoffs, nondeterminism, residual risks, migration, rollback and remote placeholders
- [x] T067 Run final Spec Kit analysis and resolve every critical/high finding at its originating artifact
- [x] T068 Run Spec Kit convergence; append and implement any remaining tasks without rewriting completed tasks
- [x] T069 Mark F007 locally converged in `specs/007-docling-native-adapter/spec.md` and `specs/README.md` only after all checks pass

---

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 freezes and reviews the provider dependency.
- Phase 2 establishes strict provider-neutral contracts and blocks all stories.
- US1 implements pure provider output and worker behavior.
- US2 depends on US1 output and adds atomic persistence/reuse.
- US3 hardens every US1/US2 failure path.
- US4 depends on persisted verified evidence and adds bounded consumption/CLI behavior.
- Phase 7 depends on every story and closes compatibility/convergence evidence.

### Within each story

- Tests are written and observed failing before corresponding implementation.
- Pure models and validation precede I/O.
- Worker/provider output precedes persistence.
- Migration precedes catalog rich-row code.
- Catalog commit/load precedes service orchestration and CLI.
- Cache reuse is not accepted until full integrity validation exists.

### Parallel opportunities

- Documentation/status work T002 and dependency contract tests T003 are independent.
- Pure model/security/port tests T007–T011 touch separate test surfaces.
- Native translation and worker tests T018–T023 are separable before implementation.
- Migration/catalog/service test files T030–T034 are separable.
- Failure matrix tests T041–T045 are separable.
- Pointer/service/CLI tests T050–T053 are separable.
- Phase 7 documentation tasks T059–T061 are separable after behavior freezes.

## Implementation Strategy

### MVP first

1. Freeze and lock the provider.
2. Establish strict internal contracts.
3. Convert actual synthetic DOCX/PPTX in the bounded offline worker.
4. Construct and validate complete native/F006 evidence in memory.
5. Stop and independently validate US1.

### Incremental completion

1. Add migration and atomic catalog commit.
2. Prove parser-free verified reuse and immutable change handling.
3. Complete adversarial failure matrix.
4. Add bounded provider-free inspection and CLI routing.
5. Prove compatibility, packaging, cross-platform CI and convergence.

### Rollback

Revert the isolated F007 feature/merge commit before opening a production workspace with
catalog revision 5. After migration, restore a revision-4 backup for older software;
never edit checksummed migration history or downgrade the live SQLite file in place.
Immutable CAS objects remain safe but may be unreachable until F013 retention/recovery
tools.
