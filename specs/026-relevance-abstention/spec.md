# Feature Specification: Minimum Relevance and Explicit Abstention

**Feature Branch**: `codex/f026-relevance-abstention`

**Created**: 2026-08-03

**Status**: Implemented

**Input**: Add a minimum relevance floor and genuine evidence abstention as the first remediation from F025.

## Clarifications

### Session 2026-08-03

- Q: What counts as abstention? → A: The context result contains no selected evidence and carries a stable body-free
  notice that no candidate met the declared relevance policy; an empty result caused by corruption or resource failure
  is not relabelled as abstention.
- Q: May the relevance rule use F025 answers, support atoms or expected sources? → A: No. It uses only the submitted
  task, verified candidate content and a predeclared deterministic policy.
- Q: Does this feature also rewrite, translate or semantically expand the task? → A: No. The task remains byte-for-byte
  unchanged. Provider-neutral and multilingual query planning is reserved for F029.
- Q: Does this feature include ranking diversity, source quotas or CSV? → A: No. Those are separately governed F027
  and F028 slices.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abstain Instead of Returning Weak Evidence (Priority: P1)

As a local evidence consumer, I receive an explicit abstention when no verified candidate is sufficiently related to my
task, rather than a large context bundle whose incidental words create false confidence.

**Why this priority**: F025 selected evidence for both intentionally unsupported questions and therefore demonstrated
that bounded output alone is not a relevance control.

**Independent Test**: Submit the two frozen unsupported F025 questions and synthetic unrelated tasks against a populated
workspace; each returns no selected evidence, a stable abstention notice and no integrity failure.

**Acceptance Scenarios**:

1. **Given** a valid corpus and a question with only incidental lexical overlap, **When** context is compiled, **Then**
   no evidence is selected and the result explicitly records relevance abstention.
2. **Given** an empty match set, **When** context is compiled, **Then** the same abstention is reported deterministically.
3. **Given** corrupt, stale or unverifiable evidence, **When** compilation fails closed, **Then** the failure remains an
   integrity failure and is never presented as a safe abstention.

---

### User Story 2 - Preserve Strong Exact Evidence (Priority: P1)

As an evidence consumer, I continue to receive exact source-backed context when meaningful task terms strongly match
verified evidence.

**Why this priority**: A threshold that removes false positives by discarding useful evidence would not improve the
product.

**Independent Test**: Re-run every F025 direct question that previously had full support and require identical atom and
source support with complete citation integrity.

**Acceptance Scenarios**:

1. **Given** a task with strong exact evidence, **When** relevance is evaluated, **Then** supported candidates remain
   eligible and retain exact provenance and citation resolution.
2. **Given** multiple candidates with different degrees of overlap, **When** the floor is applied, **Then** every retained
   and rejected candidate is classified using the same frozen policy.

---

### User Story 3 - Audit and Reproduce the Decision (Priority: P2)

As an evaluator, I can identify the exact relevance-policy version and distinguish candidates rejected for insufficient
relevance from trust, freshness, integrity or budget outcomes.

**Why this priority**: Relevance is a derived heuristic and must never masquerade as source truth.

**Independent Test**: Compile and replay the same task in two fresh workspaces and compare policy identity, candidate
partition, abstention state, selected evidence identities and ordering.

**Acceptance Scenarios**:

1. **Given** identical task, evidence and policy, **When** compilation is repeated, **Then** relevance classifications,
   context and receipt identities are identical.
2. **Given** a candidate below the floor, **When** the receipt is inspected, **Then** it has one stable relevance rejection
   reason and cannot also appear as selected, omitted or stale.

### Edge Cases

- Punctuation-only and stopword-only tasks cannot manufacture meaningful relevance.
- Exact identifiers, dates, acronyms and short high-information tokens remain eligible without requiring long prose.
- Repeated occurrences cannot alone compensate for missing task coverage.
- Trust or sensitivity rejection takes precedence over relevance and retains its original reason.
- Candidate truncation cannot be reported as confident abstention unless all evaluated candidates are below the floor
  and the result discloses truncation.
- Relevance evaluation never reads unverified index bodies or changes evidence content, trust or provenance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST apply one versioned deterministic minimum-relevance policy before context budget selection.
- **FR-002**: The policy MUST use only the exact task and verified candidate evidence available to the product path.
- **FR-003**: Benchmark questions, answers, support atoms, expected sources and source-fitness labels MUST be inaccessible
  to runtime relevance evaluation.
- **FR-004**: The policy MUST define bounded task normalization, informative-term classification, candidate coverage and
  an integer comparison that does not depend on floating-point rounding.
- **FR-005**: A candidate below the policy floor MUST be placed exactly once in the rejected receipt partition with a
  stable insufficient-relevance reason.
- **FR-006**: When no candidate survives relevance and no integrity/configuration/resource failure occurred, the context
  bundle MUST select zero evidence and both bundle and receipt MUST expose a stable body-free abstention notice.
- **FR-007**: Integrity, trust, sensitivity, freshness, cancellation, configuration and resource-limit failures MUST NOT
  be converted into relevance abstention.
- **FR-008**: Relevance is a disposable retrieval heuristic and MUST NOT change original bytes, content identities,
  trust labels, source attribution or authoritative catalog facts.
- **FR-009**: The exact relevance-policy identity and floor MUST be bound into the context algorithm identity so persisted
  receipts are reproducible and incompatible policies cannot replay silently.
- **FR-010**: Existing legacy lexical behavior MUST remain constructible under its previous explicit algorithm identity
  for historical receipt verification; the improved policy is used only when deliberately composed.
- **FR-011**: Selection and rejection ordering MUST remain deterministic across platforms and fresh workspaces.
- **FR-012**: Unit tests MUST cover score boundaries, identifiers, acronyms, dates, stopwords, repetition, punctuation,
  Unicode, trust precedence and truncated discovery.
- **FR-013**: Integration tests MUST prove abstention, strong-evidence retention, exact CAS verification and replay.
- **FR-014**: F026 MUST rerun an unchanged, identity-verified F025 comparison slice without modifying questions, operator
  terms, support atoms, thresholds or corpus bytes.
- **FR-015**: F027 ranking/diversity, F028 CSV and F029 translation/semantic providers MUST remain unimplemented here.
- **FR-016**: Full local lint, formatting, strict typing, tests, build, independent repository validation and Spec-Kit
  convergence MUST pass before publication.

### Non-Goals and Compatibility Impact

- **Non-goal**: Candidate reranking, round-robin diversification or per-source quotas.
- **Non-goal**: CSV ingestion, conversion or benchmark substitution.
- **Non-goal**: Translation, stemming, fuzzy matching, embeddings, rerankers, LLMs or network providers.
- **Compatibility impact**: Additive experimental application behavior and algorithm profile. Original schemas, content
  identities, workspace format, parser/provider profiles and export profiles remain unchanged. Historical persisted
  receipts retain their recorded algorithm identity.

### Key Entities

- **Relevance Policy**: Versioned normalization, informative-term and integer-floor rules used for one compilation.
- **Relevance Observation**: Body-free task coverage and decision facts for one verified candidate.
- **Relevance Rejection**: Exhaustive receipt decision stating that a candidate did not satisfy the policy floor.
- **Evidence Abstention**: Successful zero-selection result explicitly stating that no evaluated candidate was relevant
  enough; distinct from all failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both unchanged F025 unsupported questions abstain in two fresh executions, yielding 100% unsupported-question
  abstention with zero selected evidence.
- **SC-002**: All six F025 direct questions previously carrying full support retain full atom/source support and 100%
  citation integrity.
- **SC-003**: Synthetic boundary vectors immediately below, at and above the floor produce the declared rejection or
  retention outcome with zero cross-platform disagreement.
- **SC-004**: Two fresh executions produce byte-identical semantic result projections, algorithm identity, candidate
  partitions, notices and selected evidence ordering.
- **SC-005**: Every selected item and every relevance-rejected item resolves to verified authoritative content; zero
  index-only bodies or benchmark-oracle facts enter the decision.
- **SC-006**: The unchanged F025 direct full-support rate does not fall below 35.2941%, direct atom recall does not fall
  below 32.6087% and citation integrity remains 100%.
- **SC-007**: The focused comparison finishes within five minutes and emits no source bodies, host paths, secrets or raw
  exceptions.
- **SC-008**: All repository quality gates pass with at least 85% branch coverage and no network-enabled unit tests.

## Assumptions

- F025 question, corpus and protocol identities remain frozen and available.
- The relevance floor is intentionally conservative; F027 will improve ordering and allocation after F026 proves safe
  abstention.
- Exact lexical evidence remains valuable for identifiers and dates, so short high-information tokens receive explicit
  treatment rather than being discarded as short words.
- No external model package or new dependency is needed for this feature.
