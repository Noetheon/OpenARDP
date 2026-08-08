# Tasks: Semantic Retrieval Product Surface

## Phase 1: Setup and frozen contracts

- [x] T001 Freeze F030 feature map, prompt, specification, clarification, plan and design artifacts in `spec-kit/FEATURE_MAP.md`, `spec-kit/feature-prompts/030-semantic-retrieval-product-surface.md` and `specs/030-semantic-retrieval-product-surface/`
- [x] T002 Freeze CLI/MCP profile and benchmark result-shape contracts in `specs/030-semantic-retrieval-product-surface/contracts/README.md`
- [x] T003 Add F030 to feature/spec indexes and status governance in `specs/README.md` and `.specify/feature.json`

## Phase 2: Foundational profile resolution

- [x] T004 Add model-free retrieval-profile resolution and invalid-combination tests in `tests/unit/test_semantic_product_surface.py`
- [x] T005 Implement interface-local lexical/semantic compiler resolution without changing F029 domain/port contracts in `src/openardp/interfaces/context_composition.py`
- [x] T006 Add exact semantic algorithm classification and replay-drift tests in `tests/unit/test_semantic_product_surface.py`

## Phase 3: US1 — Explicit CLI semantic context

**Goal**: A local operator can opt into the exact F029 profile while lexical behavior remains the default.

**Independent test**: Default lexical output remains unchanged; explicit semantic compile uses a fake provider and exact semantic algorithm identity.

- [x] T007 [US1] Add CLI grammar, all-or-none configuration and sanitized-failure tests in `tests/integration/test_cli_semantic_context.py`
- [x] T008 [US1] Add fake-provider semantic compile and lexical non-regression tests in `tests/integration/test_cli_semantic_context.py`
- [x] T009 [US1] Implement additive context and MCP startup arguments in `src/openardp/interfaces/cli.py`
- [x] T010 [US1] Implement CLI provider construction, semantic compilation and guaranteed close in `src/openardp/interfaces/cli.py`
- [x] T011 [US1] Update CLI help and stable output/error contract tests in `tests/integration/test_cli_context.py` and `tests/integration/test_cli_semantic_context.py`

## Phase 4: US2 — Process-authorized MCP semantic context

**Goal**: A local MCP server may expose semantic selection without granting path/configuration authority to clients.

**Independent test**: Provider-free semantic calls fail closed; configured semantic and lexical calls coexist in one session and reuse one provider lifecycle.

- [x] T012 [US2] Add MCP 0.2.0 descriptor and canonical fixture tests for the optional path-free profile input in `tests/unit/test_mcp_protocol.py` and `tests/fixtures/mcp/tools-list.json`
- [x] T013 [US2] Add configured/unconfigured selection, lifecycle, cache-reuse, cancellation and sanitized-error tests in `tests/integration/test_mcp_semantic_context.py`
- [x] T014 [US2] Change the compiler factory to accept a bounded retrieval profile in `src/openardp/interfaces/mcp_server.py`
- [x] T015 [US2] Implement MCP per-request selection with lexical default and no fallback in `src/openardp/interfaces/mcp_server.py`
- [x] T016 [US2] Implement process-start semantic capability ownership and guaranteed shutdown in `src/openardp/interfaces/cli.py`
- [x] T017 [US2] Bump and document the additive experimental MCP interface contract in `src/openardp/interfaces/mcp_protocol.py`, `docs/05_CONTEXT_COMPILER_AND_MCP.md` and `tests/fixtures/mcp/tools-list.json`

## Phase 5: US3 — Exact semantic replay

**Goal**: Semantic replay succeeds only with an exact configured provider recipe and matching profile.

**Independent test**: Matching replay reproduces the original; absent, lexical-selected and drifted providers fail before returning evidence.

- [x] T018 [US3] Add semantic replay success, inference, explicit mismatch and recipe-drift tests in `tests/integration/test_cli_semantic_context.py`
- [x] T019 [US3] Implement verified receipt-first profile inference and exact provider-bound replay in `src/openardp/interfaces/context_cli.py` and `src/openardp/interfaces/context_composition.py`
- [x] T020 [US3] Add privacy/security tests for path, task, evidence and raw-provider-error non-disclosure in `tests/security/test_semantic_product_surface_boundaries.py`

## Phase 6: US4 — Operational cost evidence

**Goal**: Maintainers can reproduce and independently validate honest cold/warm cost evidence.

**Independent test**: A stdlib-only validator recomputes two-run identities, summaries, gates and privacy rules and rejects tampering.

- [x] T021 [US4] Freeze the canonical operational protocol in `benchmarks/semantic-surface/v0.1.0/protocol.json`
- [x] T022 [US4] Add producer/validator contract and tamper tests in `tests/unit/test_semantic_surface_benchmark.py`
- [x] T023 [US4] Implement atomic body-free measurement production in `scripts/run_semantic_surface_benchmark.py`
- [x] T024 [US4] Implement independent stdlib-only validation in `scripts/validate_semantic_surface_benchmark.py`
- [x] T025 [US4] Run two fresh exact-bundle measurements and commit all validated reference evidence in `benchmarks/semantic-surface/v0.1.0/results/reference-macos-arm64/`

## Phase 7: Polish, compatibility and convergence

- [x] T026 Update README, changelog, product guide, F029/F030 docs and implementation notes, then verify the unchanged maintainability policy in `README.md`, `CHANGELOG.md`, `docs/`, `quality/` and `specs/030-semantic-retrieval-product-surface/implementation-notes.md`
- [x] T027 Run focused CLI/MCP/replay/security/benchmark tests and all F029 validators from `specs/030-semantic-retrieval-product-surface/quickstart.md`
- [x] T028 Run Ruff, format, strict mypy, full pytest/coverage, repository validators, pre-commit, build and release-evidence drift gates from repository root
- [x] T029 Complete `speckit-converge` with zero critical/high findings and mark F030 converged in `specs/030-semantic-retrieval-product-surface/spec.md` and `specs/README.md`

## Dependencies

- Phase 2 blocks every product surface.
- US1 establishes CLI capability ownership before US3 replay.
- US2 is independently testable after Phase 2 and shares only the resolver/provider lifecycle.
- US4 depends on US1 behavior and the unchanged F029 provider profile, not on MCP.
- Convergence follows all user stories and complete reference evidence.

## Implementation Strategy

Implement model-free tests first, preserve lexical compatibility at every checkpoint, then add the optional real-model
measurement only after CLI/MCP contracts are stable. No task authorizes a new retrieval policy, persisted vector or
answer-generation path.

## Phase 8: Convergence

- [x] T030 Add direct modified-protocol and privacy-forbidden-value rejection tests for the independent F030 validator in `tests/unit/test_semantic_surface_benchmark.py` per SC-006 (partial)
