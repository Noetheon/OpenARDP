# OpenARDP — Open Agent-Ready Document Package

> **Working title. Public naming and trademark checks are still required.**

OpenARDP is a local-first, provider-neutral reference architecture for **parse once, reuse many** document intelligence.
It prepares PDF, DOCX, PPTX and related files once, stores a versioned and provenance-rich intermediate representation,
and lets coding agents or assistants retrieve only the evidence they need instead of reparsing entire files on every task.

This revision integrates **GitHub Spec Kit for Codex** so the platform is implemented through bounded specifications,
quality gates and convergence checks rather than one uncontrolled generation pass.

## The problem

Large Office files and PDFs impose repeated cost:

- document parsing and layout reconstruction;
- OCR and image understanding;
- table and chart extraction;
- repeated prompt/context assembly;
- repeated embeddings and summaries;
- long delays before the actual task can begin.

OpenARDP does **not** claim to make a universal latent vector that every model understands. It creates a durable, open,
machine-readable document layer and a context compiler that progressively discloses the smallest sufficient evidence.

## Product thesis

> **Compress access, not truth.**

The original file remains authoritative. Parsed blocks, summaries, OCR, captions, embeddings and indexes are derived,
versioned caches with explicit provenance and invalidation rules.

## What is included

- Product requirements, non-goals and measurable outcomes
- Architecture and component boundaries
- OpenARDP package and data model
- Incremental update and cache invalidation design
- CLI and read-only MCP contracts
- Security threat model and controls
- Benchmark and test strategy
- Open-source and enterprise roadmap
- Architecture Decision Records and JSON Schemas
- Python repository scaffold and basic tests
- GitHub Spec Kit constitution and pinned bootstrap
- A bounded feature map for all 14 work packages
- Ready-to-use feature prompts for Codex
- macOS/Linux and Windows setup scripts
- Step-by-step operating procedure

## Which ZIP should be used?

For a new Codex implementation, use this **Spec-Kit-integrated revision**. The previous ZIP remains a valid architecture
blueprint, but this package adds the safer execution workflow and should replace it before coding begins.

See [`docs/14_MIGRATION_FROM_PREVIOUS_BLUEPRINT.md`](docs/14_MIGRATION_FROM_PREVIOUS_BLUEPRINT.md).

## Start here

### 1. Initialize Git

```bash
git init
git add .
git commit -m "chore: add OpenARDP architecture and Spec Kit blueprint"
```

### 2. Bootstrap Spec Kit

macOS/Linux:

```bash
bash scripts/bootstrap-speckit.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/bootstrap-speckit.ps1
```

### 3. Review and commit the generated Spec Kit integration

```bash
git status
git add .
git commit -m "chore: initialize Spec Kit for Codex"
```

### 4. Open Codex in the repository root

Paste [`spec-kit/FIRST_CODEX_SESSION.md`](spec-kit/FIRST_CODEX_SESSION.md). Do not ask Codex to implement the complete
platform in one pass.

### 5. Implement one bounded feature at a time

Begin with `001-repository-baseline`, following [`spec-kit/FEATURE_MAP.md`](spec-kit/FEATURE_MAP.md).

## Required Spec Kit lifecycle

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

Project-wide truth remains in the constitution, `AGENTS.md`, accepted ADRs, schemas and `docs/`. Feature-specific
artifacts are generated under `specs/`.

## Recommended build strategy

1. **Do not build document parsing from scratch.** Use Docling as the default rich parser through an adapter.
2. Build the unique layer around it: durable identity, content-addressed storage, normalized blocks, provenance, change
   detection, derived-artifact invalidation, context compilation and agent interfaces.
3. Prove the benefit on a benchmark before building SharePoint or enterprise integrations.
4. Keep the first implementation a modular local monolith.
5. Treat documents as untrusted data and keep MCP read-only in the MVP.

## Intended command experience after implementation

```bash
uv sync --all-extras
uv run openardp init
uv run openardp ingest ./examples/files/report.docx
uv run openardp status ./examples/files/report.docx
uv run openardp search --document <document-id> "comparison study"
uv run openardp context --document <document-id> --query "Compare the three conditions" --budget 4000
uv run openardp watch ./documents
uv run openardp mcp
```

The current repository is a blueprint and scaffold; these commands are implemented incrementally through the feature map.

## Read first

1. [`docs/00_EXECUTIVE_BRIEF.md`](docs/00_EXECUTIVE_BRIEF.md)
2. [`docs/01_PRODUCT_REQUIREMENTS.md`](docs/01_PRODUCT_REQUIREMENTS.md)
3. [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md)
4. [`docs/06_SECURITY_THREAT_MODEL.md`](docs/06_SECURITY_THREAT_MODEL.md)
5. [`docs/09_CODEX_EXECUTION_PLAN.md`](docs/09_CODEX_EXECUTION_PLAN.md)
6. [`docs/12_SPEC_KIT_INTEGRATION.md`](docs/12_SPEC_KIT_INTEGRATION.md)
7. [`docs/13_STEP_BY_STEP_USER_GUIDE.md`](docs/13_STEP_BY_STEP_USER_GUIDE.md)
8. [`AGENTS.md`](AGENTS.md)

## License recommendation

Apache-2.0 is recommended for code and specifications because it is permissive and includes an explicit patent grant.
Confirm ownership and employer IP requirements before public release.
