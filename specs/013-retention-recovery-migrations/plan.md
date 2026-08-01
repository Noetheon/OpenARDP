# Implementation Plan: Retention, Recovery and Migrations

**Branch**: `codex/f013-retention-gc-quarantine` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/013-retention-recovery-migrations/spec.md`

## Summary

Add an explicit, bounded maintenance plane for long-running local workspaces. Revision
10 records retention holds, quarantine batches and restart-persistent maintenance
intent. A dedicated filesystem maintenance adapter can quarantine, restore, back up and
commit only exact catalog-authorized objects; the ordinary object-store port remains
immutable and non-destructive. Normal workspace open becomes validate-only, migration
becomes explicit and requires a verified paired backup, and the disposable lexical
index gains an all-or-prior complete rebuild.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: Python stdlib, Pydantic v2 and the locked RFC 8785 helper
**Storage**: existing SHA-256 filesystem CAS and SQLite catalog; additive revision 10
**Testing**: pytest with network disabled, synthetic clocks/filesystems, fault hooks and subprocess crash probes
**Target Platforms**: Linux, macOS and Windows on supported local filesystems
**Project Type**: installable Python library and CLI
**Performance Goals**: bounded streaming inventory/backup/restore; constant-memory file copying; one maintenance writer per workspace
**Constraints**: no automatic irreversible deletion, no source mutation, no link traversal, no remote/shared filesystem claim, no raw paths/bodies in reports or audit, no public-schema/dependency change
**Scale/Scope**: configurable entry/byte ceilings; v0.1 protects every catalog reference and selects only complete verified unreferenced CAS objects at least 24 hours old
**Contract/Version Impact**: internal CLI/service additions and workspace revision 9→10; public schemas, MCP 0.1.0, provider profiles and export profile remain byte-stable
**Trust/Operational Impact**: document content stays inert; only an explicit trusted CLI operator can persist maintenance intent; every destructive transition is named, bounded, journaled and recoverable

## Constitution Check

### Before design

| Article | Gate | Result |
|---|---|---|
| I Source truth | Originals are never maintenance targets; every referenced object is protected | PASS |
| II Disposable accelerators | Only lexical index rows are rebuildable/disposable | PASS |
| III Reuse/provider neutrality | stdlib/SQLite mechanisms sit behind narrow maintenance ports | PASS |
| IV Thin projection | No second document model or public interchange archive | PASS |
| V Data is not instruction | Content cannot create holds, plans, acknowledgement or tool actions | PASS |
| VI Identity/atomicity | JCS/SHA-256 plans/manifests and durable operation intent | PASS |
| VII Progressive delivery | inventory/diagnostics expose opaque reasons/counts before bytes | PASS |
| VIII Test-first gates | failure, restart, concurrency and immutability tests precede paths | PASS |
| IX Measured claims | recovery and cross-platform claims require reproducible tests | PASS |
| X Simplicity | one local maintenance service; no daemon or storage replacement | PASS |
| XI Feature isolation | only F013 retention/recovery/migration/index maintenance | PASS |
| XII Contract governance | ADR 0014 and immutable revision-10 migration | PASS |

### After design

- `ObjectStore` remains immutable; destructive authority exists only in the internal
  maintenance port and CLI composition root.
- SQLite is the durable authority for operation intent. Filesystem presence alone never
  authorizes deletion, and generic recovery cannot create irreversible intent.
- A short SQLite writer reservation plus `Connection.backup()` on a second connection
  creates a consistent catalog snapshot while the persistent maintenance fence blocks
  normal writers. Raw catalog copying and shared-filesystem correctness are rejected.
- Backup is an implementation recovery artifact, not F014 interchange.
- Revision 10 is additive. Existing revisions/checksums and all public contracts remain
  frozen. ADR 0014 records the destructive boundary and refines the earlier migration
  lock from `BEGIN EXCLUSIVE` to a writer reservation compatible with a second reader.
- All gates remain PASS; implementation begins only after analysis reports no unresolved
  critical or high contradiction.

## Project Structure

### Feature documentation

```text
specs/013-retention-recovery-migrations/
├── analysis.md
├── checklists/
│   ├── requirements.md
│   └── retention-recovery.md
├── contracts/
│   └── internal-maintenance-contract.md
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
│   ├── filesystem_cas.py
│   ├── filesystem_maintenance.py
│   ├── local_workspace.py
│   ├── sqlite_catalog.py
│   └── sqlite_migrations.py
├── domain/
│   └── maintenance.py
├── ports/
│   └── maintenance.py
├── services/
│   └── maintenance.py
└── interfaces/
    └── cli.py

tests/
├── contract/test_maintenance_ports.py
├── domain/test_maintenance.py
├── integration/test_backup_restore.py
├── integration/test_f013_migration.py
├── integration/test_index_rebuild.py
├── integration/test_retention_catalog.py
├── integration/test_retention_recovery.py
├── integration/test_retention_service.py
├── integration/test_workspace.py
└── security/test_maintenance_boundaries.py
```

## Phase 0 — Research and decision closure

1. Freeze the richer catalog-root snapshot and deterministic plan projection.
2. Freeze the restart-persistent cross-resource operation protocol and exact recovery
   states for quarantine, restore and commit.
3. Freeze consistent backup, fresh restore and explicit migration topology.
4. Freeze local filesystem admission/copy/move/durability and capacity rules on all
   three platforms.
5. Record the destructive authority and migration-lock refinement in ADR 0014.

## Phase 1 — Pure contracts and revision 10

1. Add closed internal maintenance models, canonical identities, state transitions and
   body-free result projections.
2. Add narrow catalog/filesystem maintenance protocols without changing `ObjectStore`.
3. Append revision 10 tables for holds, batches, entries, operations, ordered operation
   entries, events and paired migration-backup identity.
4. Add a partial unique active-operation fence and make ordinary catalog writes reject
   while durable maintenance intent requires recovery.

## Phase 2 — Inventory, retention and recovery

1. Implement validate-only CAS opening and a bounded rich inventory containing safe
   modification time, length, link/type checks and quarantine state.
2. Produce a single-transaction root/hold snapshot with closed reason codes and opaque
   reference digests covering every F012 root family.
3. Build deterministic dry-run plans; overflow and any managed-tree inconsistency
   expose no actionable plan.
4. Claim exact ordered quarantine/restore/commit intents transactionally, perform
   idempotent same-filesystem transitions, then publish terminal audit state.
5. Recovery replays only persisted intent. Commit intent must already contain the
   distinct acknowledgement and exact final actions before any unlink occurs.

## Phase 3 — Backup, restore and explicit migration

1. Validate fresh disjoint local destinations and reserve capacity before publication.
2. Fence ordinary writers, reserve the SQLite writer, copy the catalog through the
   online backup API, enumerate exact roots from the coordinating snapshot and stream
   verified object bytes to sibling staging.
3. Normalize only the backup copy by removing the ephemeral active-operation fence and
   disposable index rows; write the canonical manifest last and publish after complete
   verification.
4. Restore only manifest-allowlisted regular files into fresh sibling staging, verify
   catalog history and all objects, then atomically publish without migrating.
5. Split new initialization, validate-only open and explicit migration. Migration must
   publish a verified revision-9 backup first, then apply the complete pending chain in
   one transaction.

## Phase 4 — Diagnostics, index rebuild, CLI and convergence

1. Report bounded logical category bytes, catalog/sidecar bytes, capacity reserve and a
   closed health state without paths or content.
2. Replace the complete lexical accelerator from verified authoritative prepared
   evidence in one transaction; failure leaves the prior index visible.
3. Add explicit `storage-*`, `workspace-*` and `index-rebuild` CLI commands with stable
   human/JSON projections and sanitized error categories.
4. Update architecture, data model, security, operations, compatibility, roadmap,
   README, start guide, changelog and validation evidence.
5. Run focused/full/package gates, converge artifacts and verify Linux/macOS/Windows PR
   plus post-merge CI before F014.

## Complexity Tracking

| Decision | Why needed | Simpler alternative rejected |
|---|---|---|
| Persistent maintenance operation journal | SQLite and filesystem cannot share one transaction; crash recovery needs exact authority | Inferring from object locations could legitimize accidental deletion |
| Live SQLite writer reservation plus second backup connection | Paired catalog/object snapshot must exclude concurrent roots while permitting the SQLite backup reader | Raw file copy is unsafe; `BEGIN EXCLUSIVE` blocks the required reader |
| Dedicated destructive filesystem adapter | Ordinary CAS contract deliberately has no deletion authority | Adding delete to `ObjectStore` expands every consumer's authority |
| Backup-copy normalization | Active operation fence and lexical index are operational/disposable, not restored truth | Copying them makes a restored workspace falsely fenced or stale |

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

The final PR and post-merge `main` run must pass Linux, macOS and Windows before F014
begins.
