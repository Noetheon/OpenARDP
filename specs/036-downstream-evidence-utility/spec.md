# Feature Specification: Downstream Evidence Utility

**Feature Branch**: `codex/f036-downstream-evidence-utility`

**Created**: 2026-08-09

**Status**: Implemented

**Governance Tier**: high-assurance

**Input**: Prove whether the frozen retrieval profiles create useful, trustworthy evidence-review packets under a
bounded downstream task, without answer generation or holdout tuning.

## User Scenarios & Testing

### User Story 1 - Complete a bounded evidence-review task (Priority: P1)

A reviewer can assess whether a retrieval result contains all required supporting facts and sources within a fixed number
of progressively disclosed evidence items, while unsupported questions result in abstention rather than fabricated
support.

**Why this priority**: Retrieval metrics alone do not show whether a bounded consumer can finish a concrete evidence task.

**Independent Test**: Replay body-free F025 observations through a provider-free reviewer model at budgets 1, 3, 5, 10
and 64, independently recompute completion, atom/source coverage, citation integrity and review effort, and require exact
agreement with the published result.

**Acceptance Scenarios**:

1. **Given** an answerable question, **when** the reviewer reaches a budget, **then** completion is credited only when all
   required atoms and sources have appeared in citation-valid relevant evidence.
2. **Given** an unsupported question, **when** the producer reports explicit abstention with no selected evidence,
   **then** the downstream task is credited as safely completed; any selected evidence or missing abstention fails it.
3. **Given** a result that exposes question text, reference answers, document bodies or local paths, **when** validation
   runs, **then** publication fails closed.

---

### User Story 2 - Compare utility and time-to-ready fairly (Priority: P1)

A maintainer can determine whether F035 preserves or improves bounded downstream utility versus exact F029 while reducing
the retrieval delay before the review packet is ready.

**Why this priority**: A speed improvement is valuable only if the task result remains equally useful and trustworthy.

**Independent Test**: Compare the two counterbalanced F025 runs by exact question and run identity, require identical
utility projections across repeated runs, and calculate paired warm latency only over a predeclared population.

**Acceptance Scenarios**:

1. **Given** the frozen primary budget of three items, **when** F029 and F035 are compared, **then** F035 must not regress
   task completion, answerable completion, atom coverage, source coverage, source fitness, citation integrity or safe
   abstention.
2. **Given** the same warm-question population used by F035, **when** latency is compared, **then** F035 time-to-ready p50
   must remain at most 75% of F029 and p95 must be no worse; review time itself is not inferred from item count.
3. **Given** incomplete pairs, identity drift or non-deterministic timing-free projections, **when** validation runs,
   **then** no comparative verdict is published.

---

### User Story 3 - Test independent downstream generalization once (Priority: P1)

A reviewer receives one post-freeze F034 holdout evaluation of the same downstream method, including a negative result,
without changing the F034 questions, corpus, retrieval outputs or the method selected on F025.

**Why this priority**: A downstream method shaped after viewing the holdout would not provide independent evidence.

**Independent Test**: Bind the method and F025 decision in the protocol, then derive exactly one F034 evaluation from the
already frozen F035 observations and independently verify every aggregate from raw body-free rows.

**Acceptance Scenarios**:

1. **Given** the frozen protocol, **when** F034 is evaluated, **then** no budget, metric definition, threshold or retrieval
   parameter can change in response to the holdout result.
2. **Given** a valid holdout result below the development level or an unfavorable lexical/semantic comparison, **when**
   publication completes, **then** the result remains committed with a negative verdict and bounded claims.

### Edge Cases

- A question requires several atoms from one source: source coverage alone never substitutes for atom coverage.
- One evidence item covers multiple atoms: it counts once toward review effort and each unique atom at most once.
- A selected item is relevant but its citation is invalid: its atoms and source cannot contribute to trusted completion.
- A result contains more than 64 items: only the frozen prefix is evaluated and the observation remains bounded.
- Two repeated runs differ only in time: utility may remain deterministic; timing is summarized separately.
- F034 lacks an F029 baseline row in the F035 evidence: the validator uses the separately frozen F034 baseline evidence,
  never fabricates or relabels a treatment.

## Requirements

### Functional Requirements

- **FR-001**: The benchmark MUST consume only immutable body-free F034/F035 evidence and exact protocol identities; it
  MUST NOT invoke a parser, embedding provider, retrieval provider, answer generator or network service.
- **FR-002**: The downstream consumer MUST be implemented independently of retrieval ranking and MUST use only ordered
  selected-evidence facts available to a bounded evaluator.
- **FR-003**: The protocol MUST bind budgets `1, 3, 5, 10, 64`, primary budget `3`, completion semantics, warm-population
  semantics, input digests and every accepted producer/profile identity before F034 evaluation.
- **FR-004**: Trusted answerable completion at budget K MUST require every required atom and required source within the
  first K selected items, counting only relevant items with valid citations.
- **FR-005**: Safe unsupported completion MUST require explicit abstention and zero selected evidence.
- **FR-006**: Published metrics MUST separate answerable completion, unsupported abstention, atom coverage, source
  coverage, source fitness, citation validity, items inspected and retrieval time-to-ready; item count MUST NOT be
  converted into human duration or answer correctness.
- **FR-007**: F025 candidate acceptance MUST require non-regression at the primary budget for every utility/trust metric,
  deterministic timing-free projections across both runs, warm p50 at most 75% of F029 and warm p95 no worse.
- **FR-008**: The F034 holdout MUST be evaluated exactly once after protocol freeze; its validity and downstream outcome
  verdicts MUST remain separate, and an unfavorable valid result MUST be retained. Exact validator reconstruction and
  reproducibility reruns of the frozen package do not create a new decision or permit method changes.
- **FR-009**: The F034 comparison MUST retain exact treatment names from their authoritative inputs and MUST disclose
  when measurements came from different frozen benchmark packages rather than paired execution.
- **FR-010**: Results MUST be bounded, body-free, written atomically with the manifest last and independently validated
  without importing the producer or evaluator implementation.
- **FR-011**: The validator MUST reject duplicate JSON members, unexpected files, symlinks, absolute paths, body/question
  fields, unknown metrics, invalid arithmetic, duplicate question/treatment/run keys and input/protocol drift.
- **FR-012**: The report MUST state that this is a deterministic evidence-review proxy, not a human study, generated-answer
  evaluation, domain-readiness guarantee or universal quality claim.

### Non-Goals and Compatibility Impact

- **Non-goal**: Generate or grade natural-language answers, estimate human reading time, run a user study, tune retrieval,
  add a provider, persist embeddings or create a product API.
- **Non-goal**: Change F025/F034 fixtures, existing benchmark observations, runtime retrieval behavior or release status.
- **Compatibility impact**: Additive benchmark-only evidence contract. Application, public interchange schemas, workspace,
  provider-profile and export-profile versions remain unchanged.

### Key Entities

- **Review protocol**: Immutable method identity over inputs, budgets, completion rules and decision thresholds.
- **Review observation**: Body-free per-question result at each budget with coverage, trust, effort and completion facts.
- **Utility comparison**: Recomputed aggregate and verdict for exact treatments and runs.
- **Holdout evaluation**: One post-freeze downstream projection over unchanged independent evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of eligible questions have one independently validated review observation for every declared budget,
  treatment and run, with exact aggregate reconciliation.
- **SC-002**: At budget three, F035 preserves or improves every F029 F025 utility/trust metric and produces identical
  timing-free results in both fresh-workspace runs.
- **SC-003**: F035 warm retrieval time-to-ready p50 is at most 0.75 times F029 and warm p95 is no worse on the unchanged
  F035 warm population.
- **SC-004**: One protocol-frozen F034 downstream result is published with a valid positive or negative all-budget
  non-regression outcome versus exact F029 and no mutation to its authoritative evidence.
- **SC-005**: The independent validator reconstructs all observations, summaries and decisions without producer imports,
  and full repository gates pass.

## Assumptions

- F025 is the permitted development/control set; using it to choose the primary review budget does not create a holdout
  claim.
- Existing F034/F035 body-free observations are immutable, sufficient and cheaper to reuse than rerunning the model.
- Three evidence items are the primary budget because F025 reaches its first stable task-completion plateau there; the
  entire predeclared curve remains visible to prevent selective reporting.

## Clarification record

- **Q: Does deterministic evidence coverage prove that a human or LLM can answer correctly?**
  **A:** No. It proves only that a bounded, citation-valid review packet contains the benchmark's required support. A
  blinded human or fixed answer-generation study is a separate future boundary and must not be inferred here.
- **Q: Does independent validation violate the one-time holdout rule?**
  **A:** No. The rule allows one decision-bearing post-freeze projection. Validators and reproducibility runs may
  reconstruct that exact frozen projection, but cannot change the method, inputs, thresholds or published decision.
