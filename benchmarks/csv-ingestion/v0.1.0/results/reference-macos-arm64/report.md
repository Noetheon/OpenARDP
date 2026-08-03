# F028 Stable CSV Ingestion

Decision: `CSV_INGESTION_READY`.

Logical records: 1656; cells: 18216.
Source bytes: 932085; canonical derived bytes: 2816113.

| Question | Treatment | Full support | Selected | First relevant rank |
|---|---|---:|---:|---:|
| Q15 | openardp_direct | False | 0 | None |
| Q15 | openardp_operator | True | 1 | 1 |
| Q16 | openardp_direct | False | 0 | None |
| Q16 | openardp_operator | True | 1 | 1 |

The exact F025 CSV questions and oracle are reused without changing their bytes. Direct outcomes are reported, while the
acceptance gate requires the declared operator queries to retrieve exact verified source-backed evidence.
