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

Test-first clarification: receipt identities include actual provider cache-hit diagnostics. Equal selected evidence is required across cold/warm paths; receipt equality is asserted only for equal complete audit facts. The wording was corrected before implementation to preserve truthful diagnostics rather than hiding cache behavior. Existing identity algorithms and historical replay remain unchanged.

## Implementation and regression evidence

MCP holds one `(EstimatorIdentity, ContextCompilerService)` slot. The ordinary request error path clears it for semantic compilation, including post-dispatch deadline, cancellation and response-limit rejection; lexical/unrelated errors leave it alone. The E5 worker validates existing count/UTF-8 bounds, checks duplicate/cached object bodies, keeps only unique requested objects and one prepared selection with exact limits and total text bytes. Overlap is retained; direct scoring clears prepared handles. Parent prepared scoring rejects query-plus-corpus byte overflow before IPC.

Red/green commands (all offline, model-free):

- `uv run --no-sync pytest tests/integration/test_mcp_semantic_session.py --no-cov -q`: 17 failures before production edits; final expanded suite 18 passed.
- `uv run --no-sync pytest --no-cov tests/unit/test_e5_worker_selection.py --tb=no -o addopts=''`: initially 20 failed / 11 passed before edits.
- `uv run --no-sync pytest --no-cov tests/unit/test_e5_semantic.py::test_prepared_query_combined_byte_limit_fails_before_worker --tb=short -o addopts=''`: failed before correction.
- `uv run --no-sync pytest --no-cov tests/unit/test_e5_worker_selection.py tests/unit/test_e5_semantic.py tests/security/test_semantic_retrieval_boundaries.py tests/unit/test_semantic_retrieval.py --tb=short -o addopts=''`: expanded worker/parent/domain/boundary suite 68 passed in 0.31 s.

The isolated red/green worker invocations override pytest addopts but import only synthetic dependencies; the authoritative complete suite runs with the configured socket-denial and branch-coverage gates. The worker tests exercise actual request functions and dispatch, not model quality or numeric inference. Warm MCP tampering tests cover CAS body, reference mapping and a structurally valid projection with changed sensitivity; failures are body-free and a restored source prepares afresh.

`uv sync --locked --all-extras` completed successfully. `uv run --locked ruff check .`, `uv run --locked ruff format --check .` (422 files), `uv run --locked mypy src` (129 source files), `uv run --locked python scripts/audit_maintainability.py`, `uv run --no-sync python scripts/audit_ci.py audit`, `uv run --no-sync pre-commit validate-config`, and `uv build` passed. Final suite and governance results follow below; remote CI remains the delivery gate.

## Independent convergence and durable design

Independent read-only convergence found zero implementation gaps and zero critical/high findings across all 8 functional requirements, 4 success criteria and 8 acceptance scenarios. No gap tasks were required. The review independently ran:

```bash
uv run --locked pytest --no-cov tests/integration/test_mcp_semantic_session.py tests/integration/test_mcp_semantic_context.py tests/integration/test_semantic_candidates.py tests/unit/test_e5_worker_selection.py tests/unit/test_e5_semantic.py tests/security/test_semantic_retrieval_boundaries.py tests/security/test_semantic_product_surface_boundaries.py tests/unit/test_semantic_product_surface.py tests/unit/test_semantic_retrieval.py
```

Result: 104 passed in 3.81 s, with the configured socket denial. Code convergence is complete; final merge remains conditional on the complete suite/coverage, compacted governance and required platform CI.

The selected design uses no LRU, disk cache or multi-estimator compiler map: these would retain obsolete state without a demonstrated need. `SemanticRetrievalLimits` already requires `max_cache_entries >= max_passages`; retaining at most the requested unique objects therefore preserves the cache bound. Every prepared selection records exact limits and total UTF-8 bytes. Domain state, source originals, public schemas, provider recipe and selection identities are unchanged. No model-quality, speed, portability timing or human-value claim follows from these synthetic lifecycle checks.

After code convergence, unique planning decisions and validation are retained here and in `spec.md` and the private lifecycle contract. The full specify/plan/tasks/checklist history is committed before removing transient files, as required by repository governance. No external corpus/model result was regenerated. Rollback is a code revert with process restart; no data migration is needed. Scope churn intentionally gives up reuse of evicted vectors to keep session memory bounded.

The archived original real-stdio probe was rerun after implementation: two successful tool responses, one compiler, one preparation and two provider scoring calls, matching the direct compiler-lifetime baseline (previously two compilers and two preparations).

## Final local gates

`uv run --locked pytest` executed the complete suite: 1,846 passed, 4 skipped, one stale milestone-locator assertion failed in 314.51 s; branch coverage 85.52% exceeds the unchanged 85% gate. The sole failure expected F036 in `.specify/feature.json` even though F037 is now active. Its expected locator was updated to F037 (no product code change). `uv run --locked pytest --lf --cov-append --cov-report=term:skip-covered` then passed the one failed test, preserving full-suite coverage at 85.52%. Thus all 1,847 non-skipped cases were exercised successfully across the complete run and narrow correction rerun. CI will run the full suite once against the final tree.

`uv run --locked python scripts/validate_repository.py` and `git diff --check` pass after compaction. `git diff e8268f0 --name-only -- benchmarks corpora schemas uv.lock pyproject.toml` is empty. Required Linux/macOS/Windows CI must all succeed for the exact PR head before merge; its checks are the authoritative delivery record. The merge must preserve the planning commits so removed lifecycle files remain recoverable in Git history.

## Verified delivery

[PR #48](https://github.com/Noetheon/OpenARDP/pull/48) merged on 2026-09-19 as `4504cbd469db7b7c30f06f0655a2e39da8e02322` after Preflight and complete Linux/macOS/Windows checks succeeded for exact head `70aa27a7f1b3c0f82f312a12a4e6934aa41b7e15` ([CI run](https://github.com/Noetheon/OpenARDP/actions/runs/35420328064)). Local `main` and remote `main` matched, the worktree was clean and the merged tree equalled the tested PR head. The merge commit retains both planning and compaction history.
