# Implementation Notes: F031 Repository Hygiene and Bounded Refactoring

## Acceptance criteria restatement

F031 is complete only when the repository contains no sync-conflict artifact, a deterministic read-only audit prevents
silent recurrence, four selected oversized functions lose their policy exceptions with behavior preserved, and all ten
SC-001–SC-010 gates pass. The feature does not claim to eliminate unselected legacy complexity.

## Frozen baseline

- Base commit: `658e3ae60fced4131fb807dfdeb6e02dfeabb489` (merged PR #32 head).
- Feature branch: `codex/f031-repository-hygiene`.
- Remote baseline: `origin/main`; no open pull request at feature start.
- Clean validation worktree: `/tmp/openardp-f031-baseline`, detached at the base commit.
- Locked environment: `uv sync --locked --all-extras` passed in the clean baseline worktree.
- Production baseline: 107 Python modules, 46,342 lines and 1,650 functions.
- Maintainability baseline: five module exceptions and 21 function exceptions; audit passed.
- Optional Ruff baseline: 61 C901, 26 PLR0912 and 17 PLR0915 findings.
- Selected measured function spans: `_parser` 270, `_success` 166, `_parse_markdown` 173 and
  `LocalWatchScanner.scan` 118; combined baseline 727.

## Pre-clean inventory

The initial read-only inventory found 151 untracked worktree paths matching a numbered sync-conflict-copy pattern. Every
candidate had a canonical tracked counterpart:

- 146 candidates were byte-identical to the canonical file.
- Five candidates differed and were demonstrably older Spec-Kit states: four under
  `specs/021-incremental-freshness/` and one `specs/024-redistributable-realworld-corpus/tasks 2.md` copy. Canonical files
  contained the later completed tasks/evidence; no unique newer requirement existed in a copy.
- Zero candidates lacked a canonical counterpart; zero candidates were outside the narrow pattern.
- Four inactive `.git/index N` copies (`index 2` through `index 5`) existed. The active `.git/index` remained distinct
  and outside cleanup scope.

This evidence authorizes no generic glob deletion. T017 must recompute it with the implemented audit and direct canonical
comparison immediately before T018.

## Planning and analysis commands

```bash
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
.specify/scripts/bash/setup-plan.sh --json
.specify/scripts/bash/setup-tasks.sh --json
rg -n '<placeholder patterns>' specs/031-repository-hygiene
rg -n '^[-*] \\[ \\] T[0-9]{3}' specs/031-repository-hygiene/tasks.md
```

Result: specification, clarification, plan, research, model, contract, checklists, 44 tasks and cross-artifact analysis
complete; no unresolved critical/high finding and no ADR trigger.

## Implementation evidence

### Repository audit and cleanup

- Added `scripts/audit_repository_hygiene.py`, a standard-library, Git-aware, read-only audit with deterministic,
  body-free SHA-256 findings and no repair flag.
- Seven synthetic unit tests cover clean, tracked-numbered, identical, divergent, missing-canonical, symlink,
  mutation-free, active/inactive index, loose-ref, linked-worktree and invalid-root behavior.
- The immediate pre-clean audit reproduced exactly 146 `identical`, five `divergent` and four `git_metadata_copy`
  findings. Direct diffs proved each divergent copy was an older state: F021 test/evidence counts, Windows-race notes,
  convergence wording/task completion and F024 task completion were all newer in canonical tracked files.
- `git clean -n -f -- <151 exact paths>` previewed exactly 151 paths. The matching exact cleanup removed those paths;
  four explicitly named `.git/index N` copies were then unlinked. No glob or unrelated untracked path was removed.
- The active `.git/index` SHA-256 was identical before and after cleanup; the post-clean audit passed, `git fsck --full
  --no-dangling` exited zero and the remaining untracked paths were exclusively intentional F031 files.

### Bounded refactoring

- CLI argument construction moved into bounded command groups in `interfaces/cli_arguments.py`; stable `cli._parser`
  remains the callable seam. Human/JSON output moved into `interfaces/cli_output.py`; stable `_success`, `_json_value` and
  `_write_json` seams remain available where previously exercised.
- Markdown parsing now delegates to explicit fence, ATX, Setext, list, quote, heading and paragraph transitions in the
  same adapter module. A new mixed empty-construct/list-transition characterization locks warning and grouping behavior.
- Local-watch scanning now separates bounded tree traversal, single-directory enumeration and entry projection while
  preserving immediate overflow, fresh-stat, race, link and all-or-nothing semantics.
- Focused evidence: 83 CLI/MCP tests, 42 parser/ingestion/search/semantic tests and 55 watcher contract/integration tests
  passed with `--no-cov`; the authoritative coverage result remains the pending full-suite gate.

### Maintainability result

| Original hotspot seam | Baseline | Final owner span | Reduction |
|---|---:|---:|---:|
| CLI `_parser` → `cli_arguments.parser` | 270 | 18 | 93.33% |
| CLI `_success` → `cli_output.success` | 166 | 22 | 86.75% |
| `TextParserAdapter._parse_markdown` | 173 | 6 | 96.53% |
| `LocalWatchScanner.scan` | 118 | 32 | 72.88% |
| **Combined** | **727** | **78** | **89.27%** |

All four function exceptions were removed. `interfaces/cli.py` fell from 1,896 to 1,380 lines and its reviewed ceiling
was tightened from 1,934 to 1,380. The two cohesive interface modules are 296 and 248 lines; no new module or function
exception was added. The maintainability audit, Ruff and strict mypy pass.

The complete production inventory changed from 107 modules / 46,342 lines / 1,650 functions / 641 classes to 109 modules
/ 46,450 lines / 1,679 functions / 643 classes. The 108-line increase is disclosed: explicit typed helpers and docstrings
replace compressed branching. Optional Ruff source-only findings improved from C901 61 / PLR0912 26 / PLR0915 17 to
58 / 23 / 13; this is supporting evidence, not a claim that all complexity is gone.

## Final local validation commands

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/audit_maintainability.py . --policy quality/maintainability-policy.json
uv run python scripts/audit_repository_hygiene.py --root .
uv run python scripts/validate_repository.py
uv run pytest
uv build
uv run pre-commit run --all-files
git diff --check
git fsck --full --no-dangling
```

Results: locked resolution checked 121 packages; Ruff and formatting passed; strict mypy passed for 109 source files;
both audits and repository validation passed; 1,729 tests passed, four existing optional/platform cases skipped, and
branch coverage was 85.47 percent in 181.17 seconds; sdist/wheel build and every pre-commit hook passed; Git whitespace
and object-graph checks passed. An exploratory `uv run python -m build` correctly failed because the undeclared `build`
package is absent; the repository-authoritative `uv build` command then passed and is the documented command.

## Ten-gate scorecard

| Score | Criterion | Status | Evidence |
|---:|---|---|---|
| 1 | Repository integrity (SC-001) | PASS | Zero findings; active index stable; `git fsck` passed |
| 2 | Safe recurrence detection (SC-002) | PASS | Seven synthetic audit tests plus validator composition |
| 3 | Maintainability reduction (SC-003) | PASS | 727 → 78 lines; four exceptions removed |
| 4 | Behavioral equivalence (SC-004) | PASS | Focused slices and complete suite passed |
| 5 | Static quality (SC-005) | PASS | Ruff, format, strict mypy and policy audits passed |
| 6 | Full offline tests and coverage (SC-006) | PASS | 1,729 passed; 85.47% branch coverage |
| 7 | Reproducible validation/build/drift (SC-007) | PASS | Validator, `uv build` and pre-commit passed |
| 8 | Linux/macOS/Windows CI (SC-008) | PENDING | — |
| 9 | Documentation truth (SC-009) | PASS | Architecture, hygiene, roadmap, changelog and evidence agree |
| 10 | Merge and branch hygiene (SC-010) | PENDING | — |

**Current score**: 8/10 locally. The feature must not claim 10/10 until exact-SHA cross-platform CI and normal merge/branch
cleanup supply gates 8 and 10.

## Tradeoffs and residual risks

The CLI split adds two small private modules and explicit delegation; this is more files and 108 net production lines in
exchange for isolated ownership and 649 fewer lines in the four original owner spans. The legacy SQLite facade,
append-only migration history, five module exceptions and other reviewed function exceptions remain debt. Workspace
relocation out of a synchronized directory remains a user operational choice, not an F031 mutation. The audit detects
future conflicts but intentionally does not delete or infer whether divergent content is obsolete.

## Rollback

Revert the bounded F031 change set, then run the complete locked gate. No schema, migration, persisted object or provider
operation requires reversal. Verified redundant local sync copies are intentionally not reconstructed because canonical
tracked files remain authoritative; if unique future copies are found, preserve them independently before any rollback.
