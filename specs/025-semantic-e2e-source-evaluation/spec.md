# Feature Specification: Semantic End-to-End Source Evaluation

**Feature Branch**: `codex/f025-semantic-e2e-source-evaluation`

**Created**: 2026-08-02

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Test realistic semantic questions, evidence selection and source-quality evaluation end to end over F024.

## Clarifications

### Session 2026-08-02

- Q: Does “end to end” require OpenARDP to generate fluent answers with an LLM? → A: No. OpenARDP is the local document-
  intelligence and evidence layer. F025 evaluates question → ingestion → retrieval → bounded context → answer-support
  atoms → citations/source fitness. A generated prose answer would confound OpenARDP with an unpinned model and is
  therefore outside the binding claim.
- Q: May F025 add embeddings or rewrite questions after observing failures? → A: No. The delivered direct-question path
  is measured unchanged. A frozen operator-keyword treatment is reported separately as manual assistance, never as
  semantic retrieval. Optional semantic providers remain future product work.
- Q: How is source quality judged without claiming universal truth? → A: A question-specific rubric uses only retained
  facts: authoritative publisher, directness to the asked fact, temporal fit, exact integrity/provenance and reviewed
  reuse basis. It evaluates fitness as evidence for this question, not legal certainty, global truth or publisher
  endorsement.
- Q: Is the CISA CSV converted into a supported document to make coverage look complete? → A: No. Its locked row facts
  are valid oracle ground truth, but current stable product ingestion does not support CSV. The resulting coverage gap is
  retained in the decision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask Real Questions Against Exact Sources (Priority: P1)

As an evaluator, I can submit realistic questions and verify whether the exact F024 sources selected by OpenARDP contain
the evidence required to support a reference answer.

**Why this priority**: Structural parsing alone does not establish that retrieved evidence is useful for a real task.

**Independent Test**: Ingest the exact six-file corpus where supported, compile context for every frozen question with
sockets denied, and compare selected evidence against pre-run answer-support atoms and expected source roles.

**Acceptance Scenarios**:

1. **Given** a direct English factual question, **When** the product path runs, **Then** the result records support-atom
   coverage, relevant evidence rank, exact citation resolution and source fitness.
2. **Given** a paraphrase without exact answer wording, **When** direct-question retrieval runs, **Then** success or
   failure is retained without substituting a post-hoc keyword query.
3. **Given** a multi-source question, **When** context compiles, **Then** every required source and support atom must be
   present for a fully supported judgment.

---

### User Story 2 - Distinguish Semantic Ability from Manual Query Assistance (Priority: P1)

As a product owner, I can distinguish what OpenARDP achieves from an untouched natural-language question from what it
achieves only after a human supplies curated lexical terms.

**Why this priority**: Calling keyword overlap “semantic retrieval” would overstate the product and obscure the next
investment decision.

**Independent Test**: Run the same ground truth through direct-question and pre-frozen operator-keyword treatments and
report each metric and failure independently.

**Acceptance Scenarios**:

1. **Given** a frozen question, **When** direct and operator treatments execute, **Then** both use identical corpus,
   budget, candidate limits and evaluation rules; only the query text differs.
2. **Given** operator keywords improve retrieval, **When** results are reported, **Then** the improvement is labelled
   manual lexical assistance and cannot satisfy the full semantic-readiness gate.
3. **Given** a question in German against English sources, **When** it fails, **Then** no translation or hidden model call
   is introduced during the run.

---

### User Story 3 - Evaluate Citations and Source Fitness (Priority: P1)

As a reviewer, I can see whether selected evidence points to the expected authoritative source, resolves to exact
content and is appropriate for the time and claim in the question.

**Why this priority**: A plausible matching passage can still be indirect, stale for a current claim or drawn from a
license/readme rather than the underlying record.

**Independent Test**: Re-resolve every selected item from CAS/catalog evidence, map it to the locked F024 asset and apply
the frozen question-specific source rubric without trusting producer summaries.

**Acceptance Scenarios**:

1. **Given** selected evidence, **When** citation validation runs, **Then** source identity, evidence/block identity,
   anchor/provenance and retrieval bytes all verify exactly.
2. **Given** two publisher sources with different roles, **When** source fitness is judged, **Then** the directly relevant
   primary/data source outranks general repository or license material for the factual question.
3. **Given** a historical frozen source, **When** a question asks about that historical snapshot, **Then** it may be fit;
   the same source cannot silently establish a claim about the current live state.

---

### User Story 4 - Retain Unsupported and Unanswerable Cases (Priority: P1)

As a safety-conscious evaluator, I can detect when the product returns irrelevant context, cannot ingest a required
format or should abstain because the corpus does not support the question.

**Why this priority**: False confidence and concealed coverage gaps are more harmful than an honest negative result.

**Independent Test**: Include unsupported questions and CSV-dependent questions, then verify false-positive selection,
abstention and format-coverage failures affect the decision.

**Acceptance Scenarios**:

1. **Given** an unsupported question, **When** direct context compiles, **Then** irrelevant selected evidence counts as a
   false positive; an empty/explicit-missing result counts as abstention.
2. **Given** a CSV-dependent question, **When** the stable product path has no CSV ingestion adapter, **Then** the row is
   recorded as `unsupported_format` and no benchmark-only probe is presented as product support.
3. **Given** any runtime, integrity, resource or network failure, **When** evaluation completes, **Then** a stable
   body-free failure row is retained and the decision fails closed as specified.

---

### User Story 5 - Independently Reproduce the Semantic Decision (Priority: P1)

As an independent maintainer, I can recompute every aggregate and final decision from the frozen ground truth and raw
body-free observations without importing the producer or trusting report prose.

**Why this priority**: Semantic metrics are easy to manipulate through hidden judgments or changed thresholds.

**Independent Test**: Mutate question coverage, ranks, source roles, metrics, reports and result hashes one at a time and
verify the independent validator rejects each disagreement.

**Acceptance Scenarios**:

1. **Given** the committed result, **When** independent validation runs, **Then** question/treatment coverage, metrics,
   judgments, decision, report and file identities are regenerated exactly.
2. **Given** an unfavorable row, **When** it is deleted or relabelled, **Then** validation fails rather than recomputing a
   more favorable partial result.
3. **Given** unchanged inputs, **When** two fresh runs execute, **Then** all non-timing semantic judgments and identities
   are identical.

---

### User Story 6 - Make a Sustainable Product Decision (Priority: P2)

As the project owner, I receive a bounded `READY`, `CONDITIONALLY_READY` or `NOT_READY` outcome and a concrete capability
gap list rather than a marketing conclusion.

**Why this priority**: The benchmark should guide whether to invest in optional semantic retrieval, query assistance,
CSV support or source metadata—not reward the project for existing.

**Independent Test**: Apply the frozen policy to synthetic passing, conditional and failing raw fixtures and confirm that
the report preserves F015/F020/F024 history and states exactly what F025 changes or leaves unresolved.

**Acceptance Scenarios**:

1. **Given** strong direct-question, citation, source and abstention results across all required strata, **When** policy
   evaluates them, **Then** it emits `SEMANTIC_E2E_READY`.
2. **Given** only the manual operator treatment is strong or format/language gaps remain, **When** conditional thresholds
   are met, **Then** it emits `SEMANTIC_E2E_CONDITIONALLY_READY` with blockers.
3. **Given** neither direct nor assisted evidence support is adequate, **When** policy evaluates results, **Then** it emits
   `SEMANTIC_E2E_NOT_READY` and the project remains useful only for already-proven structural/exact workloads.

### Edge Cases

- Question words contain punctuation that the FTS tokenizer accepts but exact candidate rescoring does not.
- Common words create many high-occurrence irrelevant candidates and exhaust the context budget.
- The same answer phrase occurs in a table of contents, summary and substantive passage with different directness.
- A question needs two sources but the greedy budget admits repeated evidence from only one.
- An exact citation resolves while the selected passage does not support the claimed answer.
- A source is authoritative for a historical statement but stale for a present-tense operational statement.
- A reference answer atom spans two parser projections or appears with harmless whitespace/Unicode variation.
- An unsupported question happens to share generic vocabulary with many corpus blocks.
- German question terms do not overlap the English corpus.
- The PDF model bundle is absent/invalid, a rich pointer is bounded, or a worker attempts network access.
- The CSV oracle row exists but no stable OpenARDP CSV ingestion path exists.
- A producer could improve its score by omitting low-performing questions, treatments or selected irrelevant evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The benchmark MUST pin F024 corpus identity
  `sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd` and reject every changed asset,
  lock or evidence mapping before semantic execution.
- **FR-002**: Ground truth MUST be versioned, closed-schema, canonical and frozen before the binding run.
- **FR-003**: Ground truth MUST contain question ID, language, stratum, natural-language text, frozen operator terms,
  reference answer, support atoms, required/acceptable source roles, answerability and temporal scope.
- **FR-004**: The question set MUST cover direct facts, paraphrases, multi-source synthesis, source discrimination,
  unsupported questions and German cross-language prompts.
- **FR-005**: Every corpus format MUST be represented by at least one question or an explicit product-coverage row; CSV
  MUST remain an expected `unsupported_format` until a stable adapter exists.
- **FR-006**: Reference answers and support atoms MUST be human-reviewed against exact committed source bytes and MUST
  not rely on a live web page, model output or mutable external fact.
- **FR-007**: The binding run MUST use exact OpenARDP text/rich ingestion, CAS/catalog persistence, lexical candidates,
  context compilation and verified content resolution with sockets denied.
- **FR-008**: PDF execution MUST require and independently verify the exact external F023 bundle; other formats MUST NOT
  trigger model download or network access.
- **FR-009**: Direct treatment MUST pass the untouched frozen question as the context task. Operator treatment MUST use
  only pre-frozen lexical terms and be labelled manual assistance.
- **FR-010**: Direct and operator treatments MUST share corpus, source scopes, estimator, budget, limits and evaluation
  rules.
- **FR-011**: The benchmark MUST retain per-question/treatment selected evidence order, source asset keys, support-atom
  coverage, expected-source coverage, relevance labels, citation validity, failure category and bounded timings without
  retaining document bodies in results.
- **FR-012**: Every selected citation MUST be reverified through the product's exact object/catalog boundary and mapped
  to one locked source; unresolved, corrupt or mismatched evidence MUST fail the row.
- **FR-013**: Relevance MUST be computed from pre-frozen support atoms and source roles, not from producer-authored prose
  or a post-run model judgment.
- **FR-014**: Metrics MUST include answer-support recall, evidence precision, reciprocal rank, expected-source recall,
  citation integrity, full-support rate, abstention correctness and format/language/stratum coverage.
- **FR-015**: Source fitness MUST use a frozen question-specific rubric over publisher authority, directness, temporal
  fit, integrity/provenance and reviewed reuse basis; it MUST not claim legal advice, global truth or endorsement.
- **FR-016**: Unsupported questions MUST reward explicit no-evidence/missing-evidence outcomes and count irrelevant
  selected items as false positives.
- **FR-017**: A benchmark-only exhaustive oracle MUST prove ground-truth atoms exist in the locked corpus and provide an
  upper-bound coverage check; it MUST not be presented as OpenARDP product behavior.
- **FR-018**: All required questions and both product treatments MUST produce exactly one row, including failures; partial
  or duplicated coverage MUST invalidate the result.
- **FR-019**: Non-timing judgments MUST be deterministic across two fresh executions; timing remains descriptive and
  environment-bounded.
- **FR-020**: The policy thresholds, strata, budgets and required coverage MUST be committed before the binding run and
  MUST not be relaxed after observing results.
- **FR-021**: The decision MUST be one of `SEMANTIC_E2E_READY`, `SEMANTIC_E2E_CONDITIONALLY_READY` or
  `SEMANTIC_E2E_NOT_READY` and MUST fail closed on integrity, coverage, network or independent-validation failure.
- **FR-022**: Full readiness MUST depend on the direct natural-language treatment; operator-only success cannot satisfy
  it.
- **FR-023**: Conditional readiness MAY recognize strong operator-assisted evidence preparation only when citation
  integrity is complete and all remaining blockers are explicit.
- **FR-024**: Results MUST preserve unfavorable examples and capability gaps, including lexical/punctuation behavior,
  multilingual retrieval, CSV coverage, source discrimination and unanswerable false positives.
- **FR-025**: The independent validator MUST use standard-library code and MUST NOT import the producer or evaluator.
- **FR-026**: The independent validator MUST recompute closed coverage, row identities, aggregates, decision, report,
  manifest and every retained file hash.
- **FR-027**: Ordinary tests MUST use small redistributable fixtures, remain offline and not require the 384 MiB model
  bundle or full real corpus execution.
- **FR-028**: Raw and summarized results MUST prohibit absolute paths, usernames, hostnames, credentials, raw exceptions
  and full source/evidence bodies.
- **FR-029**: F015 `NO-GO`, F020 `CONDITIONALLY_WORTHWHILE` and F024 `REALWORLD_BASELINE_READY` MUST remain historical
  evidence; F025 MUST state precisely whether it changes only the semantic-quality assessment.
- **FR-030**: No embeddings, LLM provider, cloud default, persisted-identity change, schema-compatibility change or
  document-triggered tool authority may be added by this benchmark without separate feature/ADR governance.
- **FR-031**: Full local quality, build, independent validation and Spec-Kit convergence MUST pass before publication;
  GitHub runner-allocation billing failures MUST be retained separately from product/CI correctness.

### Key Entities

- **Semantic Question Set**: Frozen human-reviewed questions, strata, answer support and source expectations.
- **Support Atom**: Minimal exact source-backed fact fragment used to judge whether selected evidence can support an
  answer; not a generated answer score.
- **Question Treatment**: Direct natural-language or frozen manual operator-keyword input under otherwise identical
  product conditions.
- **Evidence Selection Observation**: Body-free selected order, source mapping, atom coverage, relevance, citation and
  timing facts for one question/treatment.
- **Source Fitness Judgment**: Question-specific, fact-bounded assessment of whether a source is appropriate evidence.
- **Semantic Evaluation Result**: Closed observations, summaries, decision, report and canonical result identity.

## Success Criteria *(mandatory)*

- **SC-001**: Ground truth covers every required stratum, both languages and all six formats/coverage states with zero
  missing, duplicate or post-run-mutated questions.
- **SC-002**: The exhaustive oracle finds 100% of required support atoms in their declared exact source assets before the
  product run is accepted.
- **SC-003**: Every non-CSV product source ingests offline and every selected item resolves to exact verified evidence;
  CSV is retained only as the declared unsupported product coverage row.
- **SC-004**: Two fresh executions produce identical question/treatment coverage, selected evidence identities/order,
  support judgments, citation judgments, aggregates and decision.
- **SC-005**: The independent validator regenerates 100% of row identities, metrics, source judgments, report and result
  identity with zero disagreement.
- **SC-006**: `SEMANTIC_E2E_READY` requires direct full-support rate ≥ 0.80, answer-support recall ≥ 0.90, evidence
  precision ≥ 0.60, reciprocal rank ≥ 0.80, expected-source recall ≥ 0.90, citation integrity = 1.00, supported-format
  coverage = 1.00, unsupported-question abstention ≥ 0.80 and German recall ≥ 0.50.
- **SC-007**: `SEMANTIC_E2E_CONDITIONALLY_READY` requires operator full-support rate ≥ 0.80, answer-support recall ≥ 0.90,
  expected-source recall ≥ 0.90 and citation integrity = 1.00, while direct full-support rate ≥ 0.40 and every direct,
  language, format and abstention blocker remains explicit.
- **SC-008**: Any lower result, integrity/coverage/network breach or oracle failure emits `SEMANTIC_E2E_NOT_READY`.
- **SC-009**: The binding run stays within 30 minutes, 4 GiB address space, 2 GiB workspace and 16 MiB result on the
  declared environment; no timing value is generalized beyond that run.
- **SC-010**: Result artifacts contain zero prohibited private/host-specific fields or complete source/evidence bodies.
- **SC-011**: Public documentation gives at least one representative success and failure per relevant treatment and
  converts each measured gap into a concrete, non-mandatory follow-up option.
- **SC-012**: All repository quality gates pass locally; available remote checks are reported exactly, and external
  billing refusal is never relabelled as green CI or used to weaken branch protection.

## Assumptions

- The binding environment still has the independently verified F023 bundle available outside Git.
- F024 source bytes and rights evidence are suitable for committing short reference answers/support atoms.
- English is the corpus language; German prompts deliberately test cross-language limitations rather than promise
  translation.
- The benchmark evaluates OpenARDP's evidence preparation, not factual correctness of an unpinned downstream LLM.

## Out of Scope

- Training, choosing or calling an embedding model, reranker, translator or answer-generating LLM.
- Creating a stable CSV ingestion API or converting the CSV into another format for a favorable product result.
- Live-current CISA operational advice or treating the frozen KEV snapshot as a current vulnerability feed.
- Human-subject source credibility research, legal advice, publisher endorsement or universal truth scoring.
- Changing stable public APIs or persisted identities solely to improve benchmark metrics.
