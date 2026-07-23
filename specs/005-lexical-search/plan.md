# Implementation Plan: Lexical Search over Prepared Evidence

**Branch**: `codex/f005-lexical-search` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-lexical-search/spec.md`

## Summary

Add exact source-backed lexical retrieval to the local workspace. A revision-4 catalog migration introduces one
contentless-delete FTS5 index and one STRICT mapping table. Index rows are written inside the existing atomic READY
commit, so every newly prepared document is searchable in the same transaction that publishes it; representations
committed before this feature are backfilled by an explicit idempotent `reindex` command that re-verifies canonical
CAS blocks. The bounded query grammar (terms and quoted phrases) is translated into one parameterized FTS5 MATCH
expression; results rank by `bm25` with a documented total tie-break and return body-minimizing evidence references
whose snippets are generated only from verified CAS blocks. Structural coverage is checked inside every search read
transaction and uncovered scopes fail closed toward `reindex`. The installable CLI gains `search` and `reindex` with
the shared workspace, envelope and exit-classification contract. F005 adds no embeddings, fuzzy or semantic
matching, rich-document coordinates beyond the stable filter surface, watchers, MCP, HTTP or export.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`argparse`, `hashlib`, `json`, `os`, `re`, `sqlite3`, `uuid`)
plus existing Pydantic 2.12/rfc8785; SQLite FTS5 from the runtime's bundled SQLite; no new runtime dependency

**Storage**: Existing filesystem SHA-256 CAS plus SQLite catalog revision 4 under the accepted DELETE/EXTRA profile
with `trusted_schema=OFF`

**Testing**: pytest with branch coverage and socket blocking; domain, grammar, migration, coverage, commit-atomicity,
search, reindex, CLI and security tests using synthetic UTF-8 fixtures and temporary workspaces

**Target Platform**: Local filesystems on Linux, macOS and Windows with Python 3.12; runtimes without FTS5 fail
closed with a capability classification

**Project Type**: Installable modular-monolith Python application with one CLI composition root

**Performance Goals**: Bounded indexed lookups; at most 100 verified block reads per query; no unmeasured latency
claim (F013 owns the documented search benchmark)

**Constraints**: exact-token matching only, limit 1–100 (default 20), snippet ≤ 240 escaped characters, query ≤ 4096
characters/32 items, no bodies in SQLite, no network, parameterized SQL only, atomic READY/index visibility

**Scale/Scope**: Single-machine local workspaces; the PRD's 100k-block search target remains the F013 benchmark
responsibility, not an F005 claim.

## Constitution Check

*Gate evaluated before research and re-evaluated after design.*

| Article | Gate | Design evidence | Status |
|---|---|---|---|
| I — Evidence Preservation | Originals remain authoritative | Index derives only from verified CAS blocks; source paths are never read; `reindex` mutates no evidence | PASS |
| II — Derived Data Is Disposable | Index is invalidatable and reproducible | Contentless index + mapping rows are rebuilt deterministically from verified blocks; entries record scope and text hash | PASS |
| III — Local-First and Provider-Neutral | No provider coupling | FTS5 is the mandated local mechanism behind the catalog port; no network or model call | PASS |
| IV — Untrusted Document Boundary | Text and queries never become authority | Bounded grammar with uniform quoting; bound-parameter MATCH; snippets escaped `role=data`; no operator surface | PASS |
| V — Determinism, Identity and Atomicity | Exact identities and complete visibility | Index rows commit in the READY transaction; total ranking order; checksummed migration 4; SHA-256 text hashes | PASS |
| VI — Progressive Context Delivery | References before bodies | Hits carry references and bounded snippets only; bodies require explicit `get` | PASS |
| VII — Test-First Quality Gates | Public/persisted/security behavior is tested | Tests precede each implementation phase; full Ruff/format/mypy/pytest gates remain mandatory | PASS |
| VIII — Measured Claims | No invented performance assertion | Only count/order/atomicity acceptance bounds are claimed; latency deferred to F013 | PASS |
| IX — Simplicity and Incremental Delivery | Small bounded slice | One migration, one mapping table, one service, two CLI verbs; no triggers, daemons or frameworks | PASS |
| X — Specification and Decision Governance | Contracts precede code | Clarification, research, data model, internal contract, checklists and task graph precede implementation | PASS |

### Post-design re-check

The design extends the catalog port with search/index methods and the CLI with two verbs but changes no accepted
content/representation identity algorithm, no public F002 schema, no F003/F004 persisted meaning and no ADR. FTS5
shadow tables join the strictly validated catalog table set; the table inventory for revision 4 is pinned
empirically. No constitutional violation requires a waiver and no prohibited architecture change is introduced.

## Architecture and Index Design

### Index storage

`block_search_index` is a contentless-delete FTS5 table (`content=''`, `contentless_delete=1`,
`tokenize='unicode61 remove_diacritics 0'`) holding exactly the block text tokens. Its `rowid` equals
`block_search_entries.entry_id`, a STRICT mapping row carrying scope, block handle, kind, trust zone, nullable
page/slide, exact line range, `text_hash` and write time. No document body is stored in SQLite beyond the irreducible
token index (F004's rejected "bodies in SQLite" boundary stands).

### Atomic index population

```text
IngestionService commit path (unchanged signature)
  -> Catalog.commit_ready_representation (one BEGIN IMMEDIATE transaction)
       register objects
       INSERT representation_blocks ...
       INSERT block_search_entries + INSERT INTO block_search_index(rowid, block_text) ...
       UPDATE document_representations SET state='READY' ...
       verify aggregate
       advance head + event
  -> COMMIT exposes READY representation and its index rows together
```

The READY aggregate already carries every canonical block text, so indexing needs no CAS re-read. Any failure rolls
the whole transaction back; existing fault-point injection plus new index fault points prove the boundary. Cache
hits write nothing; historical READY entries persist unchanged when heads move.

### Query path

```text
CLI search -> SearchService
  -> parse bounded grammar -> match_expression()
  -> resolve scope (current heads | --all-versions | --version, plus filters)
  -> Catalog.search_block_entries (ONE read transaction)
       structural coverage pre-check (projection ordinals vs entry ordinals)
       SELECT rowid, bm25(...) FROM block_search_index MATCH ? JOIN entries JOIN projections
       ORDER BY bm25 ASC, document_id ASC, ordinal ASC
  -> for each page hit: verify CAS block + projection + text_hash
  -> build bounded escaped snippet from verified text
  -> SearchOutcome {hits, truncated, available}
```

Snippet position is located in the verified block text; absence of any match position or hash disagreement fails
with `SearchIndexDrifted`. A query spanning an uncovered READY scope fails with `SearchIndexIncomplete` before
serving anything.

### Backfill and repair

`reindex` resolves the target scopes (one document or every READY representation), loads each verified aggregate
through the same canonical block path as reads, and calls `Catalog.replace_scope_index` per scope in one bounded
write transaction. Outcomes per scope: `current` (coverage and hashes already agree), `rebuilt`, or `failed` with a
bounded code. `reindex` never touches representations, CAS objects, source files or heads.

### Capability probe

FTS5 availability is probed by creating and dropping a temporary `fts5` table on the catalog connection before
migration 4 is applied and at workspace open; failure raises `SearchCapabilityUnavailable` before any result is
served.

## Persistence Revision 4

Append `MIGRATION_4 = lexical-block-search` without changing revisions 1–3.

- `block_search_index`: contentless-delete FTS5 virtual table (shadows join `_SCHEMA_TABLES[4]`, empirically pinned).
- `block_search_entries`: STRICT mapping with scope FK (`ON DELETE RESTRICT`), unique scope+ordinal and
  scope+block, value checks in the F003/F004 style, plus block/scope indexes.
- `reference_snapshot` is unchanged: indexing creates no CAS objects.

## Workspace and CLI Design

Workspace layout, marker validation and composition are unchanged. `openardp.interfaces.cli` gains `search` and
`reindex` parsing, mapping and rendering only; no SQL, FTS or snippet logic enters the interface layer. Exit
classifications reuse the F004 scheme; new search errors map per the internal contract.

## Project Structure

### Documentation (this feature)

```text
specs/005-lexical-search/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── lexical-search.md
├── checklists/
│   ├── requirements.md
│   └── search-safety.md
├── tasks.md
└── implementation-notes.md
```

### Source code

```text
src/openardp/
├── domain/
│   └── search.py                # query/filters/hit/outcome/coverage/report records
├── ports/
│   └── catalog.py               # F005 search/index protocol methods
├── adapters/
│   ├── sqlite_catalog.py        # revision-4 operations, coverage, scoped search, replace_scope_index
│   └── sqlite_migrations.py     # append-only migration 4
├── services/
│   └── search.py                # grammar, scope resolution, verified snippets, reindex orchestration
└── interfaces/
    └── cli.py                   # search + reindex verbs

tests/
├── contract/
│   └── test_search_ports.py
├── domain/
│   └── test_search.py
├── integration/
│   ├── test_search_catalog.py
│   ├── test_search_service.py
│   ├── test_reindex.py
│   └── test_cli.py              # extended for search/reindex
└── security/
    └── test_search_boundaries.py
```

**Structure Decision**: Extend the existing inward-pointing architecture. Pure query/result records live in
`domain`; index/search operations join the catalog port; SQLite/FTS5 stay in adapters; grammar, scope resolution,
verification and reindex orchestration live in services; only argument/rendering/composition lives in interfaces.

## Test Strategy

- Domain tests cover grammar parsing/rejection, deterministic MATCH translation vectors (including hostile operator
  lookalikes), filter validation, bounds and record invariants.
- Migration tests cover fresh/v3 upgrade, checksum drift, foreign/gap histories, newer rejection, the exact revision-4
  table inventory (including FTS shadows) and FTS5 capability probing under `trusted_schema=OFF`.
- Catalog tests cover atomic READY+index commit with fault injection at every boundary, idempotent retry, coverage
  classes (missing/orphaned), scoped MATCH with filters, total ordering, truncation and snapshot isolation during a
  concurrent ingest.
- Service tests cover term/phrase semantics, superseded exclusion, history opt-in, document resolution by UUID and
  path, serve-time hash guard, snippet bounds/escaping, CAS-only operation after source removal and reindex
  idempotency/outcomes.
- CLI tests invoke the installed entry point for `search`/`reindex` in human and JSON modes with envelope and exit
  assertions; no response contains full bodies.
- Security tests cover operator-token injection, oversized/unbalanced queries, hostile snippet text, workspace
  boundaries and zero network use; all fixtures are small synthetic UTF-8 files.

## Migration and Compatibility Impact

- SQLite schema advances from revision 3 to 4 through the existing checksummed exclusive chain; revisions 1–3 and
  all rows remain unchanged.
- A revision-3 binary correctly rejects a revision-4 catalog as newer; forward-reading is not claimed.
- Pre-F005 READY representations stay valid but uncoverable until one explicit `reindex`; `search` fails closed
  toward that remedy instead of serving partial results.
- The five public JSON Schema 0.1.0 files, dependency/lock content and accepted ADRs remain unchanged.
- Runtime without FTS5: `init`/`open` fail closed with `SearchCapabilityUnavailable` before migration or serving.

## Security and Privacy Impact

- Query text is untrusted input; the bounded grammar plus uniform quoting plus bound parameters make MATCH/SQL
  injection impossible by construction.
- Snippets are the only document text in search output: bounded, escaped, verified from CAS and never logged by
  default.
- Index rows reveal token presence inside the catalog file to anyone who can already read the workspace; no new
  network, process or filesystem capability is introduced.
- `reindex` performs verified reads and per-scope bounded writes only; it cannot alter originals or representations.

## Documentation and Contract Updates

- Add F005 internal search/index/CLI contracts and quickstart.
- Update architecture, data-model, testing and execution-plan docs with only delivered behavior.
- Update README, START_HERE, specs index, changelog and validation status.
- Do not alter F002 schemas, accepted ADR 0006 identity projections or the F003 durability profile.

## Rejected Alternatives

- Full-content or external-content FTS5 tables: bodies in SQLite or unpredictable drift semantics.
- Plain contentless without `contentless_delete`: no safe drift repair.
- Raw FTS5 query syntax exposure: unbounded untrusted operator surface.
- FTS5 `snippet()`/`highlight()`: unavailable contentless and weaker terminal-safety control.
- Trigger- or daemon-based indexing: hidden writes; READY commit is the only honest visibility point.
- Serving partially covered scopes with a warning: silently incomplete evidence.
- Automatic rebuild on workspace open: durable writes must be explicit.
- Prefix, stemming, trigram or fuzzy matching: changes result meaning beyond exact lexical retrieval.

## Complexity Tracking

No constitutional violation requires a waiver. The mapping table is the smallest structure that provides filterable
metadata, coverage verification and serve-time staleness guards without storing bodies; the coverage pre-check is
the smallest honest answer to pre-feature representations; per-scope `reindex` transactions are the smallest
crash-safe repair unit. No trigger, background worker, search framework or query-language superset is introduced.
