# Implementation notes — Feature 020

## Acceptance criteria restated

Feature 020 is accepted only when a fresh offline evaluator can generate the exact synthetic corpora; run strong
raw-reparse, persisted-native and actual OpenARDP treatments; retain seven-sample timing evidence; measure exact search,
anchors, freshness, reuse, context and replay; exercise real DOCX/PPTX/PDF capability boundaries; recompute every summary
and decision; publish privacy-safe bounded results atomically; and pass all repository gates. The result must preserve
unfavorable and unavailable evidence and must not alter the F015 release decision.

## Implemented boundary

- Closed Pydantic models provide canonical identities for observations, robust summaries, checks and the value decision.
- Strict normative JSON loaders reject unexpected inventory, duplicate members, invalid schemas and inconsistent sample
  policy.
- The deterministic corpus generator creates exactly 100, 10,000 or 100,000 paragraphs and mechanically derived unique
  query tokens.
- The runner uses the production isolated text parser, local workspace, CAS, SQLite/FTS services, freshness status,
  context compiler and receipt replay. Rich runs use the production isolated Docling adapter and evidence service.
- Results are first written to a fresh staging directory, canonicalized, hashed and atomically published. Working corpus,
  native baseline and workspace bytes are removed from the published evidence.
- The validator rechecks the exact inventory, file digests, canonical model identities, raw-to-summary projection,
  decision policy and report projection without rerunning a workload.

## Deliberate tradeoffs

- Peak RSS is retained once as an explicitly labeled process high-water proxy, not mislabeled as an operation-specific
  allocation. Per-operation evidence remains wall time, CPU time and persisted bytes.
- Raw reparsing is intentionally expensive because it reparses the complete source for every lookup. This is the strong
  no-persistence baseline and is necessary for an honest break-even calculation.
- Context budgets below the safe base-envelope size are recorded as unavailable. Correctness is computed only over
  successfully compiled cases, while incomplete budget coverage blocks an unconditional `WORTHWHILE` result.
- PDF parsing remains unavailable without a validated explicit offline model bundle; DOCX/PPTX results do not stand in for
  PDF.
- The large orchestration and report code is maintainer tooling under `scripts/`, not shipped as part of OpenARDP's runtime
  services. Product-domain models and deterministic corpus input handling remain under `src/openardp/`.

## Verification record

### Red-to-green and focused evidence

- The first focused invocation failed during collection with the expected `ModuleNotFoundError` because the F020 models
  had not yet been implemented.
- `uv run --locked pytest --no-cov tests/unit/test_product_benchmark.py tests/integration/test_product_benchmark.py tests/test_product_benchmark_drift.py -q` passed all 16 F020 tests before repository-contract expansion.
- The expanded focused contract command covering F020 plus package and repository contracts passed 64 tests.

### Decision-bearing reference execution

```bash
uv run --locked python scripts/run_product_benchmark.py \
  --profile full \
  --output benchmarks/product-value/v0.1.0/results/reference-macos-arm64
uv run --locked python scripts/validate_product_benchmark.py \
  --result benchmarks/product-value/v0.1.0/results/reference-macos-arm64
```

The full run completed in 2,901.601 seconds. It retained 878 observations and 98 seven-sample summaries and independently
validated as `CONDITIONALLY_WORTHWHILE` with decision ID
`sha256:c8006415be754c3d71f87f0e0c1655a8e313c89176b894c51e2efde9a0b91f6a`. Exact correctness,
freshness, replay and unchanged-parser checks passed. The 100,000-block search p95 was 70.200 ms and the reference
break-even was 32 lookups. The 2,087.372 ms reference status p95 missed its 250 ms target; PDF was unavailable; and the
256/512-byte context budgets could not hold the safe base envelope. The F015 release status therefore remains `NO-GO`.

### Complete local quality gate

- `uv run --locked ruff check .` — passed.
- `uv run --locked ruff format --check .` — 254 files already formatted.
- `uv run --locked mypy src` — passed for 83 source files.
- `uv run --locked pytest` — 1,424 tests passed in 159.98 seconds; total branch-aware coverage was 85.31 percent against
  the enforced 85 percent minimum; socket access remained blocked by the suite.
- `uv run --locked python scripts/validate_repository.py` — passed with zero diagnostics.
- `uv build` — built both `openardp-0.1.0rc1` source and wheel distributions.
- `pre-commit run --all-files` — Ruff, formatting, strict mypy and complete offline pytest/coverage hooks passed.
- `git diff --check` — passed.
- Reference corpus generation followed by `--check` reproduced exactly 10,000 blocks, 1,949,999 bytes and
  `sha256:057847a9eecb7b17d38e0631892af20bc6add93195ff6bf713b8bd5032193bd5`.
- Independent result validation recomputed manifest hashes, observation identities, summaries, decision and report with
  no drift.

The initial complete suite exposed stale F017 package inventory and that placing the 1,849-line maintainer runner in
`src/openardp/services` violated the hygiene policy and diluted product coverage. F020 corrected the inventory and moved
pure benchmark orchestration/evaluation to `scripts/`; the final complete gate then passed without adding a hygiene
exception or reducing the coverage threshold.

## Corrective maintenance

Feature 033 corrected two harness defects without changing F020 inputs, policy, evidence schemas or historical results.
Reference/full runs now preflight fixture integrity and construct independent PDF, DOCX and PPTX parser instances before
the text phase; only PDF receives optional model assets. The CLI now catches the complete public `ParserError` hierarchy,
emits only `benchmark_execution_failed` with exit code 6 and logs only the safe exception class at debug level. Current
verification evidence is retained in `specs/033-product-benchmark-correctness/implementation-notes.md`.
