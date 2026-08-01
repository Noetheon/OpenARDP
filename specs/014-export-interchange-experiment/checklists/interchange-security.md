# Interchange and Security Requirements Checklist: Export and Interchange Experiment

**Purpose**: Formal PR-review gate for completeness, clarity, consistency and
measurability of F014's standard selection, export, hostile-package validation and
atomic snapshot publication requirements.
**Created**: 2026-08-01
**Feature**: [spec.md](../spec.md)

**Note**: These items test the requirements as written, not implementation behavior.

## Requirement completeness

- [x] CHK001 Are all four mandated candidates evaluated against one identical set of criteria, including residual gaps and revisit conditions? [Completeness, Spec §FR-001–FR-004]
- [x] CHK002 Are the selected standard, OpenARDP-specific profile additions and rejected custom-format claim clearly separated? [Completeness, Spec §FR-003–FR-005]
- [x] CHK003 Are source and provider-native asset dispositions independently specified for inclusion, inert reference and omission? [Completeness, Spec §FR-006, FR-010–FR-012]
- [x] CHK004 Are requirements defined for every normative record, payload, tag, inventory and relationship needed to interpret a selected scope? [Completeness, Spec §FR-008–FR-012]
- [x] CHK005 Are both verification-only and fresh snapshot-import outcomes specified without implying live-workspace merge? [Completeness, Spec §FR-017–FR-022]
- [x] CHK006 Are version, extension, trust, licensing, network and execution boundaries all explicitly specified? [Completeness, Spec §FR-023–FR-026]

## Requirement clarity

- [x] CHK007 Is “experimental profile” identified by an exact independent semantic version and forbidden suffix/non-claims? [Clarity, Spec §FR-005]
- [x] CHK008 Is “affirmative permission” distinguished from absent, unknown and sender-asserted license facts? [Clarity, Spec §FR-006, FR-010]
- [x] CHK009 Are deterministic identity-bearing bytes distinguished from non-identifying operator report metadata? [Clarity, Spec §FR-009, FR-015]
- [x] CHK010 Is the portable path language precise for separators, normalization, case-folding, reserved names, controls, depth and length? [Clarity, Spec §FR-014, FR-019; Plan §Decision 8]
- [x] CHK011 Are every resource limit's default, unit, installed range and first-failure behavior documented? [Clarity, Spec §FR-018; Plan §Decision 9]
- [x] CHK012 Is “publication” explicitly defined as fresh immutable snapshot rename rather than catalog/CAS merge? [Clarity, Spec §FR-021–FR-022]

## Requirement consistency

- [x] CHK013 Do deterministic ZIP requirements remain consistent with BagIt's directory semantics and ordinary `.zip` transport? [Consistency, Spec §FR-004–FR-005; Plan §Decision 1–2]
- [x] CHK014 Do the inclusion policy and completeness requirements agree that omitted/referenced assets remain explicit but bytes are absent? [Consistency, Spec §FR-009–FR-013]
- [x] CHK015 Do fresh-disjoint import requirements agree with the unchanged workspace/catalog compatibility statement? [Consistency, Spec §FR-016, FR-021–FR-022, Compatibility]
- [x] CHK016 Do extension preservation rules remain consistent with closed core objects and package identity? [Consistency, Spec §FR-024]
- [x] CHK017 Do integrity success requirements consistently avoid authenticity, truth, ownership, permission, license and execution claims? [Consistency, Spec §FR-025, SC-010]

## Acceptance criteria quality

- [x] CHK018 Can candidate coverage be objectively traced to 100% of published criteria and authoritative evidence? [Measurability, Spec §SC-001]
- [x] CHK019 Are deterministic export claims bounded by representative scopes, exact normative bytes and three named platforms? [Measurability, Spec §SC-002]
- [x] CHK020 Is preservation success measurable across objects, records, relationships, versions, dispositions and trust labels? [Measurability, Spec §SC-003]
- [x] CHK021 Are rejection and no-publication outcomes measurable for every attack-vector family? [Measurability, Spec §SC-004–SC-008]
- [x] CHK022 Is concurrency convergence quantified and distinguished from conflicting requests? [Measurability, Spec §SC-009]

## Scenario and edge-case coverage

- [x] CHK023 Are primary export, verify and import flows plus policy-driven reference/omission alternatives specified? [Coverage, Spec §User Stories 2–3]
- [x] CHK024 Are malformed, unsupported, policy-rejected, resource-exhausted, integrity-invalid and relationship-invalid exception classes distinct? [Coverage, Spec §FR-020, FR-023]
- [x] CHK025 Are interruption, retry, same-identity concurrency and conflict recovery requirements explicit without filename-derived authority? [Coverage, Spec §FR-016, FR-021; Edge Cases]
- [x] CHK026 Are duplicate members, Unicode/case collisions, links/devices, encrypted/compressed entries, nested archives and inconsistent size metadata covered? [Coverage, Spec §FR-019; Edge Cases]
- [x] CHK027 Are empty payload, zero-length source, shared objects, mixed asset dispositions and relationship cycles addressed? [Coverage, Edge Cases]
- [x] CHK028 Are revoked/contradictory/unknown permission and inert credential-bearing reference cases addressed? [Coverage, Edge Cases; Spec §FR-010–FR-013]

## Dependencies and assumptions

- [x] CHK029 Is the no-new-dependency decision supported by stdlib capability and explicit supply-chain rationale? [Dependency, Plan §Technical Context; Research §Decision 2]
- [x] CHK030 Is the boundary between F013 backup/recovery, F014 snapshot import and any future workspace merge explicit? [Dependency, Spec §Non-Goals; Research §Decision 10]
- [x] CHK031 Are external specifications cited from authoritative maintained sources and versioned? [Dependency, Spec §FR-003; Research §Decisions 1, 3, 4]
- [x] CHK032 Are local-filesystem, no-network, trusted-operator and synthetic-fixture assumptions visible and test-bounded? [Assumption, Spec §Assumptions; Plan §Technical Context]

## Notes

- Review completed during planning. No unresolved requirement-quality gap remained.
- Implementation evidence is tracked separately in tasks, tests and convergence notes.
