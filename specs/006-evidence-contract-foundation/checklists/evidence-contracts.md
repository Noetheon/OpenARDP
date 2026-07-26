# Requirements Checklist: Evidence Contract Foundation

**Purpose**: Formal PR-review gate for contract completeness, identity determinism,
provider neutrality, trust safety, and compatibility before implementation
**Created**: 2026-07-26
**Feature**: [spec.md](../spec.md)

## Contract Surface Completeness

- [x] CHK001 Are all four public roots named, independently validatable, and bounded by an explicit purpose? [Completeness, Spec §FR-001]
- [x] CHK002 Is the distinction between root contracts and shared nested definitions unambiguous? [Clarity, Plan §Summary]
- [x] CHK003 Are version, stability, extension, identity, source-binding, and provenance requirements present for every applicable root? [Completeness, Spec §FR-002–FR-009]
- [x] CHK004 Is the projection boundary defined by allowed purposes and prohibited content rather than the vague adjective “thin”? [Clarity, Spec §FR-015]
- [x] CHK005 Is complete provider-native preservation required independently of the projection? [Consistency, Spec §US2]

## Identity and Version Determinism

- [x] CHK006 Is the identity envelope, domain separation, algorithm version, canonicalization, and digest format specified? [Completeness, Spec §FR-005]
- [x] CHK007 Are identity-significant and excluded fields documented for every declared identifier? [Clarity, Data Model §NativeRepresentation/EvidenceReference/EvidenceProjection]
- [x] CHK008 Are declared identifier mismatches explicitly rejected instead of repaired? [Failure Mode, Spec §Edge Cases]
- [x] CHK009 Are object-order, numeric-equivalence, Unicode non-normalization, and cross-process cases covered by measurable outcomes? [Coverage, Spec §SC-002]
- [x] CHK010 Are malformed, uninstalled, and unsupported-major version failures distinguishable? [Clarity, Spec §FR-003]
- [x] CHK011 Are all five version axes explicitly independent so no release number is inferred? [Consistency, Spec §FR-002]

## Anchor Semantics

- [x] CHK012 Are all required anchor variants exhaustive and mutually exclusive through an explicit discriminator? [Completeness, Spec §FR-010]
- [x] CHK013 Are text offsets, interval closure, extent bounds, and coordinate meaning specified? [Clarity, Spec §FR-011]
- [x] CHK014 Are page origin, direction, scale, page numbering, positive area, and boundary arithmetic specified without float ambiguity? [Clarity, Spec §FR-012]
- [x] CHK015 Are table origin, row/column spans, integer bounds, and native-table scoping specified? [Completeness, Spec §FR-013]
- [x] CHK016 Are opaque pointer profile, profile version, format, length, control-character, and non-resolution requirements explicit? [Security, Spec §FR-014]
- [x] CHK017 Does the spec avoid claiming cross-provider equivalence for offsets, pages, cells, or opaque pointers? [Consistency, Spec §Non-Goals]

## Trust and Untrusted-Data Boundary

- [x] CHK018 Are origin and effective trust recorded so escalation can be checked locally? [Completeness, Spec §FR-017]
- [x] CHK019 Are every allowed downgrade and every prohibited promotion class explicit? [Clarity, Spec §FR-018]
- [x] CHK020 Are role `data` and instruction execution false immutable requirements rather than advisory labels? [Security, Spec §FR-017]
- [x] CHK021 Are pointer strings, raw JSON, extensions, fixtures, and natural-language content consistently treated as data? [Consistency, Spec §FR-019/Edge Cases]
- [x] CHK022 Are diagnostics required to avoid raw untrusted value disclosure? [Privacy, Spec §FR-019]

## Compatibility and Extension Policy

- [x] CHK023 Are unknown direct fields rejected and namespaced extension values preserved only within the JCS/I-JSON subset? [Compatibility, Spec §FR-004]
- [x] CHK024 Is the namespace-key rule sufficiently exact for independent validators? [Clarity, Research §Decision 9]
- [x] CHK025 Is F006 explicitly additive, with prior schema bytes, fixtures, identities, and semantics protected? [Compatibility, Spec §FR-025]
- [x] CHK026 Are breaking experimental changes tied to changelog, fixtures, migration/rebuild guidance, and ADR triggers? [Lifecycle, Spec §FR-026]
- [x] CHK027 Are stabilization requirements evidence-based rather than time- or declaration-based? [Governance, Contract §Compatibility]

## Conformance and Failure Coverage

- [x] CHK028 Does the conformance corpus cover every root, anchor, version category, extension rule, source mismatch, geometry failure, pointer failure, identity mismatch, and trust escalation? [Coverage, Spec §FR-021]
- [x] CHK029 Is the standalone validator bounded to caller-supplied fixture paths and free of adapter, network, pointer, and source access? [Security, Spec §FR-020]
- [x] CHK030 Are schema, record-semantic, and aggregate-semantic enforcement responsibilities distinguished? [Clarity, Contract §Semantic enforcement]
- [x] CHK031 Are valid and invalid expectations machine-readable and deterministically enumerable? [Measurability, Spec §SC-003–SC-004]
- [x] CHK032 Are synthetic/redistributable fixture and no-network requirements explicit? [Supply Chain, Spec §FR-021/FR-027]

## Standards Reuse and Scope Control

- [x] CHK033 Are W3C PROV and Web Annotation mappings required while JSON-LD, remote contexts, and conformance claims remain optional or excluded? [Scope, Spec §FR-023]
- [x] CHK034 Are known mapping losses and profile-specific choices required to be visible? [Completeness, Spec §SC-007]
- [x] CHK035 Are Docling, Python, SQLite, filesystem, ranking, prompt, and complete-tree leakage all explicitly prohibited? [Provider Neutrality, Spec §FR-024]
- [x] CHK036 Are adjacent F007–F017 capabilities clearly excluded from F006? [Scope, Spec §Non-Goals]

## Verifiability

- [x] CHK037 Can each success criterion be proven with a deterministic command, diff, fixture result, or repository audit? [Measurability, Spec §SC-001–SC-008]
- [x] CHK038 Are Linux, macOS, Windows, locked dependency, build, strict typing, coverage, and offline test gates all required? [Quality, Spec §SC-008]
- [x] CHK039 Do implementation notes restate every acceptance boundary, including rollback and remote evidence? [Traceability, Implementation Notes §Restated acceptance criteria]
- [x] CHK040 Is the feature independently useful as a contract/validator boundary before any rich adapter exists? [Story Independence, Spec §US1–US4]

## Notes

- All 40 requirement-quality questions pass after the planning artifacts and contract
  design were reviewed together.
- The checklist is a formal PR-review gate focused on the two highest-risk clusters:
  deterministic public contracts and untrusted evidence boundaries.
- Items evaluate requirement quality and traceability, not implementation behavior.
