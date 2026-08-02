# Quickstart: Semantic End-to-End Source Evaluation

## Validate frozen inputs offline

```bash
uv run python scripts/validate_realworld_corpus.py
uv run python scripts/validate_semantic_e2e_benchmark.py --inputs-only
```

## Execute the binding real-world use case

```bash
uv run python scripts/run_semantic_e2e_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1-measured \
  --output /Users/Shared/openardp-f025-reference-result
uv run python scripts/validate_semantic_e2e_benchmark.py \
  --result /Users/Shared/openardp-f025-reference-result
```

## Run focused checks

```bash
uv run pytest --no-cov \
  tests/unit/test_semantic_e2e_benchmark.py \
  tests/integration/test_semantic_e2e_benchmark.py \
  tests/test_semantic_e2e_drift.py
```

The opt-in actual-corpus test additionally requires `OPENARDP_PDF_BUNDLE` and
`OPENARDP_SEMANTIC_E2E_RESULT` and is not part of ordinary CI.

## Full repository gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run mypy src --platform win32
uv run pytest
uv run python scripts/validate_repository.py
uv build
uv run pre-commit run --all-files
git diff --check
```
