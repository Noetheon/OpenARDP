# Stable CSV ingestion benchmark v0.1.0

This F028 benchmark reuses the byte-frozen F025 Q15/Q16 questions, operator queries, support atoms and official CISA CSV.
It performs two fresh stable-product ingestions, independently reconstructs all logical CSV records from native bytes,
verifies source/block/provenance/cache facts and runs exact product search for both unchanged treatments.

`CSV_INGESTION_READY` requires exact native bytes, all 1,656 logical records and physical line ranges, deterministic fresh
runs, cache reuse and full operator-query atom/source/citation support. Direct natural-language misses remain visible and
are not a failure of ingestion; F029 owns semantic and multilingual retrieval. Results contain no source bodies or paths.
