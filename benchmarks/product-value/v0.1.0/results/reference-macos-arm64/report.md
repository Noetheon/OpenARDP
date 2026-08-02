# OpenARDP product-value benchmark

**Outcome:** `CONDITIONALLY_WORTHWHILE`

This result is workload-bounded and does not replace the inherited F015 release `NO-GO` decision.

## Decision metrics

| Metric | Observed |
|---|---:|
| `anchor_correctness` | `1` |
| `break_even` | `32` |
| `complete` | `False` |
| `context_coverage` | `1` |
| `context_selected_native_ratio` | `5.1282077580552606e-05` |
| `precision` | `1` |
| `recall` | `1` |
| `reference_blocks` | `10000` |
| `replay_match` | `1` |
| `rich_formats` | `['docx', 'pptx']` |
| `scale_blocks` | `100000` |
| `search_p95_ns_at_100k` | `70199583` |
| `stale_incidents` | `0` |
| `status_p95_ns` | `2087372167` |
| `unchanged_parser_invocations` | `0` |

## Decision reasons

- `pdf-unavailable`
- `status-latency-target-missed`
- `benchmark-incomplete`

## Observed workload facts

| Profile | Blocks | Source MiB | Workspace MiB | Context budgets |
|---|---:|---:|---:|---|
| `reference` | 10,000 | 1.86 | 70.45 | 1024: passed, 256: base-bundle-exceeds-budget, 512: base-bundle-exceeds-budget |
| `scale` | 100,000 | 18.60 | 705.67 | 1024: passed, 256: base-bundle-exceeds-budget, 512: base-bundle-exceeds-budget |

## Retained timing summaries

Wall-clock values are milliseconds. Each row below has seven retained samples; cold preparation and the process high-water RSS proxy are retained separately as one-time observations.

| Profile | Workload | Treatment | Phase | p50 ms | p95 ms | MAD ms |
|---|---|---|---|---:|---:|---:|
| `full` | `rich-docx` | `openardp` | `evidence` | 83.846 | 87.899 | 1.075 |
| `full` | `rich-docx` | `openardp` | `reingest` | 15.598 | 16.350 | 0.189 |
| `full` | `rich-docx` | `persisted_native` | `native_load` | 0.029 | 0.034 | 0.002 |
| `full` | `rich-docx` | `raw_reparse` | `prepare` | 2394.269 | 2501.609 | 18.872 |
| `full` | `rich-pptx` | `openardp` | `evidence` | 156.959 | 160.069 | 2.668 |
| `full` | `rich-pptx` | `openardp` | `reingest` | 18.108 | 18.447 | 0.218 |
| `full` | `rich-pptx` | `persisted_native` | `native_load` | 0.034 | 0.038 | 0.002 |
| `full` | `rich-pptx` | `raw_reparse` | `prepare` | 2499.712 | 2533.602 | 33.891 |
| `reference` | `context-reference-1024` | `openardp` | `context` | 182.043 | 195.654 | 7.243 |
| `reference` | `context-reference-1024` | `openardp` | `replay` | 174.554 | 202.465 | 11.371 |
| `reference` | `query-reference-000017` | `openardp` | `search` | 6.837 | 7.121 | 0.137 |
| `reference` | `query-reference-000017` | `persisted_native` | `search` | 4.436 | 4.808 | 0.066 |
| `reference` | `query-reference-000017` | `raw_reparse` | `search` | 364.005 | 389.337 | 5.769 |
| `reference` | `query-reference-000151` | `openardp` | `search` | 6.504 | 6.842 | 0.115 |
| `reference` | `query-reference-000151` | `persisted_native` | `search` | 4.239 | 4.345 | 0.037 |
| `reference` | `query-reference-000151` | `raw_reparse` | `search` | 359.834 | 362.525 | 0.942 |
| `reference` | `query-reference-000997` | `openardp` | `search` | 6.528 | 6.692 | 0.030 |
| `reference` | `query-reference-000997` | `persisted_native` | `search` | 4.252 | 4.525 | 0.037 |
| `reference` | `query-reference-000997` | `raw_reparse` | `search` | 356.497 | 358.549 | 0.512 |
| `reference` | `query-reference-004093` | `openardp` | `search` | 6.378 | 6.640 | 0.038 |
| `reference` | `query-reference-004093` | `persisted_native` | `search` | 4.393 | 4.569 | 0.022 |
| `reference` | `query-reference-004093` | `raw_reparse` | `search` | 358.560 | 367.557 | 2.624 |
| `reference` | `query-reference-008191` | `openardp` | `search` | 6.540 | 6.829 | 0.069 |
| `reference` | `query-reference-008191` | `persisted_native` | `search` | 4.287 | 4.329 | 0.043 |
| `reference` | `query-reference-008191` | `raw_reparse` | `search` | 357.293 | 366.558 | 0.658 |
| `reference` | `query-reference-009999` | `openardp` | `search` | 6.667 | 6.745 | 0.041 |
| `reference` | `query-reference-009999` | `persisted_native` | `search` | 4.291 | 4.333 | 0.021 |
| `reference` | `query-reference-009999` | `raw_reparse` | `search` | 360.128 | 363.931 | 1.388 |
| `reference` | `reingest-reference` | `openardp` | `reingest` | 2063.957 | 2211.186 | 34.738 |
| `reference` | `status-reference` | `openardp` | `status` | 1832.849 | 2087.372 | 14.167 |
| `scale` | `context-scale-1024` | `openardp` | `context` | 3014.661 | 3472.086 | 142.452 |
| `scale` | `context-scale-1024` | `openardp` | `replay` | 3122.804 | 3401.906 | 135.332 |
| `scale` | `query-scale-000031` | `openardp` | `search` | 64.340 | 70.200 | 1.024 |
| `scale` | `query-scale-000031` | `persisted_native` | `search` | 59.757 | 62.300 | 1.262 |
| `scale` | `query-scale-000031` | `raw_reparse` | `search` | 35028.600 | 45667.495 | 636.119 |
| `scale` | `query-scale-001021` | `openardp` | `search` | 63.623 | 64.010 | 0.275 |
| `scale` | `query-scale-001021` | `persisted_native` | `search` | 66.868 | 101.757 | 0.320 |
| `scale` | `query-scale-001021` | `raw_reparse` | `search` | 48139.750 | 68010.982 | 12721.947 |
| `scale` | `query-scale-010007` | `openardp` | `search` | 64.477 | 64.837 | 0.030 |
| `scale` | `query-scale-010007` | `persisted_native` | `search` | 60.962 | 61.353 | 0.391 |
| `scale` | `query-scale-010007` | `raw_reparse` | `search` | 44683.319 | 47105.512 | 908.289 |
| `scale` | `query-scale-050021` | `openardp` | `search` | 65.720 | 66.948 | 0.909 |
| `scale` | `query-scale-050021` | `persisted_native` | `search` | 58.910 | 60.405 | 1.109 |
| `scale` | `query-scale-050021` | `raw_reparse` | `search` | 43702.426 | 44845.828 | 1143.402 |
| `scale` | `query-scale-099991` | `openardp` | `search` | 66.025 | 66.608 | 0.280 |
| `scale` | `query-scale-099991` | `persisted_native` | `search` | 56.052 | 58.906 | 0.611 |
| `scale` | `query-scale-099991` | `raw_reparse` | `search` | 48166.172 | 49184.641 | 1018.469 |
| `scale` | `reingest-scale` | `openardp` | `reingest` | 28576.699 | 33025.880 | 605.363 |
| `scale` | `status-scale` | `openardp` | `status` | 24587.065 | 28625.664 | 960.689 |

## Comparative findings

- `reference` worst-query p50: raw reparse 364.005 ms, persisted native 4.436 ms, OpenARDP 6.837 ms. OpenARDP is 53.2x faster than raw reparse and 1.5x the persisted-native latency.
- `scale` worst-query p50: raw reparse 48166.172 ms, persisted native 66.868 ms, OpenARDP 66.025 ms. OpenARDP is 729.5x faster than raw reparse and 1.0x the persisted-native latency.
- `reference` workspace amplification: 37.9x source bytes.
- `scale` workspace amplification: 37.9x source bytes.
- Rich persisted-native loading is the lower-bound latency baseline; a null break-even against it means verified OpenARDP reuse did not become faster in the declared horizon.

## Rich-document capability

| Format | Available | Evidence | Raw p50 ms | Native p50 ms | OpenARDP reuse p50 ms | Break-even vs raw/native | Limitation |
|---|---|---:|---:|---:|---:|---|---|
| `docx` | `True` | 6 | 2394.269 | 0.029 | 15.598 | 2 / None | `none` |
| `pdf` | `False` | - | - | - | - | - / - | `pdf-model-bundle-unavailable` |
| `pptx` | `True` | 9 | 2499.712 | 0.034 | 18.108 | 2 / None | `none` |

## Policy checks

| Check | Status | Expected | Observed |
|---|---|---:|---:|
| `anchor-correctness` | `passed` | `1` | `1` |
| `context-coverage` | `passed` | `1` | `1` |
| `precision` | `passed` | `1` | `1` |
| `recall` | `passed` | `1` | `1` |
| `replay` | `passed` | `1` | `1` |
| `stale-safety` | `passed` | `0` | `0` |
| `unchanged-parser-avoidance` | `passed` | `0` | `0` |
| `reference-workload` | `passed` | `10000` | `10000` |
| `rich-format-completeness` | `failed` | `['docx', 'pdf', 'pptx']` | `['docx', 'pptx']` |
| `scale-workload` | `passed` | `100000` | `100000` |
| `scale-search-latency` | `passed` | `300000000` | `70199583` |
| `status-latency` | `failed` | `250000000` | `2087372167` |
| `context-reduction` | `passed` | `0.5` | `5.1282077580552606e-05` |
| `break-even` | `passed` | `100` | `32` |
| `benchmark-completeness` | `failed` | `True` | `False` |

## Interpretation

Observed facts: exact search and source anchors, changed-source replacement, unchanged parser avoidance, context coverage for budgets that can hold the safe envelope, receipt replay, storage and local timings come directly from the raw observations.

Observed disadvantages: the preparation and workspace figures expose OpenARDP's one-time persistence cost; failed latency and completeness checks above remain visible. Insufficient context budgets and unavailable rich formats are not treated as successful measurements.

Policy-derived conclusion: break-even is calculated only for the measured repeated exact-lookup workload. It is not a forecast for semantic question answering or an arbitrary production corpus.

Untested conditions include private or adversarial real-world corpora, external model answer quality, PDF conversion without the required offline assets, other hardware classes and concurrent multi-user operation.

The raw-reparse baseline reparses the exact source for every lookup. The persisted-native baseline loads a canonical parsed JSON snapshot for every lookup. OpenARDP uses its production isolated parser, content-addressed store, SQLite catalog, FTS search, freshness status, context receipts and replay.

No external model or network evaluator is used. Source bodies, task text, hostnames, usernames, credentials and absolute paths are not recorded.
