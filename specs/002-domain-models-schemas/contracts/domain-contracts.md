# Contract: OpenARDP Domain Records 0.1.0

## Public roots

| Record | Model | Schema file | Version field |
|---|---|---|---|
| Document Manifest | `DocumentManifest` | `schemas/manifest.schema.json` | `spec_version` |
| Content Block | `ContentBlock` | `schemas/block.schema.json` | `schema_version` |
| Derivation Record | `DerivationRecord` | `schemas/derivation.schema.json` | `schema_version` |
| Relation | `Relation` | `schemas/relation.schema.json` | `schema_version` |
| Context Bundle | `ContextBundle` | `schemas/context-bundle.schema.json` | `schema_version` |

All current schemas declare Draft 2020-12 and accept exactly contract release `0.1.0`. `$id` remains the reviewed `https://openardp.example/schema/<record>-0.1.0.json` identifier for this pre-stable release. It is an identifier, not a network dependency.

## Compatibility

- Readers accept only explicitly installed releases.
- Invalid semantic versions, well-formed but uninstalled releases and unsupported major families produce distinct model validation messages.
- Direct fields are closed with `additionalProperties: false`.
- Unknown JSON values are preserved only under `extensions`.
- Adding a direct optional field in a future minor release is backward-compatible for a new reader consuming old data, but an old reader is not required to accept that uninstalled new schema.
- Identity algorithms and schema versions evolve independently.
- Changing an identity projection or schema compatibility guarantee requires an ADR and migration analysis.

## JSON validation boundary

The public raw-JSON path performs two steps:

1. Inspect the input JSON for duplicate object names, non-standard constants and unsafe integers without modifying values.
2. Validate the original JSON bytes with the selected strict Pydantic root model.

This path does not execute URLs, locators, extension values or document text. Validation errors hide raw input values by default.

## Canonical JSON

`canonical_json_bytes(value)` implements RFC 8785/JCS and returns UTF-8 bytes without a BOM. It accepts only the JCS/I-JSON subset:

- null, booleans, strings, safe integers and finite binary64 numbers;
- arrays whose order is preserved;
- objects with unique string keys sorted by raw UTF-16 code units;
- Unicode preserved without normalization.

It rejects unsupported Python objects, non-string keys, cycles, lone surrogates, non-finite values and integers outside the interoperable safe range. JCS-standard equivalences apply, including `1`/`1.0` and negative/positive zero.

`canonical_sha256(value)` returns `sha256:` followed by the lowercase digest of these bytes. A content identity is integrity metadata, not a signature or authority grant.

## Identity envelope

All canonical model identities except raw source versions use:

```json
{
  "canonicalization": "RFC8785",
  "domain": "openardp:<identity-purpose>",
  "identity_version": 1,
  "payload": {}
}
```

The envelope itself is canonicalized with RFC 8785 before SHA-256.

### Source version

```text
version_id = "sha256:" + SHA256(original_source_bytes)
```

No envelope is used because the documented identity is the exact original byte digest.

### Representation identity

Domain: `openardp:representation`

```json
{
  "version_id": "sha256:<source>",
  "parser": {
    "name": "synthetic",
    "version": "1.2.3",
    "profile": "default",
    "config_hash": "sha256:<config>"
  },
  "normalization_schema_version": "0.1.0"
}
```

Excluded: document/title/state/timestamps, source locator, extensions and non-identity parser metadata.

### Block content identity

Domain: `openardp:block-content`

```json
{
  "kind": "paragraph",
  "text": "Exact extracted text",
  "structured": null,
  "asset_id": null
}
```

Excluded: block/document/version/representation IDs, parent/order, source locator, trust, timestamps and extensions. Moving unchanged content therefore does not change its content fingerprint.

### Derivation artifact identity

Domain: `openardp:derivation`

```json
{
  "input_hashes": ["sha256:<ordered-input>"],
  "generator": {
    "name": "synthetic-summary",
    "version": "1.0.0",
    "profile": "default"
  },
  "model_id": null,
  "config_hash": "sha256:<config>",
  "prompt_hash": null
}
```

Excluded: lifecycle state, timestamps, output hash, quality, trust and extensions. `output_hash` separately verifies produced bytes/content.

### Relation identity

Domain: `openardp:relation`

```json
{
  "kind": "contains",
  "source": {"record_type": "block", "...": "complete reference"},
  "target": {"record_type": "block", "...": "complete reference"}
}
```

Direction is significant. Each endpoint projection contains only the documented core fields for its `record_type`;
endpoint and relation `extensions` are excluded. Undeclared endpoint fields are rejected rather than silently becoming
version-1 identity inputs. Confidence, algorithm version and provenance time are also excluded.

## Schema versus semantic enforcement

`schemas/README.md` must publish a matrix for every non-trivial invariant. Examples:

| Invariant | Layer |
|---|---|
| Hash/UUID syntax, enums, numeric bounds | Schema + model |
| At least one non-null block payload | Schema + model |
| `version_id` equals `source.sha256` | Record model |
| Recomputed representation/block/artifact/relation ID | Record model |
| `estimated_used <= limit` | Record model |
| Evidence scope belongs to bundle versions | Record model |
| Parent block exists in identical scope | Aggregate/service later |
| Relation graph is acyclic where required | Aggregate/service in F010 |

## Deterministic schema export

`scripts/generate_schemas.py` exposes a pure `build_schemas()` mapping and an explicit write command. Output rules:

- UTF-8, LF, two-space indentation and trailing newline;
- stable file order and sorted JSON object keys;
- Pydantic validation-mode schemas;
- root `$schema`, stable `$id`, title and `x-openardp-schema-version` metadata;
- no network or timestamp in output.

Tests compare generated bytes with committed schemas. Normal test execution never rewrites them.
