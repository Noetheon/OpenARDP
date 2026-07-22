# Data Model: Domain Models and Interchange Schemas

## Model-wide rules

- Every model forbids unknown direct properties and accepts provider- or adapter-specific data only under `extensions`.
- Models are frozen at the attribute level; ordered core collections are tuples. Nested JSON values are validated snapshots and are not claimed to be recursively immutable Python containers.
- Public JSON validation is strict: no duplicate keys, non-finite numbers, unsafe integers, silent scalar coercion or non-JSON extension values.
- Timestamps are timezone-aware UTC instants and serialize with an RFC 3339 `Z` suffix.
- UUID text uses canonical lowercase, hyphenated form. `document_id` is UUIDv7; block and bundle identifiers are canonical UUIDs.
- SHA-256 identifiers use `sha256:` plus 64 lowercase hexadecimal characters. The source descriptor retains the raw 64-character digest only to match the existing Manifest contract.
- Current root-contract version is exactly `0.1.0`. Manifest retains `spec_version`; the other four roots use `schema_version`.

## Invariant ownership

| Class | Enforced by | Examples |
|---|---|---|
| Schema-expressible | JSON Schema and Pydantic | Required fields, `const`, enums, types, regexes, numeric bounds, non-null payload alternatives |
| Record-semantic | Pydantic model validator | Source/version digest equality, recomputed IDs, lifecycle combinations, budget comparison |
| Aggregate-semantic | Later service/aggregate validator | Parent record scope equality, relation graph cycles, referenced artifact existence |

The public schema may structurally accept a record that violates a record-semantic rule. Such a case is explicitly tested and documented; no non-standard JSON Schema keyword pretends otherwise.

## Shared value objects

### TrustClassification

| Field | Type | Rule |
|---|---|---|
| `zone` | `local_trusted \| organization_trusted \| external_untrusted \| model_derived` | Required |
| `role` | `data \| metadata` | Required |
| `instruction_execution_allowed` | `false` | Required constant; never configurable |
| `integrity` | `verified_sha256 \| unverified` | Required |
| `sensitivity` | `public \| internal \| confidential \| restricted \| unknown` | Required |

`DataTrustClassification` specializes this shared vocabulary for every F002 content-bearing field and constrains
`role` to the schema-visible constant `data`. The broader `metadata` vocabulary remains available for a future
non-content record; it cannot label blocks, derivations or selected evidence.

### ComponentDescriptor

| Field | Type | Rule |
|---|---|---|
| `name` | non-empty string | Required |
| `version` | non-empty string | Required; provider-neutral and not assumed to be SemVer |
| `profile` | non-empty string or null | Optional |
| `extensions` | JSON object | Default empty |

### ParserDescriptor

Extends the component facts with required `profile` and `config_hash`. Parser configuration affects `representation_id`; adapter metadata not used by identity belongs under `extensions`.

### SourceLocator

| Field | Type | Rule |
|---|---|---|
| `extraction_method` | non-empty string | Required |
| `native_id` | non-empty string or null | Optional |
| `page` | integer >= 1 or null | Optional, mutually exclusive with `slide` |
| `slide` | integer >= 1 or null | Optional, mutually exclusive with `page` |
| `bbox` | four finite numbers or null | `[x_min, y_min, x_max, y_max]`; min <= max; page or slide required |
| `extensions` | JSON object | Adapter-specific coordinate metadata only here |

Coordinates describe the source adapter's native coordinate system; F002 does not convert them. Consumers must inspect locator extensions before comparing boxes from different adapters.

### SchemaVersions

Required exact versions for `block`, `derivation` and `relation`. Context bundles are independent outputs and carry their own root version.

## DocumentManifest

| Field | Type | Rule |
|---|---|---|
| `spec_version` | `0.1.0` | Required |
| `document_id` | UUIDv7 | Logical document identity |
| `version_id` | SHA-256 ID | Must equal `sha256:` plus `source.sha256` |
| `representation_id` | SHA-256 ID | Must equal the representation identity projection |
| `title` | string or null | Optional metadata |
| `state` | `STAGING \| READY \| FAILED \| DELETED` | Required |
| `created_at` | UTC timestamp | Required |
| `source` | SourceDescriptor | Required |
| `parser` | ParserDescriptor | Required |
| `schema_versions` | SchemaVersions | Required |
| `extensions` | JSON object | Default empty |

### SourceDescriptor

`connector`, `locator` and `media_type` are non-empty strings; `byte_length` is a non-negative integer; `sha256` is exactly 64 lowercase hex characters; `modified_at` is a UTC timestamp or null; `extensions` is a JSON object. A locator is data, not filesystem authority.

### State behavior

F002 validates state names only. Transaction rules governing transitions to `READY` belong to persistence/ingestion features.

## ContentBlock

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `0.1.0` | Required |
| `block_id` | UUID | Required; native source ID remains separate |
| `document_id` | UUIDv7 | Required |
| `version_id` | SHA-256 ID | Exact source version |
| `representation_id` | SHA-256 ID | Exact parser/normalization revision |
| `parent_id` | UUID or null | May not equal `block_id` |
| `kind` | documented BlockKind enum | Required |
| `order` | integer >= 0 | Required |
| `text` | string or null | Optional payload |
| `structured` | JSON object/array or null | Optional payload |
| `asset_id` | SHA-256 ID or null | Optional payload/reference |
| `canonical_hash` | SHA-256 ID | Must equal block-content identity projection |
| `source` | SourceLocator | Required |
| `trust` | TrustClassification | Required |
| `extensions` | JSON object | Default empty |

At least one of `text`, `structured` or `asset_id` is non-null; multiple forms may coexist. Empty text is real content and remains distinct from null.

Aggregate rule deferred to the normalizer/service boundary: a parent and child must share document, source version and representation scope.

## DerivationRecord

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `0.1.0` | Required |
| `artifact_id` | SHA-256 ID | Must equal derivation recipe projection |
| `state` | `PENDING \| READY \| FAILED \| STALE \| REVOKED` | Required |
| `generator` | ComponentDescriptor | Required |
| `model_id` | non-empty string or null | Optional provider/model identity |
| `input_hashes` | non-empty ordered unique tuple of SHA-256 IDs | Direct dependencies |
| `config_hash` | SHA-256 ID | Required |
| `prompt_hash` | SHA-256 ID or null | Required when a prompt affects output |
| `created_at` | UTC timestamp | Required |
| `completed_at` | UTC timestamp or null | State-dependent; never before `created_at` |
| `output_hash` | SHA-256 ID or null | Integrity of produced content, distinct from recipe key |
| `quality_signals` | JSON object | Default empty |
| `trust` | TrustClassification | Must use `zone=model_derived`, `role=data`, execution false |
| `extensions` | JSON object | Default empty |

Lifecycle combinations:

- `PENDING`: no completion time and no output hash.
- `READY`: completion time and output hash required.
- `FAILED`: completion time required and output hash absent.
- `STALE` or `REVOKED`: completion time and prior output hash required.

F002 records lifecycle state but does not execute, retry or invalidate derivations.

## Relation

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `0.1.0` | Required |
| `relation_id` | SHA-256 ID | Must equal relation identity projection |
| `kind` | documented RelationKind enum | Required |
| `source` | RecordReference | Typed source endpoint; version-pinned when representation-dependent |
| `target` | RecordReference | Typed target endpoint; version-pinned when representation-dependent and may not equal source |
| `confidence` | finite number 0..1 or null | Required for inferred reconciliation relation |
| `algorithm_version` | non-empty string or null | Required for inferred reconciliation relation |
| `provenance` | GenerationProvenance | Component plus UTC creation time |
| `extensions` | JSON object | Default empty |

### RecordReference discriminated union

- `block`: `document_id`, `version_id`, `representation_id`, `block_id`.
- `artifact`: `artifact_id`.
- `document_version`: `document_id`, `version_id`.
- `external`: non-empty `namespace` and `record_id`; this is an opaque data reference, never a fetch instruction.

Relation-specific record rules:

- `contains`, `precedes` and `caption_of` require two block endpoints in the same scope.
- `same_logical_block_as` requires two block endpoints for the same logical document, distinct source/representation scopes, confidence and algorithm version.
- `derived_from` and `source_for` require at least one artifact endpoint.
- Graph cycles and endpoint existence are aggregate concerns outside F002.

## ContextBundle

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `0.1.0` | Required |
| `bundle_id` | UUID | Required instance identity |
| `created_at` | UTC timestamp | Required |
| `query` | non-empty string | Required; treated as data |
| `mode` | `summary \| exact \| numeric \| visual \| verification \| mixed` | Required |
| `budget` | ContextBudget | Required |
| `versions` | non-empty unique tuple of VersionScope | Required |
| `items` | unique tuple of EvidenceItem | May be empty only when missing evidence is declared |
| `selection_trace` | tuple of SelectionDecision | Default empty |
| `warnings` | tuple of BundleNotice | Default empty |
| `missing_evidence` | tuple of MissingEvidence | Default empty |
| `extensions` | JSON object | Default empty |

### ContextBudget

`unit` is `tokens`, `characters` or `bytes`; `limit >= 1`; `estimated_used >= 0` and may not exceed the limit; `estimator` is non-empty; optional `actual_used >= 0` records a later provider count but may exceed an estimate.

### VersionScope

`document_id`, `version_id` and `representation_id`. The tuple is unique by all three values.

### EvidenceItem

| Field | Type | Rule |
|---|---|---|
| `provenance` | EvidenceProvenance | Scope, block ID and SourceLocator |
| `representation` | `metadata \| outline \| summary \| exact \| structured \| visual_handle \| original_handle` | Required |
| `content` | JSON value or null | Optional payload |
| `artifact_handle` | non-empty string or null | Opaque registered handle, not path authority |
| `artifact_id` | SHA-256 ID or null | Required for summary/derived stored evidence |
| `reason` | non-empty string | Selection rationale |
| `trust` | TrustClassification | Required |
| `extensions` | JSON object | Default empty |

At least one of non-null `content` or `artifact_handle` is required. Visual/original representations require a handle; summary representations require `artifact_id`. Every evidence scope must appear in the bundle's `versions`; duplicate evidence keys are rejected.

### Audit entries

- `SelectionDecision`: non-empty `stage`, `decision`, `reason`, optional `subject_id`, extensions.
- `BundleNotice`: non-empty stable `code`, human-readable `message`, extensions.
- `MissingEvidence`: evidence representation/type, non-empty reason, optional VersionScope, extensions.

## Relationships

```text
DocumentManifest 1 ── describes ── 1 DocumentVersion + Representation
ContentBlock    * ── belongs to ── 1 DocumentManifest scope
Relation        * ── links ─────── 2 RecordReference endpoints
DerivationRecord* ── depends on ── 1..* content/artifact hashes
ContextBundle   1 ── pins ──────── 1..* VersionScope
ContextBundle   1 ── selects ───── 0..* EvidenceItem
EvidenceItem    * ── cites ─────── 1 block SourceLocator and VersionScope
```
