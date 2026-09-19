# F037 Validation

From the repository root, use the locked Python 3.12 environment:

```bash
uv sync --locked --all-extras
uv run --locked pytest --no-cov tests/integration/test_mcp_semantic_context.py tests/integration/test_semantic_candidates.py tests/unit/test_e5_semantic.py
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest
```

Run any added worker regression file alongside these tests. All synthetic regression tests run without network/model downloads. Model bundle provisioning is not necessary. Record red/green and repository/CI gate outputs in implementation notes; existing opt-in real-model tests are distinct evidence and must not be claimed as run unless actually run.
