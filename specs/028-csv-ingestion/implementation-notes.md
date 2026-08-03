# Implementation Notes: Stable CSV Ingestion

## Acceptance criteria restatement

1. Ingest direct immutable UTF-8 CSV without preprocessing or source mutation.
2. Preserve every logical header/cell in order, exact logical-record line provenance and exact native bytes.
3. Reject malformed, unsafe or oversized input in the isolated network-denied parser with sanitized failures.
4. Make CSV evidence searchable/retrievable through existing verified product paths.
5. Prove Q15/Q16 from the unchanged frozen benchmark in two fresh workspaces and keep F025 historical replay intact.
6. Add no semantic provider, translation, embedding, cloud dependency or schema/storage/identity change.

## Implementation record

### Delivered behavior

- Added a distinct `openardp-csv` recipe rather than invalidating historical `openardp-text` representations.
- Added bounded strict stdlib CSV parsing inside the existing spawned, socket-denied worker.
- Added `.csv` routing for explicit local ingestion, CLI and watcher composition with exact native CAS authority.
- Projected header and records as canonical JSON-text `table` blocks with exact physical line ranges,
  `openardp-csv-v1` extraction and inert untrusted-data classification.
- Added cache, search, exact get, source immutability, malformed/resource, formula and network-denial coverage.
- Added a two-fresh-workspace benchmark and a separate stdlib-only validator over unchanged F025 Q15/Q16 inputs.

### Measured evidence

- Decision: `CSV_INGESTION_READY`.
- Frozen source: 932,085 bytes, SHA-256
  `e9a3a5412b0d714931ffbd8114e3784519a003ce473d9db5bd382f739d6b4a24`.
- Exact logical coverage: 1,656 records and 18,216 cells; product/source table and physical-line identities match.
- Canonical manifest-plus-block bytes: 2,816,113, a 3.0213x logical derived/source ratio before physical compression.
- Q15/Q16 operator queries: one selected block each, first relevant rank 1, full atom/source support and citation integrity.
- Q15/Q16 direct questions: zero exact AND matches. This is retained as a retrieval gap rather than hidden by query
  rewriting; F029 owns semantic/multilingual evaluation.
- Two fresh result projections are identical and unchanged ingestion is a verified cache hit.

### Verification record

- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — passed (349 files).
- `uv run mypy src` — passed (99 clean-tree source files).
- `uv run python scripts/validate_repository.py` — passed.
- `uv run pytest` — 1,652 passed, 3 skipped, 85.39% coverage.
- The committed reference and one new benchmark execution both independently validated as `CSV_INGESTION_READY` with
  result ID `sha256:4c624adbdd102ec72ea46f775642bb4b709ff2530144b7debbba9355d8477ef2`.

### Tradeoffs and residual risks

- Repeating header/value association in each row costs derived bytes but makes each retrieved record self-contained and
  preserves duplicate/empty header semantics. The measured ratio remains bounded and physical compact storage applies.
- The profile is intentionally comma/double-quote/UTF-8 only and accepts LF/CR/CRLF; delimiter/encoding sniffing and broad
  spreadsheet dialect compatibility are excluded.
- Physical line ranges identify exact source evidence but the normalized JSON text does not reproduce original quoting or
  newline bytes; the native CAS object is authoritative for that fidelity.
- Exact lexical search is not semantic retrieval. Direct misses and the OR-based context discovery behavior are not
  claimed as F028 successes.

### Rollback

Remove the CSV media allowlists/composition and the `openardp-csv` adapter. Existing CSV source/native/block objects remain
immutable and harmless; derived representations can be reclaimed through the governed maintenance path. No catalog or
public-schema downgrade is required.
