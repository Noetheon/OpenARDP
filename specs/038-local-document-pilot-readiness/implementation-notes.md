# F038 implementation notes

Risk tier: high-assurance. Acceptance: explicit readable source-backed bundles, unchanged default/JSON and retrieval, a verified practical guide, a preregisterable manual three-arm pilot with pending judgments and no invented evidence, a bounded GO/pause decision, canonical focus freeze and full quality gates. Implementation in progress. F037 merged with all platform checks green before this branch began.

No new dependency, persisted format, public schema or architectural ADR trigger. Decisions, test-first results, smoke evidence, independent reviews, compaction and exact gates will be recorded here.

## Pre-implementation analysis corrections

Independent analysis reproduced that the existing human `safe_text` helper retains DEL, C1 and bidi controls, conflicting with the proposed broad output guarantee. Scope was explicitly amended before implementation for narrowly enumerated shared escaping (C0/DEL/C1 plus U+061C, U+200E–U+200F, U+202A–U+202E and U+2066–U+2069), with normal Unicode/umlaut preservation and focused tests. JSON and stored evidence remain unchanged. Manual verdict state names were aligned with the normative protocol. Multiple submitted final outputs now have an exact Q/S selection rule; earlier source/version incidents still block GO, and assigned-attempt retries cannot reset the 20-minute cumulative task cap.

Independent recheck closed all three findings: 8 FR and 4 SC mapped to 10 tasks, zero unresolved critical/high/medium findings. Full specify/clarify/plan/checklist/tasks/analyze completed before runtime/template changes.

## Implemented workflow and test-first evidence

`src/openardp/interfaces/cli_output.py` now renders an explicitly included context bundle in the existing human CLI. It prints ordered excerpts or deterministic structured JSON, actual block/source locators or rich projection/reference identities, optional existing handles, and explicit empty selections. It neither generates answers nor fetches new content. The bounded shared escaper preserves normal Unicode while escaping the agreed terminal/bidi control ranges. Default context still omits bodies; JSON, original files and receipt bytes remain unchanged.

The seven new cases in `tests/integration/test_cli_context_output.py` all failed before the product patch, then all passed:

```bash
uv run --no-sync pytest tests/integration/test_cli_context_output.py --no-cov -q
uv run --no-sync pytest tests/integration/test_cli_context_output.py tests/integration/test_cli_context.py tests/integration/test_cli_semantic_context.py --no-cov -q
uv run --no-sync ruff check src/openardp/interfaces/cli_output.py tests/integration/test_cli_context_output.py
uv run --no-sync ruff format --check src/openardp/interfaces/cli_output.py tests/integration/test_cli_context_output.py
uv run --no-sync mypy src/openardp/interfaces/cli_output.py
```

The combined focused run passed all 27 cases with the repository's default socket prohibition retained. Targeted lint/format/type checks passed. No public schema, persisted identity, dependency, provider recipe or retrieval-selection rule changed.

## Exact guide smoke

On 2026-09-19, all four Bash blocks from `docs/30_LOCAL_DOCUMENT_WORKFLOW.md` were extracted verbatim and executed sequentially by `zsh` with `set -eu` and a separate fresh `UV_PROJECT_ENVIRONMENT`, to avoid changing the contributor all-extras environment. `uv sync --locked` succeeded for the core environment. The synthetic workspace was a new home-directory child with sibling source/store directories. The script exited 0: initial ingest succeeded; second ingest reported `CACHE_HIT` with two blocks; list resolved the original source; status reported `CURRENT` and `FULL`; explicit human/JSON contexts returned the review-date passage with source lines 3–4; `get`, receipt inspection and replay succeeded. The original and final SHA-256 both equal `64603e817a22f16ce6b8a2483eaa7e6fa400d66d2378782bae3950b9c580c202`. Creation and replay printed the same receipt and bundle IDs. This is synthetic functional verification only, not a real pilot, time-saving result or adoption evidence.

## Prospective records and claim boundaries

`pilots/local-document/v0.1.0/` contains five header-only CSVs (tasks, attempts, overhead, reviews, repeat use), private-run instructions and an entirely pending decision. The normative protocol remains in `contracts/pilot-protocol.md`. Every gate has an explicit field/evidence route, including failed/rescued trials, cumulative per-task time, independent blinded source/claim checks, earlier erroneous final claims, both baselines, setup allocations, readiness effort, voluntary repeat use and both stop caps. Numeric unknowns never default to zero. Actual source data and filled records belong outside Git.

Canonical README, product/vision/roadmap/benchmark documents and feature map now restrict continued investment to demonstrating one recurring local-document workflow. New GUI/HTTP/provider/connector/format/standardization expansion is paused; necessary maintenance remains possible. Historical answer-word substring labels and fixed source-fitness rubrics are explicitly distinguished from verified human answer quality. Frozen evaluators, corpora, benchmark artifacts, schemas and dependencies remain byte-identical. The existing release NO-GO is unchanged. No real tasks, real timing, independent user reviews or returning external users are claimed.

## Design decisions and independent convergence

The small formatter uses existing runtime models only. Rich identifiers are navigation references rather than fabricated page locations; callers inspect authoritative anchors with `get-evidence`. Matching 30 distinct genuine tasks into ten triplets avoids asking one person the same question three times after learning the answer. Ten observations per arm, approximate matching and learning/fatigue remain material limits. The 30%, 9/10 and 7/10 thresholds are prospective investment heuristics, not scientifically validated thresholds or a commercial forecast. Decision states are `awaiting_real_tasks`, `in_progress`, `pending_review`, `confirmed_limited_go`, and `pause_expansion`; freezing inputs is a prerequisite, not a favorable verdict.

Independent convergence inspected all 8 functional requirements, 4 buildable success criteria, both user workflows, the bounded design and governing trust/claim rules. No critical/high/medium implementation, protocol, template or guide gaps were found, and no new gap tasks were needed. The reviewer independently ran:

```bash
uv run --locked pytest --no-cov tests/integration/test_cli_context_output.py tests/integration/test_cli_context.py tests/integration/test_cli_semantic_context.py tests/security/test_semantic_product_surface_boundaries.py
```

All 30 tests passed in 2.38 seconds with the configured socket prohibition. The root's subsequent complete guide smoke passed as recorded above. `check-prerequisites.sh --json --require-tasks --include-tasks` resolved the full F038 lifecycle before compaction. Required final full-suite/coverage and remote CI remain delivery gates, not unimplemented product scope.

Local `uv run --locked ruff check .`, `uv run --locked ruff format --check .` (423 files), `uv run --locked mypy src` (129 source files), `uv run --locked python scripts/audit_maintainability.py`, `uv run --locked python scripts/audit_ci.py audit`, `uv run --locked pre-commit validate-config`, and `uv build` all passed. The wheel and source distribution built successfully. `git diff 4504cbd --name-only -- benchmarks corpora schemas uv.lock pyproject.toml scripts/semantic_e2e_benchmark.py scripts/retrieval_holdout.py` was empty. Full suite/coverage and final governance follow lifecycle compaction; CI must succeed before merge.
