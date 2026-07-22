# ADR 0001: Use Docling as the default rich parser

Status: Proposed

## Context

OpenARDP needs high-quality PDF and Office parsing but its differentiator is not parser research. Docling provides a unified
rich document representation, multiple formats, local execution and an active open-source ecosystem.

## Decision

Use Docling behind a parser interface as the default rich parser. Preserve native output and map to OpenARDP IR. Maintain
MarkItDown and MinerU evaluation adapters/spikes.

## Consequences

- Faster MVP and less duplicated work.
- Must manage heavy dependencies, model licenses and parser resource behavior.
- Parser subprocess isolation is required.
- OpenARDP contracts cannot directly expose unstable Docling internals.
