# F022 storage amplification result

Decision: **PASS**

| Scenario | Logical bytes | Logical x | Allocated bytes | Allocated x | Files | Reduction |
|---|---:|---:|---:|---:|---:|---:|
| fresh-reference | 26026877 | 13.3471 | 100700160 | 51.6411 | 20008 | 64.77% |
| migrated-reference | 26023589 | 13.3454 | 100700160 | 51.6411 | 20008 | 64.77% |
| fresh-scale | 257404223 | 13.2002 | 1003950080 | 51.4846 | 200008 | 65.21% |

Logical and filesystem-allocated reductions are separate measurements. Allocation uses `st_blocks * 512` on this host and is filesystem-dependent. Original F020 evidence is retained; no historical result was rewritten.
