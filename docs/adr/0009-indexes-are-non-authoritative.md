# ADR 0009: Treat indexes as non-authoritative accelerators

Status: Accepted

Date: 2026-07-26

## Context

Feature 005 introduced lexical search over prepared evidence. Search indexes are efficient lookup structures, but they can
be incomplete, stale, corrupted, or manipulated independently from the content and trust metadata they reference.

## Decision

Full-text and future vector indexes are disposable, rebuildable accelerators. Search hits must be resolved against
authoritative catalog facts, and returned content plus security-sensitive metadata must be verified against the
content-addressed store and catalog before return.

Coverage, drift, and corruption fail closed. Ordering is total and deterministic. Index state cannot change trust labels,
source attribution, identity, or evidence content.

## Consequences

- Integrity and rebuild tooling covers missing, orphaned, and drifted index state.
- Corruption cannot silently authorize altered content or metadata.
- Rebuilding an index does not change evidence identity.
- Embeddings remain optional model-specific retrieval caches.
- Search performance work must include verification cost in its measurements.

## Alternatives considered

- Treat the index as authoritative: rejected because accelerator corruption would become evidence corruption.
- Verify only document text but trust indexed metadata: rejected because trust and attribution are security-sensitive.
