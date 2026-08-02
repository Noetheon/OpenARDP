# F022 storage benchmark v0.1.0

This offline benchmark retains the unfavorable F020 baseline and measures the complete optimized workspace rather than
only compressed object payloads. Fresh reference and scale runs exercise exact search, freshness, unchanged reuse,
context persistence/replay and edit/revert history. The migrated reference run materializes a real revision-10 workspace
with the pinned F021 implementation, performs the required verified backup-first migration and then runs the explicit
optimizer without source reparsing.

Run and independently validate it from a clean Git checkout:

```bash
uv run python scripts/run_storage_benchmark.py \
  --output /Users/Shared/openardp-storage-result
uv run python scripts/validate_storage_benchmark.py \
  --output /Users/Shared/openardp-storage-result
```

The result inventory is exactly `decision.json`, `observations.json`, `report.md`, `run-manifest.json` and
`summary.json`. Logical bytes are regular-file `st_size` totals. Allocated bytes use `st_blocks * 512` only where the
host exposes that value, and are explicitly unavailable otherwise. APFS allocation can exceed logical bytes because the
workspace deliberately retains many independently addressable objects; this benchmark does not generalize that physical
number to other filesystems.

Categories form a closed inventory: catalog, ordinary objects, compact derived objects, quarantine, staging and control
files. Original/source and provider-native objects remain ordinary and are never transcoded. The validator recomputes
category totals, ratios, reductions, thresholds, file hashes, decision and report from machine evidence.

The producer fixes UTC event sequences, document entropy, owners and lease tokens. Independent repeated runs therefore
produce identical optimized summaries, reports and decisions on the same platform. Pre-optimization SQLite file size and
wall-clock duration remain observations rather than reproducibility claims: SQLite may reach the same final `VACUUM`ed
state from slightly different intermediate page allocation histories.
