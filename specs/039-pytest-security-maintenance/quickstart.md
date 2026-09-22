# Maintainer validation

From the worktree, validate the reviewed lock and unchanged gates:

```bash
uv lock --check
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest
uv run --locked python scripts/validate_repository.py
uv audit --locked --output-format json
```

For a pull request, the existing ready-code CI matrix must pass on Linux, macOS and Windows before merge. The audit can still report optional Docling/semantic advisories; count the pytest finding separately.
