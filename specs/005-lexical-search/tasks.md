# Tasks: Lexical Search over Prepared Evidence

**Input**: Design documents from `specs/005-lexical-search/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/lexical-search.md`, completed checklists

**Tests**: Mandatory. Public contracts, persisted behavior, security boundaries and every acceptance scenario require
deterministic offline tests. Author each phase's failing tests before its implementation where practical.

**Organization**: Tasks are dependency-ordered. User-story labels preserve independently demonstrable slices; foundational
tasks are shared prerequisites. Do not start F006.

## Phase 1: Setup and feature boundary

**Purpose**: Establish F005 scope and empirical FTS5 facts without adding behavior.

- [x] T001 Confirm clean `main`, create `codex/f005-lexical-search`, select the feature in `.specify/feature.json` and record the restated acceptance criteria in `specs/005-lexical-search/implementation-notes.md`
- [x] T002 [P] Probe the locked runtime's FTS5 contentless-delete shadow-table inventory on an in-memory connection (`CREATE VIRTUAL TABLE ... content='', contentless_delete=1`) and pin the exact `_SCHEMA_TABLES[4]` names plus capability-probe recipe in `specs/005-lexical-search/implementation-notes.md`
- [x] T003 [P] Update `tests/test_package.py` expectations for the planned F005 module surface (`domain/search.py`, `services/search.py`, extended ports/adapter/CLI) and first prove the missing-module failures
- [x] T004 [P] Update `tests/test_repository_contract.py` so no new runtime dependency, no new script entry and unchanged F002 schemas are enforced for F005
- [x] T005 Run the focused package/repository boundary tests and record the passing setup evidence in `specs/005-lexical-search/implementation-notes.md`

---

## Phase 2: Foundational — search domain contracts, migration 4 and capability probe

**Purpose**: Pure query/result records, the checksummed revision-4 migration and the fail-closed FTS5 capability probe that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for the foundation

- [x] T006 Add failing grammar tests for terms, quoted phrases, `""` escapes, unbalanced quotes, empty/whitespace input, oversized query/items and zero-token rejection in `tests/domain/test_search.py`
- [x] T007 Add failing deterministic `match_expression()` translation vectors including operator-lookalike literals (`AND OR NEAR * ^ : - ( ) { }`), Unicode and case handling in `tests/domain/test_search.py`
- [x] T008 Add failing `SearchFilters`/hit/outcome/coverage/reindex-record invariant tests (limit bounds 1–100 default 20, snippet bound, deterministic ordering, no-body rule) in `tests/domain/test_search.py`
- [x] T009 Add failing migration-4 tests: fresh initialize, v3→v4 upgrade preserving all rows, checksum drift, foreign/gapped/newer history rejection and the exact revision-4 table inventory including the pinned FTS5 shadow tables in `tests/integration/test_search_catalog.py`
- [x] T010 Add failing FTS5 capability-probe tests: unavailable capability fails closed with `SearchCapabilityUnavailable` before migration or serving and no workspace mutation occurs in `tests/integration/test_search_catalog.py`
- [x] T011 [P] Add failing structural catalog-port tests for `search_block_entries`, `index_coverage`, `replace_scope_index` and `list_ready_scopes` plus the sanitized F005 error taxonomy in `tests/contract/test_search_ports.py`

### Implementation for the foundation

- [x] T012 Implement the pure F005 records, grammar parser, `match_expression()`, bounded validators and coverage/report aggregates in `src/openardp/domain/search.py`
- [x] T013 Add the sanitized F005 search error classifications (`SearchQueryRejected`, `SearchCapabilityUnavailable`, `SearchIndexIncomplete`, `SearchIndexDrifted`) to the shared error module without weakening F003/F004 errors
- [x] T014 Append `MIGRATION_4 = lexical-block-search` (contentless-delete FTS5 `block_search_index` + STRICT `block_search_entries` with scope FK, uniques, checks and indexes) in `src/openardp/adapters/sqlite_migrations.py` and pin `_SCHEMA_TABLES[4]` in `src/openardp/adapters/sqlite_catalog.py`
- [x] T015 Implement the FTS5 capability probe (temporary fts5 table create/drop on the catalog connection) before migration 4 and at workspace open in `src/openardp/adapters/sqlite_catalog.py`
- [x] T016 Extend `src/openardp/ports/catalog.py` with the four F005 protocol methods and records; export only reviewed public names from `src/openardp/domain/__init__.py` and `src/openardp/ports/__init__.py`
- [x] T017 Run focused domain/contract/migration tests, Ruff and strict mypy; record foundation evidence in `specs/005-lexical-search/implementation-notes.md`

**Checkpoint**: Pure grammar/records, revision 4 and the capability probe are independently validated with no I/O beyond temporary catalogs.

---

## Phase 3: User Story 1 — Index prepared documents atomically and verifiably (Priority: P1)

**Goal**: Make every newly committed READY representation searchable in the same transaction, verify coverage deterministically and backfill pre-feature workspaces through explicit `reindex`.

**Independent Test**: Commit representations with fault injection at the index boundary, delete/corrupt entries deliberately, inspect coverage classes and backfill a pre-F005 workspace while proving evidence bytes stay identical.

### Tests for User Story 1

- [x] T018 [US1] Add failing atomic-commit tests: index rows become visible only with READY, fault injection at the index-insert boundary rolls back the whole commit and no partial state is exposed to independent readers in `tests/integration/test_search_catalog.py`
- [x] T019 [US1] Add failing coverage tests: complete coverage passes and deliberately missing and orphaned entries are classified deterministically (stale-hash detection is covered serve-time and at rebuild by T031/T022) in `tests/integration/test_search_catalog.py`
- [x] T020 [US1] Add failing cache-hit and head-move tests: cache-hit reuse performs no index writes, superseded READY entries persist unchanged and A→B→A source history keeps each representation's entries intact in `tests/integration/test_search_catalog.py`
- [x] T021 [US1] Add failing reindex tests: pre-F005 workspace backfill makes exactly current ready blocks searchable, repeated runs report `current` (no-op), per-scope outcomes are bounded and representations/CAS objects/source files stay byte-identical in `tests/integration/test_reindex.py`
- [x] T022 [US1] Add failing reindex negative tests: corrupt/missing CAS block fails the scope with a bounded code without mutating other scopes, and drifted stored hashes are rebuilt from verified evidence in `tests/integration/test_reindex.py`

### Implementation for User Story 1

- [x] T023 [US1] Implement index population inside `commit_ready_representation` (entries + FTS rows after representation_blocks, before READY update) with a new index fault point in `src/openardp/adapters/sqlite_catalog.py`
- [x] T024 [US1] Implement `index_coverage` (projection ordinal sets vs entry ordinal sets, missing/orphaned/stale classes) and `list_ready_scopes` in `src/openardp/adapters/sqlite_catalog.py`
- [x] T025 [US1] Implement atomic `replace_scope_index` (delete scope entries/FTS rows, insert verified entries, READY-only guard, `entry_id`↔`rowid` bijection) in `src/openardp/adapters/sqlite_catalog.py`
- [x] T026 [US1] Implement reindex orchestration in `src/openardp/services/search.py`: scope resolution, verified canonical CAS block loading, per-scope bounded write transactions and deterministic `ReindexReport`
- [x] T027 [US1] Run the complete US1 suite plus focused Ruff/mypy and record the passing evidence in `specs/005-lexical-search/implementation-notes.md`

**Checkpoint**: New ingests are atomically searchable and pre-feature workspaces are recoverable through explicit idempotent backfill.

---

## Phase 4: User Story 2 — Find exact text with source-backed evidence (Priority: P1)

**Goal**: Serve deterministic bounded term/phrase search over current ready scopes with verified snippets and no document bodies.

**Independent Test**: Ingest synthetic TXT/Markdown fixtures with known term placement, search terms and phrases through the service and compare every reference, rank and snippet against catalog facts and verified CAS content after deleting the sources.

### Tests for User Story 2

- [x] T028 [US2] Add failing term/phrase semantics tests: exact adjacent phrase matches only adjacency, multi-term AND, no-match and whitespace-only outcomes, and results remain correct after source deletion in `tests/integration/test_search_service.py`
- [x] T029 [US2] Add failing determinism tests: at least 20 repeated identical queries return byte-identical hits/order/snippets and ties resolve through the documented bm25→document→ordinal total order in `tests/integration/test_search_service.py`
- [x] T030 [US2] Add failing snippet tests: bounded ≤240 escaped characters, match-position windows around long lines and Unicode boundaries, inert control-character rendering and no full bodies in `tests/integration/test_search_service.py`
- [x] T031 [US2] Add failing serve-time guard tests: entry/CAS `text_hash` disagreement or missing match position fails `SearchIndexDrifted`, and uncovered in-scope READY representations fail `SearchIndexIncomplete` before serving in `tests/integration/test_search_service.py`
- [x] T032 [US2] Add failing snapshot-isolation tests: at least 8 concurrent queries during an ingest observe either the complete old or the complete new searchable scope, never a mixture, in `tests/integration/test_search_service.py`

### Implementation for User Story 2

- [x] T033 [US2] Implement `search_block_entries` in `src/openardp/adapters/sqlite_catalog.py`: one read transaction with structural coverage pre-check, parameterized MATCH join against entries and projections, bm25 ordering with total tie-break and `available` count
- [x] T034 [US2] Implement the `SearchService` query path in `src/openardp/services/search.py`: grammar parse, current-head scope resolution, per-hit CAS verification, snippet construction and `SearchOutcome` assembly
- [x] T035 [US2] Run the complete US2 suite plus focused Ruff/mypy and record the passing evidence in `specs/005-lexical-search/implementation-notes.md`

**Checkpoint**: Exact term/phrase retrieval with verified bounded snippets works end to end without any original source file.

---

## Phase 5: User Story 3 — Scope and filter retrieval deterministically (Priority: P2)

**Goal**: Restrict search by document, version, history opt-in, kind, trust zone, page/slide coordinates and limit with explicit rejections.

**Independent Test**: Prepare multi-document multi-version fixtures with several block kinds and verify every filter combination and default/history semantics against committed catalog facts.

### Tests for User Story 3

- [x] T036 [US3] Add failing default-scope tests: superseded versions are excluded, `--all-versions` restores them with exact version identity and non-ready scopes never match in `tests/integration/test_search_service.py`
- [x] T037 [US3] Add failing document/version scope tests: UUID and exact-path resolution with F004 precedence, `--version` implies document scope and unknown scopes fail `not_found` in `tests/integration/test_search_service.py`
- [x] T038 [US3] Add failing kind/trust/coordinate tests: valid vocabularies filter exactly, invalid values fail `rejected_input`, and page/slide filters match only exact non-NULL coordinates (never text blocks) in `tests/integration/test_search_service.py`
- [x] T039 [US3] Add failing limit/truncation tests: limits 1/20/100 behave exactly, out-of-range values are rejected and truncation reports deterministic `truncated`/`available` counts in `tests/integration/test_search_service.py`

### Implementation for User Story 3

- [x] T040 [US3] Implement filter resolution and validation (document/version/history/kind/trust/page/slide/limit) in `src/openardp/services/search.py` and the corresponding scoped SQL predicates in `src/openardp/adapters/sqlite_catalog.py`
- [x] T041 [US3] Run the complete US3 suite plus focused Ruff/mypy and record the passing evidence in `specs/005-lexical-search/implementation-notes.md`

**Checkpoint**: All documented filters and scope semantics behave deterministically with explicit rejections.

---

## Phase 6: User Story 4 — Operate search through the stable CLI boundary (Priority: P2)

**Goal**: Expose `search` and `reindex` through the installable `openardp` command with shared workspace validation, envelopes and exit classifications.

**Independent Test**: Invoke the installed entry point for both verbs in human and JSON modes against valid, missing, foreign and newer workspaces plus the rejection corpus, asserting envelopes, exit codes and body-minimizing output.

### Tests for User Story 4

- [x] T042 [US4] Add failing CLI happy-path tests: `search` term/phrase/filter combinations and `reindex` in human and JSON modes through the installed entry point, with envelope, hit-line and summary assertions in `tests/integration/test_cli.py`
- [x] T043 [US4] Add failing CLI classification tests: empty/oversized/unbalanced queries exit 4, invalid filters exit 4, unknown scopes exit 3, missing/foreign/newer workspaces exit 6, capability/incomplete/drifted exit 6 in `tests/integration/test_cli.py`
- [x] T044 [US4] Add failing CLI output-safety tests: no full block bodies, no SQL/FTS expressions, bounded escaped snippets in human lines and versioned JSON envelopes for both verbs in `tests/integration/test_cli.py`
- [x] T045 [P] [US4] Add failing security tests: operator-token injection stays literal, hostile snippet text is escaped and inert, zero network calls and untrusted exception causes stay suppressed in `tests/security/test_search_boundaries.py`

### Implementation for User Story 4

- [x] T046 [US4] Implement `search` and `reindex` parsing, mapping, rendering and exit classification in `src/openardp/interfaces/cli.py` following the F004 verb pattern without SQL/FTS/snippet logic in the interface layer
- [x] T047 [US4] Run the complete US4 and security suites plus focused Ruff/mypy and record the passing evidence in `specs/005-lexical-search/implementation-notes.md`

**Checkpoint**: Both verbs compose with the existing CLI contract and the full acceptance corpus passes through the installed entry point.

---

## Phase 7: Polish, convergence and repository gates

**Purpose**: Cross-cutting validation, documentation and the mandatory quality gates before the F005 commit.

- [x] T048 [P] Execute all five quickstart scenarios offline against a temporary workspace and capture the observed outputs in `specs/005-lexical-search/implementation-notes.md`
- [x] T049 [P] Update `README.md`, `CHANGELOG.md`, `VALIDATION.md`, `specs/README.md` and the touched `docs/` architecture/testing pages with only delivered F005 behavior
- [x] T050 Run the full locked gates (`ruff check`, `ruff format --check`, strict `mypy src` native and `--platform win32`, `pytest` with coverage, `pre-commit run --all-files`, `scripts/validate_repository.py`, `uv build` plus isolated wheel import) and record results in `specs/005-lexical-search/implementation-notes.md`
- [x] T051 Re-run the Spec Kit analysis and convergence audit against spec/plan/tasks/code, close every finding as an appended task and finalize `specs/005-lexical-search/implementation-notes.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; **blocks all user stories** (grammar, migration 4, capability probe and port methods are shared prerequisites).
- **US1 (Phase 3)**: Depends on Phase 2; provides the indexed corpus every later story reads.
- **US2 (Phase 4)**: Depends on US1 (requires committed indexed representations).
- **US3 (Phase 5)**: Depends on US2 (extends the working query path with filters).
- **US4 (Phase 6)**: Depends on US2/US3 service behavior; reindex CLI depends on US1.
- **Polish (Phase 7)**: Depends on all user stories.

### Within Each User Story

- Tests MUST be written and observed failing before implementation.
- Adapter/catalog methods before service orchestration; services before CLI.
- Story checkpoint green before moving to the next priority.

### Parallel Opportunities

- T002, T003 and T004 touch different files and can run in parallel.
- Within each phase, all test tasks marked [P] address distinct concern groups and can be authored in parallel.
- T048 and T049 can run in parallel once the full suite is green.

---

## Parallel Example: User Story 2

```bash
# Author all US2 test groups together:
Task: "Term/phrase semantics tests in tests/integration/test_search_service.py"
Task: "Determinism tests in tests/integration/test_search_service.py"
Task: "Snippet tests in tests/integration/test_search_service.py"
Task: "Serve-time guard tests in tests/integration/test_search_service.py"
Task: "Snapshot-isolation tests in tests/integration/test_search_service.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3 (US1) and Phase 4 (US2): atomic indexing plus exact retrieval is the core value
4. **STOP and VALIDATE**: quickstart scenarios 1–3 pass through the service
5. Continue with US3 filters and the US4 CLI surface

### Incremental Delivery

1. Setup + Foundation → migration 4 live, fail-closed capability
2. US1 → every new ingest searchable; pre-feature workspaces recoverable
3. US2 → exact source-backed retrieval with verified snippets
4. US3 → deterministic scoping and filtering
5. US4 → stable CLI boundary for humans and automation
6. Polish → gates, docs, convergence
