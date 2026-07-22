# Roadmap, open-source governance and enterprise path

## Phase 0 — discovery and spike (1–2 weeks)

- benchmark Docling, Docling MCP, MarkItDown and MinerU on representative redistributable files;
- validate licenses and model licenses;
- create architecture decision records;
- implement text-only vertical slice;
- establish benchmark harness.

Exit: parser strategy and MVP scope confirmed with measured evidence.

## Phase 1 — local MVP (4–8 weeks)

- SQLite catalog and filesystem CAS;
- TXT/MD and Docling adapters;
- immutable versions, normalized blocks and provenance;
- unchanged-version skip;
- FTS search;
- basic context compiler;
- CLI and read-only MCP;
- local watcher;
- tests and benchmark.

Exit: parse-once benefit is demonstrated without a cloud dependency.

## Phase 2 — credible open-source release (6–12 additional weeks)

- portable `.ardp.zip` import/export;
- block reconciliation and derived-artifact DAG;
- image/table evidence and lazy enrichment;
- optional embedding adapters;
- stable schemas and compatibility suite;
- documentation site, examples and contributor workflow;
- SBOM, OpenSSF/REUSE/security policy;
- releases for macOS/Linux/Windows.

Exit: independent users can integrate a second parser or client using documented contracts.

## Phase 3 — authoring and publishing experiments

- structured agent output (`claims`, `evidence`, `tables`, `figures`);
- renderers for Markdown/HTML first, Office/PDF later;
- no bidirectional round-trip guarantee;
- evaluate single-source publishing separately from ingestion.

Exit: prove that generated artifacts can remain linked to canonical content without corrupting human workflows.

## Phase 4 — enterprise pilot

- service deployment, queue and worker isolation;
- Microsoft Graph change notifications + delta reconciliation;
- Entra ID and permission-aware retrieval;
- Azure Blob/PostgreSQL or approved equivalents;
- audit, data retention, classification and DLP integration;
- tenant isolation, quotas and operational SLOs;
- security assessment and privacy review.

Exit: approved limited-scope SharePoint library pilot.

## Phase 5 — standardization proposal

Only after multiple implementations:

- publish specification/profile independently of the reference code;
- conformance test suite;
- extension registry and governance process;
- mapping to RO-Crate/PROV/JSON-LD;
- neutral technical steering and transparent enhancement proposals.

## Open-source governance

Recommended initial setup:

- Apache-2.0 license after IP review;
- Developer Certificate of Origin or lightweight CLA decision;
- public roadmap and ADRs;
- CODEOWNERS for schemas/security/workflows;
- semantic versioning;
- documented deprecation window;
- vulnerability disclosure policy;
- no telemetry without explicit opt-in;
- model and dataset license inventory.

## Sustainability principles

- optimize avoided compute, not just compressed storage;
- lazy model calls;
- local deterministic extraction first;
- publish energy/resource proxies with benchmarks;
- support CPU and offline modes;
- deduplicate by content hash;
- retention/garbage collection policies for derived artifacts;
- avoid premature microservices.

## Enterprise architecture cautions

- Preserve source ACLs and re-check authorization at retrieval time.
- Graph notifications must be reconciled with delta queries.
- Do not copy every company document into a new store without a data governance decision.
- Separate global binary deduplication from tenant authorization; content equality must not leak existence across tenants.
- Embeddings may expose sensitive semantic information and require the same protection as source text.
