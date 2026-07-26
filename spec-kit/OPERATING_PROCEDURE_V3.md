# Operating procedure v3.1 adoption source

> **Status:** Adoption source, not authoritative. The active procedure is
> [`OPERATING_PROCEDURE.md`](OPERATING_PROCEDURE.md).

## Per-feature lifecycle

1. Establish clean branch, green locked baseline and rollback point.
2. Specify measurable outcome, non-goals and compatibility impact.
3. Clarify trust, identity, failure, cancellation, privacy, licensing and migration semantics.
4. Plan architecture, dependency, ADR, storage and operational effects.
5. Run requirements checklist.
6. Produce dependency-ordered, file-scoped tasks.
7. Analyze and block on every critical/high finding.
8. Implement the smallest bounded change.
9. Validate lint, format, strict typing, unit/property/integration tests, build, offline checks and supported-platform CI.
10. Validate failure injection, restart/idempotency and upgrade/rebuild paths where relevant.
11. Converge behavior, docs, contracts, ADRs, changelog and validation evidence.
12. Submit one-feature PR with residual risks and rollback instructions.

## Codex discipline

- Inspect current code and merged specs before abstraction work.
- Extend current ports/services; do not create parallel frameworks.
- Never weaken tests or silently rewrite accepted ADRs.
- Every external dependency needs maintenance, license, security and lockfile review.
- Generated outputs need deterministic regeneration and drift checks.
- Public contracts must not leak Python, SQLite, FTS5 or Docling internals unless explicitly provider-profile data.
- Resource limits must state units, defaults, configuration range and failure behavior.
- Success paths alone are insufficient: cancellation, crash, disk-full, malformed input and restart behavior are
  acceptance concerns.
