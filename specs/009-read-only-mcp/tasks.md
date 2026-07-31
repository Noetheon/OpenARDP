# Tasks: Read-only MCP

**Input**: Design documents from `/specs/009-read-only-mcp/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/mcp-read-only-tools.md`, `contracts/mcp-error-envelope.md`,
`quickstart.md`

**Tests**: Mandatory and authored before behavior/contract implementation where
practical. Unit tests run without network; the MCP suites additionally assert zero
socket creation.

**Organization**: Dependency-ordered and grouped by independently testable user
story. F009 ends at a read-only stdio MCP server with one additive CLI verb and does
not implement write tools, HTTP transport, visual extraction, watcher, retention or
export behavior.

## Phase 1: Baseline and Contract Freeze

**Purpose**: Freeze F008 compatibility and make the additive interface boundary
explicit.

- [x] T001 Record base commit, Python/source/test counts and all eleven schema/vector/conformance hashes in `specs/009-read-only-mcp/implementation-notes.md`
- [x] T002 Run and record the locked F008 Ruff, format, native/Windows mypy, full pytest, schema, conformance, repository and build baseline in `specs/009-read-only-mcp/implementation-notes.md`
- [x] T003 [P] Add failing package/surface tests bounding F009 to `interfaces/mcp_protocol.py` and `interfaces/mcp_server.py` and proving unchanged locked dependencies in `tests/test_package.py`
- [x] T004 [P] Add failing byte-freeze tests for all eleven F008 schemas, all three vector files and the F006 conformance corpus in `tests/test_repository_contract.py`
- [x] T005 Confirm the additive application contract requires no ADR and record compatibility/source-of-truth reasoning in `specs/009-read-only-mcp/research.md`
- [x] T006 Run the Phase 1 focused red/green contract-freeze tests and record exact evidence in `specs/009-read-only-mcp/implementation-notes.md`

**Checkpoint**: F008 behavior/artifacts are frozen; only interface-layer modules,
one CLI verb and application-contract fixtures may be added.

---

## Phase 2: Foundational Protocol Codec and Error Taxonomy

**Purpose**: Define the pure, fully testable framing, lifecycle and error boundary
before any service wiring.

### Tests first

- [x] T007 [P] Add failing newline-framing reader tests (exact cap, one byte over, embedded newline, invalid UTF-8, EOF mid-message) in `tests/unit/test_mcp_protocol.py`
- [x] T008 [P] Add failing JSON-RPC envelope tests (non-object, batch array, id shapes, unknown method, unknown notification) in `tests/unit/test_mcp_protocol.py`
- [x] T009 [P] Add failing lifecycle state-machine tests (initialize once, pinned revision, pre-init tool calls, ping in every state) in `tests/unit/test_mcp_protocol.py`
- [x] T010 [P] Add failing error-taxonomy mapping and fixed-message/body-free tests for every category in `tests/unit/test_mcp_protocol.py`
- [x] T011 [P] Add failing tool-descriptor shape, fixed-order and deterministic canonical `tools/list` golden tests under `tests/fixtures/mcp/`
- [x] T012 [P] Add failing deadline/cancellation flag unit tests (monotonic deadline, checkpoint observation, unknown-request cancellation no-op) in `tests/unit/test_mcp_protocol.py`

### Implementation

- [x] T013 Implement the bounded newline-framing reader/writer and single-object validation in `src/openardp/interfaces/mcp_protocol.py`
- [x] T014 Implement the pinned-revision lifecycle state machine and capability negotiation in `src/openardp/interfaces/mcp_protocol.py`
- [x] T015 Implement the versioned error taxonomy (`mcp_error_version: 1`) with fixed messages and CLI-aligned service-exception mapping in `src/openardp/interfaces/mcp_protocol.py`
- [x] T016 Implement tool descriptors, session limits and the deterministic canonical `tools/list` projection in `src/openardp/interfaces/mcp_protocol.py`
- [x] T017 Implement the monotonic deadline tracker and cooperative cancellation flag bridge to the F008 `CancellationCheck` port in `src/openardp/interfaces/mcp_protocol.py`
- [x] T018 Commit descriptor/transcript goldens under `tests/fixtures/mcp/` and wire fixture validation into the repository validator in `scripts/validate_repository.py`
- [x] T019 Run all foundational codec tests plus Ruff, format and strict mypy and record results in `specs/009-read-only-mcp/implementation-notes.md`

**Checkpoint**: The protocol boundary is pure, bounded, versioned and fully tested
without touching any service or stream.

---

## Phase 3: User Story 1 — Safe Session and Navigation Tools (Priority: P1) 🎯 MVP

**Goal**: Serve the pinned lifecycle and the six navigation tools through existing
services with identifier-only inputs, envelopes and caps.

**Independent Test**: Drive a scripted stdio session over a mixed workspace;
initialize, list, check status, read outline, block and rich evidence; prove verified
bounded output, untrusted envelopes and zero path/network reach.

### Tests first

- [x] T020 [P] [US1] Add failing session-loop tests (handshake, EOF shutdown, pre-init rejection, second initialize) in `tests/integration/test_mcp_server.py`
- [x] T021 [P] [US1] Add failing `list_documents`/`get_source_status` cap, shape and identifier-only tests in `tests/integration/test_mcp_server.py`
- [x] T022 [P] [US1] Add failing `get_document_outline`/`get_block` envelope, label-truncation and body-cap tests in `tests/integration/test_mcp_server.py`
- [x] T023 [P] [US1] Add failing `list_evidence`/`get_evidence` verification, envelope and ambiguity tests in `tests/integration/test_mcp_server.py`
- [x] T024 [P] [US1] Add failing path-bearing, traversal, URL and control-character parameter rejection tests with zero-filesystem-access proof in `tests/security/test_mcp_boundaries.py`
- [x] T025 [P] [US1] Add failing determinism tests (20 identical navigation sequences byte-identical modulo volatile fields) in `tests/integration/test_mcp_server.py`

### Implementation

- [x] T026 [US1] Implement the stdio session loop, dispatch table and clean EOF/error shutdown in `src/openardp/interfaces/mcp_server.py`
- [x] T027 [US1] Wire `list_documents` and identifier-only `get_source_status` through `DocumentQueryService` in `src/openardp/interfaces/mcp_server.py`
- [x] T028 [US1] Wire `get_document_outline` and enveloped `get_block` with per-tool caps in `src/openardp/interfaces/mcp_server.py`
- [x] T029 [US1] Wire `list_evidence` and enveloped verified `get_evidence` through `RichEvidenceService` in `src/openardp/interfaces/mcp_server.py`
- [x] T030 [US1] Implement identifier-only parameter validation and untrusted-envelope projection helpers in `src/openardp/interfaces/mcp_server.py`
- [x] T031 [US1] Implement body-free structured audit logging (tool, request-id digest, outcome, duration) in `src/openardp/interfaces/mcp_server.py`
- [x] T032 [US1] Run the User Story 1 suite, determinism repeats and socket-creation assertions and record exact evidence in `specs/009-read-only-mcp/implementation-notes.md`

**Checkpoint**: A safe pinned session navigates verified evidence with no path
resolution, no network and stable bounded output.

---

## Phase 4: User Story 2 — Search, Compile and Verified Receipt (Priority: P2)

**Goal**: Expose verified search and the exact F008 compile/receipt path with
handle-first responses and deadline/cancellation threading.

**Independent Test**: Search with filters, compile across two documents under a small
budget with and without `include_bundle`, load the receipt, and compare every result
field with equivalent CLI output.

### Tests first

- [x] T033 [P] [US2] Add failing `search_document` filter/limit/envelope/no-query-echo tests matching CLI parity in `tests/integration/test_mcp_server.py`
- [x] T034 [P] [US2] Add failing `compile_context` handle-first, counts/accounting/notices and persistence tests in `tests/integration/test_mcp_server.py`
- [x] T035 [P] [US2] Add failing bounded `include_bundle`, response-cap and stable limit-category tests in `tests/integration/test_mcp_server.py`
- [x] T036 [P] [US2] Add failing `get_context_receipt` full-verification and tamper/rejection tests in `tests/integration/test_mcp_server.py`
- [x] T037 [P] [US2] Add failing injection-shaped query/task data-only handling tests in `tests/security/test_mcp_boundaries.py`
- [x] T038 [P] [US2] Add failing deadline-threading and mid-compile cancellation tests (no catalog-visible partial result) in `tests/integration/test_mcp_server.py`

### Implementation

- [x] T039 [US2] Wire `search_document` through `SearchService` with bounded filters, enveloped snippets and no query echo in `src/openardp/interfaces/mcp_server.py`
- [x] T040 [US2] Wire `compile_context` to the exact F008 compile-and-persist path with estimator/mode mapping in `src/openardp/interfaces/mcp_server.py`
- [x] T041 [US2] Implement handle-first projection, bounded `include_bundle` and response-cap accounting in `src/openardp/interfaces/mcp_server.py`
- [x] T042 [US2] Wire `get_context_receipt` through the complete F008 verification load in `src/openardp/interfaces/mcp_server.py`
- [x] T043 [US2] Thread per-request deadline and `notifications/cancelled` into the compiler cancellation port in `src/openardp/interfaces/mcp_server.py`
- [x] T044 [US2] Run the User Story 2 suite, CLI-parity comparison and compile determinism repeats and record exact evidence in `specs/009-read-only-mcp/implementation-notes.md`

**Checkpoint**: Search and compile behave exactly like the verified CLI paths, with
bounded handle-first output and no partial compilations.

---

## Phase 5: User Story 3 — Boundary Defense and Failure Safety (Priority: P3)

**Goal**: Guarantee uniform sanitized outcomes for the complete hostile matrix with
zero leakage and zero partial writes.

**Independent Test**: Inject framing, version, tool, identifier, corruption,
cancellation and deadline faults at every phase; verify documented categories, body
freedom and prior-result immutability.

### Tests first

- [x] T045 [P] [US3] Add failing malformed/oversize/batch/unknown-method/unknown-tool taxonomy tests in `tests/security/test_mcp_boundaries.py`
- [x] T046 [P] [US3] Add failing uniform not-found and ID-enumeration shape/timing tests in `tests/security/test_mcp_boundaries.py`
- [x] T047 [P] [US3] Add failing catalog/CAS/index corruption and drift fail-closed tests in `tests/security/test_mcp_boundaries.py`
- [x] T048 [P] [US3] Add failing cancellation/deadline at every compile phase plus prior-compilation immutability tests in `tests/integration/test_mcp_server.py`
- [x] T049 [P] [US3] Add failing privacy scans proving query/task/body/path absence from errors, logs and audit records in `tests/security/test_mcp_boundaries.py`
- [x] T050 [P] [US3] Add failing resource-limit tests for every per-tool cap and the response cap in `tests/security/test_mcp_boundaries.py`

### Implementation

- [x] T051 [US3] Harden uniform not-found and sanitized mapping across every tool failure path in `src/openardp/interfaces/mcp_server.py`
- [x] T052 [US3] Enforce per-tool caps and response-cap accounting before unbounded serialization in `src/openardp/interfaces/mcp_server.py`
- [x] T053 [US3] Harden session resilience after framing errors and fail-closed mid-session workspace faults in `src/openardp/interfaces/mcp_server.py`
- [x] T054 [US3] Complete audit/error redaction guarantees and diagnostic defaults in `src/openardp/interfaces/mcp_server.py` and `src/openardp/interfaces/mcp_protocol.py`
- [x] T055 [US3] Run the complete User Story 3 hostile matrix and record exact zero-partial/leakage evidence in `specs/009-read-only-mcp/implementation-notes.md`

**Checkpoint**: Every hostile input and injected fault yields one documented category
with zero filesystem reach, zero leakage and zero partial writes.

---

## Phase 6: User Story 4 — CLI Launch and Operations (Priority: P4)

**Goal**: Compose and launch the server through one additive CLI verb while
preserving every existing CLI behavior.

**Independent Test**: Start `openardp mcp` against fresh, missing, incompatible and
corrupted workspaces; run `tools/list` against the published contract; prove all
prior CLI snapshots unchanged.

### Tests first

- [x] T056 [P] [US4] Add failing `mcp` verb parser, composition and help tests in `tests/integration/test_cli_mcp.py`
- [x] T057 [P] [US4] Add failing startup fail-closed tests (missing/incompatible/too-new/locked/corrupted workspace, no startup mutation) in `tests/integration/test_cli_mcp.py`
- [x] T058 [P] [US4] Add failing descriptor/contract parity tests against `contracts/mcp-read-only-tools.md` goldens in `tests/integration/test_cli_mcp.py`
- [x] T059 [P] [US4] Add regression assertions for all existing CLI JSON/human outputs and exit classifications in `tests/integration/test_cli_mcp.py`

### Implementation

- [x] T060 [US4] Add the `mcp` verb, store/deadline/response-cap options and service composition in `src/openardp/interfaces/cli.py`
- [x] T061 [US4] Map startup workspace failures into the existing sanitized classification without migration or repair in `src/openardp/interfaces/cli.py`
- [x] T062 [US4] Run User Story 4 and full prior CLI compatibility suites and record exact evidence in `specs/009-read-only-mcp/implementation-notes.md`

**Checkpoint**: The server launches and fails closed through the stable CLI boundary;
every pre-existing command behaves byte-identically.

---

## Phase 7: Documentation, Compatibility and Convergence

**Purpose**: Prove the complete feature, contract fixtures, packaging and prior
behavior before publication.

- [x] T063 Update install, client-configuration, tool-reference, security-boundary and limit guidance in `README.md`, `START_HERE.md` and `docs/13_STEP_BY_STEP_USER_GUIDE.md`
- [x] T064 [P] Align delivered MCP behavior in `docs/05_CONTEXT_COMPILER_AND_MCP.md` (remove the not-delivered visual tool and HTTP sketch) and update `docs/02_ARCHITECTURE.md`, `docs/06_SECURITY_MODEL_V2.md` and `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md`
- [x] T065 [P] Update contract status, schema matrix, changelog and validation history in `contracts/README.md`, `schemas/README.md`, `CHANGELOG.md` and `VALIDATION.md`
- [x] T066 Prove byte-for-byte no-diff against F008 for all eleven public schemas, all three vector files and the F006 conformance corpus
- [x] T067 Run two consecutive `tools/list` fixture generations and prove deterministic descriptor bytes
- [x] T068 Run Ruff, format, native/Windows strict mypy, full network-blocked suite, schema/conformance/repository validators, `git diff --check` and distribution builds
- [x] T069 Run the fresh quickstart transcript, 20-repeat determinism probe, hostile matrix, cancellation/deadline flows and startup-failure flows
- [x] T070 Verify isolated wheels expose the MCP interface without new dependencies and execute representative server paths
- [x] T071 Finalize `specs/009-read-only-mcp/implementation-notes.md` with exact commands, counts, hashes, tradeoffs, residual risks, rollback and remote placeholders
- [x] T072 Run final Spec Kit analysis and resolve every critical/high finding at its originating artifact
- [x] T073 Run Spec Kit convergence; append and implement any remaining tasks without rewriting completed tasks
- [x] T074 Mark F009 converged in `specs/009-read-only-mcp/spec.md` and `specs/README.md` only after all checks pass
- [x] T075 [US3] Close the final cancellation-routing gap with a thread-safe active-request registry, concurrent stdio cancellation reader and a real mid-flight stream test in `src/openardp/interfaces/mcp_protocol.py`, `src/openardp/interfaces/mcp_server.py`, `tests/unit/test_mcp_protocol.py` and `tests/integration/test_mcp_server.py`

---

## Dependencies & Execution Order

### Phase dependencies

- Baseline/contract freeze precedes every new interface artifact.
- The pure protocol codec blocks every user story.
- US1 provides the safe session and navigation and is independently valuable.
- US2 depends on US1 session/dispatch and adds search/compile/receipt.
- US3 hardens US1/US2 failure paths.
- US4 wraps the complete server in the CLI and preserves prior behavior.
- Phase 7 closes public contract, compatibility and convergence evidence.

### Within each story

- Tests are written and observed failing before corresponding implementation where
  practical.
- Pure codec precedes session loop; session loop precedes tool wiring; tool wiring
  precedes hardening; hardening precedes CLI launch.
- Shared files (`mcp_server.py`, `cli.py`) are edited sequentially even where test
  files differ.

### Parallel opportunities

- Framing, lifecycle, taxonomy and descriptor tests are separate test files.
- Navigation, search/compile and boundary test files can be authored independently
  before implementation.
- Documentation tasks on disjoint files can run in parallel after behavior freezes.

## Implementation Strategy

### MVP first

1. Freeze F008.
2. Complete the pure protocol codec and taxonomy.
3. Complete US1 safe session and navigation.
4. Validate independently before search/compile wiring.

### Incremental completion

1. Add search, compile and verified receipt.
2. Harden every hostile and lifecycle fault path.
3. Add the CLI verb and startup safety.
4. Prove compatibility, packaging and convergence.

### Rollback

Revert the isolated F009 implementation/merge commit. F009 adds no workspace
migration and no persisted contract, so existing workspaces at revision 6 remain
fully usable by F008 software after rollback; MCP transcript fixtures are additive
test data and require no data rollback.
