<!--
Sync Impact Report

- Version change: 2.0.0 -> 3.0.0
- Bump rationale: MAJOR because universal full-lifecycle governance is replaced by
  risk-proportionate routine, standard and high-assurance change tiers.
- Modified principles:
  - Article I Evidence Preservation -> Article I Source Truth and Evidence Preservation
  - Article II Derived Data Is Disposable -> Article II Derived Data and Disposable Accelerators
  - Article III Local-First and Provider-Neutral Core -> Article III Implementation First,
    Reuse and Provider Neutrality
  - Article IV Untrusted Document Boundary -> Article V Data Is Not Instruction and Execution Is Bounded
  - Article V Determinism, Identity and Atomicity -> Article VI Determinism, Identity and Atomicity
  - Article VI Progressive Context Delivery -> Article VII Progressive Context Delivery
  - Article VII Test-First Quality Gates -> Article VIII Test-First Quality Gates
  - Article VIII Measured Claims -> Article IX Fair Evidence and Measured Claims
  - Article IX Simplicity and Incremental Delivery -> Article X Simplicity and Incremental Delivery
  - Article XI Feature Isolation and Cross-Platform Quality -> Article XI Risk-Proportionate Change Governance and
    Cross-Platform Quality
  - Article XII Contract Evolution and Decision Governance -> Article XII Durable Records, Contract Evolution and
    Decision Governance
- Added principles: none
- Removed principles: none
- Dependent artifacts:
  - ✅ .specify/templates/spec-template.md
  - ✅ .specify/templates/plan-template.md
  - ✅ .specify/templates/tasks-template.md
  - ✅ spec-kit/CONSTITUTION_SOURCE.md
  - ✅ AGENTS.md
  - ✅ CONTRIBUTING.md
  - ✅ START_HERE.md
  - ✅ spec-kit/OPERATING_PROCEDURE.md
  - ✅ docs/12_SPEC_KIT_INTEGRATION.md
  - ✅ specs/README.md
  - ✅ scripts/validate_repository.py and repository tests
- Deferred follow-up: none
-->

# OpenARDP Constitution

## Article I — Source Truth and Evidence Preservation

1. Original source bytes are immutable and authoritative.
2. OpenARDP MUST never silently overwrite, rewrite or normalize an original source file.
3. Every provider-native representation, evidence projection, normalized block, derived artifact and context bundle MUST
   retain sufficient provenance to identify the exact source version, source location and generating component.
4. A compact or derived representation MUST never permanently replace access to original evidence.
5. Immutable evidence facts are append-only; mutable heads MUST be explicit pointers.

**Rationale:** OpenARDP optimizes repeated access while preserving the evidence from which every interpretation derives.

## Article II — Derived Data and Disposable Accelerators

1. Native parser outputs, evidence projections, OCR, captions, summaries, embeddings, classifications and indexes are
   derived artifacts.
2. Every derived artifact MUST record its generating component, component version, input content hash and creation time.
3. Derived artifacts MUST be invalidatable and reproducible.
4. Embeddings MUST remain optional and model-specific; they MUST NOT be treated as a universal interchange format or as
   authoritative content.
5. Search indexes and caches are rebuildable accelerators, not evidence. Returned content and security-sensitive
   metadata MUST be verified against authoritative content-addressed objects and catalog facts.

## Article III — Implementation First, Reuse and Provider Neutrality

1. OpenARDP MUST be developed and communicated as an implementation-first open-source reference platform before any
   claim of a standard.
2. Public contracts are experimental interoperability candidates until documented external-use evidence, an independent
   implementation, conformance evidence and migration practice justify stabilization.
3. Established standards such as W3C PROV, Web Annotation, JSON Schema and RFC 8785 MUST be reused where they satisfy the
   requirement. A new project-owned abstraction requires an ADR explaining why prior art is insufficient.
4. Parser, OCR, caption, embedding, language-model, storage and source connectors MUST sit behind narrow ports.
5. No cloud service or proprietary provider may become mandatory for the core package.
6. The default installation MUST operate locally without external model calls, user tracking or network egress. Egress
   MUST be explicit, configurable and disabled by default.

## Article IV — Thin Evidence Projection

1. Complete provider-native document representations MUST remain available as immutable, versioned derived artifacts.
2. OpenARDP MUST NOT create a second complete provider-neutral document representation.
3. Provider-neutral projections MUST contain only fields needed for evidence identity, navigation, retrieval, trust and
   lifecycle.
4. Provider-specific pointers MUST remain opaque and profile-scoped; cross-provider semantic equivalence MUST NOT be
   claimed without reproducible conformance evidence.

**Rationale:** Thin projections preserve fidelity and provider independence without duplicating a parser’s full model.

## Article V — Data Is Not Instruction and Execution Is Bounded

1. Document and model-derived content is untrusted data, not an instruction or policy channel.
2. Natural-language text extracted from a document MUST never directly authorize or invoke a side-effecting tool.
3. Parser and model-provider execution MUST use narrow ports with explicit resource, path, network and time limits.
4. A portable worker process MUST be described as bounded isolation, not as a universally strong sandbox.
5. Archive extraction MUST prevent path traversal, decompression bombs and unsafe links.
6. The MVP MCP interface MUST be read-only and MUST NOT provide arbitrary filesystem reach.

## Article VI — Determinism, Identity and Atomicity

1. Persisted content identity MUST use SHA-256, canonical serialization and documented algorithm versions.
2. Python’s randomized `hash()` MUST NOT be used for persisted identity.
3. Durable writes MUST be atomic.
4. Concurrent duplicate ingestion MUST converge on one valid stored object.
5. Public schemas and contracts MUST use explicit semantic versions and reject unsupported major versions.

## Article VII — Progressive Context Delivery

1. The system MUST prefer outlines, metadata and summaries before full blocks or visual evidence.
2. Context compilation MUST be task-aware, budget-aware and version-pinned.
3. The compiler MUST surface when visual or original evidence is required rather than inventing unavailable detail.
4. Context bundles MUST remain auditable and cite exact evidence selections.
5. Selection receipts MUST identify the inputs, policy, limits, selected evidence and deterministic ordering needed to
   explain a bounded result.

## Article VIII — Test-First Quality Gates

1. Tests are mandatory for every behavior or contract change and SHOULD precede implementation where practical.
2. Security boundaries, identity algorithms, schema compatibility, cache invalidation, source immutability and migration
   behavior require explicit automated tests.
3. Unit tests MUST run without network access.
4. Test fixtures MUST be synthetic or legally redistributable.
5. No task is complete until Ruff, format checks, strict mypy, pytest and the repository’s build/validation gates pass.
6. A failing check MUST be fixed at its cause; tests, typing, coverage or security controls MUST NOT be weakened merely
   to pass.

## Article IX — Fair Evidence and Measured Claims

1. Performance, quality, cost, security, interoperability and sustainability claims require reproducible evidence.
2. Benchmarks MUST report environment, data set, strong baselines, raw results and known limitations.
3. Persisted provider-native reuse MUST be included as a baseline when evaluating redundant parsing claims.
4. OpenARDP MUST document cases where it does not improve performance or quality.
5. Marketing and release language MUST NOT exceed measured evidence.

## Article X — Simplicity and Incremental Delivery

1. The MVP is a modular local monolith.
2. New abstractions require at least two concrete implementations or an accepted ADR demonstrating immediate need.
3. Work proceeds in bounded, independently testable feature slices.
4. One feature MUST converge and merge before dependent work begins.
5. Microservices, mandatory vector databases, bidirectional Office synchronization and production Microsoft Graph
   access are outside the MVP unless approved by ADR.
6. A custom export format remains an experiment until existing standards and packaging profiles are evaluated with
   evidence.

## Article XI — Risk-Proportionate Change Governance and Cross-Platform Quality

1. Each branch and pull request MUST contain one bounded change concern.
2. A change MUST be classified before implementation:
   - **Routine** changes are documentation, tests, internal refactoring or narrowly bounded fixes with no user-visible
     behavior, public contract, schema, persistence, identity, migration, security/trust boundary, provider, dependency,
     benchmark or release impact. They require a scoped pull-request record and proportionate validation, not a Spec Kit
     feature directory.
   - **Standard** changes add bounded user-visible behavior without a high-assurance trigger. They require durable
     requirements in `spec.md`, final evidence in `implementation-notes.md` and proportionate planning; the complete Spec
     Kit lifecycle is optional.
   - **High-assurance** changes affect a public contract, schema, persisted identity, migration, security/trust boundary,
     provider, external dependency, license/supply chain, benchmark methodology, release decision or similarly material
     compatibility boundary. They MUST use specify, clarify, plan, checklist, tasks, analyze, implement and converge, plus
     an ADR where Article XII requires one.
3. An unknown, mixed or disputed classification MUST move upward to the safer tier.
4. Unresolved critical or high-severity analysis findings block high-assurance implementation; unresolved critical or
   high-severity convergence findings block its merge.
5. Executable changes MUST pass the applicable locked lint, formatting, strict typing, test, build and Linux, macOS and
   Windows checks defined by repository CI policy. Governance-only changes MAY use the reviewed fail-closed preflight path; tier
   selection MUST NOT weaken executable quality or security gates.
6. External dependencies require maintenance, license, security, lockfile and supply-chain review. Generated artifacts
   require deterministic regeneration and drift validation.
7. After convergence, a completed feature MUST retain accepted `spec.md`, final `implementation-notes.md` and normative
   contracts. Plans, research, data-model notes, quickstarts, task lists, analyses, checklists and generated prompts MAY be
   removed from the current tree after unique durable content and references are migrated; exact history remains in Git.

## Article XII — Durable Records, Contract Evolution and Decision Governance

1. This constitution, `AGENTS.md`, accepted ADRs and public schemas are binding project-level constraints.
2. Durable feature requirements and implementation evidence MUST trace back to these constraints. High-assurance
   `spec.md`, `plan.md` and `tasks.md` MUST remain aligned throughout implementation and convergence.
3. Conflicts MUST be corrected in the highest-level originating artifact rather than patched only in generated tasks or
   implementation.
4. Architectural changes require an accepted ADR before implementation.
5. Contract, application, workspace, provider-profile and export-profile versions MUST evolve independently.
6. Breaking public-contract changes require versioning, migration notes, fixtures and an ADR. A contract MUST NOT become
   stable without external-use evidence and an independent implementation.
7. The source-of-truth precedence is:
   - this constitution and accepted security/legal constraints;
   - accepted ADRs and public schemas;
   - canonical project architecture and product requirements;
   - active durable feature requirements and, when required, the implementation plan;
   - active task list when the selected tier uses one;
   - implementation.
8. Historical and superseded durable records MUST remain discoverable and MUST identify their replacement. Removed
   transient planning artifacts MUST remain recoverable from Git history; they need not be duplicated in a live archive.

## Governance

- **Versioning:** Semantic versioning applies to this constitution.
- **Current version:** 3.0.0
- **Ratified:** 2026-07-22
- **Last amended:** 2026-08-09
- **Amendments:** Every amendment requires rationale, affected artifacts, migration impact, a semantic version increment
  and a Sync Impact Report propagated to dependent guidance and templates.
- **Compliance:** Every change records its Article XI tier and proportionate evidence. High-assurance changes use the
  complete lifecycle. Standard and high-assurance changes retain exact commands, results, tradeoffs, residual risks and
  rollback instructions in durable evidence.
- **Review:** Pull-request review MUST verify constitution alignment, evidence discipline, compatibility impact and feature
  isolation before merge.
- **Exception process:** Temporary exceptions require an accepted ADR with owner, scope, expiry condition and compensating
  controls.
