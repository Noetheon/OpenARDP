# Roadmap, claims and open-source governance

**Status:** Canonical governance summary. Exact dependency order and feature outcomes live only in the
[authoritative feature map](../spec-kit/FEATURE_MAP.md).

## Implementation-first progression

OpenARDP develops useful, measurable open-source software before considering a separate neutral specification. Public
contracts remain experimental interoperability candidates, not an announced industry standard. The implementation has
progressed through the local-first platform, evidence contracts, rich parsing, retrieval, context/MCP surfaces,
reconciliation, visual evidence, retention/recovery, interchange, benchmark gates, real-world evaluation, optional
multilingual retrieval and its bounded product surface.

Roadmap features proceed in dependency order and one dependent work package must converge before its successor begins.
Maintenance outside that sequence follows the lean change-record rules of Constitution 4.0.0 and does not
require artificial roadmap entries.

## Current direction: agent-ready documents

F040 and F041 ended the F038 expansion pause. Work concentrates on one outcome: an agent answers questions from a
person's local files with located, verifiable passages while using as little context as possible
([Agent access](32_AGENT_ACCESS.md)). Priorities come from real use recorded in the
[usage log](../pilots/usage-log/README.md) and from defects on real user paths (Constitution Article XIII). New GUI,
cloud, HTTP, connector, provider, export or specification-stabilization work still needs a demonstrated need.

The [F038 pilot protocol](../specs/038-local-document-pilot-readiness/contracts/pilot-protocol.md) remains available
for a deliberate formal comparison, and its adoption criterion still applies to claims about broader open-source value:
at least two independent repeat users. No usage result changes the independent F015 release gate. The
[20 September maintenance status](31_MAINTENANCE_STATUS.md) is kept as history.

## Adoption ladder

1. one useful reference implementation;
2. stable operator experience with public fixtures and reproducible benchmarks;
3. external users, issues and integrations;
4. an independent consumer or validator;
5. alternate implementations that test provider neutrality;
6. candidate contract stabilization with migration evidence;
7. neutral governance discussion only if adoption warrants it.

## Claims discipline

- Current behavior links to executable tests or validation evidence.
- Planned behavior is labelled planned and linked to its owning durable record.
- Experiments state hypotheses, baselines and valid negative outcomes.
- Performance, quality, cost, security, interoperability and sustainability claims require reproducible evidence.
- OpenARDP does not claim “first”, “universal”, “lossless”, “prompt-injection secure” or “better than Docling” without
  specific evidence and limitations.

## Open-source governance

- Apache-2.0 repository license; no trademark grant.
- Working name remains subject to ownership, employer-IP, naming and trademark review.
- The feature map, accepted specifications, implementation evidence, normative contracts and ADRs remain durable;
  removed working artifacts remain recoverable from Git history.
- Semantic contract evolution requires explicit deprecation and migration evidence.
- Private vulnerability reporting precedes public disclosure.
- No telemetry or external model/network call is enabled by default.
- Dependencies require maintenance, license, security, lockfile and supply-chain review.
- SBOM, checksums, build provenance, clean install, upgrade and rollback evidence belong to the release gate.

## Sustainability and enterprise boundaries

- Measure avoided compute against strong baselines, including direct native-artifact reuse.
- Keep enrichment lazy and providers optional.
- Retention, quarantine, recovery and explicit operator-driven reclamation precede automatic deletion.
- Multi-tenant services, permission-aware enterprise retrieval and production Microsoft Graph access are outside current
  behavior.
- Content equality must never leak document existence across authorization boundaries.

## Historical decision boundaries

The retained feature specifications and implementation notes record the exact decisions for individual work packages.
For example, F014 selected BagIt 1.0 plus an experimental bounded profile, F015 retained an independent release gate and
F017 authorized only a mocked Microsoft Graph design—not production tenant access.
