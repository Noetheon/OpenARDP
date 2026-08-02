# Tasks: Redistributable Real-World Corpus

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: Required by repository policy and explicit reproducibility/security acceptance criteria.

## Phase 1: Selection and Governance

- [X] T001 Record exact accepted/rejected sources, byte totals and review boundary in `specs/024-redistributable-realworld-corpus/research.md`
- [X] T002 [P] Add F024 authoritative prompt in `spec-kit/feature-prompts/024-redistributable-realworld-corpus.md`
- [X] T003 [P] Add requirement and redistribution-quality checklists in `specs/024-redistributable-realworld-corpus/checklists/`
- [X] T004 Complete clarification, plan, data model, quickstart and acceptance restatement in `specs/024-redistributable-realworld-corpus/`
- [X] T005 Run read-only Spec-Kit analysis and resolve every critical/high contradiction before implementation

**Checkpoint**: Exact source families, formats, rights boundary and benchmark/non-semantic scope are frozen.

## Phase 2: Corpus Contract Tests

- [X] T006 [P] Add lock/schema/identity happy-path tests in `tests/unit/test_realworld_corpus.py`
- [X] T007 [P] Add path, ordering, duplicate, normalization and case-collision tests in `tests/unit/test_realworld_corpus.py`
- [X] T008 [P] Add missing/extra/link/special-file and exact-byte tamper tests in `tests/security/test_realworld_corpus_boundaries.py`
- [X] T009 [P] Add missing/conflicting source, rights and evidence mapping tests in `tests/security/test_realworld_corpus_boundaries.py`
- [X] T010 [P] Add legal-overclaim, absolute-path, secret and document-body leakage tests in `tests/security/test_realworld_corpus_boundaries.py`
- [X] T011 [P] Add producer/independent-validator agreement and disagreement tests in `tests/integration/test_realworld_corpus.py`

## Phase 3: Frozen Corpus and Offline Validation

- [X] T012 Add six exact original payloads under `corpora/realworld/v0.1.0/sources/`
- [X] T013 Add minimal exact NASA/CISA publisher snapshots under `corpora/realworld/v0.1.0/evidence/`
- [X] T014 Add closed JSON Schema 2020-12 corpus contract in `corpora/realworld/v0.1.0/corpus-lock.schema.json`
- [X] T015 Add canonical six-asset/right/evidence inventory and corpus identity in `corpora/realworld/v0.1.0/corpus-lock.json`
- [X] T016 Add source use, versioning and non-endorsement guidance in `corpora/realworld/v0.1.0/README.md`
- [X] T017 Add complete reviewed attribution and redistribution facts in `corpora/realworld/v0.1.0/THIRD_PARTY_NOTICES.md`
- [X] T018 Implement closed lock parsing, identity, tree and mapping validation in `scripts/realworld_corpus.py`
- [X] T019 Implement an independent stdlib-only offline validator in `scripts/validate_realworld_corpus.py`
- [X] T020 Verify the actual committed corpus with both paths and record exact identity/size in `specs/024-redistributable-realworld-corpus/implementation-notes.md`

**Checkpoint**: One exact six-format corpus is usable and independently verifiable without network or parser imports.

## Phase 4: Explicit Connected Reproduction

- [X] T021 [P] Add fake-transport success, chunking and exact identity tests in `tests/unit/test_realworld_corpus.py`
- [X] T022 [P] Add redirect, content-type, truncation, oversize, digest and outage fault tests in `tests/security/test_realworld_corpus_boundaries.py`
- [X] T023 [P] Add absent/existing destination, failed staging cleanup and atomic publication lifecycle tests in `tests/integration/test_realworld_corpus.py`
- [X] T024 Implement reviewed HTTPS-host, redirect and response-type enforcement in `scripts/realworld_corpus.py`
- [X] T025 Implement bounded streaming, exact verification, staging cleanup and absent-destination publication in `scripts/realworld_corpus.py`
- [X] T026 Add explicit CLI facade and stable body-free outcomes in `scripts/fetch_realworld_corpus.py`
- [X] T027 Execute two fresh connected reproductions and independently match both against the committed corpus
- [X] T028 Record exact reproduction duration/bytes/outcomes and any retained upstream limitations in `specs/024-redistributable-realworld-corpus/implementation-notes.md`

**Checkpoint**: Independent maintainers can reconstruct exact bytes, and remote drift cannot silently change the corpus.

## Phase 5: Baseline Contract Tests

- [X] T029 [P] Add protocol, observation, summary and fail-closed decision tests in `tests/unit/test_realworld_corpus_benchmark.py`
- [X] T030 [P] Add deterministic identity, ordering and two-repetition coverage tests in `tests/unit/test_realworld_corpus_benchmark.py`
- [X] T031 [P] Add text/Markdown parser observation tests without retained bodies in `tests/integration/test_realworld_corpus_benchmark.py`
- [X] T032 [P] Add isolated body-free CSV probe and identity tests in `tests/integration/test_realworld_corpus_benchmark.py`
- [X] T033 [P] Add miniature DOCX/PPTX rich observation and pointer-resolution tests in `tests/integration/test_realworld_corpus_benchmark.py`
- [X] T034 [P] Add synthetic PDF bundle fixture and explicit missing/invalid-bundle tests in `tests/integration/test_realworld_corpus_benchmark.py`
- [X] T035 [P] Add producer/validator independence, observation/report tamper and unfavorable-result retention tests in `tests/integration/test_realworld_corpus_benchmark.py`

## Phase 6: Six-Format Baseline Implementation

- [X] T036 Add frozen baseline protocol and expected corpus ID in `benchmarks/realworld-corpus/v0.1.0/protocol.json`
- [X] T037 Add immutable pre-run baseline facts in `benchmarks/realworld-corpus/v0.1.0/baseline.json`
- [X] T038 Implement common body-free timing, RSS, hashing and stable error records in `scripts/realworld_corpus_benchmark.py`
- [X] T039 Implement TXT/Markdown observations through `TextParserAdapter` in `scripts/realworld_corpus_benchmark.py`
- [X] T040 Implement full-row/body-free CSV observations through isolated `scripts/realworld_csv_probe.py` after retaining F016's 1 MiB response-limit finding
- [X] T041 Implement PDF/DOCX/PPTX observations through `IsolatedDoclingAdapter` in `scripts/realworld_corpus_benchmark.py`
- [X] T042 Verify rich pointers/text retrieval and text/CSV block identities without retaining bodies in `scripts/realworld_corpus_benchmark.py`
- [X] T043 Implement pure summaries, closed coverage and readiness decision in `scripts/realworld_corpus_benchmark_evaluation.py`
- [X] T044 Implement deterministic body-free report and result manifest in `scripts/realworld_corpus_benchmark_evaluation.py`
- [X] T045 Add bounded atomic reference-run facade in `scripts/run_realworld_corpus_benchmark.py`
- [X] T046 Implement independent raw-result/identity/summary/decision/report validation in `scripts/validate_realworld_corpus_benchmark.py`
- [X] T047 Add opt-in actual-corpus/PDF-bundle reference test in `tests/integration/test_realworld_corpus_reference.py`

**Checkpoint**: Structural real-world behavior is measured independently without crossing into semantic evaluation.

## Phase 7: Binding Execution and Decision

- [X] T048 Execute all six actual assets twice with the validated F023 external model bundle and sockets denied
- [X] T049 Independently validate the complete result and regenerate exact summary, decision and report
- [X] T050 Commit the body-free reference result under `benchmarks/realworld-corpus/v0.1.0/results/reference-macos-arm64/`
- [X] T051 Add committed result drift test in `tests/test_realworld_corpus_drift.py`
- [X] T052 Record format counts, anchors, determinism, wall/CPU/RSS and decision in `specs/024-redistributable-realworld-corpus/implementation-notes.md`
- [X] T053 Retain every limitation, failed attempt or unfavorable observation without changing thresholds after the run

**Checkpoint**: F024 has one reproducible, decision-bearing actual six-format result.

## Phase 8: Documentation, Repository Integration and Release

- [X] T054 [P] Document corpus selection, verification, reproduction and claims in `docs/23_REALWORLD_CORPUS.md`
- [X] T055 [P] Update benchmark semantics in `docs/07_TEST_AND_BENCHMARK_STRATEGY.md`
- [X] T056 [P] Update supply-chain/network/rights operations in `docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md`
- [X] T057 [P] Update project status and F024 result in `README.md`, `VALIDATION.md` and `docs/19_PRODUCT_VALUE_BENCHMARK.md`
- [X] T058 [P] Add authoritative source and rights links in `REFERENCES.md`
- [X] T059 [P] Add additive corpus/benchmark behavior and limits in `CHANGELOG.md`
- [X] T060 Register corpus/benchmark drift checks and exact governed files in `scripts/validate_repository.py`
- [X] T061 Update maintainability inventory/ceilings only for justified new modules in `quality/maintainability-policy.json`
- [X] T062 Run every command in `specs/024-redistributable-realworld-corpus/quickstart.md` and record exact outcomes here
- [X] T063 Run Ruff, format, strict mypy, complete pytest, repository validation, build and all pre-commit hooks
- [X] T064 Run Spec-Kit analysis and convergence; resolve every critical/high finding and append only proven gaps
- [ ] T065 Open the private GitHub pull request, pass trusted Linux/macOS/Windows quality gates, merge it, verify post-merge CI and record exact evidence here

## Dependencies and Execution Order

- Phase 1 blocks implementation.
- Contract tests in Phase 2 precede corpus validator implementation.
- Frozen corpus validation in Phase 3 precedes connected reproduction and every parser claim.
- Reproduction and baseline contracts can be developed independently after Phase 3, but both must pass before binding
  execution.
- The actual PDF baseline requires the external validated F023 bundle; ordinary CI does not.
- Documentation may begin after the decision but release and F025 are blocked until convergence and remote matrix success.

## Parallel Opportunities

Items marked `[P]` touch disjoint files or independent test layers after their phase inputs are frozen. The user requested
sequential feature delivery, so F025 does not begin while any F024 task remains incomplete.

## Implementation Strategy

1. Prove byte/licensing completeness before parser quality.
2. Prove offline/atomic reproduction before relying on live publishers.
3. Prove each parser observation independently before aggregating a decision.
4. Freeze the actual result before documentation claims.
5. Release only after all local and trusted cross-platform gates converge.
