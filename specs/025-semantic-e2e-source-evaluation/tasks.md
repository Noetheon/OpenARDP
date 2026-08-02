# Tasks: Semantic End-to-End Source Evaluation

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: Mandatory under repository policy and the explicit independent-evaluation boundary.

## Phase 1: Governance and Frozen Inputs

- [X] T001 Add authoritative F025 prompt and activate `specs/025-semantic-e2e-source-evaluation`
- [X] T002 Complete clarification with explicit no-LLM, no-post-hoc-query and CSV-gap decisions
- [X] T003 Freeze nineteen question intents, strata, languages, source expectations and source facts in `research.md`
- [X] T004 Complete plan, data model, contracts, quickstart and evaluation-integrity checklists
- [X] T005 Add closed JSON Schema 2020-12 question contract
- [X] T006 Add canonical nineteen-question ground truth with exact support atoms and source-fitness facts
- [X] T007 Add frozen protocol with treatments, limits, metrics, thresholds, privacy and corpus identity
- [X] T008 Add benchmark README with claim boundaries and explicit CSV/operator semantics
- [X] T009 Independently validate all support atoms against the actual locked sources before execution

**Checkpoint**: Questions, answers, atoms and policy are immutable before a binding product run.

## Phase 2: Input and Evaluation Contract Tests

- [X] T010 [P] Add schema/canonical identity and happy-path tests in `tests/unit/test_semantic_e2e_benchmark.py`
- [X] T011 [P] Add duplicate/order/normalization/unknown-field and corpus-ID rejection tests
- [X] T012 [P] Add missing stratum/language/format/source/atom/treatment coverage tests
- [X] T013 [P] Add source-fitness range, relevance separation and temporal-scope tests
- [X] T014 [P] Add READY, CONDITIONALLY_READY and NOT_READY exact policy fixtures
- [X] T015 [P] Add integer-threshold boundary and ratio-rounding tests
- [X] T016 [P] Add unsupported-question abstention and irrelevant-selection penalty tests
- [X] T017 [P] Add report projection and deterministic aggregate tests

## Phase 3: Product-Path and Security Tests

- [X] T018 [P] Add miniature text/rich ingestion and exact selected-body resolution integration fixture
- [X] T019 [P] Add direct-versus-operator identical-limit tests
- [X] T020 [P] Add multi-source atom/source-coverage and evidence-order tests
- [X] T021 [P] Add CSV `unsupported_format` test proving no product ingestion substitution
- [X] T022 [P] Add punctuation, generic-term budget and German no-translation cases
- [X] T023 [P] Add unsupported question false-positive and explicit-abstention cases
- [X] T024 [P] Add citation corruption, source mapping drift and unresolved anchor failures
- [X] T025 [P] Add absent/invalid PDF bundle and parser/network/resource failure mapping
- [X] T026 [P] Add result privacy scan for paths, host data, secrets, raw exceptions and source bodies
- [X] T027 [P] Add producer/independent-validator disagreement fixtures for every result file

## Phase 4: Frozen Evaluation Core

- [X] T028 Implement strict question/protocol loading, canonical identity and closed coverage in `scripts/semantic_e2e_benchmark.py`
- [X] T029 Implement NFC/casefold/whitespace-only atom normalization and matching
- [X] T030 Implement exact per-row metric numerators, semantic identity and stable failure rows
- [X] T031 Implement pure integer aggregate calculations in `scripts/semantic_e2e_evaluation.py`
- [X] T032 Implement frozen READY/CONDITIONAL/NOT_READY policy without rounded-float decisions
- [X] T033 Implement deterministic body-free report with representative success/failure IDs
- [X] T034 Implement bounded atomic result publication and run manifest

**Checkpoint**: Synthetic fixtures prove every evaluation and decision path independently of model execution.

## Phase 5: Real Product-Path Producer

- [X] T035 Validate F024 corpus and F023 bundle before workspace creation
- [X] T036 Compose deterministic text and rich ingestion in one fresh local workspace
- [X] T037 Ingest TXT/MD/PDF/DOCX/PPTX through delivered services with sockets denied
- [X] T038 Build verified document/source-key scope mapping without publishing absolute paths
- [X] T039 Implement exhaustive atom oracle over product evidence plus raw locked CSV rows
- [X] T040 Compile untouched questions with exact shared budget/limits
- [X] T041 Compile pre-frozen operator terms under identical shared budget/limits
- [X] T042 Resolve every selected block/projection through CAS/catalog verification
- [X] T043 Map selected evidence to support atoms, required sources, relevance and source fitness
- [X] T044 Emit explicit CSV unsupported rows and unsupported-question abstention facts
- [X] T045 Execute a second fresh workspace and require identical semantic rows/identities
- [X] T046 Retain descriptive wall/CPU/RSS and total resource-limit facts outside semantic identity

## Phase 6: Independent Validator

- [X] T047 Implement stdlib-only closed question/protocol/result parsing in `scripts/validate_semantic_e2e_benchmark.py`
- [X] T048 Independently recompute question-set identity and closed row coverage
- [X] T049 Independently recompute selected relevance, atom/source coverage and semantic row identities
- [X] T050 Independently recompute aggregate integer metrics and policy decision
- [X] T051 Independently render report and verify manifest hashes/run identity/result size/privacy
- [X] T052 Add `--inputs-only` path that validates frozen inputs without model execution
- [X] T053 Add opt-in actual-corpus/reference-result test and committed drift test

## Phase 7: Binding Execution and Honest Decision

- [X] T054 Execute the exact real corpus twice with the validated F023 bundle and sockets denied
- [X] T055 Independently validate every raw row, aggregate, decision, report and file identity
- [X] T056 Commit body-free reference result under `benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/`
- [X] T057 Record exact runtime/resource facts and every unfavorable observation in implementation notes
- [X] T058 Interpret READY/CONDITIONAL/NOT_READY without modifying questions, terms or thresholds

## Phase 8: Documentation and Repository Integration

- [X] T059 [P] Add `docs/24_SEMANTIC_E2E_EVALUATION.md` with methods, results, examples and limitations
- [X] T060 [P] Update README and VALIDATION with the exact F025 decision
- [X] T061 [P] Update benchmark strategy and product-value interpretation without rewriting F015/F020/F024
- [X] T062 [P] Update operations/privacy guidance for public ground truth and body-free results
- [X] T063 [P] Update REFERENCES and CHANGELOG
- [X] T064 Register exact F025 governed files and drift checks in repository validation
- [X] T065 Update active package/governance inventory tests to F025 without adding runtime modules

## Phase 9: Convergence and Publication

- [X] T066 Run every command in `quickstart.md` and record exact outcomes
- [X] T067 Run Ruff, format, native/Windows mypy, full pytest/coverage, repository validation, build and pre-commit
- [X] T068 Run Spec-Kit analysis; resolve every critical/high contradiction and append only proven gaps
- [X] T069 Run Spec-Kit convergence over all requirements, criteria, tasks and retained evidence
- [ ] T070 Commit F025 independently, push to the private repository and open its pull request
- [ ] T071 Record available GitHub checks exactly; do not weaken branch protection or falsify billing-blocked CI
- [ ] T072 Merge only when repository policy permits and record final release evidence

## Dependencies and Execution Order

- Phase 1 blocks all implementation and binding execution.
- Contract/evaluation tests precede evaluator code; product-path/security tests precede the producer.
- The independent validator must reject synthetic tampering before it validates the binding result.
- Documentation follows the frozen decision, never the expected outcome.
- GitHub billing state may block remote publication but cannot relax local convergence or justify hidden direct pushes.

## Parallel Opportunities

Tasks marked `[P]` touch separate test/document files. The implementation remains one sequential F025 feature and does
not start a follow-up semantic-provider or CSV product feature.
