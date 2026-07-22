# Implementation Notes: Text Ingestion Vertical Slice

**Feature**: F004 / Work Package 3

**Branch**: `codex/f004-text-ingestion-slice`

**Status**: Implemented and locally converged; external PR and cross-platform CI pending

## Acceptance criteria restated before implementation

1. An explicit compatible local workspace initializes idempotently; other commands never initialize or repair it silently.
2. Only bounded regular UTF-8 TXT/Markdown sources are snapshotted read-only into CAS, and parsing consumes that verified
   immutable snapshot rather than rereading the path.
3. The built-in adapter deterministically emits source-backed hierarchy with exact line provenance and untrusted-data labels.
4. A complete F002 manifest, native source object and every canonical block object become READY atomically through a
   checksummed revision-3 catalog transaction.
5. A fenced representation claim prevents simultaneous duplicate parser ownership; stale owners cannot commit after expiry.
6. A verified unchanged source/recipe records a cache hit and invokes the parser zero times; changed bytes create a new
   immutable version; A → B → A advances the head correctly without rewriting history.
7. `list`, `status`, `outline` and `get` operate from exact persisted evidence, minimize bodies progressively and never mix
   versions or fall back to live source bytes.
8. Human and stable JSON forms of all six commands, security boundaries and persisted behavior pass deterministic offline
   tests and the complete Linux/macOS/Windows repository gates.

## Binding decisions

- No new runtime dependency: stdlib incremental UTF-8 parser, killable spawned-worker isolation and `argparse` CLI.
- TXT/Markdown source object is also the lossless parser-native artifact.
- F004 block handles use the reviewed SHA-256-derived UUIDv8 algorithm; canonical block content remains ADR-0006 SHA-256.
- Revision 3 adds representation, block, current-head and append-only ingestion-event tables only.
- READY candidates require full CAS and semantic verification before reuse.
- Source/version facts remain immutable; current observations belong to the document head/event projection.
- F004 READY has zero required indexes because F005 is not installed.
- No search, Docling, reconciliation, watcher, MCP, provider or export behavior enters F004.

## Test-first record

| Phase | Initial failure evidence | Passing evidence |
|---|---|---|
| Setup boundary | 7 expected failures: five absent module surfaces and two missing console-entry contracts | 31 package/repository boundary tests passed; `uv lock --check` confirmed no lock-content change |
| Domain and ports | 2 expected collection errors for absent ingestion domain and parser-port contracts | 23 focused domain/port tests passed; package/repository boundaries passed independently; Ruff and strict mypy passed |
| TXT/Markdown parser | Missing pure and isolated adapters were proven through the new parser cases before implementation | 28 focused parser/port tests passed; spawned timeout/crash cleanup, worker socket denial, strict streaming UTF-8, limits and the reviewed Markdown subset passed with Ruff and strict mypy |
| Workspace/source safety | 3 expected collection failures for the absent source/workspace adapters | 17 focused integration/security tests passed; exact CAS bytes, non-publishing inspection, explicit atomic workspace initialization, no-follow path checks, special-file rejection, race failure and source immutability passed with Ruff and strict mypy |
| Representation/catalog/cache | New migration/catalog/service cases initially exposed the absent revision-3 tables and lifecycle methods | 52 focused migration/catalog/reachability/service tests passed; migration upgrade, lease fencing, six transactional fault points, canonical block/manifest publication, 20 sequential and 8 concurrent cache hits, A → B → A, force, retry and corruption behavior passed with Ruff and strict mypy |
| Document navigation | Query tests initially failed against the empty navigation service | 5 focused query integration tests passed; deterministic body-free listing, zero-parser freshness, source removal, historical outline, progressive structural-only CAS reads and exact current-block retrieval passed with Ruff and strict mypy |
| CLI | Installed command tests initially failed against the placeholder entry point | 34 CLI/package/repository tests passed; all six commands, explicit workspace behavior, stable one-line JSON, body minimization, control-text escaping and exit classifications passed with Ruff and strict mypy |
| Convergence hardening | The first audit found missing installed-entry human coverage and an empty-blockquote validation failure | 36 focused parser/CLI tests passed after T084–T085; all six installed commands now pass in JSON and human mode, and empty quotes return one bounded warning without a block |

## Pre-implementation Spec Kit analysis

- intent inventory: 26 functional requirements, 8 measurable success criteria and 19 acceptance scenarios;
- task inventory: 83 dependency-ordered tasks across setup, four user stories, CLI, documentation, convergence and
  publication;
- requirements and success-criteria coverage: 100 percent mapped to explicit test/implementation tasks;
- constitution and architecture review: all 10 articles and relevant accepted ADR decisions checked;
- initial finding: one high-severity parser-isolation gap and one medium-clarity source-atime overclaim;
- originating-artifact corrections: FR-007 plus research/plan/contract/tasks now require the default killable spawned worker;
  FR-006 now precisely excludes access time while preserving bytes, size, modification time and mode;
- final rerun: 0 critical, 0 high, 0 medium and 0 low unresolved findings; 0 unrequested later-feature behaviors.

Implementation is unblocked.

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

Observed on macOS with Python 3.12.13 and SQLite 3.50.4:

- focused parser/port tests: 32 passed after empty-blockquote hardening;
- focused installed CLI/package/repository tests: 35 passed;
- focused workspace/source security tests: 17 passed;
- focused migration/catalog/reachability/service tests: 52 passed;
- focused navigation tests: 5 passed;
- `uv run ruff check .`: passed;
- `uv run ruff format --check .`: 59 files already formatted;
- `uv run mypy src`: passed for 30 source files;
- `uv run mypy src --platform win32`: passed for 30 source files (added after the first Windows CI mypy stop);
- `uv run pytest`: 389 passed in 14.20 seconds with 87.20 percent branch-aware coverage and network disabled;
- `uv run --locked pre-commit run --all-files`: all four authoritative hooks passed on the final converged tree;
- `uv build`: built `openardp-0.0.1.tar.gz` and `openardp-0.0.1-py3-none-any.whl`;
- two consecutive `uv run --locked python scripts/generate_schemas.py --check` runs reported all five public schemas
  current;
- `uv run --locked python scripts/validate_repository.py`: passed with zero diagnostics;
- `git diff --check`: passed;
- tracked-file drift review: build outputs remained ignored and no local/cache/OS artifact entered the candidate diff;
- contract boundary: `schemas/`, `uv.lock`, accepted identity algorithms and F005+ modules/commands remained unchanged;
  `pyproject.toml` adds only the reviewed `openardp` console entry and the runtime dependency set is unchanged.

The host continues to emit the documented non-fatal uv centralized-environment `.venv` discovery-link warning; every uv
command resolves the centralized environment and exits successfully.

Tradeoffs and residual boundaries:

- the parser deliberately implements the documented TXT/Markdown subset rather than claiming CommonMark compatibility;
- the spawned parser has a wall deadline and portable data limits; POSIX additionally applies CPU, descriptor and address
  space limits, while Windows relies on the portable bounds and forced process termination;
- no-follow/component checks target normal local filesystems; shared/network filesystems and a malicious same-user process
  racing path components remain explicitly unsupported;
- a failed cross-resource operation can leave only complete unreferenced CAS objects, which read-only reachability reports;
  automatic deletion remains out of scope;
- search, rich-document parsing, cross-version reconciliation, watchers, MCP/HTTP and export remain F005+ work.

## Post-PR CAS publication hardening

The first pull request matrix stopped the macOS job inside the F003 concurrent duplicate-write test and exposed a real
publication race: two legitimate writers of identical bytes could `os.replace` the same destination inode while a
concurrent `verify` held it open, failing spuriously. Publication is now platform-split no-clobber: POSIX publishes with
`os.link` plus staging unlink and Windows with no-clobber `os.rename`; losers converge through verified reuse. The POSIX
transient second link (winner between link and unlink) is classified by a bounded settling re-check that requires an
observable staged twin inode and re-reads the destination before judging the link count unsafe, closing the observed
check-to-scan time-of-check/time-of-use gap. The twin scan reads complete identities explicitly because Windows
`DirEntry.stat` caches directory data without a file index. Verification itself still rejects any multi-link entry.

Focused evidence: one deterministic paused-winner interleaving regression, four settling classification contracts,
twenty consecutive concurrency repetitions before the re-check hardening reproduced the race once under parallel load
and eighty full-file repetitions after it passed; the complete local gate then passed on the final tree (389 tests,
87.20 percent coverage, native plus Windows-platform strict mypy). The F003 research Decision 2 amendment records the
mechanism change.

## Spec Kit convergence evidence

- intent inventory: 26 functional requirements, 8 measurable success criteria and 19 acceptance scenarios;
- technical decisions checked: 10;
- constitution articles checked: 10;
- first findings: 0 missing, 2 partial, 0 contradicting and 0 unrequested; severity was 0 critical, 1 high, 1 medium and
  0 low;
- appended remediation: T084 for installed-entry human/JSON coverage and T085 for deterministic empty Markdown quote
  handling;
- follow-up findings: 0 missing, 0 partial, 0 contradicting and 0 unrequested at every severity;
- the clean follow-up left `tasks.md` byte-for-byte unchanged at SHA-256
  `2071406145da4079317e9ae834387156bfef9679bf33b407173f47e2906eed6b` before the final T071–T079 status updates.

Result: the implementation satisfies the F004 specification, plan and expanded task inventory. External completion still
requires the focused PR-head, post-merge `main` and final evidence-commit matrices on Ubuntu, macOS and Windows.

## External validation evidence

Pending pull request, merge and post-merge cross-platform CI.
