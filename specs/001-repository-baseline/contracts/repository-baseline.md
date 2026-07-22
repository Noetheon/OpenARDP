# Repository Baseline Contract

This contract defines the operator-visible surface of feature 001. It introduces no document-processing API or CLI.

## Environment contract

| Contract | Required outcome |
|---|---|
| Python | A project environment in the 3.12 series is selected. |
| uv | The repository-declared uv version accepts the project. |
| `uv.lock` | Present, committed and current for project metadata. |
| `uv sync --all-extras --locked` | Installs the complete baseline or fails without changing the lock. |

## Public package contract

- `import openardp` succeeds after synchronization.
- `openardp.__version__` equals the version in `pyproject.toml` and installed distribution metadata.
- `openardp.domain`, `openardp.ports`, `openardp.adapters`, `openardp.services` and `openardp.interfaces` import.
- The installed distribution includes `py.typed`.
- No console entry point or document-product operation exists.

## Mandatory quality commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Each returns zero only when its complete configured gate passes. Pytest includes branch coverage, repository/documentation
contract validation and outbound-network blocking.

## Commit-time contract

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

The configured hooks invoke the same lint, format, type and test commands through the locked project environment.

## Automation contract

- Trigger on pull requests and pushes to `main`; never use `pull_request_target`.
- Run the mandatory gates on Linux, macOS and Windows with Python 3.12.
- Use `contents: read`, no write permission and `persist-credentials: false`.
- Pin third-party actions to 40-character revisions with reviewed release annotations.
- Run locked synchronization before any quality command and verify no gate changes tracked files.

## Explicitly absent surface

Feature 001 exposes no `openardp` executable and no parser, domain document model, persisted identity, database, CAS,
ingestion, search, context, MCP, watcher, model provider or cloud connector.
