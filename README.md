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
[`009-read-only-mcp`](specs/009-read-only-mcp/spec.md) and the provider-free lifecycle in
[`010-reconciliation-derivation-dag`](specs/010-reconciliation-derivation-dag/spec.md),
plus explicit visual escalation in
[`011-visual-evidence-escalation`](specs/011-visual-evidence-escalation/spec.md) and the
foreground local watcher in
[`012-local-watcher-and-jobs`](specs/012-local-watcher-and-jobs/spec.md), followed by
verified retention and recovery in
[`013-retention-recovery-migrations`](specs/013-retention-recovery-migrations/spec.md),
and the experimental BagIt exchange profile in
[`014-export-interchange-experiment`](specs/014-export-interchange-experiment/spec.md),
followed by the fail-closed evidence gate in
[`015-benchmark-security-release-gate`](specs/015-benchmark-security-release-gate/spec.md),
the independent conformance spike in
[`016-alternate-parser-conformance-spike`](specs/016-alternate-parser-conformance-spike/spec.md),
the mock-only enterprise-connector design in
[`017-microsoft-graph-design-spike`](specs/017-microsoft-graph-design-spike/spec.md),
the behavior-preserving maintenance pass in
[`018-repository-hygiene`](specs/018-repository-hygiene/spec.md), and the CI cost/latency optimization in
[`019-ci-cost-optimization`](specs/019-ci-cost-optimization/spec.md), the workload-bounded product-value evaluation in
[`020-product-value-benchmark`](specs/020-product-value-benchmark/spec.md), and the measured status-path correction in
[`021-incremental-freshness`](specs/021-incremental-freshness/spec.md), the storage-layout correction in
[`022-storage-amplification`](specs/022-storage-amplification/spec.md), and the explicit offline PDF model package in
[`023-offline-pdf-model-bundle`](specs/023-offline-pdf-model-bundle/spec.md), and the licensed real-world corpus in
[`024-redistributable-realworld-corpus`](specs/024-redistributable-realworld-corpus/spec.md), and the realistic semantic
and source-quality evaluation in
[`025-semantic-e2e-source-evaluation`](specs/025-semantic-e2e-source-evaluation/spec.md):

The committed F020 macOS arm64 run is `CONDITIONALLY_WORTHWHILE`: exact judged correctness, zero stale incidents and
parser-free warm reuse support the parse-once thesis; 100,000-block search p95 is 70.200 ms and reference break-even
against raw reparsing is 32 tasks. It is not unconditional because reference status p95 is 2.087 seconds, PDF lacks the
explicit offline model bundle and two context budgets cannot hold the safe envelope. See the
[`reference report`](benchmarks/product-value/v0.1.0/results/reference-macos-arm64/report.md). F015 remains `NO-GO`.

F021 resolves the measured status bottleneck without weakening its claim boundary. Default `HEAD` status performs an
exact source SHA-256 inspection plus one atomic READY-header snapshot; its committed p95 is 2.257 ms at 10,000 blocks and
9.186 ms at 100,000 blocks, with zero aggregate loads, block reads, parser calls or full-verifier calls. Deliberate
`FULL` status retains exhaustive native/manifest/projection/block verification at 1.981 s and 25.451 s p95. See the
[`F021 report`](benchmarks/freshness/v0.1.0/results/reference-macos-arm64/report.md).

F022 reduced the F020 text-workspace logical amplification by 64.77–65.21 percent while preserving exact source,
search, freshness, reuse, edit/revert and context-replay behavior. F023 now provisions the exact five-file Docling PDF
profile outside Git, transfers it as a deterministic independently verified package and proves actual offline PDF use.
The committed F023 run is `PDF_OFFLINE_READY`: 384,428,156 model bytes, 2,310 package-overhead bytes, three deterministic
fresh-worker conversions and 4.169/4.271-second wall p50/p95. F024 now adds a 6,634,970-byte NASA/CISA corpus with exact
rights/provenance records and a validated `REALWORLD_BASELINE_READY` result across PDF, DOCX, PPTX, CSV, Markdown and
plain text. Its 12 structural observations are deterministic and offline; one oversized PPTX native pointer is correctly
retained as bounded. F025 now reports `SEMANTIC_E2E_NOT_READY`: exact citations and supported-format ingestion pass, but
untouched questions achieve only 35.3% full support, 32.6% atom recall and 1.1% evidence precision. Frozen operator terms
improve full support to 82.4% but remain manual assistance and miss the 90% atom/source conditional gates. See the
[`F025 report`](benchmarks/semantic-e2e/v0.1.0/results/reference-macos-arm64/report.md).

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
- body-minimizing `list`, exact bounded `status`, explicit `status --full-integrity`, `outline` and exact persisted `get`
  navigation with truthful `NONE`/`HEAD`/`FULL` assurance coverage;
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
- checksummed catalog revision 7 with conservative block lineages, exact
  lineage/content evidence bindings and canonical `same_logical_block_as` roots;
- a provider-neutral derivation DAG over ordered evidence, object and producer inputs
  with transactional `CURRENT`, `STALE`, `FAILED` and `SUPERSEDED` workspace state,
  deterministic slot replacement and exact A→B→A reactivation;
- CAS-first reconciliation/derivation services with bounded matching, cycle rejection,
  zero-false-reuse enforcement and no model or provider invocation.
- experimental `VisualEvidenceDescriptor 0.1.0`, deterministic visual/raster identities
  and checksummed catalog revision 8 with atomic page-raster reuse and reachability;
- an exact optional `visual` extra (`pypdfium2==5.12.1`, `Pillow==12.3.0`) for bounded,
  spawned, offline PDF page rendering and canonical single-frame RGB PNG crops;
- explicit `visual-materialize` / `visual-evidence` CLI operations and verified
  handle-only VISUAL context candidates; compilation never invokes the renderer;
- provider-neutral OCR/caption orchestration with no default provider; accepted output
  remains model-derived untrusted data and depends exactly on the retained crop.
- checksummed workspace revision 9 with persisted watcher roots/observations/targets,
  job eligibility, delayed retry and terminal fenced cancellation;
- explicit disjoint-root polling with bounded complete rescans, metadata stability,
  path-addressed tombstones, redacted rename hints and deterministic backpressure;
- foreground `watch`, body-free `jobs` and fenced `job-cancel` CLI operations that
  reuse the existing text/rich ingestion services and open no listener.
- checksummed workspace revision 10 with complete retention roots, operator holds,
  content-identified dry runs, reversible quarantine, explicit grace-gated commit and
  restart-persistent maintenance intent;
- paired verified internal backup, fresh disjoint restore and explicit revision-9 to
  revision-10 migration with a recorded pre-upgrade manifest;
- body-free storage diagnostics, exact reserve admission and an all-or-prior global
  lexical-index rebuild derived from verified READY evidence.
- checksummed workspace revision 11 with normalized representation scope/search
  projections and transparent bounded compact storage for canonical derived text blocks;
- explicit backup-first revision-10 migration and idempotent `storage-optimize`, while
  ordinary open remains non-mutating and source/provider-native objects remain ordinary;
- a retained offline reference/migration/scale benchmark reducing logical amplification
  from about 37.9x to 13.20–13.35x without changing exact search, context, replay or history.
- experimental BagIt profile `0.1.0` with deterministic stored-ZIP export, hostile
  package verification, fresh read-only snapshot import and no custom `.ardp` suffix;
- a strict public interchange schema and offline deterministic valid/invalid vector
  corpus covering integrity, paths, resource bounds, compatibility and trust.
- candidate `0.1.0rc1`, a frozen five-baseline synthetic benchmark protocol, exact
  mechanical judgments, deterministic bootstrap statistics and immutable platform
  evidence identities;
- closed `release-evidence`, `release-gate` and `release-report` CLI operations, a
  strict public release-evidence schema, security/privacy control manifest and bounded
  wheel/sdist inspection;
- a normalized CycloneDX 1.5 SBOM with all locked components, explicit per-component
  license review state, three-platform CI evidence jobs and one aggregate no-waiver gate.
- an isolated standard-library consumer plus non-Docling TXT/CSV producer proving the
  scoped F006 evidence-contract neutrality claim without adding a runtime adapter;
- mock-only tenant-scoped Graph delta, permission, tombstone, retry and notification
  contracts; production Microsoft Graph access remains explicitly unauthorized;
- deterministic maintainability auditing with monotonic legacy-hotspot ceilings,
  independently runnable focused tests and characterized release, CLI and watcher
  orchestration refactors.
- fail-closed changed-path classification, Draft-to-Ready execution, one authoritative
  Linux coverage lane, complete no-coverage macOS/Windows final suites and a separately
  bounded all-platform release-evidence workflow.

The core installation still supports strict UTF-8 text without Docling. Rich parsing is
an explicit optional extra and remains local/offline by default. F012 watching is a
foreground polling process over one explicitly supplied local root; it is not a daemon,
does not guarantee remote/network filesystems and adds no MCP mutation. F013 never
deletes automatically: irreversible removal requires a named expired quarantine batch
and a separate acknowledgement. There is no cloud connector, scheduled garbage
collection, HTTP transport or stable/universal custom export format. F014 is an
explicitly experimental BagIt profile and does not merge into a live workspace. PDF is
the only concrete F011 visual renderer; DOCX/PPTX page rendering,
built-in OCR/caption models and automatic materialization remain unsupported. F010 also
does not schedule reconciliation or execute generators; callers explicitly supply two
READY scopes and already-generated output bytes. Feature 015 does not authorize a
release: the committed candidate decision is `NO-GO` because required evidence remains
incomplete. Feature 017 likewise does not authorize a production Microsoft Graph
connector. Feature 018 changes no product contract, dependency, persisted identity,
workspace revision or release decision. Feature 019 changes only repository automation and its enforcement evidence;
it does not reduce the final three-platform test inventory or alter product/release contracts. Those boundaries and
remaining work packages are recorded in the
[authoritative feature map](spec-kit/FEATURE_MAP.md).

## Evidence-backed claim status

The current allowed claim IDs are `local-first`, `evidence-preserving` and
`experimental-contracts`. They map to the verified
[`claim-map.json`](release/evidence/v0.1.0/claim-map.json). Performance leadership,
universal security, three-platform support, third-party reproduction and v0.1 release
readiness are not claimed; the authoritative
[`decision.json`](release/evidence/v0.1.0/decision.json) is `NO-GO`.
The committed local capture contains 4,222 raw observations and verified local
security/privacy, artifact/install and upgrade/rollback evidence. Remaining blockers
are three-platform completion, license/current-vulnerability review and the frozen
bounded-context value threshold.

Machine mapping: allowed `claim:evidence-preserving`,
`claim:experimental-contracts`, `claim:local-first`; prohibited
`claim:enterprise-performance`, `claim:measured-parser-reuse`,
`claim:third-party-reproduced`, `claim:three-platform-supported`,
`claim:universal-security`, `claim:v0.1-release-ready`.

## Quickstart

Prerequisites: Git, `uv` 0.11.31 and Linux, macOS or Windows. The repository selects Python 3.12.

```bash
uv sync --all-extras --locked

uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/audit_maintainability.py
```

Create a local workspace and prepare text evidence:

```bash
openardp init --store .openardp
openardp ingest ./notes.md --store .openardp
openardp list --store .openardp
openardp status ./notes.md --store .openardp
openardp status ./notes.md --full-integrity --store .openardp
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
openardp visual-materialize <document-uuid> <projection-sha256> --store .openardp
openardp visual-evidence <visual-evidence-sha256> --store .openardp
openardp watch /absolute/documents --store .openardp --once --stability-ms 0 --json
openardp jobs --store .openardp --limit 50 --json
openardp job-cancel <job-uuid> --store .openardp --json
openardp storage-inventory --store .openardp --json
openardp storage-diagnostics --store .openardp --json
openardp storage-optimize --store .openardp --json
openardp workspace-backup --store .openardp --destination ../openardp-backup
openardp index-rebuild --store .openardp --json
openardp mcp --store .openardp
openardp package-export --request ./synthetic-export-request.json \
  --destination ./synthetic-package.zip --json
openardp package-verify --package ./synthetic-package.zip --json
openardp package-import --package ./synthetic-package.zip \
  --destination ./synthetic-imported-snapshot --json
openardp release-evidence --corpus benchmarks/release/v0.1.0 \
  --source-root . --output ../openardp-platform-evidence --json
openardp release-gate --policy benchmarks/release/v0.1.0/gate-policy.json \
  --evidence ../openardp-platform-evidence --output ../openardp-decision \
  --decision-at 2026-08-01T00:00:00Z --json
openardp release-report --decision ../openardp-decision/decision.json \
  --output ../openardp-decision --json
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
New compilations apply the provider-free combined F026/F027 relevance and allocation profile. Below-floor
candidates remain auditable receipt rejections; a valid no-match returns explicit
`no_relevant_evidence` abstention. A four-item ranked prefix preserves early lexical quality,
then exact-body deduplication, fair document interleaving and a 16-item per-document quota
bound source dominance. Historical receipts select their recorded legacy or F026-only
algorithm for replay. See [the measured F027 result](docs/26_LEXICAL_RANKING_AND_DIVERSITY.md).
Every workspace command except `init` requires an explicitly initialized compatible
workspace; package commands are intentionally workspace-independent and use only their
explicit local request/package/destination. Commands do not search parent directories
or create workspace state implicitly. Package request source paths never enter package
metadata/results, and included bytes require affirmative redistribution assertions.

## Validation and build

```bash
uv run pre-commit run --all-files
uv run python scripts/validate_repository.py
uv run --locked python scripts/generate_schemas.py --check
uv run python scripts/generate_release_corpus.py --check
uv run python scripts/generate_dependency_review.py --check
uv run python scripts/generate_release_sbom.py --check
uv run python scripts/generate_release_evidence.py --check
uv run python scripts/validate_release_evidence.py release/evidence/v0.1.0
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
