# Product-value benchmark

Feature 020 answers a narrower question than the release gate: whether OpenARDP's parse-once, exact-evidence and bounded-
context design produces measurable value on representative local repeated-use workloads. It does not certify a release,
all document types, semantic answer quality or every machine class. The F015 `NO-GO` remains authoritative.

## Compared treatments

- `raw_reparse` parses the complete authoritative source for every exact lookup.
- `persisted_native` parses once, persists canonical parsed JSON and reloads that artifact for every lookup.
- `openardp` uses the delivered isolated parser, content-addressed store, SQLite catalog, verified FTS retrieval,
  freshness status, bounded context receipt and byte-identical replay paths.

The generated corpus is CC0 synthetic data with one mechanically derived unique fact per block. The frozen reference
profile contains 10,000 blocks; the scale profile contains 100,000. Rich-document checks use the repository's synthetic
DOCX, PDF and PPTX fixtures. PDF remains unavailable unless an explicit validated offline model bundle is supplied.

## Measurement and decision

Each retained timing group uses one warm-up and seven samples. Reports include p50, p95, median absolute deviation and a
deterministic 95-percent percentile-bootstrap interval. Exact judgments cover precision, recall, reciprocal rank, source
anchors, changed-source handling, parser avoidance, bounded-context coverage and replay equality. Missing or insufficient
capabilities remain visible rather than receiving fabricated numeric measurements.

The frozen policy emits `WORTHWHILE`, `CONDITIONALLY_WORTHWHILE` or `NOT_DEMONSTRATED`. Correctness, stale-current serving,
unchanged-source parser invocation and an incomplete 10,000-block reference are hard failures. Full 100,000-block scale,
all rich formats, documented local latency targets, at most 0.50 selected/native context ratio, complete benchmark
coverage and break-even within 100 repeated tasks are required for an unconditional outcome.

## Reproduce

```bash
uv run --locked python scripts/run_product_benchmark.py \
  --profile full \
  --output /path/to/fresh-result
uv run --locked python scripts/validate_product_benchmark.py \
  --result /path/to/fresh-result
```

The run is offline, bounded to 100,000 blocks, 100 MiB source bytes, 2 GiB working storage, 16 MiB published evidence and
one hour. Output contains only redacted environment buckets, body-free measurements, identities, summaries, the decision
and its deterministic Markdown projection. Absolute paths, source bodies, task text, usernames, hostnames, credentials and
raw exceptions are prohibited.

## Committed reference result

The committed Apple-silicon macOS result is under
`benchmarks/product-value/v0.1.0/results/reference-macos-arm64/`. Its exact outcome, metrics and limitations are generated
from the 878 raw observations in that directory and must be read from `report.md`.

The validated outcome is `CONDITIONALLY_WORTHWHILE`: exact correctness, zero stale incidents, zero unchanged parser calls,
100,000-block search p95 of 70.200 ms and break-even after 32 reference lookups support the core repeated-use thesis.
Unmet conditions are the 2,087.372 ms reference status p95, unavailable PDF assets and incomplete 256/512-byte context
budgets. The detailed report also exposes the 28.626-second scale status p95, approximately 37.9x text storage
amplification and direct-native rich loading as a faster lower-bound baseline.
