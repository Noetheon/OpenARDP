# Roadmap, claims and open-source governance

**Status:** Canonical governance summary. The exact dependency order and outcomes live in the
[authoritative feature map](../spec-kit/FEATURE_MAP.md).

## Implementation-first progression

OpenARDP develops useful, measurable open-source software before considering a separate neutral specification. Public
contracts are experimental interoperability candidates, not an announced industry standard.

The runtime has converged through Feature 012; Feature 013 retention, recovery and
migrations are the active locally implemented package. Features 014–017 then proceed
strictly in dependency order:

1. evidence contracts before the rich-parser adapter;
2. Docling-native preservation plus thin evidence projection;
3. context receipts and read-only MCP;
4. reconciliation, visual evidence and local jobs;
5. retention/recovery before an export decision;
6. benchmark/security/release evidence;
7. alternate-parser conformance evidence;
8. mock-only Microsoft Graph design.

One work package must converge and merge before its successor begins.

## Adoption ladder

1. one useful reference implementation;
2. stable operator experience with public fixtures and reproducible benchmarks;
3. external users, issues and integrations;
4. an independent consumer or validator;
5. an alternate parser profile that tests provider neutrality;
6. candidate contract extraction;
7. neutral governance discussion only if adoption warrants it.

## Claims discipline

- Current behavior links to executable tests or validation evidence.
- Planned behavior is labelled planned and linked to its owning feature.
- Experiments state hypotheses, baselines and valid negative outcomes.
- Performance, quality, cost, security, interoperability and sustainability claims require reproducible evidence.
- OpenARDP does not claim “first”, “universal”, “lossless”, “prompt-injection secure” or “better than Docling” without
  specific evidence and limitations.

## Open-source governance

- Apache-2.0 repository license; no trademark grant.
- Working name remains subject to ownership, employer-IP, naming and trademark review.
- Public roadmap, ADRs and full Spec Kit feature history.
- Semantic contract evolution, explicit deprecation and migration evidence.
- Private vulnerability reporting before public release.
- No telemetry or external model/network call by default.
- Dependency maintenance, license, security, lockfile and supply-chain review.
- SBOM, checksums, build provenance, clean install, upgrade and rollback evidence at the release gate.

## Sustainability and enterprise boundaries

- Measure avoided compute against strong baselines, including direct native-artifact reuse.
- Keep enrichment lazy and providers optional.
- Retention, quarantine, recovery and explicit operator-driven reclamation precede automatic deletion.
- Multi-tenant services, permission-aware enterprise retrieval and production Graph access are not current v0.1 behavior.
- Content equality must never leak document existence across authorization boundaries.
# Feature 013 completion boundary

Feature 013 implements local retention, quarantine, explicit reclamation, recovery,
paired migration and disposable-index rebuilding. Feature 014 remains solely responsible
for export/interchange experimentation; this internal backup format is not promoted as a
portable public contract.
