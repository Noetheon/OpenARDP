# Implementation Notes: Context Compiler and Selection Receipts

**Feature**: `008-context-compiler-receipts`

**Branch**: `codex/f008-context-bundles`

**Date**: 2026-07-26

## Acceptance criteria restatement

- Compile deterministic version-pinned text and rich evidence under an exact budget.
- Preserve untrusted-data boundaries and surface missing/visual evidence honestly.
- Emit immutable body-free selection receipts with complete decision/accounting facts.
- Replay exact snapshots and reject tokenizer, policy, algorithm or integrity drift.
- Persist bundle/receipt links atomically without changing earlier public schema bytes.
- Preserve all F001–F007 behavior and pass the complete three-platform gate.

## Frozen baseline

- Base commit: `4561cfdc40d069ebd3f24868c43c19725214f108`.
- Python: CPython 3.12.13 on macOS.
- Source modules: 38.
- Test collection: 566 tests.
- Existing public schemas: 9.
- Locked local baseline:
  - Ruff and formatting: pass; 90 files;
  - strict mypy native and Windows target: pass; 38 source modules;
  - pytest: 566 passed in 134.54 seconds; 85.36% branch coverage;
  - all 9 schemas current;
  - F006 conformance: 7 valid, 8 invalid, 1 record set, 6 identity vectors;
  - repository validation, source/wheel build and `git diff --check`: pass.

### Frozen public artifact hashes

| Artifact | SHA-256 |
|---|---|
| `block.schema.json` | `413d725016a9f4f261e384efff3f82906a08c7e3b73a25bc8f96963a10861562` |
| `context-bundle.schema.json` | `e6cea129f58bd11ec52e1f63ef87258d8ec9c01ac37ff7fa933b08e96790a31a` |
| `derivation.schema.json` | `56e8fc17050584b6d4bfc430d5f8d24de03237e5ef2b96fc7d9f6afd61f3e88a` |
| `evidence-projection.schema.json` | `cc580d589e46142a6c8429e0deb855c1bf3be79cf4334d9b39129e46c80aaf1e` |
| `evidence-reference.schema.json` | `b86968eca4d9a8c208c4a4f52f207dda863377dcc5bf353775b0067e2b4f4362` |
| `manifest.schema.json` | `1995cc1062e5322405a00adba8e47c7f3bed9fa294de6920dc27476c5a36dfd4` |
| `native-representation.schema.json` | `c4685f98633f2628240059e55703a0d8f27e32eb549cd7d453deb91b23d4d6ef` |
| `relation.schema.json` | `00b581b077089e6534f4cc0c3af511fa2caa8ede6b81649ee5094f0b60bca142` |
| `trust-classification.schema.json` | `7c4a7b429a3994ebd62af394b06cf7daaeeb691720778ef0122c1871fff302bc` |
| F002 identity vectors | `9387f64d8cf90f2039ca975c71d6f02d57cef8027005b69da6e07b4f8b6c291b` |
| F006 identity vectors | `da1c718da44c6e51f3ec2e7aafcd94de4b59dad8b3c02e442eb02527a8729e97` |

The initial Spec Kit analysis covered 28 functional requirements, 12 success criteria,
four independently testable user stories and 76 tasks. It found one CRITICAL provenance
contradiction: ContextBundle `0.1.0` requires a F002 block UUID, while F007 rich evidence
has exact F006 SHA-256 projection identities. The originating spec, plan, research, data
model, contracts and tasks now add ContextBundle `0.2.0` with discriminated
block/projection provenance while preserving `0.1.0`. The second analysis pass found no
unresolved critical/high finding and complete requirement coverage.

## Test-first and phase evidence

### Phase 1 — Baseline and contract freeze (T003, T004, T006)

- `tests/test_package.py` bounds the F008 module surface (new `domain.context_compilation`
  and `ports.context` only) and proves in a fresh subprocess that both context surfaces
  plus `ports.catalog` import without loading any `docling` module. Adapter/service
  surface entries for Phase 3 modules (`context_estimators`, `context_candidates`,
  `context_compiler`) were removed from the Phase 1 expectations and belong to the
  Phase 3 test-first tasks.
- `tests/test_repository_contract.py::test_f007_contract_bytes_remain_frozen` hashes all
  nine F007 schemas, both established identity-vector files and the complete F006
  conformance tree against the frozen table above.
- Focused runs (red when the modules were absent, green after implementation):
  - `uv run pytest tests/test_package.py tests/test_repository_contract.py -q --no-cov`
    → 39 passed.

### Phase 2 — Foundational domain, contract and ports (T007–T019)

Test-first files and coverage:

- `tests/domain/test_context_compilation.py` (31 tests): request/policy/limit bounds and
  nesting, sorted-unique corpus snapshot, candidate/provenance scope and identity
  agreement, closed discriminated block/projection union, exact budget-ledger
  recomputation, decision partition and machine reason codes, extension URI namespaces,
  receipt body-freedom, flat and nested receipt-identity mutation matrix, UUIDv5 bundle
  identity, unpinned/duplicate/empty evidence rules, compilation result/record/commit
  invariants.
- `tests/contract/test_context_ports.py` (5 tests): runtime-protocol shape of estimator,
  both candidate sources and the additive `ContextCatalog` port, sanitized failure
  taxonomy distinct from catalog persistence errors.
- `tests/domain/test_models.py` (10 new tests): golden round-trip and invalid raw JSON
  for `ContextBundleV020` and `SelectionReceipt`; `ContextBundle 0.1.0` remains the
  installed prior reader and rejects `0.2.0` input.
- `tests/contract/test_context_schemas.py` (new; T011 names `tests/test_schema_generation.py`,
  mapped to the repository's per-contract convention alongside
  `test_domain_schemas.py`/`test_evidence_schemas.py`): schema/model parity for both new
  roots, closed direct fields, distinct version-failure categories, deterministic
  generation and committed bytes, body-free receipt shape, data-only trust, closed
  provenance union and structural untrusted-content envelope at schema level.
- `tests/domain/test_identity_vectors.py` (7 tests) with
  `tests/fixtures/context/canonicalization-vectors.json`: independent task-digest,
  policy-digest, receipt-id, bundle-UUIDv5 and compilation-row-fingerprint vectors,
  recomputation from the golden fixtures and stability across three fresh interpreter
  processes with different `PYTHONHASHSEED` values.

Generated public artifacts (deterministic across two consecutive `--write` runs,
`--check` reports `all 11 schemas are current`):

| Artifact | SHA-256 |
|---|---|
| `schemas/context-bundle-0.2.0.schema.json` | `2a5c3c286456aae31fa558f8d43d7c9226b15affc6d96a6641d4666e886a3d9e` |
| `schemas/selection-receipt.schema.json` | `05c24f533da13b9705af4e6f25f0b96d5e41ee5d1d329756571a5c63a867d607` |
| `tests/fixtures/context/canonicalization-vectors.json` | `2e221ba1533ce53db389fffa37a25b633472ef49646e6f9f3be5c68ff752afad` |
| `tests/fixtures/context/context-bundle-0.2.0.json` | `d275077fa059faf2fc02886c1db8556eb6a34d30b5e572f4cf1a74f4b40f0610` |
| `tests/fixtures/context/selection-receipt.json` | `47ec5bbf657757cdf6018441774334fba3864d30c7b3c709799a1d3bd79b55fd` |

All nine pre-F008 schema hashes and both established vector hashes remain byte-identical
(proven by `test_f007_contract_bytes_remain_frozen`).

Closing gate for Phases 1–2 (exact commands):

- `uv run pytest tests/domain tests/contract tests/test_package.py tests/test_repository_contract.py tests/test_repository_validation.py --no-cov`
  → 398 passed in 7.97 s.
- `uv run ruff check .` → all checks passed.
- `uv run ruff format --check .` → 96 files already formatted.
- `uv run mypy src` → success, no issues in 40 source files.
- `uv run mypy src --platform win32` → success, no issues in 40 source files.

### Phase 3 — User Story 1: compile bounded evidence (T020–T034)

Test-first files and coverage:

- `tests/unit/test_context_estimators.py` (8 tests): exact UTF-8 byte, scalar-character
  and conservative token estimators at version `1.0.0`, distinct config hashes,
  `BUILT_IN_ESTIMATORS`/`resolve_estimator` closed registry and fixed-point budget
  accounting with length-invariant identity placeholder.
- `tests/unit/test_context_candidates.py` (12 tests): deterministic bounded lexical item
  normalization with fail-closed caps, FTS discovery with coverage-checked full-body
  CAS reverification and exact casefolded integer rescoring, fail-closed mapping of
  incomplete/drifted accelerators, stale superseded index rows as body-free STALE
  candidates, cancellation checkpoints, bounded provider-free rich projection scans
  with representation verification and media-type mapping, body/discovery limits, and
  the synthetic mixed classification partition (stale/trust/sensitivity/duplicate) plus
  complete deterministic total order and policy-over-mode required representations.
- `tests/integration/test_context_compiler.py` (6 tests): real mixed text+rich corpus
  compiled end to end with both record types in one bundle and a body-free receipt,
  fail-closed snapshot resolution for unknown documents and documents without READY
  heads (failed rich parse leaves FAILED representation), estimator-identity mismatch
  rejection, exact budget fit followed by one-unit overflow omitting exactly the last
  item, base-bundle-over-budget refusal, and the T034 20-repeat probe asserting
  byte-identical canonical bundle and receipt bytes plus identical identities.
- `tests/security/test_context_boundaries.py` (3 tests): prompt-injection strings in
  task and evidence bodies survive only inside the `untrusted_data`/
  `openardp-evidence-v1` envelope with `instruction_execution_allowed=False`; NUMERIC
  and VERIFICATION modes without matching evidence report `required_evidence_unavailable`
  instead of substitutes; VISUAL mode escalates the missing handle as
  `visual_evidence_required` missing evidence plus receipt notice without fabricating
  visual items.

Implementation surfaces:

- `src/openardp/adapters/context_estimators.py`: `Utf8ByteEstimator`,
  `UnicodeCharacterEstimator`, `ConservativeTokenEstimator` (each version `1.0.0`),
  `BUILT_IN_ESTIMATORS`, `resolve_estimator`, `fixed_point_measure`.
- `src/openardp/adapters/context_candidates.py`: `lexical_query_items`,
  `lexical_match_expression`, `lexical_score`, `TextLexicalCandidateSource` (FTS5 OR
  discovery per snapshot document with `include_history`, coverage errors mapped to
  `accelerator_incomplete`/`accelerator_drifted`, full-body CAS reverification plus
  ContentBlock and text-hash validation before exact rescoring, superseded rows exposed
  as STALE body-free candidates, page exhaustion fail-closed),
  `RichLexicalCandidateSource` (skips non-rich scopes, injected representation verifier,
  `text/plain`→EXACT and canonical `application/json`→STRUCTURED, body limit
  fail-closed, trust mapped from the accepted projection).
- `src/openardp/services/context_compiler.py`: `context_algorithm_identity`,
  `required_representations`, `candidate_total_order_key`, `classify_candidates` and
  `ContextCompilerService.compile` (estimator-identity match, exact READY-head snapshot
  with `created_at=max(last_ingested_at)`, discovery/candidate truncation flags,
  greedy admission with full canonical bundle re-measurement per candidate via a
  fixed-width placeholder identity, honest missing-evidence and visual escalation,
  UUIDv5 bundle identity and SHA-256 receipt identity recomputed over canonical
  payloads).
- `src/openardp/adapters/__init__.py` and `src/openardp/services/__init__.py` export the
  reviewed surfaces; `tests/test_package.py` restored the Phase 3 module entries and the
  subprocess proof imports `adapters.context_estimators`,
  `adapters.context_candidates` and `services.context_compiler` without loading any
  `docling` module.

Closing gate for Phase 3 (exact commands):

- `uv run pytest tests/unit/test_context_estimators.py tests/unit/test_context_candidates.py tests/integration/test_context_compiler.py tests/security/test_context_boundaries.py tests/test_package.py -q --no-cov`
  → 46 passed.
- `uv run pytest tests/unit tests/domain tests/contract tests/integration tests/security tests/test_package.py tests/test_repository_contract.py tests/test_repository_validation.py --no-cov`
  → 665 passed in 34.71 s.
- `uv run ruff check .` → all checks passed.
- `uv run ruff format --check .` → 103 files already formatted.
- `uv run mypy src` → success, no issues in 43 source files.
- `uv run mypy src --platform win32` → success, no issues in 43 source files.

### Phase 4 — User Story 2: explain, persist and replay selection (T035–T046)

Test-first files and coverage:

- `tests/integration/test_sqlite_catalog.py` (extended): migration 5→6 upgrade keeps
  every prior migration checksum byte-identical, revision-6 schema validation covers all
  21 tables, and `test_failed_migration_six_rolls_back_to_revision_five_unchanged`
  proves a failing migration 6 leaves the database at revision 5 with unchanged content
  (T035). Hard-wired revision-5 assertions were raised to 6 in
  `test_sqlite_catalog.py`, `test_rich_catalog.py` and `test_ingestion_catalog.py`;
  the too-new probe now uses version 7.
- `tests/integration/test_context_catalog.py` (new, 8 tests): commit/load/list roundtrip
  and `None` for unknown receipts, atomic idempotent re-commit with exact record equality
  plus immutable-conflict rejection of a divergent same-identity record, scope-root
  foreign-key refusal for non-persisted representations, receipt/bundle objects as
  reachability roots, and tamper refusal for mutated rows, mutated CAS objects and
  scope-ordinal reordering, including service-level `load_verified` against a tampering
  store (T036, T037).
- `tests/integration/test_context_compiler.py` (extended, +3 tests): five
  compile-persist-load cycles converge byte-identically, replay stays pinned to the
  recorded snapshot after a newer head is committed (fresh compile diverges, replay of
  the stored receipt reproduces the stored bundle/receipt bytes exactly), and replay
  fails closed with `task_mismatch`/`estimator_mismatch`/`algorithm_mismatch` for
  wrong task, estimator or algorithm identities (T038).
- `tests/security/test_context_boundaries.py` (extended, +1 test): privacy scan proves
  task text, evidence bodies and source paths appear neither in receipt CAS bytes nor in
  SQLite compilation rows nor in captured logs, with a positive control asserting the
  markers do appear in the untrusted bundle envelope (T039).
- `tests/unit/test_context_candidates.py` (rewritten):
  `test_superseded_versions_stay_invisible_not_silent_drift` now asserts superseded
  index rows stay invisible to fresh compiles while a pinned replay snapshot still
  discovers the superseded version exactly; drift (index row without catalog version)
  still fails closed as `accelerator_drifted`.

Implementation surfaces:

- `src/openardp/adapters/sqlite_migrations.py`: `MIGRATION_6` ("context-compilations")
  adds `context_compilations` (receipt identity PK with
  `CHECK (receipt_id = receipt_object_id)`, receipt/bundle object references with byte
  lengths and object foreign keys, bundle identity, task/algorithm/estimator/policy
  digests and identity triples, budget limit and unit, four counts, row fingerprint,
  creation timestamp) and `context_compilation_scopes` (PK `(receipt_id, ordinal)`,
  unique scope, RESTRICT foreign keys to the compilation and to
  `document_representations`) plus three indexes; `CURRENT_SCHEMA_VERSION` is 6 (T040).
- `src/openardp/adapters/sqlite_catalog.py`: `_SCHEMA_TABLES[6]`; `reference_snapshot`
  unions receipt/bundle object ids from `context_compilations` so both CAS objects are
  reachability roots without touching `ReachabilityService` (T042);
  `commit_context_compilation` (single `BEGIN IMMEDIATE` write, object registration,
  scope-root precheck mapped to `RepresentationNotFound`, insert-or-ignore rows followed
  by reload and exact equality comparison mapped to `ContextCompilationConflict`),
  `load_context_compilation`/`_load_context_compilation` (row→model revalidation with
  closed `CatalogError` mapping) and `list_context_compilations` ordered by receipt
  identity (T041).
- `src/openardp/services/context_compiler.py`: module helpers `receipt_object_bytes`
  (canonical identity envelope `{canonicalization, domain:
  "openardp:selection-receipt", identity_version: 1, payload}` whose SHA-256 equals the
  receipt identity, so the CAS object id equals the receipt id) and
  `bundle_object_bytes`; `PersistedCompilation`; `compile_and_persist` (compile, publish
  and reverify both CAS objects, compute the row fingerprint, atomic catalog commit,
  verified reload with `persisted_compilation_diverged` on any drift); `load_verified`
  (row revalidation, receipt envelope verification including canonicality, bundle
  canonicality, and closed cross-fact checks: `row_mismatch`, `count_mismatch`,
  `scope_mismatch`, `scope_missing`, `decision_mismatch`, `budget_mismatch`);
  `replay(task, receipt_id)` (verified load, `task_mismatch`/`estimator_mismatch`/
  `algorithm_mismatch` guards, snapshot rebuilt from the persisted scope rows with the
  receipt timestamp, recompile on that exact snapshot and byte comparison of bundle and
  receipt, returning the stored verified objects) (T043–T045).
- `src/openardp/domain/identity.py`: exported constant `SELECTION_RECEIPT_DOMAIN`;
  receipt identity values are unchanged, so the frozen Phase 2 vectors stay valid.
- `src/openardp/adapters/context_candidates.py`: non-snapshot FTS rows are skipped
  instead of surfaced as STALE candidates; rows without any catalog version still fail
  closed as `accelerator_drifted`.

Design notes:

- The receipt CAS object stores the identity envelope itself; object id == receipt id
  holds by construction and is enforced by `CHECK (receipt_id = receipt_object_id)`.
- Superseded FTS rows are invisible rather than stale because the frozen Phase 2 domain
  contract requires every receipt decision scope to lie inside the corpus snapshot;
  staleness remains representable for scopes inside the snapshot, and replay pins exact
  recorded scopes instead of floating to newer heads. This refines the Phase 3 discovery
  wording above; the stale-candidate helper was removed accordingly.
- Replay rebuilds the request with the recorded policy, budget and default
  `ContextCompileLimits`: compilations recorded with non-default limits fail replay
  honestly as a mismatch instead of silently converging.
- Rollback: migration 6 is additive; a revision-5 backup is required for older readers,
  never an in-place downgrade.

Closing gate for Phase 4 (exact commands):

- `uv run pytest tests/unit/test_context_candidates.py tests/integration/test_context_compiler.py tests/security/test_context_boundaries.py tests/integration/test_context_catalog.py tests/integration/test_sqlite_catalog.py --no-cov`
  → 63 passed in 4.53 s.
- `uv run pytest tests/ -q --no-cov` → 679 passed in 31.89 s (Phase 3 baseline: 665),
  including `tests/test_repository_contract.py::test_f007_contract_bytes_remain_frozen`
  (all nine legacy schemas and both legacy vectors byte-identical).
- `uv run ruff check .` → all checks passed.
- `uv run ruff format --check .` → 104 files already formatted.
- `uv run mypy src` → success, no issues in 43 source files.
- `uv run mypy src --platform win32` → success, no issues in 43 source files.

### Phase 5 — User Story 3: fail closed on integrity and lifecycle faults (T047–T057)

Test-first files and coverage:

- `tests/security/test_context_boundaries.py` (extended, +5 tests): incomplete index
  coverage, version-rewired (orphaned) index scopes and drifted indexed text hashes all
  fail closed with closed accelerator/verification codes while the compiler never
  rebuilds, bypasses or mutates the index and leaves zero compilation rows (T047);
  corrupted evidence bodies, receipt objects and bundle objects fail compile and
  `load_verified` while the intact compilation stays byte-identical (T048); index trust
  metadata cannot promote candidate trust — rejection uses only the reverified body
  trust and stays body-free (T048); discovery/body/decision caps fail closed,
  scope/bundle-unit caps reject the request model-side, and soft candidate truncation
  stays honest via receipt flag and notice (T049); cancellation, limit and
  integrity-failure messages, their full cause chains and DEBUG logs carry no task,
  body, path or traceback data, with a positive marker control in the bundle (T052).
- `tests/integration/test_context_compiler.py` (extended, +2 tests): cancellation
  before retrieval, during verification and post-CAS pre-commit leaves no
  catalog-visible compilation, pre-published objects remain unreachable recovery
  candidates, and a retry converges on the identical compilation (T050); publication
  and once-failing commit faults expose no partial row, retries converge on identical
  identities, duplicate commits collapse to one immutable record, and a prior
  compilation stays byte-identical throughout (T051).

Implementation surfaces:

- `src/openardp/services/context_compiler.py`: combined discovery is truncated after
  every source so no cross-source allocation can exceed `max_discovered` (T053);
  measurement drafts build `ContextBundleBudget` via `model_construct`, so tiny budgets
  converge to the closed `ContextLimitExceeded` taxonomy instead of leaking raw
  pydantic `ValidationError` across the service boundary (T054); new bounded
  cancellation checkpoint `cancelled_before_commit` after CAS publication and
  verification, before the atomic commit (T054); sanitized closed failure mapping for
  commit (`compilation_commit_conflict`, `compilation_scope_root_missing`,
  `compilation_commit_failed`), snapshot reads (`catalog_read_failed`) and scope
  re-reads (`compilation_scope_unreadable`) (T054, T055); body-free structured
  operational logging through `openardp.context_compiler` with identifiers, counts and
  millisecond timings only, failure lines reduced to closed codes via `_failure_code`
  (T056). Catalog commit was already atomic (`BEGIN IMMEDIATE` + rollback on every
  fault class in `_write_connection`); no schema or catalog change was needed (T055).
- Public methods `compile`, `compile_and_persist`, `load_verified` and `replay` are now
  thin logging wrappers over private entry points, so every failure path emits exactly
  one sanitized warning and re-raises unchanged.

Design notes:

- `SearchIndexDrifted` is part of the port contract but never raised by the SQLite
  adapter; real drift is caught either by coverage (`accelerator_incomplete`) or by
  reverification (`indexed_text_drift`, `indexed_block_mismatch`), which the tests now
  pin explicitly. Orphan rows rewired to unknown versions are structurally invisible to
  search joins and surface as coverage failures first.
- The `max_bundle_units` and `max_scopes` bounds are enforced before any retrieval at
  the request-model boundary; admission (`ceiling < budget_limit <= max_bundle_units`)
  keeps measured usage below the unit cap structurally.
- Cancellation after publication intentionally leaves the immutable CAS objects on
  disk as unreachable recovery candidates for F013 retention tooling; no job or
  transaction state persists.

Closing gate for Phase 5 (exact commands):

- `uv run pytest tests/security/test_context_boundaries.py tests/integration/test_context_compiler.py --no-cov`
  → 20 passed in 4.12 s.
- `uv run pytest tests/ -q --no-cov` → 686 passed in 31.43 s (Phase 4 baseline: 679),
  including `tests/test_repository_contract.py` (all nine legacy schemas and both
  legacy vectors byte-identical) and `tests/test_package.py`.
- `uv run ruff check .` → all checks passed.
- `uv run ruff format --check .` → 104 files already formatted.
- `uv run mypy src` → success, no issues in 43 source files.
- `uv run mypy src --platform win32` → success, no issues in 43 source files.

### Phase 6 — User Story 4: stable local CLI workflows (T058–T064)

Test-first files and coverage:

- `tests/integration/test_cli_context.py` (new, 10 tests): JSON contract with exact
  data-key set, handles and accounting, sorted scopes, idempotent stable repeat with
  byte-equal data (T058); explicit `--include-bundle` returning the digest-checked
  untrusted-envelope payload (T058); exact deterministic body-free `context-receipt`
  JSON with byte-identical repeated output (T058); human summaries for both commands
  without task or body content (T058); pinned byte-identical replay through `--replay`
  (T058); honest no-match result with `required_evidence_unavailable` (T059); stable
  envelope mapping for tiny budget (4/rejected_input), replay task and unit mismatches
  (5/conflict), corrupted receipt CAS object (6/integrity_or_workspace), malformed
  receipt id and missing document (2/invalid_usage) (T059, T063); cancellation mapped
  to the conflict envelope in JSON and human modes via monkeypatched service fault
  (T059); task/body/path marker redaction across human, JSON, receipt and failure
  surfaces with an explicit include-bundle positive control (T059); prior list,
  search, outline and evidence JSON plus list/search human outputs unchanged in the
  mixed workspace (T060).

Implementation surfaces:

- `src/openardp/interfaces/cli.py`: `context` command (positional task, repeated
  `--document`, `--budget`, `--unit bytes|characters|tokens`, `--mode` over all six
  context modes, `--include-bundle`, `--replay RECEIPT_ID`) and `context-receipt`
  command (T061); `_estimator_for` maps the bounded unit names to the exact built-in
  estimator identities; `_context_compiler` composes the provider-free service over
  the open workspace with the verified text and rich candidate sources; replay rejects
  document/budget/mode flags as usage errors because the recorded receipt is
  authoritative; compile requests deduplicate and sort document ids (T061);
  `_context_summary` projects results into body-free handles, scopes, ledger and
  decision counts and attaches the full bundle only under `--include-bundle`;
  `context-receipt` returns the exact verified receipt model after `load_verified`
  (T062); human renderers print identifiers, counts, budget, warning codes and
  missing-evidence codes only (T062); `_classification` maps `ContextNotFound`→3,
  `ContextLimitExceeded`→4, `ContextConfigurationMismatch`/`ContextCompilationCancelled`→5
  and `ContextIntegrityFailure`→6 into the existing sanitized envelopes without new
  codes or messages (T063).

Design notes:

- The CLI default policy admits every sensitivity of the owner's own corpus
  (`maximum_sensitivity=UNKNOWN`) because text blocks carry `unknown` sensitivity and
  the model default would silently reject local notes; trust classification is still
  recorded body-free and instruction execution stays structurally disabled.
- `context` persists every compilation atomically so `context-receipt` can verify it;
  repeating the same arguments converges on the identical record through the Phase 4
  idempotent commit.
- The receipt CAS layout probe confirmed `objects/sha256/<2>/<2>/<rest>`; the
  corruption test writes through that real layout.
- `--unit` defaults to bytes and `--mode` to mixed when omitted; replay defaults to
  the bytes estimator and fails honestly with `estimator_mismatch` when the recording
  used another unit.

Closing gate for Phase 6 (exact commands):

- `uv run pytest tests/integration/test_cli_context.py --no-cov` → 10 passed in 0.66 s.
- `uv run pytest tests/integration/test_cli.py tests/integration/test_cli_rich.py --no-cov`
  → 8 passed in 7.69 s (prior CLI snapshots unchanged).
- `uv run pytest tests/ -q --no-cov` → 696 passed in 31.85 s (Phase 5 baseline: 686),
  including `tests/test_repository_contract.py` (all nine legacy schemas and both
  legacy vectors byte-identical).
- `uv run ruff check .` → all checks passed.
- `uv run ruff format --check .` → 105 files already formatted.
- `uv run mypy src` → success, no issues in 43 source files.
- `uv run mypy src --platform win32` → success, no issues in 43 source files.

## Validation

The final local gate ran from the exact locked feature tree on macOS with CPython
3.12:

| Command/evidence | Result |
|---|---|
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass; 105 files |
| `uv run mypy src` | pass; 43 source files |
| `uv run mypy src --platform win32` | pass; 43 source files |
| `uv run pytest` | 696 passed in 48.64 s; 85.92% total coverage (gate: 85% branch) |
| `uv run python scripts/generate_schemas.py --check` | all 11 schemas current |
| `uv run python scripts/validate_evidence_contracts.py conformance/evidence/v0.1.0/manifest.json` | 7 valid, 8 invalid, 1 record set, 6 identity vectors |
| `uv run python scripts/validate_repository.py` | pass |
| `git diff --check` | pass |
| `uv build` | source distribution and wheel built |

Byte comparison against the F007 base `4561cfd` found no change in any of the nine
earlier public schema JSON files, either canonicalization-vector file
(`tests/fixtures/domain/canonicalization-vectors.json`,
`conformance/evidence/v0.1.0/canonicalization-vectors.json`), or the complete F006
conformance corpus (`git diff HEAD --stat` empty for all three paths). Their frozen
hashes remain those recorded above; the in-repo freeze test
`tests/test_repository_contract.py::test_f007_contract_bytes_remain_frozen` passes.

Two consecutive schema generations both reported all 11 schemas current; the new
artifacts hash to
`context-bundle-0.2.0.schema.json`
`2a5c3c286456aae31fa558f8d43d7c9226b15affc6d96a6641d4666e886a3d9e`,
`selection-receipt.schema.json`
`05c24f533da13b9705af4e6f25f0b96d5e41ee5d1d329756571a5c63a867d607`,
`tests/fixtures/context/canonicalization-vectors.json`
`2e221ba1533ce53db389fffa37a25b633472ef49646e6f9f3be5c68ff752afad`.

Fresh isolated wheel probes established both packaging boundaries:

- the core wheel installed seven packages, imported all context compiler, estimator,
  candidate-source, domain and CLI surfaces, reported OpenARDP `0.0.1`, and had no
  `docling` distribution or loaded module;
- the installed core console executed `init`, `ingest`, `context`,
  `context-receipt` and `--replay` end to end for a text document, proving the
  context commands run without the optional provider installed;
- the rich wheel installed 103 packages with exactly `docling 2.114.0`, imported the
  CLI without eagerly loading any `docling` module, and executed compile plus
  byte-identical replay.

A live quickstart probe against the locked environment (fresh mixed workspace with
one Markdown and one synthetic DOCX document) confirmed: 20 repeated `context`
invocations converged on one receipt identity, five `--replay` invocations returned
the identical receipt with `replayed=true`, repeated `context-receipt` output was
byte-identical, no-match returned zero counts with honest missing evidence, a tiny
budget returned the stable `rejected_input` envelope, VISUAL mode escalated missing
visual evidence with its notice, and a task mismatch returned the stable `conflict`
envelope. Head-change pinning, exact-fit/overflow, corruption and cancellation flows
are executed by the dedicated integration and security tests recorded in Phases 3–6.

The final Spec Kit analysis mapped all 28 functional requirements, the success
criteria and the four independently testable stories to the 76 tasks and the
implementation evidence recorded above. No unresolved critical/high contradiction,
uncovered requirement, ambiguous normative term, or constitution violation remained.
Convergence found no additional task to append.

## Tradeoffs and residual risks

- Replay recompiles with default `ContextCompileLimits`; compilations recorded through
  the API with custom limits fail replay honestly as divergence instead of silently
  converging. CLI-recorded compilations always use the defaults.
- The CLI default policy admits every sensitivity of the owner's own corpus because
  text blocks carry `unknown` sensitivity; trust classification is still recorded
  body-free and instruction execution stays structurally disabled. Policy flags
  remain a later CLI refinement.
- The lexical baseline is deterministic but intentionally shallow: no semantic
  ranking, structural expansion or provider tokenizer exists yet. The estimator port
  and candidate-source protocols are the reviewed extension seams.
- `SearchIndexDrifted` is part of the catalog port contract but never raised by the
  SQLite adapter; drift is caught by coverage checks and reverification, which the
  hostile-path tests pin explicitly.
- Cancellation or commit faults after CAS publication leave immutable objects as
  unreachable recovery candidates until F013 retention/recovery tooling.
- Catalog revision 6 is forward-only for this release. Older readers require a
  revision-5 backup; live in-place downgrade is unsupported.
- The local evidence supports correctness, determinism, privacy and failure-taxonomy
  claims for the covered flows, not universal performance, recall or cross-platform
  claims. Linux/Windows execution evidence is inferred from the platform-strict
  mypy gate and portable code paths, not from remote runs (see below).

## Rollback

Revert the F008 implementation commit before opening a workspace at catalog revision 6.
After migration/use, restore a revision-5 backup for an older reader; never edit migration
history or downgrade a live catalog in place. Immutable pre-commit CAS objects may remain
unreachable until F013 recovery/retention tooling.

## Remote verification

GitHub Actions minutes for this repository are exhausted, so the three-platform
remote gate could not run for F008. In its place the complete locked local gate
above (Ruff, format, strict native and `win32` mypy, full network-blocked suite with
coverage, schema/conformance/repository validators, `git diff --check`, distribution
build and both isolated wheel probes) ran green on macOS; the `win32` mypy platform
gate and the three-platform-aware test design provide the portable-code evidence.
The merge is performed locally directly onto `main` by the maintainer; no pull
request or remote workflow exists for this feature. If remote minutes return, the
same quality workflow should be re-run against the merge commit and this section
updated with run identifiers.
