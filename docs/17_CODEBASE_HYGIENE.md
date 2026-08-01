# Codebase hygiene and maintainability baseline

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
transactional facade, and `src/openardp/interfaces/cli.py` still contains the complete
stable argument and projection grammar. Splitting either into inheritance mixins or a
framework was rejected here because that would relocate coupling without a second
implementation or a behavior benefit.

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
