# ADR 0010: Define minimal contracts before rich-parser adapters

Status: Accepted

Date: 2026-07-26

## Context

If the first rich-parser adapter defines the public evidence model while it is implemented, provider-specific details can
become accidental shared contracts. A later alternate parser would then confirm only that it can imitate Docling rather
than test whether the boundary is truly provider-neutral.

## Decision

Feature 006 defines the smallest experimental provider-neutral native-artifact, evidence-anchor, trust, and lifecycle
contracts required by the roadmap. Feature 007 then implements the Docling adapter against those contracts.
Provider-specific pointers remain opaque and profile-scoped.

Contract, application, workspace, provider-profile, and export-profile versions evolve independently. Contracts may
change after migration notes and fixtures during the experimental phase; stabilization additionally requires external
use, independent implementation, conformance evidence, and compatibility practice.

## Consequences

- Feature 006 is contract-foundation work and does not add a rich parser.
- Feature 007 cannot invent a parallel public model.
- Feature 016 tests or falsifies provider neutrality with an alternate parser or consumer.
- Contract examples in Feature 005A are design guidance, not public schemas.
- Later additions follow the documented contract lifecycle and migration policy.

## Alternatives considered

- Let Feature 007 define contracts opportunistically: rejected because the adapter would dictate the abstraction.
- Wait until multiple full adapters exist before documenting any shared fields: rejected because the first adapter still
  needs a bounded, reviewable integration target.
