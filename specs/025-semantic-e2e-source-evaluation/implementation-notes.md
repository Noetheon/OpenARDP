# Implementation Notes: Semantic End-to-End Source Evaluation

**Feature**: `025-semantic-e2e-source-evaluation`

**Branch**: `codex/f025-semantic-e2e-source-evaluation`

**Date**: 2026-08-02

## Restated acceptance criteria

1. Freeze realistic questions, exact support atoms, source roles and thresholds before a binding result.
2. Measure untouched questions separately from frozen human lexical assistance.
3. Run exact product ingestion, catalog/CAS persistence, lexical candidates and context compilation offline.
4. Re-resolve every selected citation and retain irrelevant, unsupported and unanswerable failures.
5. Keep CSV an explicit unsupported product format and never substitute a benchmark conversion.
6. Require two fresh executions with identical non-timing judgments.
7. Recompute the complete result through a standard-library validator independent of producer/evaluator imports.
8. Publish an honest READY, CONDITIONAL or NOT_READY decision without post-run threshold changes.

## Frozen inputs

- Corpus ID: `sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd`.
- Question-set ID: `sha256:e251354b95bcd59d68604cd4a1cf0a5e2300dabdf8145844e2e2a0bb5703bdce`.
- Protocol ID: `sha256:8182f5d410292529b3ae35c0bfe3e07f674fc2e3c02b78406073c8890d924ad8`.
- Nineteen questions, 46 required atoms, six strata, English/German and all six format/coverage states.
- Product limits: exact mode, 262,144-byte budget, five scopes and 64 candidates.

One pre-binding oracle correction changed Q09's exact variant from plural `ML Engineers` to the parser's retained
singular `ML Engineer`. This was discovered by exact source/projection inspection before any accepted product result and
changed the question-set identity. No question, operator term or policy threshold changed after the binding run.

## Harness findings before binding

The first incomplete attempt exposed quadratic benchmark code: calling rich evidence `get` once per projection
reloaded and validated the complete PDF bundle each time. The harness now loads one accepted aggregate, performs one
complete representation verification and linearly reads each exact CAS object. A later diagnostic run showed that text
context items contain the verified text body rather than a serialized `ContentBlock`; the citation comparison was fixed
and locked by a product-path integration test. Neither issue changed product retrieval behavior or favorable/unfavorable
atom judgments.

The 256 KiB/64-candidate limits were frozen before the first complete binding result to bound selection serialization
and reflect a usable context handoff. They are shared by both product treatments.

## Binding result

The accepted two-workspace execution took 241,417,797,959 ns and independently validates as
`SEMANTIC_E2E_NOT_READY`. Run ID:
`sha256:731270a1f442f62afe96e6815aa822187434b461cb2e84dee5c20b9a8398eddb`.

- Direct: 6/17 full support, 15/46 atom recall, 1.1029% evidence precision, 28.8622% MRR, 50% source recall,
  100% citation integrity, 0% unsupported abstention and 0% German atom recall.
- Operator: 14/17 full support, 40/46 atom recall, 5.0704% precision, 78.9661% MRR, 16/18 source recall,
  100% citation integrity, 0% unsupported abstention and 100% German atom recall.
- Five supported formats ingested; Q15/Q16 remain explicit CSV `unsupported_format` rows.
- Every semantic row/identity matched across both fresh workspaces. There were zero hard execution failures.

The operator treatment misses conditional gates by 2/46 atoms and 2/18 expected source instances. Direct retrieval is
well below the 40% conditional full-support floor and selects irrelevant evidence for both unsupported questions.
Accordingly, no conditional label is justified.

## Interpretation and remaining risk

The result validates the local evidence and citation substrate while falsifying semantic readiness of the current exact
lexical OR selector on this corpus. It does not invalidate exact navigation, reuse, structural parsing or operator-led
workflows. It does justify separately governed work on abstention, ranking/diversity, CSV coverage and optional
provider-neutral semantic retrieval. The benchmark remains small and diagnostic; no population-wide accuracy claim is
made.

GitHub Actions runner allocation is presently blocked by the account billing state observed after F024. Local gates
remain mandatory; branch protection will not be weakened and remote status will be recorded separately.

## Local convergence evidence

The binding result and committed copy independently validate as `SEMANTIC_E2E_NOT_READY`; input-only validation also
passes. Focused F025 tests pass, with the actual-corpus rerun intentionally opt-in. In a clean staged-tree worktree:

- `uv run ruff check .` and `uv run ruff format --check .` passed across 320 formatted files;
- `uv run mypy src` and `uv run mypy src --platform win32` each passed 91 source files;
- `uv run pytest` passed 1,569 tests, skipped three explicit opt-in tests and reached 85.24% coverage;
- repository validation, result/input validation, `uv build` and `git diff --check` passed;
- `uv run pre-commit run --all-files` passed every hook, including the repeated full no-network pytest gate.

The primary worktree contains user-owned untracked files ending in ` 2.py`/` 2.md`. They were neither changed nor staged;
the clean staged-tree run prevents those unrelated duplicates from corrupting binding gate evidence.

## Private publication status

Implementation commit `89063bba223fdc138256b27ac914af97f5a002ee` was pushed to the private repository and opened
as PR #33. GitHub Actions run `30764275869` rejected Preflight before runner allocation: runner ID is zero, there are no
steps and the exact annotation states that recent account payments failed or the spending limit needs increasing. The
Ubuntu, macOS and Windows quality jobs were consequently skipped. This is external billing evidence, not a failed code
step, and the run was not retried or bypassed. Branch protection remains unchanged; merge task T072 is pending until the
required remote check can actually run.
