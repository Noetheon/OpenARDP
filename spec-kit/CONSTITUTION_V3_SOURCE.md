# OpenARDP Constitution v3 adoption source

> **Status:** Adoption source, not authoritative. The ratified project constitution is
> [`CONSTITUTION_SOURCE.md`](CONSTITUTION_SOURCE.md), mirrored at
> [`.specify/memory/constitution.md`](../.specify/memory/constitution.md).

This preserved v3.1 source records the concise principles reviewed during Feature 005A. Where wording differs, the
ratified Constitution 2.0.0 governs because it reconciles these principles with all pre-existing security and engineering
obligations.

## I. Source truth and evidence

Original source bytes are authoritative. Native parser outputs, evidence projections, indexes, summaries, OCR, captions
and embeddings are derived artifacts with explicit provenance and freshness.

## II. Implementation first

The project builds useful open-source software before claiming a standard. Public contracts are experimental
interoperability candidates until adoption criteria are met.

## III. Reuse before reinvention

Use Docling for rich document understanding. Reuse established standards such as W3C PROV, Web Annotation, JSON Schema
and RFC 8785 where applicable. New project-owned abstractions require an ADR explaining why existing standards are
insufficient.

## IV. Thin evidence projection

OpenARDP must not create a second complete document IR. Provider-native representations remain available.
Provider-neutral projections contain only fields needed for evidence identity, navigation, retrieval, trust and
lifecycle.

## V. Data is not instruction

Source documents and model-derived content are untrusted data. Ingestion cannot create executable instructions or trusted
policy.

## VI. Deterministic identity and immutable facts

Source versions, native representations and derived artifacts use versioned deterministic identity projections.
Immutable facts are append-only; mutable heads are explicit pointers.

## VII. Disposable accelerators

Search indexes, caches and projections are rebuildable. Authoritative objects live in verified CAS/catalog records.
Returned content and security-sensitive metadata must be verified.

## VIII. Bounded execution

Parsers and model providers run behind narrow ports with explicit resource, network and timeout constraints. Core tests
remain offline.

## IX. Fair evidence

Performance, quality and security claims require reproducible benchmarks against strong baselines, especially persisted
DoclingDocument reuse.

## X. Feature isolation

One bounded Spec Kit feature per branch/PR. The flow is specify → clarify → plan → checklist → tasks → analyze → implement
→ converge. Critical/high findings block implementation or merge.

## XI. Cross-platform quality

Linux, macOS and Windows CI, locked dependencies, lint, formatting, strict typing, tests and build are mandatory.

## XII. Evolution

Breaking public-contract changes require versioning, migration notes, fixtures and an ADR. No contract becomes stable
without external-use evidence.
