# OpenARDP — Open Agent-Ready Document Package

> Working title. Ownership, employer-IP, public naming and trademark checks are still required before public release.

OpenARDP is a local-first, provider-neutral reference architecture for **parse once, reuse many** document intelligence.
It is designed to prepare PDF, DOCX, PPTX and related files once, preserve a versioned and provenance-rich intermediate
representation, and let agents retrieve the smallest sufficient evidence instead of reparsing entire files for every task.

## Current status

The repository is implementing the roadmap one bounded GitHub Spec Kit feature at a time. Feature
`001-repository-baseline` establishes only the reproducible engineering foundation:

- Python 3.12 and uv with a committed lock;
- installable package metadata and empty architecture namespaces;
- Ruff, formatting, strict mypy, offline pytest/coverage and pre-commit gates;
- least-privilege cross-platform CI configuration;
- offline Markdown/governance validation;
- license, contribution, security and validation evidence.

There is deliberately **no document parser, domain document model, hashing API, database, ingestion, search, context
compiler, MCP server, watcher, model provider, cloud connector or `openardp` product command yet**. Those capabilities
belong to later features in [the feature map](spec-kit/FEATURE_MAP.md).

## Product thesis

> Compress access, not truth.

Original files remain authoritative. Parsed blocks, summaries, OCR, captions, embeddings and indexes are derived,
versioned caches with explicit provenance and invalidation rules. Embeddings stay optional and model-specific; document
content is untrusted data, never an instruction channel.

## Why OpenARDP is not simply another RAG layer

OpenARDP's planned differentiators are:

1. portable, validated package contracts;
2. durable document/version/block identity;
3. content-addressed original and derived artifacts;
4. explicit dependency and invalidation graphs;
5. source-versus-derived trust separation;
6. budget-aware, evidence-preserving context compilation;
7. local automation and later least-privilege enterprise connectors;
8. reproducible evaluation of latency, cost, quality and security.

The architecture uses Docling through a future adapter rather than rebuilding a PDF/Office parser. SQLite, filesystem CAS,
read-only MCP and optional embeddings remain governed by the accepted/proposed ADR status in `docs/adr/`.

## Prerequisites

- Git
- uv 0.11.31
- Linux, macOS or Windows

The project selects Python 3.12 through `.python-version`. A newer global Python does not replace the project environment.

## Set up a clean checkout

```bash
uv sync --all-extras --locked
```

This installs the package and mandatory development group from `uv.lock`. Locked mode fails when dependency metadata and
the lock disagree; it does not silently rewrite the lock. The repository enables uv's bounded
`centralized-project-envs` preview: the disposable environment lives in uv's cache while the conventional `.venv` path
remains available to editors as a discovery link when the host filesystem permits it. If a file provider blocks that
link, uv still resolves the centralized environment directly.

## Run the authoritative quality gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Pytest includes branch coverage, an 85 percent threshold, socket blocking and offline repository/documentation checks.

Validate the repository directly with:

```bash
uv run python scripts/validate_repository.py
```

## Enable commit-time checks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

The hooks use the locked project tools rather than separately resolved hook environments.

## Build the baseline package

```bash
uv build
```

The wheel currently exposes only `openardp.__version__`, `py.typed` and the `domain`, `ports`, `adapters`, `services` and
`interfaces` namespaces.

## Spec Kit workflow

Project-wide constraints live in the [Constitution](.specify/memory/constitution.md), [AGENTS.md](AGENTS.md), accepted ADRs,
public schemas and `docs/`. Feature-specific truth lives under `specs/<feature>/`.

Every production-relevant feature follows:

```text
specify → clarify → plan → checklist → tasks → analyze → implement → converge
```

Implementation is blocked by unresolved critical/high analysis findings. One feature must converge before a dependent
feature begins. See [the operating procedure](spec-kit/OPERATING_PROCEDURE.md) and
[contribution guide](CONTRIBUTING.md).

## Architecture boundaries

- `domain/`: pure models and invariants; no I/O.
- `ports/`: narrow provider-neutral protocols.
- `adapters/`: parsers, stores, sources and providers.
- `services/`: use cases and orchestration.
- `interfaces/`: CLI, MCP and later HTTP entry points.

Dependencies point inward. Feature 001 creates only the namespaces; later features add tested contracts and behavior.

## Read first

1. [Executive brief](docs/00_EXECUTIVE_BRIEF.md)
2. [Product requirements](docs/01_PRODUCT_REQUIREMENTS.md)
3. [Architecture](docs/02_ARCHITECTURE.md)
4. [Security threat model](docs/06_SECURITY_THREAT_MODEL.md)
5. [Test and benchmark strategy](docs/07_TEST_AND_BENCHMARK_STRATEGY.md)
6. [Codex execution plan](docs/09_CODEX_EXECUTION_PLAN.md)
7. [Spec Kit integration](docs/12_SPEC_KIT_INTEGRATION.md)
8. [Feature map](spec-kit/FEATURE_MAP.md)

## Governance

- [License](LICENSE): Apache-2.0
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Validation evidence](VALIDATION.md)
- [Changelog](CHANGELOG.md)

Apache-2.0 is the repository license. It does not grant trademark rights, and it does not replace the ownership,
employer-IP, naming or trademark clearance required before public release.
