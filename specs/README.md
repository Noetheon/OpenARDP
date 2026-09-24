# Feature records

This directory contains durable records for changes to user-visible behavior, public contracts, schemas, persisted
identity, migrations, security/trust boundaries, providers or default dependencies
([Article XI](../.specify/memory/constitution.md)). Documentation, tests and narrow fixes need only their pull-request
record. [`spec-kit/FEATURE_MAP.md`](../spec-kit/FEATURE_MAP.md) is the single authoritative feature-status registry.

After a feature converges, its durable minimum is:

```text
specs/<feature>/
├── spec.md
├── implementation-notes.md
└── contracts/                 # only when the feature owns normative contracts
```

Project-wide architectural truth remains in `docs/`, `AGENTS.md`, the constitution and accepted ADRs. Feature records
may refine those decisions but may not silently contradict them.

## Working-artifact retention

Work may temporarily use plans, research notes, data models, quickstarts, task lists, analysis reports, checklists and
feature prompts while the feature is active; they are optional tools, not gates. After convergence, those working artifacts may be removed
once durable requirements, decisions, evidence and normative contracts have been consolidated and all repository
references have been migrated. Git history remains the recovery path; this policy does not rewrite history or reduce
the size of existing Git objects.

## Release evidence registry

Feature 015 normative inputs live under `benchmarks/release/v0.1.0/`. Generated public evidence lives under
`release/evidence/v0.1.0/` and must be regenerated only through the documented scripts. Corpus sources are synthetic or
redistributable; generated reports, claim maps, checksums and the SBOM are disposable projections. The source allowlist
excludes generated release evidence, VCS state, caches and build output so candidate identity is not self-referential.

The active-feature locator is `.specify/feature.json`. A later work package must not be started by adding behavior to an
earlier feature directory.
