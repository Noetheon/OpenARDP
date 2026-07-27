# Context Compiler Requirements Checklist: Context Compiler and Selection Receipts

**Purpose**: Formal PR-review gate for completeness, clarity, consistency and
measurability of F008 budget, audit, privacy, replay and failure requirements
**Created**: 2026-07-26
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are task, corpus, budget, estimator, policy and limits all defined as required inputs? [Completeness, Spec §FR-001]
- [x] CHK002 Are exact snapshot resolution and historical replay semantics both specified? [Completeness, Spec §FR-002–FR-003]
- [x] CHK003 Are text and rich candidate sources covered without requiring a provider-specific model? [Completeness, Spec §FR-004–FR-006]
- [x] CHK004 Are selected, omitted, rejected and stale outcomes all defined as distinct exhaustive inventories? [Completeness, Spec §FR-012–FR-014]
- [x] CHK005 Are public bundle, receipt, CAS and catalog outputs all stated explicitly? [Completeness, Spec §FR-013, §FR-017]
- [x] CHK006 Are human and machine CLI flows plus replay and receipt inspection specified? [Completeness, Spec §FR-023; US4]

## Requirement Clarity

- [x] CHK007 Is “deterministic” reduced to a total order and exact semantic inputs rather than left subjective? [Clarity, Spec §FR-007, §FR-016]
- [x] CHK008 Is the budget scope explicit about full bundle bytes, response reserve and receipt exclusion? [Clarity, Spec §FR-009]
- [x] CHK009 Are high-value evidence and visual escalation rules tied to documented modes/evidence types? [Clarity, Spec §FR-011, §FR-014]
- [x] CHK010 Is “privacy-conscious” defined by an explicit receipt/log/error denylist? [Clarity, Spec §FR-013–FR-014, §FR-022]
- [x] CHK011 Are replay mismatch dimensions and no-fallback behavior named exactly? [Clarity, US2/AC3; Spec §FR-003, §FR-020]
- [x] CHK012 Are candidate and object verification boundaries distinguished from accelerator discovery? [Clarity, Spec §FR-005–FR-006]

## Requirement Consistency

- [x] CHK013 Do exact-current initial compilation and exact-historical replay requirements avoid contradictory freshness semantics? [Consistency, Spec §FR-002–FR-003]
- [x] CHK014 Do receipt privacy requirements remain consistent with complete auditability and policy disclosure? [Consistency, Spec §FR-013–FR-015]
- [x] CHK015 Do ContextBundle compatibility and the new independent receipt contract agree across spec, plan and contract? [Consistency, Spec §Compatibility; Plan §Contract Impact]
- [x] CHK016 Do model-free selection requirements align with all non-goals and assumptions? [Consistency, Spec §FR-004; Non-Goals]
- [x] CHK017 Do atomicity, idempotency and unreachable-CAS rollback requirements agree? [Consistency, Spec §FR-017–FR-019]

## Acceptance Criteria Quality

- [x] CHK018 Can stable replay be measured byte-for-byte across an explicit repeat count? [Measurability, Spec §SC-002]
- [x] CHK019 Can zero budget overflow be proven at exact-fit and one-unit-overflow boundaries? [Measurability, Spec §SC-003]
- [x] CHK020 Can decision inventory exhaustiveness be measured for every discovered subject? [Measurability, Spec §SC-004]
- [x] CHK021 Can receipt/log/error body leakage be tested as an exact zero-occurrence outcome? [Measurability, Spec §SC-005]
- [x] CHK022 Are integrity and failure criteria quantified as zero unverifiable returns and zero partial compilations? [Measurability, Spec §SC-006–SC-007]
- [x] CHK023 Are compatibility and cross-platform quality outcomes objectively bounded? [Measurability, Spec §SC-010–SC-012]

## Scenario and Edge-Case Coverage

- [x] CHK024 Are primary mixed text/rich, budget-constrained and missing-evidence flows covered? [Coverage, US1]
- [x] CHK025 Are audit, repeat, replay, head-change and version-mismatch flows covered? [Coverage, US2]
- [x] CHK026 Are index, CAS, catalog, trust, scope, stale, publication and cancellation failures covered? [Coverage, US3]
- [x] CHK027 Are empty, no-match, tiny-budget, duplicate, maximum-cap and exact-boundary cases addressed? [Coverage, Edge Cases]
- [x] CHK028 Are visual and numeric evidence requirements addressed without leaking F011 or generated-summary scope? [Coverage, Spec §FR-011]
- [x] CHK029 Are before-retrieval, during-verification, post-CAS and pre-commit cancellation points specified? [Coverage, Edge Cases]

## Security, Privacy and Operational Requirements

- [x] CHK030 Is document/task content consistently classified as data with no path, URL, import, policy or tool authority? [Security, Spec §FR-010]
- [x] CHK031 Are trust promotion, sensitivity limits and stale assertion handling explicitly fail-closed? [Security, Spec §FR-012]
- [x] CHK032 Are resource dimensions and accepted caps documented for corpus, discovery, bodies, decisions and bundles? [Operational, Spec §FR-008; Research §Limits]
- [x] CHK033 Are cancellation, retry, migration and rollback requirements present for every mutation boundary? [Recovery, Spec §FR-018–FR-021]
- [x] CHK034 Are network, cloud, provider and arbitrary-filesystem exclusions unambiguous? [Security, Spec §FR-024]

## Dependencies, Assumptions and Traceability

- [x] CHK035 Are F005 index authority, F007 rich evidence, F009 MCP, F011 visuals and F013 retention boundaries explicit? [Dependency, Spec §Assumptions/Non-Goals]
- [x] CHK036 Are contract, application, workspace, provider and export version impacts separated? [Compatibility, Spec §Compatibility]
- [x] CHK037 Is the conservative token-estimator assumption documented without an accuracy overclaim? [Assumption, Spec §Assumptions]
- [x] CHK038 Does every public-contract addition require schema, fixtures, vectors, compatibility and migration evidence? [Traceability, Spec §FR-027–FR-028]
- [x] CHK039 Are all four user stories independently testable and mapped to measurable outcomes? [Traceability, Spec §User Scenarios; §Success Criteria]
- [x] CHK040 Are remaining model ranking, visual production, MCP, scheduler, DAG and export behaviors explicitly excluded? [Boundary, Spec §Non-Goals]

## Notes

- All 40 requirement-quality checks pass before task generation.
- The checklist evaluates requirements writing, not implementation behavior.
