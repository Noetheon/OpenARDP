# Stable CSV ingestion

F028 promotes CSV from the F024 benchmark-only structural probe into the ordinary local product path. Explicit `.csv`
sources are snapshotted unchanged into CAS and parsed from those verified bytes by the same spawned, socket-denied worker
boundary used for built-in text parsing, but under the distinct `openardp-csv` recipe.

The fixed profile accepts strict UTF-8, an optional leading UTF-8 signature, comma delimiters, double-quote escaping and
CR/LF/CRLF physical lines. It does not sniff dialects, infer types or evaluate spreadsheet formulas. The first logical
record is the ordered header. Every later row becomes a canonical JSON-text `table` block containing ordered
`[header-or-null, value]` pairs, its record number and exact inclusive physical-line range. Duplicate/empty headers,
ragged rows, empty cells, quoted commas/newlines and overflow cells therefore remain distinguishable.

The original source object is still the lossless native artifact. Normalized blocks are searchable disposable evidence,
not a rewritten CSV. Source, line, field, column, record and normalized-block sizes are bounded; malformed input produces
typed body-free errors. Formula-like cells remain `role=data` with instruction execution disabled.

## Measured result

The committed two-workspace result is `CSV_INGESTION_READY`: all 1,656 records and 18,216 cells from the 932,085-byte
official CISA source match an independent stdlib reconstruction, native and line-range identities are exact, cache reuse
passes and both unchanged Q15/Q16 operator queries select one required-source block at rank 1 with complete atom/citation
support. Canonical manifest-plus-block bytes are 2,816,113, or about 3.02 times source size before physical compression.

The untouched natural-language Q15/Q16 queries return no exact AND match. This is retained evidence that ingestion is
ready but semantic retrieval is not; F029 evaluates provider-neutral semantic/multilingual retrieval against the frozen
benchmark. The general OR-based context compiler is not claimed as the F028 evaluation path.
