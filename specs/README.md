# Feature specifications

This directory is managed through GitHub Spec Kit after project bootstrap.

Do not create one specification for the entire OpenARDP platform. Create one bounded feature per work package, following
[`spec-kit/FEATURE_MAP.md`](../spec-kit/FEATURE_MAP.md).

Each generated feature directory should contain at least:

```text
specs/<feature>/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

Project-wide architectural truth remains in `docs/`, `AGENTS.md`, the constitution and ADRs. Feature specifications may
refine those decisions but may not silently contradict them.

## Implemented features

| Feature | Scope | Status |
|---|---|---|
| `001-repository-baseline` | Reproducible Python/uv foundation and three-platform CI | Converged |
| `002-domain-models-schemas` | Pure records, RFC 8785 identities and reviewed JSON Schemas | Converged |
| `003-cas-sqlite-catalog` | Immutable filesystem CAS, transactional catalog, durable jobs and reachability | Converged |
| `004-text-ingestion-slice` | Safe TXT/Markdown ingestion, verified cache and progressive local CLI navigation | Converged |
| `005-lexical-search` | Exact source-backed FTS5 retrieval, coverage/reindex and `search`/`reindex` CLI | Converged and merged |
| `005A-strategic-realignment` | Implementation-first governance, contract boundary and v3.1 roadmap with no runtime change | Converged, merged and remotely verified |
| `006-evidence-contract-foundation` | Experimental native/evidence/trust roots, anchor fixtures and adapter-independent validation | Converged, merged and remotely verified |
| `007-docling-native-adapter` | Offline bounded Docling PDF/DOCX/PPTX native artifacts and F006 thin evidence | Converged, merged and remotely verified |
| `008-context-compiler-receipts` | Deterministic context compiler, `ContextBundle 0.2.0`, `SelectionReceipt 0.1.0`, replay and `context`/`context-receipt` CLI | Converged, merged and remotely verified |
| `009-read-only-mcp` | Least-privilege read-only MCP stdio server, nine object-scoped tools, versioned error taxonomy and `mcp` CLI verb | Converged, merged and remotely verified |
| `010-reconciliation-derivation-dag` | Conservative lineages, exact reuse bindings and transactional derivation invalidation/reactivation | Converged, merged and remotely verified |
| `011-visual-evidence-escalation` | Explicit bounded PDF raster/crop evidence, handle-only context and optional untrusted interpretation | Converged, merged and remotely verified |
| `012-local-watcher-and-jobs` | Bounded explicit local polling, durable stability/tombstones and cancellable ingestion jobs | Converged, merged and remotely verified |
| `013-retention-recovery-migrations` | Verified backups, revision-9 migration, retention, quarantine, restore and explicit reclamation | Converged, merged and remotely verified |
| `014-export-interchange-experiment` | Deterministic bounded BagIt exchange profile, hostile verification and fresh read-only import | Converged, merged and remotely verified |
| `015-benchmark-security-release-gate` | Frozen benchmarks, security/supply-chain/reproduction evidence and fail-closed v0.1 gate | Converged, merged and remotely verified; candidate remains `NO-GO` |
| `016-alternate-parser-conformance-spike` | Isolated independent evidence consumer, non-Docling TXT/CSV producer and bounded neutrality decision | Converged, merged and remotely verified; scoped claim supported, contract remains experimental |
| `017-microsoft-graph-design-spike` | Mock-only tenant-scoped delta, permission, tombstone, retry and notification architecture | Implemented; mock architecture `GO`, production connector `NO-GO` |
| `018-repository-hygiene` | Behavior-preserving hotspot decomposition, truthful focused validation and deterministic maintainability guard | Implemented locally; release and production-connector decisions unchanged |
| `019-ci-cost-optimization` | Event-aware lower-cost CI with unchanged final three-platform tests and bounded release evidence | Converged, merged and remotely verified |
| `020-product-value-benchmark` | Reproducible end-to-end value, scale and rich-reuse benchmark with a three-state worth-it decision | Converged, merged and remotely verified; `CONDITIONALLY_WORTHWHILE` |
| `021-incremental-freshness` | Exact bounded HEAD freshness plus explicit exhaustive FULL integrity and frozen 10k/100k evidence | Active; local benchmark `PASS` |
| `022-storage-amplification` | Compact derived block storage with exact logical verification and migration evidence | Converged, merged and remotely verified |
| `023-offline-pdf-model-bundle` | Explicit offline Docling PDF model package, verification and measured conversion | Converged, merged and remotely verified |
| `024-redistributable-realworld-corpus` | Licensed frozen six-format NASA/CISA corpus and structural baseline | Converged, merged and remotely verified |
| `025-semantic-e2e-source-evaluation` | Frozen real-world semantic questions, citations and honest readiness decision | Converged, merged and remotely verified; `SEMANTIC_E2E_NOT_READY` |
| `026-relevance-abstention` | Minimum lexical relevance and explicit deterministic abstention | Converged, merged and remotely verified |
| `027-lexical-ranking-diversity` | Deterministic lexical ranking, deduplication, diversity and source quotas | Converged, merged and remotely verified |
| `028-csv-ingestion` | Stable lossless logical CSV ingestion, retrieval and frozen Q15/Q16 evidence | Converged, merged and remotely verified; `CSV_INGESTION_READY` |
| `029-provider-neutral-multilingual-retrieval` | Optional offline semantic provider, hybrid retrieval and frozen multilingual comparison | Converged, merged and remotely verified; v0.3 `PROVIDER_RETRIEVAL_READY` |
| `030-semantic-retrieval-product-surface` | Opt-in CLI/MCP semantic retrieval, exact replay and frozen cold/warm operational evidence | Converged; `SEMANTIC_SURFACE_READY`, publication pending |

## Release evidence registry

Feature 015 normative inputs live under `benchmarks/release/v0.1.0/`. Generated public
evidence lives under `release/evidence/v0.1.0/` and must be regenerated only through the
documented scripts. Corpus sources are synthetic or redistributable; generated reports,
claim maps, checksums and the SBOM are disposable projections. The source allowlist
excludes generated release evidence, VCS state, caches and build output so candidate
identity is not self-referential.

The active-feature locator is `.specify/feature.json`. A later work package must not be started by adding behavior to an
earlier feature directory.
