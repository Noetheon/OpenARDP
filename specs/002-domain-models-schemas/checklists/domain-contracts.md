# Domain Contract Requirements Checklist: Domain Models and Interchange Schemas

**Purpose**: Review the completeness, clarity, consistency and measurability of F002 identity, compatibility, provenance and security requirements before implementation
**Created**: 2026-07-22
**Feature**: [spec.md](../spec.md)

**Review profile**: Formal PR/release gate; focus on deterministic identity, contract compatibility and untrusted-data boundaries.

## Requirement Completeness

- [x] CHK001 Are all five required public record types explicitly named with independently testable outcomes? [Completeness, Spec §FR-001, SC-001]
- [x] CHK002 Are shared identity, timestamp, trust, provenance and extension requirements defined for every applicable record? [Completeness, Spec §FR-002–FR-018]
- [x] CHK003 Are representation revisions distinguished from source-byte versions wherever normalized evidence is referenced? [Completeness, Spec §FR-003, FR-005, FR-007–FR-008]
- [x] CHK004 Are derivation recipe identity and produced-output integrity specified as different concepts? [Completeness, Spec §FR-006; Data Model §DerivationRecord]
- [x] CHK005 Are context warnings, selection trace and missing-evidence requirements present so an empty or incomplete bundle remains honest? [Completeness, Spec §FR-008; Data Model §ContextBundle]

## Requirement Clarity

- [x] CHK006 Is the exact installed schema release distinguished from the broader major-family compatibility rule? [Clarity, Spec §US3, FR-002, Assumptions]
- [x] CHK007 Are canonicalization equivalences such as `1`/`1.0`, negative zero and unchanged mapping order stated without promising every lexical mutation changes a hash? [Clarity, Spec §US2, SC-003]
- [x] CHK008 Is Unicode preservation clearly separated from future format-specific text normalization? [Clarity, Spec §US2/AC4, FR-015, Assumptions]
- [x] CHK009 Are identity inputs and excluded operational fields named for each persisted SHA-256 purpose? [Clarity, Contract §Identity envelope]
- [x] CHK010 Is an opaque locator or artifact handle explicitly defined as data rather than filesystem or network authority? [Clarity, Spec §FR-009–FR-011; Data Model §SourceDescriptor, §EvidenceItem]

## Requirement Consistency

- [x] CHK011 Do strict unknown-field rejection and forward-compatible extensions coexist without claiming an old reader accepts an uninstalled direct-field schema? [Consistency, Spec §FR-010–FR-011, Assumptions]
- [x] CHK012 Do schema-generation requirements preserve reviewed public artifacts as the interchange authority while preventing model/schema drift? [Consistency, Spec §FR-018–FR-020, FR-026]
- [x] CHK013 Are all content-bearing trust requirements consistent with the constitution's non-authority rule? [Consistency, Spec §FR-009; Constitution IV]
- [x] CHK014 Is direct source-byte hashing kept distinct from domain-separated canonical model identities? [Consistency, Contract §Source version, §Identity envelope]
- [x] CHK015 Are later aggregate rules identified without pulling persistence, graph evaluation or context-selection behavior into F002? [Consistency, Spec §FR-025, FR-027; Data Model §Invariant ownership]

## Acceptance Criteria Quality

- [x] CHK016 Can the five-record round-trip result be measured without relying on an unspecified implementation detail? [Measurability, Spec §SC-001]
- [x] CHK017 Is subprocess determinism quantified by execution count, construction-order variation and platform matrix? [Measurability, Spec §SC-002]
- [x] CHK018 Are negative outcomes tied to named fixture classes and the capable validation layer? [Measurability, Spec §FR-022, SC-004]
- [x] CHK019 Is schema reproducibility defined as byte-for-byte stability over repeated generation? [Measurability, Spec §SC-005]
- [x] CHK020 Is traceability measurable for every record across model, schema, fixture and tests? [Measurability, Spec §SC-007]

## Scenario and Edge-Case Coverage

- [x] CHK021 Are primary, invalid-input, extension and unsafe-instruction scenarios all covered for contract exchange? [Coverage, Spec §US1]
- [x] CHK022 Are insertion order, list order, unsupported runtime types, unsafe numbers and Unicode edge cases covered for canonical identity? [Coverage, Spec §US2, Edge Cases]
- [x] CHK023 Are malformed, uninstalled and unsupported-major version scenarios distinguished for compatibility handling? [Coverage, Spec §US3, SC-006]
- [x] CHK024 Are missing content, identity mismatch, self-reference, lifecycle mismatch and unpinned context evidence addressed? [Coverage, Spec §Edge Cases, FR-022]
- [x] CHK025 Are no-result/missing-evidence and cross-version bundle cases specified rather than left to later implementation guesswork? [Coverage, Data Model §ContextBundle]

## Security and Dependency Assumptions

- [x] CHK026 Is the no-network, synthetic-fixture boundary explicit for every test category? [Security, Spec §FR-023, SC-008]
- [x] CHK027 Is document text consistently classified as untrusted data with instruction execution fixed to false? [Security, Spec §FR-009, US1/AC4]
- [x] CHK028 Are non-JSON extension values, duplicate keys and silent coercion addressed at the public validation boundary? [Security, Spec §FR-010–FR-015; Research §Decision 4]
- [x] CHK029 Are content hashes described as integrity/equality metadata rather than signatures or authorization? [Security, Contract §Canonical JSON]
- [x] CHK030 Are parser resource controls, persistence atomicity and provider egress intentionally excluded and routed to their authoritative later work packages? [Scope, Spec §FR-025, Assumptions]

## Notes

- All 30 requirement-quality checks pass after the second specification validation.
- Traceability references are present on every checklist item.
- This checklist evaluates the written contract, not the implementation. Runtime evidence belongs to tests, implementation notes and convergence.
