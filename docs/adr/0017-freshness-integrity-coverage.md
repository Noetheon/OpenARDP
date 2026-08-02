# ADR 0017: Separate source freshness from complete representation integrity

Status: Accepted for Feature 021

Date: 2026-08-02

## Context

`DocumentQueryService.status` currently hashes the authoritative source and then loads and completely verifies every
block in the current READY representation. F020 measured status p95 at 2.087 seconds for 10,000 blocks and 28.626 seconds
for 100,000 blocks against a 250 ms target. Focused profiling confirmed that complete block verification dominates the
path. Source freshness and exhaustive derived-evidence integrity are both valuable but answer different questions.

Removing source hashing would weaken stale safety. Caching a prior full verification would miss later external CAS
corruption without a trustworthy invalidation channel. Adding a persisted attestation would not prove that every
referenced object still has its expected bytes.

## Decision

Feature 021 separates the operations and exposes their assurance coverage explicitly:

- Default status always hashes the authoritative local source and reads one atomic catalog document/head/representation
  header snapshot. It does not enumerate block projections or block CAS and reports `HEAD` coverage.
- Explicit service/CLI full status reuses the existing exhaustive verifier and reports `FULL` only after every required
  artifact passes.
- Failed or unperformed complete verification never reports `FULL`.
- MCP remains identifier-only and bounded to default HEAD coverage; it cannot initiate the expensive audit.
- Existing freshness values and exact SHA-256 source identity remain unchanged.

The atomic snapshot uses existing catalog rows and requires no workspace migration, new stored attestation or identity
algorithm. F021 adds an experimental output field and documents its semantics across service, CLI and MCP.

## Consequences

- Routine freshness becomes proportional to source inspection plus constant catalog metadata, not prepared block count.
- `CURRENT` no longer ambiguously implies that every derived artifact was reread; coverage states what was established.
- Arbitrary post-publication block corruption is detected by explicit full verification, not bounded HEAD status.
- Operators and benchmark reports must present performance and assurance together.
- A future filesystem integrity monitor or trusted invalidation cache requires a separate feature and threat analysis.

## Alternatives considered

- Keep exhaustive verification in default status: rejected by measured scaling and interaction latency.
- Trust modification time/size: rejected because exact same-metadata byte edits must be detected.
- Cache full-verifier success in memory: rejected because external mutation would make the cache stale.
- Store only a Merkle/attestation root: rejected because verifying the stored root alone does not prove current object
  bytes and scanning all leaves recreates the current complexity.
- Expose full mode through MCP: rejected as an avoidable resource-exhaustion boundary.
