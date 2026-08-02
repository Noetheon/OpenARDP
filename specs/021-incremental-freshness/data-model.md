# Data model: Incremental Freshness Status

## IntegrityCoverage

Closed, body-free assurance vocabulary:

- `NONE`: no prepared-representation integrity coverage was established.
- `HEAD`: the exact source identity and one atomic catalog head/header snapshot were checked; block projections and block
  objects were not enumerated.
- `FULL`: every native, manifest, projection and block artifact required by the existing verifier passed during this
  request.

`FULL` is a successful coverage claim, not a requested-mode or attempted-mode marker. A failed full audit returns
`INTEGRITY_ERROR` with a non-full coverage value.

## StatusMode

Request-only closed selection:

- `HEAD`: default exact source freshness with bounded header coverage.
- `FULL`: exact source freshness followed by complete representation verification.

The mode is not persisted and is not available through MCP.

## DocumentStatusSnapshot

One immutable in-memory catalog projection loaded from one read transaction:

- `document`: registered logical document.
- `head`: current successful observation, or absent.
- `representation`: matching representation header, or absent.

Validation rules:

- Head and representation document identities must match the document.
- A representation may exist only when a head exists and must match its exact scope.
- No block projection or body is part of the snapshot.

## SourceStatus extension

Existing fields and freshness vocabulary remain unchanged. Add:

- `integrity_coverage`: `IntegrityCoverage`, required in serialized output.

Shape rules:

- `NOT_REGISTERED` implies `NONE`.
- `FULL` requires a READY head and a successful complete verifier call.
- `INTEGRITY_ERROR` cannot claim `FULL`.
- `HEAD` means bounded catalog-head coverage only and never arbitrary block integrity.
- Existing document/head/observed-version invariants remain in force.

## Freshness benchmark records

### Observation

- protocol, environment and F020 baseline identities;
- scale, mode, workload and repetition;
- status, freshness and integrity coverage;
- wall time and process CPU time;
- parser, projection-load and block-read counters;
- sanitized unavailable/failure reason.

### Summary

- homogeneous seven-sample group identity;
- p50 and p95 latency;
- exact counter totals and semantic pass counts.

### Decision

- `TARGET_MET` only when both scales meet 250 ms p95 and all hard semantic/counter checks pass;
- `TARGET_MISSED` otherwise, with stable reasons;
- F015 and F020 decisions remain inherited references, not inputs that can be rewritten.

### Run manifest

Atomic published inventory containing input and output hashes, environment class, duration and result identity. No paths,
bodies, usernames, hostnames or raw exceptions are permitted.
