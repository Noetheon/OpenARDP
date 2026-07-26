# ADR 0007: Evolve OpenARDP implementation first

Status: Accepted

Date: 2026-07-26

## Context

OpenARDP has a working local-first implementation through Feature 005, but it has no evidence of external consensus,
independent implementation, or adoption as a standard. Standards-oriented language would create expectations that the
project cannot currently support and could freeze immature contracts prematurely.

## Decision

Develop and communicate OpenARDP as an implementation-first open-source reference platform. Public contracts are
experimental interoperability candidates. A separate neutral specification may be considered only after documented
external adoption, independent implementation, conformance evidence, compatibility practice, and sustainable governance
exist.

Claims about performance, quality, security, interoperability, adoption, cost, or sustainability require reproducible
evidence and explicit limitations.

## Consequences

- The roadmap prioritizes useful software, operations, benchmarks, integrations, and falsifiable conformance evidence.
- OpenARDP makes no official, universal, consensus, namespace-registration, or standards-body claim.
- Experimental contracts may change before stabilization, but changes require version notes and migration evidence.
- Community feedback and alternate implementations can reshape provider-neutral boundaries.
- The working project name remains subject to ownership, employer-IP, naming, and trademark review.

## Alternatives considered

- Announce an external standard now: rejected because adoption and independent-implementation evidence do not exist.
- Avoid any contracts: rejected because explicit experimental contracts improve implementation discipline and later
  interoperability evaluation.
