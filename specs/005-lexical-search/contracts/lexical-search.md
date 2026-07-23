# Internal Contracts: Lexical Search, Index Lifecycle and CLI

**Version**: F005 internal contract 1

These contracts extend the provider-neutral Python application boundary. They do not change the public F002 JSON
Schema release and do not authorize document text or query text to initiate side effects.

## Error contract

All public errors are typed and sanitized. They may carry canonical scope/block identifiers, bounded machine codes
and counts. They must not contain document bodies, snippets, raw SQL, FTS expressions, lease tokens or untrusted
exception text.

### Search/index errors

- `SearchQueryRejected`: empty, oversized, unbalanced or zero-token query input.
- `SearchCapabilityUnavailable`: the runtime cannot provide the mandated FTS5 index capability.
- `SearchIndexIncomplete`: an in-scope READY representation lacks complete structural index coverage; the remedy is
  `reindex`.
- `SearchIndexDrifted`: an entry's stored text hash or scope disagrees with verified catalog/CAS evidence at serve
  or rebuild time.
- `DocumentNotFound`: unknown document scope filter (shared F004 classification).
- `RepresentationNotFound`: requested version/history has no READY representation (shared F004 classification).
- Workspace and catalog errors remain the shared F003/F004 classifications.

## Query grammar contract

```text
query   := item (WS item)*
item    := term | phrase
term    := 1..256 characters without whitespace or '"'
phrase  := '"' (character | '""')* '"'        -- 1..1024 characters after unescaping
```

- Items are AND-combined; a phrase is one exact adjacent token sequence; a term is a one-token phrase.
- Tokenization is `unicode61 remove_diacritics 0`: case-folded per Unicode 6.1, diacritic-preserving, no stemming,
  no prefix expansion.
- `AND`, `OR`, `NOT`, `NEAR`, `*`, `^`, `:`, `-`, parentheses and braces inside any item are literal text.
- Total query input is bounded (≤ 4096 characters, ≤ 32 items); a query whose items all tokenize to zero terms is
  rejected.
- Translation is the deterministic `match_expression()` recipe; the expression is only ever a bound parameter.

## Ranking and result contract

- Total order: `bm25(block_search_index)` ascending, then `document_id` ascending, then `ordinal` ascending.
- Raw scores are advisory and never persisted; ordering on a fixed corpus is deterministic.
- `limit` defaults to 20 and accepts 1–100; truncation after the full ranked set is reported via `truncated` and
  `available` counts.
- Every hit carries scope, block handle, kind, trust zone, exact line range, nullable page/slide and a bounded
  snippet (≤ 240 escaped characters) derived from the verified CAS block; full bodies require `get`.

## Scope and filter contract

- Default scope: the current `document_heads` READY representation of every document (or of the `--document` scope).
- `--all-versions` includes every READY representation in scope; `--version` selects one exact source version of one
  document and implies that document's scope.
- `--document` accepts a UUID or an exact source path, resolved with the F004 `status` precedence (UUID first, then
  canonical source-key lookup).
- `--kind` validates against the F002 `BlockKind` vocabulary; `--trust` against the F002 `TrustZone` vocabulary.
- `--page`/`--slide` accept non-negative integers and match only entries carrying that exact coordinate; line-based
  text entries carry NULL and therefore never match a coordinate filter.
- Unknown scopes fail `not_found`; invalid values fail `rejected_input`.

## Index lifecycle contract

- READY commit inserts the representation's entries and FTS rows in the same SQLite transaction as the
  representation blocks and READY state (see plan "Atomic index population").
- Cache-hit reuse performs no index writes; a verified READY representation already has complete entries.
- `reindex` verifies each in-scope READY aggregate and its canonical CAS blocks, then replaces that scope's entries
  in one bounded write transaction per scope; it is idempotent and reports per-scope outcomes.
- Structural coverage (projection ordinal sets vs entry ordinal sets) is checked inside the search read transaction;
  incomplete in-scope coverage fails with `SearchIndexIncomplete`.
- Serve-time hash verification (entry `text_hash` vs verified CAS block text) guards every served hit; disagreement
  fails with `SearchIndexDrifted`.
- No read command ever writes index rows; no index row is ever served without a backing READY projection.

## Catalog port additions

```python
class Catalog(Protocol):
    def search_block_entries(
        self, *, match: str, filters: ResolvedSearchFilters,
    ) -> SearchMatchPage: ...
    def index_coverage(
        self, *, scopes: tuple[RepresentationScope, ...] | None,
    ) -> IndexCoverage: ...
    def replace_scope_index(
        self, scope: RepresentationScope, entries: tuple[SearchIndexEntry, ...], *, now: datetime,
    ) -> int: ...
    def list_ready_scopes(self, *, document_id: UUID | None) -> tuple[RepresentationScope, ...]: ...
```

- `search_block_entries` executes coverage pre-check, MATCH and projection join in one read transaction and returns
  the total ordered page plus `available` count.
- `replace_scope_index` deletes the scope's entries/FTS rows and inserts the supplied verified entries atomically;
  the scope MUST be READY.
- All SQL remains parameterized; the MATCH expression arrives as one bound value.

## CLI contract

```text
openardp search QUERY [--document ID_OR_PATH] [--version SHA] [--all-versions]
                      [--kind KIND] [--trust ZONE] [--page N] [--slide N]
                      [--limit N] [--store PATH] [--json]
openardp reindex [--document ID_OR_PATH] [--store PATH] [--json]
```

- Both commands use the shared workspace validation, versioned JSON envelope and exit classification:
  `2 invalid_usage`, `3 not_found`, `4 rejected_input`, `5 conflict`, `6 integrity_or_workspace`, `1 unexpected`.
- `SearchCapabilityUnavailable`, `SearchIndexIncomplete` and `SearchIndexDrifted` map to `6`;
  `SearchQueryRejected` and invalid filter values map to `4`; unknown scopes map to `3`.
- Human output prints one bounded escaped line per hit (`document_id block_id kind lines snippet`) plus a summary
  line; JSON returns the full `SearchOutcome`/`ReindexReport` structure.
- Neither command prints full block bodies, raw query SQL or FTS expressions.
