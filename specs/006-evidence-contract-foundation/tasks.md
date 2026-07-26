# Tasks: Evidence Contract Foundation

**Input**: Design documents from `specs/006-evidence-contract-foundation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/evidence-contracts.md`, `quickstart.md`

**Tests**: Contract, identity, compatibility, security, and conformance changes require
tests first where practical. Every test remains offline and uses synthetic or
redistributable inputs.

**Organization**: Tasks are grouped by independently testable user story. F006 adds only
the contract foundation; the rich-parser adapter remains F007.

## Phase 1: Setup and Baseline

**Purpose**: Freeze the additive boundary before contract code changes.

- [x] T001 Record the F005A base commit and hashes for the five existing schemas plus canonical identity vectors in `specs/006-evidence-contract-foundation/implementation-notes.md`
- [x] T002 Verify the current locked baseline with the mandatory commands and record counts/results in `specs/006-evidence-contract-foundation/implementation-notes.md`
- [x] T003 [P] Add the F006 feature inventory and status row to `specs/README.md`
- [x] T004 [P] Add contract-family directory purpose and fixture policy to `conformance/README.md`

**Checkpoint**: The pre-change compatibility and quality baseline is reproducible.

---

## Phase 2: Foundational Contract Primitives

**Purpose**: Establish shared version, extension, scalar, and identity behavior used by
all stories.

**⚠️ CRITICAL**: No root model work begins until this phase passes.

### Tests first

- [x] T005 Add failing tests for installed/malformed/uninstalled/unsupported evidence versions, stability, and URI-namespaced extensions in `tests/domain/test_evidence_contracts.py`
- [x] T006 [P] Add failing golden tests for native/reference/projection identity domains, allowlists, excluded metadata, and process determinism in `tests/domain/test_evidence_identity.py`
- [x] T007 [P] Add failing raw-JSON tests for duplicate names, unsafe integers, constants, unknown fields, and sanitized errors in `tests/security/test_evidence_boundaries.py`

### Implementation

- [x] T008 Implement strict evidence contract metadata, semantic-version, media-type, bounded-string, safe-integer, and URI-extension primitives in `src/openardp/domain/evidence.py`
- [x] T009 Add native-representation, evidence-reference, and evidence-projection identity helpers using the existing RFC 8785 façade in `src/openardp/domain/identity.py`
- [x] T010 Export only intentional F006 public symbols without changing prior imports in `src/openardp/domain/__init__.py`
- [x] T011 Run the Phase 2 focused tests and document the observed red-to-green transition in `specs/006-evidence-contract-foundation/implementation-notes.md`

**Checkpoint**: Shared strict/versioned primitives and domain-separated identity helpers
pass without changing existing identity vectors.

---

## Phase 3: User Story 1 — Exchange Source-Bound Evidence Safely (Priority: P1) 🎯 MVP

**Goal**: Validate all four source-bound anchor variants independently of any adapter.

**Independent Test**: Construct valid text/page/table/pointer references, then reject
stale bindings, invalid geometry, malformed pointers, and identifier drift.

### Tests first

- [x] T012 [US1] Add failing positive/negative tests for text spans and fixed-point page geometry in `tests/domain/test_evidence_contracts.py`
- [x] T013 [US1] Add failing positive/negative tests for table cells and bounded profile-scoped pointers in `tests/domain/test_evidence_contracts.py`
- [x] T014 [US1] Add failing reference identity and embedded source/native binding tests in `tests/domain/test_evidence_contracts.py`

### Implementation

- [x] T015 [US1] Implement `ProviderPointer`, `TextSpanAnchor`, `PageRegionAnchor`, `TableCellAnchor`, and `OpaqueProviderPointerAnchor` in `src/openardp/domain/evidence.py`
- [x] T016 [US1] Implement immutable `EvidenceReference` with discriminated anchors and declared-identity verification in `src/openardp/domain/evidence.py`
- [x] T017 [US1] Implement pure source/native aggregate checks for references in `src/openardp/domain/evidence.py`
- [x] T018 [US1] Run the User Story 1 independent test and record exact results in `specs/006-evidence-contract-foundation/implementation-notes.md`

**Checkpoint**: The minimum viable evidence-reference contract is deterministic,
source-bound, and adapter-independent.

---

## Phase 4: User Story 2 — Preserve Native Fidelity Without a Second Full IR (Priority: P2)

**Goal**: Represent the retained complete native artifact and one thin retrieval
projection without provider-model leakage.

**Independent Test**: Validate native/projection records, recompute their identities, and
prove projection/reference/native scope consistency.

### Tests first

- [x] T019 [US2] Add failing native artifact provenance, provider-profile, identity, and mutation tests in `tests/domain/test_evidence_contracts.py`
- [x] T020 [US2] Add failing projection retrieval/navigation/provenance, identity, and mismatch tests in `tests/domain/test_evidence_contracts.py`
- [x] T021 [US2] Add failing contract-surface tests prohibiting complete-tree, provider-class, storage-path, ranking, and prompt fields in `tests/security/test_evidence_boundaries.py`

### Implementation

- [x] T022 [US2] Implement provider recipe and immutable `NativeRepresentation` with exact source/artifact provenance in `src/openardp/domain/evidence.py`
- [x] T023 [US2] Implement `RetrievalHandle`, projection provenance, and immutable `EvidenceProjection` in `src/openardp/domain/evidence.py`
- [x] T024 [US2] Complete aggregate validation for native/reference/projection scopes and duplicate-ID collisions in `src/openardp/domain/evidence.py`
- [x] T025 [US2] Run the User Story 2 independent test and record exact results in `specs/006-evidence-contract-foundation/implementation-notes.md`

**Checkpoint**: Native fidelity remains available, while the provider-neutral projection
is measurably limited to the accepted thin surface.

---

## Phase 5: User Story 3 — Enforce Trust and Version Boundaries (Priority: P3)

**Goal**: Make trust promotion, instruction authority, and version ambiguity fail closed.

**Independent Test**: Validate every allowed trust transition and reject every promotion,
non-data role, execution flag, unsupported version, and unsafe extension.

### Tests first

- [x] T026 [US3] Add failing complete trust-lattice transition tests in `tests/domain/test_evidence_contracts.py`
- [x] T027 [US3] Add failing data-only/non-execution and raw-value-redaction tests in `tests/security/test_evidence_boundaries.py`
- [x] T028 [US3] Add failing caller-pinned stale-source and duplicate semantic-ID collision tests in `tests/domain/test_evidence_contracts.py`

### Implementation

- [x] T029 [US3] Implement F006 `TrustClassification` origin/effective anti-escalation invariants in `src/openardp/domain/evidence.py`
- [x] T030 [US3] Integrate trust classification into projections without making trust identity-significant in `src/openardp/domain/evidence.py`
- [x] T031 [US3] Finalize sanitized aggregate diagnostics and pinned-source validation in `src/openardp/domain/evidence.py`
- [x] T032 [US3] Run the User Story 3 independent test and record exact results in `specs/006-evidence-contract-foundation/implementation-notes.md`

**Checkpoint**: Evidence cannot gain authority or compatibility through malformed data.

---

## Phase 6: User Story 4 — Reuse the Contracts Independently (Priority: P4)

**Goal**: Publish deterministic schemas, conformance fixtures, standalone validation, and
optional standards mappings.

**Independent Test**: A clean offline command validates the complete public corpus without
loading adapters and old schemas remain unchanged.

### Tests first

- [x] T033 [US4] Add failing four-root JSON Schema/model parity and deterministic-generation tests in `tests/contract/test_evidence_schemas.py`
- [x] T034 [US4] Add failing manifest path-confinement, expected-category, adapter-import, and no-network tests in `tests/security/test_evidence_boundaries.py`
- [x] T035 [US4] Add failing valid/invalid corpus and golden-vector coverage tests in `tests/contract/test_evidence_schemas.py`

### Implementation

- [x] T036 [US4] Extend per-root deterministic generation without altering existing schema bytes in `scripts/generate_schemas.py`
- [x] T037 [US4] Generate and review the four F006 JSON Schema files in `schemas/`
- [x] T038 [US4] Add synthetic valid/invalid roots, cross-record scenarios, canonical vectors, and manifest under `conformance/evidence/v0.1.0/`
- [x] T039 [US4] Implement the path-confined adapter-independent fixture validator in `scripts/validate_evidence_contracts.py`
- [x] T040 [P] [US4] Document all new roots, enforcement layers, extension/version policy, and additive compatibility in `schemas/README.md`
- [x] T041 [P] [US4] Publish optional W3C PROV/Web Annotation mappings and explicit non-mappings in `docs/15_EVIDENCE_CONTRACT_STANDARDS_MAPPING.md`
- [x] T042 [P] [US4] Update `contracts/README.md`, `conformance/README.md`, and `CHANGELOG.md` for the experimental family and migration boundary
- [x] T043 [US4] Run the standalone validator and User Story 4 independent test, recording exact results in `specs/006-evidence-contract-foundation/implementation-notes.md`

**Checkpoint**: An independent consumer has reviewed roots, fixtures, vectors, and an
offline validation entry point.

---

## Phase 7: Polish, Compatibility, and Convergence

**Purpose**: Prove completeness, prior-contract preservation, packaging, and repository
quality.

- [x] T044 Verify every task and requirement against `spec.md`, `plan.md`, and `contracts/evidence-contracts.md`; correct the highest-level originating artifact before downstream changes
- [x] T045 Run `uv run --locked python scripts/generate_schemas.py --check` and the standalone evidence validator
- [x] T046 Run Ruff, format, strict mypy for native and Windows targets, full network-blocked pytest, repository validation, and distribution build
- [x] T047 Prove no diff from base for the five Feature 005 schemas and `tests/fixtures/domain/canonicalization-vectors.json`
- [x] T048 Validate wheel import in an isolated offline environment and confirm the public domain surface is packaged
- [x] T049 Update `README.md`, `VALIDATION.md`, and `docs/03_DATA_MODEL_AND_PACKAGE.md` only where the delivered F006 status or contract inventory requires it
- [x] T050 Run Spec Kit analysis and resolve every critical/high finding at its originating artifact before implementation closure
- [x] T051 Run Spec Kit convergence; append and implement any remaining tasks without rewriting completed tasks
- [x] T052 Finalize `specs/006-evidence-contract-foundation/implementation-notes.md` with exact commands, counts, tradeoffs, residual risks, rollback, and remote-evidence placeholders

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** freezes the F005A baseline.
- **Phase 2** establishes strict shared primitives and blocks all user stories.
- **US1** provides the independently useful evidence-reference MVP.
- **US2** depends on US1 reference semantics and adds native/projection records.
- **US3** depends on the projection surface and closes security/version policy.
- **US4** depends on all record semantics before schemas and fixtures can become reviewed
  public artifacts.
- **Phase 7** depends on every story and completes compatibility/convergence evidence.

### Within Each User Story

- Tests are authored and observed failing before their implementation tasks.
- Identity helpers precede models that recompute declared identities.
- Record-local invariants precede aggregate cross-record validation.
- Schema generation follows final model shape.
- Public fixtures and validator follow stable experimental `0.1.0` semantics.

### Parallel Opportunities

- T003/T004 touch independent documentation.
- T006/T007 establish independent identity and security tests.
- T040/T041/T042 document independent public surfaces after schemas and fixtures exist.
- The full quality commands in T046 may run independently after the tree is frozen, but
  their combined result is recorded once.

## Implementation Strategy

### MVP first

1. Freeze baseline.
2. Implement shared strict/version/identity primitives.
3. Deliver source-bound `EvidenceReference` and all four anchor variants.
4. Stop and independently validate US1.

### Incremental completion

1. Add native representation plus thin projection.
2. Close trust and compatibility boundaries.
3. Generate schemas and conformance evidence.
4. Prove zero prior-contract drift.
5. Converge, publish one PR, pass three-platform CI, merge, and reverify `main`.

### Rollback

Revert the single F006 feature commit or merge commit. F006 adds no workspace migration,
catalog data, adapter dependency, network behavior, or source-file mutation. New
experimental records may be discarded and regenerated; existing F002/F005 records remain
unchanged.
