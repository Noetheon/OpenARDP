# Data model and package specification

**Status:** Canonical data-model guidance. Existing public schemas remain the Feature 002 contracts. Export packaging is
an experiment owned by Feature 014, not a current stable format.

## 1. Design goals

- Human-debuggable JSON/JSONL.
- JSON Schema 2020-12 validation.
- Content-addressed assets.
- Streaming-friendly block records.
- Explicit provenance and trust classification.
- Forward-compatible extension fields.
- Optional JSON-LD/PROV/RO-Crate compatibility profile later.

## 2. Runtime versus export experiment

The implemented runtime store is content-addressed and deduplicated. No custom portable package has been selected.
Feature 014 evaluates existing packaging profiles and a minimal custom archive against concrete exchange requirements.
The earlier illustrative tree is retained only as a non-binding candidate:

```text
<export-root>/
├── manifest.json
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

If a future archive is adopted, import verifies it before publication and clients receive targeted content rather than
being asked to decode archives manually.

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

Source- and representation-scoped F002 block handle. F010 does not rewrite this frozen
identifier across versions. Cross-version continuity instead uses a separate
version-independent `lineage_id`; ambiguous blocks receive a new lineage. Page numbers
remain source coordinates and never become lineage identity.

### `lineage_id` and evidence binding

The lineage is a domain-separated RFC 8785/SHA-256 identity rooted at its first exact
F002 block reference. An evidence-binding digest combines that lineage with the exact
canonical block-content hash. Logical similarity can preserve continuity, but a
derivation is reusable only when this exact binding remains active.

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

### Runtime persistence records (F003–F004)

- `StoredObject`: canonical `sha256:<lowercase-hex>` identity plus verified byte length. Exact bytes remain in the CAS.
- `SourceKey`: exact binary-collated `(connector, opaque locator)` key; the locator is metadata, never a filesystem path.
- `LogicalDocument`: stable UUIDv7 assigned on first registration and reused across source versions.
- `DocumentVersion`: immutable source-version fact whose `version_id` equals its source object's identity, plus typed,
  ordered object references carrying verified byte lengths.
- `Job` and `JobEvent`: durable queued/running/terminal projection, bounded attempts, revision fencing, lease ownership and
  sanitized append-only transition evidence. Raw lease tokens are capabilities and are not records.
- `ReferenceSnapshot` and `ReachabilityReport`: deterministic read-only views of all historical version/job roots,
  verified objects, complete candidates and integrity/layout inconsistencies.
- `DocumentRepresentation`: fenced `STAGING`, `FAILED` or immutable complete `READY` projection for one document, source
  version and exact parser recipe.
- `RepresentationBlock`: body-free ordinal/parent/kind/order/line projection pointing to one canonical F002 block object.
- `DocumentHead` and `IngestionEvent`: current observation ordering plus append-only `COMMITTED`, `CACHE_HIT`,
  `FORCED_REPARSE` or convergence evidence without document bodies.
- `SourceSnapshot`, `ParsedTextDocument`, `IngestionResult`, `SourceStatus` and `OutlineItem`: bounded internal use-case
  records; document-originated text remains explicitly untrusted data.

These runtime records are internal Python/catalog contracts. They do not change the F002
public JSON Schema release and do not claim that a portable package or rich-document
representation exists. Feature 005 separately implements a non-authoritative lexical
index. Feature 006 adds an independent experimental `0.1.0` evidence family for retained
native artifacts, source-bound references, thin projections, and anti-escalation trust;
it does not alter the five F002 roots.

### Feature 010 internal records

- `ReconciliationPlan` contains both READY scopes, complete prior/current membership
  sets, conservative one-to-one matches, inactive bindings, bounded counts and a
  non-time result fingerprint.
- `BlockLineageMembership` binds one exact scoped block and canonical content digest to
  one lineage; a lineage has at most one member per representation and never crosses a
  logical document.
- `DerivationDependency` records ordered evidence-binding, immutable-object or exact
  producer-output input identity.
- `DerivationNode` maps an unchanged terminal F002 `DerivationRecord` into internal
  workspace state `CURRENT`, `STALE`, `FAILED` or `SUPERSEDED` and carries a complete
  row/edge fingerprint.
- `DerivationSlotKey` identifies one logical output purpose. Replacing its current
  artifact supersedes every prior current/stale occupant atomically.

These are internal revision-7 contracts, not a twelfth public schema. Lifecycle state
changes never rewrite the canonical record or output objects.

### Feature 006 evidence contracts

- `NativeRepresentation` records exact source/native artifact identities and a versioned
  provider recipe.
- `EvidenceReference` binds text, fixed-point page, table-cell, or opaque provider
  anchors to that exact source/native pair.
- `EvidenceProjection` adds only navigation, a content-addressed retrieval handle, trust,
  and immutable projection provenance.
- F006 `TrustClassification` records origin/effective zones, forces role `data` and
  instruction execution false, and rejects trust promotion.

The exact identity projections, semantic enforcement layers, fixtures, and migration
boundary are documented in the
[F006 contract](../specs/006-evidence-contract-foundation/contracts/evidence-contracts.md).

### Feature 007 rich runtime records

Feature 007 keeps complete Docling JSON in CAS and adds internal, provider-neutral
records without changing any public F002/F006 schema:

- `NativeArtifactDescriptor` binds the source, F006 native record, complete native
  object, exact component versions, provider/export profiles and optional local
  model-bundle identity.
- `RichEvidenceBundle` binds ordered F006 references/projections to their canonical
  record objects and exact retrieval objects.
- `RichParseAttempt` is append-only and classified `CANONICAL`, `CONVERGED` or
  `DIVERGED`; only the first canonical attempt is accepted for a READY scope.
- `RichRepresentationArtifacts` joins the accepted attempt to the existing zero-block
  base representation in one catalog snapshot.

Checksummed workspace migration 5 adds accepted-attempt, parse-attempt and per-attempt
evidence rows. All rich CAS objects, including divergent attempts, remain reachability
roots. A changed source, provider profile, semantic limit or model-bundle identity
creates a separate representation identity.

### Feature 008 context compilation records

Feature 008 adds two public roots and internal persistence records without changing
any earlier public schema:

- `ContextBundleV020` is the public `ContextBundle 0.2.0` handoff: query, exact
  version scopes, discriminated block/projection items in untrusted-data envelopes,
  selection trace, budget, warnings and missing evidence. Its UUIDv5 identity is
  recomputed over the canonical payload.
- `SelectionReceipt` is the public experimental `SelectionReceipt 0.1.0`: task digest,
  algorithm/estimator/policy identities with policy digest, corpus snapshot, complete
  budget ledger and the exhaustive selected/omitted/rejected/stale decision
  inventories. It is body-free by construction; its RFC 8785/SHA-256 identity equals
  the digest of its stored identity envelope, so the CAS object id equals the receipt
  id.
- `ContextCompilationRecord` plus `ContextCompilationScope` are internal immutable
  catalog rows linking both object identities, digests, counts and one recomputed row
  fingerprint; `ContextCompilationCommit` carries the atomic insert unit.

Checksummed workspace migration 6 adds the compilation and scope tables with RESTRICT
foreign keys to persisted representations; receipt and bundle objects are
reachability roots. Compilation rows are insert-once: a conflicting same-identity
record fails closed, an identical re-commit converges.

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

- Version application releases, public contracts, workspace schemas, provider profiles and export profiles independently.
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

Any future export inventory must list each packaged path, byte length and SHA-256. Import must verify all records before
making them available. Optional signatures/attestations remain a later decision.

At runtime, F003–F005 apply the same original-first principle before portable packaging exists: SHA-256 is computed over
exact streamed bytes, canonical leaves are immutable, catalog object lengths cannot drift, READY reuse verifies every
artifact, and every reachability inventory rehashes complete files. Prepared text blocks are reproducible derived data;
their trust role is fixed to data and instruction execution remains disabled.

## 9. Alignment strategy

Do not claim formal compliance initially. Design mappings for:

- JSON-LD for linked entities;
- W3C PROV for entity/activity/agent provenance;
- RO-Crate profile for packaging and contextual metadata;
- SPDX/CycloneDX for the software/model bill of materials of the implementation, not as the document content schema.
