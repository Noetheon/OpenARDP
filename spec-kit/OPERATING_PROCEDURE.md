# OpenARDP Spec Kit operating procedure

**Status:** Authoritative
**Adopted:** 2026-07-26; risk-tier amendment 2026-08-09

## Classify before planning

Use the lowest tier whose complete conditions are satisfied. Unknown, mixed or disputed scope moves upward.

### Routine

Documentation, tests, internal refactoring or a narrow fix with no user-visible behavior, contract, schema, persistence,
identity, migration, security/trust, provider, dependency, benchmark or release impact.

- No feature directory or Spec Kit lifecycle.
- One bounded PR with scope, relevant tests, exact results, risks and rollback where meaningful.
- Executable-path CI remains determined by the fail-closed CI classifier.

### Standard

A bounded user-visible behavior change without a high-assurance trigger.

- Create concise accepted requirements in `spec.md`.
- Use only planning artifacts that materially reduce risk.
- Record exact final evidence, risks and rollback in `implementation-notes.md` before merge.

### High assurance

Any public contract, schema, persisted identity, migration, security/trust boundary, provider, external dependency,
license/supply-chain, benchmark methodology, release decision or similarly material compatibility change.

Use the complete lifecycle below and any required ADR.

## High-assurance lifecycle

1. Establish a clean branch, green locked baseline and exact rollback commit.
2. Specify a measurable outcome, explicit non-goals and compatibility impact.
3. Clarify trust, identity, failure, cancellation, privacy, licensing and migration semantics.
4. Plan architecture, dependency, ADR, storage, contract/version and operational effects.
5. Run a requirements-quality checklist that challenges completeness and testability.
6. Produce dependency-ordered, file-scoped tasks with tests before implementation where practical.
7. Analyze specification, plan, tasks and constitution; block on every critical or high finding.
8. Implement the smallest bounded change and mark tasks only after evidence exists.
9. Validate lint, format, strict typing, unit/property/integration tests, build, offline behavior and supported-platform CI.
10. Validate failure injection, cancellation, restart/idempotency, upgrade/rebuild and recovery paths where relevant.
11. Converge behavior, documentation, contracts, ADRs, changelog, task state and validation evidence.
12. Submit one feature pull request with residual risks and exact rollback instructions; confirm post-merge `main` CI.

The high-assurance order is: constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge.
Constitution amendments occur only when the active feature explicitly owns them.

## Completed-feature compaction

After convergence and durable-content review, retain `spec.md`, `implementation-notes.md` and normative contracts. Remove
plans, research, data-model notes, quickstarts, task lists, analyses, checklists and generated prompts when their unique
durable content and references have been migrated. Git history is the recovery path; do not create a parallel archive.

## Implementation discipline

- Inspect current code, schemas, merged specifications and accepted ADRs before abstraction work.
- Extend current ports and services; do not create parallel frameworks.
- Never weaken tests, typing, coverage, security controls or accepted decisions to make a gate pass.
- Every external dependency requires maintenance, license, security, lockfile and supply-chain review.
- Generated output requires deterministic regeneration and drift checks.
- Public contracts must not leak Python, SQLite, FTS5 or provider internals unless explicitly profile-scoped.
- Resource limits must state units, defaults, supported configuration range and failure behavior.
- A worker process is bounded isolation, not a universally strong sandbox.
- Success paths alone are insufficient: cancellation, crash, disk exhaustion, malformed input and restart behavior are
  acceptance concerns where the feature can encounter them.

## Evidence and claims

- Record exact commands, versions, environments, results, limitations and rollback point.
- Use persisted provider-native reuse as a baseline for redundant-parsing performance claims.
- Qualify future behavior as planned; do not present a roadmap requirement as implemented.
- Public contracts remain experimental until external-use and independent-implementation evidence supports stabilization.
- Verify content and security-sensitive metadata referenced by disposable indexes against authoritative records.

## Pull-request boundary

- One bounded change concern per branch/PR.
- No later-feature runtime behavior.
- No unrelated dependency or lockfile change.
- Durable historical records remain discoverable; removed transient planning remains recoverable from Git history.
- Critical/high convergence findings block merge.
