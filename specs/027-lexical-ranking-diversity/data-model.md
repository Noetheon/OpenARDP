# Data Model: F027

## LexicalAllocationPolicy

Immutable fields: `name`, `version`, `max_per_document=16`, `ranked_prefix=4`,
`deduplicate_exact_bodies=true`, `fair_round_robin=true`. `policy_id` is the canonical SHA-256 of all fields.

## RankedCandidate

An existing verified `ContextCandidate` plus an internal deterministic total-order key. No source body, benchmark label or
new persisted identity is introduced.

## AllocationResult

`ordered` contains all accepted candidates in fair order; `rejected` contains each exact duplicate or over-quota item
once with its stable reason. It composes with the existing freshness/rejection partitions.

## Invariants

- Every eligible input appears exactly once in `ordered` or allocation `rejected`.
- No document occurs more than `max_per_document` times in `ordered`.
- Exact body identities occur at most once in `ordered` when dedupe is enabled.
- Policy identity and results are independent of input enumeration order after stable ranking.
