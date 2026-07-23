# Implementation Notes: Lexical Search over Prepared Evidence

**Feature**: `005-lexical-search`  
**Branch**: `codex/f005-lexical-search`  
**Date**: 2026-07-23

## Restated acceptance criteria

1. READY commits publish searchable FTS5 index rows in the same SQLite transaction.
2. Pre-feature READY scopes become searchable through explicit idempotent `reindex`.
3. Coverage detection fails closed (`SearchIndexIncomplete`) instead of serving partial evidence.
4. Query grammar is bounded to terms/phrases; operator lookalikes are literal.
5. Hits are body-minimizing references with verified CAS snippets and deterministic ranking.
6. Filters cover document, version, history, kind, trust, page, slide and limit.
7. CLI exposes `search` and `reindex` with shared envelopes and exit classifications.
8. No embeddings, fuzzy matching, network, or public schema/ADR changes.

## Design decisions implemented

| Decision | Implementation |
|---|---|
| Contentless-delete FTS5 + STRICT mapping | `MIGRATION_4`, `block_search_index`, `block_search_entries` |
| Atomic READY+index commit | inserts after blocks, before READY update |
| Application snippets from CAS | `SearchService` verifies hash then builds snippet |
| Bound-parameter MATCH | `SearchQuery.match_expression()` + static SQL with bound params |
| Explicit reindex | `SearchService.reindex` + CLI `reindex` |
| Fail-closed coverage | `SearchIndexIncomplete` before serving |
| FTS5 capability probe | temp virtual table create/drop at catalog initialize |

## Evidence table

| Gate | Result |
|---|---|
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass |
| `uv run mypy src` | pass (strict) |
| `uv run pytest` | pass, coverage ≥ 85% branch |
| Schema revision | 4 (`lexical-block-search`) |
| Runtime deps | unchanged (stdlib FTS5 only) |

## Module surface

- `openardp.domain.search`
- `openardp.services.search`
- Catalog port methods: `search_block_entries`, `index_coverage`, `replace_scope_index`,
  `list_ready_scopes`, `list_scope_index_entries`
- CLI verbs: `search`, `reindex`

## Tradeoffs and risks

- Snippet location uses casefold substring matching against verified text; tokenizer-exact
  matches that differ from casefold still serve a head window rather than failing.
- Pre-F005 READY representations require one explicit `reindex` (by design).
- CURRENT reindex detection compares ordinal→text_hash maps; it does not compare FTS
  token streams byte-for-byte (rebuild is always available and safe).
- Remote CI evidence for this branch is produced after push/PR (same F001–F004 pattern).

## Out of scope (unchanged)

Embeddings, semantic/fuzzy search, OCR, watchers, MCP, HTTP, export, F006+ formats.
