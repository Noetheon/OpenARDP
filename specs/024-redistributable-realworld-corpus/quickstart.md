# Quickstart: Redistributable Real-World Corpus

## Verify the committed corpus offline

```bash
uv run python scripts/validate_realworld_corpus.py
```

## Explicitly reproduce it from publishers

This is the only connected F024 command and must target an absent external directory.

```bash
uv run python scripts/fetch_realworld_corpus.py --destination /Users/Shared/openardp-realworld-v0.1.0-a
uv run python scripts/fetch_realworld_corpus.py --destination /Users/Shared/openardp-realworld-v0.1.0-b
uv run python scripts/validate_realworld_corpus.py --corpus /Users/Shared/openardp-realworld-v0.1.0-a
uv run python scripts/validate_realworld_corpus.py --corpus /Users/Shared/openardp-realworld-v0.1.0-b
```

## Execute the binding six-format baseline

```bash
uv run python scripts/run_realworld_corpus_benchmark.py \
  --pdf-bundle /Users/Shared/openardp-pdf-bundle-2.114.0-v1-measured \
  --output /Users/Shared/openardp-f024-reference-result
uv run python scripts/validate_realworld_corpus_benchmark.py \
  --result /Users/Shared/openardp-f024-reference-result
```

## Run focused checks

```bash
uv run pytest --no-cov \
  tests/unit/test_realworld_corpus.py \
  tests/security/test_realworld_corpus_boundaries.py \
  tests/integration/test_realworld_corpus.py \
  tests/unit/test_realworld_corpus_benchmark.py \
  tests/integration/test_realworld_corpus_benchmark.py \
  tests/test_realworld_corpus_drift.py
```

## Full repository gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
uv run pre-commit run --all-files
```
