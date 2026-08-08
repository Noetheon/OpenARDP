# Requirements Quality Checklist: Maintainability and Repository Integrity

**Purpose**: Challenge whether F031 requirements are complete, measurable and safe for formal release review
**Created**: 2026-08-08
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

## Repository safety requirements

- [x] CHK001 Does the specification distinguish detection, classification and deletion authority? [Completeness, FR-002–FR-008]
- [x] CHK002 Are ambiguous, newer, symlinked and missing-canonical candidates required to fail closed? [Coverage, Edge Cases]
- [x] CHK003 Are diagnostics constrained against bodies and absolute host facts? [Security, FR-003, Contract]
- [x] CHK004 Is the cleanup inventory time-bound and revalidation required immediately before mutation? [Assumption, FR-007]
- [x] CHK005 Is repository relocation explicitly excluded from implied authority? [Scope, FR-009]

## Refactoring quality requirements

- [x] CHK006 Are selected hotspots grounded in baseline measurements rather than code volume alone? [Traceability, Plan]
- [x] CHK007 Is observable behavior characterized before extraction across success, boundary and failure paths? [Coverage, FR-011]
- [x] CHK008 Does the metric resist moving complexity into a new oversized helper? [Measurability, FR-012–FR-013]
- [x] CHK009 Are public contracts, persistence, identity and architecture changes explicitly forbidden? [Compatibility, FR-001, FR-010]
- [x] CHK010 Is unrelated mechanical cleanup excluded? [Scope, FR-014]

## Completion claim requirements

- [x] CHK011 Are all ten “10/10” gates binary, independently observable and required together? [Measurability, SC-001–SC-010]
- [x] CHK012 Do local, coverage, build, drift and three-platform gates remain mandatory? [Completeness, FR-017–FR-019]
- [x] CHK013 Must unfavorable results and residual debt be disclosed? [Evidence, FR-020]
- [x] CHK014 Does the plan avoid claiming that unselected legacy hotspots are resolved? [Truthfulness, Plan]
- [x] CHK015 Is CI cost controlled without weakening or bypassing required checks? [Operations, FR-019]

## Resolution

All questions are answered by explicit normative requirements or plan constraints. No unresolved ambiguity blocks task
generation.
