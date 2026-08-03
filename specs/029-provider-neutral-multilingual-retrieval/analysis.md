# Analysis: Provider-Neutral Multilingual Retrieval

## Pre-implementation review

- Scope matches the authoritative F029 feature map and does not add generation, vector persistence, cloud defaults or a
  schema/catalog migration.
- ADR 0003 already makes embeddings optional/model-specific; ADR 0019 fixes the immediate provider/runtime/cache boundary.
- F025 ground truth is immutable, F027 remains the paired/default baseline and F028 supplies CSV without conversion.
- Every provider input comes from a verified exact snapshot; provider scores remain disposable and cannot create evidence.
- The real model is absent from ordinary tests/CI; fake providers exhaust contract/security behavior offline.

No unresolved critical or high-severity contradiction blocks test-first implementation. The binding threshold is frozen
before execution and may produce a negative result.

## Post-implementation review

- The implementation remains additive: the lexical F027 profile is still the default, semantic dependencies are optional,
  and no schema, catalog migration, vector persistence or cloud runtime was introduced.
- Exact snapshot/CAS verification precedes provider scoring. The provider worker is spawned, socket-denied, offline,
  revision-bound and limited by text, batch, token, response, timeout and cache bounds.
- FTS paging now discovers more than one hundred deterministic lexical matches without unbounded materialization; lexical
  minimum-relevant evidence remains the first allocation tier and semantic candidates only augment it.
- The committed v0.1.0 and v0.2.0 negative results explain the source-balance and projection-precedence defects. v0.3.0
  changes only RichEvidence precedence, passes the frozen multilingual/non-regression gates and preserves every prior row.
- The result validator is standard-library-only and independently recomputes identities, metrics, decision and body/path/
  vector exclusions without importing OpenARDP or a provider runtime.

No unresolved critical or high-severity contradiction remains. The final staged-tree snapshot passed Ruff lint/format,
strict mypy over 106 source modules, the full no-network pytest/pre-commit gate at 85.24% branch coverage, repository and
release-evidence validation, all three independent provider-result validators, and wheel/sdist construction. The exact
real E5 bundle also passed its opt-in socket-blocked integration test after the worker refactor. F029 is converged; only
independent commit and GitHub publication remain.
