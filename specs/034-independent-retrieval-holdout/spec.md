# Feature Specification: Independent Retrieval Holdout

**Feature Branch**: `codex/f034-independent-retrieval-holdout`

**Created**: 2026-08-09

**Status**: Complete

**Governance Tier**: high-assurance

**Input**: Freeze an independent holdout before profiling or retrieval optimization and measure the current product once.

## User Scenarios & Testing

### User Story 1 - Reproduce an independent frozen corpus (Priority: P1)

A maintainer can regenerate the exact holdout from one pinned external XQuAD revision and verify every derived byte,
license notice, source mapping and identity without trusting a network response at benchmark time.

**Why this priority**: A locally invented or post-tuning question set cannot provide independent product evidence.

**Independent Test**: Regenerate from the reviewed upstream snapshot into a fresh directory and compare its complete
manifest and payload bytes to the committed holdout.

**Acceptance Scenarios**:

1. **Given** the pinned English, German and Spanish XQuAD files, **when** generation runs, **then** exactly 20 Markdown
   source documents and 100 ordered questions are reproduced byte-for-byte.
2. **Given** any upstream, corpus, question, license or manifest drift, **when** verification runs, **then** it fails closed
   with a body-free category.

---

### User Story 2 - Measure an untuned multilingual baseline (Priority: P1)

A maintainer can compare the current F027 lexical and F029 hybrid-semantic profiles against the frozen holdout in two fresh
offline workspaces and receive exact quality, abstention, citation and runtime results.

**Why this priority**: The existing 19-question set has become a development set and cannot establish generalization.

**Independent Test**: Run both profiles twice, verify oracle coverage and deterministic semantic projections, publish
body-free evidence atomically, and independently recompute the summary and verdict.

**Acceptance Scenarios**:

1. **Given** the reviewed local E5 bundle, **when** the baseline runs, **then** it evaluates 200 treatment rows per fresh
   run over English, German, Spanish, multi-source and unsupported strata.
2. **Given** quality below predeclared absolute targets, **when** evidence validates, **then** publication still succeeds
   with an explicit below-target verdict rather than weakening thresholds.

---

### User Story 3 - Protect holdout independence (Priority: P1)

A future optimizer can use F025 for development while F034 remains a milestone-only validation set whose questions,
answers, corpus and thresholds never change in response to measured results.

**Why this priority**: Repeated tuning against the holdout would convert it into another development benchmark.

**Independent Test**: Repository contracts bind all frozen input identities and prohibit threshold overrides or result-led
regeneration.

**Acceptance Scenarios**:

1. **Given** a later optimization feature, **when** it changes retrieval behavior, **then** F034 inputs remain byte-identical
   and the candidate is first tuned against F025.
2. **Given** a need for a materially different holdout, **when** approved, **then** it receives a new version and retains
   the old results rather than overwriting v0.1.0.

### Edge Cases

- Parallel XQuAD languages disagree on title, paragraph or QA identifiers: generation fails before output.
- An answer span is absent from the English corpus document: oracle verification fails before retrieval.
- A negative question's source accidentally enters the selected corpus: generation fails.
- A result contains question, body, path, hostname or username fields: validation rejects it.
- Model identity, provider recipe or semantic projections differ across fresh runs: validity fails independently of quality.

## Requirements

### Functional Requirements

- **FR-001**: The holdout MUST be derived deterministically from XQuAD commit
  `7d30520c717524000f0d9d2f9c10a069acd9d285` under CC BY-SA 4.0 with exact upstream digests.
- **FR-002**: The corpus MUST contain exactly 20 English Markdown documents selected by a documented SHA-256 seed.
- **FR-003**: The question set MUST contain exactly 100 ordered questions: 30 English direct, 20 German cross-language,
  20 Spanish cross-language, 10 English source-discrimination, 10 English multi-source and 10 unsupported mixed-language.
- **FR-004**: Every answerable atom MUST occur in its declared authoritative corpus source; every unsupported question's
  upstream source MUST be absent from the corpus.
- **FR-005**: Generator and verifier MUST reject duplicate JSON members, symlinks, path escape, identity drift, source
  mismatch, missing attribution and unexpected inventory.
- **FR-006**: Baseline execution MUST use unchanged F027 lexical and F029 v0.3 hybrid-semantic policies with the exact local
  E5 provider identity; no query rewriting or answer generation is allowed.
- **FR-007**: Two fresh workspaces MUST produce identical timing-independent semantic rows for each treatment.
- **FR-008**: Results MUST retain per-treatment full support, atom recall, source recall, evidence precision, MRR, citation
  integrity, unsupported abstention and English/German/Spanish/stratum slices plus wall/CPU/provider metrics.
- **FR-009**: Absolute targets MUST be frozen before execution at full support 80%, atom recall 90%, source recall 90%,
  precision 60%, MRR 80%, citation integrity 100%, unsupported abstention 80% and German/Spanish atom recall 50%.
- **FR-010**: Validity and quality MUST be separate verdict axes so unfavorable valid evidence remains publishable.
- **FR-011**: Published files MUST be body-free, bounded, manifest-last and independently recomputable.
- **FR-012**: F034 inputs MUST be milestone-only and MUST NOT be changed or used as the iterative tuning set.

### Non-Goals and Compatibility Impact

- **Non-goal**: Change ranking, caching, context compilation, providers or product interfaces.
- **Non-goal**: Profile internal phases, optimize latency or evaluate generated answers; these are later work packages.
- **Compatibility impact**: Additive maintainer evidence only. No application, workspace, schema, provider-profile or export
  profile version changes.

## Key Entities

- **Upstream lock**: Exact XQuAD revision, file digests, URLs, license and deterministic selection seed.
- **Holdout corpus**: Twenty derived Markdown documents with stable source keys and payload hashes.
- **Question set**: One hundred external or mechanically composed records with source-bound support atoms.
- **Baseline evidence**: Body-free rows, exact summaries, dual verdict and checksummed run manifest.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Independent regeneration reproduces 20 documents, 100 questions and all declared identities byte-for-byte.
- **SC-002**: Coverage is exactly 80 answerable single-source, 10 answerable multi-source and 10 unsupported questions,
  across 50 English, 25 German and 25 Spanish queries.
- **SC-003**: Both treatments cover all 100 questions twice with no missing/duplicate row, citation mismatch or body leak.
- **SC-004**: Independent validation recomputes every metric and both verdict axes from raw rows and frozen inputs.
- **SC-005**: Complete repository gates pass without changing any F025/F029 input or lowering an existing threshold.

## Assumptions

- XQuAD's professional German and Spanish translations are suitable for cross-language retrieval evaluation against the
  aligned English contexts.
- The public XQuAD test set is externally sourced and frozen before F035 optimization; it is not secret and independence
  depends on milestone-only use rather than access control.
- F025 remains the iterative development/control set for the subsequent optimization feature.
