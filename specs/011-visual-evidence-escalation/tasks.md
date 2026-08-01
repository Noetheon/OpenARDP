# Tasks: Visual Evidence Escalation

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, visual contract and
completed requirements-quality checklists.

**Scope**: F011 only. Tests precede implementation where practical.
**Rollback baseline**: `57b9b6746724273e53670c563b91655c225ecba7`.

## Phase 1 — Governance, acceptance criteria and baseline

**Purpose**: Turn the compatibility/safety boundary into executable evidence before
runtime changes.

- [x] T001 Record F011 acceptance criteria, rollback baseline, external prompt digest
  and planned exact commands in `specs/011-visual-evidence-escalation/implementation-notes.md`.
- [x] T002 Run and record the green locked baseline (`ruff`, format, strict mypy,
  network-disabled pytest/coverage, build, schema and repository validators) in
  `specs/011-visual-evidence-escalation/implementation-notes.md`.
- [x] T003 Add and accept the architecture/compatibility decision in
  `docs/adr/0012-visual-evidence-descriptors-and-rendering.md` before persisted identity
  or schema implementation.
- [x] T004 [P] Add repository governance expectations for F011 artifacts, ADR 0012,
  schema inventory and revision 8 to `tests/test_repository_contract.py`.
- [x] T005 [P] Add a byte-freeze baseline for the eleven prior schemas, F006 vectors/
  corpus, F007 profile/export facts, F008 identity fixtures and F009 descriptors, plus
  an allowlisted dependency-diff assertion that permits only the new exact `visual`
  extra while preserving prior pins, in `tests/contract/test_f011_compatibility.py`.

**Checkpoint**: Highest-level decisions and prior compatibility are test-enforced.

## Phase 2 — Visual contract, identities and pure geometry foundation

**Purpose**: Implement provider-free contracts and deterministic arithmetic before any
renderer or I/O.

- [x] T006 [P] [US1] Add failing visual/raster identity golden-vector tests in
  `tests/domain/test_visual_identity.py` and fixtures under
  `tests/fixtures/visual/identity/`.
- [x] T007 [US1] Implement domain-separated raster/visual identity helpers in
  `src/openardp/domain/identity.py` without altering prior projections.
- [x] T008 [P] [US1] Add failing strict model/invariant tests for limits, recipe, usage
  policy, raster, region, transform, descriptor, commit and catalog record in
  `tests/domain/test_visual.py`.
- [x] T009 [P] [US1] Add failing exact integer floor/ceiling/no-clamp/boundary/rotation/
  scale and 1,000-PPM aspect-admission corpus tests in
  `tests/domain/test_visual_geometry.py`.
- [x] T010 [US1] Implement closed pure visual models and validation in
  `src/openardp/domain/visual.py`.
- [x] T011 [US1] Implement deterministic integer PPM-to-pixel transform and exact
  descriptor/row fingerprints in `src/openardp/domain/visual.py`.
- [x] T012 [P] [US1] Add valid/invalid public descriptor fixtures and manifest under
  `tests/fixtures/visual/contract/`.
- [x] T013 [P] [US1] Add schema/version/extension/trust/identity conformance tests in
  `tests/contract/test_visual_schema.py`.
- [x] T014 [US1] Extend deterministic schema generation and inventory in
  `scripts/generate_schemas.py`, `schemas/visual-evidence-descriptor.schema.json` and
  `schemas/README.md`.
- [x] T015 [US1] Export only intended additive visual domain symbols in
  `src/openardp/domain/__init__.py` and verify importing domain code loads no optional
  provider or I/O module.
- [x] T016 [US1] Prove 20-process/hash-seed identity and geometry determinism in
  `tests/domain/test_visual_identity.py`.

**Checkpoint**: The public root, identity and geometry are deterministic and provider-free.

## Phase 3 — Provider ports, native resolution and isolated renderer (US1)

**Goal**: Produce bounded exact page/crop bytes from one accepted PDF target without
granting source/path/network authority.

**Independent Test**: Render and crop synthetic rotated PDF targets, exercise table
granularity and hostile/resource fixtures, and compare exact outputs across fresh
workers/processes.

### Tests for User Story 1

- [x] T017 [P] [US1] Add failing protocol/error/capability tests for renderer, rights
  policy and interpretation ports in `tests/unit/test_visual_ports.py`.
- [x] T018 [P] [US1] Add failing native resolver tests for page-region, picture pointer,
  cell-exact, table-fallback, missing/multiple/mismatched provenance in
  `tests/unit/test_visual_resolver.py`.
- [x] T019 [P] [US1] Add synthetic PDF fixtures with exact page sizes, rotations,
  vector regions and redistributable metadata under `tests/fixtures/visual/pdf/`.
- [x] T020 [P] [US1] Add failing worker protocol/lifecycle tests for streaming bounds,
  timeout, crash, cancellation, cleanup and error sanitization in
  `tests/unit/test_isolated_visual.py`.
- [x] T021 [P] [US1] Add failing renderer/crop golden tests for page count/dimensions,
  RGB/PNG canonicalization, rotation, scale and single-frame decoding in
  `tests/unit/test_visual_pdfium.py`.
- [x] T022 [P] [US1] Add failing security tests for decompression/dimension/pixel/output/
  metadata/frame bombs, malformed/encrypted PDFs and egress in
  `tests/security/test_visual_boundaries.py`.

### Implementation for User Story 1

- [x] T023 [US1] Define narrow typed visual renderer, rights policy and interpreter
  protocols plus stable body-free errors in `src/openardp/ports/visual.py`.
- [x] T024 [US1] Implement accepted-native region resolution without provider imports in
  `src/openardp/services/visual_evidence.py`.
- [x] T025 [US1] Add exact optional `visual` dependency declarations and regenerate the
  reviewed lock in `pyproject.toml` and `uv.lock`.
- [x] T026 [US1] Implement wheel-content-bound recipes plus deterministic bounded
  PDFium page rendering and Pillow PNG/crop functions in
  `src/openardp/adapters/visual_pdfium.py`.
- [x] T027 [US1] Implement spawned strict render/crop IPC, offline environment, resource
  limits and guaranteed terminate/kill/reap cleanup in
  `src/openardp/adapters/isolated_visual.py`.
- [x] T028 [US1] Implement the conservative local-only/export-denied default usage policy
  in `src/openardp/adapters/visual_policy.py`.
- [x] T029 [US1] Run focused provider/worker/security tests and record exact vectors,
  limits and residual native-code risks in
  `specs/011-visual-evidence-escalation/implementation-notes.md`.

**Checkpoint**: A registered PDF page/raster can be rendered and cropped in bounded
offline isolation; unsupported media fails honestly.

## Phase 4 — Migration 8 and atomic visual persistence (US1, US4)

**Goal**: Make page raster reuse and visual descriptors reachable atomically and
restart-safe.

### Tests

- [x] T030 [P] [US4] Add failing revision-8 SQL shape/checksum/STRICT/FK/index tests in
  `tests/integration/test_f011_migration.py`.
- [x] T031 [P] [US4] Add failing fresh/populated revision-7-to-8 preservation, too-new,
  per-statement fault and concurrent-initializer tests in
  `tests/integration/test_f011_migration.py`.
- [x] T032 [P] [US1] Add failing catalog tests for raster+descriptor commit/load/list,
  exact convergence and same-identity conflict in
  `tests/integration/test_visual_catalog.py`.
- [x] T033 [P] [US1] Add failing FK/scope/projection/raster/object/fingerprint drift and
  independent-reader atomicity tests in `tests/integration/test_visual_catalog.py`.
- [x] T034 [P] [US4] Add failing reachability tests for raster-record, raster, descriptor
  and crop objects in `tests/integration/test_visual_reachability.py`.

### Implementation

- [x] T035 [US4] Add append-only checksummed `MIGRATION_8` and explicit exports in
  `src/openardp/adapters/sqlite_migrations.py`.
- [x] T036 [US1] Add visual catalog conflicts and `VisualCatalog` protocol methods to
  `src/openardp/ports/catalog.py`.
- [x] T037 [US1] Implement transactional insert/reuse/load/list and complete semantic
  conflict verification in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T038 [US1] Add raster/visual fault points after each write and immediately before
  commit in `src/openardp/adapters/sqlite_catalog.py`; prove rollback.
- [x] T039 [US4] Extend reference snapshots/reachability roots and integrity reporting
  for every F011 object in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T040 [US4] Verify migration/reachability suites and record upgrade/rollback/recovery
  evidence in `specs/011-visual-evidence-escalation/implementation-notes.md`.

**Checkpoint**: Revision 8 exposes either one complete visual record or none and reuses
page rasters across target crops.

## Phase 5 — Verified materialization and inspection service (US1)

**Goal**: Bind accepted evidence, renderer, CAS and catalog into one explicit safe use case.

### Tests

- [x] T041 [P] [US1] Add failing service tests for current accepted target resolution,
  source/native/reference/projection/CAS revalidation and unsupported target failures in
  `tests/integration/test_visual_evidence_service.py`.
- [x] T042 [P] [US1] Add failing first-render, cached-page/new-crop, exact-record cache-hit
  and recipe-change invocation-count tests in
  `tests/integration/test_visual_evidence_service.py`.
- [x] T043 [P] [US1] Add failing CAS publication/catalog fault/cancellation/retry tests
  at every boundary in `tests/integration/test_visual_evidence_service.py`.
- [x] T044 [P] [US1] Add failing 20-concurrent identical/conflicting request tests with
  independent catalogs in `tests/integration/test_visual_evidence_concurrency.py`.
- [x] T045 [P] [US1] Add failing descriptor/raster/crop tamper and exact inspection tests
  in `tests/integration/test_visual_evidence_service.py`.
- [x] T046 [P] [US1] Add body/path/metadata/prompt-safe error and logging tests in
  `tests/security/test_visual_service_privacy.py`.

### Implementation

- [x] T047 [US1] Implement exact artifact resolution, rights-policy binding and canonical
  deterministic request recipe in `src/openardp/services/visual_evidence.py`.
- [x] T048 [US1] Implement verified page-cache reuse, worker render/crop calls and
  CAS-first object publication in `src/openardp/services/visual_evidence.py`.
- [x] T049 [US1] Implement atomic catalog commit, exact retry/conflict handling and
  cooperative cancellation in `src/openardp/services/visual_evidence.py`.
- [x] T050 [US1] Implement descriptor inspection with complete catalog/object/model/
  identity verification in `src/openardp/services/visual_evidence.py`.
- [x] T051 [US1] Run the complete US1 focused suite and record page/crop hashes,
  invocation counts, fault/concurrency results and unsupported-media truth in
  `specs/011-visual-evidence-escalation/implementation-notes.md`.

**Checkpoint**: Exact page/picture/table/cell visual materialization is complete for the
declared capability and safely inspectable.

## Phase 6 — Verified visual context handles (US2)

**Goal**: Let existing F008 compilation select current exact visual handles without
changing public F008/F009 contracts or invoking providers.

**Independent Test**: Compile before/after materialization and after head change;
compare items, missing evidence, receipts, budgets and replay while injecting object/
catalog drift.

### Tests

- [x] T052 [P] [US2] Add failing internal candidate payload-shape tests for content vs
  visual handle candidates in `tests/domain/test_context_compilation.py`.
- [x] T053 [P] [US2] Add failing visual candidate discovery tests for exact snapshot,
  canonical profile, deterministic order, duplicate recipes, bounds and cancellation in
  `tests/unit/test_context_candidates.py`.
- [x] T054 [P] [US2] Add failing current/stale/different-scope and descriptor/page/crop/
  target drift tests in `tests/security/test_context_boundaries.py`.
- [x] T055 [P] [US2] Add failing compiler tests for handle-only items, descriptor cost,
  selection receipt and preserved missing notice in
  `tests/integration/test_context_visual_evidence.py`.
- [x] T056 [P] [US2] Add failing deterministic replay and head-change integration tests
  in `tests/integration/test_context_visual_evidence.py`.
- [x] T057 [P] [US2] Prove ContextBundle/SelectionReceipt schema and existing MCP
  descriptor bytes remain unchanged in `tests/contract/test_f011_compatibility.py`.

### Implementation

- [x] T058 [US2] Add mutually exclusive handle payload fields/invariants to internal
  `ContextCandidate` in `src/openardp/domain/context_compilation.py`.
- [x] T059 [US2] Implement verified bounded `VisualContextCandidateSource` in
  `src/openardp/adapters/context_candidates.py`.
- [x] T060 [US2] Build handle-only visual items and exact costs without reading image
  bytes into bundle content in `src/openardp/services/context_compiler.py`.
- [x] T061 [US2] Compose the visual candidate source in existing CLI/MCP application
  construction without adding tools or provider authority in
  `src/openardp/interfaces/cli.py`.
- [x] T062 [US2] Run focused context/replay/MCP freeze tests and record exact before/
  after/stale outcomes in `specs/011-visual-evidence-escalation/implementation-notes.md`.

**Checkpoint**: VISUAL context truthfully returns current handles or the existing
escalation notice and replay never floats.

## Phase 7 — Optional untrusted OCR/caption orchestration (US3)

**Goal**: Make the provider-neutral interpretation boundary executable and reusable
through F010 while registering no provider by default.

**Independent Test**: Publish deterministic fake OCR/caption results; vary every recipe
input, exercise failures and assert exact F010 dependencies/trust/slots.

### Tests

- [x] T063 [P] [US3] Add failing request/result bounds, confidence, warnings and hostile
  content tests in `tests/domain/test_visual_interpretation.py`.
- [x] T064 [P] [US3] Add deterministic fake provider fixtures for OCR/caption, network
  attempt, malformed and oversized results in `tests/fixtures/visual/interpreters.py`.
- [x] T065 [P] [US3] Add failing service tests for exact descriptor/crop verification,
  provider/model/config/prompt identity, F010 OBJECT dependency and independent parent-
  scope current-use checks in
  `tests/integration/test_visual_interpretation.py`.
- [x] T066 [P] [US3] Add failing retry/change/supersession/failure/cancellation/no-provider
  tests in `tests/integration/test_visual_interpretation.py`.
- [x] T067 [P] [US3] Add trust/instruction/no-network/low-confidence-crop retention tests
  in `tests/security/test_visual_interpretation_boundaries.py`.

### Implementation

- [x] T068 [US3] Implement strict interpretation request/result models in
  `src/openardp/domain/visual.py`.
- [x] T069 [US3] Implement explicit provider invocation, canonical output and complete
  READY/FAILED F002 derivation record construction in
  `src/openardp/services/visual_interpretation.py`.
- [x] T070 [US3] Publish exact crop-dependent OCR/caption outputs and slots through the
  existing `DerivationService` in `src/openardp/services/visual_interpretation.py`.
- [x] T071 [US3] Verify no provider is registered by default and record fake-provider/
  trust/invalidation evidence in
  `specs/011-visual-evidence-escalation/implementation-notes.md`.

**Checkpoint**: Optional interpretation is fully specified/tested, untrusted and backed
by F010 without a mandatory model or egress.

## Phase 8 — CLI, operational truth and documentation (US4)

**Goal**: Expose identifier-scoped local operations and truthful upgrade/security/
rights/supply-chain guidance.

**Independent Test**: Run materialize/inspect JSON and human paths, invalid identifier/
dependency/unsupported cases, upgrade/reachability checks and documentation validators.

- [x] T072 [P] [US4] Add failing CLI parser/envelope/help/error tests for
  `visual-materialize` and `visual-evidence` in `tests/integration/test_cli_visual.py`.
- [x] T073 [US4] Implement identifier-scoped materialize/inspect commands and stable
  body-free JSON/human output in `src/openardp/interfaces/cli.py`.
- [x] T074 [P] [US4] Update `docs/03_DATA_MODEL_AND_PACKAGE.md`,
  `docs/05_CONTEXT_COMPILER_AND_MCP.md` and `docs/06_SECURITY_MODEL_V2.md` with delivered
  descriptor, context, trust and worker facts.
- [x] T075 [P] [US4] Update `docs/08_ROADMAP_AND_GOVERNANCE.md`,
  `docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md` and
  `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md` with status, version axes, optional
  dependency review, rights, recovery and rollback.
- [x] T076 [P] [US4] Update `README.md`, `START_HERE.md`, `CHANGELOG.md`, `VALIDATION.md`
  and `specs/README.md` with commands, revision 8, limitations and F011 status.
- [x] T077 [US4] Validate every planned command in
  `specs/011-visual-evidence-escalation/quickstart.md` and correct it to delivered syntax.
- [x] T078 [US4] Complete `specs/011-visual-evidence-escalation/implementation-notes.md`
  with FR/SC/task traceability, exact commands/results, supply-chain review, metrics,
  tradeoffs, residual risks and rollback.

## Phase 9 — Analyze, validate, converge and publish

**Purpose**: Prove cross-artifact consistency, repository quality and remote
cross-platform behavior before F012.

- [x] T079 Run read-only Spec Kit analysis; resolve every critical/high contradiction at
  its highest source and record the final matrix in
  `specs/011-visual-evidence-escalation/analysis.md`.
- [x] T080 Run focused identity/schema/domain/geometry/renderer/worker/security suites
  and record exact counts/hashes in
  `specs/011-visual-evidence-escalation/implementation-notes.md`.
- [x] T081 Run focused migration/catalog/service/context/interpretation/CLI/fault/
  concurrency/reachability suites and record exact results.
- [x] T082 Run Ruff, format, strict mypy, full network-disabled pytest/coverage, build,
  schema/repository validators and full pre-commit.
- [x] T083 Prove only the intended optional dependency/lock changes and new schema were
  introduced, and zero prior schema/vector/profile/MCP drift occurred from the rollback
  baseline.
- [x] T084 Inspect wheel/sdist in an isolated core environment and optional visual
  environment; demonstrate core import without Pillow/PDFium and local visual smoke
  without network.
- [x] T085 Run Spec Kit convergence across behavior, docs, ADR, migration, changelog,
  validation and clean repository status; resolve all critical/high findings.
- [x] T086 Commit one coherent F011 feature, push `codex/f011-visual-evidence-escalation`,
  open one PR, wait for Linux/macOS/Windows CI, merge only when green, then wait for
  post-merge `main` CI before F012.

## Dependencies and execution order

- Phase 1 governance/freeze blocks persisted identity and schema work.
- Phase 2 domain/identity/geometry blocks renderer, catalog and service implementation.
- Phase 3 ports/worker blocks first materialization; migration tasks may proceed after
  Phase 2 but service integration requires both Phase 3 and Phase 4.
- Phase 5 materialization/inspection blocks context visual discovery and interpretation.
- US2 and US3 share verified F011 records after Phase 5 but remain independently tested.
- All runtime phases block CLI/docs/convergence and remote publication.

## Parallel opportunities

- Tasks marked `[P]` touch independent fixture/test/document files and may be authored
  together, but implementation remains sequential in this single-agent delivery.
- Contract/model/geometry tests T006, T008, T009, T012 and T013 can be prepared before
  the domain implementation.
- Migration, catalog and reachability tests T030-T034 can be prepared together.
- Context tests T052-T057 and interpretation tests T063-T067 are independent after the
  materialization service exists.
- Documentation T074-T076 can be updated in parallel after behavior stabilizes.

## Explicit exclusions

No task authorizes automatic watching/jobs, durable scheduler cancellation, deletion/
GC/quarantine, export package creation, new MCP tools/mutation, HTTP service, DOCX/PPTX
page renderer, built-in OCR/caption/model, cloud/network provider, full page/layout IR,
F006/F008 identity change or bidirectional document editing.
