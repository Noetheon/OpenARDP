# Tasks: Reconciliation and Derivation DAG

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, runtime contract,
ADR 0011 and completed checklists.

**Scope**: F010 only. Tests precede implementation where practical.
**Rollback baseline**: `1e2992c294cf67bc1f87ab58dbfa4b2555f264e6`.

## Phase 1 — Governance and freeze baseline

- [x] T001 Record acceptance-criteria reconciliation, rollback point and exact baseline
  evidence in `specs/010-reconciliation-derivation-dag/implementation-notes.md`.
- [x] T002 Verify and record the green locked baseline (`ruff`, format, strict mypy,
  pytest, build, repository validator) before runtime edits.
- [x] T003 Add repository governance expectations for F010 artifacts, ADR 0011 and
  revision 7 to `tests/test_repository_contract.py`.
- [x] T004 Add a byte-freeze test for all eleven schemas, prior identity vectors, F006
  conformance corpus, F009 descriptor fixture, `pyproject.toml` and `uv.lock`.

**Checkpoint**: Feature sources and compatibility boundary are executable tests.

## Phase 2 — Persisted identity and domain lifecycle foundations

- [x] T005 Add failing golden-vector tests for lineage, binding, run and derivation-slot
  identities in `tests/domain/test_reconciliation_identity.py`.
- [x] T006 Add the four additive ADR-0011 identity helpers without changing prior
  projections in `src/openardp/domain/identity.py`.
- [x] T007 Add reviewed golden fixtures under `tests/fixtures/reconciliation/identity/`
  and prove 20-process/hash-seed determinism.
- [x] T008 Add failing validation/state-machine tests for reconciliation records in
  `tests/domain/test_reconciliation.py`.
- [x] T009 Implement strict pure reconciliation records, fixed bounds/config hash,
  fixed-point confidence and fingerprints in `src/openardp/domain/reconciliation.py`.
- [x] T010 Add failing validation/state-machine tests for dependency/slot/publication/
  node/event records in `tests/domain/test_derivation_lifecycle.py`.
- [x] T011 Implement strict pure derivation lifecycle records in
  `src/openardp/domain/derivation_lifecycle.py`.
- [x] T012 Export only the intended additive domain symbols and verify domain imports
  remain I/O-free.

**Checkpoint**: New persisted identities and lifecycle invariants are deterministic,
typed and documented before matching or storage.

## Phase 3 — Conservative matcher and safety corpus (US1)

- [x] T013 Add failing tests for input completeness, cross-document/same-scope errors,
  hierarchy/count/depth/text/comparison bounds and cancellation checkpoints.
- [x] T014 Add failing phase tests for unique native identity, exact hash, asset/table,
  similarity and bounded sequence matching.
- [x] T015 Add failing ambiguity tests for duplicate IDs/content, ties, near-margin
  winners, incompatible kinds/parents and crossed moves.
- [x] T016 Implement deterministic phase arbitration and one-to-one candidate tracking
  in `src/openardp/domain/reconciliation.py`.
- [x] T017 Implement bounded deterministic normalization/similarity scoring and
  sibling-gap alignment without external dependencies.
- [x] T018 Enforce the hard reuse rule (`logical match AND exact canonical hash`) in
  the model/matcher, independent from confidence/method.
- [x] T019 Build a reviewed synthetic labelled corpus generator and static expectation
  manifest under `tests/fixtures/reconciliation/`.
- [x] T020 Add the corpus audit with ≥100 reuse decisions, per-phase metrics, reported
  recall, exact precision 1.000 and unconditional zero-false-reuse gate in
  `tests/domain/test_reconciliation_corpus.py`.
- [x] T021 Add permutation/fresh-process/platform determinism tests for full plans and
  relation canonical bytes.

**Checkpoint**: Pure reconciliation is bounded and proves zero false reuse before any
catalog mutation exists.

## Phase 4 — Revision-7 migration and catalog contracts

- [x] T022 Add failing revision-7 migration SQL shape/checksum tests for all STRICT
  tables, checks, indexes and restrictive foreign keys.
- [x] T023 Add failing empty/populated revision-6→7 preservation tests and older-code
  too-new behavior in `tests/integration/test_f010_migration.py`.
- [x] T024 Add failing per-statement migration fault and concurrent-initializer tests.
- [x] T025 Implement append-only `MIGRATION_7` and update the explicit migration export
  set in `src/openardp/adapters/sqlite_migrations.py`.
- [x] T026 Add body-free F010 catalog exception classes and the narrow
  `ReconciliationDerivationCatalog` protocol to `src/openardp/ports/catalog.py`.
- [x] T027 Add failing catalog tests for complete reconciliation commit, load,
  idempotent convergence and conflicting target/run rejection.
- [x] T028 Add failing constraint tests for lineage cross-document/cross-scope
  collisions, missing relations and invalid binding/run fingerprints.
- [x] T029 Implement atomic run/lineage/member/relation commit and verified load methods
  in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T030 Add reconciliation fault points after run, lineage, member, relation and
  immediately before commit; prove independent readers see all or none.

**Checkpoint**: Revision 7 safely stores complete reconciliations without derivation
state changes.

## Phase 5 — Verified reconciliation service (US1)

- [x] T031 Add failing service tests for exact CAS/model/scope verification and
  bounded native-ID extraction from explicit untrusted `SourceLocator.native_id` data.
- [x] T032 Implement bounded canonical block loading/verification and matcher input
  projection in `src/openardp/services/reconciliation.py`.
- [x] T033 Add failing tests that relation objects are canonical, reverified and
  registered before catalog visibility.
- [x] T034 Implement CAS-first relation publication plus atomic catalog commit with
  cooperative cancellation.
- [x] T035 Add concurrent identical/conflicting reconciliation tests using independent
  catalog connections.
- [x] T036 Add body-free error/logging security tests with hostile block text, paths,
  URLs, control characters and prompt-shaped content.

**Checkpoint**: Two READY scopes reconcile end-to-end with no unsafe reuse or partial
visibility.

## Phase 6 — Transactional derivation publication (US2)

- [x] T037 Add failing catalog tests for successful and failed node publication,
  ordered dependencies, slots and initial events.
- [x] T038 Add failing dependency tests for missing bindings/objects/producers, output
  mismatch, stale/failed/superseded producer and duplicate/reordered inputs.
- [x] T039 Add failing self/transitive-cycle tests including injected corrupt ancestry.
- [x] T040 Add failing same-publication convergence, divergent-output conflict and
  concurrent publisher tests.
- [x] T041 Implement dependency/slot/node/event persistence, complete conflict
  comparison and recursive cycle checks in `src/openardp/adapters/sqlite_catalog.py`.
- [x] T042 Add publication fault points after slot/node/edge/state/event writes and
  prove full rollback.
- [x] T043 Add failing service tests for canonical F002 record publication, READY/
  FAILED mapping, output streaming/hash verification and cancellation.
- [x] T044 Implement provider-free CAS-first publication in
  `src/openardp/services/derivations.py`.
- [x] T045 Implement verified body-free derivation/event read APIs and drift detection.

**Checkpoint**: Exact DAG nodes publish atomically, idempotently and cycle-free without
executing a provider.

## Phase 7 — Exact invalidation, supersession and A→B→A (US3)

- [x] T046 Add a pure reference-oracle test generator for branching DAG closures and
  ≥100 randomized valid graph cases.
- [x] T047 Add failing tests that one/multiple inactive bindings stale exactly the
  direct/transitive current closure and leave unrelated/shared branches unchanged.
- [x] T048 Add failing no-op retry/event-order/revision tests for invalidation.
- [x] T049 Implement recursive invalidation CTE selection and deterministic atomic
  state/slot/event updates.
- [x] T050 Add failing slot replacement tests proving prior `CURRENT`/`STALE` occupant
  becomes `SUPERSEDED` atomically and failed/superseded nodes never reactivate.
- [x] T051 Implement slot supersession semantics and invariant verification.
- [x] T052 Add failing deterministic fixed-point revalidation tests for evidence,
  object and producer dependency combinations.
- [x] T053 Implement bounded sorted stale→current revalidation and empty-slot reclaim.
- [x] T054 Add end-to-end A→B→A tests proving original artifact, record and output
  identities reactivate without output publication or generator invocation.
- [x] T055 Integrate invalidation/reactivation into reconciliation commit only after the
  transaction rechecks the target as current head; test stale-caller races.
- [x] T056 Add cancellation/fault tests around closure updates and pre-commit, proving
  lineage plus lifecycle are one visibility unit.

**Checkpoint**: Exact invalidation, supersession and historical reactivation satisfy
all lifecycle scenarios.

## Phase 8 — Reachability, compatibility and operational documentation (US4)

- [x] T057 Add failing reachability tests for relation, derivation-record and all
  successful output roots in every lifecycle state.
- [x] T058 Extend `reference_snapshot()` and integrity reporting with F010 roots; never
  delete or quarantine.
- [x] T059 Add missing/length-drifted F010 object tests and verify reads fail closed.
- [x] T060 Update `docs/03_DATA_MODEL_AND_PACKAGE.md`, `docs/04_INCREMENTAL_PROCESSING.md`,
  `docs/02_ARCHITECTURE.md` and `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md` with only
  delivered F010 facts and honest limitations.
- [x] T061 Update `README.md`, `START_HERE.md`, `CHANGELOG.md`, `VALIDATION.md` and
  `specs/README.md` for revision 7, backup/rollback and feature status.
- [x] T062 Complete `implementation-notes.md` with criteria traceability, exact commands,
  metrics, fault/concurrency/migration evidence, tradeoffs, risks and rollback.

## Phase 9 — Analyze, validate and converge

- [x] T063 Run cross-artifact analysis; resolve every critical/high contradiction at
  its highest source and record the final matrix in `analysis.md`.
- [x] T064 Run focused identity/domain/corpus tests and record decision counts,
  precision/recall and deterministic fixture hashes.
- [x] T065 Run focused catalog/service/migration/fault/concurrency/reachability/security
  suites and record exact counts/results.
- [x] T066 Run Ruff, format, strict mypy, full network-disabled pytest/coverage, build,
  repository validator and full pre-commit.
- [x] T067 Prove no drift in `pyproject.toml`, `uv.lock`, eleven schemas, prior vectors,
  F006 corpus and F009 descriptors against rollback baseline.
- [x] T068 Inspect the built wheel in an isolated environment and demonstrate the
  service API with no provider/network/new dependency.
- [x] T069 Mark tasks complete only from evidence; run convergence across behavior,
  docs, ADR, migration, changelog, validation and repository status with zero
  critical/high finding.
- [ ] T070 Commit one coherent F010 feature, push the `codex/` branch, open one PR,
  wait for Linux/macOS/Windows CI, merge only when green, then wait for post-merge
  `main` CI before F011.

## Dependency order

- Phases 1–2 block every persisted/runtime implementation.
- Phase 3 blocks reconciliation persistence/service.
- Migration/protocol tasks T022–T026 block catalog writes.
- Reconciliation catalog/service (Phases 4–5) block lifecycle integration T055.
- Derivation publication (Phase 6) blocks invalidation/reactivation (Phase 7).
- All runtime phases block documentation/convergence and remote merge.

## Explicit exclusions

No task authorizes public schema changes, rich-projection lineage, model/provider
execution, watcher/jobs, visual evidence, MCP mutation, retention/deletion,
export/interchange, new dependency or lockfile change.
