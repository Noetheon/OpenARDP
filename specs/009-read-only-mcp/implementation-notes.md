# Implementation Notes: Read-only MCP

**Feature**: `009-read-only-mcp`

**Branch**: `codex/f009-read-only-mcp`

**Date**: 2026-07-31

## Acceptance criteria restatement

- Expose prepared evidence through nine object-scoped, least-privilege MCP tools on
  one local stdio transport under pinned protocol revision `2025-06-18`.
- Reach state only through the existing verified service ports; accept identifiers
  only, never filesystem paths; no ingestion, reindex, deletion or source mutation.
- Label and delimit every returned body as untrusted data; default compile results
  to body-free handles with bounded explicit payload opt-in.
- Enforce bounded pagination, message and response caps, per-request deadlines and
  cooperative cancellation with one versioned sanitized error taxonomy.
- Keep MCP transport-only: no MCP SDK, no network listener, no new dependency, no
  new persisted contract, no workspace migration.
- Preserve all F001–F008 behavior, the eleven frozen schemas and every identity
  vector byte-for-byte, and pass the complete three-platform gate.

## Frozen baseline

- Base commit: `5a73d3a2e2bb524a2b190e3bec9178e6c249ad93`.
- Python: CPython 3.12.13 on macOS.
- Source modules: 43.
- Test collection: 696 tests.
- Existing public schemas: 11.
- Locked local baseline (recorded 2026-07-27, macOS arm64, after
  `uv sync --all-extras --locked`):
  - Ruff and formatting: pass; 105 files;
  - strict mypy native and Windows target: pass; 43 source modules;
  - pytest: 696 passed in 150.20 seconds; 85.92% branch coverage;
  - all 11 schemas current;
  - F006 conformance: 7 valid, 8 invalid, 1 record set, 6 identity vectors;
  - repository validation, source/wheel build and `git diff --check`: pass.
- Frozen dependency manifests (unchanged by F009; no MCP SDK or network library):
  - `pyproject.toml` SHA-256
    `739c224eb4dbc41155a986c76f30c9074646748c95f4b13dbade356d7fa70736`;
  - `uv.lock` SHA-256
    `1540dd72ac6b4d9873f9502deff4b2ebce2b9df40cd339799fe5272caed2f8dc`.
- Environment note: the first mypy probe failed because the optional `docling` extra
  was not yet installed in this fresh worktree; `uv sync --all-extras --locked`
  restored the locked baseline environment, after which every gate passed. No
  manifest changed.

### Frozen public artifact hashes

| Artifact | SHA-256 |
|---|---|
| `block.schema.json` | `413d725016a9f4f261e384efff3f82906a08c7e3b73a25bc8f96963a10861562` |
| `context-bundle.schema.json` | `e6cea129f58bd11ec52e1f63ef87258d8ec9c01ac37ff7fa933b08e96790a31a` |
| `context-bundle-0.2.0.schema.json` | `2a5c3c286456aae31fa558f8d43d7c9226b15affc6d96a6641d4666e886a3d9e` |
| `derivation.schema.json` | `56e8fc17050584b6d4bfc430d5f8d24de03237e5ef2b96fc7d9f6afd61f3e88a` |
| `evidence-projection.schema.json` | `cc580d589e46142a6c8429e0deb855c1bf3be79cf4334d9b39129e46c80aaf1e` |
| `evidence-reference.schema.json` | `b86968eca4d9a8c208c4a4f52f207dda863377dcc5bf353775b0067e2b4f4362` |
| `manifest.schema.json` | `1995cc1062e5322405a00adba8e47c7f3bed9fa294de6920dc27476c5a36dfd4` |
| `native-representation.schema.json` | `c4685f98633f2628240059e55703a0d8f27e32eb549cd7d453deb91b23d4d6ef` |
| `relation.schema.json` | `00b581b077089e6534f4cc0c3af511fa2caa8ede6b81649ee5094f0b60bca142` |
| `selection-receipt.schema.json` | `05c24f533da13b9705af4e6f25f0b96d5e41ee5d1d329756571a5c63a867d607` |
| `trust-classification.schema.json` | `7c4a7b429a3994ebd62af394b06cf7daaeeb691720778ef0122c1871fff302bc` |
| F002 identity vectors | `9387f64d8cf90f2039ca975c71d6f02d57cef8027005b69da6e07b4f8b6c291b` |
| F006 identity vectors | `da1c718da44c6e51f3ec2e7aafcd94de4b59dad8b3c02e442eb02527a8729e97` |
| F008 context vectors | `2e221ba1533ce53db389fffa37a25b633472ef49646e6f9f3be5c68ff752afad` |

The initial Spec Kit analysis covered 27 functional requirements, 12 success criteria,
four independently testable user stories and 74 planned tasks across two passes. The removed working analysis remains
recoverable from Git history; its final pass found no unresolved critical/high finding and complete requirement
coverage.

## Test-first and phase evidence

### Phase 1 — Baseline and contract freeze (T003, T004, T006)

- `tests/test_repository_contract.py::test_f008_contract_bytes_remain_frozen` hashes
  all eleven F008 schemas (nine F007 plus the additive `context-bundle-0.2.0` and
  `selection-receipt` roots), all three identity-vector files (F002, F006, F008
  context) and the complete F006 conformance tree against the frozen table above.
- `tests/test_repository_contract.py::test_f009_dependency_manifests_remain_frozen`
  pins the exact `pyproject.toml` and `uv.lock` bytes, proving no MCP SDK, async
  framework or network dependency enters the locked set.
- `tests/test_package.py` bounds the F009 module surface (`interfaces` gains exactly
  `mcp_protocol`), keeps `openardp.interfaces.mcp` forbidden and adds
  `test_no_mcp_or_network_dependency_is_introduced` scanning every declared runtime
  and extra requirement for MCP/async/network package fragments.
- Focused runs (red when `mcp_protocol` was absent, green after Phase 2):
  - red: `uv run pytest tests/unit/test_mcp_protocol.py tests/test_package.py
    tests/test_repository_contract.py -q --no-cov` → collection error
    (`ModuleNotFoundError: openardp.interfaces.mcp_protocol`) plus one red
    interface-surface assertion; freeze tests green;
  - green: `uv run pytest tests/unit/test_mcp_protocol.py tests/test_package.py
    tests/test_repository_contract.py tests/test_repository_validation.py -q
    --no-cov` → 122 passed.

### Phase 2 — Foundational protocol codec and error taxonomy (T007–T019)

Test-first file and coverage:

- `tests/unit/test_mcp_protocol.py` (64 tests): bounded newline framing (fragment
  stitching, exact cap, one byte over with and without terminator, EOF-mid-message
  leftover), single-object JSON-RPC envelopes (batch/scalar/malformed/truncated
  UTF-8 rejection, id shapes, params rule), canonical encoding (sorted compact
  single line plus raw-newline drift guard), pinned-revision lifecycle (handshake
  identity, tools-only capabilities, revision/missing-version rejection, pre-ready
  tool denial, out-of-order transitions, ping in every state), complete ten-category
  taxonomy with fixed messages, default JSON-RPC codes and service-family mapping,
  golden fixtures for descriptors and error envelopes, session-limit ranges,
  response-cap exact-fit/overflow, injected-clock deadline expiry and cooperative
  cancellation including the F008 `CancellationCheck` bridge.
- `src/openardp/interfaces/mcp_protocol.py`: pure stdlib codec, zero I/O, 100%
  branch coverage from the unit suite alone; imports only existing domain/ports/
  workspace error types for the mapping.
- `tests/fixtures/mcp/tools-list.json` and `error-envelopes.json`: canonical golden
  bytes, regenerated deterministically and pinned by byte-equality tests.
- `scripts/validate_repository.py` gains `GOV010`: every MCP golden fixture must be
  valid UTF-8 JSON and byte-identical to its canonical deterministic serialization.
- Gates after Phase 2 (2026-07-27, macOS arm64):
  - `uv run --locked ruff check .` → all checks passed (107 files);
  - `uv run --locked ruff format --check .` → 107 files already formatted;
  - `uv run --locked mypy src` and `--platform win32` → success, 44 source modules;
  - `uv run --locked pytest tests/ -q --no-cov` → 763 passed;
  - `uv run --locked pytest` (full gate) → 763 passed in 54.86s, 86.36% branch
    coverage;
  - schema check (11 current), F006 conformance, repository validation (incl.
    GOV010), `uv build` and `git diff --check` → pass.

### Phase 3 — US1 session loop and navigation tools (T020–T032)

Test-first files and coverage:

- `tests/integration/test_mcp_server.py` (37 tests): handshake identity and
  tools-only capabilities, pre-initialization rejection, second-initialize and
  unknown-method stability, framing-failure recovery, clean EOF shutdown,
  `tools/list` contract surface, bounded body-free `list_documents` with explicit
  truncation at the documented cap, identifier-only `get_source_status` with
  uniform body-free unknown-identifier result, bounded outline items with
  documented label truncation, enveloped verified `get_block` with fail-closed
  body cap, body-free `list_evidence`, enveloped verified `get_evidence`
  (optional document scope, unknown-projection not-found, ambiguity→conflict),
  20 repeated navigation sessions byte-identical modulo documented volatile
  fields, body-free audit records (digests, codes, timings only), sanitized
  internal mapping for unexpected handler failures, fail-closed pending
  Phase-4 tools, closed-schema validation helpers (string/integer/boolean/array
  bounds, enums, patterns, malformed published schemas, identifier helpers),
  cooperative cancellation notifications (bool/list/unknown ids discarded, flag
  consumed with the finished request), unknown and mistimed notification
  discard, oversize-frame recovery in the `serve` loop and the default
  body-free audit log sink.
- `tests/security/test_mcp_boundaries.py` (7 tests): path-bearing, traversal,
  URL and control-character parameters rejected with zero filesystem access
  proof, error envelopes echo-free.
- `tests/test_package.py`: `INTERFACE_MODULES` extended with `mcp_server`.
- `src/openardp/interfaces/mcp_server.py`: stdlib-only `McpServer` composing
  `DocumentQueryService` + `RichEvidenceService` with injectable
  `SessionLimits`/`ServerCaps`/clock/audit; dispatch for the six US1 tools;
  closed argument validation against the published descriptor schemas
  (identifier shapes only, never paths); untrusted-data envelopes that fail
  closed above caps and never truncate; body-free structured audit records
  (tool, `sha256:` request-id digest, outcome, duration_ms); deadline and
  cooperative cancellation checks around every handler; the three Phase-4
  tools fail closed with the internal category (pinned by test).
- Coverage: `mcp_server.py` 100% statements and branches from the focused
  suites; red→green: helper/notification/serve-recovery coverage gaps closed by
  13 added tests (31 → 44 focused tests).
- Gates after Phase 3 (2026-07-27, macOS arm64):
  - `uv run --locked pytest tests/integration/test_mcp_server.py
    tests/security/test_mcp_boundaries.py --no-cov` → 44 passed;
  - `uv run --locked pytest tests/ -q --no-cov` → 807 passed;
  - `uv run --locked pytest` (full gate) → 807 passed, 86.89% branch coverage
    (required 85%);
  - `uv run --locked ruff check .` → all checks passed (110 files);
  - `uv run --locked ruff format --check .` → 110 files already formatted;
  - `uv run --locked mypy src` and `--platform win32` → success, 45 source
    modules;
  - schema check (11 current), F006 conformance, repository validation (incl.
    GOV010), `uv build` and `git diff --check` → pass.

### Phase 4 — US2 search, compile and verified receipt (T033–T044)

- Added verified `search_document` parity with `SearchService`, bounded filters,
  enveloped snippets, explicit truncation and no query echo; unknown scopes and
  invalid filters reduce to the documented body-free taxonomy.
- Added the exact F008 `compile_and_persist` composition with all three installed
  estimators, bounded modes/scopes, handle-first summaries, ledger/count/notice
  projections, optional full bundle and complete-response cap enforcement.
- Added `get_context_receipt` through `ContextCompilerService.load_verified`; CAS,
  canonical-model, identity, scope and catalog verification therefore remain in the
  existing F008 application service rather than the transport.
- Deadline and cooperative cancellation flags are threaded to the F008 cancellation
  port; the mid-discovery cancellation test proves zero catalog-visible partial state
  and a clean deterministic retry.
- The opt-in bundle cap check handles both embedded-content and legitimate
  handle-only evidence items; embedded text/JSON bodies fail closed above the single
  body cap and are never truncated.
- Evidence on 2026-07-31 (macOS arm64):
  - `uv run --locked ruff check .` → all checks passed;
  - `uv run --locked ruff format --check .` → 110 files already formatted;
  - `uv run --locked mypy src` and `--platform win32` → success, 45 source modules;
  - focused US2/injection selection → 17 passed;
  - complete protocol/server/security MCP selection → 126 passed;
  - no network access, provider invocation or client-supplied path resolution occurs.

### Phase 5 — US3 hostile boundary and failure safety (T045–T055)

- Added a single-session hostile matrix for malformed JSON, batch arrays, wrong
  protocol revision, unknown method/tool and oversize messages, followed by a valid
  request to prove session recovery.
- Unknown and near-miss identifiers now have fixture-independent evidence for one
  identical error shape, category and deterministic audit-duration projection; audit
  records contain only the fixed tool, request-id digest, outcome and integer timing.
- Injected FTS drift and CAS corruption reduce to `integrity_or_workspace`; private
  paths, bodies and exception strings never enter protocol errors or audit records.
- Every published tool family has an executable cap assertion: list, outline and
  evidence pagination; one-body rejection; search limit; compile scope limit; bundle
  body limit and complete serialized response cap.
- Deadline expiry observed while the compiler unwinds is distinguished from explicit
  caller cancellation as `deadline_exceeded`; cancellation remains `cancelled`.
  A valid earlier compilation remains byte-verifiable and catalog-identical after a
  cancelled follow-up.
- Evidence on 2026-07-31 (macOS arm64):
  - complete protocol/server/security selection → 133 passed;
  - Ruff and format → pass, 110 files;
  - strict mypy native and Windows target → pass, 45 source modules;
  - hostile privacy assertions found zero task/query/body/path/traceback leakage and
    all cancellation/deadline probes left zero partial compilation.

### Phase 6 — US4 CLI launch and operations (T056–T062)

- Added `openardp mcp --store PATH [--deadline-ms 1000..120000]
  [--response-cap-bytes 65536..4194304]`; it owns stdio exclusively and therefore
  does not accept the ordinary CLI `--json` output switch.
- Startup calls only `LocalWorkspace.open`, validates current revision 6 and composes
  query/search/rich-evidence/context-compiler services; it never invokes initialize,
  migration, reindex, ingestion or provider conversion.
- Actual missing, malformed-marker, corrupt-SQLite, too-new and exclusively locked
  workspaces fail through the existing `integrity_or_workspace` classification.
  Exact file-byte snapshots before/after prove zero startup repair or mutation.
- The real initialize/ready/tools-list/EOF transcript matches the canonical
  `tests/fixtures/mcp/tools-list.json` object exactly and exits with code 0.
- Evidence on 2026-07-31 (macOS arm64):
  - MCP CLI launch/startup suite → 8 passed;
  - prior base CLI → 5 passed; rich CLI → 3 passed; context CLI → 10 passed;
  - package/repository/repository-validator compatibility selection → 60 passed;
  - native strict mypy and focused Ruff/format → pass.

### Phase 7 — compatibility, packaging and convergence (T063–T075)

- Public guidance now describes only the delivered stdio boundary: protocol revision
  `2025-06-18`, the nine fixed tools, identifier-only access, untrusted body envelopes,
  startup behavior and every launch/runtime bound. The removed visual-evidence and
  HTTP sketches remain future work rather than accidental F009 claims.
- Direct comparison with base `5a73d3a2e2bb524a2b190e3bec9178e6c249ad93`
  found no byte change in any of the eleven public schema files, all three identity
  vector files or any file in the F006 conformance corpus. The dependency-manifest
  hashes also remain the frozen values above.
- Two independent `tools_list_result()` generations matched the committed
  `tools-list.json` fixture exactly: 5,520 bytes, SHA-256
  `770c959ebc5db69b8ff6d1dc8214c0417f21daa3853aeff565f2822a42d29d7e`.
  `error-envelopes.json` hashes to
  `7ebcfc4e348f8c3d6f247491673a3724d383ceec12a859d05e87e0df2f57a76d`.
- Final review found and closed one high-impact runtime gap before convergence: a
  purely synchronous stdio loop could not read a cancellation notification while
  compilation was executing. The final server uses one stdlib reader thread solely
  to frame input, register queued request IDs and consume cancellation notifications;
  application dispatch remains sequential. The registry is lock-protected, ignores
  unknown/completed IDs and cancels only active or already queued requests.
- The pending non-cancellation queue is capped at 64 frames. Overflow cancels active
  work and closes the session with a fixed sanitized protocol error instead of
  accumulating unbounded memory. A staged blocking-stream test proves real mid-flight
  cancellation; a saturation test proves bounded fail-closed unwind.
- The final focused codec/server/security/CLI matrix passed 144 tests, including the
  fresh initialize/ready/discovery/EOF transcript, 20-repeat byte determinism, every
  hostile/corruption/privacy cap, actual mid-flight cancellation, deadline distinction,
  startup non-mutation and pending-frame overflow.

#### Final local gate

Observed on macOS arm64 with CPython 3.12.13 and the unchanged locked environment:

| Command/evidence | Result |
|---|---|
| `uv run --locked ruff check .` | pass |
| `uv run --locked ruff format --check .` | pass; 111 files |
| `uv run --locked mypy src` | pass; 45 source modules |
| `uv run --locked mypy src --platform win32` | pass; 45 source modules |
| `uv run --locked pytest` | 843 passed; 87.10% total coverage (gate: 85% branch) |
| `uv run --locked python scripts/generate_schemas.py --check` | all 11 schemas current |
| `uv run --locked python scripts/validate_evidence_contracts.py conformance/evidence/v0.1.0/manifest.json` | 7 valid, 8 invalid, 1 record set, 6 identity vectors |
| `uv run --locked python scripts/validate_repository.py` | pass, including MCP fixture governance |
| `git diff --check` | pass |
| `uv build` | sdist and wheel built |
| `uv run --locked pre-commit run --all-files` | all hooks pass, including the complete offline suite |

The final isolated core-wheel environment installed exactly seven packages, imported
both MCP modules without Docling, exposed all nine descriptors and executed
initialize, discovery and `list_documents` against a fresh revision-6 workspace. No
MCP, async or network package entered the distribution requirements. The observed
final build hashes were sdist
`89c9cfd5d7cf1435dc603fff741f62447eb89ebb81c07ba1b80c7721f7a5ad79`
and wheel
`ba6196e26dc249bec3ca8436629eaf49bcb88936984843afcc7fc3a03ca132c9`;
these are evidence for this build, not a cross-build reproducibility claim.

#### Tradeoffs and residual risks

- A small pinned protocol subset avoids an SDK/network dependency and keeps the core
  inspectable, but clients requiring another MCP revision or capabilities beyond tools
  must wait for a separately reviewed interface release.
- Dispatch is intentionally sequential for deterministic local single-user behavior;
  only framing and cancellation observation are concurrent. A slow underlying service
  can occupy the one dispatch slot until its bounded checkpoint/deadline fires.
- Cooperative cancellation cannot interrupt arbitrary blocking third-party/native code;
  F009 never invokes the rich parser, and the F008 compiler checkpoints bound the paths
  used here. Strong process-level preemption remains outside this interface feature.
- stdio access inherits the permissions of the launching local process. F009 is not a
  multi-tenant authorization boundary and must only be configured in a trusted client.

#### Rollback

Revert the isolated F009 implementation/merge commit. No dependency, public schema,
identity algorithm or workspace migration changed. Existing revision-6 workspaces and
all F001–F008 CLI/application behavior remain usable; additive MCP fixtures and modules
can be removed without data conversion. Immutable context results created through the
MCP compiler are ordinary valid F008 artifacts and do not require cleanup for rollback.

#### Remote evidence

Final Spec Kit analysis identified the real mid-flight cancellation, pending-frame
memory-bound and unknown-ID lifecycle gaps as two high and one medium finding. Their
originating spec/research/plan/data-model/contract artifacts were corrected, task T075
was appended and implemented, and the repeated convergence matrix passed. The final
mapping covers all 27 functional requirements, 12 success criteria, four user stories
and 75 completed tasks with zero unresolved critical/high findings and no further task
to append.

- Pull request [#12](https://github.com/Noetheon/OpenARDP/pull/12) reviewed the exact
  feature head `f02fa9a07f04d622f1ac6d790fc6620edf4eb7a5`.
- PR-head workflow
  [30649553804](https://github.com/Noetheon/OpenARDP/actions/runs/30649553804)
  passed Ubuntu (3m46s), macOS (3m02s) and Windows (6m07s).
- The PR squash-merged to `main` as
  [`ca0a20d40b8f28d986e7af77e2c0ceefcee24997`](https://github.com/Noetheon/OpenARDP/commit/ca0a20d40b8f28d986e7af77e2c0ceefcee24997).
- Post-merge `main` workflow
  [30650000034](https://github.com/Noetheon/OpenARDP/actions/runs/30650000034)
  passed Ubuntu (3m57s), macOS (2m54s) and Windows (10m07s). Every platform ran the
  locked sync, pre-commit validation, lint, formatting, strict mypy, all 843 offline
  tests, distribution build and tracked-file drift check.

### Known environment note

The host `uv` binary warns that `[tool.uv] preview-features` is unknown during
settings discovery; the warning predates F009, appears in every `uv run` invocation
and does not affect any locked gate result. No manifest changed.
