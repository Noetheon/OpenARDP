# Requirements Checklist: Semantic Retrieval Product Surface

**Purpose**: Formal PR/release review of product-surface, authority, replay and operational-evidence requirements
**Created**: 2026-08-08

## Requirement Completeness

- [x] CHK001 Are CLI default, opt-in and replay requirements all explicitly defined? [Completeness, Spec §FR-001–FR-006]
- [x] CHK002 Are MCP startup authority, request selection and unavailable-capability behaviors defined? [Completeness, Spec §FR-007–FR-010]
- [x] CHK003 Are provider lifecycle and cleanup requirements stated for success, cancellation and failure? [Completeness, Spec §FR-010, Edge Cases]
- [x] CHK004 Are the operational producer, two-run evidence and independent validator requirements complete? [Completeness, Spec §FR-014–FR-017]

## Requirement Clarity

- [x] CHK005 Is the lexical default distinguished unambiguously from explicit semantic selection? [Clarity, Spec §FR-001]
- [x] CHK006 Is the all-or-none bundle/source-lock rule and lack of ambient discovery explicit? [Clarity, Spec §FR-002]
- [x] CHK007 Is “exact F029 profile” bounded by unchanged policy, limits, allocation and verification behavior? [Clarity, Spec §FR-003]
- [x] CHK008 Are cold, warm, cache reuse, peak RSS and deterministic projection defined as distinct measures? [Clarity, Spec §FR-014–FR-017]

## Requirement Consistency

- [x] CHK009 Do CLI and MCP requirements share the same profile semantics without sharing filesystem authority? [Consistency, Spec §FR-001, FR-008]
- [x] CHK010 Does semantic replay identity align with the existing receipt algorithm rather than a second persisted profile? [Consistency, Spec §FR-004–FR-005, Assumptions]
- [x] CHK011 Are the handle-first privacy requirements consistent with the existing explicit bundle opt-in? [Consistency, Spec §FR-011]
- [x] CHK012 Do performance gates avoid changing F029 relevance or quality claims? [Consistency, Spec §FR-014–FR-017]

## Scenario and Edge-Case Coverage

- [x] CHK013 Are missing, partial, drifted and mismatched provider configurations covered? [Coverage, Spec §SC-002, Edge Cases]
- [x] CHK014 Are provider-free semantic MCP rejection and subsequent lexical availability covered? [Coverage, Spec §SC-003]
- [x] CHK015 Are cancellation, disconnect, worker crash, timeout and malformed responses addressed? [Coverage, Edge Cases]
- [x] CHK016 Are abstention, tiny budget, corrupt CAS and changed source snapshots addressed? [Coverage, Edge Cases]

## Acceptance and Non-Functional Quality

- [x] CHK017 Are lexical compatibility and semantic replay outcomes objectively measurable? [Measurability, Spec §SC-001, SC-004]
- [x] CHK018 Are warm-cache and peak-memory gates numeric and platform-qualified? [Measurability, Spec §SC-005]
- [x] CHK019 Are privacy-forbidden outputs and validator tamper classes explicit? [Security, Spec §SC-002, SC-006]
- [x] CHK020 Are network, dependency, persistence, generation and vector-database exclusions explicit? [Boundary, Spec §FR-018–FR-019]
