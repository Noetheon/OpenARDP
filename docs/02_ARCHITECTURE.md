# Architecture

**Status:** Canonical architecture. Sections distinguish delivered Features 001–012 from planned components in the
[005A–017 feature map](../spec-kit/FEATURE_MAP.md). Feature 007 delivered the bounded
Docling-native adapter; Feature 008 delivered the deterministic context compiler and
selection receipts described below.
Feature 010 delivers conservative F002 block lineages and the exact derivation lifecycle;
it does not add generator execution. Feature 012 delivers local foreground polling and
stable jobs; it does not add a daemon, cloud connector or MCP mutation.

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
                            │        │ Native artifact    │
                            │        │ + thin projection  │
                            │        └─────────┬──────────┘
                            │                  │ evidence/anchors/trust
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

The implemented F004/F005 coordinator snapshots an explicitly selected regular local file into CAS, registers or reuses its
immutable source version, and acquires a fenced representation claim. Parsing runs outside SQLite against CAS bytes only;
the complete manifest, native reference, normalized block projections, head and ingestion event then become visible in
one immediate transaction. An unchanged candidate is reused only after physical and semantic verification of every READY
artifact. F012 composes this unchanged coordinator behind exact revalidated watcher
targets; it does not introduce a watcher-specific parser or source identity.

### Parser adapters

`ParserAdapter` receives byte chunks plus a declared media type and returns deterministic candidate blocks, hierarchy,
line provenance and bounded warnings under an immutable recipe. For F004 the exact source CAS object is also the lossless
native artifact. The product composition always uses a fresh spawned `IsolatedParserAdapter`; the pure adapter is reserved
for deterministic unit tests. The worker receives no source path, denies socket creation and is bounded by bytes, line
length, block count and wall-clock time.

The built-in `openardp-text` adapter supports only UTF-8 TXT and a reviewed Markdown subset. Docling and other rich-format
providers remain later adapters rather than implicit F004 dependencies.

### Native artifacts and evidence projection

The complete provider-native representation is retained unchanged as an immutable derived artifact. A projection builder
emits only evidence identity, navigation, retrieval, trust and lifecycle fields. It must not invent content or reproduce
the provider’s complete model. Model-generated interpretation belongs in derived artifacts, never in source evidence.

### Catalog

The implemented SQLite catalog records exact source-key identity, logical documents, immutable source-version facts,
object references, recoverable job/event state and, since revision 3, fenced document representations, body-free block
projections, current heads and append-only ingestion evidence. Revision 4 adds lexical index coverage and mapping records.
Revisions 5–6 add rich attempts and immutable context compilations. Revision 7 adds
reconciliation runs, complete lineage memberships, CAS-backed relations and exact
derivation slots/nodes/dependencies/events. Canonical relation, generation-record and
output bytes live in the content-addressed store; the catalog retains only verified
metadata and the canonical F002 generation-record JSON required to reconstruct and
fingerprint its internal lifecycle row.
Revision 8 adds visual page/crop evidence. Revision 9 atomically rebuilds the released
job tables to add eligibility and cancellation, then adds watcher roots, observations,
exact targets and body/path-free events. The public JSON schemas remain unchanged.

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

F010 implements the provider-free publication/lifecycle half of this component.
`DerivationService` accepts a valid terminal F002 record plus already-generated output
chunks, publishes and verifies record/output CAS objects, and commits the node, ordered
direct edges, slot pointer and event in one SQLite transaction. Evidence changes stale
the exact current transitive closure; historical nodes reactivate only when every exact
binding/object/producer input is current and verified. `SUPERSEDED` is reserved for a
new artifact occupying the same deterministic logical-output slot.

### Index service

- SQLite FTS5 implements exact local search in Feature 005.
- Embeddings are optional and namespaced by model/profile.
- Reranking is optional and never required for retrieval correctness tests.
- All indexes are disposable accelerators. Hits, bodies, trust and attribution are verified against CAS/catalog authority.

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
- The delivered read-only MCP stdio interface wraps the same query, search, evidence
  and context-compiler services; it contains no business logic or path resolver.
- HTTP API follows the same use cases after contracts stabilize.

## 3. Deployment profiles

### Local MVP

```text
single Python process
SQLite + FTS5
filesystem CAS
bounded parser worker
CLI
read-only stdio MCP
```

The F012 watcher is an optional foreground loop in the same process; it is not an
installed service. HTTP remains a later bounded feature. Run rich parsers in a worker process with explicit limits
and denied network where supported; this is defense in depth, not a universal strong sandbox.

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

F003's source-fact boundary remains unchanged. F004 additionally implements the complete text-representation boundary:

A version becomes `READY` only after:

1. source object stored or source reference verified;
2. parser-native artifact stored;
3. normalized blocks validated;
4. every required object hash and semantic scope verified;
5. catalog representation, block projections, head and event committed atomically.

F005 publishes lexical entries in the same transaction before the representation becomes READY. Coverage and drift fail
closed, and `reindex` rebuilds from verified READY evidence. A complete object published before a failed catalog
transaction is a safe reachability candidate, never a partially visible READY representation.

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

F004 applies the same fencing posture to `(document_id, version_id, representation_id)`. One unexpired owner may parse;
same-token retries are idempotent, stale owners cannot commit, and forced parsing of READY state succeeds only when the
new canonical aggregate is byte-identical to the persisted evidence.

F012 claims only eligible `watch_ingest` jobs for the selected root. Retry eligibility
is a persisted UTC instant. Queued cancellation is immediately terminal; running
cancellation increments the revision, fences stale renew/complete/fail operations and
is acknowledged by the current owner or expired-lease recovery. Watch reconciliation
and target creation share one SQLite transaction, while parsing remains outside it.

### Delivered Feature 012 watcher

`WatcherService` treats polling observations as hints. `LocalWatchScanner` admits one
canonical absolute directory disjoint from the managed workspace, rejects links and
recognizable UNC/device authority, stays on the root device and returns either a
complete sorted bounded metadata set or an empty incomplete result. Complete scans
advance a durable generation, debounce unchanged fingerprints, tombstone missing
path-addressed locators and schedule at most the configured active capacity. Exact
source bytes are still acquired and SHA-256 hashed by the existing ingestion service.

Rename recognition is audit-only: a unique one-to-one same-root file identity emits a
redacted hint, while the old path is tombstoned and the new path follows a fresh
observation lifecycle. Hard-link ambiguity degrades to independent path facts.

## 6. Failure behavior

- Parser failure creates a terminal or retryable job result but no partial version.
- Derived enrichment failure does not invalidate canonical ingestion.
- Stale artifacts are never returned as current unless the caller explicitly allows stale data.
- Missing originals are reported; they are not silently replaced by summaries.
- Failed object staging exposes no canonical leaf. A post-publication catalog failure leaves only a complete orphan.
- Failed migration chains roll back every pending DDL statement and migration record.
- Reachability inconsistencies are reported separately from complete unreferenced candidates and trigger no deletion.

## 7. Delivered Feature 008 context compiler

The context compiler is a provider-neutral service above the existing ports. One
invocation resolves an exact READY corpus snapshot, discovers lexical candidates from
the verified FTS accelerator and the bounded rich-projection scan, reverifies every
candidate body against content-addressed facts, classifies trust/sensitivity/freshness
under the declared policy, sorts by a documented total order and admits items greedily
under one fixed-point estimator budget with a ten-percent response reserve. Output is
one public `ContextBundle 0.2.0` with structurally delimited untrusted-data envelopes
plus one body-free experimental `SelectionReceipt 0.1.0`.

Persistence composes the existing primitives: both canonical objects are published to
the CAS, reverified, then linked atomically by checksummed workspace migration 6 rows
with exact scope foreign keys. Replay rebuilds the recorded snapshot from those scope
rows and requires byte-identical bundle and receipt objects; algorithm, estimator,
policy and task drift fail with closed mismatch codes instead of silent recompilation.
All failure paths use the sanitized ports taxonomy with bounded cancellation
checkpoints; pre-published objects from interrupted runs remain unreachable immutable
recovery candidates until Feature 013 retention tooling.
