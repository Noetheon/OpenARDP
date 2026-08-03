# Requirements Quality Checklist: Relevance and Abstention Integrity

**Purpose**: Review whether F026 requirements are complete, unambiguous and measurable before implementation
**Created**: 2026-08-03

## Requirement Completeness

- [x] CHK001 Are genuine abstention and every excluded failure class explicitly distinguished? [Spec §FR-006–FR-007]
- [x] CHK002 Are both empty discovery and all-below-floor discovery covered? [Spec US1/AC1–AC2]
- [x] CHK003 Are relevance inputs bounded to task plus verified evidence with oracle inputs prohibited? [Spec §FR-002–FR-003]
- [x] CHK004 Are historical algorithm/replay expectations documented? [Spec §FR-009–FR-010]
- [x] CHK005 Are all later F027–F029 capabilities explicitly excluded? [Spec §FR-015, Non-Goals]

## Requirement Clarity

- [x] CHK006 Is the relevance floor defined as an integer decision without rounding ambiguity? [Spec §FR-004]
- [x] CHK007 Is a relevance rejection placed in exactly one exhaustive receipt partition? [Spec §FR-005]
- [x] CHK008 Is the precedence of trust, sensitivity, freshness and relevance clear? [Spec Edge Cases]
- [x] CHK009 Is `explicit abstention` observable in both bundle and receipt? [Spec §FR-006]
- [x] CHK010 Is the distinction between heuristic relevance and authoritative evidence explicit? [Spec §FR-008]

## Acceptance Criteria Quality

- [x] CHK011 Are unsupported-question abstention targets quantified against exact frozen rows? [Spec §SC-001]
- [x] CHK012 Is strong-evidence non-regression tied to named prior-success questions and citation integrity? [Spec §SC-002]
- [x] CHK013 Are below/at/above threshold boundaries objectively measurable? [Spec §SC-003]
- [x] CHK014 Is deterministic fresh-workspace reproduction measurable? [Spec §SC-004]
- [x] CHK015 Are privacy, timing and complete quality-gate outcomes bounded? [Spec §SC-007–SC-008]

## Scenario and Edge Coverage

- [x] CHK016 Are punctuation, stopwords, identifiers, dates, acronyms, repetition and Unicode addressed? [Spec Edge Cases; FR-012]
- [x] CHK017 Is truncated discovery prevented from implying undisclosed confidence? [Spec Edge Cases]
- [x] CHK018 Are index corruption and unverified-body authority explicitly prohibited? [Spec §FR-007–FR-008]
- [x] CHK019 Is a restrictive trust-only empty result kept distinct from relevance abstention? [Spec US1/AC3; US3/AC2]
- [x] CHK020 Is unchanged F025 input identity a binding anti-overfitting dependency? [Spec §FR-014]

## Notes

- Formal release-gate depth for PR reviewers; all 20 requirement-quality checks pass on 2026-08-03.
