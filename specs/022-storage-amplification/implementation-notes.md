# F022 implementation notes

## Acceptance criteria restatement

- Fresh reference and scale workspaces must remain behaviorally equivalent while using at most 15 times source bytes.
- Existing revision-10 workspaces must migrate only after a verified backup and optimize idempotently without reparsing.
- Exact logical bytes and SHA-256 identities must be independent of raw or compact physical form; corruption fails closed.
- Search, context, maintenance, backup and restore must account for both forms without treating indexes as authority.
- A versioned offline benchmark must independently reconcile logical bytes, allocated bytes, files and category totals.

## Implemented design

Workspace revision 11 normalizes representation scopes and merges nullable disposable search metadata into one block
projection. Canonical derived blocks may use the bounded deterministic `openardp-deflate-dict-v1` physical envelope;
source/native objects remain ordinary. `storage-optimize` selects only catalog-approved derived objects, converges crash
duplicates and explicitly vacuums the catalog. A durable exclusive `STORAGE_OPTIMIZE` maintenance operation fences
ordinary catalog writes across every physical mutation; an interrupted run remains visible and is resumed only by an
explicit optimizer retry. After a colliding source/provider-native identity commits, the verified ordinary form removes
only its exact compact peer, so catalog authority wins even when CAS-first publication overlapped optimization. Ordinary
open remains non-mutating.

## Measured result

The binding macOS arm64 run produced `PASS`: fresh reference 13.3471x logical and 51.6411x allocated, migrated reference
13.3454x logical and 51.6411x allocated, and fresh scale 13.2002x logical and 51.4846x allocated. Logical reduction versus
F020 is 64.77% to 65.21%. All retained correctness checks passed. APFS allocation remains high because 200,000 scale
block objects are independently addressable; the report does not generalize that value across filesystems.

## Tradeoffs and remaining risks

- Revision-11 workspaces require a current reader; rollback uses the verified revision-10 backup, not in-place downgrade.
- The compact codec and dual-layout maintenance paths add internal complexity and must remain covered by hostile-input,
  interruption and cross-platform tests.
- The catalog and maintenance adapters remain documented legacy hotspots; F022 growth has reviewed exact ceilings rather
  than disguising a broad rewrite inside a persistence-format feature.
