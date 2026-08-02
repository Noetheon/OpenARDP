# Feature Specification: Product Value Benchmark

**Feature Branch**: `codex/f020-product-value-benchmark`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User request to test the complete delivered OpenARDP project, design and execute a meaningful benchmark,
publish inspectable results, and determine whether its actual benefits justify its preparation and storage costs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure the Real Repeated-Use Value (Priority: P1)

As a prospective local user, I can compare preparing evidence once and reusing it with reparsing the same sources and
with directly reusing a persisted provider-native representation, so that I can judge whether OpenARDP saves meaningful
time or work on repeated document tasks.

**Why this priority**: Avoiding redundant parsing is the central product thesis. A benchmark that omits a strong native
reuse baseline or ignores one-time preparation cost cannot answer whether the product is worthwhile.

**Independent Test**: Execute fixed exact-lookup and bounded-context tasks from a fresh state and after preparation;
derive the break-even task count from measured setup and repeated-operation costs for every comparable treatment.

**Acceptance Scenarios**:

1. **Given** identical source versions and tasks, **When** all comparable treatments run, **Then** raw reparsing,
   persisted-native reuse and OpenARDP reuse report preparation cost, repeated-task latency and parser invocations
   separately.
2. **Given** measured preparation and repeated-task costs, **When** value is assessed, **Then** the report states the
   first repeat count at which OpenARDP amortizes its extra preparation cost or states that no break-even was observed.
3. **Given** a baseline that is faster, smaller or more complete, **When** results are summarized, **Then** the
   unfavorable comparison receives the same prominence as favorable results.

---

### User Story 2 - Validate Correctness at Useful Scale (Priority: P1)

As an evaluator, I can measure exact retrieval, evidence anchors, bounded context and deterministic replay on both a
representative reference corpus and the documented 100,000-block scale target, so that speed is never reported without
answer and evidence quality.

**Why this priority**: A fast cache is harmful if it returns the wrong source version, misses expected evidence or loses
the ability to cite an exact origin.

**Independent Test**: Generate the declared synthetic corpus, execute its fixed judgments, and independently recompute
retrieval precision, recall, rank, anchor correctness, context coverage, replay equality and stale-evidence incidents.

**Acceptance Scenarios**:

1. **Given** a deterministic corpus with uniquely judged facts and distractors, **When** exact lookup runs, **Then**
   every result can be compared with an expected document, evidence identity and source location.
2. **Given** at least 100,000 prepared blocks, **When** the fixed search workload runs, **Then** latency distributions,
   correctness and failures remain separated and all retained samples are inspectable.
3. **Given** fixed context budgets, **When** evidence is compiled and replayed, **Then** supplied bytes, selected and
   omitted evidence, expected-fact coverage and byte-identical replay are reported per task.
4. **Given** an operation that cannot complete within the declared limits, **When** the suite continues, **Then** the
   failure remains an explicit unavailable or failed observation and is not silently removed from aggregates.

---

### User Story 3 - Measure Rich-Document Reuse Honestly (Priority: P1)

As a user of PDF, DOCX and PPTX documents, I can see the actual cold parsing cost, warm unchanged reuse cost, native
artifact size, projected evidence size and parser avoidance for each delivered rich format, including an explicit result
when an optional model bundle is not provisioned.

**Why this priority**: Rich parsing is the largest expected source of avoided compute, but the result must describe the
real optional-provider boundary rather than substitute a lightweight parser or claim unsupported formats.

**Independent Test**: Run redistributable documents through the delivered rich ingestion path, repeat unchanged
ingestion, retrieve exact evidence, and compare it with fresh provider parsing and persisted-native reuse.

**Acceptance Scenarios**:

1. **Given** an available rich-format provider, **When** cold and unchanged ingestion run, **Then** the benchmark records
   provider invocations, latency, CPU time, peak-memory proxy and stored bytes for both phases.
2. **Given** a prepared provider-native artifact, **When** native reuse and OpenARDP evidence reuse run, **Then** both
   are measured against the same source and expected facts without counting source reparsing as native reuse.
3. **Given** a format requiring an absent optional model bundle, **When** the benchmark reaches that case, **Then** the
   format is reported as unavailable with a closed reason and reduces completeness; it is never emulated by another
   parser.

---

### User Story 4 - Exercise Freshness, Change and Failure Boundaries (Priority: P1)

As a cautious operator, I can verify unchanged checks, one-fact edits, invalidation, reparsing, stale rejection and
deterministic recovery, so that a favorable latency result cannot be produced by serving obsolete evidence.

**Why this priority**: Reuse only has value when the system distinguishes safe cache hits from changed or corrupt state.

**Independent Test**: Run unchanged checks repeatedly, apply deterministic edits to copies, query before and after
re-ingestion, and inject declared unavailable and limit outcomes while preserving originals.

**Acceptance Scenarios**:

1. **Given** an unchanged source, **When** freshness and re-ingestion are repeated, **Then** no parser runs and the same
   source/evidence identities remain current.
2. **Given** a deterministic fact edit, **When** freshness is checked before re-ingestion, **Then** the prior result is
   not represented as current; after re-ingestion only the new fact is returned for the current head.
3. **Given** any benchmark interruption or case failure, **When** output is published, **Then** source fixtures stay
   unchanged, partial results cannot replace a complete result set and the failed case remains visible.

---

### User Story 5 - Receive a Reproducible Worth-It Decision (Priority: P1)

As the project owner, I receive raw observations, a machine-readable decision and a concise human report that distinguish
measured facts, derived conclusions and limitations and answer whether OpenARDP is worthwhile for the tested workloads.

**Why this priority**: Thousands of observations are not useful unless they lead to a transparent, repeatable decision
with a clear boundary on what was and was not proven.

**Independent Test**: Regenerate the corpus and non-timing artifacts, validate their identities, recompute the decision
from raw observations, and verify that changing or removing a mandatory observation changes the decision predictably.

**Acceptance Scenarios**:

1. **Given** a complete run, **When** the report is generated, **Then** it publishes environment, corpus, workloads,
   baselines, raw samples, p50/p95, dispersion, confidence intervals, resource proxies, storage, correctness, break-even,
   limitations and decision thresholds.
2. **Given** strong correctness and reuse but incomplete format or performance evidence, **When** the decision is made,
   **Then** the outcome is `CONDITIONALLY_WORTHWHILE`, not an unconditional success.
3. **Given** failed correctness, stale serving or no demonstrated parser avoidance, **When** the decision is made,
   **Then** the outcome is `NOT_DEMONSTRATED` regardless of favorable latency.
4. **Given** identical corpus, policy and raw observations, **When** the evaluator reruns, **Then** the machine decision
   and human report are byte-identical.

### Edge Cases

- Reference-machine load, thermal throttling or timer granularity creates noisy or invalid samples.
- A treatment cannot support one document format or task without an optional dependency or model bundle.
- An operation succeeds but produces zero candidates, incomplete anchors or insufficient context.
- The 100,000-block corpus exceeds a declared time, memory, file-count or storage limit.
- Persisted-native loading is faster than OpenARDP for a small corpus but slower beyond a crossover point.
- Preparation cost is never amortized within the declared repeated-task horizon.
- A changed source has the same path but different bytes, or a reverted source returns to an earlier content identity.
- Raw observations contain duplicate identities, inconsistent units, negative durations or non-finite values.
- A process exits, is cancelled or runs out of space before atomic result publication.
- A machine lacks PDF models, a supported rich parser or a stable reference environment.
- Reports accidentally contain document bodies, absolute paths, usernames, hostnames or raw exception text.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The benchmark MUST publish one versioned protocol, corpus manifest, judgment set and decision policy before
  interpreting results.
- **FR-002**: The protocol MUST distinguish a fast smoke profile, a decision-bearing reference profile and the
  100,000-block scale workload; only the declared decision-bearing runs may support the final conclusion.
- **FR-003**: Required comparisons MUST include raw reparsing, persisted provider-native reuse and OpenARDP prepared
  reuse whenever the treatment supports the same source and task.
- **FR-004**: Every treatment MUST receive identical source bytes, task identities, expected facts, repetition policy
  and resource limits; unavailable treatments MUST remain visible.
- **FR-005**: Timing MUST discard declared warm-ups and retain at least seven measured repetitions for repeated
  operations, with p50, p95, median absolute deviation and 95-percent confidence intervals.
- **FR-006**: Raw observations MUST identify the protocol, corpus, policy, environment class, workload, treatment, phase,
  metric, unit, repetition and terminal status without source bodies or machine-identifying paths.
- **FR-007**: Efficiency metrics MUST include wall time, process CPU time, parser invocations, input/source bytes,
  selected bytes, persistent workspace bytes and a peak-memory proxy where the host can supply one.
- **FR-008**: The reference text corpus MUST be deterministic, redistributable, contain uniquely judged facts plus
  realistic distractors, and exercise at least 10,000 blocks.
- **FR-009**: The scale workload MUST prepare and query at least 100,000 blocks using fixed judgments and bounded disk,
  memory and execution time.
- **FR-010**: Search evaluation MUST report p50/p95 latency, precision, recall, reciprocal rank and exact source/evidence
  correctness for every judged query.
- **FR-011**: Context evaluation MUST report task latency, selected/native byte ratio, expected-fact coverage,
  insufficiency, exact evidence identities and deterministic replay for at least three budgets.
- **FR-012**: Freshness evaluation MUST measure unchanged status and re-ingestion, require zero warm parser invocations,
  and verify identity stability.
- **FR-013**: Change evaluation MUST use deterministic source copies and prove changed detection, new-head publication,
  current-result replacement, prior-version preservation and stale-result exclusion.
- **FR-014**: Rich evaluation MUST use the delivered rich parser and ingestion boundary for DOCX, PPTX and PDF; a missing
  required model bundle or provider capability MUST be explicit rather than substituted.
- **FR-015**: Rich comparisons MUST separate cold provider parsing, direct persisted-native loading, OpenARDP unchanged
  reuse, evidence retrieval and storage amplification.
- **FR-016**: The evaluator MUST compute preparation amortization and the first break-even repeat count up to a declared
  horizon for every comparable workload; no observed crossover MUST be a valid result.
- **FR-017**: Decision thresholds MUST be frozen before the reference run and MUST include correctness, stale safety,
  parser avoidance, documented latency targets, context reduction, completeness and break-even.
- **FR-018**: The decision MUST be one of `WORTHWHILE`, `CONDITIONALLY_WORTHWHILE` or `NOT_DEMONSTRATED`, with stable
  reason codes and no override path.
- **FR-019**: `WORTHWHILE` MUST require complete mandatory evidence, exact judged correctness, zero stale incidents,
  zero unchanged parser calls, attainment of the documented local status/search latency targets, bounded-context
  reduction and observed amortization within the policy horizon.
- **FR-020**: `CONDITIONALLY_WORTHWHILE` MUST require exact correctness, zero stale incidents and parser avoidance but
  identify each missing capability, missed target or non-amortized workload.
- **FR-021**: `NOT_DEMONSTRATED` MUST result from any correctness failure, stale-current result, parser invocation on
  unchanged reuse, invalid evidence or inability to complete the minimum reference workload.
- **FR-022**: Corpus generation, policy validation, observation validation, aggregation, decision generation and report
  generation MUST be independently runnable and covered by automated negative tests.
- **FR-023**: Generated normative corpus and report projections MUST support deterministic drift checks; timed samples
  MUST be preserved as new environment-bound observations rather than expected to reproduce byte-for-byte.
- **FR-024**: Results MUST be published atomically and must not overwrite an existing complete run unless exact bytes
  already agree.
- **FR-025**: The complete benchmark MUST run locally with network access denied, preserve original fixtures, use only
  synthetic or redistributable data and avoid external model evaluation.
- **FR-026**: The final report MUST distinguish observed facts, policy-derived conclusions, extrapolations and untested
  conditions and MUST document cases where OpenARDP is slower or more expensive.
- **FR-027**: The benchmark feature MUST run the repository's full offline quality suite and incorporate the existing
  release/security evidence status without relabelling a prior `NO-GO` as a passing product-value result.
- **FR-028**: The benchmark MUST remain a maintainer evaluation tool and MUST NOT change application, workspace,
  evidence-contract, provider-profile or export-profile compatibility.

### Non-Goals and Compatibility Impact

- **Non-goal**: Tune production algorithms until a favorable benchmark result appears.
- **Non-goal**: Use proprietary documents, network services, external model graders or unverifiable energy estimates.
- **Non-goal**: Claim enterprise-scale, universal parser, answer-quality or hardware-independent performance.
- **Non-goal**: Clear Feature 015 supply-chain, platform or release blockers through a separate product-value policy.
- **Non-goal**: Add a runtime parser, storage provider, public API or mandatory dependency.
- **Compatibility impact**: None. Application `0.1.0rc1`, workspace revision 10, experimental evidence contracts,
  Docling provider profile and BagIt export profile remain unchanged.

### Key Entities

- **Benchmark Protocol**: Versioned rules for workloads, treatments, repetitions, metrics, invalid samples and privacy.
- **Corpus Case**: Synthetic source family, scale, immutable identity, judged tasks, edits and redistribution facts.
- **Benchmark Observation**: One immutable measurement or explicit failure bound to all normative identities.
- **Metric Summary**: A deterministic aggregation of compatible observations with sample count and uncertainty.
- **Value Policy**: Predeclared thresholds and the three-outcome decision procedure.
- **Value Decision**: Machine-readable outcome, reason codes, passed and failed thresholds and evidence identities.
- **Reference Report**: Human projection of the verified observations and decision, including unfavorable results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean reference run completes the minimum 10,000-block corpus, all judged workflows and at least seven
  retained repeated-operation samples per comparable treatment without network access.
- **SC-002**: The scale run prepares at least 100,000 blocks and reports search p95 against the canonical 300 ms target
  without omitting failures or correctness results.
- **SC-003**: All judged successful retrieval and context cases achieve 100-percent expected-fact and source-anchor
  correctness; any deviation prevents an unconditional worthwhile decision.
- **SC-004**: Every unchanged source reuse records zero parser invocations and stable source/evidence identities.
- **SC-005**: Changed-source cases record 100-percent stale-current rejection and return only the new current fact after
  successful re-ingestion.
- **SC-006**: DOCX and PPTX produce measured cold and warm results; PDF produces a measured result or one explicit closed
  unavailable reason tied to the missing provisioned capability.
- **SC-007**: Every fixed context budget reports selected/native bytes, coverage and replay; an unconditional worthwhile
  decision requires the aggregate selected/native ratio to be at most 0.50.
- **SC-008**: The report states a measured break-even count or `not-observed` for every required repeated-use workload,
  using a policy horizon no larger than 100 tasks.
- **SC-009**: Re-evaluation of identical raw observations produces byte-identical aggregate, decision and human report,
  and tampered or incomplete inputs fail closed in automated tests.
- **SC-010**: Raw observations and generated reports contain zero absolute user paths, usernames, hostnames, source
  bodies, task text, credentials or raw exception strings.
- **SC-011**: Ruff, formatting, strict typing, all offline tests, build, repository validation and benchmark-specific
  drift validation pass before publication.
- **SC-012**: The final report gives one of the three declared decisions and clearly answers which tested workloads are
  worthwhile, where OpenARDP loses, and which conclusions remain unproven.

## Assumptions

- The current macOS machine is the binding reference environment for timing; shared CI validates semantics only.
- Synthetic reference and scale corpora are sufficient to test mechanical value but not enterprise generalization.
- Seven retained repetitions plus one warm-up balance uncertainty with a bounded local run time.
- The reference profile targets at least 10,000 blocks; the separate scale profile owns the 100,000-block PRD target.
- A 100-task break-even horizon is useful for a persistent evidence layer; failure to amortize within it is reported.
- Existing F015 security and release evidence remains authoritative for release readiness and is cited, not regenerated
  or weakened by this feature.
- Optional PDF model assets may not be present. Absence is a completeness limitation, not permission for network access.
