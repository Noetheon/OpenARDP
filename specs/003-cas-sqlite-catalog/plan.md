# Implementation Plan: Content-Addressed Storage and SQLite Catalog

**Branch**: `codex/f003-cas-sqlite-catalog` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-cas-sqlite-catalog/spec.md`

## Summary

Implement the first local persistence slice as two provider-neutral resources: a streaming SHA-256 filesystem object store and a transactionally migrated SQLite catalog. Exact bytes are staged, synchronized, atomically published and verified before a short catalog transaction makes a source-version fact and all of its references visible together. A failure between resources may leave only a complete unreferenced object, which a deterministic read-only reachability service reports without deleting. The same catalog provides stable document registration and a small, fenced job state machine for restart recovery.

F003 commits source-version facts only. It does not create a complete F002 `DocumentManifest` in `READY`, because normalized blocks, parser artifacts and indexes arrive in later features.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`hashlib`, `os`, `pathlib`, `secrets`, `sqlite3`, `tempfile`, `uuid`) plus the existing Pydantic 2.12 domain foundation; no new runtime dependency

**Storage**: Unpacked SHA-256 filesystem CAS plus SQLite catalog, as governed by ADR 0002; SQLite rollback journal in `DELETE` mode with `synchronous=EXTRA`

**Testing**: pytest with branch coverage and socket blocking; deterministic unit, contract, concurrency, migration, crash-boundary, recovery and security tests using temporary local stores

**Target Platform**: Local filesystems on Linux, macOS and Windows under Python 3.12; shared/network filesystems and adversarial same-user mutation of the managed root are not claimed as supported

**Project Type**: Installable provider-neutral Python library; no CLI or server entry point in F003

**Performance Goals**: Stream objects in bounded chunks, avoid body copies in catalog/logs, and converge 32 concurrent duplicate writes; broader latency/throughput claims are deferred to F013 benchmarks

**Constraints**: Offline by default; exact SHA-256 identity; atomic visibility; no partial logical version; no body logging; parameterized dynamic SQL; no automatic deletion; independent SQLite connections; bounded busy waits; cross-platform behavior

**Scale/Scope**: Single-machine modular monolith and single-node writes; object size is bounded by filesystem capacity rather than process memory, while numeric production-scale claims remain unmade until measured

## Constitution Check

*Gate evaluated before research and re-evaluated after design.*

| Article | Gate | Design evidence | Status |
|---|---|---|---|
| I — Evidence Preservation | Originals remain exact, immutable and reachable | CAS hashes and stores exact bytes; no update/delete API; historical source versions remain reachability roots | PASS |
| II — Derived Data Is Disposable | Storage must not confuse source with derived output | Typed reference roles preserve source identity; F003 does not derive content | PASS |
| III — Local-First and Provider-Neutral | Default is local and storage sits behind ports | `ObjectStore` and `Catalog` protocols isolate filesystem/SQLite adapters; no network dependency | PASS |
| IV — Untrusted Document Boundary | Content cannot become authority or unsafe path/SQL | Object paths use validated digests only; source locators are opaque bound parameters; no body-driven commands | PASS |
| V — Determinism, Identity and Atomicity | SHA-256, atomic writes, duplicate convergence and versioned schemas | F002 identities reused; staged atomic publish; transactional migration chain and source-version commit | PASS |
| VI — Progressive Context Delivery | No premature context behavior | Retrieval and context compilation remain out of scope | PASS |
| VII — Test-First Quality Gates | Tests cover security, identity and persisted behavior | Test tasks precede implementation and all repository gates remain mandatory | PASS |
| VIII — Measured Claims | No unsupported performance/durability claim | Only quantified acceptance probes are claimed; power-loss and scale limits are documented | PASS |
| IX — Simplicity and Incremental Delivery | Modular monolith and bounded slice | Standard library adapters, two narrow ports, no ORM, CLI, parser or generic unit-of-work framework | PASS |
| X — Specification and Decision Governance | Higher-level decisions precede code | ADR 0002 is accepted and expanded before implementation; F002 schemas and identity algorithms remain unchanged | PASS |

### Post-design re-check

The design remains within the approved SQLite/filesystem-CAS architecture. The apparent cross-resource atomicity problem is not hidden: CAS publication precedes the catalog transaction, and any failure between them produces only a complete reachability candidate. No constitutional exception or complexity waiver is required.

## Architecture and Transaction Design

### Resource boundary

```text
validated byte chunks
  -> ObjectStore.put_chunks
  -> complete verified CAS object
  -> PersistenceService verifies every referenced object
  -> Catalog.commit_source_version (one SQLite transaction)
  -> complete source-version fact becomes visible
```

There is no distributed transaction across the filesystem and SQLite. The catalog never references a partially published object, and the CAS never interprets catalog locators as paths.

### Filesystem publication

Objects use `objects/sha256/ab/cd/<remaining-60-hex>`. A secure temporary file below the same storage root is written and hashed incrementally, flushed and synchronized, then atomically published with `os.replace`. Existing destinations are verified before reuse and corrupt/non-regular entries are never silently repaired. Legitimate concurrent writers can replace only with complete bytes that hash to the same destination. The managed root must be private to the OpenARDP process boundary; Python's cross-platform standard library cannot prove race-free safety against an actively malicious same-user filesystem writer.

### SQLite profile

Every operation uses its own thread-bound connection with explicit SQL transaction control. Existing catalogs are compatibility-inspected before any persistent PRAGMA change. The supported profile is:

- `foreign_keys=ON`;
- `busy_timeout=5000`;
- `trusted_schema=OFF`;
- `read_uncommitted=OFF`;
- `journal_mode=DELETE`;
- `synchronous=EXTRA`;
- `query_only=ON` for dedicated read snapshots.

WAL is deliberately not enabled. The observed Python 3.12.13 runtime binds SQLite 3.50.4, which lies in the officially documented 2026 WAL-reset race range. A later WAL option requires a corrected runtime gate and its own recovery evidence.

### Migrations

Two real revisions provide a meaningful upgrade path:

1. objects, documents, source versions and version-object references;
2. jobs, append-only job events, job-object references and operational indexes.

Static statements are executed individually inside one `BEGIN EXCLUSIVE` transaction for all pending revisions. Checksums, ordering and gaps are verified before mutation. `executescript()` and `INSERT OR REPLACE` are prohibited.

### Job fencing

Jobs move through `QUEUED`, `RUNNING`, `SUCCEEDED` and `FAILED`. A caller-supplied cryptographically random lease token supports lost-response retries; only its SHA-256 is stored. Owner, token hash, revision and strict expiry (`expires_at > now`) participate in compare-and-set transitions. Every state change and recovery transition appends a sanitized event in the same transaction.

## Project Structure

### Documentation (this feature)

```text
specs/003-cas-sqlite-catalog/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── storage-catalog.md
├── checklists/
│   ├── requirements.md
│   └── storage-safety.md
├── tasks.md
└── implementation-notes.md
```

### Source code

```text
src/openardp/
├── domain/
│   └── storage.py
├── ports/
│   ├── catalog.py
│   └── object_store.py
├── adapters/
│   ├── filesystem_cas.py
│   ├── sqlite_catalog.py
│   └── sqlite_migrations.py
└── services/
    ├── persistence.py
    └── reachability.py

tests/
├── contract/
│   └── test_storage_ports.py
├── domain/
│   └── test_storage.py
├── integration/
│   ├── test_filesystem_cas.py
│   ├── test_persistence.py
│   ├── test_reachability.py
│   └── test_sqlite_catalog.py
└── security/
    └── test_storage_boundaries.py
```

**Structure Decision**: Extend the existing hexagonal package in place. Pure persistence records and invariants stay in `domain`; protocols and sanitized errors stay in `ports`; filesystem and SQL I/O stay in `adapters`; cross-resource orchestration and reachability stay in `services`. No interface module is added because F004 owns the first product CLI.

## Test Strategy

- Domain tests validate strict identities, source-key exactness, fixed-width UTC storage time, version/reference invariants and job state combinations.
- Port contract tests prove adapters return the same typed outcomes and sanitized error taxonomy expected by services.
- CAS tests cover chunking, empty payloads, 32-thread convergence, spawn-compatible multiprocess publication, interruption, corruption, unsafe entries and bounded reads.
- Catalog tests cover fresh-to-v2, repeated open, v1-to-v2, migration rollback, too-new catalogs, foreign keys, SQL-bound hostile metadata, independent readers and idempotent source-version commits.
- Job tests cover deduplication, fenced claim/renew/complete/fail, exact lease expiry, stale owners, retries, recovery and reopen behavior.
- Reachability tests cover live, candidate, missing, corrupt, malformed and staging entries and compare pre/post bytes to prove no deletion.
- All tests use synthetic data and remain socket-blocked.

## Documentation and Decision Updates

- Accept and expand ADR 0002 with the crash model, SQLite safety profile and read-only reachability boundary.
- Keep ADR 0005 proposed until F012 package interchange.
- Update architecture, data-model, test and operational docs only where F003 makes behavior concrete.
- Update README, START_HERE, specs index, changelog and validation evidence without claiming later ingestion or retrieval features.
- Do not change the five public F002 JSON Schemas; F003 introduces internal persistence records, not a new interchange version.

## Complexity Tracking

No constitutional violation requires justification. The two ports are mandated provider boundaries, the two adapters are the selected local implementations, and the two services each own one cross-resource use case. No ORM, migration framework, repository hierarchy, filesystem abstraction or generic unit-of-work layer is introduced.
