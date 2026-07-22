# Research: Content-Addressed Storage and SQLite Catalog

**Date**: 2026-07-22

**Scope**: Resolve F003 storage, transaction, migration, recovery and security decisions before design. Research used repository sources plus official Python, SQLite, POSIX, Apple and Microsoft documentation. No networked behavior enters the implementation.

## Decision 1 — Preserve the CAS and catalog as two explicit resources

**Decision**: Publish and verify a complete CAS object first, then atomically commit catalog facts and the entire reference set in SQLite. A failure between resources may leave a complete unreferenced object, never a partial logical version.

**Rationale**: Filesystem rename and SQLite commit cannot participate in one portable atomic transaction. The safe invariant is asymmetric: durable bytes may temporarily lack a reference, but a visible reference must never point to incomplete bytes. Read-only reachability exists specifically to expose the benign orphan case.

**Alternatives considered**:

- Pretend filesystem and SQLite share one transaction: rejected as false.
- Insert a visible `STAGING` version before CAS publication: rejected because readers would need extra correctness filters and partial logical state would become durable.
- Delete the CAS object when SQLite fails: rejected because concurrent references and crash timing make compensating deletion unsafe.

## Decision 2 — Atomic filesystem publication uses same-root staging and `os.replace`

**Decision**: Write secure temporary files below `<root>/staging`, compute SHA-256 and byte length while streaming, flush and `fsync`, then atomically publish to `objects/sha256/ab/cd/<remaining-hash>` with `os.replace`. Verify a pre-existing destination before reuse and never silently overwrite a destination already known to be corrupt or unsafe.

**Rationale**: Same-root staging avoids cross-filesystem rename. `os.replace` provides portable atomic destination replacement and follows the repository's mandated `tempfile` plus `os.replace` pattern. Legitimate duplicate writers publish only complete bytes with the same digest. Windows hard links are filesystem-dependent, while direct exclusive creation at the final name exposes partial bytes.

**Alternatives considered**:

- Direct final-path write: rejected because readers can observe prefixes.
- System temp directory: rejected because publication can cross filesystems.
- Hard-link no-clobber publication: rejected as insufficiently portable across supported Windows filesystems and inconsistent with repository guidance.
- Global lock file: rejected because it introduces stale-lock recovery and platform-specific semantics.

**Primary sources**: [Python 3.12 tempfile](https://docs.python.org/3.12/library/tempfile.html), [Python 3.12 os](https://docs.python.org/3.12/library/os.html), [POSIX rename](https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html), [Microsoft MoveFileEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexa).

**Amendment (F004 hardening)**: A macOS CI race during feature 004 showed that `os.replace` lets two legitimate duplicate writers swap the same destination inode while a concurrent `verify` holds it open, producing spurious `UnsafeStoreEntry`/`ObjectCorrupt` failures. Publication is now platform-split no-clobber: POSIX links the staged file to the destination (`os.link` fails with `FileExistsError` when it exists) and then unlinks the staged name, while Windows keeps the no-clobber `os.rename` behavior. The POSIX transient second link is recognized by a bounded settling re-check that confirms a staged twin inode before any reuse verification retries; the transient never passes verification and still fails closed once no twin can be observed. The original hard-link rejection applied to a single cross-platform mechanism; the portability concern is now answered by the platform split. See the feature 004 implementation notes.

## Decision 3 — Validate the managed object tree without interpreting user paths

**Decision**: Public reads accept only `sha256:<64 lowercase hex>`. Only validated digest segments build object paths. Managed ancestors and leaves are inspected without following links; symlinks, Windows junctions, non-regular leaves, hard-linked leaves where link counts are reliable, and malformed tree entries are reported as unsafe.

**Rationale**: Connector locators are untrusted opaque metadata and never path authority. Digest-only mapping removes traversal syntax from normal path construction. `lstat`, non-following opens where available, post-open `fstat`, and a private app-owned storage root provide a practical cross-platform boundary.

**Residual risk**: Python's portable standard library cannot guarantee race-free defense against an actively malicious same-user process mutating a Windows storage root. F003 supports local, app-owned roots, not shared or untrusted-writable NFS/SMB locations.

**Alternatives considered**:

- `Path.resolve().is_relative_to(root)` alone: rejected because it follows links and does not eliminate time-of-check/time-of-use races.
- Trust the configured object tree: rejected because corrupted or manually altered stores must fail safely.

**Primary sources**: [Python 3.12 os stat/open/scandir](https://docs.python.org/3.12/library/os.html), [Microsoft CreateFile reparse-point flags](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilea).

## Decision 4 — Make durability claims precise and platform-bounded

**Decision**: Synchronize staged file content before publication and synchronize destination directories where the platform exposes directory file descriptors. A post-publication sync failure reports durability uncertainty; retry verifies and re-syncs the complete object. F003 claims process-crash atomic visibility and best-effort local durability, not universal power-loss survival.

**Rationale**: Linux requires directory synchronization for rename durability; macOS may require `F_FULLFSYNC` for stronger hardware-cache flushing; Windows' standard replacement call does not automatically request write-through. Hardware and filesystem behavior cannot be made uniform from pure Python.

**Alternatives considered**:

- Claim absolute durable commits after `fsync(file)`: rejected as inaccurate.
- Ignore directory sync: rejected where the platform provides it.
- Fail by deleting after a post-publish sync error: rejected because the published object is complete and deletion is outside F003.

**Primary sources**: [Linux fsync](https://man7.org/linux/man-pages/man2/fsync.2.html), [Apple fsync](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html), [Apple F_FULLFSYNC](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fcntl.2.html), [Microsoft FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers).

## Decision 5 — Use explicit SQLite transactions and one connection per operation

**Decision**: Open Python 3.12 connections with `autocommit=True`; use internal `BEGIN IMMEDIATE` for mutations, `BEGIN EXCLUSIVE` for migration chains, and explicit SQL `COMMIT`/`ROLLBACK`. Keep connections thread-bound and short-lived. Never expose a generic transaction port.

**Rationale**: Explicit SQL makes locking and visibility boundaries auditable. `autocommit=False` automatically opens deferred transactions and makes exact boundaries harder to reason about. One connection per operation avoids shared-connection concurrency ambiguity.

**Alternatives considered**:

- Shared `check_same_thread=False` connection: rejected because correctness would depend on external serialization.
- ORM/Alembic: rejected as an unnecessary dependency and abstraction for two small static migrations.
- `executescript()` migration: rejected because its transaction behavior can invalidate atomicity assumptions.

**Primary sources**: [Python 3.12 sqlite3 transaction control](https://docs.python.org/3.12/library/sqlite3.html), [SQLite transactions](https://www.sqlite.org/lang_transaction.html), [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

## Decision 6 — Default to rollback journal `DELETE` plus `synchronous=EXTRA`

**Decision**: F003 explicitly configures `journal_mode=DELETE` and `synchronous=EXTRA`. It also enables foreign keys, a bounded busy timeout, `trusted_schema=OFF`, and `read_uncommitted=OFF`; read snapshots add `query_only=ON`.

**Rationale**: The observed locked runtime is Python 3.12.13 with SQLite 3.50.4. SQLite's current official WAL documentation places 3.50.4 in the 2026 WAL-reset race range, with fixes only in later patch releases. Rollback journal avoids that known risk and WAL sidecar/backup complexity. In DELETE mode, `EXTRA` adds directory synchronization beyond `FULL`.

**Alternatives considered**:

- WAL as a fashionable default: rejected for the actually shipped SQLite runtime and because F003 does not need its reader/writer throughput tradeoff.
- `synchronous=NORMAL`: rejected because acknowledged transaction loss can occur after power failure.
- Silent WAL-to-DELETE fallback: rejected because configuration drift must be explicit.

**Primary sources**: [SQLite WAL and WAL-reset bug](https://www.sqlite.org/wal.html), [SQLite synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous), [SQLite foreign keys](https://www.sqlite.org/pragma.html#pragma_foreign_keys), [SQLite trusted schema](https://www.sqlite.org/pragma.html#pragma_trusted_schema).

## Decision 7 — Use two checksummed transactional migrations

**Decision**: Revision 1 creates objects, documents, source versions and version references. Revision 2 creates jobs, job events, job references and indexes. Static statement tuples have stable SHA-256 checksums. On open, the adapter rejects foreign schemas, gaps, checksum drift and newer revisions before persistent configuration changes; all pending revisions apply within one exclusive transaction.

**Rationale**: Two real revisions exercise the upgrade path required by F003 without dummy schema. A migration record is written only after its statements succeed, and one transaction over the pending chain leaves the previous catalog intact on failure.

**Alternatives considered**:

- One monolithic initial revision: rejected because it cannot honestly prove an installed older-to-current upgrade.
- Separate migration transaction per revision: rejected in F003 because partial pending-chain advancement is less predictable.
- `PRAGMA user_version` as sole truth: rejected because it has no checksum or migration identity.

## Decision 8 — Keep global object identity separate from document version identity

**Decision**: `objects.object_id` is global SHA-256 identity. `document_versions` uses `(document_id, version_id)` and requires `source_object_id == version_id`. Source keys compare exact `(connector, locator)` text with no Unicode, case or whitespace normalization.

**Rationale**: The same exact bytes can represent the source version of multiple logical documents. F002 already defines version identity from source bytes; F003 must persist that rule without changing it. Exact source-key comparison avoids accidental aliasing and keeps locators opaque.

**Alternatives considered**:

- Global `version_id` primary key: rejected because it collapses distinct logical documents.
- Normalize source locators: rejected because connectors own locator semantics.
- Store media type globally on the object: rejected because identical bytes can be classified differently by reference context.

## Decision 9 — Generate UUIDv7 internally with injected time/randomness

**Decision**: Provide a small RFC 9562-compatible UUIDv7 generator using an injected millisecond clock and cryptographic random bits. Validate all resulting identifiers through the existing F002 `DocumentId` contract.

**Rationale**: F002 requires UUIDv7, while Python 3.12 has no `uuid.uuid7()`. A small tested generator avoids adding a runtime dependency or silently weakening the identity contract to UUIDv4. Concurrent registration remains protected by the source-key unique constraint.

**Alternatives considered**:

- UUIDv4: rejected because it contradicts the public F002 contract.
- New UUID library: rejected because one reviewed generator is smaller than an added core dependency.

**Primary sources**: [Python 3.12 uuid](https://docs.python.org/3.12/library/uuid.html), [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html).

## Decision 10 — Fence job leases with token hashes and revisions

**Decision**: Jobs use `QUEUED`, `RUNNING`, `SUCCEEDED` and `FAILED`; each claim increments attempt count and revision. Worker mutations compare job id, revision, owner, SHA-256 lease-token hash and strict expiry. Only token hashes are persisted. State transitions append sanitized events atomically.

**Rationale**: Owner names alone have an ABA problem after expiry and reassignment. A caller-supplied strong token makes a lost claim response retryable without storing a bearer token. Fixed-width UTC timestamps make lexicographic SQL comparison deterministic.

**Alternatives considered**:

- Owner-only lease: rejected because a stale worker can overwrite a newer claim using the same owner name.
- Store raw token: rejected because the database needs only equality proof.
- Add `CANCELLED` now: deferred until F009 introduces scheduler cancellation semantics.
- Store free-form failure text: rejected because it can leak source content and destabilize machine handling.

## Decision 11 — Treat all version and job references as conservative reachability roots

**Decision**: The catalog snapshot returns object identities referenced by every committed historical source version and every job, including terminal jobs. The service inventories and verifies the CAS after the snapshot, classifying reachable objects, unreferenced complete candidates, missing/corrupt references, malformed entries and staging residues. It never deletes.

**Rationale**: F003 has no retention policy. Conservative roots protect evidence, while candidates mean only "unreferenced at the observed snapshot." A concurrent CAS publish may appear as a candidate before its later catalog commit; this is harmless because the report is advisory.

**Alternatives considered**:

- Treat every `objects` row as reachable: rejected because metadata rows alone would hide true orphans.
- Drop terminal-job references: rejected because retention is undefined.
- Delete candidates automatically: rejected by scope and evidence-preservation rules.

## Decision 12 — Accept ADR 0002 before production code

**Decision**: Change ADR 0002 from Proposed to Accepted and record the source-version boundary, CAS-before-catalog crash model, SQLite safety profile and read-only reachability rule. Leave ADR 0005 Proposed until F012.

**Rationale**: F003 is the first production implementation of these architecture choices. Project governance requires the ADR to become authoritative before code relies on it.

## Resolved unknowns

- No new runtime dependency is needed.
- WAL is not safe as the current default and is outside F003.
- F003 persists committed source-version facts, not complete ready representations.
- CAS and SQLite atomicity are deliberately separate.
- Job recovery is generic persistence behavior; watcher orchestration remains F009.
- Power-loss guarantees remain bounded to documented OS/filesystem behavior.
- All research questions are resolved; no `NEEDS CLARIFICATION` item remains.
