# Phase 0 Research: Lexical Search over Prepared Evidence

**Feature**: `005-lexical-search` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

All findings consolidate the official [SQLite FTS5 documentation](https://sqlite.org/fts5.html), the converged
F003/F004 persistence design and the mandated constitution articles. Subagents could not be dispatched in this
environment, so the three research strands (FTS5 mechanics, atomic index-commit design, CLI/query contract) were
executed directly against the primary sources and the repository.

## Decision 1 — Index table variant: contentless-delete plus a STRICT mapping table

**Decision**: Store the FTS5 index as one contentless-delete virtual table
`block_search_index(block_text)` (`content=''`, `contentless_delete=1`, `tokenize='unicode61 remove_diacritics 0'`)
whose rowid is the primary key of a companion STRICT table `block_search_entries` carrying scope, block handle, kind,
trust zone, nullable page/slide, exact line range and the indexed text's SHA-256.

**Rationale**: F004 explicitly rejected document bodies in SQLite ("leakage or non-progressive reads"), so a
full-content FTS copy is unacceptable. A contentless table stores no column values — only the token index, which is
the irreducible derived data. `contentless_delete=1` (SQLite ≥ 3.43; the locked runtime binds 3.50.4) supports DELETE
and INSERT OR REPLACE, which drift repair needs. `bm25()` remains available because the default `columnsize=1`
maintains the docsize backing table even for contentless tables. The mapping table supplies filterable metadata and
the anchor for deterministic coverage verification; block text itself is always re-read and re-verified from the CAS
when served.

**Alternatives considered**:

- Full-content FTS5 table: rejected — duplicates bodies into the catalog and contradicts the F004 boundary.
- External-content table (`content=...`): rejected — requires the text in a same-database table OpenARDP does not
  have, and the official documentation warns results are unpredictable when the two sides drift.
- Plain contentless (`content=''` without `contentless_delete`): rejected — no DELETE support, so drifted rows could
  only be removed through the fragile value-based delete command.

## Decision 2 — Snippets are application-generated from verified CAS blocks

**Decision**: `snippet()`/`highlight()` are not used. Each served hit re-loads its canonical block object from the
CAS, verifies it and its catalog projection, checks the stored text hash, and derives a bounded snippet from the
exact verified text; a hit whose stored hash disagrees with the verified block fails as an integrity error.

**Rationale**: Auxiliary snippet functions require column values, which a contentless table does not store (they
return NULL). Application-side generation doubles as the deterministic serve-time staleness guard required by FR-005:
an index row whose text drifted from the CAS block can never silently produce a plausible snippet. Bounded per-query
hit counts (≤ 100) bound the extra verified reads. Terminal safety is fully controlled (existing `_safe_text`
escaping, no marker strings from document text).

**Alternatives considered**:

- Full-content table solely for snippets: rejected (Decision 1).
- No snippets: rejected — the spec's progressive-disclosure contract requires a bounded preview before `get`.

## Decision 3 — Query grammar and safe MATCH translation

**Decision**: The operator grammar is a bounded list of items, each either a bare term (no whitespace or quotes) or a
double-quoted phrase (with `""` escaping, per the FTS5 string rules). Translation wraps every item in double quotes
with internal quotes doubled and AND-combines the quoted items; the complete expression is passed as one bound
parameter to `WHERE block_search_index MATCH ?`. Operator lookalikes (`AND`, `OR`, `NOT`, `NEAR`, `*`, `^`, `:`, `-`,
parentheses) are therefore literal text. Queries that are empty, exceed the documented size/item bounds or tokenize
to zero terms are rejected before execution.

**Rationale**: The FTS5 grammar treats every special construct outside double-quoted strings; inside quotes the
string is simply tokenized into a phrase. Uniform quoting thus makes raw operator injection impossible by
construction, while a bound parameter keeps the query out of SQL. A quoted multi-token string yields the exact
adjacent phrase semantics the spec requires; separate items AND together without adjacency. Malformed MATCH input
surfaces as `sqlite3.OperationalError` and is sanitized, but the grammar rejects such input deterministically first.

**Alternatives considered**:

- Exposing raw FTS5 syntax: rejected — queries are untrusted operator input (Constitution Article IV) and raw syntax
  would make rejection of dangerous or implementation-revealing expressions impossible to bound.
- Prefix or trigram matching: rejected — the feature is exact lexical retrieval; prefix/stemming changes result
  meaning and belongs to no accepted requirement.

Tokenizer choice: `unicode61 remove_diacritics 0` keeps exact Unicode token identity (case-folded per Unicode 6.1,
diacritics preserved, no stemming), so "exact" means tokenizer-exact rather than byte-exact — documented in the data
model and contract.

## Decision 4 — Atomic index population inside the existing READY commit

**Decision**: Mapping and FTS rows are inserted inside the existing `commit_ready_representation` write transaction
after the `representation_blocks` inserts and before the `READY` state update. The commit aggregate already carries
every block's canonical text, so no CAS re-read is needed on the ingest path. A failure anywhere in the transaction
rolls back catalog and index rows together; existing fault-point injection proves the rollback boundary. Cache hits
never re-index (the original READY commit already indexed); head changes only move scope selection, not index rows.

**Rationale**: FR-002 demands index visibility exactly with READY visibility. The current commit path
(`sqlite_catalog.commit_ready_representation`) already runs one `BEGIN IMMEDIATE` transaction with object
registration, block inserts, READY update, verification and head/event advance; the FTS rows are additional
statements in the same transaction. A long transaction around parser work was previously rejected and stays rejected:
index insertion is pure SQL over already-parsed in-memory data.

**Alternatives considered**:

- Post-commit background indexing: rejected — violates atomic visibility and introduces a daemon OpenARDP does not
  have.
- Index-before-parse-commit visibility states: rejected — durable partial logical state was already rejected in F003.

## Decision 5 — Coverage verification, drift classes and verified rebuild

**Decision**: Three deterministic drift classes are checked per representation scope: **missing** (READY projection
ordinals without entries), **orphaned** (entries without a READY projection) and **stale** (entry text hash
disagrees with the verified CAS block). A structural coverage check (per-scope ordinal sets and counts, one grouped
query) runs inside the search read transaction; `search` refuses an in-scope uncovered representation with a stable
`SearchIndexIncomplete` classification instead of serving partial results. Result assembly joins FTS rowids through
the mapping table onto catalog projections and `document_heads`, so orphaned rows can never surface even before
repair. `reindex` is the only repair: for each requested (or every uncovered READY) scope it loads the verified
aggregate, recomputes exact text hashes from canonical CAS blocks and replaces that scope's entries in one bounded
write transaction, reporting per-scope `current`/`rebuilt`/`failed(code)` outcomes.

**Rationale**: JOIN discipline makes silent orphan-serving impossible by construction; the serve-time hash check
(Decision 2) makes stale rows fail loudly; the coverage pre-check makes missing rows an explicit operator-visible
state with a documented remedy. Idempotent per-scope transactions keep crashes safe and retries convergent.

**Alternatives considered**:

- Serving partially covered scopes with a warning: rejected — silently incomplete retrieval violates the evidence
  contract.
- Triggers tying FTS to projections: rejected — FTS5 external-content trigger patterns do not apply to a
  contentless design, and trigger-hidden writes were already rejected as non-explicit.
- Automatic rebuild on open: rejected — durable writes must be explicit (Clarifications, Article V).

## Decision 6 — Capability probe, migration 4 and history validation

**Decision**: FTS5 availability is probed explicitly by creating and dropping a temporary `fts5` probe table on the
catalog connection before migration 4 is applied and whenever the workspace opens; failure raises a sanitized
`SearchIndexUnavailable` classification before any result is served. Migration 4 (`lexical-block-search`) appends the
virtual table, the mapping table and its indexes without touching revisions 1–3; `_SCHEMA_TABLES[4]` additionally
expects the four contentless shadow tables (`_data`, `_idx`, `_docsize`, `_config`; no `_content` table exists for
contentless), verified empirically against the locked runtime. The existing checksum chain, `trusted_schema=OFF`,
`DELETE` journal and `synchronous=EXTRA` profile remain unchanged and cover the FTS shadow tables, which are ordinary
SQLite tables under the same transaction semantics.

**Rationale**: FTS5 ships in the SQLite amalgamation and in the locked CPython 3.12 runtime, but is not contractually
guaranteed on every system `libsqlite3`; an explicit probe turns an environment gap into a clean capability error
instead of a mid-commit migration failure. `trusted_schema=OFF` does not block built-in virtual-table creation or
direct application queries, which the integration suite proves.

**Alternatives considered**:

- Trusting compile-option pragmas only: rejected — a live create/drop probe tests the real capability.
- Skipping the strict table-set update: rejected — drift detection would silently stop verifying the catalog shape.

## Ranking and determinism notes

- `bm25(block_search_index)` is ordered ascending (lower is a better match). Scores depend only on corpus
  statistics, so a fixed corpus yields a reproducible order; raw float values are never persisted or asserted
  cross-platform — tests pin relative order on a fixed synthetic corpus.
- The documented total order is `bm25 ASC, document_id ASC, ordinal ASC`, making every tie deterministic regardless
  of storage or insertion order.
- Truncation applies after the full ranked set is computed; `truncated` is reported when the hit count exceeds the
  selected limit (limit 1–100, default 20).
- Concurrent ingest and search are isolated by SQLite snapshot semantics: coverage check, MATCH and projection joins
  run in one read transaction, so a query observes exactly one consistent searchable scope.
