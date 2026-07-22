# Tasks: Text Ingestion Vertical Slice

**Input**: Design documents from `specs/004-text-ingestion-slice/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/text-ingestion.md`, completed checklists

**Tests**: Mandatory. Public contracts, persisted behavior, security boundaries and every acceptance scenario require
deterministic offline tests. Author each phase's failing tests before its implementation where practical.

**Organization**: Tasks are dependency-ordered. User-story labels preserve independently demonstrable slices; foundational
tasks are shared prerequisites. Do not start F005.

## Phase 1: Setup and feature boundary

**Purpose**: Establish F004 scope, dependency and implementation evidence without adding behavior.

- [x] T001 Confirm clean `main`, create `codex/f004-text-ingestion-slice`, verify Spec Kit 0.13.3 integration and select the feature in `.specify/feature.json`
- [x] T002 Record the restated acceptance criteria, resolved design decisions and test-first evidence table in `specs/004-text-ingestion-slice/implementation-notes.md`
- [x] T003 [P] Update `tests/test_package.py` expectations for the planned F004 domain/port/adapter/service/interface module surface and first prove the missing-module/entry-point failures
- [x] T004 [P] Update `tests/test_repository_contract.py` to allow only the reviewed unchanged runtime dependencies plus the `openardp` console entry and first prove the expected entry-point failure
- [x] T005 Add `[project.scripts] openardp = "openardp.interfaces.cli:main"` to `pyproject.toml`, refresh `uv.lock` only if uv reports a lock-content change, and keep runtime dependencies unchanged
- [x] T006 Run the focused package/repository boundary tests and record the passing setup evidence in `specs/004-text-ingestion-slice/implementation-notes.md`

---

## Phase 2: Pure ingestion contracts and provider ports

**Purpose**: Define strict deterministic parser/representation/query records and narrow provider boundaries before I/O.

- [x] T007 [P] Add failing scalar, parser-recipe, parsed-block/document and resource-limit tests to `tests/domain/test_ingestion.py`
- [x] T008 [P] Add failing representation scope/identity, SHA-256-derived UUIDv8 golden-vector and Unicode-distinction tests to `tests/domain/test_ingestion.py`
- [x] T009 [P] Add failing representation lifecycle/lease, READY aggregate, hierarchy/cycle/order/line-provenance and object-consistency tests to `tests/domain/test_ingestion.py`
- [x] T010 [P] Add failing document-head, event, bounded result, freshness, summary/status and outline-record tests to `tests/domain/test_ingestion.py`
- [x] T011 Implement the pure F004 records, limits, validators and deterministic block-handle helper in `src/openardp/domain/ingestion.py`
- [x] T012 [P] Add failing structural parser-port and sanitized error-taxonomy tests to `tests/contract/test_ingestion_ports.py`
- [x] T013 [P] Extend the failing catalog protocol expectations for document/representation/head/query/event methods in `tests/contract/test_ingestion_ports.py`
- [x] T014 Implement `ParserAdapter` and typed parser errors in `src/openardp/ports/parser.py`, and extend `src/openardp/ports/catalog.py` with F004 methods/errors without weakening F003 contracts
- [x] T015 Export only reviewed public names from `src/openardp/domain/__init__.py` and `src/openardp/ports/__init__.py`
- [x] T016 Run focused domain/contract tests, Ruff and strict mypy; record foundation evidence in `specs/004-text-ingestion-slice/implementation-notes.md`

**Checkpoint**: Pure identities, aggregates, lifecycle and ports are independently validated with no I/O.

---

## Phase 3: User Story 2 — Deterministic TXT/Markdown parsing (Priority: P1)

**Goal**: Parse bounded verified UTF-8 byte streams into deterministic hierarchy/provenance candidates without side effects.

**Independent Test**: Feed synthetic chunked TXT/Markdown bytes directly to the adapter and validate all candidates without CAS, SQLite or CLI.

### Tests for User Story 2

- [x] T017 [P] [US2] Add failing TXT tests for empty/whitespace input, paragraphs, no trailing newline, LF/CRLF/CR and whitespace preservation in `tests/unit/test_text_parser.py`
- [x] T018 [P] [US2] Add failing Markdown tests for ATX/setext hierarchy, skipped levels, pre-heading paragraphs, fenced code, lists, quotes and delimiter-like fenced text in `tests/unit/test_text_parser.py`
- [x] T019 [P] [US2] Add failing streaming tests for UTF-8 characters/delimiters split across chunks, leading BOM, non-ASCII and code-point-distinct Unicode in `tests/unit/test_text_parser.py`
- [x] T020 [P] [US2] Add failing negative tests for unsupported media/profile, invalid UTF-8, embedded NUL, overlong line, excessive bytes/blocks and sanitized errors in `tests/unit/test_text_parser.py`
- [x] T021 [P] [US2] Add failing isolation tests for spawned streamed IPC, no path/network capability, timeout termination, crash/error sanitization, child cleanup and exact invocation counts in `tests/contract/test_ingestion_ports.py`

### Implementation for User Story 2

- [x] T022 [US2] Implement incremental strict UTF-8/BOM/newline handling and resource counters in `src/openardp/adapters/text_parser.py`
- [x] T023 [US2] Implement deterministic TXT paragraph candidates and exact line ranges in `src/openardp/adapters/text_parser.py`
- [x] T024 [US2] Implement the reviewed Markdown heading/paragraph/fence/list/quote subset, hierarchy and warnings in `src/openardp/adapters/text_parser.py`
- [x] T025 [US2] Implement the killable spawned-worker wrapper in `src/openardp/adapters/isolated_parser.py`, export both adapters from `src/openardp/adapters/__init__.py` and keep direct pure-adapter use out of product composition
- [x] T026 [US2] Run the complete parser suite plus focused Ruff/mypy and record the passing evidence

**Checkpoint**: The parser story is complete and independently usable through the provider port.

---

## Phase 4: User Story 1 — Workspace and safe local source boundary (Priority: P1)

**Goal**: Initialize/open explicit local state and snapshot one authorized regular source without modifying it.

**Independent Test**: Initialize a temporary store and snapshot synthetic files through a fake/real object store without invoking parser or catalog representation code.

### Tests for User Story 1

- [x] T027 [P] [US1] Add failing workspace-marker tests for new/repeated init, atomic marker publication, missing/malformed/newer/foreign roots and no implicit initialization in `tests/integration/test_workspace.py`
- [x] T028 [P] [US1] Add failing source tests for suffix/media mapping, canonical local source key, bounded descriptor streaming and exact CAS bytes in `tests/integration/test_local_source.py`
- [x] T029 [P] [US1] Add failing security tests for path controls, symlinks, junctions, directories, FIFO/device/socket where supported, descriptor/path mismatch and outer sentinels in `tests/security/test_local_source_boundaries.py`
- [x] T030 [P] [US1] Add failing source-race/limit tests for replace, truncate, append, oversize and before/after stat disagreement in `tests/security/test_local_source_boundaries.py`
- [x] T031 [P] [US1] Add failing immutability tests comparing source bytes, size, mtime and mode across success/cache/failure paths while explicitly excluding atime in `tests/security/test_local_source_boundaries.py`

### Implementation for User Story 1

- [x] T032 [US1] Implement safe path validation, media classification, no-follow regular descriptor open and source snapshot/inspection records in `src/openardp/adapters/local_source.py`
- [x] T033 [US1] Implement bounded descriptor-to-CAS streaming, post-read stability checks and body-free error translation in `src/openardp/adapters/local_source.py`
- [x] T034 [US1] Implement canonical version-1 marker validation and atomic marker publication in `src/openardp/adapters/local_workspace.py`
- [x] T035 [US1] Implement explicit workspace initialize/open composition over `FilesystemObjectStore` and `SQLiteCatalog` in `src/openardp/adapters/local_workspace.py`
- [x] T036 [US1] Run focused workspace/source/security tests plus Ruff/mypy and record the passing evidence

**Checkpoint**: Workspace and source boundaries are complete without representation behavior.

---

## Phase 5: User Story 3 — Atomic representations, claims and cache evidence (Priority: P1)

**Goal**: Persist one complete READY representation, prevent duplicate active parsing, verify unchanged reuse and advance a correct current head.

**Independent Test**: Exercise migration/catalog and the ingestion service with a parser spy against temporary CAS/SQLite state.

### Tests for User Story 3

- [x] T037 [P] [US3] Add failing migration-3 tests for fresh/v1/v2 upgrade, unchanged prior checksums, repeated open, injected rollback, too-new and exact table/index shape in `tests/integration/test_ingestion_catalog.py`
- [x] T038 [P] [US3] Add failing acquire/renew/fail tests for absent/READY/BUSY, same-token retry, strict expiry, takeover and stale owner/token/revision fencing in `tests/integration/test_ingestion_catalog.py`
- [x] T039 [P] [US3] Add failing READY commit tests for object registration, empty blocks, hierarchy, events, head, exact retry and every immutable conflict in `tests/integration/test_ingestion_catalog.py`
- [x] T040 [P] [US3] Add failing fault-injection tests after object metadata, block inserts, READY transition, head, event and pre-commit with independent-reader proof in `tests/integration/test_ingestion_catalog.py`
- [x] T041 [P] [US3] Add failing head tests for A → B → A, older overlapping completion, equal-time conflict and monotonic event order in `tests/integration/test_ingestion_catalog.py`
- [x] T042 [P] [US3] Add failing reachability tests proving every historical manifest/native/block root is retained and analysis remains read-only in `tests/integration/test_reachability.py`
- [x] T043 [P] [US3] Add failing service tests for first TXT/MD ingest, manifest/block CAS validation, source-version reuse and parser-from-CAS-only in `tests/integration/test_ingestion_service.py`
- [x] T044 [P] [US3] Add failing service tests for 20 unchanged hits, eight concurrent unchanged requests, initial claim BUSY behavior and exact parser invocation counts in `tests/integration/test_ingestion_service.py`
- [x] T045 [P] [US3] Add failing changed-source, A → B → A, failed-attempt retry, source-removed queryability and prior-version immutability tests in `tests/integration/test_ingestion_service.py`
- [x] T046 [P] [US3] Add failing forced equal/divergent output, missing/corrupt cache artifact and no-automatic-reparse tests in `tests/integration/test_ingestion_service.py`

### Implementation for User Story 3

- [x] T047 [US3] Append `MIGRATION_3` and revision/table metadata without modifying revisions 1–2 in `src/openardp/adapters/sqlite_migrations.py` and `src/openardp/adapters/sqlite_catalog.py`
- [x] T048 [US3] Implement document lookup/list plus representation row conversion and aggregate reload helpers in `src/openardp/adapters/sqlite_catalog.py`
- [x] T049 [US3] Implement fenced representation acquire/renew/fail transitions with parameterized SQL in `src/openardp/adapters/sqlite_catalog.py`
- [x] T050 [US3] Implement atomic READY aggregate commit, immutable retry comparison, block inserts, head ordering and ingestion events in `src/openardp/adapters/sqlite_catalog.py`
- [x] T051 [US3] Implement READY reuse recording, summary/scope/block/event queries and expanded reference snapshots in `src/openardp/adapters/sqlite_catalog.py`
- [x] T052 [US3] Implement candidate-to-F002 manifest/block normalization, deterministic block IDs and canonical CAS record serialization in `src/openardp/services/ingestion.py`
- [x] T053 [US3] Implement the snapshot/register-or-reuse/acquire/cache/parse/commit/fail orchestration with injected clock/owner/token sources in `src/openardp/services/ingestion.py`
- [x] T054 [US3] Verify all READY artifact bytes/models before cache reuse and keep corrupt/incomplete results explicit in `src/openardp/services/ingestion.py`
- [x] T055 [US3] Run focused migration/catalog/reachability/service tests plus Ruff/mypy and record the passing evidence

**Checkpoint**: First ingest, unchanged skip, changed version, force and concurrency are durable and independently proven.

---

## Phase 6: User Story 4 — Body-minimizing navigation (Priority: P2)

**Goal**: List, compare freshness, navigate hierarchy and retrieve one exact persisted block without FTS or live-path fallback.

**Independent Test**: Query multi-document/multi-version fixtures after deleting the original paths and inspect which CAS objects were read.

### Tests for User Story 4

- [x] T056 [P] [US4] Add failing deterministic body-free list and registered/no-ready/current summary tests to `tests/integration/test_document_query.py`
- [x] T057 [P] [US4] Add failing status tests for path/document ID, current/changed/missing/not-registered/incomplete/integrity states and zero parser calls in `tests/integration/test_document_query.py`
- [x] T058 [P] [US4] Add failing outline tests for current/historical scope, hierarchy/depth/line labels and proof that unrelated paragraph objects are not read in `tests/integration/test_document_query.py`
- [x] T059 [P] [US4] Add failing get tests for one current exact block, source removal, unknown/ambiguous handles, scope projection mismatch and corrupt object in `tests/integration/test_document_query.py`

### Implementation for User Story 4

- [x] T060 [US4] Implement deterministic summaries and safe source freshness inspection without parsing or CAS publication in `src/openardp/services/document_query.py`
- [x] T061 [US4] Implement exact READY scope resolution and progressive outline loading in `src/openardp/services/document_query.py`
- [x] T062 [US4] Implement unambiguous current-block resolution, CAS verification, strict F002 deserialization and projection cross-checks in `src/openardp/services/document_query.py`
- [x] T063 [US4] Run focused query tests plus Ruff/mypy and record passing evidence

**Checkpoint**: All library use cases required by the CLI are complete without search infrastructure.

---

## Phase 7: CLI completion

**Purpose**: Expose the six bounded use cases through stable human and machine interfaces.

- [x] T064 [P] Add failing installed-entry/help/usage and missing-workspace CLI tests in `tests/integration/test_cli.py`
- [x] T065 [P] Add failing human and JSON tests for `init`, `ingest`, `list`, `status`, `outline` and `get` in `tests/integration/test_cli.py`
- [x] T066 [P] Add failing exit/error mapping, single-stdout-envelope, UTF-8/control-text and non-`get` body-leak tests in `tests/integration/test_cli.py`
- [x] T067 Implement `argparse` command grammar, composition and success DTO conversion in `src/openardp/interfaces/cli.py`
- [x] T068 Implement stable JSON/human rendering plus sanitized error/exit classification in `src/openardp/interfaces/cli.py`
- [x] T069 Export the interface entry point from `src/openardp/interfaces/__init__.py` and verify wheel-installed `openardp` execution
- [x] T070 Run the full CLI suite plus package/repository contracts and record passing evidence

---

## Phase 8: Documentation and full quality gates

**Purpose**: Align authoritative documentation and prove the complete bounded feature.

- [x] T071 [P] Update delivered F004 boundaries in `README.md`, `START_HERE.md`, `CHANGELOG.md`, `VALIDATION.md` and `specs/README.md`
- [x] T072 [P] Update concrete representation/parser/head behavior in `docs/02_ARCHITECTURE.md`, `docs/03_DATA_MODEL_AND_PACKAGE.md`, `docs/04_INCREMENTAL_PROCESSING.md`, `docs/07_TEST_AND_BENCHMARK_STRATEGY.md`, `docs/09_CODEX_EXECUTION_PLAN.md` and `docs/11_OPERATIONAL_AND_ENTERPRISE_REQUIREMENTS.md`
- [x] T073 Verify `schemas/`, accepted ADR identity projections, dependency set and F005+ module/command boundaries remain unchanged; document the result
- [x] T074 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` and `uv run pytest`
- [x] T075 Run `uv run --locked pre-commit run --all-files`, `uv build`, `git diff --check`, schema drift check and tracked-file drift inspection
- [x] T076 Inspect the complete diff for source immutability, body leakage, parameterized SQL, trust labels, exact feature scope and accidental artifacts
- [x] T077 Complete every task checkbox, record exact local evidence/tradeoffs/residual risks in `specs/004-text-ingestion-slice/implementation-notes.md` and set local implementation status

---

## Phase 9: Spec Kit convergence and publication

**Purpose**: Prove implementation/artifact convergence and externally verify each supported operating system.

- [x] T078 Run `$speckit-converge`, append only genuinely missing implementation tasks and repeat until zero unresolved findings
- [x] T079 Re-run all mandatory local gates after convergence and verify `tasks.md` changed only through explicit append/status updates
- [ ] T080 Commit the complete bounded F004 feature, push `codex/f004-text-ingestion-slice` and open a focused pull request
- [ ] T081 Require and record green Ubuntu, macOS and Windows PR-head workflow jobs, fixing any portability issue before merge
- [ ] T082 Mark the PR ready, squash-merge only after all gates pass, then require and record green post-merge `main` CI
- [ ] T083 Commit/push the final F004 validation-evidence closeout on `main`, require its cross-platform CI and confirm clean synchronized local/remote heads before starting F005

## Phase 10: Convergence

- [x] T084 Exercise `init`, `ingest`, `list`, `status`, `outline` and `get` in both human and JSON mode through the installed `openardp` entry point in `tests/integration/test_cli.py` per SC-007, plan CLI testing and T065/T069 (partial)
- [x] T085 Handle empty source-backed Markdown block quotes deterministically with a bounded warning and add direct/isolated regression coverage in `tests/unit/test_text_parser.py` and `tests/contract/test_ingestion_ports.py` per FR-009 and the Markdown edge-case contract (partial)

---

## Dependencies and execution order

1. Phase 1 establishes scope and packaging.
2. Phase 2 blocks all behavior until pure contracts/ports pass.
3. Phases 3 and 4 can be implemented independently after Phase 2.
4. Phase 5 depends on Phases 3 and 4 plus F003 persistence.
5. Phase 6 depends on READY aggregates from Phase 5.
6. Phase 7 depends on all four user-story services.
7. Documentation, convergence and publication follow complete behavior.

## Parallel opportunities

- Tasks marked `[P]` may run in parallel only when they edit distinct files or independent test sections.
- Parser tests and workspace/source tests are independent after the domain/port foundation.
- Documentation files in T071/T072 are independent after behavior stabilizes.
- SQLite implementation tasks T047–T051 are serialized because they share migration/catalog transaction code.

## Completion rule

F004 is complete only when all 83 tasks are checked, all mandatory local gates pass, convergence reports zero unresolved
findings, the focused PR is merged, post-merge `main` CI and the final evidence-commit CI are green on Linux/macOS/Windows,
and no F005+ behavior entered the diff.
