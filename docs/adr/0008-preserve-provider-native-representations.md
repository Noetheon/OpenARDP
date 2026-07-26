# ADR 0008: Preserve provider-native representations and project thin evidence

Status: Accepted

Date: 2026-07-26

Supersedes in part: [ADR 0001](0001-use-docling-as-default-parser.md)

## Context

Rich parsers such as Docling already expose detailed document models. Recreating a complete provider-neutral document
model would duplicate that work, lose provider-specific fidelity, enlarge the compatibility surface, and risk encoding
the first provider’s assumptions as a nominally neutral contract.

## Decision

Store the complete provider-native representation unchanged as an immutable, versioned derived artifact with exact
provenance. OpenARDP creates only a thin provider-neutral evidence projection containing fields required for evidence
identity, navigation, retrieval, trust, and lifecycle.

Provider-specific pointers remain opaque and provider-profile scoped. OpenARDP does not guarantee complete semantic
equivalence across providers. Clients that need advanced provider semantics retrieve the native artifact.

## Consequences

- Native artifacts and projections are reproducible, invalidatable derived data; originals remain authoritative.
- The provider-neutral surface stays small enough to evaluate with a second parser or consumer.
- Adapter changes cannot silently rewrite a retained native artifact.
- Provider-profile versions evolve independently from contract, application, workspace, and export-profile versions.
- The “map to OpenARDP IR” phrase in ADR 0001 is superseded; Docling remains the planned default rich parser.

## Alternatives considered

- Create a complete OpenARDP rich-document IR: rejected because it duplicates provider models and weakens fidelity.
- Expose Docling internals directly as the neutral contract: rejected because it prevents meaningful provider
  independence.
