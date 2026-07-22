# Implementation Plan: Text Ingestion Vertical Slice

**Branch**: `codex/f004-text-ingestion-slice` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-text-ingestion-slice/spec.md`

## Summary

Implement the first complete local document workflow for bounded UTF-8 TXT and Markdown. An explicitly authorized regular
file is streamed once into the existing immutable CAS, registered as an F003 source version and parsed only from that
verified snapshot through a provider-neutral port. A fenced representation claim prevents concurrent duplicate parsing.
The adapter emits deterministic source-backed candidates that become F002 manifests/blocks and individual CAS objects; a
revision-3 SQLite transaction makes the complete representation ready, advances a monotonic document head and records the
ingest disposition. Subsequent unchanged ingest verifies and reuses the exact representation without invoking the parser.

The installable CLI exposes `init`, `ingest`, `list`, `status`, `outline` and `get` with stable JSON envelopes. F004 does
not add FTS/search, rich document parsing, reconciliation, watchers, MCP, providers or package export.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`argparse`, `codecs`, `hashlib`, `json`, `os`, `pathlib`, `stat`,
`tempfile`, `uuid`) plus existing Pydantic 2.12/rfc8785; no new runtime dependency

**Storage**: Existing filesystem SHA-256 CAS plus SQLite catalog revision 3 under the accepted DELETE/EXTRA profile

**Testing**: pytest with branch coverage and socket blocking; domain, parser, migration, transaction, source-race,
cache/concurrency, CLI and security tests using synthetic UTF-8 fixtures and temporary workspaces

**Target Platform**: Local filesystems on Linux, macOS and Windows with Python 3.12; shared/network filesystems and an
actively malicious same-user process remain outside the supported filesystem race boundary

**Project Type**: Installable modular-monolith Python application with one CLI composition root

**Performance Goals**: Bounded streaming snapshot and decoding; zero parser calls for verified unchanged representations;
at most one active parser claim per document/version/recipe; no unmeasured latency claim

**Constraints**: 100 MiB source limit, 1 MiB decoded line limit, 100,000-block limit, strict UTF-8, no NUL, no source
writes, no network, body-free default diagnostics, atomic ready visibility and exact SHA-256 reuse

**Scale/Scope**: Single-machine local workspaces and bounded TXT/Markdown sources. F013 owns representative performance,
energy and security benchmarks.

## Constitution Check

*Gate evaluated before research and re-evaluated after design.*

| Article | Gate | Design evidence | Status |
|---|---|---|---|
| I — Evidence Preservation | Originals remain authoritative and immutable | Read-only descriptor snapshot; exact bytes stay in CAS; parsing uses CAS; no source write operation | PASS |
| II — Derived Data Is Disposable | Parser output cannot replace originals | Manifest/block/native roles are explicit; native text is the original object; normalized objects are reproducible | PASS |
| III — Local-First and Provider-Neutral | No default cloud/provider coupling | Parser remains a port; built-in adapter/SQLite/CAS are local; stdlib CLI makes no network call | PASS |
| IV — Untrusted Document Boundary | Text never becomes authority | Every block is external-untrusted `role=data`; text is never interpreted as path, URL, option or command | PASS |
| V — Determinism, Identity and Atomicity | Exact identities and complete visibility | Accepted representation identity reused; SHA-256 block handles; fenced claims; one READY transaction | PASS |
| VI — Progressive Context Delivery | Outline precedes body retrieval | `list`/`status` omit bodies; `outline` loads headings only; `get` retrieves one verified block | PASS |
| VII — Test-First Quality Gates | Public/persisted/security behavior is tested | Tests precede each implementation phase; full Ruff/format/mypy/pytest gates remain mandatory | PASS |
| VIII — Measured Claims | No invented performance assertion | Only byte/count/concurrency acceptance bounds are claimed; latency deferred to F013 | PASS |
| IX — Simplicity and Incremental Delivery | Small bounded modular slice | Stdlib parser/CLI, one append-only migration, no search/rich parser/watcher/framework | PASS |
| X — Specification and Decision Governance | Contracts precede code | Clarification, research, data model, internal contract, checklists and task graph precede implementation | PASS |

### Post-design re-check

The design introduces the first representation lifecycle but does not change accepted content/representation identity
algorithms or public F002 schemas. The new SHA-256-derived UUIDv8 rule is a documented initial block-handle allocation rule,
not a content identity change; F010 may reconcile new-version handles without rewriting historical records. No prohibited
architecture change or ADR exception is required.

## Architecture and Transaction Design

### End-to-end flow

```text
explicit source path
  -> LocalSourceSnapshot validates and opens read-only
  -> ObjectStore.put_chunks streams exact bytes
  -> register/reuse logical document and source version
  -> derive exact ParserRecipe + RepresentationScope
  -> Catalog.acquire_representation
       READY  -> verify full aggregate -> record CACHE_HIT -> return
       BUSY   -> retryable busy result
       CLAIMED-> ParserAdapter parses CAS chunks
                -> normalize candidates into F002 blocks/manifest
                -> publish and verify canonical record objects
                -> Catalog.commit_ready_representation
                -> READY + head + event commit together
```

No SQLite write transaction spans source I/O or parser work. Filesystem publication always precedes the logical commit;
failure may leave complete unreferenced objects and never triggers compensating deletion.

### Parser boundary

`ParserAdapter` accepts a one-shot iterable of verified bytes plus declared supported media type and returns a pure
`ParsedTextDocument`. The pure built-in adapter owns decoding and syntax recognition only. The default
`IsolatedParserAdapter` streams those chunks to a killable spawned worker, passes no source path, disables socket creation
there and enforces a 30-second wall deadline plus portable input/line/block bounds. `IngestionService` assigns document,
version, representation, block identities, trust and persisted object references.

### Representation lifecycle and fencing

```text
absent  -> STAGING (claim attempt 1)
FAILED  -> STAGING (retry attempt +1)
expired STAGING -> STAGING (takeover attempt +1)
STAGING -> READY (complete aggregate)
STAGING -> FAILED (sanitized failure code)
READY   -> READY (immutable; verified cache hit or equal forced reparse)
```

Active ownership requires owner, SHA-256 token hash, revision and `lease_expires_at > now`. A stale worker cannot commit or
fail after takeover. Readers may observe STAGING/FAILED status but only READY aggregates are content-queryable.

### Head and observation ordering

The current source association is `document_heads`, not maximum immutable version time. A later `source_observed_at`
advances the head; the same scope/time is idempotent; equal time with a different scope conflicts; an older overlapping
operation records historical success but cannot move the head backward. This makes A → B → A reversion and concurrent
different-version completion deterministic.

### Cache decision

A candidate hit must pass CAS verification and strict manifest/block deserialization plus aggregate cross-checks. Only
after proof does the service record `CACHE_HIT`; a corrupt READY result is an integrity failure, not an automatic reparse.
`--force` deliberately parses but must reproduce the existing immutable aggregate exactly.

## Persistence Revision 3

Append `MIGRATION_3 = text-representations-blocks-heads` without changing the first two migration definitions.

- `document_representations`: scoped recipe, lifecycle, fencing, singleton manifest/native object roots and block count.
- `representation_blocks`: global ordinal, sibling order, parent, kind, canonical hash, exact line range and block object.
- `document_heads`: current ready scope, monotonic source observation, last ingest/disposition and revision.
- `ingestion_events`: append-only body-free disposition evidence.

Domain validation owns graph acyclicity, complete contiguous ordinals/sibling orders, exact scope agreement, line extension
agreement and manifest/recipe identity recomputation. SQLite owns types, checks, uniqueness, foreign keys and transaction
visibility. `reference_snapshot` adds every manifest, native and block object from all historical representations.

## Workspace and CLI Design

Workspace layout:

```text
<store>/
├── .openardp-workspace.json
├── catalog.sqlite3
├── objects/sha256/...
└── staging/...
```

`LocalWorkspace.initialize` validates an empty/compatible root, initializes the current catalog and CAS, then atomically
publishes the version-1 marker. `LocalWorkspace.open` requires the marker and exact supported version before composing
adapters/services. No parent search or implicit initialization occurs.

`openardp.interfaces.cli` is the thin composition root. It parses arguments, maps stable domain errors to exit/error codes,
and renders human or versioned JSON output. It contains no parsing, SQL or object-path logic.

## Project Structure

### Documentation (this feature)

```text
specs/004-text-ingestion-slice/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── text-ingestion.md
├── checklists/
│   ├── requirements.md
│   └── ingestion-safety.md
├── tasks.md
└── implementation-notes.md
```

### Source code

```text
src/openardp/
├── domain/
│   └── ingestion.py
├── ports/
│   ├── catalog.py                 # F004 representation/query operations
│   └── parser.py
├── adapters/
│   ├── local_source.py
│   ├── local_workspace.py
│   ├── isolated_parser.py
│   ├── sqlite_catalog.py          # revision-3 operations
│   ├── sqlite_migrations.py       # append-only migration 3
│   └── text_parser.py
├── services/
│   ├── ingestion.py
│   └── document_query.py
└── interfaces/
    └── cli.py

tests/
├── contract/
│   └── test_ingestion_ports.py
├── domain/
│   └── test_ingestion.py
├── unit/
│   └── test_text_parser.py
├── integration/
│   ├── test_ingestion_catalog.py
│   ├── test_ingestion_service.py
│   ├── test_document_query.py
│   └── test_cli.py
└── security/
    └── test_local_source_boundaries.py
```

**Structure Decision**: Extend the existing inward-pointing architecture. Pure lifecycle/aggregate records remain in
`domain`; the parser boundary joins the catalog/object-store ports; filesystem/SQLite/text parsing remain adapters;
orchestration/query logic remains services; only argument/rendering/composition lives in interfaces.

## Test Strategy

- Domain tests cover recipe/scope identity, deterministic UUIDv8 vectors, aggregate completeness, hierarchy/cycle/order,
  line provenance, state/lease/head/event invariants and hostile invalid combinations.
- Parser tests cover TXT/Markdown forms, BOM, LF/CRLF/CR, chunk splits inside UTF-8 and delimiters, Unicode distinction,
  fences, lists, quotes, heading jumps, empty input, malformed UTF-8, NUL and resource limits. Isolation tests prove spawn,
  streamed IPC, no path/network capability, timeout termination, crash/error sanitization and child cleanup.
- Migration/catalog tests cover fresh/v1/v2 upgrade, rollback, newer/drift rejection, fencing/takeover, atomic ready commit,
  idempotent retry/conflicts, head monotonicity, event order and expanded reachability.
- Source security tests cover path controls, links/junctions, directories/special files, replacement/truncation during read,
  unsupported extension/content, size limits, unchanged bytes/mode/mtime and no body leakage.
- Service tests use parser spies/faults to prove first ingest, 20 unchanged hits, concurrent single claim, changed bytes,
  A → B → A, forced equal/divergent output, parser failure/retry and CAS-only queries after source removal.
- CLI tests invoke the installed entry point for all commands in human/JSON mode, validate envelopes/exit codes and ensure
  only `get` returns body text.
- All fixtures are small synthetic UTF-8 files and all tests remain socket-blocked.

## Migration and Compatibility Impact

- SQLite schema advances from revision 2 to 3 through the existing checksummed exclusive chain.
- Revisions 1 and 2 and all existing rows remain unchanged.
- F003 source/catalog public behavior remains compatible; its reference snapshot expands conservatively.
- The five public JSON Schema 0.1.0 files remain unchanged; F004 persists valid existing manifest/block records.
- `pyproject.toml` gains only the `openardp` console entry point; dependency/lock content remains unchanged.
- A revision-2 binary correctly rejects a revision-3 catalog as newer; forward-reading is not claimed.

## Security and Privacy Impact

- Explicit source selection grants one bounded read, not directory traversal authority.
- Path strings cannot control CAS paths, SQL, CLI options after parsing, network calls or tools.
- Source bodies live only in source/CAS/block objects and explicit `get` output; normal errors/events/list/status omit them.
- Raw lease tokens remain process capabilities; only SHA-256 hashes persist.
- Malicious instruction-like content is always marked external-untrusted data with execution disabled.
- Best-effort no-follow checks reduce path escape risk but do not claim immunity to hostile same-user replacement races.

## Documentation and Contract Updates

- Add F004 internal parser/ingestion/CLI contracts and quickstart.
- Update architecture, data-model, incremental-processing, testing and execution-plan docs with only delivered behavior.
- Update README, START_HERE, specs index, changelog and validation status.
- Do not accept ADR 0001 or introduce Docling; F006 owns that decision and dependency.
- Do not alter F002 schemas or accepted ADR 0006 identity projections.

## Rejected Alternatives

- Parsing the live path after hashing: source-race mismatch.
- A READY-only insert without claim: duplicate initial parsing.
- Long SQLite transaction around parser work: unnecessary lock contention and crash surface.
- Bodies in SQLite or a single blocks bundle: leakage or non-progressive reads.
- Implicit workspace discovery/initialization: surprising state mutation.
- Framework CLI/Markdown dependencies: unjustified core growth.
- mtime/size cache identity, newest-version-as-head or corrupt-hit auto-repair: incorrect evidence semantics.
- Search/index scaffolding in F004: violates feature order.

## Complexity Tracking

No constitutional violation requires a waiver. The representation state machine is justified by real concurrent parser
ownership and retry requirements; the document head is necessary for reversion correctness; the fourth event table is the
smallest durable evidence that an unchanged ingest actually skipped parsing. No generic artifact graph, ORM, filesystem
abstraction, background worker or parser framework is introduced.
