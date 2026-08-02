# Incremental freshness and full integrity

Feature 021 separates two useful but fundamentally different questions:

1. **Is the authoritative local source still the exact source version named by the current READY head?**
2. **Are every native, manifest, projection and block byte still physically and semantically valid?**

Default status answers the first question. It hashes the complete source with SHA-256 on every request and reads one
transactionally consistent document/head/representation-header snapshot. It reports `HEAD` only when that snapshot names
a complete READY header. It does not enumerate projections, read block bodies, invoke a parser or claim arbitrary CAS
tamper detection.

Explicit full status answers both questions. It loads the complete representation and reuses the existing exhaustive
verifier. `FULL` is emitted only after native, manifest, catalog projection and every block object pass. Any failure
returns `INTEGRITY_ERROR` without full coverage.

```bash
openardp status ./notes.md --store .openardp
openardp status ./notes.md --full-integrity --store .openardp
```

MCP `get_source_status` remains identifier-only and always uses bounded `HEAD` mode. It accepts no path and exposes no
switch for an unbounded remote audit.

## Reproduce the measured result

```bash
uv run --locked python scripts/run_freshness_benchmark.py \
  --output /path/to/fresh-result
uv run --locked python scripts/validate_freshness_benchmark.py \
  --result /path/to/fresh-result
```

The frozen protocol reuses F020's exact 10,000/100,000-block corpus and reference environment. Each mode/scale group uses
one warm-up plus seven retained samples. Structural counters make the complexity claim executable: default requests must
show exactly one source inspection and zero aggregate loads, block-object verifications, parser calls and exhaustive
verifier calls.

The committed run is `PASS`: `HEAD` p95 is 2.257 ms at 10,000 blocks and 9.186 ms at 100,000 blocks, approximately
924.690x and 3,116.072x faster than F020. `FULL` p95 is 1,980.830 ms and 25,451.076 ms. Exact source hashing still scales
with source bytes; only work relative to prepared block count and workspace size is sublinear.
