# Tasks: Domain Models and Interchange Schemas

**Input**: Design documents from `specs/002-domain-models-schemas/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/domain-contracts.md`, `quickstart.md`

**Tests**: Required for every public contract, security boundary and persisted identity behavior. Test tasks precede their corresponding implementation tasks.

**Organization**: Tasks are grouped by user story; shared strict-value and identity primitives are foundational because all five records depend on them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no incomplete dependency.
- **[Story]**: Maps to US1, US2 or US3 in `spec.md`.
- Every task names its primary file path.

## Phase 1: Setup

**Purpose**: Add only the two reviewed runtime dependencies and adapt the F001 boundary contract for the intentional F002 surface.

- [X] T001 Add constrained Pydantic 2.12 and rfc8785 runtime dependencies and refresh `uv.lock` in `pyproject.toml` and `uv.lock`
- [X] T002 Update the package-scope contract from “F002 absent” to “only reviewed F002 modules/dependencies present” in `tests/test_package.py` and `tests/test_repository_contract.py`

---

## Phase 2: Foundational Contracts

**Purpose**: Establish strict shared values and explicit identity primitives before any root record.

**Critical**: No root-model task starts until these tests fail for the missing behavior and the foundation passes.

- [X] T003 [P] Write failing strict-value, UTC, UUID, hash, extension, duplicate-key and trust-boundary tests in `tests/domain/test_common.py`
- [X] T004 [P] Write failing source-byte, RFC-envelope and domain-separation smoke tests in `tests/domain/test_identity.py`
- [X] T005 Implement strict frozen base models, supported-version checks, JSON-only values, UTC/UUID/hash types, trust and provenance value objects in `src/openardp/domain/common.py`
- [X] T006 Implement the strict raw-JSON inspection path and sanitized public validation helper in `src/openardp/domain/common.py`
- [X] T007 Implement RFC 8785 canonical bytes, canonical SHA-256, source version and explicit v1 identity-envelope primitives in `src/openardp/domain/identity.py`
- [X] T008 Export only the reviewed foundational types and helpers in `src/openardp/domain/__init__.py`

**Checkpoint**: Shared validation and identity primitives pass focused tests without I/O or network access.

---

## Phase 3: User Story 1 — Exchange trustworthy domain records (Priority: P1) MVP

**Goal**: Validate and round-trip Manifest, Block, Derivation, Relation and Context Bundle with exact provenance, trust and extensions.

**Independent Test**: Five synthetic golden JSON files validate through the matching models and public schemas, round-trip semantically and reject schema-expressible/model-semantic negative cases at the documented layer.

### Tests for User Story 1

- [X] T009 [P] [US1] Add one complete synthetic golden JSON record per root contract in `tests/fixtures/domain/manifest.json`, `block.json`, `derivation.json`, `relation.json` and `context-bundle.json`
- [X] T010 [US1] Write failing Manifest and Block invariant/round-trip tests in `tests/domain/test_models.py`
- [X] T011 [US1] Extend failing tests for Derivation lifecycle/recipe identity and derived trust in `tests/domain/test_models.py`
- [X] T012 [US1] Extend failing tests for typed Relation endpoints, relation-specific rules and deterministic edge identity in `tests/domain/test_models.py`
- [X] T013 [US1] Extend failing tests for Context budget, pinned scopes, evidence payloads, audit entries and missing evidence in `tests/domain/test_models.py`
- [X] T014 [US1] Write failing five-schema golden round-trip and schema/model invariant-classification tests in `tests/contract/test_domain_schemas.py`

### Implementation for User Story 1

- [X] T015 [US1] Implement SourceDescriptor, ParserDescriptor, SchemaVersions and DocumentManifest with recomputed source/representation invariants in `src/openardp/domain/manifest.py`
- [X] T016 [US1] Implement ContentBlock, BlockKind and content-hash validation using the shared SourceLocator from `src/openardp/domain/common.py` in `src/openardp/domain/block.py`
- [X] T017 [US1] Implement DerivationRecord lifecycle rules and artifact/output identity separation in `src/openardp/domain/derivation.py`
- [X] T018 [US1] Implement discriminated RecordReference variants, Relation kinds and relation-specific invariants in `src/openardp/domain/relation.py`
- [X] T019 [US1] Implement ContextBundle scopes, budget, evidence, selection, notice and missing-evidence invariants in `src/openardp/domain/context.py`
- [X] T020 [US1] Publish the five root models and their intentional shared types from `src/openardp/domain/__init__.py`
- [X] T021 [US1] Implement deterministic in-memory schema construction and explicit `--check`/`--write` behavior in `scripts/generate_schemas.py`
- [X] T022 [US1] Generate and review all five Draft 2020-12 contracts in `schemas/manifest.schema.json`, `schemas/block.schema.json`, `schemas/derivation.schema.json`, `schemas/relation.schema.json` and `schemas/context-bundle.schema.json`
- [X] T023 [US1] Make all focused US1 model and contract tests pass in `tests/domain/test_models.py` and `tests/contract/test_domain_schemas.py`

**Checkpoint**: US1 independently exchanges all five records with no persistence, parser, retrieval or interface implementation.

---

## Phase 4: User Story 2 — Reproduce content identities (Priority: P2)

**Goal**: Prove RFC 8785 conformance, strict JSON-value boundaries and stable domain-specific hashes across fresh processes.

**Independent Test**: Official/golden canonical bytes and digests match; 20 subprocess executions across multiple hash seeds and construction orders agree; unsupported values fail; semantically distinct mutations change the correct ID.

### Tests for User Story 2

- [X] T024 [P] [US2] Add RFC main, UTF-16 sort, numeric equivalence, Unicode and OpenARDP identity vectors in `tests/fixtures/domain/canonicalization-vectors.json`
- [X] T025 [US2] Extend failing JCS conformance and unsafe-value tests for NaN, infinity, unsafe integers, lone surrogates, cycles, non-string keys and unsupported Python types in `tests/domain/test_identity.py`
- [X] T026 [US2] Add failing tests proving each representation/block/derivation/relation projection includes and excludes the documented fields in `tests/domain/test_identity.py`
- [X] T027 [US2] Add failing 20-process determinism tests with permuted mapping order and multiple `PYTHONHASHSEED` values in `tests/domain/test_identity.py`
- [X] T028 [US2] Add failing duplicate-key, non-standard constant and strict JSON/model-boundary tests in `tests/domain/test_common.py`

### Implementation for User Story 2

- [X] T029 [US2] Harden `canonical_json_bytes` and `canonical_sha256` to the complete documented JCS/I-JSON boundary in `src/openardp/domain/identity.py`
- [X] T030 [US2] Implement named representation, block-content, derivation-artifact and relation identity payload builders in `src/openardp/domain/identity.py`
- [X] T031 [US2] Complete strict raw-JSON inspection without reinterpreting original JSON bytes in `src/openardp/domain/common.py`
- [X] T032 [US2] Make the complete US2 vector, mutation and subprocess suite pass in `tests/domain/test_identity.py` and `tests/domain/test_common.py`

**Checkpoint**: Stable identities are proven against independent vectors and fresh processes rather than only self-comparison.

---

## Phase 5: User Story 3 — Evolve and audit interchange contracts (Priority: P3)

**Goal**: Make compatibility, deterministic schema generation and change traceability reviewable and enforceable.

**Independent Test**: Supported `0.1.0` fixtures pass; malformed, uninstalled and unsupported-major releases fail distinctly; two schema checks are byte-stable and leave no diff.

### Tests for User Story 3

- [X] T033 [US3] Add failing malformed, uninstalled and unsupported-major version cases for all five roots in `tests/contract/test_domain_schemas.py`
- [X] T034 [US3] Add failing byte-for-byte schema drift, Draft 2020-12, stable ID/version metadata and no-write check-mode tests in `tests/contract/test_domain_schemas.py`
- [X] T035 [US3] Add failing traceability coverage asserting one model/schema/golden/negative/round-trip mapping per public root in `tests/contract/test_domain_schemas.py`

### Implementation for User Story 3

- [X] T036 [US3] Publish the compatibility, invariant-layer and regeneration contract in `schemas/README.md`
- [X] T037 [US3] Complete stable root metadata and deterministic normalized output in `scripts/generate_schemas.py`
- [X] T038 [US3] Make all compatibility, schema-drift and traceability tests pass in `tests/contract/test_domain_schemas.py`

**Checkpoint**: Contract evolution is explicit, deterministic and independently auditable.

---

## Phase 6: Documentation, Governance and Verification

**Purpose**: Align higher-level truth, record exact evidence and close all repository gates without expanding feature scope.

- [X] T039 [P] Record RFC 8785 identity and migration governance in `docs/adr/0006-rfc8785-canonical-identities.md`
- [X] T040 [P] Correct identity, representation pinning, invariant layers and installed-minor compatibility guidance in `docs/03_DATA_MODEL_AND_PACKAGE.md`
- [X] T041 [P] Update F002 status, public API usage and non-goals in `README.md`, `START_HERE.md`, `specs/README.md` and `CHANGELOG.md`
- [X] T042 [P] Update schema/identity test strategy and exact F002 verification commands in `docs/07_TEST_AND_BENCHMARK_STRATEGY.md` and `VALIDATION.md`
- [X] T043 Verify no F003+ persistence/parser/retrieval/CLI/provider modules or dependencies entered scope using `tests/test_package.py` and `tests/test_repository_contract.py`
- [X] T044 Run schema check twice plus focused quickstart scenarios and record results in `specs/002-domain-models-schemas/implementation-notes.md`
- [X] T045 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` and `uv run pytest`, then record exact results in `specs/002-domain-models-schemas/implementation-notes.md`
- [X] T046 Run `uv run --locked pre-commit run --all-files`, `uv build`, `git diff --check` and the offline locked pytest smoke, then record exact results in `specs/002-domain-models-schemas/implementation-notes.md`
- [X] T047 Update all task checkboxes, the specification status and convergence evidence in `specs/002-domain-models-schemas/tasks.md`, `spec.md` and `implementation-notes.md`
- [ ] T048 Verify the existing workflow defines the Linux/macOS/Windows release gate and prepare explicit PR/post-merge evidence fields in `specs/002-domain-models-schemas/implementation-notes.md`; populate live run URLs during publication after local convergence
- [X] T049 [US2] Exclude endpoint `extensions` from the version-1 relation projection, reject undeclared endpoint fields and add regression vectors in `src/openardp/domain/identity.py`, `tests/domain/test_identity.py` and `tests/fixtures/domain/canonicalization-vectors.json`
- [X] T050 [US1] Complete explicit invariant-branch coverage for locators, blocks, derivation lifecycle states, every relation reference variant and context consistency rules in `tests/domain/test_common.py` and `tests/domain/test_models.py`
- [X] T051 [US1] Introduce a schema-visible data-only trust subtype for content-bearing records and prove schema/model agreement in `src/openardp/domain/common.py`, the root models and `tests/contract/test_domain_schemas.py`
- [X] T052 [US3] Enforce LF checkouts for reviewed text contracts, decode Unicode vectors explicitly as UTF-8 and add a repository regression contract in `.gitattributes`, `tests/domain/test_identity.py` and `tests/test_repository_contract.py`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup** has no dependencies.
- **Foundational Contracts** depends on Setup and blocks every root model.
- **US1** depends on the foundation and delivers the independently exchangeable five-record MVP.
- **US2** depends only on the identity foundation; it may be implemented after US1 in this single-maintainer sequence and must not change record meaning silently.
- **US3** depends on US1 schemas and US2 canonicalization evidence.
- **Documentation/Verification** depends on all three stories.

### User-story dependency graph

```text
Setup -> Foundation -> US1 -> US2 -> US3 -> Verification
```

US2's user outcome can be demonstrated from the foundation without persistence or US3. US3 consumes the schemas produced by US1 and the identity rules proven by US2.

### Parallel opportunities

- T003 and T004 can be authored in parallel.
- The five independent golden fixture files in T009 can be prepared in parallel.
- T039 through T042 touch separate documentation files and can be reviewed in parallel after contracts stabilize.
- Model modules are separate, but T015–T019 remain sequential here because fixtures and cross-model shared types require one coherent public contract review.

## Requirement coverage

| Requirement group | Primary tasks |
|---|---|
| FR-001–FR-013 domain records/invariants | T009–T023 |
| FR-014–FR-017 canonicalization/identity | T004, T007, T024–T032 |
| FR-018–FR-020 schemas/drift | T014, T021–T022, T034, T036–T038 |
| FR-021–FR-023 fixtures/negative/offline tests | T003–T004, T009–T014, T024–T028, T033–T035 |
| FR-024–FR-025 typing/purity/scope | T002, T005–T008, T043, T045–T046 |
| FR-026–FR-027 traceability/invariant layers | T035–T042, T044–T048 |

## Implementation Strategy

### MVP first

1. Complete Setup and Foundational Contracts.
2. Complete US1 through its independent five-record round-trip checkpoint.
3. Do not start persistence or ingestion; F002 is already demonstrable at this point.

### Incremental delivery

1. US1 establishes trustworthy public records.
2. US2 independently proves stable identity and tightens no record outside the approved contract.
3. US3 freezes compatibility and deterministic schema-review mechanics.
4. Documentation and full gates close the feature.

### Task discipline

- Tests are written and observed failing before their implementation task.
- A completed task is marked `[X]` immediately.
- Changes to a persisted identity projection require updating the contract and governance before code.
- No task authorizes work from F003 or later.
