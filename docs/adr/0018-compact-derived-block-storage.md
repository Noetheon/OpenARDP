# ADR 0018: Compact derived-block storage and normalized block projections

Status: Accepted for Feature 022

Date: 2026-08-02

## Context

The F020 reference workload persisted 73,874,827 logical workspace bytes for a 1,949,999-byte source (37.8845x) and
739,947,189 bytes for a 19,499,999-byte source (37.9460x). A fresh F022 profile decomposition attributes roughly two
thirds of the logical total to repeated SQLite scope/search metadata and one third to loose CAS, including one canonical
JSON file per block. On APFS the 20,002 small block/manifest files occupy about 81.9 MiB despite containing 20.4 MiB.

The existing decisions remain binding: originals are authoritative, SHA-256 identifies exact logical bytes, returned
evidence is verified, indexes are disposable, SQLite remains the catalog and the runtime CAS remains filesystem-backed.
Changing public identities, dropping history or serving FTS content as evidence would reduce bytes by weakening the
product and is rejected.

## Decision

Retain the SQLite catalog and filesystem content-addressed store, with two bounded internal evolutions:

1. Workspace revision 11 normalizes repeated representation scope fields behind a surrogate scope key. One compact
   block projection owns body-free navigation plus nullable disposable search metadata. The separate search-mapping table
   and redundant global/scope indexes are removed. FTS remains contentless and rebuildable; returned bodies and sensitive
   metadata continue to be verified against catalog projections and CAS objects.
2. The filesystem CAS gains `openardp-deflate-dict-v1`, an optional physical form only for canonical derived F002 block
   JSON. Its path is still derived solely from the logical SHA-256 identity, while a fixed envelope declares the logical
   length and a version-pinned raw-DEFLATE dictionary. Verification expands under a strict logical bound and recomputes
   the SHA-256 over exact logical bytes. The compact form is published only when its complete envelope is smaller.

Source snapshots, provider-native representations and arbitrary artifacts remain ordinary exact-byte CAS leaves.
Logical object identities, byte lengths, F002 schemas, representation IDs, block IDs and replay bytes do not change.

Fresh text ingestion requests the compact derived-block profile through an optional narrow object-store capability;
providers without that capability retain the ordinary form. Existing workspaces use an explicit backup-first revision-11
migration followed by an idempotent `storage-optimize` operation. Ordinary `open` never migrates or compacts. A crash may
leave both physical forms; retry verifies both, keeps the compact form and synchronously removes only the eligible derived
ordinary leaf. Missing, corrupt, unsafe or non-saving objects fail or remain ordinary without hidden data loss.

Reachability, full verification, diagnostics, quarantine, backup and restore understand both layouts and count one
logical identity once. Backup inventories bind the exact physical relative file copied as well as the logical object set.
Valid duplicate forms are a recoverable optimization residue; conflicting or corrupt forms are inconsistent storage.

## Rationale

- Normalizing repeated keys attacks the measured 49.6 MiB catalog cause instead of changing page size or hiding files.
- A versioned per-object encoding preserves independent addressability, exact retrieval and current maintenance semantics,
  unlike multi-object packs whose partial retention and recovery require a new locator/index authority.
- A static dictionary exploits repeated canonical schema/provenance keys substantially better than generic per-file
  compression while remaining deterministic, standard-library-only and bounded.
- Keeping originals and native artifacts ordinary preserves direct byte inspection and the strongest evidence boundary.
- Optional capability fallback keeps the storage port provider-neutral and avoids making one filesystem encoding public.

## Consequences

- Older binaries reject revision-11 workspaces; the verified revision-10 backup is the rollback artifact.
- Logical amplification and catalog size fall materially, but one-file-per-block allocation remains a known limitation.
  F022 therefore reports both logical and allocated bytes and does not equate them.
- Full integrity and maintenance scans must decode compact blocks and are CPU-heavier per compact object; this is measured
  and remains explicit rather than moved into default F021 freshness.
- The catalog migration and physical optimization are separately restartable. A migrated workspace can remain correct
  with ordinary blocks until explicit optimization completes.
- No runtime dependency, network capability, public schema version, application version or export profile changes.

## Rejected Alternatives

- Delete history, omit block objects or trust FTS text: violates evidence preservation and measured-workload fairness.
- Change block/object identifiers to hash compressed bytes: breaks persisted identity and interchange semantics.
- Compress sources/native artifacts: weakens direct original evidence handling for limited additional value.
- Multi-object packfiles: reduce allocation further but introduce locator authority, partial-retention rewriting and broader
  crash recovery than this bounded feature can justify.
- Store canonical block bodies in SQLite: makes catalog/body failure domains converge and reverses the thin metadata
  boundary.
- Change SQLite page size or run `VACUUM` alone: does not remove the measured repeated strings and redundant indexes.
