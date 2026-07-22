# OpenARDP — Open Agent-Ready Document Package

> Working title. Ownership, employer-IP, public naming and trademark checks are still required before public release.

OpenARDP is a local-first, provider-neutral reference architecture for **parse once, reuse many** document intelligence.
It is designed to prepare PDF, DOCX, PPTX and related files once, preserve a versioned and provenance-rich intermediate
representation, and let agents retrieve the smallest sufficient evidence instead of reparsing entire files for every task.

## Current status

The repository implements the roadmap one bounded GitHub Spec Kit feature at a time. Features
`001-repository-baseline` and `002-domain-models-schemas` established the reproducible foundation and public domain
contracts. Feature `003-cas-sqlite-catalog` adds the first local persistence slice:

- Python 3.12 and uv with a committed lock;
- installable package metadata and empty architecture namespaces;
- Ruff, formatting, strict mypy, offline pytest/coverage and pre-commit gates;
- least-privilege cross-platform CI configuration;
- observed green Ubuntu, macOS and Windows GitHub Actions execution;
- offline Markdown/governance validation;
- license, contribution, security and validation evidence.
- strict, frozen Pydantic v2 models for Manifest, Block, Derivation, Relation and Context Bundle;
- five reviewed JSON Schema Draft 2020-12 contracts with synthetic golden fixtures;
- strict raw-JSON validation, RFC 8785 canonical bytes and versioned SHA-256 identity projections;
- deterministic schema regeneration and drift checks;
- an immutable streaming filesystem CAS with atomic same-filesystem publication and full integrity verification;
- a checksummed, transactionally migrated SQLite catalog for exact source keys, source-version facts and fenced jobs;
- provider-neutral object-store/catalog ports plus persistence and read-only reachability services;
- deterministic crash, concurrency, path-safety, migration, restart and reclamation-candidate tests.

There is deliberately **no document parser, normalized ingestion workflow, search/index, context compiler, MCP server,
watcher, model provider, cloud connector, automatic garbage deletion or `openardp` product command yet**. F003 exposes a
Python library persistence boundary; parsing and end-user workflows belong to later features in
[the feature map](spec-kit/FEATURE_MAP.md).

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

The wheel exposes `openardp.__version__`, `py.typed`, the pure `openardp.domain` record/identity API, provider-neutral
persistence ports, reviewed filesystem/SQLite adapters and persistence/reachability services. The `interfaces` namespace
remains empty until a later CLI/MCP feature.

Validate or regenerate the reviewed public schemas with:

```bash
uv run --locked python scripts/generate_schemas.py --check
uv run --locked python scripts/generate_schemas.py --write  # explicit review action only
```

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

Dependencies point inward. Feature 003 keeps storage I/O in adapters and cross-resource ordering in services; domain
models remain pure and provider-neutral.

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
