# Storage Safety Requirements Checklist: Storage Amplification Reduction

**Purpose**: Review whether F022's persistence, migration, recovery and measurement requirements are complete,
unambiguous and release-ready
**Created**: 2026-08-02
**Feature**: [spec.md](../spec.md)

**Audience/Timing**: Author and PR reviewer before task generation and again before convergence

## Requirement Completeness

- [x] CHK001 Are all logical artifacts that must survive reduction enumerated, including historical versions, blocks,
  manifests, provenance and search-rebuild inputs? [Completeness, Spec §FR-004]
- [x] CHK002 Are the object classes eligible and ineligible for physical compaction explicitly separated? [Completeness,
  Spec §FR-006–FR-008]
- [x] CHK003 Are requirements defined for fresh ingestion, existing-workspace migration and post-migration optimization as
  distinct flows? [Completeness, Spec §User Stories 1 and 3]
- [x] CHK004 Are all affected maintenance surfaces named rather than treating ordinary retrieval as the only reader?
  [Completeness, Spec §FR-017]
- [x] CHK005 Are backup contents and restore acceptance requirements specified for both physical and logical inventories?
  [Completeness, Spec §FR-018]
- [x] CHK006 Are benchmark inputs, comparison baselines, observations, projections and validation artifacts all required?
  [Completeness, Spec §FR-001 and FR-021–FR-023]

## Requirement Clarity

- [x] CHK007 Is “logical workspace bytes” defined independently from filesystem-allocated bytes and source bytes?
  [Clarity, Spec §SC-001–SC-004]
- [x] CHK008 Is “exact logical bytes” tied to SHA-256 identity, declared length and replay equality rather than semantic
  equivalence? [Clarity, Spec §FR-005 and FR-009]
- [x] CHK009 Is “ordinary open” clearly distinguished from explicit migration and explicit optimization? [Clarity, Spec
  §FR-013–FR-015]
- [x] CHK010 Is the permitted duplicate physical-form state distinguished from corruption and from one logical object in
  inventory accounting? [Clarity, Spec §FR-010 and Edge Cases]
- [x] CHK011 Is “unsafe layout” made concrete through the enumerated active-operation, corruption, backup and compatibility
  conditions? [Clarity, Spec §FR-016]
- [x] CHK012 Is the binding platform for the allocated-byte threshold named while other platforms remain report-only?
  [Clarity, Spec §FR-003 and SC-003]

## Requirement Consistency

- [x] CHK013 Do compact-storage requirements preserve the immutable-original and exact-identity requirements without an
  alternate authority? [Consistency, Spec §FR-005–FR-009]
- [x] CHK014 Do normalized-catalog requirements remain consistent with search disposability and verified evidence return?
  [Consistency, Spec §FR-011–FR-012]
- [x] CHK015 Do migration requirements align with the prohibition on open-time mutation? [Consistency, Spec §FR-013–FR-015]
- [x] CHK016 Do duplicate-form recovery requirements align with fail-closed corruption requirements rather than allowing a
  valid peer to hide corrupt data? [Consistency, Spec §FR-009–FR-010 and FR-016]
- [x] CHK017 Do storage-reduction targets retain the complete F020 workload and quality metrics instead of reducing the
  measured scope? [Consistency, Spec §FR-001–FR-004 and FR-024]
- [x] CHK018 Are the no-new-dependency and cross-platform requirements consistent with the stated local-first scope?
  [Consistency, Spec §FR-020 and FR-025]

## Acceptance Criteria Quality

- [x] CHK019 Are reference and scale logical ceilings stated as exact byte values and ratios? [Measurability, Spec §SC-001
  and SC-002]
- [x] CHK020 Is the 60-percent comparison defined against both pinned F020 workload results? [Measurability, Spec §SC-004]
- [x] CHK021 Is the allocated-byte criterion measurable with a stated binding filesystem and an explicit non-binding report
  elsewhere? [Measurability, Spec §SC-003]
- [x] CHK022 Are equivalence requirements quantified across all vectors for bytes, identities and navigation? [Measurability,
  Spec §SC-005]
- [x] CHK023 Are migration and interruption outcomes objectively defined as convergence or verified restore with zero
  missing logical objects? [Measurability, Spec §SC-007]
- [x] CHK024 Are search and context equivalence tied to the frozen F020 metrics rather than a vague “no regression” claim?
  [Measurability, Spec §SC-006]
- [x] CHK025 Is the quality gate threshold and required platform matrix stated objectively? [Measurability, Spec §SC-010]

## Scenario and Edge-Case Coverage

- [x] CHK026 Are primary requirements defined for both capability-aware and ordinary provider implementations? [Coverage,
  Spec §FR-008 and Assumptions]
- [x] CHK027 Are zero-saving and size-expanding compaction outcomes explicitly addressed? [Coverage, Spec §FR-008 and Edge
  Cases]
- [x] CHK028 Are empty, truncated, unknown-version, oversized, trailing-data and digest-mismatch payloads covered as distinct
  exception classes? [Coverage, Spec §FR-009 and Edge Cases]
- [x] CHK029 Are concurrent publication, interruption before/after publication and retry requirements all documented?
  [Coverage, Spec §FR-010 and User Story 3]
- [x] CHK030 Are raw-only, compact-only, valid duplicate and corrupt duplicate states addressed? [Coverage, Spec §FR-010,
  FR-016 and Edge Cases]
- [x] CHK031 Are migration rollback and restore requirements defined without requiring an unsafe reverse migration?
  [Recovery, Spec §FR-013, FR-018 and User Story 3]
- [x] CHK032 Are retention and quarantine requirements defined for objects reachable through either physical layout?
  [Coverage, Spec §FR-017 and User Story 4]
- [x] CHK033 Are workspaces below the new revision, at the new revision and newer-than-supported addressed? [Coverage,
  Spec §FR-013–FR-016 and Edge Cases]

## Non-Functional Requirements and Assumptions

- [x] CHK034 Are decompression resource limits and rejection behavior specified independently of expected input size?
  [Security, Spec §FR-009]
- [x] CHK035 Are privacy requirements body-free for errors, logs, CLI results and benchmark artifacts? [Privacy, Spec
  §FR-019]
- [x] CHK036 Are determinism and offline operation requirements explicit for codec, migration, benchmark and validation?
  [Non-Functional, Spec §FR-020–FR-023]
- [x] CHK037 Are latency, CPU, file-count and allocation tradeoffs required in the report even when storage thresholds pass?
  [Transparency, Spec §SC-011]
- [x] CHK038 Is the assumption that the frozen F020 workload remains the fair comparison explicitly documented and protected
  by immutable input identities? [Assumption, Spec §FR-001 and FR-022]
- [x] CHK039 Is optional provider capability fallback documented so the filesystem implementation does not become a public
  mandatory storage format? [Dependency, Spec §FR-008 and Assumptions]
- [x] CHK040 Are exclusions for packfiles, source compression, history deletion and public-schema changes explicit enough to
  prevent scope drift? [Boundary, Spec §Non-Goals]

## Notes

- All 40 requirement-quality checks passed during planning. Re-open any affected item if implementation evidence exposes
  a requirement ambiguity rather than silently resolving it in code.
- The checklist intentionally reviews the written requirements; implementation verification belongs in `tasks.md` and the
  benchmark contract.
