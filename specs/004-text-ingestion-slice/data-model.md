# Data Model: Text Ingestion Vertical Slice

**Feature**: F004 | **Catalog revision**: 3 | **Public schema release**: unchanged `0.1.0`

## Existing authoritative records

F004 reuses without changing:

- F002 `DocumentManifest`, `ContentBlock`, `ParserDescriptor`, `SourceLocator` and trust contracts;
- ADR-0006 `representation_id` and `block_content_hash` projections;
- F003 `StoredObject`, `SourceKey`, `LogicalDocument` and `DocumentVersion` source facts.

The records below are internal Python/catalog contracts. Manifest and block CAS objects validate against the existing public
JSON Schemas; no new interchange schema is introduced.

## Scalar limits

| Name | Value | Purpose |
|---|---:|---|
| maximum source bytes | 104,857,600 | bound parser/resource exposure |
| maximum decoded line characters | 1,048,576 | prevent one-line memory exhaustion |
| maximum normalized blocks | 100,000 | bound aggregate/catalog work |
| representation lease duration | 300 seconds | fence duplicate synchronous parsing |
| parser warning code length | 128 | body-free machine classifications |

## Pure parser records

### `ParserRecipe`

| Field | Type | Rule |
|---|---|---|
| `name` | non-empty string | Built-in value `openardp-text` |
| `version` | non-empty string | Built-in value `1` |
| `profile` | non-empty string | F004 CLI accepts `default` |
| `config_hash` | SHA-256 ID | RFC 8785 hash of the complete adapter configuration |
| `normalization_schema_version` | installed schema version | `0.1.0` |

`representation_id` is recomputed from source version plus these fields using the existing identity helper.

### `ParsedBlock`

| Field | Type | Rule |
|---|---|---|
| `kind` | F002 `BlockKind` | F004 emits heading, paragraph, list, list-item, code or note |
| `text` | string | source-backed normalized text; never invented; only a fenced code block may be empty |
| `parent_index` | optional integer | points to an earlier candidate only |
| `order` | integer | contiguous zero-based sibling order |
| `line_start` | integer | one-based inclusive |
| `line_end` | integer | `>= line_start` |
| `structural_path` | tuple of strings | deterministic parser structure, not filesystem authority |

### `ParsedTextDocument`

| Field | Type | Rule |
|---|---|---|
| `media_type` | enum | `text/plain` or `text/markdown` |
| `blocks` | tuple of `ParsedBlock` | global reading order, at most 100,000 |
| `warnings` | sorted unique machine-code tuple | no body text |
| `bom_present` | boolean | records accepted leading UTF-8 signature |

Aggregate validation requires parent indices to be earlier/in-range, global order to be deterministic, every sibling order
to be contiguous and warning codes to be sorted/unique.

## Representation identity and handles

### `RepresentationScope`

| Field | Type | Rule |
|---|---|---|
| `document_id` | UUIDv7 | registered logical document |
| `version_id` | SHA-256 ID | exact source object |
| `representation_id` | SHA-256 ID | recomputed from version and recipe |

The same `representation_id` may appear for multiple logical documents because the accepted identity projection excludes
`document_id`; persistence scope is therefore `(document_id, version_id, representation_id)`.

### Deterministic F004 block ID

Input envelope:

```json
{
  "canonicalization": "RFC8785",
  "domain": "openardp:text-block-handle",
  "identity_version": 1,
  "payload": {
    "document_id": "<uuidv7>",
    "structural_path": ["h1:0", "paragraph:0"],
    "kind": "paragraph",
    "canonical_hash": "sha256:<hex>",
    "line_start": 2,
    "line_end": 3,
    "occurrence": 0
  }
}
```

The RFC 8785 bytes are SHA-256 hashed. The first 16 digest bytes become a UUID after setting version bits to 8 and RFC
variant bits to `10`. `representation_id` is deliberately excluded so structurally unchanged evidence can retain its
handle across versions; exact representation scope remains present on every `ContentBlock`. `occurrence` disambiguates
duplicate candidates under the same parent/path.

This UUID is a logical handle, not a content hash. `canonical_hash` remains the content identity.

## Representation lifecycle records

### `RepresentationState`

```text
STAGING
READY
FAILED
```

### `DocumentRepresentation`

| Field | Type | Lifecycle rule |
|---|---|---|
| `scope` | `RepresentationScope` | immutable |
| `recipe` | `ParserRecipe` | immutable and scope-consistent |
| `state` | enum | state-machine constrained |
| `attempt_count` | integer | starts 1; increases on failed/expired takeover |
| `revision` | integer | starts 1; increments on every lifecycle mutation |
| `active_owner_id` | optional bounded string | required only for STAGING |
| `lease_expires_at` | optional UTC time | required only for STAGING and later than updated time |
| `last_failure_code` | optional token | required only for FAILED |
| `manifest_object` | optional `StoredObject` | required only for READY |
| `native_object` | optional `StoredObject` | required only for READY |
| `block_count` | integer | zero outside READY; exact aggregate count in READY |
| `warning_codes` | sorted tuple | parser machine codes; populated for READY |
| `created_at` | UTC time | first claim time |
| `updated_at` | UTC time | monotonic |
| `ready_at` | optional UTC time | required only for READY |

Raw lease tokens and their hashes are not exposed by this domain projection. `READY` is immutable and cannot transition to
another state. A corrupt READY artifact is reported as an integrity failure; the catalog row is not rewritten.

### `RepresentationAcquireDisposition`

```text
CLAIMED
READY
BUSY
```

### `RepresentationLease`

Contains one STAGING `DocumentRepresentation` and a masked raw caller token. The token is at least 16 characters and is
never serialized or logged.

## Ready aggregate records

### `PreparedRepresentationBlock`

| Field | Type | Rule |
|---|---|---|
| `block` | F002 `ContentBlock` | scope/canonical hash/provenance valid |
| `object` | `StoredObject` | exact canonical JSON bytes of `block` |
| `ordinal` | integer | global contiguous `0..N-1` |
| `line_start` | integer | matches `block.source.extensions` |
| `line_end` | integer | matches `block.source.extensions` |

`block.parent_id` is null or references a block in the same aggregate. The graph is acyclic. Each parent's child orders
are exactly contiguous from zero. All block object IDs/lengths are unique by record slot, though identical byte objects may
naturally deduplicate in CAS.

This commit-only record carries a full block long enough to validate and publish its canonical object. SQLite never stores
the block body.

### `RepresentationBlock`

The persisted/query projection contains scope, block handle, object reference, global ordinal, parent handle, kind,
sibling order and line range only. Services load and strictly cross-check the full F002 block from CAS when needed.

### `ReadyRepresentationCommit`

| Field | Type | Rule |
|---|---|---|
| `scope` | `RepresentationScope` | authoritative scope |
| `recipe` | `ParserRecipe` | recomputes scope representation ID |
| `manifest` | F002 `DocumentManifest` | READY and exact scope/recipe/source |
| `manifest_object` | `StoredObject` | canonical manifest JSON bytes |
| `native_object` | `StoredObject` | equals verified source object for F004 |
| `blocks` | tuple of `PreparedRepresentationBlock` | complete aggregate |
| `warning_codes` | sorted tuple | body-free parser warnings |
| `source_observed_at` | UTC time | completed snapshot observation |
| `ready_at` | UTC time | `>= source_observed_at` |

The aggregate validates:

1. scope representation identity recomputation;
2. manifest state/scope/recipe/source/native consistency;
3. exact contiguous global/sibling ordering;
4. parent existence, same-scope membership and acyclicity;
5. unique `(block_id, ordinal)` slots;
6. line extension equality and valid ranges;
7. every block's canonical content hash;
8. manifest/block object IDs are supplied as verified immutable metadata.

## Operational projections

### `DocumentHead`

| Field | Type | Rule |
|---|---|---|
| `scope` | `RepresentationScope` | must reference READY |
| `source_observed_at` | UTC time | never moves backward |
| `last_ingested_at` | UTC time | `>= source_observed_at` |
| `last_disposition` | enum | latest successful observation outcome |
| `revision` | integer | starts 1, increments on head change/equivalent later observation |

An older observation does not mutate the head. Equal observation/same scope is idempotent; equal observation/different
scope conflicts.

### `IngestionDisposition`

```text
COMMITTED
CACHE_HIT
FORCED_REPARSE
CONVERGED
```

### `IngestionEvent`

| Field | Type | Rule |
|---|---|---|
| `document_id` | UUIDv7 | parent document |
| `sequence` | integer | contiguous from 1 per document |
| `scope` | `RepresentationScope` | ready representation observed |
| `disposition` | enum | successful classification |
| `parser_invoked` | boolean | false exactly for CACHE_HIT |
| `head_advanced` | boolean | whether this observation became current |
| `occurred_at` | UTC time | append time |
| `source_observed_at` | UTC time | snapshot ordering input |

No event stores source body, filename, locator, parser exception, token or arbitrary message.

### `IngestionResult`

Bounded service/CLI outcome with scope, disposition, parser-invoked/cache-hit booleans, head-advanced flag, block count,
warning codes and ingestion time. It contains no full block text.

### `SourceFreshness`

```text
NOT_REGISTERED
NO_READY_REPRESENTATION
CURRENT
SOURCE_CHANGED
SOURCE_MISSING
INTEGRITY_ERROR
```

### `DocumentSummary`, `SourceStatus`, `OutlineItem`

- Summary: document/source key, current scope/state, block count, warning count and last ingestion time; no body.
- Status: freshness plus selected head/scope and observed source identity where safely available; no parser invocation.
- Outline item: block handle, kind, parent, order, depth, bounded heading/list label and exact line range. Paragraph bodies are
  not returned.

## SQLite revision 3 relations

```text
documents 1 ---- * document_versions
document_versions 1 ---- * document_representations
document_representations 1 ---- * representation_blocks
document_representations 1 ---- 0..1 document_heads (current pointer per document)
documents 1 ---- * ingestion_events
objects 1 ---- * representation manifest/native/block references
```

The migration creates:

- `document_representations`;
- `representation_blocks`;
- `document_heads`;
- `ingestion_events`;
- ready/scope, object-reference, outline, block-handle and event-order indexes.

The self-parent foreign key on blocks is deferred until transaction commit. SQL cannot prove graph acyclicity or contiguous
orders, so those are mandatory domain/adapter checks before writes and after reload.

## State transitions

```text
acquire absent:          none    -> STAGING  attempt=1 revision=1
retry failed:            FAILED  -> STAGING  attempt+1 revision+1
take over expired:       STAGING -> STAGING  attempt+1 revision+1
renew active:            STAGING -> STAGING  revision+1
commit complete:         STAGING -> READY    revision+1, lease cleared
fail active:             STAGING -> FAILED   revision+1, sanitized code
ready cache/force retry: READY   -> READY     no immutable-row mutation
```

An active lease requires `lease_expires_at > now`; equality is expired. Owner, token hash and expected revision fence every
STAGING mutation.

## Invariant ownership

| Invariant | Owner |
|---|---|
| scalar syntax, strict enum/type/time/ID validation | domain models |
| representation and block-handle identity recomputation | domain identity helpers |
| hierarchy, ordering, line extension and aggregate scope | ready aggregate validator |
| UTF-8/syntax/resource parsing | parser adapter |
| regular/no-link/stable read snapshot | local source adapter |
| object digest/length/immutability | F003 object store |
| uniqueness, foreign keys, state-shape checks | SQLite schema |
| lease/head compare-and-set, ready atomicity, append event | SQLite catalog adapter |
| full CAS deserialization verification before reuse/query | ingestion/query services |
| argument/error/envelope rendering | CLI interface |

## Reachability

All manifest/native/block objects of every historical representation state that has a non-null reference are conservative
roots. READY objects remain live even when the document head later changes. STAGING/FAILED has no artifact references.
Document heads and ingestion events point only to already rooted representation scopes and add no object identity.

## Compatibility

- Existing revisions 1 and 2 are unchanged.
- Revision 3 is append-only and transactional.
- F002 public schemas and schema IDs remain unchanged.
- Existing catalogs upgrade with all document/version/job facts intact.
- An older F003 reader rejects revision 3 as newer; it does not partially interpret representation state.
