# ADR 0001: Use Docling as the default rich parser

Status: Proposed; partly superseded by
[ADR 0008](0008-preserve-provider-native-representations.md)

## Context

OpenARDP needs high-quality PDF and Office parsing but its differentiator is not parser research. Docling provides a unified
rich document representation, multiple formats, local execution and an active open-source ecosystem.

## Decision

Use Docling behind a parser interface as the default rich parser. Preserve native output. The earlier decision to map
that output to a complete OpenARDP IR is superseded by ADR 0008: OpenARDP retains the complete provider-native artifact
and creates only a thin provider-neutral evidence projection. Maintain alternate-parser evaluation adapters or spikes.

## Consequences

- Faster MVP and less duplicated work.
- Must manage heavy dependencies, model licenses and parser resource behavior.
- Parser subprocess isolation is required.
- OpenARDP contracts cannot directly expose unstable Docling internals.
- There is no guarantee of complete semantic equivalence across parser providers.
