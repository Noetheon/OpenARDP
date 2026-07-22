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

Version-1 domain-separated RFC 8785 identity over the source version, parser name/version/profile/configuration hash and
normalization schema version. It changes when the parsing recipe changes even when the authoritative bytes do not.
Document title/state, timestamps, source locations, extensions and unrelated parser metadata are excluded.

### `block_id`

Stable within a logical document where possible:

1. reuse a trustworthy native Office/XML object identifier;
2. otherwise reconcile against the previous version by exact fingerprint;
3. then structural path + similarity matching;
4. create a new UUID when confidence is below threshold.

Never encode page numbers into permanent block identity because pagination changes.

### `artifact_id`

For derivations, a version-1 recipe identity over ordered direct inputs, generator name/version/profile, optional model,
configuration hash and optional prompt hash. It is not proof of output bytes: `output_hash` separately records produced
content integrity.

### Canonicalization and identity governance

All structured identity envelopes use RFC 8785 without Unicode normalization. Values outside the interoperable JSON
domain—non-finite floats, unsafe integers, lone surrogates, cycles, non-string mapping keys and runtime-only Python
objects—are rejected rather than coerced. Source versions remain direct SHA-256 digests of original bytes.

Block content identity includes only `kind`, `text`, `structured` and `asset_id`. Relation identity includes only the kind
and complete typed source/target references. Operational metadata is intentionally excluded. The exact preimages are in
the [F002 domain contract](../specs/002-domain-models-schemas/contracts/domain-contracts.md) and the governing decision is
[ADR 0006](adr/0006-rfc8785-canonical-identities.md).

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

- `block_id`, `document_id`, `version_id`, `representation_id`;
- `kind`;
- `parent_id`, `order`;
- at least one non-null `text`, `structured` or `asset_id` payload;
- source locator and coordinates;
- canonical content hash;
- trust and sensitivity labels;
- extraction provenance.

### Relation

Relations use a deterministic edge ID and discriminated source/target references. A block reference pins document,
source version, representation and block; artifact, document-version and namespaced external references carry their own
complete identities. Examples:

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

### Context Bundle

An immutable, budgeted evidence handoff with exact `{document_id, version_id, representation_id}` scopes, selected
evidence, provenance, selection decisions, notices and explicit missing-evidence records. It validates internal scope and
budget consistency but does not retrieve data or compile context in F002.

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
- The installed F002 readers accept exactly reviewed release `0.1.0`; a well-formed but uninstalled minor is rejected
  distinctly from malformed text and an unsupported major family.
- Core records are closed. Readers preserve JSON-only unknown data only under `extensions`.
- A future minor may add optional fields only through a new reviewed schema; an old reader is not required to accept an
  uninstalled release.
- Canonicalization rules and ID algorithms are versioned independently.
- Maintain golden package fixtures for every supported version.
- Removing fields, weakening invariants or changing identity inputs requires an ADR and migration analysis.

Schema-expressible rules (shape, required members, enum/pattern/bounds and structural alternatives) are enforced by both
the public schema and model. Recomputed identifiers, lifecycle combinations, budget comparisons and within-record scope
membership are record-semantic model rules. Cross-record existence and graph properties are aggregate-semantic rules for
later services. See [`schemas/README.md`](../schemas/README.md) for the complete matrix.

## 8. Integrity

`integrity.json` lists every packaged file path, byte length and SHA-256. Portable import verifies all records before making
them available. Optional signatures/attestations are post-MVP.

## 9. Alignment strategy

Do not claim formal compliance initially. Design mappings for:

- JSON-LD for linked entities;
- W3C PROV for entity/activity/agent provenance;
- RO-Crate profile for packaging and contextual metadata;
- SPDX/CycloneDX for the software/model bill of materials of the implementation, not as the document content schema.
