# Implementation Plan: Bounded semantic session reuse

**Branch**: `codex/f037-semantic-session-reuse` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

## Summary

Keep one semantic compiler per MCP session, keyed by the complete estimator identity. Keep only the active provider corpus and the unique object vectors required by it. Replace obsolete state rather than accumulating it. Existing authority checks, limits, rankings and persisted contracts remain authoritative.

## Technical Context

Python 3.12; existing Pydantic v2, MCP stdio adapter and optional offline E5 worker. No new dependency, persistent storage or public API. Pytest offline synthetic providers and worker dependencies exercise regressions; existing integration/security tests cover authority. Linux, macOS and Windows remain supported.

Performance acceptance uses preparation/encoding counts, not timing claims. At most one session compiler, one active prepared handle and `max_cache_entries` unique object vectors. Every request must also satisfy existing passage and byte limits.

Contract/version impact: no public schema, persisted identity, workspace format, application version, provider recipe or export profile change. Worker corpus bookkeeping is private, disposable process state. ADR-0019 already permits bounded process-local prepared corpora. A changed estimator evicts the old compiler; a failed semantic compilation clears the slot. Unknown estimators continue to fail closed. Lexical behavior remains unchanged.

Trust/operations: no network/model provisioning in tests, no original mutation. A cached compiler still obtains a current source snapshot and verifies authoritative catalog/CAS data. Invalid worker input is rejected before mutation; runtime failures invalidate worker/session state through existing failure handling. No transparent retry changes cancellation semantics.

## Constitution Check

Before research and after design: PASS. Originals, thin projections, provider-native evidence and disposable accelerators are preserved. Dependencies point inward. Stronger reuse does not make caches authoritative. Scope is one high-assurance work package with full lifecycle, red/green tests and exact validation results. No ADR-triggering architectural replacement or frozen benchmark modification.

## Design and Structure

- `src/openardp/interfaces/mcp_server.py`: one optional `(EstimatorIdentity, ContextCompilerService)` slot. Create on miss, replace on identity change, drop on any semantic compile failure.
- `src/openardp/adapters/e5_semantic.py`: validate requested passages and limits first, deduplicate by object ID with equal text, retain overlap and encode unique missing objects once. Prepare replaces the single handle and records exact limits. Direct score invalidates prepared handles. Prepared scoring requires the original limits and live object entries.
- `tests/integration/test_mcp_semantic_context.py`: real stdio/factory lifetime, identity changes, authority and recovery regressions.
- `tests/unit/test_e5_semantic.py` or a focused sibling: real worker request functions with synthetic numerical/model dependencies for bounded replacement, overlap, shared objects, conflicts, stale handles and limit mismatch.
- `docs/` and `CHANGELOG.md`: explain process-local reuse and invalidation without new speed claims.

See [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md) and [contracts/session-lifecycle.md](contracts/session-lifecycle.md). No new framework or provider abstraction is needed.

## Execution and Dependencies

Complete requirements checklist and analyze spec/plan/tasks before code. MCP and worker regression/fix tracks may run in parallel because files are disjoint. Then run combined regressions, all repository gates and independent convergence. Merge this package before beginning the dependent user-workflow package.

## Complexity Tracking

No constitutional violations or new architectural abstractions.
