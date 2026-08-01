# Quickstart: Repository Hygiene and Maintainability

Run the deterministic structural guard:

```bash
uv run --locked python scripts/audit_maintainability.py
```

Run focused behavior checks without applying the repository-wide coverage threshold to a partial suite:

```bash
uv run --locked pytest --no-cov \
  tests/unit/test_maintainability_audit.py \
  tests/integration/test_release_gate.py \
  tests/integration/test_watcher_catalog.py \
  tests/integration/test_cli.py \
  tests/integration/test_release_cli.py
```

Then run every authoritative gate. This separate pytest invocation retains branch coverage and socket blocking from
`pyproject.toml`:

```bash
uv lock --check
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest
uv run --locked python scripts/validate_repository.py
uv build
uv run --locked pre-commit run --all-files
```

Expected result: focused and full commands exit zero, maintainability diagnostics are empty, coverage remains at least
85 percent and no public/frozen artifact changes outside the declared governance files.
