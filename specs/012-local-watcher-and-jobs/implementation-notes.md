# Implementation Notes: F012 Local Watcher and Stable Jobs

## Acceptance-criteria reconciliation

1. Admit one explicit canonical local directory, never implicit authority.
2. Reconcile complete bounded scans; observation metadata is a scheduling hint only.
3. Require persistent stability before one canonical deduplicated ingestion job.
4. Reuse existing text/rich ingestion and exact SHA-256/CAS representation semantics.
5. Preserve delete/rename facts as watcher tombstones without deleting evidence.
6. Extend generic jobs with eligibility, deterministic retry and fenced cancellation.
7. Recover expired work and backpressure/rescan state after restart.
8. Expose only body/path/token-free events and foreground local CLI control.
9. Upgrade revision 8 atomically to revision 9 while freezing public schemas.
10. Prove fault, race, security, migration, packaging and three-platform quality.

## Baseline and rollback

- Rollback commit: `e852f7ce59a6fc491c9978b9f9f8b4eddd3344e5`
- Branch: `codex/f012-local-watcher-and-jobs`
- External v3.1 prompt SHA-256:
  `47e5a8357e669a51fd18ce4c77105697bd678f98f674d83658a4f8d09dcf2377`
- Rollback after workspace upgrade requires restoring a paired pre-revision-9 backup;
  never edit migration rows or persisted job state manually.

## Pre-implementation evidence

The read-only analysis covered 30 functional requirements, 10 measurable success
criteria and 82 tasks. Six initial findings were corrected at their originating
artifacts; the second pass reported zero unresolved findings.

The authoritative baseline ran after active-feature governance moved to F012 and before
any runtime source changed:

| Command | Result |
|---|---|
| `uv run ruff check .` | success |
| `uv run ruff format --check .` | success; 155 files |
| `uv run mypy src` | success; 56 source files |
| `uv run pytest` | success; 1,027 passed, 86.40% coverage |
| `uv build` | success; wheel and sdist |
| `uv run python scripts/generate_schemas.py --check` | success; all 12 schemas current |
| evidence conformance validator | success; 7 valid, 8 invalid, 1 record set, 6 vectors |
| repository validator | success |

## Implementation evidence

### Delivered architecture and requirement traceability

| Requirement group | Delivered evidence |
|---|---|
| FR-001–FR-005 | `LocalWatchScanner` requires an absolute lexically canonical, link-free, disjoint local root; counts every enumerated entry before bounded sorting; stays on one device; and returns either a complete deterministic scan or an empty incomplete result. Adapter, CLI and security tests cover relative/dot-segment aliases, symlinks, recognizable shares, overlap, device boundaries, directory races, disappearing entries, depth and overflow. |
| FR-006–FR-013 | Pure watcher models freeze metadata-only stability, JCS/SHA-256 identities and event shapes. One SQLite reconciliation transaction persists candidates, stability, exact job targets, backpressure, tombstones, unique rename hints and fresh reappearance jobs. Existing SHA-256 source ingestion remains authoritative. |
| FR-014–FR-019 | Workspace revision 9 adds `CANCELLED`, `available_at` and cancellation-request facts without changing migrations 1–8. Claims are eligibility ordered; queued/running cancellation is idempotent and revision fenced; retries are capped and deterministic; every cycle recovers expired leases, including cancellation-requested work. |
| FR-020–FR-023 | Per-root queue and total-enumeration bounds are durable. Root/reconciliation/job-outcome fault tests prove prior-or-complete transactions. Watch events expose closed opaque fields only; paths, names, bodies, tokens, owners and exception strings remain absent. |
| FR-024–FR-026 | `watch`, `jobs` and `job-cancel` use existing JSON/human envelopes. One-cycle and injected-sleeper continuous modes are foreground-only, stop on interruption, open no listener and add no MCP mutation. Existing text/rich services are selected only from trusted CLI configuration. |
| FR-027–FR-030 | All fixtures are synthetic, sockets are blocked for the full suite, migration/compatibility/security tests are cross-platform, prior public contracts and dependency files are byte-frozen, and operator/rollback limitations are documented without zero-loss claims. |

### Measurable success-criteria evidence

- SC-001/SC-002: 100 repeated plus 20 concurrent identical reconciliations converge
  to one job/target; the 1,999 ms/2,000 ms stability boundary produces zero/one job.
- SC-003: an exact 1,001-entry root against a 1,000-entry limit exposes no observation,
  tombstone or job; after removal to 1,000 entries the next scan schedules all 1,000.
  Unsupported entries also consume the enumeration limit.
- SC-004: attempts 1–5 persist the exact 1 s, 2 s, 4 s, 5 s capped schedule through
  exhaustion, while 100 pre-eligibility claims acquire no lease.
- SC-005: both queued and running 20-client cancellation races converge to one request
  and one terminal event; stale renew, complete and fail transitions are rejected.
- SC-006/SC-007: fresh catalog/service instances recover candidate, delayed queue,
  expired lease, backpressure/rescan and tombstone state. Rename, deletion and standalone
  reappearance preserve old jobs/targets and create a fresh locator lifecycle.
- SC-008: path, link, overlap, share, device, hostile-name, body and token tests reject
  authority expansion and find no private material in structured output.
- SC-009: populated revision 8 is preserved; failures injected before/after every one
  of migration 9's 27 statements expose exact revision 8 and permit a clean retry;
  twenty initializers converge to one revision-9 history row.
- SC-010: the local network-blocked gate passed 1,147 tests at 86.51% branch-aware
  coverage. Linux/macOS/Windows PR and post-merge evidence remains the publication gate.

### Task and convergence evidence

Phases 2–6 delivered generic job evolution, pure watcher contracts, safe scanning,
durable reconciliation, foreground orchestration and CLI control. Phase 7 froze prior
contracts and completed documentation/package checks. The first read-only convergence
pass found ten genuine gaps (canonical root admission, total enumeration bounds, exact
SC-003/004/005/006/007/009 proof, service source races, terminal-event fault atomicity
and retried-cancel event truth). Tasks T083–T092 corrected all ten and the focused F012
suite now passes 121 tests.

The second read-only pass checked the same 56 requirements/acceptance criteria, 23
plan decisions and 12 constitution articles and found zero remaining gap at every
severity. It left `tasks.md` byte-identical at SHA-256
`262d012ab7a36a5ae40a5f628000ca8ccb67dfe78952eec003b120d4cdaf6fcf`.

### Exact local commands and results

| Command | Result |
|---|---|
| `uv run ruff check .` | success |
| `uv run ruff format --check .` | success; 169 files |
| `uv run mypy src` | success; 60 source files |
| focused F012 `pytest --no-cov` invocation | success; 121 passed |
| `uv run pytest` | success; 1,148 passed, 86.51% coverage |
| `uv build` | success; wheel and source distribution |
| `uv run python scripts/generate_schemas.py --check` | success; all 12 schemas current |
| evidence conformance validator | success; 7 valid, 8 invalid, 1 record set, 6 vectors |
| repository validator / `git diff --check` | success |
| `uv run pre-commit run --all-files` | success; complete repeated gate |

The validated quickstart used
`/private/tmp/openardp-f012-quickstart-20260801-1`: revision-9 initialization, text
`watch --once`, body-free inspection and queued cancellation all succeeded. `/tmp` on
this macOS host is a symlink and was correctly rejected; `/private/tmp` was accepted.
A fresh isolated offline core-wheel probe at
`/private/tmp/openardp-f012-wheel-20260801-3` installed exactly seven packages with no
Docling dependency, imported the watcher adapter/service and completed revision-9 init,
watched text ingestion and body-free job inspection.

The first PR-head run `30682261668` exposed a Linux-only inode-reuse assumption in a
root-replacement test; retaining the renamed old root made the replacement identity
portable. The next run `30682726438` passed Ubuntu and macOS but exposed that Windows
sets `os.DirEntry.stat()` device and file identities to zero. The scanner now obtains
fresh no-follow `os.stat()` metadata for every authority and target check, and a
regression test forbids use of the cached directory-entry metadata. The corrected local
gate is the 1,148-test result above; final three-platform publication evidence remains
mandatory.

### Tradeoffs, residual risks and rollback

- Polling provides portable reconciliation truth but latency follows `poll_ms`; no
  zero-loss notification or throughput claim is made.
- Remote POSIX mounts cannot be identified portably. Recognizable UNC/device paths and
  cross-device traversal are rejected; other shared filesystems remain unsupported.
- Metadata is only debounce evidence. A target is revalidated immediately before the
  existing exact-byte ingestion boundary, which can still return a retryable race.
- Cancellation is cooperative and cannot preempt arbitrary native parser work or undo
  already committed immutable evidence.
- One process executes bounded jobs serially by default. SQLite fencing is correctness
  evidence, not a horizontal-throughput claim.
- Tombstones do not reclaim data. F013 owns dry-run reachability, quarantine, restore
  and physical collection.

To roll back, stop every foreground watcher and restore the complete paired revision-8
workspace/CAS backup while reverting to commit
`e852f7ce59a6fc491c9978b9f9f8b4eddd3344e5`. Older binaries must never open a live
revision-9 catalog, and migration rows, constraints, jobs or CAS objects must not be
edited manually.
