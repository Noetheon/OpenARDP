# Quickstart: Incremental Freshness Status

## 1. Focused semantic checks

```bash
uv run --locked pytest --no-cov \
  tests/domain/test_ingestion.py \
  tests/integration/test_document_query.py \
  tests/integration/test_cli.py \
  tests/integration/test_mcp_server.py
```

Expected: exact source changes remain detected, default status reports `HEAD`, explicit full verification reports `FULL`
only on success, corruption fails closed and MCP remains bounded.

## 2. Default and full CLI status

```bash
uv run --locked openardp status <target> --store .tmp/f021-workspace --json
uv run --locked openardp status <target> --full-integrity --store .tmp/f021-workspace --json
```

Expected: the first result is coverage-explicit and block-independent; the second may be slower and claims `FULL` only
after complete verification.

## 3. Decision-bearing benchmark

```bash
uv run --locked python scripts/run_freshness_benchmark.py \
  --output .tmp/f021-freshness-result
uv run --locked python scripts/validate_freshness_benchmark.py \
  --result .tmp/f021-freshness-result
```

Expected: retained default/full samples at 10k and 100k, F020 baseline comparison, exact counters, one target decision
and deterministic report.

## 4. Complete gates

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest
uv run --locked python scripts/validate_repository.py
uv build
pre-commit run --all-files
git diff --check
```
