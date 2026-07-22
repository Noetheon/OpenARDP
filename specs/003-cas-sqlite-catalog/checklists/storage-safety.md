# Storage Safety Requirements Checklist: Content-Addressed Storage and SQLite Catalog

**Purpose**: Formal PR/release review of requirement completeness, clarity, consistency and measurability for atomic storage, catalog recovery and security boundaries
**Created**: 2026-07-22
**Feature**: [spec.md](../spec.md)

**Review profile**: Reviewer-facing release gate; deep focus on evidence preservation, crash boundaries, migrations, leases and path safety.

## Requirement Completeness

- [x] CHK001 Are exact-byte identity, length, immutability and integrity obligations defined for every stored object? [Completeness, Spec §FR-001–FR-007]
- [x] CHK002 Are the two independent commit resources and the permitted complete-orphan outcome documented without implying a distributed transaction? [Completeness, Spec §Assumptions; Plan §Resource boundary]
- [x] CHK003 Are document, source-version, object-reference, migration, job and reachability entities all defined with ownership relationships? [Completeness, Spec §Key Entities; Data Model §Domain records]
- [x] CHK004 Are all required source-version reference checks stated before catalog visibility? [Completeness, Spec §FR-010–FR-012]
- [x] CHK005 Are job identity, attempts, fencing, expiry, terminal outcome and recovery requirements all present? [Completeness, Spec §FR-016–FR-018; Data Model §Job]
- [x] CHK006 Are migration ordering, checksums, compatibility rejection and rollback expectations all specified? [Completeness, Spec §FR-014–FR-015; Contract §Catalog initialization]
- [x] CHK007 Are all live-root categories and inconsistency classes defined for reachability? [Completeness, Spec §FR-019–FR-020; Research §Decision 11]

## Requirement Clarity

- [x] CHK008 Is a committed source-version fact explicitly distinguished from a complete `READY` parser representation? [Clarity, Plan §Summary; Contract §Source-version commit]
- [x] CHK009 Is object identity defined as exact source bytes rather than metadata, path text or a model serialization? [Clarity, Spec §FR-001; Data Model §Object identity]
- [x] CHK010 Is the exact source-key comparison rule stated, including the absence of case, whitespace or Unicode normalization? [Clarity, Spec §Assumptions; Data Model §Source key]
- [x] CHK011 Is the meaning of `candidate` limited to unreferenced-at-snapshot rather than safe-to-delete? [Clarity, Spec §US4; Contract §ReachabilityService]
- [x] CHK012 Is the exact lease boundary defined so equality cannot be interpreted as both active and expired? [Clarity, Data Model §State transitions; Contract §Failure and recovery]
- [x] CHK013 Are process-crash visibility, filesystem synchronization and universal power-loss guarantees clearly separated? [Clarity, Quickstart §Interpreting durability evidence; Research §Decision 4]
- [x] CHK014 Are failure classifications distinguished from raw exception messages and document content? [Clarity, Spec §FR-016; Contract §Error contract]

## Requirement Consistency

- [x] CHK015 Do immutable CAS requirements remain consistent with idempotent duplicate publication and corruption rejection? [Consistency, Spec §FR-002–FR-004; Research §Decision 2]
- [x] CHK016 Do global object IDs and composite document-version IDs permit identical bytes across logical documents without identity collision? [Consistency, Spec §FR-008–FR-011; Research §Decision 8]
- [x] CHK017 Do catalog atomicity requirements align with the documented CAS-before-catalog orphan outcome? [Consistency, Spec §US2/AC3; Plan §Resource boundary]
- [x] CHK018 Do job retry requirements preserve terminal immutability and bounded attempts? [Consistency, Spec §FR-016–FR-018; Data Model §State transitions]
- [x] CHK019 Do reachability roots conservatively preserve historical evidence and job references while excluding metadata-only object rows? [Consistency, Data Model §ReferenceSnapshot; Research §Decision 11]
- [x] CHK020 Does the no-network/local-first boundary remain consistent across dependencies, tests and runtime behavior? [Consistency, Spec §FR-021–FR-022; Plan §Technical Context]
- [x] CHK021 Do the plan and contracts preserve F002 SHA-256/UUIDv7 rules without introducing a new persisted identity algorithm? [Consistency, Spec §Dependencies; Plan §Documentation and Decision Updates]

## Acceptance Criteria Quality

- [x] CHK022 Is concurrent duplicate convergence quantified by caller count and observable object count? [Measurability, Spec §SC-001]
- [x] CHK023 Are interruption outcomes quantified as zero partial objects and zero partial versions at named boundaries? [Measurability, Spec §SC-002]
- [x] CHK024 Is retry idempotency measurable across document, version and job operations? [Measurability, Spec §SC-003]
- [x] CHK025 Are migration outcomes measurable across fresh, repeated, older and failed upgrade cases? [Measurability, Spec §SC-004]
- [x] CHK026 Are restart and recovery outcomes measurable for recoverable and terminal jobs? [Measurability, Spec §SC-005]
- [x] CHK027 Is path-boundary success defined by zero outside-root access across a named hostile corpus? [Measurability, Spec §SC-006]
- [x] CHK028 Is reachability accuracy defined for live, orphaned, missing and corrupt cases with zero deletion? [Measurability, Spec §SC-007]
- [x] CHK029 Is cross-platform completion tied to the existing Linux/macOS/Windows quality gate rather than an unverified portability claim? [Measurability, Spec §SC-008; Plan §Test Strategy]

## Scenario Coverage

- [x] CHK030 Are primary, duplicate, concurrent, interrupted and corrupt-object scenarios all addressed? [Coverage, Spec §US1; Edge Cases]
- [x] CHK031 Are successful, retried, conflicting, missing-reference and interrupted source-version commits addressed? [Coverage, Spec §US2; Edge Cases]
- [x] CHK032 Are fresh initialization, upgrade, migration failure and too-new catalog scenarios addressed? [Coverage, Spec §US3; Quickstart §2]
- [x] CHK033 Are claim, lost response, renew, complete, retryable failure, exhausted failure, exact expiry and restart recovery scenarios addressed? [Coverage, Contract §Job claim–Failure and recovery]
- [x] CHK034 Are reachable, candidate, missing, corrupt, malformed and staging-residue cases addressed without a delete path? [Coverage, Spec §US4; Contract §ReachabilityService]
- [x] CHK035 Are empty objects, unusual chunks, same bytes across documents and hostile source metadata included as boundary classes? [Coverage, Spec §Edge Cases; Quickstart §1–3]

## Security and Operational Boundaries

- [x] CHK036 Is the storage-root trust assumption stated together with the unsupported shared/adversarial filesystem boundary? [Security, Plan §Technical Context; Research §Decision 3]
- [x] CHK037 Are locators explicitly denied filesystem and SQL authority? [Security, Spec §Assumptions; Contract §Logging contract]
- [x] CHK038 Are raw lease tokens, document bytes, locators and SQL values prohibited from logs and public errors? [Security, Contract §Logging contract]
- [x] CHK039 Are automatic garbage deletion, retention and secure erasure explicitly excluded? [Scope, Spec §Out of Scope; FR-020]
- [x] CHK040 Are parser, ingestion CLI, FTS, cloud storage and `READY` representation behavior routed to later features? [Scope, Spec §FR-022; Plan §Summary]
- [x] CHK041 Is WAL exclusion justified against the actually observed runtime rather than asserted as a timeless database preference? [Operational Risk, Research §Decision 6]
- [x] CHK042 Are unsupported scale and absolute durability claims explicitly deferred to measured evidence? [Operational Honesty, Spec §Success Criteria; Plan §Technical Context]

## Notes

- All 42 requirement-quality checks pass after one formal review on 2026-07-22.
- Every item contains direct traceability to the spec or a Phase-1 design artifact.
- This checklist evaluates written requirements and design obligations only; implementation evidence belongs to tests, implementation notes and convergence.
