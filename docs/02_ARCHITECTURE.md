# Architecture

## 1. Architectural style

Use a modular monolith for the MVP with hexagonal boundaries. A distributed system would add operational failure modes
before scale requirements are known. Each boundary should permit later extraction into a service.

```text
                ┌──────────────────────────────────────────┐
Sources         │ Local FS | OneDrive/SharePoint (later)  │
                └──────────────────┬───────────────────────┘
                                   │ SourceEvent
                         ┌─────────▼─────────┐
                         │ Ingestion Service │
                         └──────┬───────┬────┘
                                │       │
                    source hash │       │ parse profile
                 ┌──────────────▼─┐   ┌─▼────────────────┐
                 │ Version Catalog │   │ Parser Adapters   │
                 │ SQLite          │   │ Docling default   │
                 └──────────┬──────┘   └───────┬──────────┘
                            │                  │ parser-native output
                            │        ┌─────────▼──────────┐
                            │        │ Normalizer         │
                            │        │ OpenARDP IR        │
                            │        └─────────┬──────────┘
                            │                  │ blocks/assets/relations
                     ┌──────▼──────────────────▼──────┐
                     │ Content-addressed Artifact Store│
                     └──────┬──────────────────┬──────┘
                            │                  │
                  ┌─────────▼────────┐  ┌─────▼────────────┐
                  │ Enrichment DAG   │  │ Index Service     │
                  │ lazy/optional    │  │ FTS + optional vec│
                  └─────────┬────────┘  └─────┬────────────┘
                            │                  │
                         ┌──▼──────────────────▼──┐
                         │ Context Compiler       │
                         └──────┬──────────┬──────┘
                                │          │
                         ┌──────▼───┐  ┌──▼────────┐
                         │ CLI       │  │ MCP/API    │
                         └───────────┘  └───────────┘
```

## 2. Components

### Source adapters

Produce normalized source events. MVP includes local paths. Enterprise adapters must treat notifications only as hints and
reconcile authoritative state using delta APIs.

### Ingestion coordinator

- acquires a per-document lock;
- waits for a stable file snapshot;
- computes SHA-256 while streaming;
- checks whether the version already exists;
- invokes parser and normalizer in a staging transaction;
- validates schemas and invariants;
- atomically commits catalog rows and artifact references.

### Parser adapters

`ParserAdapter` returns:

- parser-native lossless representation;
- normalized candidate blocks/assets/relations;
- warnings and quality signals;
- parser/model/version metadata.

Default rich adapter: Docling. Lightweight fallback: MarkItDown. Optional complex-PDF adapter: MinerU. Native Open XML
adapter is a later optimization for part-level change detection, not the first parser.

### Normalizer

Maps parser-specific data into the stable OpenARDP IR. It must not invent content. Model-generated interpretation belongs
in derived artifacts, never in canonical source blocks.

### Catalog

The implemented F003 SQLite catalog records exact source-key identity, logical documents, immutable source-version facts,
object references, checksummed schema history and recoverable job/event state. Later features add block metadata,
derivation dependencies, staleness and index state through append-only migrations. Binary and large JSON artifacts live
in the content-addressed store rather than ordinary catalog rows.

Every connection enables foreign keys, disables trusted schemas and dirty reads, uses parameterized record SQL and enters
an explicit transaction. The current local profile uses rollback-journal `DELETE` plus `synchronous=EXTRA`; WAL is not an
F003 compatibility requirement. Open rejects newer, gapped, checksum-drifted, structurally drifted or foreign catalogs
without attempting a repair.

### Content-addressed artifact store

Object path:

```text
objects/sha256/ab/cd/<remaining-hash>
```

Objects are immutable. Metadata records media type, length and integrity. Duplicate assets across documents are stored once.

F003 stages bytes below the same managed root, computes SHA-256 and length in one pass, synchronizes the staged file and
publishes with `os.replace`. Reads validate the exact lowercase identity and every managed ancestor, reject links,
junctions, hard-linked/non-regular leaves and verify the full digest. A catalog failure after publication may leave a
complete unreferenced object; it cannot leave a partially visible version.

### Persistence and reachability services

`PersistenceService` orders the two local resources: publish and verify CAS objects first, then commit all catalog facts in
one SQLite transaction. It never rolls back by deleting an object because another record may already reference identical
bytes. `ReachabilityService` captures one catalog-root snapshot, inventories verified objects and reports reachable,
candidate and inconsistent entries. It is advisory and has no delete port.

### Enrichment DAG

Each artifact is a pure or declared transformation:

```text
artifact_key = sha256(
    canonical_json({
        "input_hashes": [...],
        "generator": "picture-caption",
        "generator_version": "1.3.0",
        "model_id": "provider/model",
        "config_hash": "...",
        "prompt_hash": "..."
    })
)
```

If the key exists, reuse it. A network/model call is prohibited when a valid artifact already exists.

### Index service

- SQLite FTS5 is mandatory for exact/local search.
- Embeddings are optional and namespaced by model/profile.
- Reranking is optional and never required for retrieval correctness tests.

### Context compiler

Input:

- query/task;
- document scope;
- budget;
- answer mode;
- required evidence types;
- freshness and trust policy.

Output: immutable `ContextBundle` containing selected representations, provenance and a selection trace.

### Interfaces

- CLI is authoritative for local behavior and test automation.
- MCP wraps application services; it does not contain business logic.
- HTTP API follows the same use cases after contracts stabilize.

## 3. Deployment profiles

### Local MVP

```text
single Python process
SQLite + FTS5
filesystem CAS
local watcher
stdio MCP
Docling in-process or subprocess
```

Run parsers in a worker subprocess even locally when possible, so parser crashes and memory growth do not corrupt the main
process.

### Team server

```text
API/MCP gateway
worker pool
PostgreSQL catalog
S3-compatible/Azure Blob CAS
queue
OpenTelemetry
```

### Microsoft 365 enterprise

```text
Graph webhooks/Event Grid → reconciliation queue → drive delta crawler
→ permission-aware ingestion → tenant-scoped storage/indexes → policy gateway → MCP/API
```

## 4. Transaction boundaries

F003 implements a narrower source-fact boundary: document-version header, source-object metadata and all explicit object
references become visible in one SQLite commit. This fact does **not** mean a parsed representation is `READY`. A complete
object published before a failed catalog commit is a safe reachability candidate.

The later end-to-end ingestion boundary remains:

A version becomes `READY` only after:

1. source object stored or source reference verified;
2. parser-native artifact stored;
3. normalized blocks validated;
4. asset hashes verified;
5. catalog transaction committed;
6. required indexes committed.

Optional enrichment may remain `PENDING`. Search must expose artifact freshness.

## 5. Concurrency

- lock by `(source_connector, source_locator)` during snapshot/ingest;
- deduplicate by source hash globally where allowed;
- lease jobs with timeout and heartbeat;
- make all handlers idempotent;
- use optimistic version checks for catalog updates.

F003 concretely enforces exact source-key uniqueness, composite immutable version identity and job revision compare-and-set
fencing. Raw caller lease tokens are never stored; only SHA-256 token hashes are durable. Lease expiry equality counts as
expired, mutating timestamps cannot move backward, retries are bounded and every state change appends a sanitized event.

## 6. Failure behavior

- Parser failure creates a terminal or retryable job result but no partial version.
- Derived enrichment failure does not invalidate canonical ingestion.
- Stale artifacts are never returned as current unless the caller explicitly allows stale data.
- Missing originals are reported; they are not silently replaced by summaries.
- Failed object staging exposes no canonical leaf. A post-publication catalog failure leaves only a complete orphan.
- Failed migration chains roll back every pending DDL statement and migration record.
- Reachability inconsistencies are reported separately from complete unreferenced candidates and trigger no deletion.
