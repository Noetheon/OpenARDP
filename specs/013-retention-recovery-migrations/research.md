# Research: Retention, Recovery and Migrations

## Decision 1 — Conservative live roots and bounded actionable plans

**Decision**: v0.1 protects every object referenced by the catalog through F012 plus
every active operator hold. The catalog exposes one transactional retention snapshot
containing the schema revision, sorted `(object_id, reason_code, opaque_reference)`
edges and active holds. The filesystem adapter returns a bounded verified active and
quarantine inventory including exact length and safe modification time.

The semantic plan identity is JCS/SHA-256 over a versioned policy, schema revision,
root/hold digest, full verified inventory/anomaly digest and exact sorted candidates.
Reporting time is excluded. Any inconsistency or `limit + 1` result returns no
actionable plan identity or partial candidate set.

**Rationale**: false retention is reversible; false reclamation is not. Exact root and
inventory evidence lets quarantine reproduce the plan under its write fence.

**Rejected**: treating derived objects as disposable merely by type; persisting dry-run
plans; using age or wall clock as the only authorization; returning partial plans.

## Decision 2 — Dedicated maintenance authority

**Decision**: keep `ObjectStore` unchanged and non-destructive. Add a narrow internal
filesystem-maintenance port used only by the maintenance service/composition root.
Document content, parser results, MCP tools and normal services cannot reach it.

**Rationale**: deletion capability should not leak into routine ingestion or query
consumers. This preserves the released CAS safety contract.

## Decision 3 — Restart-persistent intent bridges SQLite and files

**Decision**: revision 10 adds one durable maintenance operation plus ordered exact
entries. A partial unique index permits only one `PREPARED`/`APPLYING` operation.
Ordinary catalog writes reject while that fence exists; operation-ID-scoped maintenance
methods alone may progress it.

Protocol:

1. validate all inputs and compute exact actions;
2. transactionally revalidate roots/holds and persist complete ordered intent;
3. perform idempotent filesystem transitions;
4. transactionally verify outcomes, update lifecycle/audit rows and mark terminal.

Before step 2 no filesystem mutation occurs. After it, explicit recovery has complete
authority and finishes forward. Filesystem presence alone never creates authority.

**Rationale**: SQLite and the filesystem do not offer a shared transaction. A transient
process lock cannot survive a crash; an advisory lock file is not enforced by existing
writers.

## Decision 4 — Quarantine and restore transitions

**Decision**: the global quarantine tree mirrors the immutable SHA-256 fanout:
`quarantine/sha256/ab/cd/<60 hex>`. Batch ownership remains in SQLite. Every transition
checks same device, regular non-linked source, exact digest/length and absent
destination.

On POSIX, exclusive `link(..., follow_symlinks=False)` then source `unlink` creates a
recoverable two-link interval; on Windows, same-filesystem `rename` is used after all
handles close. Parent durability is synchronized where supported. Recovery classifies
source-only, destination-only, same-inode-both, independent-both or neither; only the
first three are replayable.

**Rejected**: `shutil.move` because it may silently copy across devices; `os.replace`
because it overwrites on POSIX; batch-derived paths because path presence must not
encode ownership.

## Decision 5 — Explicit irreversible commit

**Decision**: after the batch grace and hard 24-hour minimum, final preflight under the
maintenance fence records one exact action per entry: `DELETE` only when still
unreferenced, unheld and verified; `RESTORE_CONFLICT` when newly protected; unsafe or
ambiguous state fails before intent. The distinct irreversible acknowledgement is part
of durable intent before any unlink. Recovery may finish an already-authorized commit
but generic recovery can never create one.

**Rationale**: after one successful unlink the only truthful restart behavior is to
finish the exact persisted action set. There is no secure-erasure claim.

## Decision 6 — Consistent paired backup

**Decision**: backup first persists a non-destructive operation fence, then a
coordination connection obtains `BEGIN IMMEDIATE`. A second source connection uses
`sqlite3.Connection.backup()` to copy the catalog while the coordinating transaction
enumerates the exact active/recoverable roots. Immutable files are streamed with
`lstat → open → fstat → read → fstat`, hash and length checks.

Every low-level Windows descriptor includes `O_BINARY`; the Python 3.12 documentation
explicitly requires that flag for binary-mode `os.open()` and without it CRT text
translation can make read bytes disagree with physical file length. The same open
descriptor is additionally replayed and its exact bytes/hash and length must agree
before publication, while device/inode identity remains fail-closed. See
[Python `os.open`](https://docs.python.org/3.12/library/os.html#os.open).
Python implements Windows `os.fsync()` with the Microsoft CRT `_commit()` operation.
Operation-owned staged files are therefore opened read/write for their explicit durable
flush; source and verification descriptors remain read-only. See
[Python `os.fsync`](https://docs.python.org/3.12/library/os.html#os.fsync) and
[Microsoft `_commit`](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/commit?view=msvc-170).

The staged backup catalog removes the ephemeral operation fence and disposable lexical
index rows, while retaining authoritative and quarantine/hold facts. The manifest is
written last and includes only sorted relative POSIX paths, file types, lengths,
hashes, migration checksums, root sets and closed exclusions. Complete verification
precedes a sibling no-overwrite rename.

**Rationale**: the SQLite online backup API yields a consistent DB snapshot. The writer
reservation permits its second reader while blocking new roots. Calling backup on the
same connection that owns a transaction can block; raw file copy can separate a live
database from its journal.

**Rejected**: `copy2` of the live catalog; `VACUUM INTO`; changing journal mode to WAL;
`BEGIN EXCLUSIVE` before the required backup reader.

## Decision 7 — Fresh manifest-driven restore

**Decision**: fully validate manifest version/canonical bytes, paths, limits, hashes,
catalog history and source topology before creating output. Require an absent disjoint
target whose parent exists. Copy allowlisted regular files into unique sibling staging,
verify the complete catalog/object set, synchronize, close handles and atomically
rename. Restore never edits the backup and never migrates the restored revision.

**Rationale**: fresh publication makes failure visibility unambiguous and enables a
real A→B→A drill. In-place downgrade could merge incompatible B facts into A.

## Decision 8 — Validate-only open and explicit migration

**Decision**: split workspace behavior:

- `initialize`: new workspace or idempotent current only, never upgrade;
- `open`: validate marker/layout/catalog through read-only adapters only;
- `migrate`: exact supported old revision, verified paired backup, then the complete
  pending checksummed chain in one transaction.

Read-only SQLite uses URI `mode=ro`, connection-local `query_only`/security settings and
never persistent `journal_mode`. CAS validation creates no directories. Newer, gapped,
drifted, malformed or hot auxiliary state rejects byte- and timestamp-unchanged.

Migration uses a writer reservation compatible with the pre-upgrade backup reader; DDL
acquires stronger locks as needed. ADR 0014 refines ADR 0002's earlier standalone
`BEGIN EXCLUSIVE` choice.

## Decision 9 — Local filesystem and capacity boundary

**Decision**: support only fresh disjoint local paths, reject recognizable UNC/device
paths, links/junctions, hardlinks, overlap and cross-device publication. POSIX remote
mounts cannot be recognized portably and remain documented unsupported. Every file
copy is bounded and constant-memory; owned staging is the only cleanup target.

`shutil.disk_usage(path).free` supplies capacity. A maintenance write starts only when
`free >= known_required + reserve`; reserve-exact succeeds and reserve-minus-one fails.
Long copies recheck capacity and `ENOSPC` never triggers reclamation.

## Decision 10 — Disposable lexical index replacement

**Decision**: enumerate and verify all authoritative prepared evidence first. One
SQLite transaction replaces every mapping/FTS row only after the corpus is complete;
any failure rolls back to the prior index. Evidence/CAS identities never change.

**Rationale**: scope-at-a-time rebuild can expose a mixed old/new global index and does
not prove orphan removal.

## Decision 11 — Audit, privacy and fault evidence

**Decision**: reports/events contain stable categories, opaque identifiers, counts,
bytes and UTC times only. They exclude paths, filenames, content, queries, tokens, raw
SQL and provider exception strings. Fault hooks bracket intent, each filesystem entry,
manifest publication, each migration statement and final commit. Subprocess
`os._exit()` tests exercise real journal/staging residue; twenty-way races verify one
terminal outcome.

## Known limitations

- Remote/shared filesystems are unsupported; local semantics are tested only on
  Linux, macOS and Windows CI filesystems.
- Backup is an internal recovery artifact and has no portable interchange guarantee.
- Operator commit is logical removal, not secure erasure.
- v0.1 intentionally cannot reclaim catalog-referenced historical objects.
