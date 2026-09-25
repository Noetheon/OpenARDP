# OpenARDP Spec Kit operating procedure

**Status:** Authoritative
**Adopted:** 2026-07-26; risk-tier amendment 2026-08-09; lean-records amendment 2026-09-24 (Constitution 4.0.0)

## Start from the task

Name the concrete person or agent task the change improves and how the improvement will be observed
([Article XIII](CONSTITUTION_SOURCE.md)). Prefer the smallest change someone can try this week. Defects on real user
paths (installation, ingestion, agent connection, retrieval) come before new capability.

## Keep records in proportion

- **Pull-request record only:** documentation, tests, internal refactoring and narrow fixes with no user-visible
  behavior, contract, schema, persistence, identity, migration, security/trust, provider or default-dependency
  impact. State scope, relevant tests, exact results and rollback where meaningful.
- **Durable feature record:** user-visible behavior, public contracts, schemas, persisted identity, migrations,
  security/trust boundaries, providers or default dependencies. Keep a concise `spec.md` (task served, acceptance
  criteria, decisions) and an `implementation-notes.md` (exact commands and results, tradeoffs, residual risks,
  rollback) under `specs/NNN-name/`, and add a feature-map row.
- **ADR first:** irreversible or architectural decisions, such as persisted identity, storage format, security
  boundaries, default-install dependencies and public contract compatibility.

Executable-path CI remains determined by the fail-closed CI classifier for every change.

## Optional Spec Kit stages

Clarify, plan, checklist, tasks, analyze and converge are tools, not gates. Use a stage when it reduces a concrete risk,
for example a checklist for a migration or an analysis for a security boundary. The steps that remain mandatory for
any behavior change are:

1. Establish a clean branch, a green locked baseline and an exact rollback point.
2. Add tests before behavior where practical; cover failure, cancellation, restart and recovery where the change can
   meet them.
3. Implement the smallest bounded change.
4. Validate lint, format, strict typing, tests, build, offline behavior and supported-platform CI.
5. Converge behavior, documentation, contracts, ADRs, changelog and the durable record.
6. Submit one pull request with residual risks and exact rollback instructions, and confirm post-merge `main` CI.

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
- Known critical or high-severity defects in the change block merge.
