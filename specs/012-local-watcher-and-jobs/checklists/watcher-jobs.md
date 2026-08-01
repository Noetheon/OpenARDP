# Watcher and Job Correctness Checklist

**Purpose**: Challenge the requirement set before implementation
**Created**: 2026-08-01
**Feature**: [spec.md](../spec.md)

## Root and scan authority

- [x] Explicit root and workspace authority is required at every public entrypoint
- [x] Root/workspace overlap, symlink/junction and device-boundary rules are closed
- [x] Complete versus incomplete scan semantics prevent partial delete/schedule claims
- [x] Entry, depth and root-identity bounds are measurable
- [x] Unsupported network-share guarantees are not overstated

## Stability and identity

- [x] Metadata fingerprint fields and clock behavior are exact
- [x] Stability cannot replace exact SHA-256 ingestion
- [x] Deduplication inputs and excluded operational fields are explicit
- [x] Rename hints cannot mutate path-addressed source identity
- [x] Tombstone and reappearance transitions preserve evidence/history

## Jobs and recovery

- [x] Queued and running cancellation races have one fenced terminal outcome
- [x] Existing transition replays and stale token/revision rejection remain defined
- [x] Eligibility and retry time survive restart and affect deterministic claim order
- [x] Cancellation-aware lease expiry is distinct from retry/failure
- [x] Backpressure always leaves durable evidence for later convergence

## Privacy and operations

- [x] Persisted/default output allowlists exclude path/body/token/free-form error data
- [x] Continuous mode is foreground, interruptible and independently testable
- [x] Rich ingestion configuration is explicit and never downloaded
- [x] Upgrade, failed migration, backup and rollback behavior is explicit
- [x] Three-platform and no-network evidence is required before merge

**Result**: PASS. No critical or high watcher/job requirement gap remains.
