# Quickstart: Product Value Benchmark

## Prerequisites

- clean checkout of the F020 branch;
- Python 3.12 and pinned `uv`;
- locked environment including the existing Docling extra;
- enough local disk for the generated 100,000-block workspace;
- no network access is required or permitted by the benchmark.

```bash
uv sync --all-extras --locked
```

## 1. Fast semantic smoke

```bash
uv run --locked python scripts/run_product_benchmark.py \
  --profile smoke \
  --output .tmp/product-benchmark-smoke

uv run --locked python scripts/validate_product_benchmark.py \
  --result .tmp/product-benchmark-smoke
```

Expected: a complete evidence directory, exact judged correctness and a valid decision. Smoke timing does not support a
product claim.

## 2. Full decision-bearing run

```bash
uv run --locked python scripts/run_product_benchmark.py \
  --profile full \
  --output .tmp/product-benchmark-full

uv run --locked python scripts/validate_product_benchmark.py \
  --result .tmp/product-benchmark-full
```

Expected: the 10,000-block reference workload, 100,000-block scale workload, committed DOCX/PPTX/PDF cases, unchanged
and change checks, all raw samples, one three-state decision and `report.md`. PDF may be explicitly unavailable when its
offline model bundle was not provisioned; this prevents an unconditional result.

## 3. Determinism and corpus drift

```bash
uv run --locked python scripts/generate_product_benchmark.py \
  --profile reference \
  --output .tmp/product-corpus-reference

uv run --locked python scripts/generate_product_benchmark.py \
  --profile reference \
  --check .tmp/product-corpus-reference
```

Expected: exact match. Timing values are intentionally not golden; interpretation of one frozen observation set is.

## 4. Focused automated evidence

```bash
uv run --locked pytest --no-cov \
  tests/unit/test_product_benchmark.py \
  tests/integration/test_product_benchmark.py \
  tests/test_product_benchmark_drift.py
```

## 5. Repository gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/validate_repository.py
uv build
```

## Interpretation boundary

- The report answers value only for its exact synthetic workloads and environment class.
- A product-value result does not replace the existing F015 `NO-GO` release decision.
- Inspect `observations.json` before citing a latency or resource claim.
- Treat every unavailable case and unfavorable comparison as part of the result.
