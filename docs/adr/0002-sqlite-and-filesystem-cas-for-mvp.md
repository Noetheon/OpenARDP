# ADR 0002: SQLite catalog and filesystem CAS for the MVP

Status: Accepted

Date: 2026-07-22

## Decision

Use SQLite (including FTS5 in the later lexical-search feature) for metadata/search and a SHA-256 content-addressed
filesystem object store for original and large artifact bytes.

The local runtime commits across these two resources in a deliberate order:

1. stream exact bytes into same-root staging, compute SHA-256 and byte length, synchronize the staged file and publish it
   atomically into the immutable object tree;
2. verify every physical object referenced by the operation;
3. commit object metadata, one complete source-version fact and its entire reference set in one SQLite transaction.

Filesystem and SQLite commits are not a distributed transaction. A process failure between steps may leave a complete
unreferenced object, but it must never expose a catalog version whose required references are partial or unverified.
Read-only reachability analysis reports complete unreferenced objects and integrity inconsistencies; it does not delete.

The F003 catalog uses the rollback journal in `DELETE` mode with `synchronous=EXTRA`, foreign keys enabled,
`trusted_schema=OFF` and a bounded busy timeout. WAL is not the default while the locked Python runtime can bind SQLite
versions in the officially documented WAL-reset race range. A future WAL option requires a corrected runtime gate and
separate recovery evidence.

F003 persists committed source-version facts only. A complete `READY` document representation still requires validated
parser artifacts, normalized blocks and required indexes in later ingestion/search features.

## Rationale

Local-first, portable, transactional, low operational overhead and sufficient for the target benchmark. It avoids forcing
Docker, PostgreSQL or a vector database on initial users.

Same-root temporary publication ensures canonical object paths never expose partially written bytes. SQLite transactions
then provide all-or-nothing logical visibility. Keeping the resources explicit makes crash behavior honest and permits
safe inspection of the only expected cross-resource residue: a complete object with no committed reference.

## Consequences

- Single-node write scaling only.
- Enterprise migration requires ports and data migration tooling.
- Keep SQL/catalog concerns behind interfaces.
- Managed storage roots must be local and app-owned; F003 does not claim correctness on shared/network filesystems or
  against an actively malicious same-user process rewriting the root.
- File and directory synchronization provide the strongest practical local durability available through the supported
  Python/OS surface, not a universal guarantee against hardware failure or ignored flushes.
- Catalog migrations are ordered, checksummed and transactional. Newer or drifted histories fail without mutation.
- Historical source-version and job references remain conservative reachability roots until a later retention policy is
  explicitly designed.
