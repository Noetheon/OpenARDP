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
| `uv run mypy src --platform win32` | pass (strict) |
| `uv run pytest` | 407 tests pass, 86.45% branch coverage (required ≥ 85%) |
| `uv run pre-commit run --all-files` | pass |
| `uv run scripts/validate_repository.py` | pass |
| `uv build` + isolated wheel import | pass (`0.0.1`) |
| FTS5 shadow-table probe (SQLite 3.50.4) | `block_search_index_{config,data,docsize,idx}`; no `_content`; `bm25` and contentless delete verified under `trusted_schema=OFF` |
| Schema revision | 4 (`lexical-block-search`) |
| Runtime deps | unchanged (stdlib FTS5 only) |

## Quickstart validation (offline, temporary workspace)

- Scenario 1: term search returns hits from both ingested documents; identical results after source deletion.
- Scenario 2: phrase adjacency, term AND, `--kind` filter and `--limit 1` with `truncated`/`available` behave per contract.
- Scenario 3: superseded version excluded by default; `--all-versions` restores the old hit with its exact previous `version_id`.
- Scenario 4: entries deleted to simulate a pre-F005 workspace → `search` fails closed exit 6 (`search_index_incomplete`); `reindex` reports `rebuilt` per scope; second run reports `current` (no-op); search serves verified hits; all CAS objects and representations byte-identical before/after.
- Scenario 5: empty query exit 4, operator lookalikes literal exit 0, invalid `--kind` exit 4, missing workspace exit 6; hostile snippet text renders escaped and inert (`` in human mode).

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

## Remote verification

- Pull request [#5](https://github.com/Noetheon/OpenARDP/pull/5), squash merge `26947ad2ebdf4a2c90a2726838b870aa3fb564a8`.
- PR-head workflow [30050801259](https://github.com/Noetheon/OpenARDP/actions/runs/30050801259): Ubuntu, macOS and Windows all passed.
- Post-merge `main` workflow [30050939386](https://github.com/Noetheon/OpenARDP/actions/runs/30050939386): Ubuntu, macOS and Windows all passed.

## Out of scope (unchanged)

Embeddings, semantic/fuzzy search, OCR, watchers, MCP, HTTP, export, F006+ formats.
