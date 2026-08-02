# Tasks: Offline PDF Model Bundle

**Input**: Design documents from `specs/023-offline-pdf-model-bundle/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
**Tests**: Required tests-first because the request and repository constitution require deterministic offline/security
evidence before behavior changes.

## Phase 1: Setup and Frozen Inputs

**Purpose**: Freeze the exact upstream, licensing and benchmark inputs before implementation.

- [X] T001 Record the five exact upstream file lengths and SHA-256 values at immutable revisions in `model-bundles/pdf-docling-2.114.0-v1/source-lock.json`
- [X] T002 [P] Add the official Apache-2.0 text in `model-bundles/pdf-docling-2.114.0-v1/licenses/Apache-2.0.txt`
- [X] T003 [P] Add the official CDLA-Permissive-2.0 text in `model-bundles/pdf-docling-2.114.0-v1/licenses/CDLA-Permissive-2.0.txt`
- [X] T004 Add per-source revision, file and license assertions in `model-bundles/pdf-docling-2.114.0-v1/THIRD_PARTY_NOTICES.md`
- [X] T005 Generate and review the existing canonical model inventory in `model-bundles/pdf-docling-2.114.0-v1/manifest.json`
- [X] T006 Document connected/offline boundaries and exact usage in `model-bundles/pdf-docling-2.114.0-v1/README.md`
- [X] T007 [P] Freeze body-free profile, inputs, resource limits, samples and decision rules in `benchmarks/pdf-bundle/v0.1.0/protocol.json`
- [X] T008 [P] Freeze historical F020 PDF evidence and expected F023 source/bundle facts in `benchmarks/pdf-bundle/v0.1.0/baseline.json`
- [X] T009 Add benchmark reproduction and claims boundary in `benchmarks/pdf-bundle/v0.1.0/README.md`
- [X] T010 Update `.gitignore` to exclude generated heavyweight bundle/package/staging artifacts without hiding committed locks or evidence

---

## Phase 2: Foundational Contracts and Failure-First Tests

**Purpose**: Establish closed models, deterministic serialization and hostile-input expectations shared by every story.

**Critical**: No provisioner, package writer or parser-boundary change starts until these tests fail for the intended
missing behavior.

- [X] T011 [P] Add canonical source-lock, installation and result contract tests in `tests/contract/test_pdf_bundle_contract.py`
- [X] T012 [P] Add miniature locked source and valid installation builders in `tests/fixtures/pdf_bundle.py`
- [X] T013 [P] Add closed-tree missing/extra/link/type/case/Unicode/digest failure tests in `tests/security/test_pdf_bundle_boundaries.py`
- [X] T014 [P] Add hostile ZIP traversal/link/device/duplicate/collision/overflow/trailing-data tests in `tests/security/test_pdf_bundle_boundaries.py`
- [X] T015 [P] Add deterministic JSON, manifest/source reconciliation and limit tests in `tests/unit/test_docling_bundle.py`
- [X] T016 Define bounded source-lock, provenance, package and operation models in `src/openardp/adapters/docling_bundle.py`
- [X] T017 Implement strict canonical JSON loading and stable sanitized error taxonomy in `src/openardp/adapters/docling_bundle.py`
- [X] T018 Implement collision-safe traversal-free path and exact closed regular-file inventory primitives in `src/openardp/adapters/docling_bundle.py`
- [X] T019 Implement source-lock/manifest/provenance/license reconciliation in `src/openardp/adapters/docling_bundle.py`
- [X] T020 Verify project ignore and optional-dependency boundaries remain correct in `.gitignore` and `pyproject.toml`

**Checkpoint**: Synthetic contracts and every foundational rejection class are deterministic and network-free.

---

## Phase 3: User Story 1 — Reproducible Provisioning (Priority: P1) 🎯 MVP

**Goal**: Explicitly retrieve five pinned files into a fully verified atomically published installation.

**Independent Test**: A fake pinned source provisions twice from empty cache/destination to byte-identical manifests and
bundle IDs; interruption or mismatch never publishes a destination.

### Tests for User Story 1

- [X] T021 [P] [US1] Add exact revision/path allowlist and streamed length/digest tests in `tests/unit/test_docling_bundle.py`
- [X] T022 [P] [US1] Add atomic staging/interruption/existing-destination tests in `tests/integration/test_pdf_bundle_lifecycle.py`
- [X] T023 [P] [US1] Add tests proving ordinary imports and PDF use never invoke the provisioner in `tests/integration/test_pdf_bundle_lifecycle.py`
- [X] T024 [P] [US1] Add body/path/credential/raw-exception leakage tests in `tests/security/test_pdf_bundle_boundaries.py`

### Implementation for User Story 1

- [X] T025 [US1] Implement lazy explicit immutable-revision retrieval with per-file/aggregate admission in `src/openardp/adapters/docling_bundle_provisioning.py`
- [X] T026 [US1] Implement staging materialization of runtime files, canonical manifest/provenance and review material in `src/openardp/adapters/docling_bundle_provisioning.py`
- [X] T027 [US1] Implement fsync, complete verification and absent-destination atomic publication in `src/openardp/adapters/docling_bundle_provisioning.py`
- [X] T028 [US1] Implement deterministic body-free provisioning result and sanitized failures in `src/openardp/adapters/docling_bundle_provisioning.py`
- [X] T029 [US1] Add the explicit connected command facade in `scripts/provision_pdf_bundle.py`
- [X] T030 [US1] Add the offline verification command facade in `scripts/verify_pdf_bundle.py`
- [X] T031 [US1] Provision the real five-file bundle to an external fresh reference root and verify exact source revisions using `scripts/provision_pdf_bundle.py`
- [X] T032 [US1] Repeat real provisioning from a logically empty destination/cache and record manifest/bundle identity equality in `specs/023-offline-pdf-model-bundle/implementation-notes.md`

**Checkpoint**: The exact real model tree exists outside Git, is reproducible and validation needs no network.

---

## Phase 4: User Story 2 — Actual Offline PDF Conversion (Priority: P1)

**Goal**: Make the real isolated PDF path consume only the exact manifest tree and prove no cache/network fallback.

**Independent Test**: With every provider cache redirected to a new empty directory and sockets denied before provider
import, the frozen PDF produces canonical native and page-anchored evidence; missing/extra/tampered assets fail first.

### Tests for User Story 2

- [X] T033 [P] [US2] Extend listed-file validation tests to require an exact closed model-root tree in `tests/security/test_docling_boundaries.py`
- [X] T034 [P] [US2] Add empty-cache/offline-environment/socket-denial worker tests in `tests/unit/test_isolated_docling.py`
- [X] T035 [P] [US2] Add an opt-in real-bundle PDF reference test in `tests/integration/test_pdf_bundle_reference.py`
- [X] T036 [P] [US2] Add recipe bundle-ID and deterministic native/evidence identity tests in `tests/integration/test_pdf_bundle_reference.py`

### Implementation for User Story 2

- [X] T037 [US2] Make `validate_model_bundle` reject every unlisted or unsafe tree entry in `src/openardp/adapters/docling_native.py`
- [X] T038 [US2] Close provider cache/environment authority and preserve offline variables before import in `src/openardp/adapters/isolated_docling.py`
- [X] T039 [US2] Preserve CPU/one-thread/disabled-enrichment options while binding exact bundle identity in `src/openardp/adapters/docling_native.py`
- [X] T040 [US2] Run three real fresh-worker synthetic-PDF conversions from empty caches with socket denial and record exact outcomes in `specs/023-offline-pdf-model-bundle/implementation-notes.md`

**Checkpoint**: PDF is an actual local capability rather than a validated-but-unused archive claim.

---

## Phase 5: User Story 3 — Deterministic Offline Transfer (Priority: P1)

**Goal**: Build one byte-deterministic bounded ZIP and install it safely into a fresh offline destination.

**Independent Test**: Two packages from the same installation are byte-identical; safe extraction into two new roots
reconciles exact IDs; every hostile archive class fails without destination publication.

### Tests for User Story 3

- [X] T041 [P] [US3] Add deterministic metadata/order/compression/package-digest tests in `tests/unit/test_docling_bundle.py`
- [X] T042 [P] [US3] Add safe extraction and atomic install lifecycle tests in `tests/integration/test_pdf_bundle_lifecycle.py`
- [X] T043 [P] [US3] Add central-directory/local-header/trailing-byte adversarial tests in `tests/security/test_pdf_bundle_boundaries.py`
- [X] T044 [P] [US3] Add package round-trip contract tests in `tests/contract/test_pdf_bundle_contract.py`

### Implementation for User Story 3

- [X] T045 [US3] Implement deterministic sorted `ZIP_STORED` construction with normalized metadata and bounded fixed overhead in `src/openardp/adapters/docling_bundle_archive.py`
- [X] T046 [US3] Implement bounded preflight and streamed safe extraction into a disjoint staging tree in `src/openardp/adapters/docling_bundle_archive.py`
- [X] T047 [US3] Implement post-extraction full verification and absent-destination atomic publication in `src/openardp/adapters/docling_bundle_archive.py`
- [X] T048 [US3] Add deterministic package command facade in `scripts/package_pdf_bundle.py`
- [X] T049 [US3] Add safe offline install command facade in `scripts/install_pdf_bundle.py`
- [X] T050 [US3] Build the real portable package twice, verify byte identity and install/verify it in a fresh external root using `scripts/package_pdf_bundle.py`

**Checkpoint**: One independently verifiable artifact can cross an air-gap without global provider-cache state.

---

## Phase 6: User Story 4 — Decision-Bearing Measurement (Priority: P2)

**Goal**: Produce and independently validate the first honest offline PDF readiness result.

**Independent Test**: The real-bundle benchmark emits the exact five-file result set and an independent validator
regenerates every identity, statistic, judgment, report and decision; altered evidence fails.

### Tests for User Story 4

- [X] T051 [P] [US4] Add observation schema, robust-statistics and deterministic bootstrap tests in `tests/unit/test_pdf_bundle_benchmark.py`
- [X] T052 [P] [US4] Add readiness hard-failure and unfavorable-result retention tests in `tests/unit/test_pdf_bundle_benchmark.py`
- [X] T053 [P] [US4] Add producer/validator independence and tamper tests in `tests/integration/test_pdf_bundle_benchmark.py`
- [X] T054 [P] [US4] Add committed reference artifact drift validation in `tests/test_pdf_bundle_benchmark_drift.py`

### Implementation for User Story 4

- [X] T055 [US4] Implement body-free environment, inventory, package, validation, conversion and correctness observations in `scripts/pdf_bundle_benchmark.py`
- [X] T056 [US4] Implement warm-up/retained sampling, p50/p95/MAD/bootstrap summaries and resource measurements in `scripts/pdf_bundle_benchmark.py`
- [X] T057 [US4] Implement closed coverage and `PDF_OFFLINE_READY`/`PDF_OFFLINE_NOT_READY` evaluation in `scripts/pdf_bundle_benchmark_evaluation.py`
- [X] T058 [US4] Implement deterministic Markdown/report and exact result-file manifest generation in `scripts/pdf_bundle_benchmark_evaluation.py`
- [X] T059 [US4] Add the bounded benchmark producer facade in `scripts/run_pdf_bundle_benchmark.py`
- [X] T060 [US4] Implement an independent raw-evidence validator and regenerated projections in `scripts/validate_pdf_bundle_benchmark.py`
- [X] T061 [US4] Run the binding actual-bundle benchmark into `benchmarks/pdf-bundle/v0.1.0/results/reference-macos-arm64/`
- [X] T062 [US4] Independently validate the committed reference and record exact measurements/limitations in `specs/023-offline-pdf-model-bundle/implementation-notes.md`

**Checkpoint**: PDF readiness is a reproducible decision with explicit cost and failure evidence.

---

## Phase 7: User Story 5 — Rights and Supply-Chain Audit (Priority: P2)

**Goal**: Make every runtime byte traceable to one immutable source and reviewed license assertion without legal overclaim.

**Independent Test**: Reconciliation covers every file/source/license exactly once and rejects missing/conflicting claims;
the generated notices and reports distinguish mechanical verification from human legal review.

### Tests for User Story 5

- [X] T063 [P] [US5] Add missing/conflicting source/license and license-text-digest tests in `tests/contract/test_pdf_bundle_contract.py`
- [X] T064 [P] [US5] Add report/notice legal-overclaim and URL/query leakage tests in `tests/security/test_pdf_bundle_boundaries.py`

### Implementation for User Story 5

- [X] T065 [US5] Reconcile exact upstream card assertions and official license text digests in `model-bundles/pdf-docling-2.114.0-v1/source-lock.json`
- [X] T066 [US5] Document verified facts, review assertions and open legal/provenance limits in `docs/22_OFFLINE_PDF_MODEL_BUNDLE.md`
- [X] T067 [US5] Update supply-chain operating guidance in `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md`
- [X] T068 [US5] Add source URLs and model/license references in `REFERENCES.md`

**Checkpoint**: Redistribution inputs are inspectable and no automated artifact claims legal certainty.

---

## Phase 8: Polish, Governance and Release

**Purpose**: Align public claims, run every gate and release only after convergence.

- [X] T069 [P] Update delivered PDF capability and honest limitations in `README.md`
- [X] T070 [P] Add F023 result and reproduction commands in `VALIDATION.md`
- [X] T071 [P] Add the offline PDF result without rewriting F020 history in `docs/19_PRODUCT_VALUE_BENCHMARK.md`
- [X] T072 [P] Add F023 benchmark semantics in `docs/07_TEST_AND_BENCHMARK_STRATEGY.md`
- [X] T073 [P] Add model bundle/package behavior and compatibility notes in `CHANGELOG.md`
- [X] T074 Verify source/package module sizes and update exact reviewed ceilings in `quality/maintainability-policy.json` only when justified
- [ ] T075 Run every command in `specs/023-offline-pdf-model-bundle/quickstart.md` and record exact outcomes in `specs/023-offline-pdf-model-bundle/tasks.md`
- [ ] T076 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest`, `uv run python scripts/validate_repository.py`, `uv build` and `uv run pre-commit run --all-files`
- [ ] T077 Run Spec-Kit analysis and convergence, resolve every critical/high finding and record remaining risks in `specs/023-offline-pdf-model-bundle/tasks.md`
- [ ] T078 Open the private GitHub pull request, pass trusted Linux/macOS/Windows quality gates, merge it, verify post-merge CI and record exact evidence in `specs/023-offline-pdf-model-bundle/tasks.md`

---

## Dependencies and Execution Order

### Phase Dependencies

- Setup (Phase 1) has no feature dependencies beyond merged F022.
- Foundational tests/contracts (Phase 2) depend on the frozen input shapes and block every user story.
- US1 provisioning (Phase 3) is the MVP and produces the actual bundle needed by later real proofs.
- US2 parser proof (Phase 4) depends on US1's bundle but is independently testable with miniature assets until the real run.
- US3 portable transfer (Phase 5) depends on US1 verification, not on parser behavior.
- US4 benchmark (Phase 6) depends on US1–US3 because it measures provisioned, installed offline execution.
- US5 audit (Phase 7) can begin after Phase 2 but must converge before any redistribution-ready statement.
- Polish/release (Phase 8) begins only after every story checkpoint.

### Parallel Opportunities

- License texts, benchmark protocol and baseline use different files after T001 defines exact inputs.
- Contract, unit and security tests in Phase 2 may be authored independently before shared implementation.
- US2 parser tests and US3 archive tests touch separate files after US1's bundle contract stabilizes.
- Documentation in Phase 8 can be updated independently after the binding result is frozen.

## Implementation Strategy

### MVP First

1. Freeze five files and two licenses.
2. Complete closed synthetic validation contracts.
3. Provision and independently verify the real bundle.
4. Stop if reproducibility or licensing facts fail; do not hide the result behind later packaging.

### Incremental Delivery

1. Exact provisioned directory (US1).
2. Real cache-independent PDF conversion (US2).
3. Deterministic offline transfer (US3).
4. Decision-bearing measurement (US4).
5. Complete rights/supply-chain record (US5).
6. Full gates and release.

## Notes

- Check tasks only after their named tests/artifacts actually exist; record exact commands for T075–T078.
- Never stage generated model weights, packages, caches or the existing user-owned untracked `* 2` duplicate files.
- If implementation reveals a requirement conflict, correct `spec.md`/`plan.md`, regenerate tasks and rerun read-only
  analysis before continuing.
