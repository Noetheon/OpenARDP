# Lexical Search Safety Requirements Checklist

**Purpose**: Formal review of F005 requirement completeness, clarity, consistency, measurability and security boundaries
**Created**: 2026-07-22
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are migration, fail-closed history validation and FTS5 capability obligations defined? [Completeness, Spec FR-001/FR-015; Research Decision 6]
- [x] CHK002 Are atomic READY/index visibility and rollback requirements complete? [Completeness, Spec FR-002; Plan Atomic index population]
- [x] CHK003 Are verified-evidence indexing, source-path exclusion and pre-feature backfill requirements complete? [Completeness, Spec FR-003/FR-004; Contract Index lifecycle]
- [x] CHK004 Are all three drift classes (missing/orphaned/stale) with detection, refusal and repair requirements defined? [Completeness, Spec FR-005; Research Decision 5]
- [x] CHK005 Are grammar, ranking, hit-content, scope, filter and bound requirements complete? [Completeness, Spec FR-006–FR-013]
- [x] CHK006 Are concurrency, trust, diagnostics, test and scope-bounding obligations present? [Completeness, Spec FR-014–FR-019]
- [x] CHK007 Are the `search` and `reindex` CLI surfaces fully specified with arguments and defaults? [Completeness, Clarifications; Contract CLI contract]

## Requirement Clarity

- [x] CHK008 Is "exact" matching pinned to tokenizer-exact semantics (case-folded, diacritic-preserving, no stemming/prefix)? [Clarity, Research Decision 3; Contract Query grammar]
- [x] CHK009 Is the deterministic total ranking order stated with an explicit tie-break? [Clarity, Spec FR-007; Contract Ranking and result]
- [x] CHK010 Are snippet origin (verified CAS block), bound (≤ 240 escaped chars) and body-exclusion precise? [Clarity, Spec FR-008; Research Decision 2]
- [x] CHK011 Is default current-head scope distinguished from explicit history and exact-version selection? [Clarity, Spec FR-009/FR-010; Contract Scope and filter]
- [x] CHK012 Are page/slide no-match semantics for line-based text stated without silent broadening? [Clarity, Spec FR-011; Assumptions]
- [x] CHK013 Is the document filter's UUID-or-path resolution precedence defined? [Clarity, Clarifications; Contract Scope and filter]
- [x] CHK014 Are result-limit default (20) and range (1–100) quantified? [Clarity, Spec FR-013; Clarifications]

## Requirement Consistency

- [x] CHK015 Do index-on-commit, cache-hit-no-reindex and head-move-only-rescope align across spec, plan and contract? [Consistency, Spec FR-002; Research Decision 4; Contract Index lifecycle]
- [x] CHK016 Does the contentless table choice align with the F004 "no bodies in SQLite" rejection? [Consistency, Research Decision 1; Plan Index storage]
- [x] CHK017 Do coverage refusal (search) and verified repair (reindex) refer to the same structural coverage definition? [Consistency, Spec FR-005; Contract Index lifecycle]
- [x] CHK018 Do exit classifications for new search errors align with the shared F004 scheme? [Consistency, Contract Error contract; Contract CLI contract]
- [x] CHK019 Do spec out-of-scope items match the plan's rejected alternatives? [Consistency, Spec Out of Scope; Plan Rejected Alternatives]

## Acceptance Criteria Quality

- [x] CHK020 Are hit correctness, determinism repetitions and concurrency mixture bounds measurable? [Measurability, Spec SC-001/SC-002]
- [x] CHK021 Are superseded-exclusion, fault-injection and drift-detection rates quantified? [Measurability, Spec SC-003/SC-004]
- [x] CHK022 Are backfill idempotency and evidence byte-identity objectively verifiable? [Measurability, Spec SC-005]
- [x] CHK023 Are rejection corpus, CLI envelope and cross-platform gates measurable? [Measurability, Spec SC-006–SC-008]

## Scenario Coverage

- [x] CHK024 Are primary flows (first ingest searchable, term/phrase retrieval, filters) covered? [Coverage, Spec US1–US3]
- [x] CHK025 Are alternate flows (history opt-in, document scoping, truncation) covered? [Coverage, Spec US3]
- [x] CHK026 Are exception flows (malformed queries, unknown scopes, missing capability, uncovered scopes) covered? [Coverage, Spec US4; Edge Cases]
- [x] CHK027 Are recovery flows (index fault rollback, drift rebuild, idempotent reindex) covered? [Coverage, Spec US1; Research Decision 5]

## Edge Case Coverage

- [x] CHK028 Are operator lookalikes, punctuation, Unicode and zero-token queries addressed? [Edge Case, Spec Edge Cases; Research Decision 3]
- [x] CHK029 Are concurrent ingest/search and mid-query head movement addressed? [Edge Case, Spec FR-014; Research Ranking notes]
- [x] CHK030 Are empty documents, whitespace-only blocks and only-superseded matches addressed? [Edge Case, Spec Edge Cases]
- [x] CHK031 Are limit boundaries, long-line snippets and Unicode snippet bounds addressed? [Edge Case, Spec Edge Cases; Data Model SearchHit]

## Non-Functional Requirements

- [x] CHK032 Are injection resistance (grammar + quoting + bound parameter) and logging minimization specified? [Non-Functional, Spec FR-006/FR-016/FR-017; Plan Security]
- [x] CHK033 Is performance honesty (bounded reads, no unmeasured latency claim, F013 owns benchmark) specified? [Non-Functional, Spec Assumptions; Plan Technical Context]
- [x] CHK034 Are offline determinism and cross-platform capability fail-closed behavior specified? [Non-Functional, Spec FR-015/FR-018/SC-008]

## Dependencies & Assumptions

- [x] CHK035 Are F001–F004 convergence dependencies and the mandated FTS5 mechanism documented? [Dependency, Spec Dependencies; Spec Assumptions]
- [x] CHK036 Is the contentless-shadow-table inventory assumption pinned for empirical verification? [Assumption, Research Decision 6; Data Model revision 4]

## Ambiguities & Conflicts

- [x] CHK037 No [NEEDS CLARIFICATION] markers remain; clarification answers are integrated into FR-004/FR-006/FR-010/FR-012/FR-013. [Ambiguity, Spec Clarifications]
- [x] CHK038 No conflict between progressive disclosure (Article VI) and snippet return: snippets are the documented bounded exception with bodies still requiring `get`. [Conflict, Spec Assumptions; Contract Ranking and result]
