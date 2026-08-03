# Research: Stable CSV Ingestion

## Decision 1 - Extend the built-in isolated text adapter

CSV is decoded text and needs the same source-snapshot, cache, trust and atomic publication guarantees as TXT/Markdown.
A focused `CsvParserAdapter` implements the existing `ParserAdapter`; the isolated adapter selects it through a closed
constructor kind. This reuses worker/ingestion machinery without changing the historical `openardp-text` recipe and adds
no runtime dependency.

## Decision 2 - Preserve logical records as ordered canonical JSON text

`DictReader` is rejected because duplicate/empty headers and overflow cells can be collapsed or assigned special mapping
semantics. Header and cells are arrays. Each data row stores ordered `[header-or-null, value]` pairs plus its one-based
record number. This makes exact field-aware product search self-contained. The broader OR-based context discovery path is
not used to claim F028 retrieval quality; provider-neutral retrieval is evaluated separately in F029. The byte-exact
source remains the native CAS artifact.

## Decision 3 - Accept publisher line endings, reject dialect inference

The frozen authoritative CISA CSV uses LF rather than RFC 4180's historical CRLF wording. The reviewed profile therefore
accepts CRLF, LF and CR record boundaries supported by Python's CSV reader, but fixes delimiter, quote, double-quote and
strict parsing. Locale delimiters, encodings, type inference and dialect sniffing are excluded.

## Decision 4 - Bound parser-global field size safely

Python exposes CSV field size as process-global state. The focused parser serializes access with a module lock, saves the
previous value, applies the reviewed limit and restores it in `finally`. Product parsing already runs in a dedicated
spawned worker; the lock additionally makes direct unit use deterministic.

## Decision 5 - Evaluate without rewriting F025

The F025 protocol truthfully froze CSV as unsupported at that historical stage. F028 adds opt-in composition/execution
flags and its own result contract. It reuses the exact F025 corpus, questions and oracle bytes but does not mutate their
identities or reinterpret the old reference result.
