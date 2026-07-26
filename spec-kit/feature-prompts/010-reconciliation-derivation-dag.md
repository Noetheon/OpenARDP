# Feature 010 — Reconciliation and derivation DAG

## Goal
Reuse valid evidence across small edits without false identity reuse and invalidate dependent derivatives exactly.

## Requirements
Deterministic conservative matching with bounded structural context; ambiguity creates new evidence. Derivations bind exact input digests, generator/version/config/model/prompt identities and states CURRENT/STALE/FAILED/SUPERSEDED. Publication is transactional, cycle-safe, idempotent and restartable. A→B→A can converge to immutable prior artifacts.

## Evidence
Synthetic edit corpus with precision/recall and explicit zero-tolerance false-reuse safety gate; crash/cancel tests; migration and concurrency tests.
