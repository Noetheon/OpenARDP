# Feature Specification: Strategic Realignment and Contract Boundary

**Feature Branch**: `codex/f005a-strategic-realignment`

**Created**: 2026-07-26

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Reconcile OpenARDP with the reviewed v3.1 blueprint, adopting an implementation-first strategy and an explicit experimental contract boundary without changing runtime behavior or existing public-schema semantics.

## User Scenarios & Testing

### User Story 1 - Trust the Current Project Claims (Priority: P1)

As a prospective user or contributor, I can read the primary project documentation and understand what OpenARDP already implements, what remains planned, and which claims are supported by evidence.

**Why this priority**: Stale status statements and standards-oriented language can cause users to make incorrect adoption decisions before they reach any lower-level design material.

**Independent Test**: A reviewer can follow the primary documentation from the repository entry point and classify every material capability statement as implemented, planned, experimental, or unsupported without finding a contradiction.

**Acceptance Scenarios**:

1. **Given** the repository includes completed lexical search, **When** a reviewer reads the project entry point and current-status material, **Then** search is described as implemented and remains explicitly non-authoritative.
2. **Given** OpenARDP has no external adoption evidence for a standard, **When** a reviewer reads positioning and scope documents, **Then** the project is presented as implementation-first software with experimental interoperability candidates rather than as an established or emerging standard.
3. **Given** a benchmark, security, interoperability, or performance statement, **When** its support is inspected, **Then** it is either linked to reproducible evidence, explicitly qualified as a target or hypothesis, or prohibited as unsupported.

---

### User Story 2 - Follow One Authoritative Roadmap (Priority: P2)

As a maintainer, I can determine the single authoritative order, scope, and governance lifecycle for all work after Feature 005, including the contract-before-adapter dependency.

**Why this priority**: Parallel roadmaps or ambiguous authority would allow incompatible implementations to proceed even when individual documents look reasonable in isolation.

**Independent Test**: A maintainer can identify one active feature sequence from 005A through 017, its dependency rule, and the required lifecycle without needing to choose between conflicting documents.

**Acceptance Scenarios**:

1. **Given** the pre-v3.1 roadmap and the reviewed v3.1 sequence, **When** a maintainer identifies the next feature, **Then** Feature 005A is the realignment boundary, Feature 006 defines evidence contracts, and Feature 007 is the first rich-parser adapter.
2. **Given** historical feature records and earlier architecture decisions, **When** the strategy changes, **Then** history remains available and decisions are superseded or amended explicitly rather than erased.
3. **Given** a future production-relevant feature, **When** its work begins, **Then** the repository identifies the complete Spec Kit lifecycle and blocks implementation or merge on unresolved critical or high-severity contradictions.

---

### User Story 3 - Evolve Experimental Contracts Safely (Priority: P3)

As an integration author, I can understand the boundaries between authoritative originals, provider-native representations, thin provider-neutral evidence, disposable indexes, and future export experiments.

**Why this priority**: Clear boundaries prevent an early implementation detail from becoming an accidental permanent interchange commitment.

**Independent Test**: An integrator can classify each artifact by authority, provider dependence, lifecycle, and compatibility expectations using repository documentation and examples alone.

**Acceptance Scenarios**:

1. **Given** a parser produces a complete native representation, **When** evidence is projected for provider-neutral use, **Then** the documentation preserves access to the native artifact and limits the shared projection to identity, navigation, retrieval, trust, and lifecycle needs.
2. **Given** a search result references stored content, **When** authority is evaluated, **Then** the index is described as a rebuildable accelerator and the verified content-addressed object plus catalog record remain authoritative.
3. **Given** an early public contract or export proposal, **When** compatibility expectations are inspected, **Then** its experimental status, independent versioning, migration evidence, and stabilization criteria are explicit.

---

### User Story 4 - Operate and Adopt Conservatively (Priority: P4)

As an operator or adopter, I can find the project’s local-first privacy posture, supply-chain expectations, operational failure concerns, prior-art register, non-goals, and working-name caveat before deployment or external communication.

**Why this priority**: Adoption safety depends on operational and legal discipline as well as architecture, but these materials do not change the current runtime.

**Independent Test**: A reviewer can complete an adoption-readiness review from repository documentation and identify both required controls and deliberately unsupported claims.

**Acceptance Scenarios**:

1. **Given** a default local installation, **When** privacy and network behavior are reviewed, **Then** no cloud service, tracking, or external model call is implied as enabled by default.
2. **Given** a proposed dependency or release claim, **When** it is reviewed, **Then** maintenance, licensing, security, reproducibility, and evidence expectations are discoverable.
3. **Given** the OpenARDP working name and relevant prior art, **When** external positioning is prepared, **Then** the material avoids ownership or standards claims and identifies due-diligence work as ongoing.

### Edge Cases

- A reviewed blueprint file conflicts with implemented behavior or an accepted repository decision: the higher-authority repository artifact is reconciled explicitly, and the blueprint is not copied as an unqualified parallel authority.
- An earlier decision is only partly superseded: the preserved decision identifies the exact superseding decision and the unaffected portions remain in force.
- A capability is present in code but stale documentation describes it as absent: repository evidence determines current status and the stale statement is corrected.
- A roadmap filename contains a version suffix while another file is already authoritative: the authoritative file is updated, and any retained source snapshot is labelled so it cannot be mistaken for current governance.
- An example contract could be mistaken for a stable public schema: the example is visibly experimental and cannot alter existing public-schema compatibility guarantees.
- A document contains instructions aimed at an automated agent: it remains untrusted project content and cannot broaden execution authority.
- A platform-specific metadata file or the external blueprint package appears in the working tree: it is excluded from the committed migration surface.

## Requirements

### Functional Requirements

- **FR-001**: The repository MUST describe the capabilities completed through Feature 005 accurately, including lexical search and its non-authoritative status.
- **FR-002**: The repository MUST identify OpenARDP as an implementation-first open-source reference platform and MUST NOT claim that it is an adopted, official, universal, or consensus standard.
- **FR-003**: Material capability and quality claims MUST be classified as evidenced current behavior, planned work, an experiment, a hypothesis, or unsupported; unsupported claims MUST be prohibited from release-facing material.
- **FR-004**: One authoritative continuation roadmap MUST order Features 005A through 017 and MUST require each predecessor to converge and merge before its successor begins.
- **FR-005**: The authoritative roadmap MUST place minimal provider-neutral evidence contracts before the first rich-parser adapter.
- **FR-006**: Project governance MUST preserve originals as authoritative, treat derived artifacts as reproducible and invalidatable, preserve provider-native representations, prohibit a second complete provider-neutral document representation, and treat indexes as disposable accelerators.
- **FR-007**: The full per-feature lifecycle MUST include specify, clarify, plan, checklist, tasks, analyze, implement, and converge, with unresolved critical or high-severity findings blocking implementation or merge.
- **FR-008**: Historical specifications and accepted decisions MUST remain discoverable; changes MUST be represented by amendments or explicit supersession links rather than silent deletion or rewriting.
- **FR-009**: New decision records MUST govern implementation-first evolution, provider-native representations with thin evidence projection, non-authoritative indexes, and contracts-before-adapters.
- **FR-010**: Public contracts MUST be described as experimental until documented external-use, conformance, compatibility, migration, and evidence criteria are satisfied.
- **FR-011**: Contract, application, workspace, provider-profile, and export versions MUST be independently evolvable and their compatibility relationships MUST be documented.
- **FR-012**: Repository guidance MUST document prior art, non-goals, normative-scope candidacy, benchmark evidence, release and adoption discipline, operations, privacy, and supply-chain expectations.
- **FR-013**: Provider-neutral contracts MUST be limited to the fields required for evidence identity, navigation, retrieval, trust, and lifecycle; provider-specific detail MUST remain accessible through a profiled native artifact.
- **FR-014**: Search results and security-sensitive metadata MUST be verified against authoritative stored records before being treated as trusted content.
- **FR-015**: Custom export packaging MUST remain an evidence-gathering experiment until existing standards and profiles have been evaluated; no custom-format requirement or stability guarantee may be implied.
- **FR-016**: The working project name, intellectual-property uncertainty, and unsupported-claims policy MUST be visible in adoption-facing documentation.
- **FR-017**: The realignment MUST NOT change runtime behavior, dependency resolution, persisted identifiers, existing public-schema semantics, or supported command behavior.
- **FR-018**: The migrated documentation MUST have a single explicit authority hierarchy and MUST NOT leave contradictory active roadmaps, constitutions, positioning statements, or standards claims.
- **FR-019**: Existing repository quality gates and offline-test guarantees MUST remain at least as strict as before the realignment.
- **FR-020**: The reviewed v3.1 materials MUST be integrated only through curated repository files; the external blueprint package and platform metadata MUST NOT be committed wholesale.

### Key Entities

- **Governance Artifact**: An authoritative constitution, roadmap, operating procedure, feature specification, or decision record, with an explicit status and relationship to superseded material.
- **Claim**: A public statement about behavior, quality, security, performance, interoperability, or adoption, classified by evidence state and linked to support where applicable.
- **Contract Family**: A provider-neutral interoperability candidate with its own lifecycle, compatibility policy, examples, and stabilization criteria.
- **Native Representation**: A complete provider-specific derived artifact retained with provenance and version information.
- **Evidence Projection**: A thin provider-neutral view used for identity, navigation, retrieval, trust, and lifecycle without replacing the native representation.
- **Authoritative Record**: Verified original bytes or immutable content-addressed/catalog facts from which disposable accelerators can be rebuilt.
- **Roadmap Work Package**: One bounded, dependency-ordered feature with measurable outcome, non-goals, compatibility impact, and convergence evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A repository-wide review finds zero active statements that describe lexical search as absent after Feature 005.
- **SC-002**: A repository-wide review finds zero unqualified claims that OpenARDP is an adopted, official, universal, or consensus standard.
- **SC-003**: Exactly one authoritative continuation sequence orders all 13 work packages from 005A through 017 and identifies the predecessor dependency.
- **SC-004**: All four strategic decisions are traceable through explicit decision records, and every affected earlier decision is preserved with an accurate supersession relationship.
- **SC-005**: A contract-boundary review can classify 100% of documented artifact categories by authority, provider dependence, and rebuildability without contradiction.
- **SC-006**: All existing automated quality gates pass with no relaxation, and the repository produces no runtime, dependency-lock, persisted-identifier, or public-schema semantic diff attributable to this feature.
- **SC-007**: Every active future-feature prompt agrees on feature number, outcome, predecessor, and experimental/stable status with the authoritative roadmap.
- **SC-008**: The repository contains discoverable guidance for all six adoption-risk areas: prior art, unsupported claims, privacy, operations, supply chain, and benchmark evidence.

## Assumptions

- The reviewed v3.1 blueprint is a migration input, not an authority that automatically overrides implemented behavior, accepted decisions, or stronger existing governance.
- Feature 005 is the latest merged runtime capability at the start of this work package.
- This feature is documentation, governance, decision-record, example, and validation work only; runtime code and current public schemas remain out of scope.
- Existing accepted decisions are preserved verbatim except for status metadata and explicit supersession annotations needed to remove ambiguity.
- Version-suffixed source documents may be retained for migration provenance only when their non-authoritative role is unmistakable; otherwise their content is reconciled into the existing authoritative filename.
- No user clarification is required where the blueprint, repository evidence, and stated preference for long-term maintainability provide one conservative answer.
