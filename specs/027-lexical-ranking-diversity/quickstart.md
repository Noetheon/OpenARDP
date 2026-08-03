# Quickstart: F027 validation

```bash
uv run pytest tests/domain/test_context_ranking.py tests/unit/test_context_ranking.py \
  tests/integration/test_context_ranking.py tests/security/test_context_ranking_boundaries.py
uv run python scripts/run_ranking_benchmark.py --output /tmp/f027-result.json
uv run python scripts/validate_ranking_benchmark.py /tmp/f027-result.json
uv run python scripts/validate_repository.py
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run pre-commit run --all-files
```
