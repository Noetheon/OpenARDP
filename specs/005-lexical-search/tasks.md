# Tasks: Lexical Search over Prepared Evidence

**Input**: Design documents from `specs/005-lexical-search/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/lexical-search.md`, completed checklists

**Tests**: Mandatory. Public contracts, persisted behavior, security boundaries and every
acceptance scenario require deterministic offline tests. Author each phase's failing tests
before its implementation where practical.

**Organization**: Tasks are dependency-ordered. User-story labels preserve independently
demonstrable slices; foundational tasks are shared prerequisites. Do not start F006.

## Phase 1: Setup and feature boundary

**Purpose**: Establish F005 scope, dependency and implementation evidence without adding
behavior beyond the reviewed module surface.

- [x] T001 Confirm clean base at F004-complete `main`, work on `codex/f005-lexical-search`,
  verify Spec Kit integration and select the feature in `.specify/feature.json`
- [x] T002 Record the restated acceptance criteria, resolved design decisions and
  test-first evidence table in `specs/005-lexical-search/implementation-notes.md`
- [x] T003 [P] Update `tests/test_package.py` expectations for the planned F005
  domain/port/service module surface (`openardp.domain.search`, `openardp.services.search`)
  and first prove the missing-module failures
- [x] T004 [P] Confirm `tests/test_repository_contract.py` still allows only the reviewed
  runtime dependencies (no new third-party packages for FTS5) and prove the lock stays
  unchanged after implementation
- [x] T005 Run the focused package/repository boundary tests and record the setup evidence
  in `specs/005-lexical-search/implementation-notes.md`

---

## Phase 2: Pure search contracts and catalog port extensions

**Purpose**: Define strict deterministic query/hit/coverage records and narrow catalog
search methods before any SQLite/FTS work.

- [x] T006 [P] Add failing grammar tests for empty/whitespace, terms, quoted phrases,
  `""` escaping, size/item bounds, operator lookalikes as literals and
  `match_expression()` golden vectors in `tests/domain/test_search.py`
- [x] T007 [P] Add failing filter/bounds tests for limit 1–100 default 20, kind/trust
  vocabulary, page/slide non-negative, document+version coupling and reject codes in
  `tests/domain/test_search.py`
- [x] T008 [P] Add failing hit/outcome/coverage/reindex-report invariant tests (snippet
  ≤ 240, deterministic ordering fields, no body fields) in `tests/domain/test_search.py`
- [x] T009 Implement pure F005 records, grammar, filters, outcomes and typed search errors
  in `src/openardp/domain/search.py`
- [x] T010 [P] Add failing catalog protocol expectations for `search_block_entries`,
  `index_coverage`, `replace_scope_index` and `list_ready_scopes` plus search error taxonomy
  in `tests/contract/test_search_ports.py`
- [x] T011 Extend `src/openardp/ports/catalog.py` with F005 search/index methods and typed
  errors without weakening F003/F004 contracts
- [x] T012 Export only reviewed public names from `src/openardp/domain/__init__.py` and
  `src/openardp/ports/__init__.py`
- [x] T013 Run focused domain/contract tests, Ruff and strict mypy; record foundation
  evidence in `specs/005-lexical-search/implementation-notes.md`

**Checkpoint**: Pure query contracts and ports are independently validated with no I/O.

---

## Phase 3: User Story 1 — Atomic index population, coverage and reindex (Priority: P1)

**Goal**: Every READY commit publishes searchable index rows atomically; pre-feature
representations become searchable through explicit idempotent `reindex`; coverage detects
missing/orphaned/stale state without mutation.

**Independent Test**: Migrate temporary catalogs, commit READY aggregates with and without
index fault injection, backfill pre-migration READY scopes, and compare coverage against
projections without any original source file present.

### Tests for User Story 1

- [x] T014 [P] [US1] Add failing migration-4 tests for fresh/v3 upgrade, unchanged prior
  checksums, repeated open, injected rollback, too-new rejection and exact revision-4
  table inventory (mapping + FTS + shadows) in `tests/integration/test_search_catalog.py`
- [x] T015 [P] [US1] Add failing FTS5 capability-probe tests under `trusted_schema=OFF` and
  sanitized `SearchCapabilityUnavailable` in `tests/integration/test_search_catalog.py`
- [x] T016 [P] [US1] Add failing atomic READY+index commit tests for multi-block insert,
  empty-block representation, exact entry/FTS rowid bijection and text_hash identity in
  `tests/integration/test_search_catalog.py`
- [x] T017 [P] [US1] Add failing fault-injection tests at every index boundary
  (after entries, after FTS insert, after READY update, pre-commit) with independent-reader
  proof of zero partial READY+index visibility in `tests/integration/test_search_catalog.py`
- [x] T018 [P] [US1] Add failing coverage tests for complete/missing/orphaned ordinals and
  read-only scan semantics in `tests/integration/test_search_catalog.py`
- [x] T019 [P] [US1] Add failing `replace_scope_index` tests for READY-only scope, atomic
  delete+insert, non-READY rejection and idempotent rebuild in
  `tests/integration/test_search_catalog.py`
- [x] T020 [P] [US1] Add failing service reindex tests for pre-feature READY scopes, CAS-only
  verification, per-scope outcomes (`current`/`rebuilt`/`failed`), idempotent second run and
  byte-identical representations/sources in `tests/integration/test_reindex.py`

### Implementation for User Story 1

- [x] T021 [US1] Append `MIGRATION_4` (`lexical-block-search`) without modifying revisions
  1–3 in `src/openardp/adapters/sqlite_migrations.py`
- [x] T022 [US1] Extend `_SCHEMA_TABLES[4]`, FTS capability probe at open/initialize and
  schema validation for FTS shadows in `src/openardp/adapters/sqlite_catalog.py`
- [x] T023 [US1] Implement index insert helpers and wire them into
  `commit_ready_representation` after block inserts and before READY state update, with
  fault points, in `src/openardp/adapters/sqlite_catalog.py`
- [x] T024 [US1] Implement `index_coverage`, `list_ready_scopes` and
  `replace_scope_index` with parameterized SQL in `src/openardp/adapters/sqlite_catalog.py`
- [x] T025 [US1] Implement reindex orchestration (verified aggregates, per-scope replace,
  bounded reports) in `src/openardp/services/search.py`
- [x] T026 [US1] Run the complete US1 suite plus focused Ruff/mypy and record evidence

**Checkpoint**: Index lifecycle is complete and independently usable through catalog/service
ports without the full query grammar CLI.

---

## Phase 4: User Story 2 — Exact term/phrase search with source-backed hits (Priority: P1)

**Goal**: Operators find exact terms and quoted phrases and receive deterministic ranked hits
with verified references and bounded escaped snippets, never full bodies.

**Independent Test**: Ingest synthetic TXT/MD fixtures with known term placement, run
term/phrase searches through the service, and compare every hit against catalog projections
and verified CAS block content.

### Tests for User Story 2

- [x] T027 [P] [US2] Add failing term-match tests for multi-block multi-document hits,
  exact-once identity and provenance fields in `tests/integration/test_search_service.py`
- [x] T028 [P] [US2] Add failing phrase-match tests proving adjacency requirement and
  non-adjacent multi-term rejection in `tests/integration/test_search_service.py`
- [x] T029 [P] [US2] Add failing determinism tests for 20 identical queries (hit set, order,
  snippets) and total-order tie-break in `tests/integration/test_search_service.py`
- [x] T030 [P] [US2] Add failing empty/no-match and rejected-query outcome tests with
  body-free errors in `tests/integration/test_search_service.py`
- [x] T031 [P] [US2] Add failing serve-time verification tests for CAS hash mismatch
  (`SearchIndexDrifted`), missing objects and source-file-absent success in
  `tests/integration/test_search_service.py`
- [x] T032 [P] [US2] Add failing snippet tests for ≤ 240 bound, control-character escaping,
  instruction-like inert text and progressive-disclosure (no full bodies) in
  `tests/integration/test_search_service.py`

### Implementation for User Story 2

- [x] T033 [US2] Implement `search_block_entries` (coverage pre-check, parameterized MATCH,
  projection join, bm25 + document_id + ordinal total order, limit/available) in
  `src/openardp/adapters/sqlite_catalog.py`
- [x] T034 [US2] Implement SearchService grammar→MATCH, scope resolution defaults, CAS
  verification, hash guard and snippet builder in `src/openardp/services/search.py`
- [x] T035 [US2] Run the complete US2 suite plus focused Ruff/mypy and record evidence

**Checkpoint**: Exact lexical retrieval works end-to-end through the service layer.

---

## Phase 5: User Story 3 — Scope and filter retrieval (Priority: P2)

**Goal**: Restrict search by document, version, kind, trust, limit and optional history;
page/slide filters match only exact coordinates.

**Independent Test**: Prepare multi-document multi-version multi-kind fixtures and verify
every filter combination against committed catalog facts.

### Tests for User Story 3

- [x] T036 [P] [US3] Add failing current-vs-history tests (superseded excluded by default,
  included with `--all-versions` / history flag with exact version identity) in
  `tests/integration/test_search_service.py`
- [x] T037 [P] [US3] Add failing kind/trust filter and vocabulary-rejection tests in
  `tests/integration/test_search_service.py`
- [x] T038 [P] [US3] Add failing document UUID/path resolution, unknown-scope not-found and
  exact version scope tests in `tests/integration/test_search_service.py`
- [x] T039 [P] [US3] Add failing limit truncation (deterministic order, truncated/available
  counts, bounds 1–100) tests in `tests/integration/test_search_service.py`
- [x] T040 [P] [US3] Add failing page/slide filter tests proving line-based text never
  matches coordinate filters while accepting the stable contract in
  `tests/integration/test_search_service.py`
- [x] T041 [P] [US3] Add failing concurrent ingest/search snapshot isolation tests
  (complete old or complete new scope, never mixed) in
  `tests/integration/test_search_service.py`

### Implementation for User Story 3

- [x] T042 [US3] Complete filter resolution and SQL WHERE clauses for document/version/
  history/kind/trust/page/slide in `src/openardp/adapters/sqlite_catalog.py` and
  `src/openardp/services/search.py`
- [x] T043 [US3] Run the complete US3 suite plus focused Ruff/mypy and record evidence

**Checkpoint**: Scoped retrieval is complete through the service layer.

---

## Phase 6: User Story 4 — Stable CLI `search` and `reindex` (Priority: P2)

**Goal**: Expose `search` and `reindex` through the installable `openardp` CLI with shared
workspace validation, human/JSON envelopes and exit classifications.

**Independent Test**: Invoke the installed entry point for both commands against valid,
missing, foreign and newer workspaces and against rejected input.

### Tests for User Story 4

- [x] T044 [P] [US4] Extend `tests/integration/test_cli.py` with failing `search --json`
  envelope, hit shape, body-minimizing and exit-code tests
- [x] T045 [P] [US4] Extend `tests/integration/test_cli.py` with failing `reindex --json`
  report, idempotent second run and workspace-boundary tests
- [x] T046 [P] [US4] Add failing human-mode output, rejected query/filter and capability
  classification tests in `tests/integration/test_cli.py`
- [x] T047 [P] [US4] Add failing security tests for operator-token injection, oversized/
  unbalanced queries, hostile snippets, workspace boundaries and zero network use in
  `tests/security/test_search_boundaries.py`

### Implementation for User Story 4

- [x] T048 [US4] Add `search` and `reindex` argument parsing, service composition, human/
  JSON rendering and exit-class mapping in `src/openardp/interfaces/cli.py`
- [x] T049 [US4] Export reviewed service names from `src/openardp/services/__init__.py` and
  keep SQL/FTS logic out of the interface layer
- [x] T050 [US4] Run the complete CLI/security suite plus focused Ruff/mypy and record
  evidence

**Checkpoint**: Search is operable through the audited CLI contract.

---

## Phase 7: Polish, documentation and quality gates

**Purpose**: Cross-cutting validation, documentation and feature closure.

- [x] T051 [P] Update architecture/data-model/testing/execution-plan docs with only
  delivered F005 behavior under `docs/`
- [x] T052 [P] Update `README.md`, `START_HERE.md`, `specs/README.md`, `CHANGELOG.md` and
  `VALIDATION.md` for F005
- [x] T053 Complete `specs/005-lexical-search/implementation-notes.md` with full evidence
  table, FR/SC mapping and tradeoffs
- [x] T054 Run full locked gates: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `uv run pytest` (branch coverage ≥ 85%), package build and offline
  repository validator
- [x] T055 Confirm no public F002 schema, ADR or runtime-dependency change; lockfile
  unchanged unless uv reports no content drift
- [x] T056 Mark all tasks complete only after convergence findings are zero and the feature
  is ready for a single bounded commit/PR

---

## Dependencies

```text
Phase 1 (Setup)
  └─> Phase 2 (Domain + Ports)
        └─> Phase 3 US1 (Index lifecycle)  ← MVP foundation
              └─> Phase 4 US2 (Exact search)
                    └─> Phase 5 US3 (Filters)
                          └─> Phase 6 US4 (CLI)
                                └─> Phase 7 (Polish)
```

- US1 blocks US2–US4 (index must exist before serving).
- US2 and US3 share `SearchService`/`search_block_entries`; US3 extends filters after
  baseline term/phrase path is green.
- US4 depends on service completeness for both `search` and `reindex`.
- Within a phase, tests marked `[P]` may be authored in parallel; implementation tasks on
  the same file are sequential.

## Parallel execution examples

```text
# Phase 2 domain tests in parallel:
T006, T007, T008  → then T009

# Phase 3 catalog tests in parallel (same file — author sequentially if contended):
T014..T019 as separate test classes, then T021..T024 sequential on sqlite_* modules

# Phase 4/5 service tests:
T027..T032 parallel authoring, T033–T034 sequential; T036..T041 then T042

# Phase 6 CLI/security:
T044..T047 parallel authoring, T048–T049 sequential
```

## Implementation strategy

1. **MVP**: Phases 1–3 deliver atomic indexing, coverage and reindex — searchable state
   without full query UX is already valuable for internal validation.
2. **Core value**: Phase 4 delivers exact term/phrase retrieval with verified snippets.
3. **Precision**: Phase 5 adds the stable filter surface F006+ will reuse.
4. **Operator surface**: Phase 6 integrates CLI envelopes.
5. **Close**: Phase 7 documents and gates; one bounded commit/PR only.

## Independent test criteria summary

| Story | Independent test |
|---|---|
| US1 | Temporary catalogs + READY commits + fault injection + reindex; no sources needed after prepare |
| US2 | Synthetic fixtures + service searches; hits match catalog + CAS |
| US3 | Multi-doc/version/kind corpus; every filter vs committed facts |
| US4 | Installed entry point human/JSON; shared exit classifications |

## Format validation

- All tasks use `- [x] Tnnn` checklist format with sequential IDs T001–T056
- Story labels `[US1]`–`[US4]` only on user-story phases
- `[P]` only where different files or non-conflicting authoring apply
- Every task includes exact file paths
- Total: **56 tasks** (Setup 5, Foundation 8, US1 13, US2 9, US3 8, US4 7, Polish 6)
