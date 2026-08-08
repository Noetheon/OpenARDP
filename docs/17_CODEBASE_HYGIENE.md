# Codebase hygiene and maintainability baseline

## Feature 031 measured refresh

Feature 031 extends the historical F018 baseline after F030. It addresses a concrete local synchronization failure mode
and four measured function hotspots without changing public behavior, storage, schemas, identities or dependencies.

The read-only [`scripts/audit_repository_hygiene.py`](../scripts/audit_repository_hygiene.py) begins with Git ownership
facts. It inspects only untracked numbered conflict-copy names and explicitly scoped inactive Git index/loose-ref copies,
compares safe regular files with SHA-256 and emits relative metadata without bodies. It has no deletion flag. Tracked
numbered filenames and unrelated untracked files are ignored; missing canonical files, divergent content, links and
unsafe objects fail closed for review.

The 2026-08-08 recovery found 151 worktree copies with tracked canonical counterparts: 146 byte-identical and five older
Spec-Kit states. Four `.git/index N` conflict copies were inactive. After exact-path preview and removal, the active index
hash was unchanged, the audit reported zero findings and `git fsck --full --no-dangling` passed. This evidence does not
authorize deleting future matches without a fresh review.

### Preventing recurrence

- Exclude active development repositories, especially their hidden `.git` directories, from file synchronization. The
  most robust option is a non-synchronized development root; moving this repository remains an explicit user operation.
- Run `uv run python scripts/audit_repository_hygiene.py --root .` before trusting a suspicious worktree and as part of
  normal repository validation.
- If a finding is `divergent`, `missing_canonical` or `unsafe`, preserve it. Compare it with Git history/canonical content
  and quarantine unique work outside the repository before any repair.
- Never repair invalid refs with a broad glob, `git clean -fdx`, reset or automatic deletion. Identify the exact inactive
  path, preserve the active index/ref, preview exact candidates and finish with the audit plus `git fsck`.

### F031 maintainability result

| Original hotspot seam | Baseline span | Final owner span | Reduction |
|---|---:|---:|---:|
| CLI `_parser` | 270 | 18 | 93.33% |
| CLI `_success` | 166 | 22 | 86.75% |
| `TextParserAdapter._parse_markdown` | 173 | 6 | 96.53% |
| `LocalWatchScanner.scan` | 118 | 32 | 72.88% |
| **Combined** | **727** | **78** | **89.27%** |

CLI grammar and output now have bounded interface-owned modules; Markdown and scanning stay inside their adapters with
explicit transition/traversal helpers. All four function exceptions were removed. `interfaces/cli.py` fell from 1,896
to 1,380 lines and its allowance tightened accordingly. The remaining five module exceptions and other reviewed function
exceptions are retained debt, not hidden by the F031 score.

## Scope and claim boundary

Feature 018 is a behavior-preserving maintenance slice based on merged commit
`8fa38524e79235c3f36348dd17af743af7c9ea8a`. It improves three high-risk orchestration
functions, makes partial-test commands truthful and introduces a structural
non-regression guard. It does not claim that all legacy complexity has been removed.

No public schema, persisted identifier, SQLite migration, runtime dependency, optional
provider profile, frozen release evidence or application version changes in this
feature. The F015 candidate remains `NO-GO`, and the F017 production Microsoft Graph
connector remains `NO-GO`.

## Reproducible measurements

Production Python was measured with UTF-8 decoding and Python's standard-library AST.
Function spans include decorators and both endpoints. The initial and final inventories
are:

| Metric | Initial | After extraction | Interpretation |
|---|---:|---:|---|
| Python modules | 81 | 81 | No architectural package expansion |
| Source lines | 39,392 | 39,697 | Named helpers, types and docstrings make control flow explicit |
| Functions/methods | 1,401 | 1,424 | Large orchestration was decomposed into bounded owners |
| Classes | 557 | 559 | Two private watcher transition/progress records |

Line count is not presented as an improvement: it increased by 305 lines because the
refactor favors named, typed, testable stages over compressed branching. The selected
orchestration spans changed as follows:

| Hotspot | Initial span | Final span | Reduction |
|---|---:|---:|---:|
| `evaluate_release` | 327 | 43 | 86.9% |
| CLI `_execute` | 248 | 18 | 92.7% |
| `SQLiteCatalog.reconcile_watch_scan` | 291 | 33 | 88.7% |

The extracted owning helpers are each below the policy's 100-line default. Their code
remains in the original service/interface/adapter modules so dependency direction and
transaction ownership stay unchanged.

## Maintainability policy

[`quality/maintainability-policy.json`](../quality/maintainability-policy.json) sets
default ceilings of 1,000 lines per production module and 100 lines per function. Every
pre-existing exceedance is identified by exact repository path and qualified function
name with an inclusive measured ceiling and rationale.

[`scripts/audit_maintainability.py`](../scripts/audit_maintainability.py) uses only the
standard library and fails when:

- a new module or function exceeds a default ceiling;
- an accepted hotspot grows beyond its reviewed ceiling;
- an exception target disappears or is renamed; or
- an exception becomes unnecessary but is not removed.

Policy JSON rejects duplicate keys, unknown fields, unsafe paths, incomplete records and
unsupported versions. Findings contain paths and integer metrics, never source or
document bodies. Sorted findings and two identical clean runs make the output
deterministic. Repository validation invokes the same audit without importing product
code.

## Behavior and validation evidence

Characterization was added before each extraction. The combined pre-refactor release,
CLI and watcher characterization set passed 40 tests. After extraction, the release
target passed 5 tests, the broader CLI set passed 71 tests and the broader watcher set
passed 70 tests. These suites preserve exact release-check ordering, duplicate-platform
rejection, unknown-command non-mutation, watcher event ordering, incomplete scans,
rename hints, backpressure, tombstones and transaction rollback.

Every corrected focused quickstart ran with explicit `--no-cov` semantics and exited
zero: F010 corpus 2, F010 lifecycle 45, F010 migration/reachability 24, F014 44, F015
24, F016 25, F017 29 and F018 47 test executions. These counts are command evidence and
may overlap; they are not presented as unique repository tests. The authoritative full
`uv run --locked pytest` command still enables socket blocking and the configured 85%
branch-coverage threshold.

## Residual debt and exclusions

The five production modules above the 1,000-line default remain explicit policy
exceptions. In particular, `src/openardp/adapters/sqlite_catalog.py` remains a large
transactional facade, and `src/openardp/interfaces/cli.py` remains a large execution and
composition facade after its argument and output grammar moved to bounded helpers.
Splitting SQLite or adding inheritance/framework machinery remains unjustified without
a second implementation or a demonstrated behavior benefit.

An optional, non-gating Ruff sweep for cyclomatic complexity, branch count and statement
count reported 184 findings on the initial repository. F018 does not claim those are all
resolved. A focused sweep after extraction still reports 16 findings in the three owning
modules, none on the three selected top-level orchestration functions. Future work can
ratchet those independently behind characterization tests.

The cleanup deliberately excludes `.venv` and every user worktree. `git ls-files`
confirms zero tracked virtual environments, bytecode, test/type/lint caches, coverage
databases or build directories. Local `.coverage`, cache and `dist/` output may be
removed after validation because it is disposable and ignored; the working Python
environment is preserved.

## Rollback

Revert the single F018 change set. No migration, persisted state, public artifact,
identifier or external provider operation needs reversal. Re-run the complete locked
gate after the revert to prove the restored behavior.
