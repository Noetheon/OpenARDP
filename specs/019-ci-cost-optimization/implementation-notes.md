# Implementation Notes: CI Cost and Latency Optimization

## Acceptance criteria restatement

- Final code-bearing PRs retain the complete offline suite on Linux, macOS and Windows.
- Ubuntu alone owns at least 85 percent branch coverage and all platform-independent gates.
- Draft iteration and governance-only changes are cheaper but cannot authorize a code merge without final checks.
- F015 release evidence remains complete and fail-closed at explicit release boundaries.
- Classification is deterministic and unknown/unsafe/empty input fails closed.
- uv cache use remains subordinate to locked synchronization; actions and permissions remain hardened.
- The dated cost claim is reproducible and explicitly distinct from the owner's invoice.
- F019 merges through one private PR, then `main` protection is applied and verified.

## Baseline

- Repository: private `Noetheon/OpenARDP`, `main` at `1c74d56c84fdf22e41cfa601c452294410f6a7ee`.
- Prior topology: one workflow; three quality jobs plus three release-evidence jobs and one aggregate release gate on
  every pull request and every `main` push.
- 2026-08-01 observation: 34 runs, 158 jobs, 939 per-job rounded minutes and 18.630 USD gross modeled runner cost.
- Runner split: Linux 277 minutes/1.662 USD; Windows 463/4.630; macOS 199/12.338.
- Owner-observed account charge: approximately 15 USD; exact billing export was unavailable to the current CLI token.
- Local test phase: 1,381 tests in 141.64 seconds with coverage and 93.71 seconds with `--no-cov`.
- Current remote risk evidence: historical Windows-only failures and one macOS-only concurrent-CAS failure forbid
  eliminating either final platform.

## Implementation log

### Spec Kit and test-first evidence

- Completed `specify`, `clarify`, `plan`, requirements/CI checklists, `tasks` and non-destructive `analyze`.
- Analysis covered 17 functional requirements, eight success criteria, four user stories and 32 tasks with 100 percent
  task coverage and zero critical/high/medium/low findings.
- Both checklists were complete before implementation: requirements 23/23 and CI quality 28/28.
- Intentional red command:
  `uv run --locked pytest --no-cov tests/unit/test_ci_audit.py tests/test_repository_contract.py` stopped during
  collection because `scripts.audit_ci` did not yet exist. This establishes that the policy tests preceded the module.

### Implemented topology and policy

- `scripts/audit_ci.py` strictly parses duplicate-free JSON, validates a narrow governance allowlist, classifies empty,
  unsafe, mixed and unknown paths as full, audits body-free workflow invariants and recomputes cost evidence with
  decimal arithmetic.
- Core CI performs fail-closed classification inside its stable Preflight job. Ready full-classified PRs add explicit
  Ubuntu, macOS and Windows jobs. Folding classification into Preflight avoids another rounded billable job. Explicit
  paid-platform jobs were selected over a conditional matrix because GitHub evaluates
  a job condition before matrix expansion; separate jobs guarantee both required status contexts when skipped.
- Ubuntu owns the only full coverage, lint, format, mypy and build execution. macOS and Windows each execute the complete
  suite with `--no-cov`; global socket denial remains inherited.
- F015 release evidence moved without behavior change to `.github/workflows/release-evidence.yml`, limited to manual,
  version-tag and release-owned ready-PR boundaries.
- setup-uv's bounded cache is keyed to `uv.lock`; every job still synchronizes locked and prunes with
  `uv cache prune --ci`. Environments and outputs are not cached.

### Focused validation

- `uv run --locked pytest --no-cov tests/unit/test_ci_audit.py tests/test_repository_contract.py
  tests/test_repository_validation.py`: 71 passed in 1.09 seconds.
- `uv run --locked ruff check scripts/audit_ci.py scripts/validate_repository.py tests/unit/test_ci_audit.py
  tests/test_repository_contract.py`: passed.
- `uv run --locked python scripts/audit_ci.py audit`: zero findings.
- `uv run --locked python scripts/audit_ci.py estimate`: gross 18.630 USD; projected 6.520–8.384 USD under the stored
  55–65 percent comparable-activity assumptions.
- Two audit runs and two estimate runs were byte-identical; their combined canonical-output SHA-256 was
  `411d1a87dc0656fa11792d220ce2f5e984b75485b120079bcfdf4c1cf9333601`.
- Ruby Psych parsed both workflow YAML files successfully. `git diff --check` passed.
- Live refresh of the 2026-08-01 GitHub inventory confirmed 34 runs (26 PR, eight push), 158 jobs and rounded minutes
  Linux 277, macOS 199, Windows 463. The 158 jobs divide into 102 quality, 42 release-evidence and 14 aggregate-gate
  jobs; no run/job identifiers are stored in the aggregate evidence.
- Classifier probes returned `governance` for the F019 operations document alone and `full` for the same document mixed
  with `scripts/audit_ci.py`.

### Compatibility evidence

- `git diff --name-only origin/main -- src schemas pyproject.toml uv.lock release/evidence` is empty.
- No runtime/development dependency, lockfile, public schema, persisted identity, application/workspace/profile version,
  F015 evidence byte or `NO-GO` decision changed.

### Pending completion evidence

The complete locked local gate passed: Ruff checked the repository, Ruff format checked 244 files, strict mypy checked
81 source files, and 1,407 offline tests passed in 151.10 seconds at 85.35 percent branch-aware coverage. `uv build`
created the `0.1.0rc1` sdist (303 KiB) and pure-Python wheel (352 KiB, 87 files) in a disposable directory; archive
inspection showed the expected package metadata, license and source tree. All four pre-commit hooks then passed against
all files, including a second complete coverage test run. Convergence, private PR cross-platform execution, strict
branch protection, merge and the post-merge Preflight remain to be recorded.

### Convergence

Final implementation-to-spec convergence rechecked 17 functional requirements, eight success criteria, four user
stories, both complete checklists, the CI policy, both workflows, the cost snapshot and all 32 tasks. It found zero
missing, partial, contradictory, weakened or unrequested implementation items. T032 already and completely represents
the remaining remote publication boundary, so convergence appended no new task. Product source, schemas, dependency
manifests and frozen release evidence remain unchanged from `origin/main`.

## Residual risks and rollback

Realized savings depend on Draft-to-Ready discipline, cache hits, runner images, per-job rounding and later prices.
Static workflow auditing does not replace remote GitHub parsing/execution. Release path filters require review if F015
files move. The authoritative rollback is one protected revert PR plus status-context update; no force push, evidence
deletion or quality-threshold reduction is permitted.
