# ADR 0005: Portable ZIP export, unpacked content-addressed runtime

Status: Deferred

Deferred to: Feature `014-export-interchange-experiment`

## Decision

No custom interchange package is selected yet. Feature 014 will compare existing standards and packaging profiles with a
custom export using explicit evidence and will record the resulting decision in a new ADR.

## Rationale

The original proposal assumed that a custom `.ardp.zip` was necessary before interoperability requirements and existing
profiles had been evaluated. Runtime CAS remains governed separately by
[ADR 0002](0002-sqlite-and-filesystem-cas-for-mvp.md).

## Consequences

- No custom-format requirement or stability guarantee exists before Feature 014 converges.
- Any future archive handling must be bounded against traversal, unsafe links and decompression bombs.
- An export decision must define independent export-profile versioning, integrity, migration and recovery behavior.
