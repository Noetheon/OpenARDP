# F021 Incremental Freshness Benchmark

**Outcome:** `PASS`

## Measured results

| Scale | Blocks | Mode | p50 | p95 | F020 p95 | Improvement |
|---|---:|---|---:|---:|---:|---:|
| `reference` | 10000 | `HEAD` | 2.126 ms | 2.257 ms | 2087.372 ms | 924.690x |
| `reference` | 10000 | `FULL` | 1851.855 ms | 1980.830 ms | 2087.372 ms | not compared |
| `scale` | 100000 | `HEAD` | 9.040 ms | 9.186 ms | 28625.664 ms | 3116.072x |
| `scale` | 100000 | `FULL` | 24333.788 ms | 25451.076 ms | 28625.664 ms | not compared |

## Policy result

- Default HEAD p95 target: at most 250 ms at both scales.
- Default structural target: one exact source inspection and zero aggregate loads, block verifications, parser calls or full-verifier calls.
- Failed checks: none.

## Assurance boundary

`HEAD` proves exact current source identity against one atomic READY catalog header. It does not read every stored block and therefore does not claim arbitrary CAS tamper detection.

`FULL` retains the exhaustive native, manifest, projection and block verification path. Its cost is reported separately and is intentionally not represented as constant-time.

## Limitations

- The timing decision binds to the committed macOS arm64 reference environment; shared CI checks semantics and counters.
- The corpus is deterministic and synthetic. Real-world and semantic-use-case evidence remain F024 and F025.
- Exact source hashing still scales with authoritative source bytes; the optimized claim is sublinear in prepared block count.
