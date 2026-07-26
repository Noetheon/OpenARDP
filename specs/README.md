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
| `007-docling-native-adapter` | Offline bounded Docling PDF/DOCX/PPTX native artifacts and F006 thin evidence | Locally converged; remote verification pending |

The active-feature locator is `.specify/feature.json`. A later work package must not be started by adding behavior to an
earlier feature directory.
