# Feature Specification: Profiled Retrieval Optimization

**Feature Branch**: `codex/f035-profiled-retrieval-optimization`

**Created**: 2026-08-09

**Status**: Implemented

**Governance Tier**: high-assurance

**Input**: Profile the frozen F029 retrieval path, improve absolute retrieval quality and warm latency together on F025,
then run one milestone-only validation against the unchanged F034 holdout.

## User Scenarios & Testing

### User Story 1 - Explain retrieval cost by phase (Priority: P1)

A maintainer can reproduce a body-free phase profile that separates ingestion, corpus discovery and authority checking,
provider startup, passage preparation, query scoring, candidate admission, compilation and publication.

**Why this priority**: Optimization without attributed cost can move work between phases or improve an irrelevant total.

**Independent Test**: Run the frozen F029 profile on F025 in a fresh workspace, independently validate phase coverage and
arithmetic, and reconcile every phase with the measured end-to-end duration.

**Acceptance Scenarios**:

1. **Given** the unchanged F025 corpus, questions and F029 profile, **when** profiling runs, **then** every query and setup
   operation receives bounded monotonic phase observations whose totals reconcile without document bodies or local paths.
2. **Given** a missing, negative, overlapping or arithmetically inconsistent phase, **when** validation runs, **then** the
   evidence fails closed rather than publishing an optimization claim.

---

### User Story 2 - Improve quality and warm latency together (Priority: P1)

An operator who explicitly selects semantic retrieval receives a new exactly identified profile that returns more useful
evidence with less warm delay while the provider-free lexical default and historical replay remain unchanged.

**Why this priority**: Faster low-quality retrieval and slower high-quality retrieval are both product regressions.

**Independent Test**: Select the candidate only on repeated F025 development runs, compare it with exact F029 v0.3 in
counterbalanced fresh workspaces, and require every quality, trust, determinism and latency gate simultaneously.

**Acceptance Scenarios**:

1. **Given** an unchanged exact corpus snapshot within one compiler lifetime, **when** later semantic questions run, **then**
   reusable model-specific state is process-local and bounded, repeated full-body transfer is avoided, and every selected
   evidence object and security-sensitive catalog fact is reverified before delivery.
2. **Given** corpus, provider recipe, policy, limit or algorithm drift, **when** preparation or replay occurs, **then** the
   cache is invalidated or the request fails closed; no lexical fallback silently changes the requested profile.
3. **Given** paired F025 baseline and candidate runs, **when** the candidate is assessed, **then** full support, atom recall,
   source recall, evidence precision, MRR, German per-question support, citation integrity and unsupported abstention do not
   regress; at least one absolute quality metric improves strictly and candidate warm wall p50 improves by at least 25%
   with warm p95 no worse.

---

### User Story 3 - Validate generalization once (Priority: P1)

A reviewer receives one honest post-freeze result on the independent F034 holdout, including unfavorable results, without
changing its corpus, questions, targets or historical baseline.

**Why this priority**: F025 improvement alone can be overfitting and does not establish downstream generalization.

**Independent Test**: Freeze the complete candidate identity and decision thresholds, execute F034 once in two fresh
workspaces, and independently recompute quality, timing, identity and validity verdicts.

**Acceptance Scenarios**:

1. **Given** a frozen F025-selected candidate, **when** F034 validation begins, **then** no candidate parameter or decision
   threshold may change afterward in this feature.
2. **Given** a valid below-target or regressing holdout result, **when** publication completes, **then** it remains committed
   with an explicit negative verdict and no readiness claim.

### Edge Cases

- The prepared worker terminates, times out or loses its handle: fail closed and discard all process-local state.
- Two evidence records share an object body but have distinct evidence identities: preserve both identities while reusing
  only the model-specific body embedding.
- A catalog row or CAS object changes or becomes unverifiable after preparation: reject selected evidence before delivery.
- A workload has one question only: report cold behavior and mark warm evidence insufficient rather than inventing a gain.
- Timing noise reverses a claimed gain at p95: the joint optimization gate fails even if median improves.

## Requirements

### Functional Requirements

- **FR-001**: Profiling MUST use the unchanged F025 corpus/question/protocol identities and exact F029 v0.3 baseline.
- **FR-002**: Phase evidence MUST use monotonic durations, bounded body-free counters and independently checked arithmetic.
- **FR-003**: The candidate MUST be selected only with F025; F034 inputs and absolute targets MUST remain byte-identical.
- **FR-004**: Reusable semantic corpus state MUST remain optional, model-specific, bounded, process-local and disposable.
- **FR-005**: Prepared state MUST bind the ordered evidence/object identities, provider recipe and resource limits with a
  deterministic identity; no document body, embedding or universal-vector claim may be persisted.
- **FR-006**: Every selected candidate MUST be resolved and reverified against authoritative catalog and CAS records after
  accelerator lookup and before context delivery.
- **FR-007**: The new algorithm identity MUST bind preparation, admission and allocation behavior; legacy F029/F030 receipts
  MUST replay under their original identity and fail closed under mismatch.
- **FR-008**: F025 candidate quality MUST preserve or improve F029 full support, atom recall, source recall, evidence
  precision, MRR, German per-question support, 100% citation integrity and 100% unsupported abstention.
- **FR-009**: At least one of full support, atom recall, source recall, evidence precision or MRR MUST improve strictly.
  The report MUST retain the negative result that bounded floor/quota/Top-K variants could not produce the initially
  hypothesized 25% precision gain without protected-quality regression.
- **FR-010**: Across at least two counterbalanced fresh-workspace pairs, candidate warm wall p50 MUST be at most 75% of
  baseline and candidate warm p95 MUST be no slower than baseline; cold wall time and peak RSS MUST be disclosed.
- **FR-011**: Timing-independent candidate projections MUST be identical across fresh runs.
- **FR-012**: After candidate and thresholds freeze, F034 MUST run exactly once as this feature's milestone evaluation;
  validity and quality/performance verdicts MUST remain separate and unfavorable valid evidence MUST publish.
- **FR-013**: Results MUST be bounded, atomic, manifest-last and independently validated without importing the producer.
- **FR-014**: The provider-free lexical profile MUST remain the default and no cloud call, answer generation, persistent
  vector store or new embedding provider may be introduced.

### Non-Goals and Compatibility Impact

- **Non-goal**: Tune against F034, change F025/F034 answers, add query rewriting, generate answers or evaluate another model.
- **Non-goal**: Persist embeddings or prepared handles beyond the provider process; create a vector database.
- **Compatibility impact**: Add one experimental semantic algorithm/profile version and optional prepared-provider port.
  Application and public receipt schemas remain unchanged; workspace, export and persisted-identifier versions do not move.

### Key Entities

- **Phase observation**: Body-free operation, monotonic duration, count and reconciliation parent.
- **Prepared corpus handle**: Process-local opaque handle plus deterministic identity over exact ordered evidence facts.
- **Candidate profile**: Exact provider recipe, policy, limits, preparation mode, ranking and allocation identity.
- **Paired comparison**: Counterbalanced F025 baseline/candidate evidence with quality and latency ratios.
- **Holdout validation**: One post-freeze F034 result with independent validity and outcome verdicts.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Profiling accounts for 100% of declared setup/query phases with valid non-negative arithmetic.
- **SC-002**: Every protected F025 quality metric is non-regressing and at least one absolute metric improves strictly;
  rejected 25%-precision variants remain disclosed rather than being reclassified as successful.
- **SC-003**: F025 warm wall p50 is at most 0.75 times F029 and warm p95 is no worse in at least two counterbalanced pairs.
- **SC-004**: Selected evidence remains 100% citation-valid, authoritative-object verified and deterministic across runs.
- **SC-005**: One unchanged F034 milestone run publishes a valid positive or negative generalization result after freeze.
- **SC-006**: Full repository gates and independent benchmark validation pass with legacy replay compatibility intact.

## Assumptions

- F025 is intentionally the development/control set; repeated profiling and candidate comparison there is permitted.
- The reviewed local PDF and multilingual-E5 bundles remain available and sufficient; no dependency change is needed.
- Process-lifetime reuse is valuable for CLI/MCP servers and repeated benchmark questions but deliberately provides no
  cross-process warm-start guarantee.

## Clarification record

- **Q: What happens if the planned 25% precision gain requires losing relevant evidence?**
  **A:** The 25% hypothesis fails and remains negative evidence. Candidate selection may proceed only with a strict
  absolute quality improvement, complete protected-metric non-regression and the unchanged latency/trust gates. This
  clarification was recorded before the candidate identity and F034 milestone were frozen.
