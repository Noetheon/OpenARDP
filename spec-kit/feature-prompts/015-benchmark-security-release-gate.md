# Feature 015 — Benchmark, security and v0.1 release gate

## Goal
Produce reproducible evidence and a genuine go/no-go release decision.

## Baselines
Raw reparsing; persisted DoclingDocument; persisted DoclingDocument plus Docling retrieval; OpenARDP retrieval; OpenARDP compiler.

## Required suites
Performance/cache/update/storage; anchor and retrieval correctness; budget/quality evaluation with confidence intervals; stale/reconciliation safety; prompt-injection fixtures; malformed parser isolation; privacy/log-redaction; dependency/license/SBOM review; fresh install, previous-version upgrade, backup/restore and supported-platform reproduction.

## Release gate
Machine/human report, traceable README claims, residual risks, support matrix and rollback instructions. NO-GO is mandatory when distinct operational value, safety gates or reproducibility are not demonstrated.
