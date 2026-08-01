# ADR 0014: Journal explicit local maintenance and require paired recovery

Status: Accepted for Feature 013

Date: 2026-08-01

## Context

OpenARDP writes immutable objects before catalog facts, retains every historical
reference and treats indexes as disposable. Long-running workspaces therefore need
bounded storage explanation, reversible quarantine, explicit reclamation and practiced
recovery. SQLite transactions cannot atomically move or remove filesystem objects, and
filesystem presence cannot distinguish an authorized interrupted operation from
external corruption.

The prior catalog ADR selected `BEGIN EXCLUSIVE` for a standalone migration. F013 also
requires a consistent pre-upgrade catalog backup through SQLite's online backup API,
which uses a second reader and therefore cannot run behind an exclusive read-blocking
lock in rollback-journal mode.

## Decision

### Keep ordinary object storage non-destructive

The released `ObjectStore` port remains immutable and has no delete or move method.
F013 adds a dedicated internal maintenance port and one local filesystem adapter. Only
the explicit trusted CLI composition root receives that authority; document content,
parsers, query services, watchers and MCP do not.

### Persist complete operation intent before filesystem mutation

SQLite revision 10 records retention holds, quarantine batches, exact ordered
maintenance operations/entries and body-free audit events. A partial unique index
permits one active maintenance operation. Normal writes fail while intent requires
recovery; the fence has no expiring lease.

Quarantine, restore and commit first revalidate inputs and persist the complete action
set in one transaction. Only then may the filesystem adapter act. Final catalog state
is published after exact outcome verification. Recovery replays only this durable
intent. Filesystem names or locations alone never grant deletion authority.

An irreversible commit stores the distinct acknowledgement and final DELETE versus
RESTORE_CONFLICT action for every entry before the first unlink. After that boundary,
recovery completes the already-authorized action set forward. Generic recovery cannot
create commit intent, and no automatic path invokes commit.

### Use same-filesystem, no-overwrite transitions

The canonical quarantine tree mirrors SHA-256 fanout and does not encode batch
authority. Linux/macOS use exclusive hard-link then unlink with directory durability;
Windows uses same-device rename after handles close. Links, junctions, external
hardlinks, independent duplicates, cross-device paths and ambiguous state fail closed.
Remote/shared filesystems remain unsupported.

### Pair backup and migration under a writer reservation

Backup persists a non-destructive maintenance fence, obtains a SQLite
`BEGIN IMMEDIATE` writer reservation, and calls `Connection.backup()` on a second
source connection. This blocks new catalog roots while allowing the backup reader. The
coordinating transaction enumerates exact reachable/recoverable objects, which are
streamed and verified into fresh sibling staging. The manifest is written last and the
backup becomes visible only after full verification.

The backup copy removes the ephemeral operation fence and disposable lexical index but
retains authoritative, hold and quarantine facts. Restore is manifest-driven and only
publishes to a fresh disjoint location. It does not migrate the restored revision.

Existing workspaces never migrate during open or initialization. Explicit migration
requires the verified paired backup and applies the complete pending chain in one
transaction. This refines ADR 0002's exclusive lock to a writer reservation compatible
with the required second backup reader; the durability and atomic-migration intent of
ADR 0002 remains unchanged.

## Compatibility

- Workspace revision advances additively from 9 to 10.
- Migrations 1–9 and their checksums remain immutable.
- Existing public schemas, identity vectors, MCP descriptors, dependencies, parser/
  provider profiles and export-profile decisions remain unchanged.
- Older applications reject revision 10. Rollback is verified revision-9 backup
  restoration to a fresh location, never schema-history editing.
- Backup format is an internal recovery artifact and makes no F014 interchange claim.

## Consequences

- A crash can leave a write-fenced workspace requiring explicit recovery, but cannot
  silently convert unexplained bytes into deletion authority.
- Backups block catalog writers while copying potentially large immutable objects;
  readers remain available. This favors coherent recovery evidence over write latency.
- v0.1 may reclaim only verified unreferenced objects and intentionally retains every
  catalog-referenced historical object.
- Operator commit is logical removal, not secure erasure.

## Alternatives considered

- Add delete to `ObjectStore`: rejected because it spreads destructive authority.
- Infer recovery from quarantine filenames: rejected because external mutation could
  be mistaken for authorization.
- Use advisory lock files only: rejected because existing writers do not enforce them
  and crash ownership is ambiguous.
- Copy the live SQLite file: rejected because database and rollback journal can diverge.
- Use `BEGIN EXCLUSIVE` before online backup: rejected because it blocks the required
  second reader.
- Convert to WAL or replace SQLite/CAS: rejected as unnecessary storage-contract
  changes requiring a separate ADR.
