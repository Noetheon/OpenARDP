# Data Model: Storage Amplification Reduction

## Logical object and physical form

`StoredObject` remains unchanged: `object_id` is `sha256:<64 lowercase hex>` over exact logical bytes and `byte_length`
is the decoded logical length.

`PhysicalObjectForm` is internal adapter state:

| Field | Rule |
|---|---|
| `encoding` | `ordinary` or `openardp-deflate-dict-v1` |
| `object_id` | unchanged logical object identity |
| `logical_length` | 0..16 MiB for compact; ordinary retains existing bounds |
| `stored_length` | exact regular-file length |
| `relative_location` | derived solely from closed namespace plus object digest |
| `allocated_length` | optional platform observation, never an identity input |

At most one form is the converged state. Both valid forms may coexist only as restartable optimization residue. A form
whose decoded bytes do not match identity/length is corrupt.

## Compact envelope v1

The complete physical file is:

1. fixed profile magic and version;
2. fixed-width unsigned logical byte length;
3. raw DEFLATE stream using the code-pinned canonical-block dictionary;
4. no trailing members or bytes.

The decoder rejects unknown version, short header, logical length over 16 MiB, output beyond declared length, incomplete
stream, unused/trailing bytes, dictionary failure, length mismatch and logical digest mismatch. The envelope is used only
when shorter than the ordinary payload.

## Representation scope revision 11

`RepresentationScopeRow` normalizes one existing document/version/representation triple:

| Field | Rule |
|---|---|
| `scope_key` | local positive surrogate key, not serialized or identity-bearing |
| `document_id` | existing UUID text |
| `version_id` | existing SHA-256 source version |
| `representation_id` | existing SHA-256 recipe-bound representation |

The triple remains unique and references the unchanged representation header.

`CompactRepresentationBlock` replaces the old projection plus separate search mapping:

| Field | Rule |
|---|---|
| `entry_id` | stable local positive row/FTS key |
| `scope_key` | required normalized scope reference |
| `ordinal` | contiguous 0..99,999 per scope |
| `block_id` | unchanged UUID text, unique per scope |
| `object_id` | unchanged logical canonical-block object identity |
| `parent_id` | nullable unchanged scoped block UUID |
| `kind`, `sibling_order`, `line_start`, `line_end` | unchanged body-free navigation facts |
| `trust_zone`, `page`, `slide`, `text_hash`, `indexed_at` | nullable disposable search metadata; all null means uncovered |

The table has only scoped ordinal uniqueness, scoped block uniqueness and the object-reference index required by
reachability. Search coverage is complete only when every scoped block has complete search metadata and a matching FTS
row. Clearing/rebuilding search never removes a block projection.

## Optimization records

`StorageOptimizationItem` is an in-memory result with closed outcome `compacted`, `ordinary_smaller`, `already_compact`,
`duplicate_converged` or `failed`, plus logical/stored before/after counts and a sanitized reason code. Bodies and physical
paths are excluded.

`StorageOptimizationReport` contains workspace revision, eligible/completed/skipped/failed counts, logical/stored deltas,
and deterministic sorted items. It is an operation result, not a new durable authority.

## Storage benchmark evidence

`StorageObservation` binds protocol/corpus/environment/scenario/category, source identity/length, logical bytes, allocated
bytes or explicit unavailable reason, file count and object count. It contains no paths or bodies.

`StorageDecision` contains input IDs, scenario checks, exact F020 baselines, amplification/reduction values, limitations and
closed outcome `PASS` or `FAIL`. Its identity is canonical SHA-256 over decision facts excluding prose.

## State transitions

```text
ordinary eligible
  -> compact published and verified
  -> ordinary + compact (recoverable duplicate)
  -> compact only (converged)

ordinary non-saving -> ordinary only
compact only -> compact only
any corrupt/unsafe form -> failed closed; no cleanup
```

Catalog migration is independently:

```text
revision 10 -- verified backup --> revision 11 ordinary/compact compatible
revision 11 -- explicit optimize --> revision 11 compact where beneficial
```
