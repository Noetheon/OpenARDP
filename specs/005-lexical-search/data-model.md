# Phase 1 Data Model: Lexical Search over Prepared Evidence

**Feature**: `005-lexical-search` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

This model extends the converged F003/F004 persistence contracts. It adds no public JSON Schema, no CAS object type
and no new representation lifecycle state; the index is derived catalog data (Constitution Article II).

## Persistence revision 4 (`lexical-block-search`)

Appended to the immutable chain; revisions 1–3 remain byte-identical.

### `block_search_index` (FTS5 virtual table)

```sql
CREATE VIRTUAL TABLE block_search_index USING fts5(
    block_text,
    content='',
    contentless_delete=1,
    tokenize='unicode61 remove_diacritics 0'
)
```

- Exactly one indexed column; no metadata columns (contentless tables return NULL for column reads).
- `rowid` equals `block_search_entries.entry_id` for the same hit.
- Expected shadow tables under the locked runtime (empirically pinned in tests): `block_search_index_data`,
  `block_search_index_idx`, `block_search_index_docsize`, `block_search_index_config`.

### `block_search_entries` (STRICT mapping table)

| Column | Type | Rule |
|---|---|---|
| `entry_id` | INTEGER | PRIMARY KEY; also the FTS `rowid` |
| `document_id` | TEXT | part of scope FK, length 36 |
| `version_id` | TEXT | part of scope FK, `sha256:` form |
| `representation_id` | TEXT | part of scope FK, `sha256:` form |
| `ordinal` | INTEGER | block ordinal within the representation, `0..99999` |
| `block_id` | TEXT | F002 block handle, length 36 |
| `kind` | TEXT | F002 `BlockKind` value |
| `trust_zone` | TEXT | F002 `TrustZone` value |
| `page` | INTEGER NULL | exact page coordinate; NULL for line-based text |
| `slide` | INTEGER NULL | exact slide coordinate; NULL for line-based text |
| `line_start` / `line_end` | INTEGER | exact one-based inclusive range, mirrors the projection |
| `text_hash` | TEXT | `sha256:` of the exact indexed UTF-8 block text |
| `indexed_at` | TEXT | RFC 3339 UTC write time (advisory only) |

Constraints: `PRIMARY KEY (entry_id)`; `UNIQUE (document_id, version_id, representation_id, ordinal)`;
`UNIQUE (document_id, version_id, representation_id, block_id)`; FK scope → `document_representations`
`ON DELETE RESTRICT`; value checks mirror the F003/F004 style. Indexes: `block_search_entries_block_id_idx`,
`block_search_entries_scope_idx (document_id, version_id, representation_id)`.

`_SCHEMA_TABLES[4]` = revision-3 set + `block_search_entries`, `block_search_index` and its four shadow tables.

## Domain records (`openardp.domain.search`)

Pure Pydantic v2 contracts; no I/O, mirroring the F004 domain style.

### `SearchQuery`

- `terms`: 1–32 items; each item is a bare term (1–256 chars, no whitespace/quote characters) or a phrase
  (1–1024 chars, arbitrary text except unescaped quote structure from the grammar parse).
- `match_expression() -> str`: deterministic translation — every item double-quoted with internal `"` doubled,
  items joined with one space (implicit AND). Always used as a bound parameter.
- Grammar errors raise `SearchQueryRejected` (empty input, bounds exceeded, unbalanced quotes, zero-token item).

### `SearchFilters`

- `document`: UUID or exact canonical source path resolution result (`None` = all documents).
- `version_id`: exact `sha256:` version (requires `document`).
- `include_history`: bool, default `False` (current heads only).
- `kind`: optional F002 `BlockKind`.
- `trust_zone`: optional F002 `TrustZone`.
- `page` / `slide`: optional non-negative integers; match only exact non-NULL coordinates.
- `limit`: 1–100, default 20.

### `SearchHit`

- `scope` (`RepresentationScope`), `block_id`, `kind`, `trust_zone`, `line_start`, `line_end`,
  `page`/`slide` (None for text), `rank` (float, advisory), `order_index` (int, position in the total order),
  `snippet` (bounded verified text window, ≤ 240 chars).

### `SearchOutcome`

- `hits` (deterministic total order), `truncated` (bool), `returned`/`available` counts, `query_echo`
  (bounded, escaped) — no full block bodies.

### `IndexCoverage`

- Per-scope sets: `ready_ordinals`, `indexed_ordinals`; derived `missing`, `orphaned` tuples and
  `is_covered` flag. Deterministic ordering everywhere.

### `ReindexScopeReport` / `ReindexReport` (the spec's "Backfill Report")

- Per scope: `scope`, `outcome` (`current` | `rebuilt` | `failed`), `failure_code` (bounded, nullable),
  `entry_count`. Report is ordered by scope identity and contains no document text.

## Invariants

1. Every entry's scope+ordinal maps to exactly one `representation_blocks` projection of a READY representation
   (enforced at write; verified at coverage check and serve time).
2. `text_hash` equals the SHA-256 of the exact canonical block text re-verified from the CAS before serving.
3. FTS `rowid` ↔ `entry_id` is a bijection within one catalog (checked at rebuild; serve joins through the mapping
   table only).
4. Index rows exist only for READY representations; STAGING/FAILED scopes never produce entries.
5. Deleting or superseding never mutates historical READY entries; scope selection (current head vs history) is a
   read-time join against `document_heads`.
6. The index changes only inside an explicit write transaction (READY commit or `reindex`), never in a read command.

## Trust and provenance

- Indexed text and snippets stay `role=data`, `instruction_execution_allowed=false`; snippet rendering reuses the
  existing control-character escaping.
- Provenance per hit mirrors the projection: document, version, representation, block handle, exact line range;
  page/slide are NULL until rich parsers provide them.
- `text_hash` uses the accepted SHA-256 recipe over exact UTF-8 bytes; no Python `hash()` anywhere.
