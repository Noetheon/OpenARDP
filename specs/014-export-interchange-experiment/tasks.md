# Tasks: Export and Interchange Experiment

**Input**: Design documents from `/specs/014-export-interchange-experiment/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Mandatory and test-first where practical. All fixtures are synthetic and
network-free.

## Phase 1: Setup and governance

- [x] T001 Record active F014 prompt digest and acceptance criteria in specs/014-export-interchange-experiment/implementation-notes.md
- [x] T002 [P] Publish the four-candidate evidence decision in docs/adr/0015-bagit-interchange-profile.md
- [x] T003 [P] Add the experimental profile/version compatibility entry to docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md
- [x] T004 [P] Add package/import threats and trust non-claims to docs/06_SECURITY_THREAT_MODEL.md
- [x] T005 Validate all planning checklists in specs/014-export-interchange-experiment/checklists/

## Phase 2: Foundational profile contracts

- [x] T006 [P] Add failing domain model/version/identity tests in tests/domain/test_interchange.py
- [x] T007 [P] Add failing port runtime-conformance tests in tests/contract/test_interchange_port.py
- [x] T008 Implement closed interchange enums, limits, records, assets, relationships and results in src/openardp/domain/interchange.py
- [x] T009 Implement package identity and cross-record invariant helpers in src/openardp/domain/interchange.py
- [x] T010 Implement sanitized errors and source-reader/export/validator/import protocols in src/openardp/ports/interchange.py
- [x] T011 Register the public interchange model in scripts/generate_schemas.py
- [x] T012 Generate schemas/openardp_interchange_package.schema.json and add schema agreement tests in tests/test_schema_contracts.py
- [x] T013 Run domain, contract and schema focused gates and record evidence in specs/014-export-interchange-experiment/implementation-notes.md

## Phase 3: User Story 1 — Evidence-based decision (Priority: P1) 🎯 MVP

**Independent Test**: ADR matrix covers every published criterion and repository claim
validation finds no custom/universal-format claim.

- [x] T014 [P] [US1] Add ADR decision-quality tests in tests/test_repository_governance.py
- [x] T015 [P] [US1] Add the BagIt/RO-Crate/OCFL evidence matrix to docs/10_PRIOR_ART_AND_BUILD_DECISIONS.md
- [x] T016 [US1] Complete ADR 0015 deviations, revisit triggers and compatibility consequences in docs/adr/0015-bagit-interchange-profile.md
- [x] T017 [US1] Update docs/04_PRIOR_ART_AND_DD.md with authoritative versions and reviewed dates
- [x] T018 [US1] Validate User Story 1 independently and record evidence in specs/014-export-interchange-experiment/implementation-notes.md

## Phase 4: User Story 2 — Deterministic permitted export (Priority: P1)

**Independent Test**: Representative synthetic inputs export twice to identical bytes;
disallowed assets and changed sources fail with no destination.

- [x] T019 [P] [US2] Add failing deterministic ZIP/profile tests in tests/integration/test_bagit_interchange.py
- [x] T020 [P] [US2] Add failing source mutation, path/secret and permission tests in tests/security/test_interchange_boundaries.py
- [x] T021 [US2] Implement canonical portable path and BagIt manifest codecs in src/openardp/adapters/bagit_interchange.py
- [x] T022 [US2] Implement safe streaming asset reader and exact digest/length verification in src/openardp/adapters/bagit_interchange.py
- [x] T023 [US2] Implement deterministic stored-entry ZIP writer and fixed metadata in src/openardp/adapters/bagit_interchange.py
- [x] T024 [US2] Implement export inventory, canonical semantic record and package identity in src/openardp/services/interchange.py
- [x] T025 [US2] Implement fresh sibling staging, self-verification and no-overwrite atomic export publication in src/openardp/services/interchange.py
- [x] T026 [US2] Add repeated and twenty-way concurrent export tests in tests/integration/test_bagit_interchange.py
- [x] T027 [US2] Validate User Story 2 independently and record evidence in specs/014-export-interchange-experiment/implementation-notes.md

## Phase 5: User Story 3 — Verify before snapshot publication (Priority: P1)

**Independent Test**: Valid packages publish exactly once; every malformed, resource,
path, digest or relationship vector leaves destination absent/unchanged.

- [x] T028 [P] [US3] Add failing validator structure/version/limit tests in tests/integration/test_bagit_interchange.py
- [x] T029 [P] [US3] Add failing traversal/link/duplicate/collision/encryption/compression tests in tests/security/test_interchange_boundaries.py
- [x] T030 [US3] Implement bounded ZIP central-directory and entry-metadata validation in src/openardp/adapters/bagit_interchange.py
- [x] T031 [US3] Implement canonical tag/manifest/record parsing without extraction in src/openardp/adapters/bagit_interchange.py
- [x] T032 [US3] Implement streaming member hash/length and exhaustive inventory verification in src/openardp/adapters/bagit_interchange.py
- [x] T033 [US3] Implement profile-version, disposition, trust, relationship and extension validation in src/openardp/services/interchange.py
- [x] T034 [US3] Implement immutable import plan and source revalidation in src/openardp/services/interchange.py
- [x] T035 [US3] Implement safe allowlist copy, rehash, synchronization and atomic snapshot publication in src/openardp/services/interchange.py
- [x] T036 [US3] Add interruption cleanup and exact-convergence/conflict tests in tests/integration/test_bagit_interchange.py
- [x] T037 [US3] Add twenty-way duplicate import convergence tests in tests/integration/test_bagit_interchange.py
- [x] T038 [US3] Validate User Story 3 independently and record evidence in specs/014-export-interchange-experiment/implementation-notes.md

## Phase 6: User Story 4 — Compatibility without trust elevation (Priority: P2)

**Independent Test**: Unsupported versions classify distinctly; preserve/reject modes
are deterministic; instruction-like content cannot trigger authority.

- [x] T039 [P] [US4] Add failing unsupported-version and extension-policy tests in tests/domain/test_interchange.py
- [x] T040 [P] [US4] Add prompt-injection, inert-reference and license non-elevation tests in tests/security/test_interchange_boundaries.py
- [x] T041 [US4] Implement exact installed profile/schema reader policy in src/openardp/domain/interchange.py
- [x] T042 [US4] Implement bounded JSON-only extension preservation/rejection in src/openardp/domain/interchange.py
- [x] T043 [US4] Enforce data-role trust and sender-assertion semantics in src/openardp/domain/interchange.py
- [x] T044 [US4] Update docs/03_DATA_MODEL_AND_PACKAGE.md with portable projection and trust mapping
- [x] T045 [US4] Validate User Story 4 independently and record evidence in specs/014-export-interchange-experiment/implementation-notes.md

## Phase 7: User Story 5 — Reproducible cross-platform experiment (Priority: P2)

**Independent Test**: Vector generator drift check and validator classify the complete
manifest identically on Linux, macOS and Windows.

- [x] T046 [P] [US5] Add failing vector-manifest and drift tests in tests/test_interchange_conformance.py
- [x] T047 [US5] Implement adapter-independent CLI validator in scripts/validate_interchange_package.py
- [x] T048 [US5] Implement deterministic synthetic vector generator in scripts/generate_interchange_vectors.py
- [x] T049 [US5] Generate valid corpus in conformance/interchange/v0.1.0/valid/
- [x] T050 [US5] Generate invalid corpus in conformance/interchange/v0.1.0/invalid/
- [x] T051 [US5] Publish expected classifications in conformance/interchange/v0.1.0/manifest.json
- [x] T052 [US5] Document independent profile conformance scope in conformance/README.md
- [x] T053 [US5] Validate User Story 5 independently and record evidence in specs/014-export-interchange-experiment/implementation-notes.md

## Phase 8: Operator interface and cross-cutting convergence

- [x] T054 Add failing package-export/verify/import CLI tests in tests/integration/test_interchange_cli.py
- [x] T055 Implement closed request-file parsing and package commands in src/openardp/interfaces/cli.py
- [x] T056 Add bounded JSON/human results and stable exit categories in src/openardp/interfaces/cli.py
- [x] T057 [P] Update README.md and docs/02_GETTING_STARTED.md with experimental workflow and non-claims
- [x] T058 [P] Update docs/08_ROADMAP_AND_GOVERNANCE.md and CHANGELOG.md with F014 status
- [x] T059 [P] Update docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md with offline/import operational boundaries
- [x] T060 Run Ruff, format, mypy, pytest, build, schema, vector and repository quality gates
- [x] T061 Run the speckit-analyze consistency gate and resolve every critical/high issue
- [x] T062 Run the speckit-converge gate and complete specs/014-export-interchange-experiment/analysis.md
- [x] T063 Mark all tasks complete and finalize specs/014-export-interchange-experiment/implementation-notes.md
- [x] T064 Commit F014 as one isolated feature commit and push codex/f014-export-interchange-experiment
- [x] T065 Open the F014 PR and require Linux, macOS and Windows CI success
- [x] T066 Merge F014 only after clean review and verify post-merge main CI on all three platforms

## Dependencies and execution order

- Setup → Foundational blocks all stories.
- US1 decision evidence precedes the normative runtime claim.
- US2 export depends on foundational profile contracts.
- US3 verify/import depends on US2's normative writer/manifest codecs.
- US4 compatibility hardens the same closed model and can begin after foundational work.
- US5 vectors depend on US2–US4 behavior.
- CLI and convergence depend on all stories.

## Parallel opportunities

- Documentation tasks in different files can proceed independently.
- Domain, port and security tests can be authored independently before implementation.
- The user requested sequential feature completion; no later feature starts before T066.

## Implementation strategy

Freeze decision/profile contracts and tests; deliver deterministic export; add hostile
package validation and fresh snapshot publication; close version/trust behavior and
conformance evidence; then add CLI, full gates, PR CI and post-merge CI.

## Format validation

All 66 tasks use checkbox, sequential task ID, optional `[P]`, required user-story
label within story phases and an explicit target file path or exact gate/artifact.

## Phase 9: Convergence

- [x] T067 Add three-scope repeated deterministic export and complete roundtrip preservation tests in tests/integration/test_bagit_interchange.py per SC-002 and SC-003 (partial)
- [x] T068 Extend conformance/interchange/v0.1.0/ with missing path, resource, version, disposition, license and trust invalid vectors plus parity assertions per FR-027 and SC-005 (partial)
- [x] T069 Add fault-injected import interruption cleanup tests in tests/integration/test_bagit_interchange.py per T036 and SC-007 (missing)
- [x] T070 Add concurrent conflicting export and import publication tests with zero partial visibility in tests/integration/test_bagit_interchange.py per SC-009 (partial)
- [x] T071 Implement and enforce an immutable target-bound import plan in src/openardp/domain/interchange.py and src/openardp/services/interchange.py per plan: ImportPlan (missing)
- [x] T072 Complete experimental interchange onboarding in START_HERE.md and correct schema path references in specs/014-export-interchange-experiment/plan.md and specs/014-export-interchange-experiment/contracts/bagit-profile.md per T057 and FR-032 (partial)
- [x] T073 Write the generated vector manifest as explicit UTF-8 LF bytes and assert its cross-platform newline contract after Windows PR drift evidence
