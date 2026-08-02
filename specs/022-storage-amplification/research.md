# Research: Storage Amplification Reduction

## Measured cause decomposition

**Decision**: Bind design work to a retained reference decomposition rather than the aggregate 37.9x ratio alone.

**Rationale**: A reproduced 10,000-block complete workload measured 73,854,221 logical bytes and 136,196,096 allocated
bytes across 20,008 files. SQLite used 49,573,888 bytes. CAS used 24,280,216 logical bytes; 20,002 sub-1-KiB leaves held
20,377,180 logical bytes but 81,928,192 allocated bytes. SQLite `dbstat` attributed approximately 39.2 MiB to the two
block/search mapping tables and their overlapping indexes.

**Alternatives considered**: infer causes from source code; use only `du`; report only F020's total. All conceal either
logical duplication or allocation overhead.

## Relational normalization boundary

**Decision**: Revision 11 introduces one normalized representation-scope table and rebuilds the block table around a
surrogate scope key. Body-free disposable search metadata moves onto the matching block row; the separate mapping table,
global block index and redundant scope index disappear. Existing FTS row IDs are retained where coverage exists.

**Rationale**: A populated schema simulation reduced the relevant structures from roughly 39.2 MiB to 8.3 MiB while
retaining text identifiers and the scoped uniqueness constraints used by reconciliation. Merging search metadata avoids a
second copy of document/version/representation/block/kind/line data without making FTS authoritative.

**Alternatives considered**: BLOB-convert every persisted identifier (smaller but broad and migration-heavy); drop only
indexes (insufficient); store bodies in the catalog (rejected evidence boundary); use views/triggers as permanent legacy
emulation (hidden complexity).

## Derived-block physical encoding

**Decision**: Add one optional `openardp-deflate-dict-v1` filesystem-CAS namespace for canonical F002 block JSON. Use a
fixed magic/version, unsigned logical length, raw DEFLATE payload and a code-pinned dictionary. Enforce a 16 MiB logical
ceiling, exact end-of-stream, no trailing data, declared-length equality and logical SHA-256 verification. Publish compact
only when the complete envelope is smaller.

**Rationale**: Generic per-object DEFLATE retained about 62.9 percent of sampled bytes; a fixed 716-byte dictionary built
only from stable schema keys/profile vocabulary retained about 24.1 percent including a conservative envelope. Identity
continues to describe canonical logical bytes, and every object remains independently addressable.

**Alternatives considered**: zstd (new native dependency/supply-chain cost); gzip wrapper (more overhead, no preset
dictionary); transparent compression of every object (risks originals); packfiles (better allocation, unsafe partial
retention complexity); schema-shortened block JSON (public canonical identity change).

## Provider-neutral capability

**Decision**: Keep the existing `ObjectStore` baseline unchanged and add an optional runtime-checkable compact-record
capability plus an explicit optimization capability. Text ingestion uses the compact capability for block records only and
falls back to ordinary `put_chunks`; other object-store providers remain conformant.

**Rationale**: Physical encoding is an adapter optimization, not a required semantic operation. A separate narrow
capability avoids adding filesystem-specific parameters to every provider and preserves existing test doubles.

**Alternatives considered**: change the mandatory `put_chunks` signature (provider break); inspect JSON heuristically in
the filesystem adapter (could compact originals); couple the catalog to physical locators (inward dependency violation).

## Existing-workspace migration and optimization

**Decision**: Apply the schema only through the existing explicit verified backup-first migration. Record the revision-11
backup identity. Physical block conversion is a separate idempotent `storage-optimize` operation; migration may finish
correctly with ordinary blocks, and retry never parses or reads original sources.

**Rationale**: SQLite migration and thousands of filesystem publications cannot share one transaction. Separating them
makes every durable state valid: revision 10 unchanged, revision 11 with ordinary blocks, duplicates after compact publish,
or revision 11 compact. The backup remains a real rollback boundary.

**Alternatives considered**: rewrite during `open` (hidden mutation); hold the schema transaction across filesystem work
(long lock and false atomicity); delete ordinary blocks before compact verification (data loss); require migration to be
all-or-nothing across resources (unimplementable claim).

## Duplicate-form and corruption semantics

**Decision**: Direct verification validates every present form. Two valid forms with one logical identity are recoverable
optimization residue and counted once; a corrupt, unsafe or conflicting present form makes the store inconsistent.
Maintenance mutation is blocked until `storage-optimize` converges duplicates.

**Rationale**: Choosing the valid copy while ignoring a corrupt duplicate would hide tampering; counting both would
inflate logical inventory. Blocking maintenance prevents one encoding from remaining active after quarantine.

**Alternatives considered**: prefer compact unconditionally; silently delete duplicates on open; treat duplicate forms as
two objects. Each weakens integrity or introduces hidden mutation.

## Backup, restore and retention

**Decision**: Extend closed active/quarantine scans to both physical namespaces. Each logical maintenance object records
its physical form internally. Backup copies the exact observed relative file and binds its physical digest in the existing
file inventory; restore verifies the manifest, physical bytes and decoded logical object inventory before publication.

**Rationale**: The current backup already inventories exact files plus logical roots. Preserving that model supports both
forms without an export-format change. Retention can move/delete one uniquely located encoded leaf with the same durable
intent journal.

**Alternatives considered**: decode blocks into ordinary form during backup (backup no longer exact); exclude compact
files as derived (breaks offline restore); add a second backup format (unnecessary compatibility surface).

## Benchmark and decision policy

**Decision**: Add `benchmarks/storage/v0.1.0` with fresh reference, migrated reference and fresh scale scenarios. Retain
source/workspace identities, category/file/allocation inventories, exact correctness judgments and deterministic decisions.
Pass requires <=15x logical at both scales, >=60 percent logical reduction versus F020, <=55x allocated reference on the
binding environment and zero semantic/migration/integrity regressions.

**Rationale**: Fresh-only results do not prove migration; reference-only results can hide scale drift; logical-only results
hide file allocation. The three scenarios are the smallest complete evidence set.

**Alternatives considered**: rerun all F020 timings (unnecessary for a storage decision); measure only `du`; publish one
favorable aggregate without categories or migration.
