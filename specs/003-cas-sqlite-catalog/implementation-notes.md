# Implementation Notes: Content-Addressed Storage and SQLite Catalog

**Feature**: F003 / Work Package 2

**Branch**: `codex/f003-cas-sqlite-catalog`

**Status**: Local implementation and quality gates complete; external PR/CI evidence pending

## Acceptance criteria restated before implementation

1. Exact object bytes are addressed by SHA-256, published atomically, immutable through the public API, streamable and
   fully verifiable.
2. At least 32 concurrent duplicate writes converge on one valid visible object; interrupted writes never expose a
   partial canonical leaf.
3. Malformed identities, traversal strings, links/junctions and malformed object-tree entries never authorize access
   outside the configured local root.
4. Stable logical documents and exact source versions are idempotent. A source version and its complete reference set are
   either wholly visible or wholly absent to an independent reader.
5. Fresh, repeated and revision-1 catalog opens reach revision 2 through ordered checksummed transactions; failed or
   newer migrations leave the existing catalog unchanged.
6. Job create/claim/renew/complete/fail/recover transitions are fenced by owner, token hash, revision and exact expiry,
   append sanitized events, obey bounded attempts and survive reopen.
7. Reachability deterministically distinguishes live objects, complete unreferenced candidates and integrity/layout
   inconsistencies and performs no deletion or mutation.
8. All behavior is proven with synthetic offline tests and the full Ruff, formatting, strict-mypy, pytest/coverage,
   pre-commit, build and Linux/macOS/Windows CI gates.

## Binding decisions

- ADR 0002 is accepted before code.
- CAS publication precedes the SQLite transaction; cross-resource failure leaves at most a complete orphan.
- F003 commits source-version facts, not a complete F002 `READY` representation.
- SQLite uses `DELETE` plus `synchronous=EXTRA`; WAL is excluded for the observed SQLite 3.50.4 runtime.
- Migrations are static, checksummed and executed statement-by-statement in one exclusive pending-chain transaction.
- Job leases use caller-generated raw tokens while the catalog persists only SHA-256 token hashes.
- All historical version and job references are live roots; automatic garbage deletion is out of scope.
- No new runtime dependency, parser, product CLI, FTS index, cloud adapter or public-schema revision enters F003.

## Test-first record

Each task phase records its initial expected failure and its passing focused command here as implementation proceeds.

| Phase | Initial failure evidence | Passing evidence |
|---|---|---|
| Setup boundary | `tests/test_package.py`: four expected missing F003 module-surface failures; dependency contract stayed green | 29 package/repository boundary tests passed after implementation |
| Foundation | Two expected collection errors for absent `domain.storage` and persistence ports | 22 focused tests passed; focused Ruff passed and strict mypy passed |
| US1 filesystem CAS | Two expected collection errors for absent `FilesystemObjectStore` | 28 focused CAS/security tests passed, including 32 threads and spawn processes; focused Ruff and strict mypy passed |
| US2 source-version commit | Two expected collection errors for absent SQLite catalog and persistence service | 23 catalog plus 5 cross-resource persistence tests passed; SQL-hostile/sensitive-value security cases passed |
| US3 migrations/jobs/recovery | The absent SQLite adapter blocked migration/job collection before implementation | Included in the 23 catalog tests: v1-to-v2/all-pending rollback, drift, corruption, fencing, events and process restart passed |
| US4 reachability | One expected collection error for absent `ReachabilityService` | 5 focused reachability tests passed, including byte-for-byte no-mutation and snapshot/publish race semantics |
| Convergence hardening | 6 expected failures exposed retry, timestamp, record, token-check and exception-redaction gaps | 94 combined F003 domain/contract/integration/security tests passed after T063-T066 |

## Required final commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run --locked pre-commit run --all-files
uv build
git diff --check
```

## Local validation evidence

Observed runtime and catalog profile on macOS:

```text
Python 3.12.13
SQLite 3.50.4
schema_version=2
journal_mode=delete
synchronous=3 (EXTRA)
foreign_keys=1
trusted_schema=0
quick_check=ok
```

Focused acceptance evidence:

- storage domain plus port contracts: 25 passed;
- filesystem CAS plus security boundaries: 32 passed;
- SQLite catalog: 27 passed;
- cross-resource persistence: 5 passed;
- read-only reachability: 5 passed;
- package/repository scope boundaries: 29 passed.

Repository-wide evidence:

- `uv run ruff check .`: passed;
- `uv run ruff format --check .`: 40 files already formatted;
- `uv run mypy src`: passed for 21 source files;
- `uv run pytest`: 284 passed, 91.51% branch coverage, network disabled;
- `uv run --locked pre-commit run --all-files`: all four hooks passed;
- `uv build`: built `openardp-0.0.1.tar.gz` and `openardp-0.0.1-py3-none-any.whl`;
- `git diff --check`: passed;
- tracked-file drift check: validation added no unexpected source changes; build output remained ignored;
- dependency/schema boundary: `pyproject.toml`, `uv.lock`, `schemas/` and `interfaces/` remained unchanged.

The host continues to emit the already documented non-fatal uv `.venv` discovery-link warning; uv resolves and executes
the centralized environment successfully.

The first convergence audit appended T063-T066 for four partial gaps. They are complete: source-version/job references
compare canonically, `source_modified_at` conflicts while first-success `committed_at` is retained, mutating job time cannot
move backward, event/inventory/recovery records enforce deterministic shapes, raw wrapped causes are suppressed from
public CAS tracebacks and every durable transition token hash has canonical SHA-256 syntax.

## Spec Kit convergence evidence

- final intent inventory: 22 functional requirements, 8 measurable success criteria and 17 acceptance scenarios;
- plan decisions checked: 12;
- constitution articles checked: 10;
- final findings: 0 missing, 0 partial, 0 contradicting and 0 unrequested;
- final severity counts: 0 critical, 0 high, 0 medium and 0 low;
- convergence left `tasks.md` byte-for-byte unchanged at SHA-256
  `915dc8248a78a0f7d96275d481c2ea6591fbdcdbd611cd84bd5da20602277936` before the final T062 status update.

Result: local implementation satisfies the F003 specification, plan and task inventory. External cross-platform evidence
remains the only pending completion boundary.

## External validation evidence

- Pull request: Pending
- PR-head workflow: Pending
- Linux: Pending
- macOS: Pending
- Windows: Pending
- Merge commit: Pending
- Post-merge `main` workflow: Pending

F003 is not complete until local convergence, green PR-head cross-platform CI, merge and green post-merge `main` CI are
all recorded.
