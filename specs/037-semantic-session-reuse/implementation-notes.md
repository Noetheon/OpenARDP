# F037 implementation notes

Risk tier: high-assurance (provider execution and disposable-cache lifecycle). Implementation in progress.

Acceptance: one active semantic MCP compiler per exact estimator; unchanged requests prepare once; scope/estimator
changes prepare safely; every delivered body remains authoritative; failed compiles drop the slot; provider state
retains only current unique objects and one limit-bound handle; invalid requests fail before mutation; legacy scoring
cannot exhaust cache cumulatively; no identity/policy/schema/frozen-evidence change; all mandatory gates pass.

Existing ADR 0019 governs the correction. No architectural replacement or new persisted format is introduced.
Validation commands, red/green results, convergence, delivery, tradeoffs and rollback will be recorded here.

## Pre-implementation analysis

Full specify/clarify/plan/checklist/tasks/analyze sequence completed on 2026-09-19. Independent read-only analysis found a high test-coverage gap: existing semantic candidate tests did not establish warm MCP rejection of CAS/catalog tampering. T004 was amended to add both real-dispatch regressions. The A-B-A deterministic corpus-ID lifecycle was clarified. Recheck: 12/12 functional/buildable success requirements mapped, zero unresolved critical/high/medium findings. No new ADR or compatibility revision required.

Repository preflight currently rejects transient lifecycle files until final compaction (GOV028); retain them through convergence, commit their history and then migrate durable content. A pre-existing ignored root `.DS_Store` also triggered GOV009; it was moved unchanged to the external audit-artifact backup rather than weakening the validator.
