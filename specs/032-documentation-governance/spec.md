# Feature Specification: Risk-Proportionate Documentation Governance

**Feature Branch**: `codex/documentation-governance`

**Created**: 2026-08-09

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Replace mandatory full Spec Kit usage for every production-relevant change with risk-proportionate governance,
then consolidate historical Markdown without losing normative contracts or reproducible evidence.

## Clarifications

### Session 2026-08-09

- Q: Must every future change use the full Spec Kit lifecycle? → A: No; documentation depth must match change risk.
- Q: What remains after a merged feature is compacted? → A: Requirements, final evidence and normative contracts.
- Q: May historical planning artifacts disappear from the current tree? → A: Yes, after consolidation; Git history remains
  discoverable and the retained record identifies the boundary.

## User Scenarios & Testing

### User Story 1 - Choose proportionate governance (Priority: P1)

A maintainer can classify a change through explicit criteria and know the minimum planning, evidence and review required
without generating a full feature dossier for routine work.

**Why this priority**: Preventing new documentation debt is more valuable than only deleting old files.

**Independent Test**: Given representative routine, standard and high-assurance changes, the policy assigns exactly one
tier and identifies its required durable artifacts and gates.

**Acceptance Scenarios**:

1. **Given** a documentation-only or behavior-preserving routine change, **When** it is classified, **Then** no Spec Kit
   feature directory is required.
2. **Given** an ordinary bounded behavior change, **When** it is classified, **Then** a compact requirements and evidence
   record is required without the full lifecycle.
3. **Given** a contract, schema, identity, migration, security-boundary, provider, benchmark or release change, **When** it
   is classified, **Then** the full lifecycle and applicable ADR/evidence controls remain mandatory.

---

### User Story 2 - Compact historical feature records (Priority: P2)

A maintainer can navigate completed features without traversing hundreds of transient planning files, while still finding
the accepted requirements, final implementation evidence and normative contracts.

**Why this priority**: The current 347 feature Markdown files create navigation and truth-maintenance costs.

**Independent Test**: Every completed feature retains `spec.md`, `implementation-notes.md` and any contract documents,
while classified transient artifacts and historical prompts are absent from the current tree.

**Acceptance Scenarios**:

1. **Given** a completed feature, **When** compaction runs, **Then** requirements, evidence and contracts remain.
2. **Given** a transient plan, task list, research note, checklist or generated prompt, **When** the corresponding feature
   is complete, **Then** it may be removed from the current tree after references are migrated.
3. **Given** a removed artifact, **When** historical detail is needed, **Then** the retention policy explains how to recover
   it from Git history without rewriting history.

---

### User Story 3 - Keep documentation truthful (Priority: P3)

A contributor sees one authoritative feature-status source and automated validation rejects documentation architecture
drift without hard-coding every historical planning filename.

**Why this priority**: Fewer files are useful only if the remaining sources stay correct.

**Independent Test**: Repository validation passes with the compact layout, rejects missing retained records and contracts,
and no current Markdown link targets a removed artifact.

**Acceptance Scenarios**:

1. **Given** the feature registry, **When** status is read, **Then** no second manually maintained status table contradicts it.
2. **Given** a retained feature directory, **When** validation runs, **Then** required records and safe links are checked.
3. **Given** a future feature, **When** it is completed, **Then** the documented compaction rule prevents indefinite growth.

### Edge Cases

- A file named like a transient artifact is retained when an accepted ADR or public document explicitly makes it normative.
- Benchmark inputs, machine-readable results, licenses, public schemas and source evidence are never removed by a Markdown
  cleanup merely because feature documentation links to them.
- Removing files from the current tree is not described as reducing Git history or historical clone size.
- An ambiguous or mixed change classifies upward to the safer tier.

## Requirements

### Functional Requirements

- **FR-001**: Governance MUST define routine, standard and high-assurance change tiers with deterministic upward-fallback
  criteria.
- **FR-002**: Routine changes MUST NOT require a Spec Kit feature directory.
- **FR-003**: Standard changes MUST retain concise requirements and final evidence but MUST NOT require every generated
  planning artifact.
- **FR-004**: High-assurance changes MUST retain the complete lifecycle for contracts, schemas, identity, migrations,
  security boundaries, providers, benchmarks, release decisions and similarly material risks.
- **FR-005**: Cross-platform and test gates MUST remain based on executable risk and existing CI policy, not Markdown count.
- **FR-006**: Completed features MUST retain `spec.md`, `implementation-notes.md` and every normative contract document.
- **FR-007**: Completed-feature plans, research, data-model notes, quickstarts, task lists, analyses, checklists and generated
  feature prompts MAY be removed only after unique durable content and repository references are accounted for.
- **FR-008**: Git history MUST remain intact and MUST be documented as the recovery path for removed transient artifacts.
- **FR-009**: The feature map MUST be the single manually maintained feature-status registry.
- **FR-010**: Repository validation MUST validate the compact invariant instead of enumerating historical transient files.
- **FR-011**: All current Markdown links and required-file checks MUST be migrated before deletion.
- **FR-012**: Constitution, source mirror, contributor guidance, templates and runtime instructions MUST agree on the new
  tier model and retention policy.
- **FR-013**: The migration MUST report before/after file and line counts plus retained/deleted classes.
- **FR-014**: Product behavior, public schemas, persisted identities, dependencies and release claims MUST remain unchanged.

### Non-Goals and Compatibility Impact

- **Non-goal**: Rewrite Git history or remove normative contracts, benchmarks, licenses, evidence inputs or machine results.
- **Non-goal**: Weaken code quality, security, coverage, release or cross-platform gates.
- **Compatibility impact**: Governance MAJOR amendment; runtime, schema, workspace, provider and export compatibility remain
  unchanged.

### Key Entities

- **Change tier**: Risk classification that selects durable artifacts and review gates.
- **Durable feature record**: Accepted requirements, implementation evidence and normative contracts kept in the current tree.
- **Transient artifact**: Planning-time Markdown recoverable from Git history after convergence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The policy maps every reviewed example to one of three tiers and ambiguous changes fail upward.
- **SC-002**: At least 50 percent of tracked feature/prompt Markdown files are removed from the current tree.
- **SC-003**: All 32 historical features plus this transition retain requirements and final implementation evidence.
- **SC-004**: Every normative contract document present at baseline remains present after migration.
- **SC-005**: Repository validation reports zero missing retained records and zero broken local Markdown links.
- **SC-006**: Constitution, guidance, templates and validation tests contain no unconditional full-lifecycle rule for routine
  or standard changes.
- **SC-007**: Full locked quality gates and applicable private-PR checks pass without product-code or dependency changes.

## Assumptions

- Git history and merged pull requests remain available as historical planning provenance.
- `spec.md` and `implementation-notes.md` are stable link targets worth preserving across all completed features.
- Existing CI path classification remains the authority for when expensive platform jobs run.
