# Research: Product Value Benchmark

## Decision 1 — Evaluate user journeys, not isolated helper functions

**Decision**: Measure complete delivered paths: source preparation, verified search, bounded context, receipt replay,
freshness and rich unchanged reuse. Retain small pure-function tests only for validating the benchmark itself.

**Rationale**: The user asked whether the product works and is worthwhile. Microbenchmarks alone omit CAS verification,
SQLite indexing, process isolation, provenance and atomic publication costs that define OpenARDP.

**Alternatives considered**:

- Reuse only the F015 synthetic XML/text treatments: rejected because those are release-gate mechanics and explicitly
  narrower than the production rich path.
- Benchmark only CLI subprocesses: rejected because process startup would dominate repeated-query comparisons; one
  separate CLI smoke remains appropriate for user-facing integration.

## Decision 2 — Keep three strong comparison treatments

**Decision**: Compare raw source reparsing per task, persisted parsed/provider-native loading plus direct retrieval, and
OpenARDP prepared evidence reuse. Where a treatment is not meaningful for a format, record it as unavailable.

**Rationale**: Raw reparsing quantifies avoided parsing, while persisted-native reuse prevents an artificially weak
baseline. OpenARDP must justify its additional verification and persistence cost against both.

**Alternatives considered**:

- Raw reparsing only: constitutionally insufficient and biased.
- In-memory native reuse: too favorable in a different way because it omits persistence and restart costs; serialized
  persisted reuse better matches a local repeated-task workflow.

## Decision 3 — Use deterministic generated Markdown at 10k and 100k blocks

**Decision**: Generate one bounded Markdown source per profile containing uniquely identified factual paragraphs and
deterministic distractors. The reference profile has 10,000 blocks and the scale profile reaches the product limit of
100,000 blocks.

**Rationale**: One source avoids file-count noise while still exercising parsing, per-block CAS publication, catalog
rows, FTS coverage and context selection. Unique needles allow exact judgments without a model evaluator.

**Alternatives considered**:

- Commit large binary corpora: rejected for repository size and licensing.
- Thousands of tiny files: rejected because path/process overhead would obscure block-scale behavior.
- Only the existing three tiny F015 cases: rejected as incapable of testing the PRD scale target.

## Decision 4 — Treat real rich capability absence as evidence

**Decision**: Exercise the delivered Docling boundary for committed DOCX, PPTX and PDF fixtures. Do not download models
during the run. If the explicitly provisioned PDF model bundle is absent, emit a closed unavailable result and prevent an
unconditional decision.

**Rationale**: This preserves local-first/no-egress behavior and truthfully distinguishes installed code from an
operationally provisioned capability.

**Alternatives considered**:

- Allow Docling to download models: rejected because results would be network/cache dependent and violate the offline
  benchmark contract.
- Substitute the F015 standard-library PDF/XML parser: rejected because it would not measure the delivered provider.

## Decision 5 — Use existing clocks and deterministic robust statistics

**Decision**: Capture monotonic wall time and process CPU time, discard one warm-up, retain seven samples, publish p50,
p95, median absolute deviation and deterministic percentile-bootstrap confidence intervals. Peak RSS is a labelled host
proxy and may be unavailable on platforms without a safe standard-library source.

**Rationale**: This matches the proven F015 evidence approach without a new dependency. Raw samples remain available so
alternative analyses can be reproduced.

**Alternatives considered**:

- Add `pyperf` or a telemetry dependency: rejected because the needed bounded protocol is already implementable and a
  dependency would broaden supply-chain scope.
- Report only one timing: rejected as scheduler-sensitive and non-diagnostic.

## Decision 6 — Freeze a three-state value policy

**Decision**: Use `WORTHWHILE`, `CONDITIONALLY_WORTHWHILE` and `NOT_DEMONSTRATED`. Exact correctness, no stale serving and
zero unchanged parser calls are hard safety gates. Full format/scale completeness, PRD latency targets, aggregate context
ratio at most 0.50 and break-even within 100 tasks distinguish unconditional from conditional value.

**Rationale**: A binary success/failure would conflate an unsafe product with a useful product that still has capability
or performance limitations. Stable reason codes keep the judgment auditable.

**Alternatives considered**:

- Numeric composite score: rejected because weights would hide failures and imply false precision.
- Reuse F015 `GO`/`NO-GO`: rejected because release readiness also includes supply chain and cross-platform evidence;
  this feature answers a narrower product-value question and must not supersede F015.

## Decision 7 — Publish timing once, regenerate interpretation deterministically

**Decision**: Commit the actual sanitized reference/scale raw observations and their deterministic summary, decision and
report. Corpus inputs and generated sources support drift checks; timed observations are environment-bound and are not
treated as golden values in ordinary tests.

**Rationale**: Measured claims need raw evidence, but CI hardware is unsuitable as a timing oracle. Tests instead prove
models, completeness, calculations, tamper rejection and smoke execution.

**Alternatives considered**:

- Benchmark every PR: rejected due cost, noise and the just-completed CI optimization.
- Commit only the human report: rejected because conclusions would not be independently recomputable.
