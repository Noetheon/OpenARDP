# ADR 0005: Portable ZIP export, unpacked content-addressed runtime

Status: Proposed

## Decision

Use a self-contained `.ardp.zip` for interchange, but an unpacked CAS plus catalog for normal runtime.

## Rationale

ZIP is familiar and portable; CAS avoids duplicate assets and full archive rewrites during every change.

## Consequences

- Export/import and integrity verification are explicit operations.
- Safe ZIP handling is security-critical.
