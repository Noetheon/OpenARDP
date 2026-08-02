# Quickstart: CI Cost and Latency Optimization

Run from the repository root with Python 3.12 and `uv==0.11.31`.

## Fast deterministic policy validation

```bash
uv run --locked pytest --no-cov tests/unit/test_ci_audit.py tests/test_repository_contract.py
uv run --locked python scripts/audit_ci.py audit
uv run --locked python scripts/audit_ci.py estimate
```

Exercise governance and fail-closed classification without changing the worktree:

```bash
printf '%s\n' docs/07_TEST_AND_BENCHMARK_STRATEGY.md > /tmp/openardp-ci-paths.txt
uv run --locked python scripts/audit_ci.py classify --paths-file /tmp/openardp-ci-paths.txt
printf '%s\n' docs/README.md src/openardp/__init__.py > /tmp/openardp-ci-paths.txt
uv run --locked python scripts/audit_ci.py classify --paths-file /tmp/openardp-ci-paths.txt
```

Expected scopes are `governance` and `full`, respectively.

## Authoritative local completion gates

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
uv run pre-commit run --all-files
git diff --exit-code
```

Focused suites use `--no-cov`; only the full `uv run pytest` command owns repository coverage.

## Pull-request operating model

1. Open active work as a draft pull request. Classification and Preflight run on every synchronization.
2. Keep it draft while iterating; the paid-platform final matrix does not run.
3. Mark it ready only when it is a merge candidate. `ready_for_review` schedules the applicable final gate.
4. For any code/unknown change, wait for Preflight and all three `Quality (...)` checks.
5. If final CI fails and more commits are expected, convert back to draft, fix, then mark ready again.
6. Use the Release Evidence workflow manually before a release if no release-owned PR/tag event already ran it.

Do not use commit-message CI skip markers on merge candidates. Do not bypass `main` protection.

## Rollback

Revert the single F019 merge through a new protected pull request, restoring the prior combined `ci.yml`. Then update
required status contexts to the restored job names before merging any subsequent change. Do not disable protection or
force-push `main` as a shortcut.
