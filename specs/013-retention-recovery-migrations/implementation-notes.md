# Implementation Notes: F013 Retention, Recovery and Migrations

## Acceptance criteria restatement

F013 is complete only when one local workspace can explain all F012 reachability roots,
create a deterministic non-mutating retention plan, quarantine and restore exact
unreferenced objects through restart-persistent intent, irreversibly commit only after
grace and separate acknowledgement, create/verify paired backups, restore only to a
fresh location, explicitly migrate revision 9 to 10 after backup, report exact storage
capacity, and globally rebuild disposable lexical indexes without changing evidence.

Normal open, unsupported-newer input, low space, startup, watchers, ingestion, MCP and
generic recovery must never create destructive authority. Existing public schemas,
provider profiles, MCP contracts, dependencies and source identities remain unchanged.

## Commands required

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

## Evidence log

- 2026-08-01: specification checklist 16/16 and retention/recovery checklist 25/25.
- 2026-08-01: cross-artifact analysis covered 55/55 requirement criteria and formatted
  56/56 tasks; zero critical, high or medium findings after one task-path correction.
- 2026-08-01: foundational focused gate passed: 43 tests covering F013 domain/port/
  migration plus the frozen F012 revision-9 migration fixture; targeted Ruff and strict
  mypy passed. Revision 10 has seven additive tables and a normal-write recovery fence.
- 2026-08-01: US1 focused gate passed: 23 tests across domain/port, active/quarantine
  inventory, all root reasons, holds, plan determinism, limit overflow, validate-only
  workspace/CAS and CLI. Full strict mypy remained green across 64 source files.
- 2026-08-01: US2 focused gate passed: 15 tests including persisted-intent crash
  recovery, normal-write fencing, no-overwrite/idempotent active↔quarantine transitions,
  twenty concurrent same-plan callers and exact plan/batch CLI round trip. Ruff and
  strict mypy stayed green.
- 2026-08-01: US4 focused and convergence drills passed: canonical internal manifests,
  streaming hashes/copies, FTS exclusion, root completeness, exclusive fresh publication,
  capacity rejection, corruption/path rejection, A→B→A objects and catalog facts,
  revision-9 rollback, expected-revision migration and twenty concurrent migrators.
- 2026-08-01: US3 focused drills passed at 23:59:59 and the exact 24-hour boundary;
  exact acknowledgement, final root/hold revalidation, conflict restore, every exposed
  crash boundary and twenty concurrent commits/restores all converged without loss.
- 2026-08-01: US5 focused drills passed with exact reserve-minus-one/reserve-exact
  admission, closed storage categories, authoritative global index replacement,
  orphan/drift repair and injected all-or-prior transaction rollback.
- 2026-08-01: fresh quickstart validated initialization, inventory, plan, diagnostics,
  backup, restore, restored inventory and global rebuild. The retained synthetic run was
  isolated below the operating-system temporary directory.
- 2026-08-01: initial Spec Kit convergence found four partial evidence gaps (SC-001,
  SC-004, SC-005, SC-008, FR-022, FR-027 and FR-036). Tasks T057–T060 completed them;
  the second pass checked 41 requirements, 14 success criteria, 20 acceptance scenarios,
  plan decisions and constitution rules with zero remaining findings.
- 2026-08-01: final repository gates passed: Ruff check; Ruff format check over 183
  files; strict mypy over 64 source files; 1,210 offline tests; 85.85% total branch
  coverage against the 85% floor; sdist and wheel build; all 12 generated schemas
  current; evidence conformance (7 valid, 8 invalid, 1 record set, 6 identity vectors);
  repository validation; and the complete pre-commit suite.
- 2026-08-01: the first PR run exposed a Windows low-level read/physical-length mismatch.
  T061 added focused descriptor evidence and retained strong path-to-handle identity plus
  fail-closed post-read checks. The initial metadata hypothesis did not resolve Windows;
  later run evidence isolated the actual binary-mode cause recorded under T063. The
  focused suite and all then-current local gates remained green.
- 2026-08-01: the next Linux PR run exposed two exact restore callers racing at POSIX
  hard-link publication. T062 now accepts only a cryptographically verified converged
  destination after a competing OS-level result, removes the exact two-link intermediate
  state idempotently and still rejects unrelated/conflicting locations. A barrier test
  deterministically forces ten callers through that publication boundary. Ruff, format,
  strict mypy and all 1,212 offline tests passed at 85.87% branch coverage.
- 2026-08-01: two subsequent Windows runs proved that replayed hashes matched but the
  byte count disagreed with physical length. Python's `os.open()` contract requires
  `O_BINARY` on Windows; T063 now adds it to every low-level maintenance read/write
  descriptor. Same-handle byte/hash replay remains defense in depth and device/inode
  identity is again required on every platform. The focused backup/restore/CLI/security
  suite passed, followed by the complete local gate with 1,214 offline tests and 85.88%
  branch coverage before the final platform rerun.
- 2026-08-01: that platform rerun cleared every prior Windows read mismatch and exposed
  the separate `_commit()` requirement behind `os.fsync()`: operation-owned staged files
  must be opened read/write. T064 applies that least-privilege distinction without
  widening source or verification reads and adds a focused descriptor-mode regression.
  Ruff, format, strict mypy, all 1,215 offline tests at 85.87% branch coverage, package/
  schema/evidence/repository validation and the complete pre-commit suite passed.
- 2026-08-01: the following Windows run cleared those restore failures and exposed a
  late-arriving same-plan quarantine caller whose fresh inventory correctly differed
  after the winner completed. T065 rechecks the exact deterministic plan batch before
  declaring staleness and makes the catalog's atomic claim prefer exact existing
  operation history before validating a now-obsolete pre-move snapshot. Ruff, format,
  strict mypy, all 1,216 offline tests at 85.84% branch coverage, package/schema/
  evidence/repository validation and the complete pre-commit suite passed.

## Tradeoffs and residual risk

- SQLite and filesystem changes cannot share one native atomic transaction. F013 uses a
  complete durable intent plus a normal-write fence and idempotent replay; external
  modification of managed directories remains unsupported and fails closed.
- Backup is a local internal directory artifact, not Feature 014 interchange. It
  conservatively includes every verified active object in addition to required roots,
  excludes FTS and staging, and publishes `COMPLETE` last in an exclusively created
  destination. A process kill may leave an unmarked incomplete destination for explicit
  operator inspection/removal; it is never accepted as complete.
- Restore publishes the workspace marker last. It supports recorded revisions for
  recovery inspection, while normal application open still requires the current
  revision; a restored revision-9 workspace must be explicitly migrated before use by
  the current application.
- Capacity is an exact point-in-time observation, not a reservation guaranteed by the
  filesystem. Mid-stream ENOSPC cleans only operation-owned incomplete state and never
  triggers deletion. Disposable-index bytes are reported as logical indexed UTF-8 bytes,
  not an unsupported claim of exact SQLite page attribution.
- Commit means logical unlink from the managed store, not secure erasure. The v0.1
  policy protects every delivered catalog root and intentionally favors retained bytes.
- Explicit migration is deliberately limited to the one supported predecessor,
  revision 9. Newer, gapped, drifted or older unsupported histories remain untouched.

## Delivered internal contracts and operator commands

- `MaintenanceStore` owns bounded inventory, exact transition/removal, capacity and
  diagnostics; ordinary `ObjectStore` remains immutable and has no removal method.
- `MaintenanceRuntimeCatalog` owns snapshots, holds and complete quarantine/restore/
  commit intent plus terminal audit state; normal catalog writes remain fenced while an
  intent is active.
- `storage-inventory`, `storage-plan`, `storage-hold`, `storage-hold-release`,
  `storage-quarantine`, `storage-restore`, `storage-recover`, `storage-commit`,
  `storage-diagnostics`, `index-rebuild`, `workspace-backup`, `workspace-restore` and
  `workspace-migrate` use stable body-free output and sanitized failure categories.
- No public JSON schema, provider/renderer profile, MCP descriptor, dependency or
  persisted identity algorithm changed.

## Rollback

Revision-9 workspaces must be backed up before explicit migration. Supported rollback
is restoration of that verified backup to a fresh disjoint location; migration history
and original backup bytes are never edited.
