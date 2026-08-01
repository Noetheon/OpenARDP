# Implementation Plan: Local Watcher and Stable Jobs

**Branch**: `codex/f012-local-watcher-and-jobs` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/012-local-watcher-and-jobs/spec.md`

## Summary

Add an explicit foreground watcher that reconciles bounded, deterministic local scans
into durable path observations and stable ingestion jobs. Extend the existing generic
SQLite job state machine with eligibility, fenced cooperative cancellation and delayed
retry; persist watch roots, observations, exact job targets and redacted events in
workspace revision 9. Reuse the existing local-source and text/rich ingestion services,
with no daemon, network, native watcher dependency or MCP mutation.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: stdlib, Pydantic v2, RFC 8785 helper already locked
**Storage**: existing filesystem CAS and SQLite catalog, additive revision 9
**Testing**: pytest with network disabled, injected clocks/sleepers, synthetic roots
**Target Platforms**: Linux, macOS, Windows
**Project Type**: installable Python library and CLI
**Performance Goals**: bounded scan and active queue; deterministic one-job convergence
**Constraints**: original files read-only, no link traversal, no raw paths in events,
no implicit workspace/root discovery, no daemon/cloud/native-provider default
**Scale/Scope**: configurable default 10,000 files/root, depth 32, 1,000 active jobs,
one foreground worker per process and one explicitly selected root per invocation

## Constitution Check

### Before design

| Article | Gate | Result |
|---|---|---|
| I Evidence fidelity | Metadata schedules only; exact ingestion bytes remain authoritative | PASS |
| II Deterministic identity | Root/config, observation and job keys use versioned JCS/SHA-256 | PASS |
| III Provider neutrality | Scanner and ingestion runner are narrow ports/services | PASS |
| IV Progressive disclosure | CLI/events expose body-free handles/counts first | PASS |
| V Local-first privacy | Foreground local polling, no egress, paths redacted from events | PASS |
| VI Untrusted content | Names/bodies cannot grant roots, profiles or tool authority | PASS |
| VII Reproducibility | Persistent config, retry instants, observations and transitions | PASS |
| VIII Security bounds | Root, device, depth, entry, queue, retry and lease bounds | PASS |
| IX Contract evolution | ADR 0013 and revision-9 migration; prior public schemas frozen | PASS |
| X Small coherent change | Only F012 watcher/jobs; F013+ explicitly excluded | PASS |
| XI Verifiable claims | Injected time, fault, concurrency and three-platform evidence | PASS |
| XII Operability | Inspect/cancel/recover plus backup and rollback guidance | PASS |

### After design

- Domain models remain pure; filesystem and SQLite live in adapters.
- `WatchScanner` and `IngestionRunner` ports avoid provider-specific service logic.
- Migration 9 intentionally rebuilds the three revision-2 job tables inside one
  transaction to extend released CHECK constraints, then adds watcher tables. ADR 0013
  records the compatibility and rollback implications.
- No public interchange schema changes. Internal runtime models do not become public
  roots accidentally.
- Polling avoids a dependency and makes rescan truth portable. This is not a claim that
  operating-system event delivery is unnecessary for every future scale.
- All gates remain PASS; implementation may begin only after `analysis.md` reports no
  unresolved critical or high finding.

## Project Structure

### Feature documentation

```text
specs/012-local-watcher-and-jobs/
├── analysis.md
├── checklists/
│   ├── requirements.md
│   └── watcher-jobs.md
├── contracts/
│   └── internal-service-contract.md
├── data-model.md
├── implementation-notes.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Source and tests

```text
src/openardp/
├── adapters/
│   ├── local_watch.py
│   ├── sqlite_catalog.py
│   └── sqlite_migrations.py
├── domain/
│   ├── storage.py
│   └── watcher.py
├── ports/
│   ├── catalog.py
│   └── watcher.py
├── services/
│   └── watcher.py
└── interfaces/
    └── cli.py

tests/
├── contract/test_watcher_ports.py
├── domain/test_jobs.py
├── domain/test_watcher.py
├── integration/test_f012_migration.py
├── integration/test_job_cancellation.py
├── integration/test_local_watch.py
├── integration/test_watcher_catalog.py
├── integration/test_watcher_cli.py
├── integration/test_watcher_service.py
└── security/test_watcher_boundaries.py
```

## Phase 0 — Research and contract closure

1. Freeze exact polling/reconciliation, path, stability and identity semantics.
2. Freeze generic job state evolution, cancellation races, retry eligibility and lease
   recovery transitions.
3. Specify the revision-9 table rebuild and watcher tables, including populated
   revision-8 upgrade and every failure boundary.
4. Confirm existing text/rich ingestion composition can be reused without importing
   adapters into the watcher service.
5. Freeze CLI commands, redaction taxonomy and continuous/one-cycle behavior.

## Phase 1 — Pure job and watcher domain

1. Extend `JobState`, `Job`, `JobEvent` and `RecoveryResult` with eligibility and
   cancellation invariants while keeping existing construction compatible.
2. Add bounded watcher configuration, root identity, relative locator, metadata
   fingerprint, observation, target, event and cycle-result models.
3. Add domain-separated identities/golden vectors and deterministic retry calculation.
4. Define narrow scanner and ingestion-runner protocols plus sanitized exceptions.

## Phase 2 — Migration and catalog transactions

1. Add revision 9 by copying revision-2 job facts into replacement STRICT tables with
   expanded checks, restoring references/events, validating counts, then atomically
   swapping within the migration transaction.
2. Add watch roots, observations, targets and events with restrictive relationships,
   row fingerprints, opaque digests and deterministic indexes.
3. Implement eligibility-aware claim, cancellation request/acknowledgement and
   cancellation-aware expired-lease recovery with compare-and-set fencing.
4. Implement one transactional complete-scan reconciliation that performs no mutation
   from an incomplete scan and atomically creates watcher targets with generic jobs
   under the queue bound.
5. Include watcher targets and existing references in object-root/repository structural
   validation as appropriate; watcher rows themselves contain no CAS body.

## Phase 3 — Safe polling and scheduling service

1. Implement explicit root admission and deterministic stdlib scanning without link,
   device or workspace-boundary traversal.
2. Revalidate root identity before/after enumeration and classify overflow/incomplete
   outcomes without returning authoritative partial entries.
3. Orchestrate recovery, scan, reconciliation and at most the configured number of
   eligible foreground jobs per cycle.
4. Reconstruct targets safely, reject stale observation facts, invoke existing
   ingestion runners, classify failures and persist deterministic retry instants.
5. Add cooperative cancellation checks before snapshot/parse/commit boundaries where
   existing ingestion services can expose them without changing result identity.

## Phase 4 — CLI, documentation and convergence

1. Add `watch`, `jobs` and `job-cancel` with stable JSON/human summaries. Continuous
   `watch` loops only after successful root registration and stops cleanly on interrupt.
2. Update architecture, data model, security, operations, compatibility, roadmap,
   README, start guide, changelog and validation docs.
3. Validate quickstart on a fresh workspace with a disjoint synthetic root.
4. Run focused, full and package gates; assess contract freeze and dependency lock.
5. Converge spec/plan/tasks against delivered evidence and append tasks for any real
   gap before feature completion.

## Complexity Tracking

| Decision | Why needed | Simpler alternative rejected |
|---|---|---|
| Rebuild released job tables in migration 9 | SQLite cannot alter CHECK constraints for `CANCELLED`; truthful state must be persisted | Mapping cancellation to `FAILED` falsifies lifecycle semantics |
| Persist watch observations | Stability, deletion and crash recovery span processes | Memory-only debounce loses correctness on restart |
| Persist exact job targets separately | Generic jobs intentionally contain no path payload | Encoding paths in dedup/event fields leaks and weakens validation |
| Polling plus complete rescan | Cross-platform deterministic truth with no dependency | Native events alone can overflow or miss changes |

## Quality Gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/validate_evidence_contracts.py \
  conformance/evidence/v0.1.0/manifest.json
uv run python scripts/validate_repository.py
```

The final PR and post-merge `main` run must pass Linux, macOS and Windows before F013
begins.
