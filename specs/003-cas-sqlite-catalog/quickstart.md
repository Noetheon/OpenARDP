# Quickstart Validation: Content-Addressed Storage and SQLite Catalog

This guide validates the finished F003 library slice. It intentionally uses temporary local data and does not invoke a parser, network service or product CLI.

## Prerequisites

```bash
uv sync --all-extras --locked
```

Expected: synchronization succeeds without changing `pyproject.toml` or `uv.lock`.

## 1. Object-store contract

Run the focused CAS tests:

```bash
uv run --locked pytest tests/integration/test_filesystem_cas.py tests/security/test_storage_boundaries.py --no-cov
```

Expected evidence:

- exact SHA-256 identity and byte-for-byte reads;
- bounded chunked I/O, including empty content;
- at least 32 concurrent duplicate writes converge;
- interruptions do not publish a partial object;
- malformed identities, links, traversal forms and corrupt leaves fail without touching an outside sentinel;
- inventory reports staging residue and malformed entries without deletion.

## 2. Migration and catalog contract

```bash
uv run --locked pytest tests/integration/test_sqlite_catalog.py --no-cov
```

Expected evidence:

- fresh catalog reaches revision 2;
- repeated initialization makes no logical change;
- a revision-1 catalog upgrades to revision 2;
- an injected migration failure leaves the prior schema/data state intact;
- a newer catalog is rejected without mutation;
- foreign keys, exact source keys and parameterized hostile strings behave safely;
- independent readers never see a partial source-version reference set.

The diagnostics assertions confirm that WAL is not enabled; final implementation notes record the actual Python SQLite
runtime observed during convergence.

## 3. Persistence and recovery contract

```bash
uv run --locked pytest tests/integration/test_persistence.py --no-cov
```

Expected evidence:

- repeated source-key registration returns one UUIDv7 document;
- exact bytes may belong to more than one logical document;
- a lost-response source-version retry is idempotent;
- a catalog failure after CAS publication leaves one complete unreferenced object and no visible partial version;
- every extra reference is physically verified before catalog commit.

The catalog command in section 2 also proves that job claim, renewal, completion, retryable/terminal failure,
lease-expiry recovery and reopen behavior enforce owner/token/revision fencing and bounded attempts.

## 4. Read-only reachability contract

```bash
uv run --locked pytest tests/integration/test_reachability.py --no-cov
```

Expected evidence:

- every historical version and job reference remains reachable;
- deliberate complete orphans are candidates;
- missing, corrupt, malformed and staging entries are inconsistencies;
- byte-tree and catalog snapshots are unchanged after analysis;
- no object or record is deleted.

## 5. Full repository gate

Run the required commands exactly:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Then verify the broader repository contract:

```bash
uv run --locked pre-commit run --all-files
uv build
git diff --check
```

Expected: every command exits zero, the offline test suite satisfies the branch-coverage gate, and no validation command modifies tracked files.

## Interpreting durability evidence

These tests prove process-crash atomic visibility and best-effort synchronization on the CI filesystems. They do not claim universal survival of sudden power loss, defective hardware, ignored flush requests, network filesystems or an actively hostile same-user process that can rewrite the managed root.

## Out-of-scope confirmation

The finished tree must still contain no F004+ parser/normalizer/ingestion CLI, no FTS index, no automatic garbage deletion, no cloud storage dependency and no changed F002 public schema.
