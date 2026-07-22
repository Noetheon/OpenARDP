# Data model and package specification

## 1. Design goals

- Human-debuggable JSON/JSONL.
- JSON Schema 2020-12 validation.
- Content-addressed assets.
- Streaming-friendly block records.
- Explicit provenance and trust classification.
- Forward-compatible extension fields.
- Optional JSON-LD/PROV/RO-Crate compatibility profile later.

## 2. Runtime versus portable package

The runtime store is optimized and deduplicated. A portable export is a self-contained ZIP.

```text
<document-id>-<version-id>.ardp.zip
├── ardp-manifest.json
├── document.json
├── blocks.jsonl
├── relations.jsonl
├── derivations.jsonl
├── integrity.json
├── assets/
│   └── sha256/<hash>
├── native/
│   └── parser-output.json
└── schemas/                 # optional frozen schemas
```

Never require an LLM to unzip or decode this manually. The CLI/MCP server reads the package and returns targeted content.

## 3. Identity

### `document_id`

Opaque UUIDv7 generated on first registration and persisted across versions. It represents the logical document, not its
current bytes.

### `version_id`

`sha256:<source-byte-hash>`. Two byte-identical sources are the same source version. Parsing profile changes create a new
**representation revision**, not a new source version.

### `representation_id`

Hash of source version, parser identity/version/config and normalization schema version.

### `block_id`

Stable within a logical document where possible:

1. reuse a trustworthy native Office/XML object identifier;
2. otherwise reconcile against the previous version by exact fingerprint;
3. then structural path + similarity matching;
4. create a new UUID when confidence is below threshold.

Never encode page numbers into permanent block identity because pagination changes.

### `artifact_id`

Content/derivation key as defined in the architecture.

## 4. Canonical versus derived data

### Canonical source facts

- directly extracted text;
- actual table cells;
- hierarchy and reading order;
- source coordinates;
- original binary assets;
- comments/notes when configured;
- parser warnings.

### Derived data

- OCR where the source lacks machine text;
- summaries;
- captions;
- chart interpretations;
- entities;
- embeddings;
- classifications;
- answer caches.

OCR may be necessary to expose scanned content, but it remains a derived assertion with confidence and image provenance.

## 5. Core entities

### Document manifest

See `schemas/manifest.schema.json`.

### Content block

Required fields:

- `block_id`, `document_id`, `version_id`;
- `kind`;
- `parent_id`, `order`;
- `content` or structured payload reference;
- source locator and coordinates;
- canonical content hash;
- trust and sensitivity labels;
- extraction provenance.

### Relation

Examples:

- `contains`;
- `precedes`;
- `caption_of`;
- `source_for`;
- `derived_from`;
- `mentions`;
- `supersedes`;
- `same_logical_block_as`.

### Derivation record

Captures generator, model, input artifacts, prompt/config hashes, timestamps, quality signals and lifecycle state.

## 6. Trust model fields

Every content-bearing record has:

```json
{
  "trust": {
    "zone": "external_untrusted",
    "role": "data",
    "instruction_execution_allowed": false,
    "integrity": "verified_sha256",
    "sensitivity": "internal"
  }
}
```

`role=data` is not a prompt hint; it is an enforced policy input. MCP tools never expose a method that executes text found
in a document.

## 7. Schema evolution

- Use semantic versioning for package/specification versions.
- Readers must reject unsupported major versions.
- Readers should ignore unknown extension properties under `extensions`.
- Minor versions may add optional fields only.
- Canonicalization rules and ID algorithms are versioned independently.
- Maintain golden package fixtures for every supported version.

## 8. Integrity

`integrity.json` lists every packaged file path, byte length and SHA-256. Portable import verifies all records before making
them available. Optional signatures/attestations are post-MVP.

## 9. Alignment strategy

Do not claim formal compliance initially. Design mappings for:

- JSON-LD for linked entities;
- W3C PROV for entity/activity/agent provenance;
- RO-Crate profile for packaging and contextual metadata;
- SPDX/CycloneDX for the software/model bill of materials of the implementation, not as the document content schema.
