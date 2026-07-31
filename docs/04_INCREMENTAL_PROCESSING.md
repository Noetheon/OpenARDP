# Incremental processing and cache invalidation

**Status:** Canonical incremental-processing guidance. Feature 005 delivers identical-version reuse and index rebuild;
Feature 010 owns cross-version reconciliation and the derivation DAG.

## 1. Honest guarantee levels

### Level 0 — identical-version reuse (MVP mandatory)

If source SHA-256 and processing profile are already known, perform no parsing or enrichment.

F004 implements this level for local TXT/Markdown. It verifies the source object, manifest and every block object plus
their semantic projections before recording `CACHE_HIT`; corruption fails explicitly and never triggers a concealed
automatic reparse.

### Level 1 — block-level downstream reuse (MVP mandatory)

A changed file may be parsed again, but conservatively matched evidence may reuse summaries, captions, embeddings and
other derivations when exact inputs and generation profiles remain valid.

F010 delivers the conservative reuse decision and exact dependency lifecycle for F002
block aggregates. It records continuity independently from reuse: a match is reusable
only when the previous/current canonical content digests are equal. F010 does not run a
generator or automatically schedule reconciliation.

### Level 2 — format-aware parse optimization (post-MVP)

- PPTX: hash slide XML, notes, relationships and referenced assets; reparse changed parts.
- DOCX: hash package parts and use paragraph/table anchors; carefully account for styles, numbering, headers and fields.
- XLSX: hash sheets/shared strings/styles/dependencies.
- PDF: compare page-level extraction/render fingerprints after parsing; true incremental parsing is parser-dependent.

## 2. Event pipeline

```text
file event
→ debounce by path
→ wait for stable size/mtime and successful shared/read lock
→ stream SHA-256
→ lookup version/profile
→ skip OR enqueue ingestion
→ parse in staging worker
→ preserve native artifact + build thin evidence projection
→ reconcile evidence with prior version
→ compute change set
→ commit canonical version
→ invalidate/reuse derived artifacts
→ update indexes
```

The diagram is the target watcher/enrichment pipeline. Features 004–005 have no watcher: an explicit `ingest` snapshots one regular
source descriptor, parses the verified CAS object in a spawned worker, commits one complete representation, and advances a
document head by source-observation time. Reverting A → B → A reuses historical A and advances the head without rewriting
its first source-version facts. Feature 005 also publishes and verifies lexical index coverage transactionally.

## 3. Debounce and stable snapshot

A Word save may create temporary files, rename files or emit several events. The watcher must:

- ignore Office lock files such as `~$...`;
- coalesce events for a configurable quiet period;
- require two equal `(size, mtime)` observations;
- open and hash a snapshot, not assume the event path remains stable;
- retry sharing violations;
- detect deletion separately.

## 4. Block reconciliation

Apply in order:

1. native stable ID match;
2. exact canonical content hash in same structural neighborhood;
3. table/asset identity match;
4. structural path and normalized-text similarity;
5. sequence alignment for remaining siblings;
6. new identity if confidence is insufficient.

Persist `same_logical_block_as` with confidence and algorithm version. Do not automatically transfer derived artifacts
across a low-confidence match.

The delivered v1 matcher requires one-to-one unique candidates, fixed-point confidence
and a sufficient winner margin. Duplicate/tied/incompatible candidates receive a new
lineage. Native identity or high similarity can establish continuity but never override
a changed content digest. Every accepted relation is canonicalized, CAS-published and
retained as a reachability root before its catalog run becomes visible.

## 5. Dependency invalidation

Each derivation records direct input artifact hashes. A derivation is current only when:

- every dependency is available;
- dependency hashes match;
- generator/profile versions match;
- security/policy profile permits reuse;
- it has not been explicitly revoked.

Parent summaries depend on child block hashes or child summary artifacts. A table edit therefore invalidates the table
summary and ancestors, but not unrelated images.

Revision 7 records these direct edges explicitly. A head-changing reconciliation first
rechecks that the target is still current, then stales the sorted recursive closure of
current nodes that consume inactive bindings. Revalidation iterates stale nodes to a
deterministic fixed point and requires every evidence binding active at a current head,
every immutable object physically verified and every producer current with the exact
recorded output. Failed and superseded nodes never reactivate. An A→B→A return can
therefore restore the exact historical node/record/output without invoking a provider.

## 6. Queue semantics

- at-least-once delivery;
- idempotent jobs;
- deterministic deduplication key;
- bounded retries;
- dead-letter state with actionable error details;
- cancellation when a newer source version supersedes an unstarted job.

## 7. Microsoft 365 synchronization

Feature 017’s mock-only enterprise connector design:

1. Graph change notification wakes the connector.
2. Connector executes the saved Drive delta link.
3. Delta results update the local source catalog.
4. Content is fetched only for relevant changed items.
5. New delta link is persisted atomically.
6. Lifecycle events renew or reauthorize subscriptions.
7. Periodic reconciliation protects against missed notifications.

Notifications are not treated as a complete event log.
