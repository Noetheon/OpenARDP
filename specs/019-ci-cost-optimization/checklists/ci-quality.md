# CI Cost and Quality Requirements Checklist

**Purpose**: Unit-test the written F019 requirements for completeness, clarity, consistency and measurable quality
before tasks or workflow code exist.

**Created**: 2026-08-02

**Feature**: [spec.md](../spec.md)

## Final Quality Boundary

- [x] CHK001 Are all three supported platforms named and required for a final full-classified PR? [Completeness, FR-001]
- [x] CHK002 Is "complete test inventory" distinguished from coverage instrumentation? [Clarity, FR-002]
- [x] CHK003 Is exactly one authoritative coverage owner and its minimum threshold specified? [Measurability, FR-002]
- [x] CHK004 Are platform-independent gates enumerated and constrained to one execution? [Completeness, FR-003]
- [x] CHK005 Does the specification prohibit test-count, platform, coverage and supply-chain weakening as cost tactics?
  [Consistency, Non-Goals]
- [x] CHK006 Are network blocking and locked dependency semantics retained for every relevant lane? [Security, FR-010]

## Event and Classification Semantics

- [x] CHK007 Are draft, ready, governance-only, mixed, main-push and release events each covered? [Coverage, FR-004–009]
- [x] CHK008 Does Ready-for-Review trigger final validation without a new commit? [Clarity, FR-004]
- [x] CHK009 Is governance-only scope defined positively and narrowly rather than by file extension? [Clarity, FR-005]
- [x] CHK010 Are empty, malformed, traversal-shaped and unknown path sets explicitly fail-closed? [Edge Case, FR-005]
- [x] CHK011 Do workflow, policy, classifier, lock, source, test and schema changes force full validation? [Coverage, FR-006]
- [x] CHK012 Is job-level skipping required where workflow-level skipping would strand a required check? [Consistency,
  Assumptions]
- [x] CHK013 Is the post-merge `main` lane specified without duplicating the protected final matrix? [Clarity, FR-007]

## Release and Cache Safety

- [x] CHK014 Are manual, version-tag and release-owned ready-PR boundaries complete and mutually clear? [Coverage, FR-009]
- [x] CHK015 Is the unchanged three-platform release evidence plus aggregate gate required? [Consistency, FR-008]
- [x] CHK016 Are draft release PR and ordinary-main exclusions explicit? [Edge Case, FR-009]
- [x] CHK017 Is only the uv artifact cache allowed while environment caching is prohibited? [Security, FR-010]
- [x] CHK018 Must locked synchronization run even on a cache hit and rebuild safely on a miss? [Resilience, FR-010]

## Enforcement and Evidence

- [x] CHK019 Are action pinning, permissions, checkout credentials, timeouts and concurrency all normative? [Security,
  FR-011]
- [x] CHK020 Are stable required-check names and solo-safe branch protection defined? [Completeness, FR-012/015]
- [x] CHK021 Can deterministic tests reject each workflow/classification regression category? [Testability, FR-013]
- [x] CHK022 Are baseline date, prices, job rounding, model assumptions and invoice limitations required? [Evidence, FR-014]
- [x] CHK023 Is the 55 percent saving target tied to a documented comparable-activity model? [Measurability, SC-004]
- [x] CHK024 Are remote CI, merge and post-merge branch-protection observations required before completion? [Acceptance,
  SC-007/008]

## Scope and Governance

- [x] CHK025 Are product versions, schemas, identities, dependencies, release decision and egress explicit non-changes?
  [Scope, FR-016]
- [x] CHK026 Does the design preserve Constitution Articles VIII, IX and XI without an ADR exception? [Constitution]
- [x] CHK027 Are residual risks and protected rollback steps required rather than an absolute quality claim? [Evidence,
  FR-014]
- [x] CHK028 Is every requirement traceable to at least one acceptance scenario or measurable outcome? [Traceability]

## Notes

- Completed during `/speckit-checklist`. The requirements are sufficiently explicit to generate implementation tasks;
  no checklist item requires user clarification.
