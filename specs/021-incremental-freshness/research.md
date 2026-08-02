# Research: Incremental Freshness Status

## Decision 1 — Remove complete block verification from default freshness

**Decision**: Default status continues to hash the complete authoritative source but reads only a body-free atomic
document/head/representation-header snapshot. Complete physical and semantic verification becomes an explicit full mode.

**Rationale**: A fresh 10,000-block profile attributed 3.850 of 4.061 profiled seconds to
`verify_ready_representation`, including 10,001 object reads and 10,000 block validations. F020 likewise measured 2.087 s
reference and 28.626 s scale p95. This work answers a different question from source freshness.

**Alternatives considered**:

- Keep full verification on every call: rejected because it is O(block count) and failed the product target.
- Use only size and modification time: rejected because same-metadata edits would become stale false negatives.
- Memoize a successful full verification: rejected because post-verification external corruption would be silently
  hidden unless a trustworthy invalidation mechanism existed.

## Decision 2 — State integrity coverage explicitly

**Decision**: Add a closed `NONE`, `HEAD` and `FULL` coverage vocabulary. `FULL` is emitted only after the existing
complete verifier succeeds during that request.

**Rationale**: `CURRENT` describes the source/head identity relationship; it must not imply that every persisted block
was reread. Explicit coverage makes the faster result honest and machine-checkable.

**Alternatives considered**:

- Keep output unchanged and document the difference only in prose: rejected as ambiguous and unsafe for automation.
- Add a boolean `verified`: rejected because it cannot distinguish no representation check, bounded head coverage and
  complete representation coverage.

## Decision 3 — Add one atomic status snapshot over existing rows

**Decision**: Add a catalog operation returning the logical document, current head and matching representation header
from one read transaction without loading projection rows.

**Rationale**: Separate calls can mix a prior head with a newer representation during concurrent ingestion. The existing
SQLite rows already contain every field required for bounded status, so a migration or materialized attestation is not
needed.

**Alternatives considered**:

- Add a new status table or integrity root: rejected because it duplicates current rows and introduces migration and
  invalidation risk without improving source freshness.
- Read `list_document_summaries`: rejected because it scans unrelated documents and omits artifact completeness fields.

## Decision 4 — Preserve complete verification without exposing it through MCP

**Decision**: Service callers and CLI may request full verification. MCP keeps its existing identifier-only request and
always uses bounded HEAD coverage while returning the explicit coverage value.

**Rationale**: Full verification may take tens of seconds and read 100,000 objects. Exposing it as a normal read-only MCP
operation would create an avoidable resource-exhaustion surface.

**Alternatives considered**:

- Add an MCP full-mode flag: rejected as inconsistent with bounded progressive disclosure.
- Remove full status entirely: rejected because arbitrary persisted corruption still needs an exact audit path.

## Decision 5 — Reuse F020 corpora and baselines in a focused benchmark

**Decision**: Create a separate versioned F021 freshness benchmark that reuses F020's deterministic corpus generator and
committed baseline values, runs one warm-up plus seven samples for default and full modes, and retains exact operation
counters.

**Rationale**: Rerunning the 48-minute complete product benchmark is unnecessary and costly. A focused benchmark isolates
the changed path while keeping the earlier unfavorable evidence immutable and visible.

**Alternatives considered**:

- Replace the F020 result files: rejected because measured historical evidence is immutable.
- Measure only a micro-helper: rejected because SQLite, source hashing and the production service path must remain in
  scope.
- Run timing in every CI job: rejected because shared runners are noisy and F019 deliberately avoids redundant cost.

## Decision 6 — Require both semantic and structural complexity evidence

**Decision**: Acceptance requires exact current/changed/missing/corrupt outcomes plus zero block-projection loads, zero
block reads and zero parser invocations for default status. Timing alone cannot pass the feature.

**Rationale**: A single fast result could come from skipping source hashing or silently trusting stale metadata.
Operation counters prove the intended complexity boundary independently of hardware noise.

**Alternatives considered**:

- Accept only p95 latency: rejected as vulnerable to warm caches and hardware variance.
- Use Big-O claims without counters: rejected because the claim would not be executable evidence.
