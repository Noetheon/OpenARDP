# Implementation Notes: Repository Hygiene and Maintainability

## Acceptance criteria restatement

F018 is complete only when three measured orchestration hotspots are reduced by at least 40 percent without changing
their black-box behavior; a deterministic standard-library maintainability policy rejects new/growing debt; focused
commands pass independently while the full suite retains socket blocking and 85 percent branch coverage; project status
and governance agree; and every local plus cross-platform gate passes.

The feature may not change public schemas, canonical identities, migration history, application `0.1.0rc1`, workspace
revision 10, provider/export profiles, the F015 release `NO-GO`, the F017 production Graph `NO-GO`, runtime dependencies,
network defaults or original/frozen evidence.

## Starting point

- Base: merged private `origin/main` commit `8fa38524e79235c3f36348dd17af743af7c9ea8a`.
- Branch: `codex/f018-repository-hygiene`.
- The user's original `/Users/umutgoksular/Documents/OpenARDP` F006 worktree remains untouched.
- Initial source inventory: 81 modules, 39,392 lines, 1,401 functions and 557 classes.
- Initial hotspot spans: `evaluate_release` 327 lines, `_execute` 248 lines,
  `reconcile_watch_scan` 291 lines.
- Largest residual module: `src/openardp/adapters/sqlite_catalog.py` at 6,761 lines.
- Optional diagnostic Ruff complexity sweep: 184 findings; this is not the configured gate and is not represented as
  resolved by F018.
- Configured baseline: Ruff PASS; format PASS for 240 files; strict mypy PASS for 81 source files; `uv lock --check`
  PASS; repository validation PASS; tracked generated/cache artifacts zero.
- Reproduced F017 quickstart defect: 29 tests passed, but the partial command exited non-zero at 21.93 percent package
  coverage because the repository-wide 85 percent threshold was inherited.

## Test-first evidence

- `uv run --locked pytest --no-cov tests/unit/test_maintainability_audit.py tests/test_repository_contract.py -q`
  initially failed during collection with `ModuleNotFoundError: No module named
  'scripts.audit_maintainability'`, proving the guard tests preceded implementation.
- The implemented audit unit set passes 5 tests, including duplicate-key, unsafe-path,
  growth, stale-exception and deterministic-order cases.
- Release, CLI and watcher characterization was added before source extraction. The
  combined pre-refactor set passed 40 tests.
- Post-extraction targeted results: release 5 passed, broader CLI 71 passed and broader
  watcher 70 passed.

## Implementation evidence

- Added a strict standard-library AST audit and explicit monotonic policy. Repository
  validation invokes it without importing product code; two consecutive invocations
  emitted the identical line `Maintainability audit passed.`
- Extracted typed, documented stages inside the existing owners. Measured function spans
  are `evaluate_release` 327→43 (86.9%), CLI `_execute` 248→18 (92.7%) and
  `SQLiteCatalog.reconcile_watch_scan` 291→33 (88.7%). Every extracted owning helper is
  below 100 lines.
- Final structural inventory before gate execution: 81 modules, 39,697 lines, 1,424
  functions/methods and 559 classes. The 305-line increase is intentional explicit
  structure, not represented as size reduction.
- Corrected focused commands all exit zero: F010 2/45/24, F014 44, F015 24, F016 25,
  F017 29 and F018 47 passed test executions. Counts may overlap. The full-suite socket
  block and 85 percent branch gate remain configured and separate.
- No schema, migration, `pyproject.toml`, `uv.lock`, application version, frozen release
  evidence or identity algorithm changed. `git ls-files` reports no tracked generated or
  cache state.

## Final gates

- Focused F018 behavior suite: 47 passed in 12.00 seconds.
- Repository contract/validator suite: 45 passed in 0.97 seconds.
- `uv lock --check`: PASS; 143 locked packages resolved without mutation.
- `uv run --locked ruff check .`: PASS.
- `uv run --locked ruff format --check .`: PASS; 242 files already formatted.
- `uv run --locked mypy src`: PASS; 81 source files.
- `uv run --locked pytest`: PASS; 1,381 tests in 148.85 seconds with 85.33%
  branch-aware coverage, above the enforced 85% threshold.
- Maintainability audit twice, repository validation and `git diff --check`: PASS.
- `uv build --out-dir .f018-build`: PASS; candidate wheel and sdist rebuilt from
  source distribution.
- Bounded artifact inspection: PASS; wheel 87 members/360,164 bytes and sdist 93
  members/309,816 bytes, both structurally safe. Wheel member-inventory identity
  `sha256:2336c0aa3dc8365ad3cf098e9589debb7d15df62b955e966f8560ece21d127de`;
  sdist member-inventory identity
  `sha256:4ac1adca4cab4e884af109d3b0af8abccb130686afc95e31ce55eb3573e61f05`.
- `uv run --locked pre-commit run --all-files`: PASS; Ruff lint, Ruff format,
  strict mypy and the complete network-blocked coverage suite all passed.
- Final Spec Kit convergence reconciled 15/15 functional requirements, 8/8 success
  criteria, 3/3 user stories, both complete checklists and all local implementation
  tasks. It found no corrective gap and appended no task.
- Publication: private repository `Noetheon/OpenARDP`, branch
  `codex/f018-repository-hygiene`, PR `#23`. Immutable final PR and post-merge workflow
  conclusions are recorded in the PR discussion after GitHub completes them.

## Tradeoffs and residual risk

The complete SQLite catalog remains an explicit legacy hotspot; a mixin/framework split is outside F018 because it
would move coupling without changing behavior or ownership. Five modules and 21 functions remain reviewed policy
exceptions. An optional baseline Ruff complexity sweep found 184 non-gating diagnostics; a focused post-extraction sweep
still finds 16 in the three owning modules, but none on the three selected top-level orchestration functions. F018 makes
no unsupported whole-codebase-cleanliness claim.

## Rollback

Revert the single F018 commit. No database migration, public artifact, identifier or external state requires reversal.
