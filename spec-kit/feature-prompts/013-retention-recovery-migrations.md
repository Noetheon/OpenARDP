# Feature 013 — Retention, recovery and migrations

## Goal
Make long-running workspaces sustainable and recoverable without unsafe automatic deletion.

## Requirements
- Reachability inventory across sources, versions, native artifacts, projections, derivations and indexes.
- Retention policy with dry-run, reasoned candidate report, quarantine and grace period.
- No automatic irreversible GC in v0.1; explicit operator commit only.
- Backup/restore and integrity verification.
- Transactional restart-safe workspace/catalog migrations and unsupported-newer-version fail-safe.
- Disk-usage diagnostics, low-space behavior and rebuild of disposable indexes.

## Tests
Crash during migration/reclamation, restore to fresh location, A→B rollback evidence, false-reclamation prevention, open-newer-workspace without mutation and cross-platform path behavior.
