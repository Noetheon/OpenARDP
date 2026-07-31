# OpenARDP

> **Working title.** Ownership, employer-IP, public naming and trademark checks remain required before public release.

OpenARDP is an implementation-first, local-first open-source reference platform for persistent, verifiable and reusable
document evidence in AI-agent systems. It combines immutable source/version identity, content-addressed storage,
provenance, trust-aware retrieval and progressive context delivery above document-intelligence providers such as
Docling.

OpenARDP is not an adopted, official, universal or consensus standard. Its public contracts are experimental
interoperability candidates until external use, an independent implementation, conformance evidence and migration
practice justify stabilization.

## Product thesis

> Compress access, not truth.

Original source bytes remain authoritative. Complete provider-native parser representations remain available as immutable
derived artifacts. OpenARDP projects only the thin provider-neutral evidence needed for identity, navigation, retrieval,
trust and lifecycle; it does not create a second full document representation.

Summaries, OCR, captions, embeddings, projections and indexes are reproducible derived artifacts. Lexical and future
vector indexes are non-authoritative accelerators: returned content and security-sensitive metadata must be verified
against authoritative content-addressed objects and catalog facts.

## Implemented status

The repository has completed the bounded runtime work through
[`005-lexical-search`](specs/005-lexical-search/spec.md), the documentation/governance
realignment in [`005A-strategic-realignment`](specs/005A-strategic-realignment/spec.md),
and the experimental contract foundation in
[`006-evidence-contract-foundation`](specs/006-evidence-contract-foundation/spec.md), plus
the bounded provider adapter in
[`007-docling-native-adapter`](specs/007-docling-native-adapter/spec.md) and the
deterministic context compiler in
[`008-context-compiler-receipts`](specs/008-context-compiler-receipts/spec.md), plus
the least-privilege stdio interface in
[`009-read-only-mcp`](specs/009-read-only-mcp/spec.md):

- Python 3.12, locked `uv` environment, Ruff, formatting, strict mypy, offline pytest/coverage and pre-commit gates;
- least-privilege GitHub Actions on Ubuntu, macOS and Windows with commit-pinned actions;
- strict Pydantic v2 domain models, five F002 JSON Schema roots, and four independently
  versioned experimental evidence contract roots;
- RFC 8785 canonical JSON and versioned SHA-256 identity projections;
- immutable streaming filesystem CAS with verified reads and atomic same-filesystem publication;
- checksummed transactional SQLite migrations, exact source/version facts and fenced job transitions;
- explicit local workspace plus an installable `openardp` command;
- read-only, race-detecting ingestion of regular UTF-8 `.txt`, `.md` and `.markdown` files;
- a bounded spawned parser worker with denied socket creation and documented residual platform risk;
- deterministic prepared manifests/blocks, unchanged-source cache reuse and immutable version history;
- body-minimizing `list`, `status`, `outline` and exact persisted `get` navigation;
- exact term/phrase lexical search with deterministic filters, verified bounded snippets and fail-closed index coverage;
- idempotent `reindex` from verified READY evidence;
- an exact optional `docling==2.114.0` extra for offline, spawned DOCX/PPTX conversion
  and explicitly provisioned PDF conversion;
- complete immutable Docling JSON, strict F006 thin evidence and checksummed catalog
  revision 5 with accepted plus append-only converged/diverged attempts;
- fully verified rich cache reuse and provider-free `evidence`/`get-evidence`
  inspection;
- deterministic budgeted context compilation over verified text and rich evidence with
  an exact corpus snapshot, a documented total order and greedy byte-exact admission
  under a versioned estimator budget with ten-percent response reserve;
- the public `ContextBundle 0.2.0` handoff with structurally delimited untrusted-data
  envelopes and the body-free experimental `SelectionReceipt 0.1.0` recording every
  selection, omission, rejection, stale item and unit of budget;
- checksummed catalog revision 6 with atomic immutable compilation rows, exact scope
  pinning and byte-identical task-supplied replay after later head changes;
- provider-free `context` and `context-receipt` CLI commands with stable JSON and
  human envelopes, closed failure taxonomy and body-free operational logs;
- a dependency-free read-only MCP stdio server with nine fixed object-scoped tools,
  pinned protocol revision `2025-06-18`, bounded messages/responses/deadlines,
  cooperative cancellation, canonical descriptors and versioned body-free errors.

The core installation still supports strict UTF-8 text without Docling. Rich parsing is
an explicit optional extra and remains local/offline by default. There is no watcher,
cloud connector, automatic garbage collection, HTTP transport or stable custom export
format yet. Those remain separate work packages in the
[authoritative feature map](spec-kit/FEATURE_MAP.md).

## Quickstart

Prerequisites: Git, `uv` 0.11.31 and Linux, macOS or Windows. The repository selects Python 3.12.

```bash
uv sync --all-extras --locked

uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Create a local workspace and prepare text evidence:

```bash
openardp init --store .openardp
openardp ingest ./notes.md --store .openardp
openardp list --store .openardp
openardp status ./notes.md --store .openardp
openardp outline <document-uuid> --store .openardp
openardp get <block-uuid> --store .openardp
openardp search '"exact phrase" evidence' --store .openardp
openardp reindex --store .openardp
openardp ingest ./document.docx --store .openardp
openardp evidence <document-uuid> --store .openardp
openardp get-evidence <projection-sha256> --document <document-uuid> --store .openardp
openardp context "Which exact controls are documented?" \
  --document <document-uuid> --budget 12000 --unit tokens --mode verification \
  --store .openardp
openardp context-receipt <receipt-sha256> --store .openardp
openardp context "Which exact controls are documented?" \
  --replay <receipt-sha256> --store .openardp
openardp mcp --store .openardp
```

PDF additionally requires `--docling-model-root` and
`--docling-model-manifest` pointing to reviewed local assets; URLs are not accepted.
Add `--json` to ordinary commands for a versioned machine-readable stdout envelope.
The `mcp` verb owns stdout for newline-delimited JSON-RPC and therefore has no CLI
envelope switch. It bounds each inbound line to 64 KiB and pending sequential dispatch
to 64 non-cancellation frames; overflow unwinds active work and closes the session.
Only
`get`, the explicitly selected `get-evidence` and `context --include-bundle` return
bodies, always inside delimited untrusted-data envelopes. Search returns bounded
verified snippets. Receipts, default `context` output, logs and error envelopes never
contain the task string, evidence bodies or source paths. Replay reuses the recorded
exact snapshot and fails with a stable mismatch error instead of recompiling silently.
Every command except `init` requires an explicitly initialized
compatible workspace; commands do not search parent directories or create state
implicitly.

## Validation and build

```bash
uv run pre-commit run --all-files
uv run python scripts/validate_repository.py
uv run --locked python scripts/generate_schemas.py --check
uv build
```

The committed lockfile is authoritative. Core tests block network access and use synthetic or redistributable fixtures.
Performance, quality, cost, security, interoperability and sustainability statements are claims only when accompanied by
reproducible environment, data, baselines, raw results and limitations.

## Architecture boundaries

- `domain/`: pure models and invariants; no I/O.
- `ports/`: narrow provider-neutral protocols.
- `adapters/`: parsers, stores, sources and providers.
- `services/`: use cases and orchestration.
- `interfaces/`: CLI and the delivered read-only MCP stdio entry point; HTTP is later.

Dependencies point inward. Provider-specific semantics remain in native artifacts or explicit profiles. The core remains
usable locally with no cloud, user tracking, external model call or network egress enabled by default.

## Governance and roadmap

Project-wide authority follows this order:

1. [Constitution 2.0.0](.specify/memory/constitution.md) and accepted security/legal constraints;
2. accepted [ADRs](docs/adr/) and public [schemas](schemas/);
3. canonical project documentation;
4. the active feature specification and plan;
5. tasks;
6. implementation.

Every production-relevant feature follows:

```text
specify → clarify → plan → checklist → tasks → analyze → implement → converge
```

Critical/high analysis findings block implementation; critical/high convergence findings block merge. One bounded
feature is completed and merged before its dependent successor begins. Feature 006
defines the minimal evidence contracts; Feature 007 implements the Docling adapter only
after F006 has converged and merged.

## Read next

1. [Start here](START_HERE.md)
2. [Revised executive brief](docs/00_REVISED_EXECUTIVE_BRIEF.md)
3. [Vision and positioning](docs/01_VISION_AND_POSITIONING.md)
4. [Target architecture](docs/05_TARGET_ARCHITECTURE.md)
5. [Security model](docs/06_SECURITY_MODEL_V2.md)
6. [Contract lifecycle](docs/09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md)
7. [Operations, privacy and supply chain](docs/10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md)
8. [Feature map](spec-kit/FEATURE_MAP.md)

## Project policy

- [License](LICENSE): Apache-2.0; no trademark grant
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Validation evidence](VALIDATION.md)
- [Changelog](CHANGELOG.md)
- [Prior art and claims discipline](docs/04_PRIOR_ART_AND_DD.md)

The repository and its examples are implementation evidence, not legal, security, standards or performance guarantees.
