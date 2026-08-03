# Feature Specification: Lexical Ranking, Diversity and Source Quotas

**Feature Branch**: `codex/f027-lexical-ranking-diversity`

**Created**: 2026-08-03

**Status**: Implemented

## Clarifications

- A source quota is enforced per document scope, not per parser representation or filename.
- Diversification never manufactures evidence from a source that failed trust, freshness or F026 relevance checks.
- Exact duplicate evidence means identical CAS body identity; provenance is retained for the best-ranked eligible item.
- F025 corpus, questions, support atoms, expected sources and scoring protocol remain byte-for-byte unchanged.
- CSV and semantic or multilingual providers belong exclusively to F028 and F029.

## User Stories

### US1 - Strong evidence first (P1)

As an evidence consumer, I receive the most relevant verified lexical evidence before weaker matches.

**Independent test**: candidates with frozen relevance observations are ordered by relevance score, matched weight,
signal count, task coverage and occurrence count with stable source tie-breakers.

### US2 - Several useful sources survive (P1)

As an evidence consumer, one verbose document cannot consume the whole context while other relevant documents exist.

**Independent test**: eligible document queues are interleaved round-robin and no document contributes more than the
declared quota; weak or unavailable documents are never padded into the result.

### US3 - Reproduce and audit allocation (P2)

As an evaluator, I can distinguish duplicate and quota rejection from trust, freshness, relevance and budget outcomes.

**Independent test**: two fresh workspaces produce identical ordering, rejection reasons, source allocation, algorithm
identity, receipt and semantic result projection.

## Functional Requirements

- **FR-001**: Apply one immutable versioned lexical-allocation policy after F026 trust, freshness and relevance checks and
  before candidate/budget selection.
- **FR-002**: Rank only verified eligible candidates using integer F026 relevance facts and existing deterministic facts.
- **FR-003**: The total rank order MUST preserve preferred representation, lexical term coverage and occurrence strength,
  then use relevance score, matched weight, matched signals and stable source/evidence tie-breakers. This avoids penalizing
  focused answer blocks merely because a long natural-language task contains additional terms.
- **FR-004**: Reject later candidates with an already-retained exact CAS body identity as
  `duplicate_content_candidate`.
- **FR-005**: Preserve a canonical four-item global ranked prefix, then group remaining candidates by document scope and
  interleave nonempty document queues one item per round.
- **FR-006**: Reject eligible tail items beyond the immutable per-document quota as `source_quota_exceeded`.
- **FR-007**: Quotas MUST NOT reserve slots, add below-floor candidates or weaken trust/integrity rejection precedence.
- **FR-008**: Allocation decisions MUST be exhaustive, deterministic and body-free in persisted receipts.
- **FR-009**: Bind F026 and F027 policies into a new algorithm identity while retaining exact legacy and F026 identities.
- **FR-010**: Historical receipts MUST replay under their recorded profile without silent F027 substitution.
- **FR-011**: Runtime code MUST NOT import benchmark questions, answers, support atoms or expected sources.
- **FR-012**: Evaluate F026 and F027 against the same frozen F025 benchmark in two fresh workspaces.
- **FR-013**: Unsupported Q17/Q18 MUST continue to abstain with zero selected evidence.
- **FR-014**: Q02/Q03/Q06/Q13/Q14/Q19 MUST retain full atom/source support and citation integrity.
- **FR-015**: Direct precision, reciprocal rank and multi-source recall MUST not regress from the measured F026 profile.
- **FR-016**: CSV, stemming, fuzzy matching, translation, embeddings, rerankers, LLMs and network calls are excluded.
- **FR-017**: Full repository gates and Spec-Kit convergence MUST pass before merge.

## Edge Cases

- Visual handles without a body object are not content-deduplicated.
- Two provenance-distinct items with the same body retain only the higher-ranked item.
- Fewer than quota-many eligible items produces no quota rejection.
- A single eligible document may use the full bounded quota; the allocator does not fabricate diversity.
- Equal candidates remain deterministic across platforms, locale and fresh database identifiers.

## Success Criteria

- **SC-001**: Q17 and Q18 abstain in both fresh F027 executions.
- **SC-002**: All six frozen F026-positive questions retain full expected support and 100% citation integrity.
- **SC-003**: Q03 selects no more than 16 items from one document; after the four-item relevance-preserving prefix, every
  available eligible document is considered once before the next allocation round.
- **SC-004**: Direct evidence precision and mean reciprocal rank do not regress from the paired F026 baseline.
- **SC-005**: Multi-source source recall does not regress from the paired F026 baseline.
- **SC-006**: Two fresh F027 projections are byte-identical and contain no body text, host path or secret.
- **SC-007**: The paired benchmark completes in five minutes and the complete repository retains at least 85% coverage.

## Compatibility

This is an additive algorithm profile using existing receipt extension and rejection fields. It changes no source bytes,
persisted identifier algorithm, schema version, storage format, dependency or default network behavior.
