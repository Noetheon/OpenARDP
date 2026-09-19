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
Routine and standard maintenance outside that sequence follows the risk-proportionate governance tiers and does not
require artificial roadmap entries.

## Current expansion pause

After F037/F038, prioritize the [existing local document workflow](30_LOCAL_DOCUMENT_WORKFLOW.md), necessary maintenance
and the [bounded prospective pilot](../specs/038-local-document-pilot-readiness/contracts/pilot-protocol.md).
Do not start a broader feature roadmap merely because the foundation exists. New GUI, cloud, HTTP, connector, provider,
export or specification-stabilization work needs a demonstrated workflow need and a subsequent bounded decision.

The pilot compares current work, a usable parse-once native cache and OpenARDP on 30 distinct real tasks. It counts
setup, checking and repair; human supporting-span review starts pending. The predeclared stop rule is 20 additional
person-hours or ten working days. Missing evidence or unmet gates means pausing expansion. A personal limited-GO does
not establish adoption: broader open-source investment additionally needs at least two independent repeat users.
No pilot result changes the independent F015 release gate.

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
