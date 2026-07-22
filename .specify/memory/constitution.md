# OpenARDP Constitution

<!-- This is the authoritative source copied to .specify/memory/constitution.md by the bootstrap script. -->

## Article I — Evidence Preservation

1. Original source documents are immutable and authoritative.
2. OpenARDP MUST never silently overwrite, rewrite or normalize an original source file.
3. Every normalized block, derived artifact and context bundle MUST retain sufficient provenance to identify the exact
   source document version and source location.
4. A compact representation MUST never permanently replace access to original evidence.

**Rationale:** OpenARDP optimizes repeated access, not truth itself.

## Article II — Derived Data Is Disposable

1. OCR, captions, summaries, embeddings, classifications and indexes are derived caches.
2. Every derived artifact MUST record its generating component, component version, input content hash and creation time.
3. Derived artifacts MUST be invalidatable and reproducible.
4. Embeddings MUST remain optional and model-specific; they MUST NOT be treated as a universal interchange format or as
   authoritative content.

## Article III — Local-First and Provider-Neutral Core

1. The default installation MUST operate locally and without external model calls.
2. Parser, OCR, caption, embedding, language-model, storage and source connectors MUST sit behind narrow ports.
3. No cloud service or proprietary provider may become mandatory for the core package.
4. Network egress MUST be explicit, configurable and disabled by default.

## Article IV — Untrusted Document Boundary

1. Document content is untrusted data, not an instruction channel.
2. Natural-language text extracted from a document MUST never directly authorize or invoke a side-effecting tool.
3. Parser execution MUST be isolated with resource, path and time limits.
4. Archive extraction MUST prevent path traversal, decompression bombs and unsafe links.
5. The MVP MCP interface MUST be read-only.

## Article V — Determinism, Identity and Atomicity

1. Persisted content identity MUST use SHA-256, canonical serialization and documented algorithm versions.
2. Python's randomized `hash()` MUST NOT be used for persisted identity.
3. Durable writes MUST be atomic.
4. Concurrent duplicate ingestion MUST converge on one valid stored object.
5. Public schemas MUST use explicit semantic versions and reject unsupported major versions.

## Article VI — Progressive Context Delivery

1. The system MUST prefer outlines, metadata and summaries before full blocks or visual evidence.
2. Context compilation MUST be task-aware, budget-aware and version-pinned.
3. The compiler MUST surface when visual or original evidence is required rather than inventing unavailable detail.
4. Context bundles MUST remain auditable and cite exact evidence selections.

## Article VII — Test-First Quality Gates

1. Tests are mandatory, not optional, for every behavior or contract change.
2. Security boundaries, identity algorithms, schema compatibility, cache invalidation and source immutability require
   explicit automated tests.
3. Unit tests MUST run without network access.
4. Test fixtures MUST be synthetic or legally redistributable.
5. No task is complete until Ruff, format checks, strict mypy and pytest pass.
6. A failing check MUST be fixed at its cause; tests, typing or security controls MUST NOT be weakened merely to pass.

## Article VIII — Measured Claims

1. Performance, quality, cost and sustainability claims require reproducible benchmark evidence.
2. Benchmarks MUST report environment, data set, baselines, raw results and known limitations.
3. OpenARDP MUST document cases where it does not improve performance or quality.
4. Marketing language MUST not exceed measured evidence.

## Article IX — Simplicity and Incremental Delivery

1. The MVP is a modular local monolith.
2. New abstractions require at least two concrete implementations or a documented ADR demonstrating immediate need.
3. Work proceeds in bounded, independently testable feature slices.
4. One feature MUST pass specification, analysis, implementation and convergence gates before dependent work begins.
5. Microservices, mandatory vector databases, bidirectional Office synchronization and production Microsoft Graph access
   are outside the MVP unless approved by ADR.

## Article X — Specification and Decision Governance

1. This constitution, `AGENTS.md`, accepted ADRs and public schemas are binding project-level constraints.
2. Feature `spec.md`, `plan.md` and `tasks.md` MUST trace back to these constraints.
3. Conflicts MUST be corrected in the originating artifact rather than patched only in generated tasks or code.
4. Architectural changes require an ADR before implementation.
5. The source-of-truth precedence is:
   - Constitution and accepted security/legal constraints;
   - accepted ADRs and public schemas;
   - project architecture and product requirements;
   - active feature specification and plan;
   - task list;
   - implementation.
6. Constitution amendments require rationale, affected artifacts, migration impact and a version increment.

## Governance

- **Versioning:** Semantic versioning applies to this constitution.
- **Current version:** 1.0.0
- **Ratified:** 2026-07-22
- **Last amended:** 2026-07-22
- **Compliance:** Every production-relevant feature uses the full Spec Kit flow: constitution, specify, clarify, plan,
  checklist, tasks, analyze, implement and converge.
- **Exception process:** Temporary exceptions require an ADR with owner, scope, expiry condition and compensating controls.
