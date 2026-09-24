# OpenARDP

**Local-first evidence infrastructure for reusable, provenance-rich documents.**

> [!NOTE]
> OpenARDP is an implementation-first open-source reference platform and a working title.
> Its public contracts are experimental interoperability candidates, not an adopted standard.
> Public naming, trademark, ownership, and employer-IP checks remain required before release.

OpenARDP prepares a document once and makes its evidence available to many AI-assisted
workflows without turning a lossy summary, embedding, or search index into the source of truth.
It preserves immutable originals, provider-native artifacts, provenance, and verifiable
citations while keeping the default runtime local and provider-independent.

**Compress access, not truth.**

## Current focus: agent-ready documents

The goal is to let an AI agent answer questions from a person's local files without wasting its context window.
The agent finds the right passage, reads only the part it needs and verifies every quote against the exact source
version before citing it. Start with [Agent access](docs/32_AGENT_ACCESS.md).

```bash
uv sync --extra docling --locked
uv run openardp add ~/Documents/manuals --store ~/openardp-store      # files or folders, safe to repeat
uv run openardp find "How often must the sensor be calibrated?" --store ~/openardp-store
uv run openardp read manual.pdf --page 12 --store ~/openardp-store
uv run openardp verify "Calibrate the sensor every morning" --store ~/openardp-store
```

For Claude Code, Codex or another MCP client, register the local read-only server once:

```bash
claude mcp add openardp -- uv run --directory /path/to/OpenARDP openardp mcp --store ~/openardp-store
```

On the same tasks, this path used 16–34 percent of the tokens of the older tool surface
([measurement](specs/040-agent-ready-access/implementation-notes.md)). That is a token measurement, not a claim about
answer quality or human time saved; real-use evidence is collected in the [usage log](pilots/usage-log/README.md).

## Why OpenARDP?

Document systems often repeat the same expensive and error-prone work: parse a file, split it
into chunks, discard parser-specific structure, and rebuild an index for every application.
This makes provenance difficult to audit and derived data easy to mistake for authoritative
evidence.

OpenARDP separates those concerns:

1. Original bytes remain authoritative and content-addressed.
2. Complete parser-native artifacts are retained without inventing a second universal document
   representation.
3. A thin evidence projection supports identity, navigation, retrieval, trust, and lifecycle
   operations.
4. Indexes, summaries, OCR output, and embeddings remain reproducible, invalidatable
   accelerators.
5. Retrieved content is verified against authoritative storage before it is returned.

## What is implemented?

| Capability | Current implementation |
| --- | --- |
| Evidence storage | Immutable filesystem content-addressed storage with a transactional SQLite catalog |
| Ingestion | TXT, Markdown, and CSV in the core; optional Docling adapters for PDF, DOCX, and PPTX |
| Retrieval | Verified lexical search by default; optional offline multilingual semantic and hybrid retrieval |
| Context assembly | Deterministic, budgeted context bundles with source diversity, abstention, and replayable receipts |
| Agent access | `find` / `read` / `verify` in the CLI and a read-only MCP server with five compact tools; optional Markdown agent view |
| Visual evidence | Explicit, on-demand PDF page-region materialization |
| Operations | Incremental freshness checks, retention, quarantine and recovery, backup, restore, and migration |
| Portability | Experimental BagIt-based package export, verification, and import |
| Evaluation | Reproducible correctness, retrieval, performance, storage, security, and release-evidence workflows |

The complete implementation sequence and authoritative status live in the
[feature map](spec-kit/FEATURE_MAP.md). Benchmark results are documented separately so that
the README does not become a collection of stale point-in-time measurements.

## Trust boundaries

OpenARDP is designed around a few explicit constraints:

- **Originals are authoritative.** Source files are never overwritten or silently modified.
- **Document content is untrusted data.** Embedded instructions cannot initiate tools or other
  side effects.
- **Derived data is disposable.** Every accelerator must be reproducible and invalidatable.
- **The core is provider-neutral.** Parsers, OCR, embedding models, and storage integrations sit
  behind bounded interfaces.
- **Local-first means local by default.** The default install enables no cloud service, external
  model call, user tracking, or telemetry.
- **Embeddings are optional.** There is no mandatory embedding model, universal vector claim, or
  persisted universal vector database.
- **Evidence retrieval is not answer generation.** The current product assembles verifiable
  evidence and context; it does not generate an answer on the user's behalf.
- **Agent access is read-only.** The MCP server and agent commands retrieve evidence but cannot
  modify the workspace. Returned text is verified against stored originals, never served from an index alone.

See the [architecture](docs/02_ARCHITECTURE.md), [security model](docs/06_SECURITY_MODEL_V2.md),
and [non-goals](docs/03_NON_GOALS.md) for the full boundaries.

## Quick start

### Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Git

Clone the repository, install the locked core environment, and prepare a folder of TXT, Markdown or CSV files:

```bash
uv sync --locked
uv run openardp add ./notes --store .openardp
uv run openardp docs --store .openardp
```

Ask, read and check:

```bash
uv run openardp find "Which exact controls are documented?" --store .openardp
uv run openardp toc notes/controls.md --store .openardp
uv run openardp read notes/controls.md --section "Access control" --store .openardp
uv run openardp verify "Access is reviewed every quarter" --store .openardp
```

Hits and excerpts carry file and line (or page and slide) locations and the short version id. `--json` returns the
standard JSON envelope. [Agent access](docs/32_AGENT_ACCESS.md) covers PDF, DOCX and PPTX, MCP clients and the
Markdown agent view.

The evidence-level commands remain available for audits: `ingest`, `list`, `status`, `outline`, `get`, `search` and
`context` with replayable selection receipts. The [document workflow](docs/30_LOCAL_DOCUMENT_WORKFLOW.md) walks through
them. Contributor gates and the wider command reference remain in [Start Here](START_HERE.md) and the
[maintainer walkthrough](docs/13_STEP_BY_STEP_USER_GUIDE.md).

## Optional capabilities

Install only the dependency group needed by the deployment:

```bash
# Rich document parsing
uv sync --extra docling --locked

# PDF visual evidence
uv sync --extra visual --locked

# Offline semantic and hybrid retrieval
uv sync --extra semantic --locked

# Development and full validation
uv sync --all-extras --locked
```

PDF parsing is fail-closed when its verified offline model bundle is unavailable; provisioning is
documented in the [offline PDF model guide](docs/22_OFFLINE_PDF_MODEL_BUNDLE.md). Semantic and
hybrid retrieval are explicit opt-ins. Lexical search remains the provider-free default, and
semantic replay binds the exact model-bundle identity. See the
[semantic retrieval product surface](docs/29_SEMANTIC_RETRIEVAL_PRODUCT_SURFACE.md).

## Current maturity

The repository identifies the current candidate as **0.1.0rc1**. The frozen release-evidence
decision is **NO-GO**; this repository must not be represented as release-ready or independently
validated. The decision, its blockers, and the evidence identities are available in the
[release report](release/evidence/v0.1.0/report.md) and
[machine-readable decision](release/evidence/v0.1.0/decision.json).

The generated claim map permits only these bounded claims:

- `claim:evidence-preserving`
- `claim:experimental-contracts`
- `claim:local-first`

It explicitly prohibits these claims for the frozen candidate:

- `claim:enterprise-performance`
- `claim:measured-parser-reuse`
- `claim:third-party-reproduced`
- `claim:three-platform-supported`
- `claim:universal-security`
- `claim:v0.1-release-ready`

This list intentionally mirrors the
[machine-readable claim map](release/evidence/v0.1.0/claim-map.json) and is validated in CI.

## Architecture

Dependencies point inward, and domain code has no infrastructure dependencies:

```text
src/openardp/
├── domain/       Pure models and invariants
├── ports/        Provider and infrastructure protocols
├── adapters/     Parsers, stores, connectors, and model providers
├── services/     Use cases and orchestration
└── interfaces/   CLI and MCP entry points
```

The content-addressed filesystem and SQLite catalog are deliberate MVP choices. Replacing them,
changing persisted identifiers, making embeddings mandatory, or enabling a cloud dependency by
default requires an accepted architecture decision record. See the
[ADRs](docs/adr/) and [target architecture](docs/05_TARGET_ARCHITECTURE.md).

## Development and validation

Install the exact locked environment and run the complete local quality gate:

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Validate repository governance and build the distribution artifacts:

```bash
uv run python scripts/validate_repository.py
uv build
```

Unit tests do not require network access. Test fixtures are synthetic or redistributable, and
performance or quality claims must be backed by reproducible evidence against declared
baselines. See [Validation](VALIDATION.md) for the evidence model and
[CI cost and quality](docs/18_CI_COST_AND_QUALITY.md) for the tiered CI strategy.

## Documentation

- [Start Here](START_HERE.md) — installation and first end-to-end workflow
- [Agent access](docs/32_AGENT_ACCESS.md) — find, read and verify from the CLI or an MCP client
- [Executive brief](docs/00_EXECUTIVE_BRIEF.md) — concise product and evidence position
- [Architecture](docs/02_ARCHITECTURE.md) — components, data flow, and trust boundaries
- [Security model](docs/06_SECURITY_MODEL_V2.md) — threat model and control design
- [Roadmap and governance](docs/08_ROADMAP_AND_GOVERNANCE.md) — delivery and decision process
- [Benchmark strategy](docs/07_TEST_AND_BENCHMARK_STRATEGY.md) — reproducible evaluation design
- [Changelog](CHANGELOG.md) — user-visible changes

## Contributing, security, and license

Contributions are welcome when they preserve the evidence model and architecture boundaries.
Read [Contributing](CONTRIBUTING.md) before opening a change. Report vulnerabilities through the
private process in [Security](SECURITY.md), not a public issue.

OpenARDP is licensed under the [Apache License 2.0](LICENSE).
