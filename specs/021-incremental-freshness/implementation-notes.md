# Implementation Notes — Feature 021

## Acceptance Criteria Restated

F021 is accepted only when default status retains exact source SHA-256 inspection, performs no work proportional to
prepared block count, exposes bounded assurance explicitly and remains consistent under catalog snapshots. Complete
native/manifest/projection/block verification must remain available through a deliberate service/CLI mode and may report
`FULL` only after success. Service, CLI and bounded identifier-only MCP must serialize one body-free vocabulary. The
10,000/100,000-block result must retain raw samples and exact operation counters, preserve F020 evidence and pass an
independent canonical drift/privacy validator plus all repository and three-platform gates.

## Implemented Boundary

- Added closed `NONE`, `HEAD`, `FULL` integrity coverage and `HEAD`, `FULL` request modes with impossible-claim
  invariants.
- Added a catalog-port snapshot that reads document, current head and matching representation header in one existing
  SQLite read transaction without a migration or projection query.
- Default service status hashes the source and uses only the snapshot. Explicit full status loads the aggregate and
  reuses `IngestionService.verify_ready_representation`.
- CLI adds `--full-integrity`; MCP input is unchanged and cannot request full verification.
- The F021 benchmark pins F020 corpus and summary hashes, retains 28 raw measurements, exact structural counters,
  source/CAS immutability facts, deterministic summaries/decision/report and a hashed run manifest.
- New read-only SQLite projection and query-argument helpers keep the legacy `sqlite_catalog.py` and `cli.py` hotspots
  below their F018 ceilings; no maintainability exception was raised.

## Red-to-Green and Focused Evidence

- The first focused test run failed during collection because `IntegrityCoverage` did not yet exist.
- Domain, query, CLI and MCP focused tests then passed 92 tests with focused coverage enforcement deliberately disabled.
- Four corruption classes — native, manifest, projection and block — return bounded `CURRENT` under default status but
  are detected as `INTEGRITY_ERROR` by explicit full status.
- Same-size source bytes with restored modification time are still detected as `SOURCE_CHANGED`.
- Benchmark contract, identity, counter-policy, deterministic report, independent validation and tamper tests pass.

## Decision-Bearing Benchmark

```bash
uv run python scripts/run_freshness_benchmark.py \
  --repository-root . \
  --output benchmarks/freshness/v0.1.0/results/reference-macos-arm64
uv run python scripts/validate_freshness_benchmark.py \
  --repository-root . \
  --result benchmarks/freshness/v0.1.0/results/reference-macos-arm64
```

Validation returned `PASS` with decision ID
`sha256:c406634afd39c14f2ac89f4446a6739bf166e0a245f430ad29afeabf968442b8`.

| Scale | Default HEAD p95 | F020 p95 | Improvement | Full p95 |
|---|---:|---:|---:|---:|
| 10,000 blocks | 2.257 ms | 2,087.372 ms | 924.690x | 1,980.830 ms |
| 100,000 blocks | 9.186 ms | 28,625.664 ms | 3,116.072x | 25,451.076 ms |

Every default observation recorded one exact source inspection and zero aggregate loads, block-object verifications,
parser calls and full-verifier calls. Every full observation recorded one aggregate load, one verifier invocation and
exactly one block-object verification per prepared block. Source hashes and CAS inventories remained unchanged.

## Tradeoffs and Remaining Risk

- Default status no longer detects arbitrary post-publication block tampering because doing so necessarily reads the
  affected evidence. Its `HEAD` value makes that weaker assurance explicit.
- Full verification remains linear and intentionally expensive. MCP cannot initiate it, limiting resource-exhaustion
  exposure.
- Exact source hashing remains linear in source byte length; the measured sublinear claim applies to prepared block count
  and workspace size.
- The benchmark is synthetic. Real-world corpus and semantic source-quality evidence remain F024 and F025.
- F021 does not change F020's workload decision, F015 release `NO-GO`, storage amplification or PDF capability.

## Complete Quality Gate

- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — 261 files formatted.
- `uv run mypy src` — passed for 85 source files.
- `uv run pytest` — 1,436 tests passed in 157.85 seconds with 85.39 percent branch-aware coverage against the unchanged
  85 percent threshold; socket access remained blocked.
- `uv run python scripts/validate_repository.py` — passed with no hygiene or governance diagnostics.
- `git diff --check` — passed.
- `uv run python scripts/validate_freshness_benchmark.py ...` — independently returned F021 `PASS` with no drift.
- `uv build` — built `openardp-0.1.0rc1` sdist and wheel successfully.
- `pre-commit run --all-files` — Ruff, formatting, strict mypy and the complete offline pytest/coverage hook passed.
- The full suite initially exposed two stale F020 governance assumptions: the active-feature locator and exact prompt
  inventory. Both were updated to include F021, passed focused checks, and the subsequent complete suite was fully green.
- The first remote Windows matrix run exposed a pre-existing read-after-completion race in concurrent quarantine retries.
  A deterministic regression test now covers that interleaving, and the service re-reads the batch before requiring
  recovery; true non-terminal states remain fail-closed.
- Private PR cross-platform checks and post-merge verification remain pending at this point.
