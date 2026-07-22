# Quickstart: Validate the Repository Baseline

## Prerequisites

- Git
- uv 0.11.31
- A checkout of the repository on Linux, macOS or Windows

The repository selects Python 3.12 for its project environment. A newer global Python does not replace this project
selection.

## 1. Reproduce the locked environment

```bash
uv sync --all-extras --locked
```

Expected: uv creates or updates the disposable centralized project environment, attempts to maintain the conventional
`.venv` discovery link, installs the project and development group, and does not modify `uv.lock`. A missing or stale lock
fails. If a file provider blocks the discovery link, uv resolves the cached environment directly.

## 2. Verify the package contract

```bash
uv run python -c "import openardp; print(openardp.__version__)"
```

Expected: the command prints the version declared in `pyproject.toml`. No OpenARDP product command is installed by this
feature.

## 3. Run every mandatory gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Expected: all commands exit successfully. The test output confirms the configured branch-coverage threshold; socket
access is disabled throughout test execution.

## 4. Validate and exercise commit-time checks

```bash
uv run pre-commit validate-config
uv run pre-commit run --all-files
```

Expected: configuration validation and all four local hooks pass using the project environment.

## 5. Build and smoke-test distributable artifacts

```bash
uv build
```

Expected: wheel and source distributions build without adding product functionality. The wheel contains `py.typed` and
imports in an isolated Python 3.12 environment.

## 6. Verify a clean repeat

```bash
uv sync --all-extras --locked
git diff --check
git status --short
```

Expected: synchronization and validation do not create an unintended tracked diff. During implementation, `git status`
will still list the intentionally changed feature files until they are committed.

## Platform boundary

Run the steps above on the current machine. The committed GitHub Actions matrix is the authoritative execution mechanism
for the other supported operating-system families; local macOS success alone is not evidence that Linux and Windows jobs
have executed.
